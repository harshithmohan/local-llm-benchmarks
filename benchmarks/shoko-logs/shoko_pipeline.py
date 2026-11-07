#!/usr/bin/env python3
"""shoko pipeline — the stage loop: implement → normalize → gates → harness → judge → review."""

import hashlib
import json
import os
import re
import shutil
import signal
import socket
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


# The sanitized harness report is failure-only and already per-bullet bounded
# (300 chars per symptom), so a full-red stage lands around 14K chars. This
# ceiling only guards against a runaway report, and it says so in the text: a
# silent cut would leave the judge grading a truncated failure list as if it
# were complete.
REPORT_LIMIT = 64 * 1024


def report_text(text):
    text = text or ""
    if len(text) <= REPORT_LIMIT:
        return text
    elided = len(text) - REPORT_LIMIT
    return "%s\n\n... %d chars elided from this report ...\n" % (
        text[:REPORT_LIMIT],
        elided,
    )


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


# ---------------------------------------------------------------------------
# resume planning: pure file-artifact scan
# ---------------------------------------------------------------------------

# The order a stage's work happens in; resume skips every step before the
# cursor's step but never reorders one.
STAGE_STEPS = (
    "impl",
    "normalize",
    "gates",
    "export",
    "harness",
    "judge",
    "verdict",
    "reviewer",
)

# The seven relative inputs pinned in run.json by prepare/build_run_json.
PIN_INPUTS = (
    "prompt.md",
    "rubric.md",
    "reference.diff",
    "harness/README.md",
    "harness/lines.json",
    "prompts/judge.txt",
    "prompts/reviewer.txt",
)


def is_green(harness, gates, config):
    """The run's one convergence rule, shared by the pipeline and the planner.

    Kept module-level so `resume_cursor` reads artifacts with exactly the same
    rules the live Pipeline applies -- a planner with a softer rule would skip
    work a fresh run would do.
    """
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
    expected = (config.get("harness") or {}).get("expected_total")
    if expected is not None and (total != expected or passed != expected):
        return False
    return True


def artifact_path(run_dir, name):
    return os.path.join(run_dir, name)


def has_artifact(run_dir, name):
    return os.path.isfile(artifact_path(run_dir, name))


def load_artifact_json(path):
    """Read an artifact the planner must trust, or fail loudly.

    Silently treating a corrupt gates/harness file as missing would re-run a
    step whose output already exists, which is the one thing resume must not
    do. Missing is handled by the caller; corrupt is a hard failure.
    """
    if not os.path.isfile(path):
        return None
    try:
        data = S.load_json(path)
    except Exception as exc:  # noqa: BLE001 - any parse/IO error is corruption
        raise S.Fail("resume-bad-artifact", "%s: %s" % (path, exc))
    if not isinstance(data, dict):
        raise S.Fail("resume-bad-artifact", "%s: not a JSON object" % path)
    return data


def stage_presence(run_dir, stage):
    names = {
        "patch": "patch-s%d.diff" % stage,
        "stat": "stat-s%d.txt" % stage,
        "gates": "gates-s%d.json" % stage,
        "harness": "harness-s%d.json" % stage,
        "score": "score-s%d.md" % stage,
        "review": "review-s%d.md" % stage,
    }
    return {k: has_artifact(run_dir, v) for k, v in names.items()}


def resume_cursor(run_dir, config):
    """Where a run stopped, derived only from artifacts on disk.

    Returns `{stage, step, complete, reason}`. First stage whose state is not
    settled wins. A judge sheet is the authority for what has been judged, so
    `score-sN.md` is checked before green: a green stage missing its sheet still
    has a judge pass ahead of it, and `finalize` always means the sheet exists.
    """
    for stage in range(3):
        present = stage_presence(run_dir, stage)
        patch, gates, harness = (
            present["patch"],
            present["gates"],
            present["harness"],
        )
        score, review = present["score"], present["review"]
        if score:
            if stage == 2:
                return {
                    "stage": stage,
                    "step": "finalize",
                    "complete": False,
                    "reason": "stage 2 score present",
                }
            hpath = artifact_path(run_dir, "harness-s%d.json" % stage)
            gpath = artifact_path(run_dir, "gates-s%d.json" % stage)
            harness = load_artifact_json(hpath)
            gates = load_artifact_json(gpath)
            if harness is None or gates is None:
                raise S.Fail(
                    "resume-bad-artifact",
                    "missing %s" % (hpath if harness is None else gpath),
                )
            if is_green(harness, gates, config):
                return {
                    "stage": stage,
                    "step": "finalize",
                    "complete": False,
                    "reason": "score present, green",
                }
            if review:
                continue
            return {
                "stage": stage,
                "step": "reviewer",
                "complete": False,
                "reason": "score present, review missing",
            }
        if not patch and not gates:
            return {
                "stage": stage,
                "step": "impl",
                "complete": False,
                "reason": "no patch or gates",
            }
        if not gates:
            return {
                "stage": stage,
                "step": "gates",
                "complete": False,
                "reason": "patch present, gates missing",
            }
        if not patch:
            return {
                "stage": stage,
                "step": "export",
                "complete": False,
                "reason": "gates present, patch missing",
            }
        if not harness:
            return {
                "stage": stage,
                "step": "harness",
                "complete": False,
                "reason": "patch and gates present, harness missing",
            }
        # Green is informational here: it explains why no reviewer follows the
        # judge, but the missing score sheet still has to be produced.
        reason = "harness present, score missing"
        if is_green(
            load_artifact_json(artifact_path(run_dir, "harness-s%d.json" % stage)),
            load_artifact_json(artifact_path(run_dir, "gates-s%d.json" % stage)),
            config,
        ):
            reason = "gates+harness green, score missing"
        return {
            "stage": stage,
            "step": "judge",
            "complete": False,
            "reason": reason,
        }
    # Stage 2 always returns above: with a score it finalizes, without one it
    # has a pass left to run. Reaching here means the artifact scan is broken.
    raise AssertionError("resume cursor: no unsettled stage")


def _path_under(path, roots):
    if not path:
        return False
    ap = os.path.abspath(path)
    for root in roots:
        rp = os.path.abspath(root)
        try:
            if os.path.commonpath([ap, rp]) == rp:
                return True
        except ValueError:
            continue
    return False


def process_cwd(pid):
    rc, out, _ = S.proc_text(
        ["lsof", "-a", "-p", str(pid), "-d", "cwd", "-Fn"], timeout=10
    )
    if rc == 0:
        for line in out.splitlines():
            if line.startswith("n"):
                return line[1:]
    try:
        return os.readlink("/proc/%d/cwd" % pid)
    except OSError:
        return None


def _process_comm(comm, cmd):
    """Best-effort executable basename, tolerating macOS' truncated `comm`."""
    base = os.path.basename((comm or "").strip()).lower()
    if base.startswith("python") or base in ("node", "opencode"):
        return base
    first = (cmd or "").strip().split(None, 1)
    if first:
        fallback = os.path.basename(first[0]).lower()
        if fallback.startswith("python") or fallback in ("node", "opencode"):
            return fallback
    return base


def _is_runner_command(cmd, run):
    toks = (cmd or "").split()
    for i in range(len(toks) - 2):
        if (
            toks[i].endswith("shoko.py")
            and toks[i + 1] in ("run", "resume")
            and toks[i + 2] == run
        ):
            return True
    return False


def find_stale_processes(ctx):
    """Processes from an older runner/pass still holding this run's paths.

    Only a real python runner is matched by command text; a shell or wrapper
    whose command line merely mentions the runner is ignored. opencode/node
    and harness processes are matched by executable plus cwd or path. The
    current process and all of its ancestors are never reported.
    """
    roots = [ctx.run_dir(), ctx.state_dir(), ctx.views_dir()]
    abs_roots = [os.path.abspath(p) for p in roots]
    rc, out, _ = S.proc_text(["ps", "-axo", "pid=,ppid=,comm=,command="], timeout=30)
    found = []
    if rc != 0:
        return found
    records = []
    parents = {}
    for line in out.splitlines():
        parts = line.strip().split(None, 3)
        if len(parts) < 3:
            continue
        try:
            pid = int(parts[0])
            ppid = int(parts[1])
        except ValueError:
            continue
        comm = parts[2]
        cmd = parts[3] if len(parts) > 3 else ""
        records.append((pid, comm, cmd))
        parents[pid] = ppid
    excluded = {os.getpid()}
    pid = os.getppid()
    seen = set()
    while pid and pid not in seen:
        seen.add(pid)
        excluded.add(pid)
        pid = parents.get(pid)
    for pid, comm, cmd in records:
        if pid in excluded:
            continue
        base = _process_comm(comm, cmd)
        is_python = base.startswith("python")
        is_opencode = base in ("node", "opencode")
        is_harness = "harness/run.sh" in cmd
        if is_python and _is_runner_command(cmd, ctx.run):
            found.append((pid, cmd))
            continue
        if not (is_opencode or is_harness):
            continue
        if any(p in cmd for p in abs_roots) or _path_under(process_cwd(pid), roots):
            found.append((pid, cmd))
    return found


def cleanup_stale_processes(ctx, kill=True):
    """SIGTERM stale processes, then SIGKILL survivors after a 3s grace.

    With `kill=False` (dry-run) it only reports what it saw, one line per PID.
    """
    found = find_stale_processes(ctx)
    if not found:
        return []
    pids = [pid for pid, _ in found]
    if not kill:
        for pid, cmd in found:
            print("stale pid=%d %s (would SIGTERM)" % (pid, cmd[:200]), flush=True)
        return pids
    for pid, cmd in found:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
        print("stale pid=%d SIGTERM %s" % (pid, cmd[:200]), flush=True)
    deadline = time.monotonic() + 3
    alive = set(pids)
    while alive and time.monotonic() < deadline:
        for pid in list(alive):
            try:
                os.kill(pid, 0)
            except OSError:
                alive.discard(pid)
        if alive:
            time.sleep(0.1)
    for pid in sorted(alive):
        try:
            os.kill(pid, signal.SIGKILL)
            print("stale pid=%d SIGKILL" % pid, flush=True)
        except OSError:
            pass
    return pids


def harness_port_busy(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.5)
    try:
        return s.connect_ex(("127.0.0.1", int(port))) == 0
    finally:
        s.close()


def later_artifacts(run_dir, stage):
    """Stage artifacts that claim work beyond the cursor (a torn resume)."""
    names = []
    for s in range(stage + 1, 3):
        for name in (
            "patch-s%d.diff" % s,
            "gates-s%d.json" % s,
            "harness-s%d.json" % s,
            "score-s%d.md" % s,
            "review-s%d.md" % s,
        ):
            if has_artifact(run_dir, name):
                names.append(name)
    return names


def quarantine_later_artifacts(ctx, names):
    if not names:
        return None
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    dest = os.path.join(ctx.state_dir(), "quarantine-" + stamp)
    base = dest
    n = 0
    while os.path.exists(dest):
        n += 1
        dest = "%s-%d" % (base, n)
    os.makedirs(dest, exist_ok=True)
    for name in names:
        shutil.move(os.path.join(ctx.run_dir(), name), os.path.join(dest, name))
    return dest


def resume_pin_check(ctx, spec):
    """Compare the live pins/config to run.json.

    Returns `(errors, warnings)`: config/input drift is an error (the run would
    not be comparable), while runner/opencode drift is only a warning -- both
    can change without altering the measured task.
    """
    data = spec.data if hasattr(spec, "data") else spec
    errors, warnings = [], []
    config_path = getattr(ctx, "config_path", None)
    if config_path and os.path.isfile(config_path):
        if S.sha256_file(config_path) != data.get("config_sha256"):
            errors.append("config_sha256")
    else:
        errors.append("config_sha256 (config file missing)")
    old_inputs = data.get("inputs_sha256") or {}
    new_inputs = {}
    for rel in PIN_INPUTS:
        p = os.path.join(ctx.benchmark_dir, rel)
        new_inputs[rel] = S.sha256_file(p) if os.path.isfile(p) else None
    if new_inputs != old_inputs:
        changed = [
            k
            for k in sorted(set(old_inputs) | set(new_inputs))
            if new_inputs.get(k) != old_inputs.get(k)
        ]
        errors.append("inputs_sha256: " + ", ".join(changed))
    try:
        if S.runner_digest() != data.get("runner_sha256"):
            warnings.append("runner_sha256")
    except Exception:  # noqa: BLE001 - digest is advisory only
        warnings.append("runner_sha256 (unreadable)")
    oc = data.get("opencode") or {}
    oc_bin = ctx.which("opencode")
    if not oc_bin:
        warnings.append("opencode missing")
    else:
        if oc.get("path") and oc_bin != oc.get("path"):
            warnings.append("opencode.path")
        try:
            if oc.get("sha256") and S.sha256_file(oc_bin) != oc.get("sha256"):
                warnings.append("opencode.sha256")
        except OSError:
            warnings.append("opencode.sha256 (unreadable)")
        rc, out, _ = S.proc_text([oc_bin, "--version"], timeout=30)
        version = out.strip() if rc == 0 else ""
        if oc.get("version") and version != oc.get("version"):
            warnings.append(
                "opencode.version %s != %s" % (version or "?", oc.get("version"))
            )
    return errors, warnings


def saved_session_id(state_dir, stage=None, state=None):
    """The session a resume may continue: newest stream, then state."""
    streams = os.path.join(state_dir, "streams")
    try:
        names = [n for n in os.listdir(streams) if n.endswith(".jsonl")]
    except OSError:
        names = []
    if stage is None:
        names = [n for n in names if n.startswith("impl-s")]
    else:
        names = [n for n in names if n.startswith("impl-s%d-a" % stage)]

    def mtime(name):
        try:
            return os.path.getmtime(os.path.join(streams, name))
        except OSError:
            return 0

    for name in sorted(names, key=mtime, reverse=True):
        try:
            with open(
                os.path.join(streams, name), "r", encoding="utf-8", errors="replace"
            ) as fh:
                for line in fh:
                    try:
                        obj = json.loads(line)
                    except Exception:  # noqa: BLE001 - tolerate partial lines
                        continue
                    if isinstance(obj, dict) and isinstance(obj.get("sessionID"), str):
                        return obj["sessionID"]
        except OSError:
            continue
    if state:
        sid = state.get("session_id")
        if sid:
            return sid
    return None


def next_attempt(state_dir, role, stage):
    """One past the highest attempt number already in streams/ for this pass."""
    streams = os.path.join(state_dir, "streams")
    prefix = "%s-s%d-a" % (role, stage)
    highest = 0
    try:
        names = os.listdir(streams)
    except OSError:
        names = []
    for name in names:
        if name.startswith(prefix) and name.endswith(".jsonl"):
            try:
                highest = max(highest, int(name[len(prefix) : -6]))
            except ValueError:
                continue
    return highest + 1


def would_run_harness(cursor, green=None):
    step, stage = cursor["step"], cursor["stage"]
    if step in ("impl", "normalize", "gates", "export", "harness"):
        return True
    if step == "judge":
        # A green judge finalizes without another harness run; a red one
        # continues into the reviewer and the next stage.
        return not green and stage < 2
    # A reviewer runs only after a red judge, so another stage follows.
    return step == "reviewer" and stage < 2


def print_resume_plan(ctx, spec, config, force=False):
    """`resume --dry-run`: the plan, with no executor and no writes."""
    run_dir = ctx.run_dir()
    state_dir = ctx.state_dir()
    cursor = resume_cursor(run_dir, config)
    state = S.RunStore(state_dir).read_state() or {}
    outcome = state.get("outcome")
    complete = (
        cursor["step"] == "finalize"
        and has_artifact(run_dir, "score.md")
        and bool(outcome)
    )
    print("resume plan: %s" % ctx.run)
    print(
        "cursor: stage=%d step=%s reason=%s complete=%s"
        % (
            cursor["stage"],
            cursor["step"],
            cursor["reason"],
            "yes" if complete else "no",
        )
    )
    print("artifacts:")
    stage_green = {}
    for stage in range(3):
        present = stage_presence(run_dir, stage)
        green = "?"
        stage_green[stage] = False
        if present["gates"] and present["harness"]:
            stage_green[stage] = is_green(
                load_artifact_json(artifact_path(run_dir, "harness-s%d.json" % stage)),
                load_artifact_json(artifact_path(run_dir, "gates-s%d.json" % stage)),
                config,
            )
            green = "yes" if stage_green[stage] else "no"
        print(
            "  s%d patch=%s gates=%s harness=%s score=%s review=%s green=%s"
            % (
                stage,
                "yes" if present["patch"] else "no",
                "yes" if present["gates"] else "no",
                "yes" if present["harness"] else "no",
                "yes" if present["score"] else "no",
                "yes" if present["review"] else "no",
                green,
            )
        )
    errors, warnings = resume_pin_check(ctx, spec)
    if errors:
        print("pins: MISMATCH %s" % "; ".join(errors))
    else:
        print("pins: ok")
    for warning in warnings:
        print("pin warning: %s" % warning)
    later = later_artifacts(run_dir, cursor["stage"])
    if later:
        suffix = (
            " (would quarantine with --force)"
            if force
            else " (resume would fail without --force)"
        )
        print("later artifacts: %s%s" % (", ".join(later), suffix))
    else:
        print("later artifacts: none")
    stale = find_stale_processes(ctx)
    if stale:
        for pid, cmd in stale:
            print("stale pid=%d %s (would SIGTERM)" % (pid, cmd[:200]))
    else:
        print("stale processes: none")
    webui = os.path.join(run_dir, "Shoko-WebUI")
    print(
        "tree: %s"
        % ("present" if os.path.isdir(webui) else "MISSING (resume would fail)")
    )
    if complete:
        print("would run: nothing (already complete: %s)" % (outcome or "unknown"))
    elif cursor["step"] == "finalize":
        stage = cursor["stage"]
        if has_artifact(run_dir, "score-s%d.md" % stage):
            print(
                "would run: s%d finalize (score.md from score-s%d.md + harness-s%d.json)"
                % (stage, stage, stage)
            )
        else:
            print("would run: s%d judge, then finalize (score.md)" % stage)
    elif cursor["step"] == "judge":
        stage = cursor["stage"]
        if stage < 2:
            print(
                "would run: s%d judge; then finalize if green, else reviewer "
                "and s%d..s2 full stages" % (stage, stage + 1)
            )
        else:
            print("would run: s%d judge, then finalize" % stage)
    else:
        start = STAGE_STEPS.index(cursor["step"])
        seq = ["s%d %s" % (cursor["stage"], s) for s in STAGE_STEPS[start:]]
        seq = [s for s in seq if not s.endswith(" verdict")]
        tail = ""
        if cursor["stage"] < 2:
            tail = "; then s%d..s2 full stages" % (cursor["stage"] + 1)
        print("would run: %s%s" % (", ".join(seq), tail))
    plan_green = stage_green.get(cursor["stage"]) if cursor["step"] == "judge" else None
    if would_run_harness(cursor, plan_green) and not complete:
        port = (spec.harness or {}).get("port", 3100)
        print(
            "harness port %s: %s"
            % (port, "BUSY" if harness_port_busy(port) else "free")
        )
    return S.EXIT_OK


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
            level = self.spec.model.get("variant")
            variants = (
                [{"id": level, "settings": {"reasoningEffort": level}}]
                if level
                else None
            )
            return proc.provider_json(
                self.spec.provider_id,
                self.spec.model.get("id"),
                self.endpoint_base_url(),
                ctx_limit=self.spec.ctx_limit,
                out_cap=self.spec.out_cap,
                permissions=perms,
                variants=variants,
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
                trace=bool(getattr(self.ctx.args, "trace_streams", True)),
                trace_prefix="s%d %s" % (stage, role),
                trace_out=sys.stdout,
                trace_root=view,
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
        self.log_dir = os.path.join(self.state_dir, "streams")

    def _state(self, **fields):
        """Advance state.json so the run's phase on disk is never stale.

        state.json is the operator's (and the crash record's) view of where a
        run got to; before this the file still said "prepared, stage 0" after a
        full three-stage run. Best-effort: a failed state write must never stop
        a run, the artifacts are still the record.

        `done_add` appends one or more settled artifact ids (s<N>.impl etc),
        and `history_event` appends a capped event trail. Both are optional and
        tolerate schema-1 states that predate them."""
        done_add = fields.pop("done_add", None)
        history_event = fields.pop("history_event", None)
        try:
            store = S.RunStore(self.state_dir)
            state = store.read_state() or store.new_state()
            state.setdefault("done", [])
            state.setdefault("history", [])
            state.update(fields)
            state["schema"] = 2
            if done_add:
                entries = (
                    done_add if isinstance(done_add, (list, tuple)) else [done_add]
                )
                for entry in entries:
                    if entry not in state["done"]:
                        state["done"].append(entry)
            if history_event:
                state["history"].append({"at": S.now_iso(), "event": history_event})
                state["history"] = state["history"][-200:]
            store.write_state(state)
        except Exception:  # noqa: BLE001 - never fail a run over bookkeeping
            pass

    def _is_green(self, harness, gates):
        """Delegate to the module rule so the planner and the run agree."""
        return is_green(harness, gates, self.config)

    def _pass(
        self,
        *,
        role,
        stage,
        prompt_text,
        files,
        artifact_name,
        attempts=2,
        first_attempt=1,
    ):
        """Run a judge/reviewer pass, requiring the artifact on disk.

        A pass's exit status is not trusted: what matters is that the artifact
        landed. A pass that produced nothing is re-run (its runtime is minutes,
        not the implementation's hours); if it still produces nothing, the run
        stops rather than grading against a missing sheet. On resume the
        attempt numbers continue past the existing stream files so an old log
        is never overwritten."""
        last = first_attempt + attempts - 1
        for attempt in range(first_attempt, last + 1):
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

    def _finalize(self, stage, score_txt, report, green):
        """Write the run's final score.md and close the trajectory.

        `report` is already sanitized/truncated harness report text (harness
        JSON stores the same text), so this writes it verbatim."""
        label = "s%d" % stage
        with open(os.path.join(self.run_dir, "score.md"), "w") as fh:
            fh.write(score_txt + "\n\n" + report)
        if green:
            self._state(
                phase="done",
                stage=stage,
                step="verdict",
                outcome="converged",
                done_add="s%d.verdict" % stage,
            )
            say(label, "verdict", "green; score.md written")
            return S.EXIT_OK
        self._state(
            phase="done",
            stage=stage,
            step="verdict",
            outcome="not converged",
            done_add="s%d.verdict" % stage,
        )
        say(label, "verdict", "not converged; score.md written")
        return S.EXIT_HALTED

    def _restore_stage_start(self, stage, force=False):
        """Put the worktree back at the tree stage N started from.

        Stage 0 starts at the run's history-free base; a later stage starts at
        the previous stage's cumulative patch on that base. `git clean -fd`
        (never `-x`) keeps ignored node_modules, so the restore does not pay
        for a fresh install."""
        base = self.spec.pins.get("run_base_commit")
        if not base:
            raise S.Fail(
                "resume-restore-failed", "run.json has no pins.run_base_commit"
            )
        git = self.executor.git
        rc, head, err = git.text("rev-parse", "HEAD")
        if rc != 0:
            raise S.Fail(
                "resume-restore-failed",
                "git rev-parse HEAD: %s" % (err.strip() or "exit %d" % rc),
            )
        if head.strip() != base and not force:
            raise S.Fail(
                "resume-head-mismatch",
                "HEAD %s != run_base_commit %s (use --force to override)"
                % (head.strip(), base),
            )
        r = git.run("reset", "--hard", base)
        if r.returncode != 0:
            raise S.Fail(
                "resume-restore-failed",
                "git reset --hard %s: %s"
                % (base, (r.stderr or b"").decode("utf-8", "replace").strip()),
            )
        r = git.run("clean", "-fd")
        if r.returncode != 0:
            raise S.Fail(
                "resume-restore-failed",
                "git clean -fd: %s"
                % (r.stderr or b"").decode("utf-8", "replace").strip(),
            )
        if stage == 0:
            return
        prev = os.path.join(self.run_dir, "patch-s%d.diff" % (stage - 1))
        if not os.path.isfile(prev):
            raise S.Fail("resume-restore-failed", "missing %s" % prev)
        r = git.run("apply", "--whitespace=nowarn", prev)
        if r.returncode != 0:
            r = git.run("apply", "--3way", "--whitespace=nowarn", prev)
            if r.returncode != 0:
                raise S.Fail(
                    "resume-restore-failed",
                    "git apply %s: %s"
                    % (prev, (r.stderr or b"").decode("utf-8", "replace").strip()),
                )

    def _check_tree_matches_patch(self, stage, required=False):
        """Refuse to grade a worktree that no longer matches `patch-sN.diff`.

        The patch is the stage's recorded tree, exported after normalize. The
        judge/reviewer reads the candidate tree, so a worktree that was edited
        or cleaned after export must not be graded against that patch. The
        check mirrors export (`git add -A`, cached diff from the run base) and
        only stages the index transiently; the tree itself is never changed."""
        patch = os.path.join(self.run_dir, "patch-s%d.diff" % stage)
        if not os.path.isfile(patch):
            if required:
                raise S.Fail("resume-tree-mismatch", "missing %s" % patch)
            return
        base = self.spec.pins.get("run_base_commit")
        if not base:
            raise S.Fail("resume-tree-mismatch", "run.json has no pins.run_base_commit")
        with open(patch, "rb") as fh:
            expected = fh.read()
        git = self.executor.git
        add = git.run("add", "-A")
        try:
            if add.returncode != 0:
                raise S.Fail(
                    "resume-tree-mismatch",
                    "git add -A: %s"
                    % (add.stderr or b"").decode("utf-8", "replace").strip(),
                )
            diff = git.run("diff", "--cached", "--no-ext-diff", base)
            if diff.returncode != 0:
                raise S.Fail(
                    "resume-tree-mismatch",
                    "git diff %s: %s"
                    % (
                        base,
                        (diff.stderr or b"").decode("utf-8", "replace").strip(),
                    ),
                )
            if (diff.stdout or b"") != expected:
                raise S.Fail(
                    "resume-tree-mismatch",
                    "worktree differs from %s; restore the stage end before resuming"
                    % patch,
                )
        finally:
            git.run("reset", "-q")

    def _run_resume(self, force=False, continue_session=False):
        """Continue from the first missing artifact; never redo settled work."""
        ex = self.executor
        run_dir = self.run_dir
        webui = os.path.join(run_dir, "Shoko-WebUI")
        if not os.path.isdir(webui):
            raise S.Fail("resume-no-tree", webui)
        store = S.RunStore(self.state_dir)
        state = store.read_state() or {}
        previous = state.get("resume_count") or 0
        cursor = resume_cursor(run_dir, self.config)
        outcome = state.get("outcome")
        score_md = artifact_path(run_dir, "score.md")
        # A completed run is a read-only report: return its outcome without
        # touching state/tree/processes (in particular without a resume bump).
        if cursor["step"] == "finalize" and os.path.isfile(score_md) and outcome:
            print("already complete: %s" % outcome)
            return S.EXIT_OK if outcome == "converged" else S.EXIT_HALTED
        if not force:
            errors, warnings = resume_pin_check(self.ctx, self.spec)
            for warning in warnings:
                say("resume", "pin", "warning %s" % warning)
            if errors:
                raise S.Fail("resume-pins-changed", ", ".join(errors))
        later = later_artifacts(run_dir, cursor["stage"])
        if later:
            if not force:
                raise S.Fail("resume-later-artifacts", ", ".join(later))
            dest = quarantine_later_artifacts(self.ctx, later)
            say(
                "resume",
                "quarantine",
                "%d later artifact(s) -> %s" % (len(later), dest),
            )
        stale = find_stale_processes(self.ctx)
        cleanup_stale_processes(self.ctx, kill=True)
        for tool in ("git", "opencode", "pnpm"):
            if not self.ctx.which(tool):
                raise S.Fail("resume-missing-tool", tool)

        stage = cursor["stage"]
        step = cursor["step"]
        if step == "finalize" and not has_artifact(run_dir, "score-s%d.md" % stage):
            # The planner guarantees this; fail loudly if artifacts change
            # between the scan and execution rather than judging an unrecorded
            # stage. Never a normal path.
            raise S.Fail("resume-bad-artifact", "finalize without score-s%d.md" % stage)
        port = (self.spec.harness or {}).get("port", 3100)
        probe_green = None
        if step == "judge":
            probe_green = is_green(
                load_artifact_json(artifact_path(run_dir, "harness-s%d.json" % stage)),
                load_artifact_json(artifact_path(run_dir, "gates-s%d.json" % stage)),
                self.config,
            )
        probe_port = would_run_harness({"stage": stage, "step": step}, probe_green)
        if probe_port and harness_port_busy(port):
            raise S.Fail("resume-port-busy", str(port))
        if not force:
            base = self.spec.pins.get("run_base_commit")
            if not base:
                raise S.Fail(
                    "resume-head-mismatch", "run.json has no pins.run_base_commit"
                )
            rc, head, err = self.executor.git.text("rev-parse", "HEAD")
            if rc != 0:
                raise S.Fail(
                    "resume-head-mismatch",
                    "git rev-parse HEAD: %s" % (err.strip() or "exit %d" % rc),
                )
            if head.strip() != base:
                raise S.Fail(
                    "resume-head-mismatch",
                    "HEAD %s != run_base_commit %s (use --force to override)"
                    % (head.strip(), base),
                )

        # Every guard has passed. Only now is the run actually resumed, so a
        # failed guard above leaves phase/resume_count/history untouched.
        if stale:
            self._state(history_event="stale-processes")
        self._state(
            phase="running",
            resumed_at=S.now_iso(),
            resume_count=previous + 1,
            history_event="resume",
        )
        state = store.read_state() or state
        say("resume", "plan", "stage=%d step=%s" % (stage, step))

        if step == "finalize":
            score_txt = read_text(artifact_path(run_dir, "score-s%d.md" % stage))
            gates_path = artifact_path(run_dir, "gates-s%d.json" % stage)
            harness_path = artifact_path(run_dir, "harness-s%d.json" % stage)
            for required in (gates_path, harness_path):
                if not os.path.isfile(required):
                    raise S.Fail("resume-bad-artifact", "missing %s" % required)
            gates = load_artifact_json(gates_path)
            harness = load_artifact_json(harness_path)
            green = is_green(harness or {}, gates or {}, self.config)
            say("s%d" % stage, "verdict", "resuming finalize")
            return self._finalize(
                stage,
                score_txt,
                report_text((harness or {}).get("text") or ""),
                green,
            )

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
        if not (step == "impl" and not continue_session):
            session_id = saved_session_id(self.state_dir, None, state)
        last_review = ""
        begin = STAGE_STEPS.index(step)
        idx_gates = STAGE_STEPS.index("gates")
        idx_harness = STAGE_STEPS.index("harness")
        idx_judge = STAGE_STEPS.index("judge")

        for stage in range(cursor["stage"], 3):
            first = stage == cursor["stage"]
            from_step = begin if first else 0
            label = "s%d" % stage
            if stage > 0:
                rpath = artifact_path(run_dir, "review-s%d.md" % (stage - 1))
                last_review = read_text(rpath) if os.path.isfile(rpath) else ""
            gates = None
            harness = None
            score_txt = None
            if from_step > idx_gates:
                gates = load_artifact_json(
                    artifact_path(run_dir, "gates-s%d.json" % stage)
                )
            if from_step > idx_harness:
                harness = load_artifact_json(
                    artifact_path(run_dir, "harness-s%d.json" % stage)
                )
            if from_step > idx_judge:
                spath = artifact_path(run_dir, "score-s%d.md" % stage)
                score_txt = read_text(spath) if os.path.isfile(spath) else None

            if from_step <= STAGE_STEPS.index("impl"):
                if stage > 0 and not last_review:
                    raise S.Fail(
                        "resume-missing-review",
                        artifact_path(run_dir, "review-s%d.md" % (stage - 1)),
                    )
                if first and continue_session:
                    saved = saved_session_id(self.state_dir, stage, state)
                    if not saved:
                        raise S.Fail("resume-no-session", "impl-s%d" % stage)
                    session_id = saved
                    say(label, "impl", "continue session %s" % saved)
                elif first:
                    self._restore_stage_start(stage, force)
                    session_id = None
                if stage == 0:
                    text = prompt
                else:
                    text = (
                        prompt
                        + "\n\n# Repair — stage %d, address the reviewer notes below:\n"
                        % stage
                        + last_review
                    )
                kind = "initial" if stage == 0 else "repair"
                attempt = next_attempt(self.state_dir, "impl", stage)
                self._state(phase="running", stage=stage, step="impl")
                say(
                    label,
                    "impl",
                    "start kind=%s attempt=%d%s"
                    % (kind, attempt, " (resume)" if first else ""),
                )
                t0 = time.monotonic()
                res = ex.impl_turn(
                    text=text,
                    session_id=session_id,
                    attempt=attempt,
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
                self._state(
                    step="normalize",
                    session_id=session_id,
                    done_add="s%d.impl" % stage,
                )

            if from_step <= STAGE_STEPS.index("normalize"):
                self._state(step="normalize")
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

            if from_step <= idx_gates:
                self._state(step="gates")
                say(label, "gates", "start")
                gates = ex.gates(stage=stage)
                with open(
                    os.path.join(self.run_dir, "gates-s%d.json" % stage), "w"
                ) as fh:
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
                self._state(done_add="s%d.gates" % stage)

            if from_step <= STAGE_STEPS.index("export"):
                exp = ex.export(stage=stage)
                if exp.get("error"):
                    say(
                        label,
                        "export",
                        "error %s" % str(exp["error"]).splitlines()[0],
                    )
                elif exp.get("empty"):
                    say(label, "export", "empty patch vs run base")
                else:
                    say(
                        label,
                        "export",
                        "patch-s%d.diff %s" % (stage, stat_line(exp.get("stat"))),
                    )
                self._state(done_add="s%d.export" % stage)

            if from_step <= idx_harness:
                self._check_tree_matches_patch(stage)
                self._state(step="harness")
                say(label, "harness", "start")
                h = ex.harness(stage=stage)
                if h.get("passed") is None:
                    say(
                        label,
                        "harness",
                        "no result exit=%s%s"
                        % (
                            h.get("exit"),
                            " timeout" if h.get("timed_out") else "",
                        ),
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
                            "text": report_text(h["text"]),
                        },
                        fh,
                    )
                if h.get("unmapped"):
                    raise S.Fail(
                        "harness-report-unmapped",
                        "%d failure(s) not keyed in harness/lines.json: %s"
                        % (len(h["unmapped"]), "; ".join(h["unmapped"])),
                    )
                harness = {
                    "exit": h["exit"],
                    "passed": h.get("passed"),
                    "total": h.get("total"),
                    "text": report_text(h.get("text") or ""),
                }
                self._state(step="judge", done_add="s%d.harness" % stage)

            if from_step <= idx_judge:
                self._check_tree_matches_patch(stage, required=True)
                self._state(step="judge")
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
                    first_attempt=next_attempt(self.state_dir, "judge", stage),
                )
                if jres is None:
                    say(label, "judge", "no score sheet; stopping")
                    return S.EXIT_INTERNAL
                score_txt = jres.artifact_text
                say(
                    label,
                    "judge",
                    "end score-s%d.md %s" % (stage, size(score_txt)),
                )
                with open(
                    os.path.join(self.run_dir, "score-s%d.md" % stage), "w"
                ) as fh:
                    fh.write(score_txt)
                self._state(done_add="s%d.judge" % stage)
                green = is_green(harness or {}, gates or {}, self.config)
                if green or stage == 2:
                    return self._finalize(
                        stage,
                        score_txt,
                        (harness or {}).get("text") or "",
                        green,
                    )

            self._check_tree_matches_patch(stage, required=True)
            self._state(step="reviewer")
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
                first_attempt=next_attempt(self.state_dir, "reviewer", stage),
            )
            if rres is None:
                say(label, "reviewer", "no review; stopping")
                return S.EXIT_INTERNAL
            with open(os.path.join(self.run_dir, "review-s%d.md" % stage), "w") as fh:
                fh.write(rres.artifact_text)
            say(
                label,
                "reviewer",
                "end review-s%d.md %s" % (stage, size(rres.artifact_text)),
            )
            self._state(done_add="s%d.review" % stage)
            last_review = rres.artifact_text
        return S.EXIT_OK

    def run(self, resume=False, force=False, continue_session=False, dry_run=False):
        if dry_run:
            return print_resume_plan(self.ctx, self.spec, self.config, force=force)
        if resume:
            return self._run_resume(force=force, continue_session=continue_session)
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
            self._state(phase="running", stage=stage, step="impl")
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
            self._state(
                step="normalize",
                session_id=session_id,
                done_add="s%d.impl" % stage,
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
            self._state(step="gates")
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
            self._state(done_add="s%d.gates" % stage)
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
            self._state(done_add="s%d.export" % stage)
            self._state(step="harness")
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
                        "text": report_text(h["text"]),
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
            self._state(step="judge", done_add="s%d.harness" % stage)
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
            self._state(done_add="s%d.judge" % stage)
            green = self._is_green(h, gates)
            if green or stage == 2:
                return self._finalize(
                    stage, score_txt, report_text(h["text"] or ""), green
                )
            self._state(step="reviewer")
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
            with open(os.path.join(self.run_dir, "review-s%d.md" % stage), "w") as fh:
                fh.write(rres.artifact_text)
            say(
                label,
                "reviewer",
                "end review-s%d.md %s" % (stage, size(rres.artifact_text)),
            )
            self._state(done_add="s%d.review" % stage)
            last_review = rres.artifact_text
        return S.EXIT_OK


def run_pipeline(ctx, resume=False):
    if not os.path.isfile(os.path.join(ctx.state_dir(), "run.json")):
        raise S.Fail("no-run-json", os.path.join(ctx.state_dir(), "run.json"))
    spec = RunSpec.from_file(os.path.join(ctx.state_dir(), "run.json"))
    config = ctx.config
    if resume and getattr(ctx.args, "dry_run", False):
        return print_resume_plan(
            ctx, spec, config, force=getattr(ctx.args, "force", False)
        )
    executor = RealExecutor(ctx, spec, config)
    pipe = Pipeline(ctx, spec, config, executor)
    return pipe.run(
        resume=resume,
        force=getattr(ctx.args, "force", False),
        continue_session=getattr(ctx.args, "continue_session", False),
        dry_run=getattr(ctx.args, "dry_run", False),
    )
