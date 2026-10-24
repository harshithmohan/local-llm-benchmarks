#!/usr/bin/env python3
"""shoko — Shoko log-viewer benchmark runner.

Implements prepare (build a history-free repo from the base commit, run the
checks, install dependencies) and run (the stage loop: implement → normalize →
gates → harness → judge, with reviewer repair between stages). The pipeline
writes patch/gates/harness/score/review artifacts into the run directory.

stdlib only.
"""

import argparse
import datetime
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

import shoko_proc

# Running as a script makes this module `__main__`; the pipeline imports it as
# `shoko`.  Register the alias so both names resolve to the same module — a
# second copy would carry its own `Fail`, and this module's handlers would miss
# exceptions the pipeline raises.
if __name__ == "__main__":
    sys.modules.setdefault("shoko", sys.modules[__name__])

HERE = os.path.dirname(os.path.abspath(__file__))

WEBUI_URL = "https://github.com/ShokoAnime/Shoko-WebUI"
SERVER_URL = "https://github.com/ShokoAnime/ShokoServer"

# ---------------------------------------------------------------------------
# exit codes
# ---------------------------------------------------------------------------

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_HALTED = 4
EXIT_LOCKED = 5
EXIT_PRECOND = 10
EXIT_INTERNAL = 70

RUN_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,79}$")

CONFIG_ALLOWLIST_EXACT = {
    "core.repositoryformatversion",
    "core.filemode",
    "core.bare",
    "core.logallrefupdates",
    # macOS host artifacts: git init writes `core.ignorecase` on a
    # case-insensitive APFS volume and `core.precomposeunicode` on any macOS
    # build.  Neither carries a remote, ref, stash, alternate or reference
    # information -- the things this check exists to catch.
    "core.ignorecase",
    "core.precomposeunicode",
}

# Host git runs hardened: no ambient GIT_*, no host global/system config, no
# host init template, no fsmonitor, no hooks, no textconv/external diff
# drivers.  The bench tree's .git is agent-writable, so host git must never
# pick up configuration or machinery from it or from the host.
GIT_HARDEN = [
    "-c",
    "core.fsmonitor=false",
    "-c",
    "core.hooksPath=/dev/null",
]

#: diff-level hardening: --no-textconv/--no-ext-diff are not top-level git
#: options, so they go on the invocations that actually produce a diff.
GIT_DIFF_HARDEN = ["--no-ext-diff", "--no-textconv"]

_GIT_TEMPLATE_DIR = None


class Fail(Exception):
    def __init__(self, cid, detail=""):
        super().__init__("%s: %s" % (cid, detail))
        self.cid = cid
        self.detail = detail


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------


def now_iso():
    return (
        datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    )


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def dump_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, path)


DEFAULT_PROC_TIMEOUT_S = 900


def proc(argv, cwd=None, input=None, env=None, timeout=None):
    """Run a host process.  Every caller gets a wall-clock bound: a host call
    that never returns must not hang the runner for ever, so an unspecified
    timeout becomes DEFAULT_PROC_TIMEOUT_S."""
    if timeout is None:
        timeout = DEFAULT_PROC_TIMEOUT_S
    return subprocess.run(
        argv,
        cwd=cwd,
        input=input,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        timeout=timeout,
    )


def proc_text(argv, cwd=None, timeout=None, env=None):
    p = proc(argv, cwd=cwd, timeout=timeout, env=env)
    return (
        p.returncode,
        p.stdout.decode("utf-8", "replace"),
        p.stderr.decode("utf-8", "replace"),
    )


def empty_template_dir():
    global _GIT_TEMPLATE_DIR
    if _GIT_TEMPLATE_DIR is None:
        d = os.path.join(tempfile.gettempdir(), "shoko-empty-template")
        os.makedirs(d, exist_ok=True)
        _GIT_TEMPLATE_DIR = d
    return _GIT_TEMPLATE_DIR


PLAYWRIGHT_CACHE_PREFIX = "playwright-transform-cache"


def sweep_stale_transform_caches(tmpdir=None):
    """Best-effort removal of stale Playwright transform caches.

    Playwright derives its transform cache from `os.tmpdir()` as
    `<tmp>/playwright-transform-cache-<uid>`. The harness runs with a private
    `TMPDIR` inside the run dir, so a new run leaves none of its own — but a
    pre-fix run, or a concurrent unrelated Playwright, can leave one directly
    under the shared temp dir, and a pass could read compiled specs out of it.
    Only direct children of `tmpdir` whose name starts with
    `playwright-transform-cache` are touched; nothing is recursive over `tmpdir`
    itself and every other entry is left alone. Returns `(removed, unremovable)`,
    where `unremovable` is the list of matching names that could not be removed
    — a WARN, never a failure. Idempotent.
    """
    if tmpdir is None:
        tmpdir = tempfile.gettempdir()
    removed = 0
    unremovable = []
    try:
        names = sorted(os.listdir(tmpdir))
    except OSError:
        return removed, unremovable
    for name in names:
        if not name.startswith(PLAYWRIGHT_CACHE_PREFIX):
            continue
        path = os.path.join(tmpdir, name)
        try:
            if os.path.isdir(path) and not os.path.islink(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            removed += 1
        except OSError:
            unremovable.append(name)
    return removed, unremovable


def git_env(extra=None):
    """A runner-owned environment for host git.

    Ambient GIT_* variables are dropped and the global/system configuration
    and the init template are neutralised, so nothing on the host or in an
    agent-writable .git can redirect a host git invocation.
    """
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["GIT_CONFIG_GLOBAL"] = "/dev/null"
    env["GIT_CONFIG_SYSTEM"] = "/dev/null"
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_TEMPLATE_DIR"] = empty_template_dir()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_OPTIONAL_LOCKS"] = "0"
    env["LC_ALL"] = "C"
    if extra:
        env.update(extra)
    return env


def git_run(git_bin, *args, cwd=None, input=None, timeout=None, env_extra=None):
    argv = [git_bin] + GIT_HARDEN + list(args)
    return proc(argv, cwd=cwd, input=input, timeout=timeout, env=git_env(env_extra))


def git_bytes(git_bin, *args, cwd=None, env_extra=None):
    return git_run(git_bin, *args, cwd=cwd, env_extra=env_extra).stdout


def git_text(git_bin, *args, cwd=None, timeout=None, env_extra=None):
    r = git_run(git_bin, *args, cwd=cwd, timeout=timeout, env_extra=env_extra)
    return (
        r.returncode,
        r.stdout.decode("utf-8", "replace"),
        r.stderr.decode("utf-8", "replace"),
    )


def walk_tree(root, skip=(".git", "node_modules")):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip]
        yield dirpath, dirnames, filenames


# ---------------------------------------------------------------------------
# context
# ---------------------------------------------------------------------------


class Ctx:
    def __init__(
        self,
        *,
        benchmark_dir,
        bench_root,
        config,
        config_path,
        run,
        args,
        env_path=None,
        mode="production",
    ):
        self.benchmark_dir = os.path.abspath(benchmark_dir)
        self.bench_root = os.path.abspath(os.path.expanduser(bench_root))
        self.config = config
        self.config_path = config_path
        self.run = run
        self.args = args
        self.env_path = env_path or os.environ.get("PATH", "/usr/bin:/bin")
        self.mode = mode
        self._spec = None

    @property
    def spec(self):
        """The immutable post-prepare contract, loaded only from run.json.

        Prepare is the one command that legitimately builds run.json from
        `ctx.args`; every later command must read the spec from run.json so
        there is a single source of truth.
        """
        if self._spec is None:
            import shoko_pipeline  # local import: avoids a cycle at import time

            self._spec = shoko_pipeline.RunSpec.from_file(
                os.path.join(self.state_dir(), "run.json")
            )
        return self._spec

    def set_spec(self, spec):
        self._spec = spec
        return spec

    # paths ---------------------------------------------------------------
    def run_dir(self, run=None):
        return os.path.join(self.bench_root, run or self.run)

    def state_dir(self, run=None):
        return os.path.join(self.bench_root, (run or self.run) + ".state")

    def views_dir(self, run=None):
        return os.path.join(self.bench_root, (run or self.run) + ".views")

    def lock_path(self):
        return os.path.join(self.bench_root, ".shoko.lock")

    def which(self, tool):
        return shutil.which(tool, path=self.env_path)


class Reporter:
    def __init__(self, on_event=None):
        self.checks = []
        self.on_event = on_event

    def _emit(self, cid, status, detail):
        if self.on_event is not None:
            try:
                self.on_event(status, cid, detail)
            except Exception:
                pass

    def ok(self, cid, detail=""):
        self.checks.append((cid, "PASS", detail))
        self._emit(cid, "PASS", detail)
        print(("PASS %s %s" % (cid, detail)).rstrip())

    def warn(self, cid, detail=""):
        self.checks.append((cid, "WARN", detail))
        self._emit(cid, "WARN", detail)
        print(("WARN %s %s" % (cid, detail)).rstrip())

    def fail(self, cid, detail=""):
        self.checks.append((cid, "FAIL", detail))
        self._emit(cid, "FAIL", detail)
        print(("FAIL %s %s" % (cid, detail)).rstrip())
        raise Fail(cid, detail)


# ---------------------------------------------------------------------------
# run store (state.json + run.json)
# ---------------------------------------------------------------------------


class RunStore:
    def __init__(self, state_dir):
        self.dir = state_dir
        self.state_path = os.path.join(state_dir, "state.json")
        self.run_path = os.path.join(state_dir, "run.json")

    def init(self):
        os.makedirs(self.dir, exist_ok=True)

    def read_state(self):
        if os.path.exists(self.state_path):
            return load_json(self.state_path)
        return None

    def write_state(self, state):
        dump_json(self.state_path, state)

    def new_state(self):
        """A fresh state record for a new run."""
        return {"schema": 1, "phase": "prepared", "stage": 0, "step": "impl"}


# ---------------------------------------------------------------------------
# lock
# ---------------------------------------------------------------------------


class Lock:
    def __init__(self, path):
        self.path = path
        self.fh = None

    def acquire(self):
        parent = os.path.dirname(self.path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self.fh = open(self.path, "a+")
        try:
            fcntl.flock(self.fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.fh.close()
            self.fh = None
            return False
        return True

    def release(self):
        if self.fh is not None:
            try:
                fcntl.flock(self.fh.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
            self.fh.close()
            self.fh = None


# ---------------------------------------------------------------------------
# guards
# ---------------------------------------------------------------------------


def inside_git_worktree(path, git_bin):
    d = os.path.abspath(path)
    while not os.path.isdir(d):
        nd = os.path.dirname(d)
        if nd == d:
            return False
        d = nd
    if not git_bin:
        return False
    return git_run(git_bin, "-C", d, "rev-parse", "--show-toplevel").returncode == 0


def bench_root_problem(bench_root, benchmark_dir, home, git_bin):
    br = os.path.realpath(bench_root)
    bm = os.path.realpath(benchmark_dir)
    if br == bm or br.startswith(bm + os.sep):
        return "inside the benchmark repo (%s)" % bm
    if br == home or br.startswith(home + os.sep):
        rel = os.path.relpath(br, home)
        parts = rel.split(os.sep)
        if parts[0] == "code-workspace":
            return "under $HOME/code-workspace (%s)" % br
        if parts[:2] == [".config"]:
            return "under $HOME/.config (%s)" % br
        if parts[:3] == [".local", "share", "opencode"]:
            return "under $HOME/.local/share/opencode (%s)" % br
    if inside_git_worktree(br, git_bin):
        return "inside a git work tree (%s)" % br
    return None


# ---------------------------------------------------------------------------
# dev-repo helpers (read-only!)
# ---------------------------------------------------------------------------


def _hash_bytes(h, label, data):
    h.update(label.encode("utf-8", "replace"))
    h.update(b"\0")
    h.update(len(data).to_bytes(8, "little"))
    h.update(data)


def _read_bytes(path):
    try:
        if os.path.islink(path):
            return b"symlink:" + os.readlink(path).encode("utf-8", "replace")
        with open(path, "rb") as fh:
            return fh.read()
    except OSError:
        return b"<absent>"


def _git_dir_of(repo):
    """The real git dir of a checkout (handles a linked worktree's .git file)."""
    p = os.path.join(repo, ".git")
    if os.path.isdir(p):
        return p
    if os.path.isfile(p):
        with open(p, "r", encoding="utf-8", errors="replace") as fh:
            line = fh.read().strip()
        if line.startswith("gitdir:"):
            target = line.split(":", 1)[1].strip()
            if not os.path.isabs(target):
                target = os.path.join(repo, target)
            return os.path.normpath(target)
    return p


def git_snapshot(repo, git_bin):
    """A *content-sensitive* snapshot of a dev repo.

    A path list is not enough: a checkout that is already dirty can be edited
    without any path changing.  So this folds in the binary diff of the work
    tree against HEAD, the bytes of every untracked file, the git metadata
    that decides what the repo *is* (.git/HEAD, config, packed-refs, index,
    refs/stash and the alternates/shallow/grafts files) and the worktree list.
    """
    h = hashlib.sha256()
    for args in (
        ("for-each-ref",),
        ("stash", "list"),
        ("worktree", "list", "--porcelain"),
        ("status", "--porcelain=v1", "-z"),
        ("rev-parse", "HEAD"),
        ("config", "--local", "--list"),
    ):
        _hash_bytes(h, "git " + " ".join(args), git_bytes(git_bin, *args, cwd=repo))
    _hash_bytes(
        h,
        "git diff --binary HEAD",
        git_bytes(git_bin, "diff", *GIT_DIFF_HARDEN, "--binary", "HEAD", cwd=repo),
    )

    for rel in git_text(
        git_bin, "ls-files", "--others", "--exclude-standard", "-z", cwd=repo
    )[1].split("\0"):
        if not rel:
            continue
        _hash_bytes(h, "untracked " + rel, _read_bytes(os.path.join(repo, rel)))

    git_dir = _git_dir_of(repo)
    for rel in (
        "HEAD",
        "config",
        "packed-refs",
        "index",
        "refs/stash",
        "shallow",
        "info/grafts",
        "objects/info/alternates",
    ):
        _hash_bytes(h, ".git/" + rel, _read_bytes(os.path.join(git_dir, rel)))
    return h.hexdigest()


def dev_snapshot(webui, server, git_bin):
    """Snapshot both dev repos.  Both are compared -- neither is discarded."""
    return {
        "webui": git_snapshot(webui, git_bin),
        "server": git_snapshot(server, git_bin),
    }


def dev_unchanged_problems(before, after):
    """Pure comparison of the dev-repo snapshot taken before and after prepare."""
    problems = []
    for key in sorted(set(before) | set(after)):
        if before.get(key) != after.get(key):
            problems.append(
                "%s changed (%s != %s)"
                % (
                    key,
                    (before.get(key) or "<none>")[:16],
                    (after.get(key) or "<none>")[:16],
                )
            )
    return problems


def git_archive(repo, ref, git_bin):
    r = git_run(git_bin, "-C", repo, "archive", "--format=tar", ref)
    if r.returncode != 0:
        raise RuntimeError(
            "git archive failed: %s" % r.stderr.decode("utf-8", "replace")
        )
    return r.stdout


def ensure_clone(url, cache_dir, git_bin):
    """Clone `url` to `cache_dir` if missing, else fetch. Returns `cache_dir`."""
    git_dir = os.path.join(cache_dir, ".git")
    if os.path.isdir(git_dir):
        # Best-effort fetch to make sure `base`/`server_pin` exist; ignore failures (offline cache).
        try:
            git_text(git_bin, "-C", cache_dir, "fetch", "--all", "--prune", timeout=120)
        except Exception:
            pass
        return cache_dir
    # Fresh clone: shallow filter keeps download small but still allows `archive` of any commit.
    parent = os.path.dirname(cache_dir)
    os.makedirs(parent, exist_ok=True)
    # Prefer blobless clone; fallback to full clone if filter unsupported.
    rc, _out, _err = git_text(
        git_bin, "clone", "--filter=blob:none", url, cache_dir, timeout=300
    )
    if rc != 0:
        # Fallback: full clone (clean up partial dir first)
        if os.path.isdir(cache_dir):
            shutil.rmtree(cache_dir, ignore_errors=True)
        rc2, _o2, err2 = git_text(git_bin, "clone", url, cache_dir, timeout=300)
        if rc2 != 0:
            raise RuntimeError("git clone failed for %s: %s" % (url, err2))
    return cache_dir


# ---------------------------------------------------------------------------
# extracted checks (pure: callable straight from tests on a fixture repo)
# ---------------------------------------------------------------------------


def apply_checks(rep, checks, soft=False):
    """Report (id, status, detail) triples; hard mode stops at the first FAIL."""
    ok = True
    for cid, status, detail in checks:
        if status == "PASS":
            rep.ok(cid, detail)
            continue
        ok = False
        if soft:
            rep.checks.append((cid, "FAIL", detail))
            print(("FAIL %s %s" % (cid, detail)).rstrip())
        else:
            rep.fail(cid, detail)
    return ok


def check_bench_repo(webui_tree, branch, git_bin, expect_head=None):
    """P4 bench-repo hygiene on a (possibly hostile) bench repo."""
    checks = []

    if expect_head:
        # Task 1: `pins.run_base_commit` is immutable like the other pins, so
        # verify re-asserts that the candidate repo still points at it.
        head = git_text(git_bin, "-C", webui_tree, "rev-parse", "HEAD")[1].strip()
        checks.append(
            (
                "run-base-commit",
                "PASS" if head == expect_head else "FAIL",
                head if head == expect_head else "%s != %s" % (head, expect_head),
            )
        )

    out = git_text(git_bin, "-C", webui_tree, "remote")[1]
    remotes = [x for x in out.splitlines() if x.strip()]
    checks.append(
        (
            "no-remote",
            "FAIL" if remotes else "PASS",
            out.strip() if remotes else "no remotes",
        )
    )

    out = git_text(git_bin, "-C", webui_tree, "stash", "list")[1]
    stashes = [x for x in out.splitlines() if x.strip()]
    checks.append(
        ("no-stash", "FAIL" if stashes else "PASS", out.strip() if stashes else "empty")
    )

    out = git_text(git_bin, "-C", webui_tree, "replace", "-l")[1]
    repl = [x for x in out.splitlines() if x.strip()]
    checks.append(
        ("no-replace", "FAIL" if repl else "PASS", out.strip() if repl else "empty")
    )

    bad = [
        rel
        for rel in (".git/objects/info/alternates", ".git/shallow", ".git/info/grafts")
        if os.path.exists(os.path.join(webui_tree, rel))
    ]
    checks.append(
        (
            "no-alternates",
            "FAIL" if bad else "PASS",
            "present: " + ", ".join(bad) if bad else "none",
        )
    )

    cfg_out = git_text(git_bin, "-C", webui_tree, "config", "--local", "--list")[1]
    bad_keys = []
    for line in cfg_out.splitlines():
        if not line.strip():
            continue
        key = line.split("=", 1)[0].strip().lower()
        if key in CONFIG_ALLOWLIST_EXACT or key.startswith("user."):
            continue
        bad_keys.append(key)
    checks.append(
        (
            "config-allowlist",
            "FAIL" if bad_keys else "PASS",
            "unexpected keys: " + ", ".join(bad_keys) if bad_keys else "ok",
        )
    )

    count = git_text(git_bin, "-C", webui_tree, "rev-list", "--all", "--count")[
        1
    ].strip()
    refs = [
        x
        for x in git_text(
            git_bin, "-C", webui_tree, "for-each-ref", "--format=%(refname)"
        )[1].splitlines()
        if x.strip()
    ]
    wt_count = len(
        [
            x
            for x in git_text(
                git_bin, "-C", webui_tree, "worktree", "list", "--porcelain"
            )[1].splitlines()
            if x.startswith("worktree ")
        ]
    )
    single = count == "1" and refs == ["refs/heads/" + branch] and wt_count == 1
    checks.append(
        (
            "single-ref",
            "PASS" if single else "FAIL",
            "count=%s refs=%s worktrees=%d" % (count, refs, wt_count),
        )
    )

    fsck_out = git_run(
        git_bin, "-C", webui_tree, "fsck", "--unreachable", "--no-reflogs"
    )
    fsck = fsck_out.stdout.decode("utf-8", "replace").strip()
    checks.append(
        (
            "fsck-clean",
            "FAIL" if fsck else "PASS",
            fsck.splitlines()[0] if fsck else "no unreachable objects",
        )
    )

    all_ids = set(
        x.strip()
        for x in git_text(
            git_bin,
            "-C",
            webui_tree,
            "cat-file",
            "--batch-all-objects",
            "--batch-check=%(objectname)",
        )[1].splitlines()
        if x.strip()
    )
    reachable = set()
    for line in git_text(git_bin, "-C", webui_tree, "rev-list", "--objects", "--all")[
        1
    ].splitlines():
        parts = line.split()
        if parts:
            reachable.add(parts[0])
    if all_ids == reachable:
        checks.append(
            ("object-set", "PASS", "%d objects, all reachable" % len(all_ids))
        )
    else:
        checks.append(
            (
                "object-set",
                "FAIL",
                "all=%d reachable=%d diff=%d"
                % (len(all_ids), len(reachable), len(all_ids ^ reachable)),
            )
        )
    return checks


def check_containment(tree, webui_tree, git_bin):
    """P5 containment: exactly one .git, and no absolute/escaping symlinks."""
    checks = []
    found = []
    for dirpath, dirnames, filenames in os.walk(tree):
        if "node_modules" in dirnames:
            dirnames.remove("node_modules")
        if ".git" in dirnames:
            found.append(os.path.join(dirpath, ".git"))
        if ".git" in filenames:
            found.append(os.path.join(dirpath, ".git"))
        dirnames[:] = [d for d in dirnames if d != ".git"]
    expected_git = os.path.join(webui_tree, ".git")
    detail = None
    if found != [expected_git]:
        detail = "found .git at %s" % found
    elif git_run(git_bin, "-C", tree, "rev-parse", "--show-toplevel").returncode == 0:
        detail = "run root %s is inside a git work tree" % tree
    checks.append(
        (
            "git-containment",
            "FAIL" if detail else "PASS",
            detail or "single .git at the bench repo",
        )
    )

    bad_links = []
    tree_real = os.path.realpath(tree)
    for dirpath, dirnames, filenames in os.walk(tree):
        if "node_modules" in dirnames:
            dirnames.remove("node_modules")
        for name in list(dirnames) + list(filenames):
            p = os.path.join(dirpath, name)
            if not os.path.islink(p):
                continue
            target = os.readlink(p)
            if os.path.isabs(target):
                bad_links.append(
                    "%s -> %s (absolute)" % (os.path.relpath(p, tree), target)
                )
                continue
            resolved = os.path.realpath(p)
            if not (resolved == tree_real or resolved.startswith(tree_real + os.sep)):
                bad_links.append(
                    "%s -> %s (escapes tree)" % (os.path.relpath(p, tree), target)
                )
    checks.append(
        (
            "no-abs-symlink",
            "FAIL" if bad_links else "PASS",
            bad_links[0] if bad_links else "no absolute or escaping symlinks",
        )
    )
    return checks


def check_server_greps(server_tree):
    """P7: the pinned server tree carries the reference implementation."""
    tokens = (
        "TryParseLogFilterDsl",
        "Range/Read",
        "Range/Download",
        "File/Current/Download",
    )
    greps = {t: grep_tree_count(server_tree, t) for t in tokens}
    missing = [t for t, n in greps.items() if n < 1]
    if missing:
        return [("server-greps", "FAIL", "missing: " + ", ".join(missing))]
    return [
        ("server-greps", "PASS", " ".join("%s=%d" % (k, v) for k, v in greps.items()))
    ]


def extract_tar(tar_bytes, dest, tar_bin):
    os.makedirs(dest, exist_ok=True)
    r = proc([tar_bin, "-x", "-C", dest, "--no-same-owner"], input=tar_bytes)
    if r.returncode != 0:
        raise RuntimeError(
            "tar extract failed: %s" % r.stderr.decode("utf-8", "replace")
        )


def grep_tree_count(root, token):
    needle = token.encode()
    n = 0
    for dirpath, _dirnames, filenames in walk_tree(root):
        for f in filenames:
            p = os.path.join(dirpath, f)
            try:
                if os.path.islink(p):
                    continue
                with open(p, "rb") as fh:
                    n += fh.read().count(needle)
            except OSError:
                continue
    return n


DIFF_PATH_RE = re.compile(r"^diff --git a/(.*) b/(.*)$")


def diff_paths(diff_text):
    paths = []
    for line in diff_text.splitlines():
        m = DIFF_PATH_RE.match(line)
        if m and m.group(2) != "/dev/null":
            paths.append(m.group(2))
    return paths


# ---------------------------------------------------------------------------
# config / ctx construction
# ---------------------------------------------------------------------------


def default_config_path():
    return os.path.join(HERE, "shoko.config.json")


def default_bench_root():
    xdg = os.environ.get("XDG_STATE_HOME") or os.path.join(
        os.path.expanduser("~"), ".local", "state"
    )
    return os.path.join(xdg, "shoko")


def make_ctx(
    args,
    config=None,
    config_path=None,
    mode="production",
    benchmark_dir=None,
    bench_root=None,
    env_path=None,
):
    config_path = config_path or default_config_path()
    if config is None:
        config = load_json(config_path)
    benchmark_dir = benchmark_dir or HERE
    bench_root = (
        bench_root or os.environ.get("SHOKO_BENCH_ROOT") or default_bench_root()
    )
    return Ctx(
        benchmark_dir=benchmark_dir,
        bench_root=bench_root,
        config=config,
        config_path=config_path,
        run=getattr(args, "run", None) or "unset",
        args=args,
        env_path=env_path,
        mode=mode,
    )


# ---------------------------------------------------------------------------
# prepare
# ---------------------------------------------------------------------------


def _open_lock(ctx):
    lock = Lock(ctx.lock_path())
    if not lock.acquire():
        return None
    return lock


def prepare_run(ctx):
    import shoko_pipeline as _pipeline  # local import: avoids an import cycle

    # Validate the mode group before anything touches the filesystem, so a
    # bad combine is a usage error (exit 2), not a precondition failure.  The
    # CLI parser checks the same thing; this covers direct/in-process callers.
    bad = prepare_usage_error(ctx.args)
    if bad:
        print("usage: shoko prepare: %s" % bad, file=sys.stderr)
        return EXIT_USAGE

    RunSpec = _pipeline.RunSpec
    rep = Reporter()
    tree = None
    staged = False  # tree renamed to <bench>/<run>
    git_bin = ctx.which("git")
    tar_bin = ctx.which("tar")
    lock = None
    p1 = None
    server_pin = None
    # Sources are cloned from GitHub to ~/.cache/shoko.
    cache_base = os.path.join(os.path.expanduser("~/.cache"), "shoko")
    webui_dir = ensure_clone(
        WEBUI_URL, os.path.join(cache_base, "Shoko-WebUI"), git_bin
    )
    server_dir = ensure_clone(
        SERVER_URL, os.path.join(cache_base, "ShokoServer"), git_bin
    )
    try:
        # --- P0 preconditions -------------------------------------------
        home = os.path.realpath(os.path.expanduser("~"))
        problem = bench_root_problem(ctx.bench_root, ctx.benchmark_dir, home, git_bin)
        if problem:
            rep.fail("precond-bench-root", problem)
        os.makedirs(ctx.bench_root, exist_ok=True)

        lock = _open_lock(ctx)
        if lock is None:
            print("FAIL precond-lock held by another process", file=sys.stderr)
            return EXIT_LOCKED

        if not RUN_NAME_RE.match(ctx.run or ""):
            rep.fail("precond-run-name", "invalid run name %r" % (ctx.run,))

        if (
            os.path.exists(ctx.run_dir())
            or os.path.exists(ctx.state_dir())
            or os.path.exists(ctx.views_dir())
        ):
            rep.fail("precond-run-absent", "%s already exists" % ctx.run_dir())

        server_pin = ctx.config.get("server_pin")

        base = ctx.config["base"]
        rc, out, _ = git_text(git_bin, "-C", webui_dir, "cat-file", "-t", base)
        if rc != 0 or out.strip() != "commit":
            rep.fail(
                "precond-base-commit",
                "base %s not a commit in %s" % (base, webui_dir),
            )

        if server_pin:
            rc, out, _ = git_text(
                git_bin, "-C", server_dir, "cat-file", "-t", server_pin
            )
            if rc != 0 or out.strip() != "commit":
                rep.fail(
                    "precond-server-commit",
                    "pin %s not a commit in %s" % (server_pin, server_dir),
                )

        # --- P0b stale Playwright transform caches -------------
        # Playwright compiles specs into `<os.tmpdir()>/playwright-transform-
        # cache-<uid>`. The harness's own copy lives under the run dir's
        # private TMPDIR and is gone before any pass runs, so any
        # matching entry directly under the shared temp dir is stale (a pre-fix
        # run's) or a concurrent process's — and a pass could read compiled
        # specs out of it. Best-effort: an entry that will
        # not go is a WARN, never a failure; nothing is recursive over the temp
        # dir itself and every non-matching entry is left alone.
        removed, unremovable = sweep_stale_transform_caches()
        if unremovable:
            rep.warn(
                "tmp-sweep",
                "removed %d stale playwright transform cache dir(s); "
                "could not remove: %s" % (removed, ", ".join(unremovable)),
            )
        elif removed:
            rep.ok(
                "tmp-sweep",
                "removed %d stale playwright transform cache dir(s)" % removed,
            )
        else:
            rep.ok("tmp-sweep", "nothing to remove")

        # --- P1 dev snapshot --------------------------------------------
        p1 = dev_snapshot(webui_dir, server_dir, git_bin)
        rep.ok(
            "dev-unchanged",
            "(P1) webui=%s server=%s" % (p1["webui"][:16], p1["server"][:16]),
        )

        # --- P2 snapshot the dev trees ----------------------------------
        webui_tar = git_archive(webui_dir, base, git_bin)
        server_tar = (
            git_archive(server_dir, server_pin, git_bin) if server_pin else None
        )
        server_archive_sha = sha256_bytes(server_tar) if server_tar else None

        tree = os.path.join(ctx.bench_root, ".tmp-%s-%s" % (ctx.run, os.getpid()))
        if os.path.exists(tree):
            shutil.rmtree(tree)
        os.makedirs(tree)
        extract_tar(webui_tar, os.path.join(tree, "Shoko-WebUI"), tar_bin)
        if server_tar:
            extract_tar(server_tar, os.path.join(tree, "ShokoServer"), tar_bin)

        # --- P3 history-free bench repo ---------------------------------
        webui_tree = os.path.join(tree, "Shoko-WebUI")
        branch = ctx.config.get("branch", "bench/shoko-logs")
        git_dir = os.path.join(webui_tree, ".git")
        # runner-owned GIT_DIR/GIT_INDEX_FILE: nothing ambient decides which
        # repo or index this touches.
        own = {"GIT_DIR": git_dir, "GIT_INDEX_FILE": os.path.join(git_dir, "index")}
        rc, _out, err = git_text(
            git_bin,
            "init",
            "-q",
            "-b",
            branch,
            "--template=" + empty_template_dir(),
            cwd=webui_tree,
        )
        if rc != 0:
            raise RuntimeError("git init failed: %s" % err)
        rc, _out, err = git_text(
            git_bin,
            "-c",
            "core.autocrlf=false",
            "-c",
            "core.safecrlf=false",
            "add",
            "-A",
            "-f",
            cwd=webui_tree,
            env_extra=own,
        )
        if rc != 0:
            raise RuntimeError("git add failed: %s" % err)
        rc, written_tree, err = git_text(
            git_bin, "write-tree", cwd=webui_tree, env_extra=own
        )
        written_tree = written_tree.strip()
        rc2, expected_tree, _ = git_text(
            git_bin, "-C", webui_dir, "rev-parse", base + "^{tree}"
        )
        expected_tree = expected_tree.strip()
        if rc != 0 or written_tree != expected_tree:
            rep.fail(
                "tree-equal", "built=%s expected=%s" % (written_tree, expected_tree)
            )
        rc, _out, err = git_text(
            git_bin,
            "-c",
            "user.name=shoko",
            "-c",
            "user.email=shoko@invalid",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-q",
            "-m",
            "bench base",
            cwd=webui_tree,
            env_extra=own,
        )
        if rc != 0:
            raise RuntimeError("git commit failed: %s" % err)
        # Task 1: the candidate repo's own history-free base.  `bench_commit`
        # (the *benchmarks repo* HEAD) is a different pin and is not a revision
        # in here; the export must diff against this one.
        rc, run_base_commit, err = git_text(
            git_bin, "rev-parse", "HEAD", cwd=webui_tree, env_extra=own
        )
        run_base_commit = run_base_commit.strip()
        if rc != 0 or not run_base_commit:
            raise RuntimeError("git rev-parse HEAD failed: %s" % err)
        rep.ok("tree-equal", expected_tree)

        # --- P4 bench repo hygiene --------------------------------------
        apply_checks(
            rep,
            check_bench_repo(webui_tree, branch, git_bin, expect_head=run_base_commit),
        )

        # --- P5 containment ---------------------------------------------
        apply_checks(rep, check_containment(tree, webui_tree, git_bin))

        # --- P6 reference diff ------------------------------------------
        ref_diff = os.path.join(ctx.benchmark_dir, "reference.diff")
        rc, _out, err = git_text(
            git_bin, "-C", webui_tree, "apply", "--check", ref_diff
        )
        if rc != 0:
            rep.fail(
                "ref-applies",
                err.strip().splitlines()[0]
                if err.strip()
                else "git apply --check failed",
            )
        rep.ok("ref-applies", "reference.diff applies to the bench tree")

        postimage = {}
        with open(ref_diff, "r", encoding="utf-8", errors="replace") as fh:
            ref_paths = diff_paths(fh.read())
        copy = os.path.join(ctx.bench_root, ".tmp-%s-ref-%s" % (ctx.run, os.getpid()))
        if os.path.exists(copy):
            shutil.rmtree(copy)
        shutil.copytree(webui_tree, copy, symlinks=True)
        try:
            rc, _out, err = git_text(git_bin, "-C", copy, "apply", ref_diff)
            if rc != 0:
                raise RuntimeError(
                    "failed to apply reference.diff to a scratch copy: %s" % err
                )
            for rel in ref_paths:
                p = os.path.join(copy, rel)
                if os.path.isfile(p):
                    postimage[rel] = sha256_file(p)
        finally:
            shutil.rmtree(copy, ignore_errors=True)

        # --- P7 server greps --------------------------------------------
        server_tree = os.path.join(tree, "ShokoServer")
        apply_checks(rep, check_server_greps(server_tree))

        # --- P9 install --------------------------------------------------
        pnpm = ctx.which("pnpm")
        if not pnpm:
            rep.fail("tree-clean-after-install", "pnpm not found on PATH")
        install_log = os.path.join(tree, "install.log")
        # Runner-owned store + copy import: an agent edit under
        # node_modules/<pkg> must not be able to corrupt the host's shared
        # pnpm store, which on a non-reflink fs is hardlinked.
        store_dir = os.path.join(ctx.bench_root, ".shoko-pnpm-store")
        os.makedirs(store_dir, exist_ok=True)
        penv = {
            k: v
            for k, v in os.environ.items()
            if k not in ("NPM_CONFIG_STORE_DIR", "npm_config_store_dir")
        }
        # husky's `prepare` script rewrites the repo's own core.hooksPath;
        # the bench repo config must stay exactly what P3 built, and no hook
        # may ever run on host git.
        penv["HUSKY"] = "0"
        penv["HUSKY_SKIP_INSTALL"] = "1"
        with open(install_log, "wb") as logfh:
            r = subprocess.run(
                [
                    pnpm,
                    "install",
                    "--frozen-lockfile",
                    "--package-import-method=copy",
                    "--store-dir",
                    store_dir,
                ],
                cwd=webui_tree,
                stdout=logfh,
                stderr=subprocess.STDOUT,
                env=penv,
                timeout=ctx.config.get("timeouts", {}).get("pass_s", 1800) or 1800,
            )
        if r.returncode != 0:
            rep.fail(
                "tree-clean-after-install",
                "pnpm install rc=%d (see install.log)" % r.returncode,
            )
        rc, out, _ = git_text(git_bin, "-C", webui_tree, "status", "--porcelain")
        if out.strip():
            rep.fail("tree-clean-after-install", out.strip().splitlines()[0])
        rep.ok("tree-clean-after-install", "clean after pnpm install")
        lockfile = os.path.join(webui_tree, "pnpm-lock.yaml")
        lockfile_sha = sha256_file(lockfile) if os.path.isfile(lockfile) else None

        # --- P10 endpoint health (endpoint mode only) -------------------
        # Host mode has no endpoint to poll — the model is served by
        # the host's own opencode -- so the check is recorded as skipped, never
        # as a silent pass.
        if is_host_mode(ctx.args):
            rep.ok("endpoint-health", "skipped (host mode: no --endpoint to poll)")
        else:
            health = endpoint_health_url(ctx)
            code = http_get_code(health)
            if code != 200:
                rep.fail("endpoint-health", "GET %s -> %s" % (health, code))
            rep.ok("endpoint-health", "GET %s -> 200" % health)

        # --- P11 move into place ----------------------------------------
        run_dir = ctx.run_dir()
        state_dir = ctx.state_dir()
        os.replace(tree, run_dir)
        tree = None
        staged = True
        os.makedirs(state_dir, exist_ok=True)
        os.makedirs(ctx.views_dir(), exist_ok=True)
        store = RunStore(state_dir)
        store.init()

        run_json = build_run_json(
            ctx,
            base,
            server_pin,
            server_archive_sha,
            lockfile_sha,
            postimage,
            dev_p1=p1,
            run_base_commit=run_base_commit,
            dev_webui=webui_dir,
            dev_server=server_dir,
        )
        dump_json(store.run_path, run_json)
        ctx.set_spec(RunSpec.from_file(store.run_path))

        store.write_state(store.new_state())

        # --- P12 dev unchanged ------------------------------------------
        p12 = dev_snapshot(webui_dir, server_dir, git_bin)
        problems = dev_unchanged_problems(p1, p12)
        if problems:
            rep.fail("dev-unchanged", "(P12) " + "; ".join(problems))
        rep.ok(
            "dev-unchanged",
            "(P12) webui=%s server=%s" % (p12["webui"][:16], p12["server"][:16]),
        )
        return EXIT_OK

    except Fail:
        _cleanup_failed(ctx, tree, staged)
        return EXIT_PRECOND
    except Exception as exc:  # noqa: BLE001
        import traceback

        traceback.print_exc()
        print("FAIL internal %r" % (exc,), file=sys.stderr)
        _cleanup_failed(ctx, tree, staged)
        return EXIT_INTERNAL
    finally:
        if lock is not None:
            lock.release()


def _cleanup_failed(ctx, tree, staged):
    # Nothing was built by this invocation: leave any pre-existing run alone
    # (a P0 precondition failure must not touch an existing <run>/).
    if tree is None and not staged:
        return
    stamp = time.strftime("%Y%m%dT%H%M%S")
    dest = "%s.failed-%s" % (ctx.run_dir(), stamp)
    n = 0
    while os.path.exists(dest):
        n += 1
        dest = "%s.failed-%s-%d" % (ctx.run_dir(), stamp, n)
    moved = False
    for src in (tree, ctx.run_dir() if staged else None):
        if src and os.path.isdir(src):
            os.makedirs(dest, exist_ok=True)
            base = os.path.basename(src)
            target = os.path.join(dest, base if src == tree else "run")
            shutil.move(src, target)
            moved = True
    if moved or os.path.isdir(ctx.state_dir()):
        os.makedirs(dest, exist_ok=True)
        if os.path.isdir(ctx.state_dir()):
            shutil.move(ctx.state_dir(), os.path.join(dest, "state"))
        if os.path.isdir(ctx.views_dir()):
            shutil.move(ctx.views_dir(), os.path.join(dest, "views"))
    else:
        shutil.rmtree(dest, ignore_errors=True)


def endpoint_health_url(ctx, endpoint=None):
    if endpoint is None:
        try:
            endpoint = ctx.spec.endpoint
        except Exception:  # noqa: BLE001 - pre-prepare: fall back to the args
            endpoint = getattr(ctx.args, "endpoint", None)
    return "http://%s/v1/models" % endpoint


def http_get_code(url, timeout=15):
    try:
        resp = urllib.request.urlopen(url, timeout=timeout)
        return resp.getcode()
    except urllib.error.HTTPError as exc:
        return exc.code
    except Exception:  # noqa: BLE001
        return None


def runner_digest():
    """Hash the trust boundary: the runner *and* the process helpers."""
    h = hashlib.sha256()
    for rel in ("shoko.py", "shoko_proc.py"):
        _hash_bytes(h, rel, _read_bytes(os.path.join(HERE, rel)))
    return h.hexdigest()


def split_model(value):
    """Parse `provider/model#variant` (provider and variant both optional).

    Returns `{"provider","id","variant"}`; `value` is returned as the id when
    it carries no provider, and a `None` value yields all-None.  This is the
    single parser for every role's `-m`, so a cloud id like
    `opencode-go/muse-spark-1.3-contributor#xhigh` keeps its provider.
    """
    if value is None:
        return {"provider": None, "id": None, "variant": None}
    ident, _, variant = value.partition("#")
    provider = None
    if "/" in ident:
        provider, _, ident = ident.partition("/")
    return {
        "provider": provider or None,
        "id": ident or None,
        "variant": variant or None,
    }


def build_run_json(
    ctx,
    base,
    server_pin,
    server_archive_sha,
    lockfile_sha,
    postimage,
    dev_p1=None,
    run_base_commit=None,
    dev_webui=None,
    dev_server=None,
):
    inputs = {}
    for rel in (
        "prompt.md",
        "rubric.md",
        "reference.diff",
        "harness/README.md",
        "harness/lines.json",
        "prompts/judge.txt",
        "prompts/reviewer.txt",
    ):
        p = os.path.join(ctx.benchmark_dir, rel)
        inputs[rel] = sha256_file(p) if os.path.isfile(p) else None

    git_bin = ctx.which("git")
    rc, head, _ = git_text(git_bin, "-C", ctx.benchmark_dir, "rev-parse", "HEAD")
    rc2, tree_sha, _ = git_text(
        git_bin, "-C", ctx.benchmark_dir, "rev-parse", "HEAD^{tree}"
    )
    opencode_bin = ctx.which("opencode")
    rc3, oc_ver, _ = (
        proc_text([opencode_bin, "--version"]) if opencode_bin else (1, "", "")
    )

    model = split_model(ctx.args.model)
    # The mode and the effective budget. In host mode there is no endpoint
    # and no provider override, so `provider_id`/`endpoint`/`ctx`/`out_cap` are
    # null -- the run.json must not imply a budget that was never applied.
    host = is_host_mode(ctx.args)
    run_mode = "host" if host else "endpoint"
    provider_id = None if host else "shoko"
    # What the run's children are given: the launcher environment with every
    # OPENCODE_* key scrubbed (spawn_host does the same), and the config dir
    # opencode will resolve from that scrubbed environment -- not a guess.
    child_base, scrubbed_opencode = shoko_proc.child_env()
    config_dir = shoko_proc.config_dir_from_env(child_base)
    return {
        "schema": 1,
        "run": ctx.run,
        "mode": ctx.mode,
        "created": now_iso(),
        "config_sha256": sha256_file(ctx.config_path),
        "runner_sha256": runner_digest(),
        "model": model,
        "judge": split_model(ctx.args.judge),
        "reviewer": split_model(ctx.args.reviewer),
        "run_mode": run_mode,
        "provider_id": provider_id,
        "endpoint": None if host else ctx.args.endpoint,
        "dev": {
            # The developer's source checkouts the run was built from (the
            # cache clones in ~/.cache/shoko), not the run tree.
            "webui": os.path.abspath(dev_webui) if dev_webui else None,
            "server": os.path.abspath(dev_server) if dev_server else None,
        },
        "level": model["variant"],
        "ctx": None if host else ctx.args.ctx,
        "out_cap": None if host else ctx.args.out_cap,
        "harness": {
            "port": ctx.config.get("harness", {}).get("port", 3100),
            "expected_total": ctx.config.get("harness", {}).get("expected_total"),
        },
        "opencode": {
            "path": opencode_bin,
            "version": oc_ver.strip(),
            "sha256": sha256_file(opencode_bin) if opencode_bin else None,
        },
        "child_env": {
            "scrubbed_opencode_keys": scrubbed_opencode,
            "opencode_config_dir": config_dir,
        },
        "tools": {
            "node": ctx.which("node"),
            "pnpm": ctx.which("pnpm"),
        },
        "revision": (head.strip() if rc == 0 else None),
        "revision_tree": (tree_sha.strip() if rc2 == 0 else None),
        "inputs_sha256": inputs,
        "dev_snapshot_p1": dev_p1 or {},
        "pins": {
            "base": base,
            "server_pin": server_pin,
            "server_archive_sha256": server_archive_sha,
            "lockfile_sha256": lockfile_sha,
            "bench_commit": (head.strip() if rc == 0 else None),
            "bench_tree": (tree_sha.strip() if rc2 == 0 else None),
            # Task 1: the candidate repo's own history-free base.  `bench_commit`
            # is the benchmarks repo HEAD and is NOT a revision in the candidate
            # repo, so the export diffs against this one.
            "run_base_commit": run_base_commit,
        },
        "reference_postimage_sha256": postimage,
        "session_id": None,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def is_host_mode(args):
    """`--endpoint` absent selects host mode (the host's own opencode serves
    the model)."""
    return not getattr(args, "endpoint", None)


def prepare_usage_error(args):
    """Cross-field usage rules for `prepare`, or None when argv is legal.

    `--endpoint` selects one of two mutually exclusive shapes:

    * **endpoint mode** (`--endpoint` given) keeps today's contract: a bare
      `--model <id>` (provider `shoko` hardcoded) and `--ctx`/`--out-cap`
      required (they reach opencode only through the endpoint override's `limit.*`).
    * **host mode** (`--endpoint` absent) takes `--model [provider/]id[#<level>]`
      -- the provider is required -- and forbids `--ctx`/`--out-cap`, which would be
      silently inert without the override.

    Returns the message; the parser reports it as a usage error, exit 2.
    `prepare_run` re-checks it so direct/in-process callers get the same exit code.
    """
    model = split_model(args.model)
    endpoint = getattr(args, "endpoint", None)
    if endpoint:
        if model["provider"]:
            return (
                "--model %s carries a provider but --endpoint is set: endpoint "
                "mode takes a bare id" % args.model
            )
        if args.ctx is None:
            return "--ctx is required with --endpoint"
        if args.out_cap is None:
            return "--out-cap is required with --endpoint"
    else:
        if not model["provider"]:
            return (
                "--model %s has no provider and --endpoint is absent: host mode "
                "takes --model [provider/]id" % args.model
            )
        if args.ctx is not None:
            return (
                "--ctx needs --endpoint: the budget reaches opencode only through "
                "the endpoint override, so it would be inert in host mode"
            )
        if args.out_cap is not None:
            return (
                "--out-cap needs --endpoint: the budget reaches opencode only "
                "through the endpoint override, so it would be inert in host mode"
            )
    return None


def add_prepare_args(p):
    p.add_argument("run")
    p.add_argument(
        "--model",
        required=True,
        help="model to bench; host mode wants [provider/]id, plus an optional "
        "#<level> reasoning-level suffix (endpoint mode takes a bare id)",
    )
    p.add_argument("--judge", required=True)
    p.add_argument("--reviewer", required=True)
    # `--endpoint` selects the mode, so its group is not `required` at the
    # argparse layer -- `prepare_usage_error` enforces the shape (endpoint mode
    # keeps today's contract, host mode forbids the group) and reports a
    # violation as a usage error, exit 2.
    p.add_argument("--endpoint")
    p.add_argument("--ctx", type=int)
    p.add_argument("--out-cap", type=int)


class _ShokoParser(argparse.ArgumentParser):
    """Top-level parser that validates `prepare`'s mode group after parsing.

    The rules span several flags, so they cannot live on a single `type=`
    callback; running them here keeps `build_parser().parse_args` the one seam
    that turns a bad combine into a usage error (exit 2).
    """

    def parse_args(self, args=None, namespace=None):
        ns = super().parse_args(args, namespace)
        if getattr(ns, "cmd", None) == "prepare":
            bad = prepare_usage_error(ns)
            if bad:
                self.error(bad)
        return ns


def build_parser():
    ap = _ShokoParser(
        prog="shoko", description="Shoko log-viewer benchmark runner (M1)"
    )
    # The subparsers stay vanilla: `_ShokoParser.parse_args` validates the
    # top-level namespace, which is only complete after the subparser has run.
    sub = ap.add_subparsers(dest="cmd", parser_class=argparse.ArgumentParser)

    add_prepare_args(sub.add_parser("prepare"))

    p = sub.add_parser("run")
    p.add_argument("run")
    p.add_argument(
        "--no-trace",
        dest="trace_streams",
        action="store_false",
        default=True,
        help="do not print the agent's phase trace (reasoning / text / tool "
        "calls) to this run's output while a role turn is in flight",
    )

    return ap


def dispatch(ctx, args):
    if args.cmd == "prepare":
        return prepare_run(ctx)
    if args.cmd == "run":
        import shoko_pipeline as pipeline

        return pipeline.run_pipeline(ctx)
    return EXIT_USAGE


def _record_crash(ctx, etype, code, detail, trace=None):
    """Best-effort durable note of a failure that escaped a command.

    Written into the run's state.json so an operator can see why a run
    stopped; a secondary failure here is swallowed - it must never mask the
    original one."""
    try:
        state_dir = ctx.state_dir()
        if not os.path.isdir(state_dir):
            return
        store = RunStore(state_dir)
        state = store.read_state() or store.new_state()
        state["phase"] = {"halt": "halted", "internal": "internal"}.get(etype, "failed")
        failure = {"code": code, "detail": detail}
        if trace:
            failure["traceback"] = trace
        state["failure"] = failure
        store.write_state(state)
    except Exception:  # noqa: BLE001 - never mask the original failure
        pass


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    # Progress lines must be visible while a long run is in flight: with stdout
    # redirected to a file Python block-buffers, so an operator tailing the log
    # sees nothing for the whole trajectory.
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:  # noqa: BLE001 - never fail a run over a display tweak
        pass
    ap = build_parser()
    args = ap.parse_args(argv)
    if not args.cmd:
        ap.print_help()
        return EXIT_USAGE

    ctx = make_ctx(args)
    try:
        return dispatch(ctx, args)
    except Fail as exc:
        print("FAIL %s: %s" % (exc.cid, exc.detail), file=sys.stderr)
        _record_crash(ctx, "fail", exc.cid, str(exc.detail or ""))
        return EXIT_PRECOND
    except KeyboardInterrupt:
        _record_crash(ctx, "fail", "interrupted", "KeyboardInterrupt")
        return EXIT_INTERNAL
    except Exception as exc:  # noqa: BLE001 - the runner must never die silently
        import traceback

        tb = traceback.format_exc()
        print(tb, file=sys.stderr)
        _record_crash(
            ctx, "internal", "H-INTERNAL", "%s: %s" % (type(exc).__name__, exc), tb
        )
        return EXIT_INTERNAL


if __name__ == "__main__":
    sys.exit(main())
