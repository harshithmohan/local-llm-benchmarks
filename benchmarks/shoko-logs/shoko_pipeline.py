#!/usr/bin/env python3
"""shoko pipeline — the stage loop: implement → normalize → gates → harness → judge → review."""

import hashlib
import json
import os
import re
import shutil
import sys
import time

import shoko as S, shoko_proc as proc, shoko_stream as stream

JUDGE_FILE = os.path.join(S.HERE, "prompts", "judge.txt")
REVIEW_FILE = os.path.join(S.HERE, "prompts", "reviewer.txt")
EXPECTED_AGENT = "build"
DEFAULT_ROLE_PERMISSIONS = ("edit", "write", "read", "shell", "glob", "grep")


def read_text(p):
    with open(p, "r", encoding="utf-8") as fh:
        return fh.read()


def say(scope, event, detail=""):
    """One progress line for the operator: time, phase, event, detail.

    Printed and flushed immediately so `shoko.py run > run.log` shows a live
    log instead of one buffered burst at exit; a closed log never kills a run.
    """
    try:
        print(
            "%s  %-9s %-7s %s" % (time.strftime("%H:%M:%S"), scope, event, detail),
            flush=True,
        )
    except (BrokenPipeError, ValueError, OSError):
        pass


def elapsed(t0):
    return "%.0fs" % (time.monotonic() - t0)


def size(text):
    n = len(text.encode("utf-8")) if isinstance(text, str) else 0
    return "%.1fK" % (n / 1024.0)


def stat_line(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            lines = [x.strip() for x in fh.read().splitlines() if x.strip()]
    except (OSError, TypeError):
        return "(no diffstat)"
    return lines[-1] if lines else "(no diffstat)"


def fill(template, **kw):
    """Substitute `{name}` placeholders, leaving every other brace literal."""
    out = template
    for k, v in kw.items():
        out = out.replace("{%s}" % k, str(v))
    return out


# The sanitized report writes one bullet per failed test:
#   - **<spec file basename> › <test title>** — <symptom>
# while lines.json keys every test as `<spec file name> > <test title>`.
BULLET_RE = re.compile(r"^\s*-\s*\*\*(.+?)\*\*", re.M)
BULLET_KEY_SEP = "\u203a"


def failure_keys(text):
    """Every failure bullet in a sanitized report, in its lines.json key form."""
    keys = []
    for m in BULLET_RE.finditer(text or ""):
        raw = m.group(1)
        spec, sep, title = raw.partition(BULLET_KEY_SEP)
        if not sep:
            keys.append(raw.strip())
            continue
        keys.append("%s > %s" % (spec.strip(), title.strip()))
    return keys


def lines_tests(benchmark_dir):
    path = os.path.join(benchmark_dir, "harness", "lines.json")
    if not os.path.isfile(path):
        return {}
    return S.load_json(path).get("tests") or {}


def unmapped_keys(text, benchmark_dir):
    """Failure bullets whose key lines.json does not define."""
    known = lines_tests(benchmark_dir)
    return [k for k in failure_keys(text) if k not in known]


class RunSpec:
    def __init__(self, data, path=None):
        self.data = data
        self.path = path

    @classmethod
    def from_file(cls, path):
        if not os.path.isfile(path):
            raise S.Fail("no-run-json", path)
        return cls(S.load_json(path), path)

    def get(self, *keys, default=None):
        cur = self.data
        for k in keys:
            if not isinstance(cur, dict) or k not in cur:
                return default
            cur = cur[k]
        return cur

    @property
    def run(self):
        return self.data.get("run")

    @property
    def model(self):
        return self.data.get("model") or {}

    @property
    def model_id(self):
        m = self.model
        ident = m.get("id")
        return "%s#%s" % (ident, m["variant"]) if m.get("variant") else ident

    @property
    def run_mode(self):
        return self.data.get("run_mode") or "endpoint"

    @property
    def is_host_mode(self):
        return self.run_mode == "host"

    @property
    def provider_id(self):
        if self.is_host_mode:
            return self.model.get("provider")
        return self.data.get("provider_id") or "shoko"

    @property
    def endpoint(self):
        return self.data.get("endpoint")

    @property
    def ctx_limit(self):
        return self.data.get("ctx")

    @property
    def out_cap(self):
        return self.data.get("out_cap")

    @property
    def harness(self):
        return self.data.get("harness") or {}

    @property
    def pins(self):
        return self.data.get("pins") or {}

    def role_model(self, role):
        if role == "impl":
            provider = self.provider_id
            ident = self.model_id
            return "%s/%s" % (provider, ident) if provider else ident
        d = self.data.get(role) or {}
        ident = d.get("id")
        provider = d.get("provider")
        if provider:
            ident = "%s/%s" % (provider, ident)
        return "%s#%s" % (ident, d["variant"]) if d.get("variant") else ident

    def session_id(self):
        return self.data.get("session_id")


def tree_digest(git, worktree):
    h = hashlib.sha256()
    rc, head, _ = git.text("rev-parse", "HEAD")
    h.update((head.strip() if rc == 0 else "").encode())
    h.update(b"\0")
    rc, difftext, _ = git.text(
        "diff", "--binary", "--no-ext-diff", "--no-textconv", "HEAD"
    )
    h.update(difftext.encode("utf-8", "replace"))
    h.update(b"\0")
    rc, others, _ = git.text("ls-files", "--others", "--exclude-standard")
    for rel in sorted(x for x in others.splitlines() if x):
        h.update(rel.encode())
        h.update(b"\0")
        p = os.path.join(worktree, rel)
        try:
            with open(p, "rb") as fh:
                h.update(hashlib.sha256(fh.read()).hexdigest().encode())
        except OSError:
            h.update(b"-")
    return h.hexdigest()


class TreeSnapshot:
    def __init__(self, git, worktree):
        self.git = git
        self.worktree = worktree
        self.digest = None

    def take(self):
        self.digest = tree_digest(self.git, self.worktree)
        return self.digest

    def changed(self):
        if self.digest is None:
            return False
        return tree_digest(self.git, self.worktree) != self.digest


class HostGit:
    def __init__(self, git_bin, worktree):
        self.git = git_bin
        self.worktree = worktree

    def text(self, *args, timeout=120):
        return S.git_text(self.git, "-C", self.worktree, *args, timeout=timeout)

    def bytes(self, *args, timeout=120):
        argv = [self.git] + S.GIT_HARDEN + ["-C", self.worktree] + list(args)
        return S.proc(argv, env=S.git_env(), timeout=timeout)

    def run(self, *args, timeout=120):
        argv = [self.git] + S.GIT_HARDEN + ["-C", self.worktree] + list(args)
        return S.proc(argv, env=S.git_env(), timeout=timeout)


class TurnResult:
    def __init__(self, exit_code, parsed, stdout_path, timed_out=False):
        self.exit_code = exit_code
        self.parsed = parsed
        self.stdout_path = stdout_path
        self.timed_out = timed_out
        self.session_id = parsed.session_id if parsed else None
        self._touched = False


class PassResult(TurnResult):
    def __init__(self, *a, **kw):
        self.artifact_path = kw.pop("artifact_path", None)
        self.artifact_text = kw.pop("artifact_text", None)
        super().__init__(*a, **kw)


class RealExecutor:
    EXPORT_TIMEOUT_S = 300
    EXPORT_MAX_BYTES = 64 * 1024 * 1024
    VIEW_TREE_SKIP = ("node_modules", ".git")

    def __init__(self, ctx, spec, config):
        self.ctx = ctx
        self.spec = spec
        self.config = config
        self.run_dir = ctx.run_dir()
        self.state_dir = ctx.state_dir()
        self.views_dir = ctx.views_dir()
        self.webui = os.path.join(self.run_dir, "Shoko-WebUI")
        self.git = HostGit(ctx.which("git"), self.webui)
        self.log_dir = os.path.join(self.state_dir, "streams")
        os.makedirs(self.log_dir, exist_ok=True)

    def stream_path(self, role, stage, attempt):
        return os.path.join(self.log_dir, "%s-s%d-a%d.jsonl" % (role, stage, attempt))

    def endpoint_base_url(self):
        return "http://%s/v1" % self.spec.endpoint

    def role_permissions(self, role):
        cfg = self.config.get("permissions") or {}
        group = "implement" if role == "implement" else "pass"
        actions = cfg.get(group)
        if actions is None:
            actions = cfg.get(role)
            if actions is None:
                actions = DEFAULT_ROLE_PERMISSIONS
        return list(actions)

    def role_config_content(self, role):
        perms = self.role_permissions(role)
        if role == "implement" and not self.spec.is_host_mode:
            return proc.provider_json(
                self.spec.provider_id,
                self.spec.model_id,
                self.endpoint_base_url(),
                ctx_limit=self.spec.ctx_limit,
                out_cap=self.spec.out_cap,
                permissions=perms,
            )
        return proc.provider_json(None, None, None, permissions=perms)

    def _opencode_argv(self, model, text, session_id=None, agent=None):
        argv = [
            "opencode",
            "run",
            "--standalone",
            "--agent",
            agent or EXPECTED_AGENT,
            "--thinking",
            "--format",
            "json",
            "-m",
            model,
        ]
        if session_id:
            argv += ["--session", session_id]
        argv.append(text)
        return argv

    def impl_turn(self, *, text, session_id, attempt, stage, kind):
        timeout = (self.config.get("timeouts") or {}).get("impl_turn_s", 7200)
        stdout_path = os.path.join(
            self.log_dir, "impl-s%d-a%d.jsonl" % (stage, attempt)
        )
        before = TreeSnapshot(self.git, self.webui)
        before.take()
        r = proc.spawn_host(
            role="implement",
            inner=self._opencode_argv(self.spec.role_model("impl"), text, session_id),
            cwd=self.run_dir,
            stdout_path=stdout_path,
            timeout=timeout,
            env_extra={
                "OPENCODE_CONFIG_CONTENT": self.role_config_content("implement")
            },
            trace=bool(getattr(self.ctx.args, "trace_streams", True)),
            trace_prefix="s%d impl" % stage,
            trace_out=sys.stdout,
            trace_root=self.run_dir,
        )
        parsed = stream.parse_stream(r.read())
        res = TurnResult(r.exit_code, parsed, stdout_path, r.timed_out)
        res.kind = kind
        res._touched = before.changed()
        return res

    def _readonly_tree(self, src, dst):
        shutil.copytree(
            src, dst, symlinks=True, ignore=shutil.ignore_patterns(*self.VIEW_TREE_SKIP)
        )
        for dirpath, dirnames, filenames in os.walk(dst):
            for name in filenames:
                p = os.path.join(dirpath, name)
                if not os.path.islink(p):
                    os.chmod(p, 0o444)
            for name in dirnames:
                p = os.path.join(dirpath, name)
                if not os.path.islink(p):
                    os.chmod(p, 0o555)
        os.chmod(dst, 0o555)

    def _pass_view(self, role, stage, attempt, files):
        view = os.path.join(self.views_dir, "%s-s%d-a%d" % (role, stage, attempt))
        if os.path.lexists(view):
            shutil.rmtree(view, ignore_errors=True)
        os.makedirs(view, exist_ok=True)
        for name, src in files.items():
            if src and os.path.isfile(src):
                shutil.copy2(src, os.path.join(view, name))
        for src_name, dst_name in (
            ("patch-s%d.diff" % stage, "patch-s%d.diff" % stage),
            ("stat-s%d.txt" % stage, "stat-s%d.txt" % stage),
            ("gates-s%d.json" % stage, "gates.json"),
            ("harness-s%d.json" % stage, "harness.json"),
        ):
            src = os.path.join(self.run_dir, src_name)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(view, dst_name))
        tree = os.path.join(view, "Shoko-WebUI")
        if os.path.isdir(self.webui) and not os.path.lexists(tree):
            self._readonly_tree(self.webui, tree)
        return view

    def pass_turn(self, *, role, stage, attempt, prompt_text, files, artifact_name):
        timeout = (self.config.get("timeouts") or {}).get("pass_s", 1800)
        view = self._pass_view(role, stage, attempt, files)
        tree = os.path.join(view, "Shoko-WebUI")
        stdout_path = self.stream_path(role, stage, attempt)
        try:
            r = proc.spawn_host(
                role=role,
                cwd=view,
                inner=self._opencode_argv(self.spec.role_model(role), prompt_text),
                stdout_path=stdout_path,
                timeout=timeout,
                env_extra={"OPENCODE_CONFIG_CONTENT": self.role_config_content(role)},
            )
        finally:
            # The view's tree is copied read-only so the pass cannot edit the
            # graded checkout; make it writable again so the view can be removed.
            if os.path.isdir(tree):
                for dirpath, dirnames, _ in os.walk(tree):
                    for name in dirnames:
                        p = os.path.join(dirpath, name)
                        if not os.path.islink(p):
                            os.chmod(p, 0o755)
                os.chmod(tree, 0o755)
        parsed = stream.parse_stream(r.read())
        art = os.path.join(view, artifact_name)
        text = read_text(art) if os.path.isfile(art) else None
        res = PassResult(
            r.exit_code,
            parsed,
            stdout_path,
            r.timed_out,
            artifact_path=art if text is not None else None,
            artifact_text=text,
        )
        res.view = view
        return res

    def normalize(self, *, stage, timeout=None):
        cfg = [["pnpm", "dprint:fix"], ["pnpm", "oxlint:fix"]]
        timeout = timeout or 900
        results = []
        for cmd in cfg:
            r = S.proc(list(cmd), cwd=self.webui, timeout=timeout)
            results.append(
                {
                    "cmd": list(cmd),
                    "exit": r.returncode,
                    "tail": r.stdout.decode("utf-8", "replace")[-2000:],
                }
            )
        return results

    def gates(self, *, stage, timeout=None):
        cfg = [["pnpm", "tscheck"], ["pnpm", "lint"], ["pnpm", "build"]]
        timeout = timeout or 900
        results = {}
        for cmd in cfg:
            name = cmd[-1].split(":")[-1]
            try:
                r = S.proc(list(cmd), cwd=self.webui, timeout=timeout)
                code = r.returncode
                tail = r.stdout.decode("utf-8", "replace")[-4000:]
            except Exception as exc:
                code = None
                tail = "timeout: %s" % exc
            results[name] = {"cmd": list(cmd), "exit": code, "tail": tail}
        return results

    def export(self, *, stage):
        g = self.git
        g.run("add", "-A", timeout=300)
        base = self.spec.pins.get("run_base_commit")
        if not base:
            g.run("reset", "-q", timeout=120)
            return {
                "patch": None,
                "stat": None,
                "empty": None,
                "base": None,
                "error": "run.json has no pins.run_base_commit",
            }
        try:
            r = g.bytes("diff", "--cached", "--no-ext-diff", base, timeout=300)
            r2 = g.bytes(
                "diff", "--cached", "--no-ext-diff", "--stat", base, timeout=300
            )
        finally:
            g.run("reset", "-q", timeout=120)
        if r.returncode != 0 or r2.returncode != 0:
            msg = (r.stderr or r2.stderr or b"").decode("utf-8", "replace").strip()
            return {
                "patch": None,
                "stat": None,
                "empty": None,
                "base": base,
                "error": msg or "git diff exit %s" % r.returncode,
            }
        patch, stat = r.stdout, r2.stdout
        p_patch = os.path.join(self.run_dir, "patch-s%d.diff" % stage)
        p_stat = os.path.join(self.run_dir, "stat-s%d.txt" % stage)
        with open(p_patch, "wb") as fh:
            fh.write(patch)
        with open(p_stat, "wb") as fh:
            fh.write(stat)
        return {"patch": p_patch, "stat": p_stat, "empty": len(patch) == 0}

    def harness(self, *, stage):
        hcfg = self.spec.harness
        port = hcfg.get("port", 3100)
        timeout = (self.config.get("harness") or {}).get("timeout_s", 1200)
        report = os.path.join(self.run_dir, "harness-s%d.report.md" % stage)
        log = os.path.join(self.run_dir, "harness-s%d.log" % stage)
        tmpdir = os.path.join(self.run_dir, ".harness-tmp-s%d" % stage)
        shutil.rmtree(tmpdir, ignore_errors=True)
        os.makedirs(tmpdir, exist_ok=True)
        env = dict(os.environ)
        env["SHOKO_WEBUI_DIR"] = self.webui
        env["HARNESS_REPORT"] = report
        env["HARNESS_PORT"] = str(port)
        env["TMPDIR"] = tmpdir
        script = os.path.join(self.ctx.benchmark_dir, "harness", "run.sh")
        argv = ["/bin/sh", script]
        try:
            r = proc.spawn_host(
                role="harness",
                cwd=os.path.dirname(script),
                inner=argv,
                stdout_path=log,
                timeout=timeout,
                env_extra=env,
                merge_stderr=True,
            )
            code = None if r.timed_out else r.exit_code
            text = read_text(report) if os.path.isfile(report) else ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
        # The sanitized report opens with `Result: <passed>/<total> passed, ...`.
        m = re.search(r"Result:\s*(\d+)/(\d+) passed", text)
        passed, total = (int(m.group(1)), int(m.group(2))) if m else (None, None)
        return {
            "exit": code,
            "timed_out": r.timed_out,
            "report": report,
            "text": text,
            "log": log,
            "passed": passed,
            "total": total,
            "unmapped": unmapped_keys(text, self.ctx.benchmark_dir),
        }


class Pipeline:
    def __init__(self, ctx, spec, config, executor):
        self.ctx = ctx
        self.spec = spec
        self.config = config
        self.executor = executor
        self.run_dir = ctx.run_dir()
        self.state_dir = ctx.state_dir()

    def _is_green(self, harness, gates):
        if harness.get("exit") != 0 or harness.get("timed_out"):
            return False
        for g in (gates or {}).values():
            if g.get("exit") != 0:
                return False
        # Exit 0 alone is not a full pass: the report carries its own totals,
        # and the suite size is pinned in the config. A suite that loses tests
        # (a spec file that fails to load, say) reports a smaller total and is
        # not green, and a report that states no totals cannot be shown green.
        passed, total = harness.get("passed"), harness.get("total")
        if passed is None or total is None or passed != total:
            return False
        expected = (self.config.get("harness") or {}).get("expected_total")
        if expected is not None and (total != expected or passed != expected):
            return False
        return True

    def _pass(self, *, role, stage, prompt_text, files, artifact_name, attempts=2):
        """Run a judge/reviewer pass, requiring the artifact on disk.

        A pass's exit status is not trusted: what matters is that the artifact
        landed. A pass that produced nothing is re-run (its runtime is minutes,
        not the implementation's hours); if it still produces nothing, the run
        stops rather than grading against a missing sheet."""
        for attempt in range(1, attempts + 1):
            res = self.executor.pass_turn(
                role=role,
                stage=stage,
                attempt=attempt,
                prompt_text=prompt_text,
                files=files,
                artifact_name=artifact_name,
            )
            if res.artifact_text is not None:
                return res
            say(
                "s%d" % stage,
                role,
                "attempt %d produced no %s" % (attempt, artifact_name),
            )
        return None

    def run(self):
        ex = self.executor
        prompt = read_text(os.path.join(self.ctx.benchmark_dir, "prompt.md"))
        judge_base = (
            read_text(JUDGE_FILE)
            if os.path.isfile(JUDGE_FILE)
            else "judge stage {stage}"
        )
        review_base = (
            read_text(REVIEW_FILE)
            if os.path.isfile(REVIEW_FILE)
            else "review stage {stage}"
        )
        session_id = None
        last_review = ""
        say(
            "run",
            "start",
            "model=%s endpoint=%s ctx=%s out_cap=%s"
            % (
                self.spec.role_model("impl"),
                self.spec.endpoint,
                self.spec.ctx_limit,
                self.spec.out_cap,
            ),
        )
        for stage in range(3):
            if stage == 0:
                text = prompt
            else:
                text = (
                    prompt
                    + "\n\n# Repair — stage %d, address the reviewer notes below:\n"
                    % stage
                    + last_review
                )
            label = "s%d" % stage
            kind = "initial" if stage == 0 else "repair"
            say(label, "impl", "start kind=%s attempt=1" % kind)
            t0 = time.monotonic()
            res = ex.impl_turn(
                text=text,
                session_id=session_id,
                attempt=1,
                stage=stage,
                kind=kind,
            )
            session_id = res.session_id or session_id
            say(
                label,
                "impl",
                "end finish=%s exit=%s touched=%s %s"
                % (
                    res.parsed.finish if res.parsed else None,
                    res.exit_code,
                    getattr(res, "_touched", False),
                    elapsed(t0),
                ),
            )
            say(label, "normalize", "start")
            norm = ex.normalize(stage=stage)
            nbad = [r for r in norm if r.get("exit") != 0]
            say(
                label,
                "normalize",
                "%d/%d ok%s"
                % (
                    len(norm) - len(nbad),
                    len(norm),
                    ""
                    if not nbad
                    else " failed=" + ",".join(r["cmd"][-1] for r in nbad),
                ),
            )
            say(label, "gates", "start")
            gates = ex.gates(stage=stage)
            with open(os.path.join(self.run_dir, "gates-s%d.json" % stage), "w") as fh:
                json.dump(gates, fh, indent=2)
            bad = [n for n, r in gates.items() if r.get("exit") != 0]
            say(
                label,
                "gates",
                "%s %d/%d %s"
                % (
                    "fail" if bad else "pass",
                    len(gates) - len(bad),
                    len(gates),
                    " ".join(bad or list(gates)),
                ),
            )
            exp = ex.export(stage=stage)
            if exp.get("error"):
                say(label, "export", "error %s" % str(exp["error"]).splitlines()[0])
            elif exp.get("empty"):
                say(label, "export", "empty patch vs run base")
            else:
                say(
                    label,
                    "export",
                    "patch-s%d.diff %s" % (stage, stat_line(exp.get("stat"))),
                )
            say(label, "harness", "start")
            h = ex.harness(stage=stage)
            if h.get("passed") is None:
                say(
                    label,
                    "harness",
                    "no result exit=%s%s"
                    % (h.get("exit"), " timeout" if h.get("timed_out") else ""),
                )
            else:
                say(label, "harness", "%s/%s passed" % (h["passed"], h["total"]))
            with open(
                os.path.join(self.run_dir, "harness-s%d.json" % stage), "w"
            ) as fh:
                json.dump(
                    {
                        "exit": h["exit"],
                        "passed": h.get("passed"),
                        "total": h.get("total"),
                        "text": h["text"][:4000],
                    },
                    fh,
                )
            if h.get("unmapped"):
                # A report whose failure bullets have no lines.json key cannot be
                # placed against the rubric, so the run stops before it pays for
                # a judge pass it could not grade. A green report carries no
                # bullets and never trips this.
                raise S.Fail(
                    "harness-report-unmapped",
                    "%d failure(s) not keyed in harness/lines.json: %s"
                    % (len(h["unmapped"]), "; ".join(h["unmapped"])),
                )
            say(label, "judge", "start")
            judge_prompt = fill(
                judge_base,
                run=self.spec.run,
                stage=stage,
                artifact="score-s%d.md" % stage,
            )
            jfiles = {
                "prompt.md": os.path.join(self.ctx.benchmark_dir, "prompt.md"),
                "rubric.md": os.path.join(self.ctx.benchmark_dir, "rubric.md"),
            }
            jres = self._pass(
                role="judge",
                stage=stage,
                prompt_text=judge_prompt,
                files=jfiles,
                artifact_name="score-s%d.md" % stage,
            )
            if jres is None:
                say(label, "judge", "no score sheet; stopping")
                return S.EXIT_INTERNAL
            score_txt = jres.artifact_text
            say(label, "judge", "end score-s%d.md %s" % (stage, size(score_txt)))
            open(os.path.join(self.run_dir, "score-s%d.md" % stage), "w").write(
                score_txt
            )
            green = self._is_green(h, gates)
            if green or stage == 2:
                harness_text = h["text"] or ""
                with open(os.path.join(self.run_dir, "score.md"), "w") as fh:
                    fh.write(score_txt + "\n\n" + harness_text[:4000])
                if green:
                    say(label, "verdict", "green; score.md written")
                    return S.EXIT_OK
                say(label, "verdict", "not converged; score.md written")
                return S.EXIT_HALTED
            say(label, "verdict", "not green; reviewer notes next")
            say(label, "reviewer", "start")
            review_prompt = fill(review_base, run=self.spec.run, stage=stage)
            score_path = os.path.join(self.run_dir, "score-s%d.md" % stage)
            rfiles = {
                "prompt.md": os.path.join(self.ctx.benchmark_dir, "prompt.md"),
                "score-s%d.md" % stage: score_path,
            }
            rres = self._pass(
                role="reviewer",
                stage=stage,
                prompt_text=review_prompt,
                files=rfiles,
                artifact_name="review-s%d.md" % stage,
            )
            if rres is None:
                say(label, "reviewer", "no review; stopping")
                return S.EXIT_INTERNAL
            open(os.path.join(self.run_dir, "review-s%d.md" % stage), "w").write(
                rres.artifact_text
            )
            say(
                label,
                "reviewer",
                "end review-s%d.md %s" % (stage, size(rres.artifact_text)),
            )
            last_review = rres.artifact_text
        return S.EXIT_OK


def run_pipeline(ctx):
    spec = RunSpec.from_file(os.path.join(ctx.state_dir(), "run.json"))
    config = ctx.config
    executor = RealExecutor(ctx, spec, config)
    pipe = Pipeline(ctx, spec, config, executor)
    return pipe.run()
