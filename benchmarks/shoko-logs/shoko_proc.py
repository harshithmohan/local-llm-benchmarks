#!/usr/bin/env python3
"""shoko process helpers."""

import json
import os
import subprocess

OPENCODE_PREFIX = "OPENCODE_"


def scrub_opencode(env):
    dropped = sorted(k for k in env if k.startswith(OPENCODE_PREFIX))
    for k in dropped:
        del env[k]
    return dropped


def config_dir_from_env(env):
    xdg = env.get("XDG_CONFIG_HOME")
    if xdg:
        return os.path.join(xdg, "opencode")
    home = env.get("HOME")
    if home:
        return os.path.join(home, ".config", "opencode")
    return None


def child_env(env_extra=None, base=None):
    env = dict(os.environ if base is None else base)
    dropped = scrub_opencode(env)
    if env_extra:
        env.update({k: v for k, v in env_extra.items() if v is not None})
    return env, dropped


def permission_entries(actions):
    return [
        {"action": a, "resource": "*", "effect": "allow"} for a in (actions or []) if a
    ]


def provider_json(
    provider_id,
    model_key,
    base_url,
    ctx_limit=None,
    out_cap=None,
    name=None,
    permissions=None,
):
    doc = {}
    if provider_id:
        model = {}
        if name:
            model["name"] = name
        limit = {}
        if ctx_limit is not None:
            limit["context"] = int(ctx_limit)
        if out_cap is not None:
            limit["output"] = int(out_cap)
        if limit:
            model["limit"] = limit
        doc["provider"] = {
            provider_id: {
                "npm": "@ai-sdk/openai-compatible",
                "name": "shoko-endpoint",
                "options": {"baseURL": base_url},
                "models": {model_key: model},
            }
        }
    perms = permission_entries(permissions)
    if perms:
        doc["permissions"] = perms
    return json.dumps(doc)


class SpawnResult:
    def __init__(self, exit_code, stdout_path, timed_out=False, argv=None):
        self.exit_code = exit_code
        self.stdout_path = stdout_path
        self.timed_out = timed_out
        self.argv = argv or []

    @property
    def ok(self):
        return self.exit_code == 0 and not self.timed_out

    def read(self):
        try:
            with open(self.stdout_path, "rb") as fh:
                return fh.read()
        except OSError:
            return b""


def spawn_host(
    *,
    role,
    inner,
    cwd,
    stdout_path,
    timeout,
    env_extra=None,
    merge_stderr=False,
    trace=False,
    trace_prefix="",
    trace_out=None,
    env_path=None,
):
    env, _scrubbed = child_env(env_extra=env_extra)
    if cwd:
        env["PWD"] = os.path.abspath(cwd)
        env.pop("OLDPWD", None)
    os.makedirs(os.path.dirname(stdout_path) or ".", exist_ok=True)
    argv = list(inner)
    return _spawn_streaming(
        argv,
        stdout_path,
        timeout,
        cwd=cwd,
        env=env,
        merge_stderr=merge_stderr,
    )


def _spawn_streaming(
    argv, stdout_path, timeout, poll=0.2, cwd=None, env=None, merge_stderr=False
):
    with open(stdout_path, "wb") as out:
        p = subprocess.Popen(
            argv,
            stdout=out,
            stderr=subprocess.STDOUT if merge_stderr else subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            cwd=cwd,
            env=env,
        )
    timed_out = False
    try:
        p.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        _kill_group(p)
        try:
            p.wait(timeout=30)
        except subprocess.TimeoutExpired:
            pass
    try:
        err = p.stderr.read() if p.stderr is not None else b""
    except (OSError, ValueError):
        err = b""
    finally:
        if p.stderr is not None:
            try:
                p.stderr.close()
            except (OSError, ValueError):
                pass
    exit_code = p.returncode if p.returncode is not None else -9
    if timed_out:
        with open(stdout_path, "ab") as fh:
            fh.write(b"\n[shoko] timed out after %s s\n" % str(timeout).encode())
        if err:
            with open(stdout_path, "ab") as fh:
                fh.write(b"[shoko stderr] " + err[-4096:] + b"\n")
    return SpawnResult(exit_code, stdout_path, timed_out, argv)


def _kill_group(p):
    import signal

    try:
        os.killpg(os.getpgid(p.pid), signal.SIGTERM)
        for _ in range(50):
            if p.poll() is not None:
                return
            import time

            time.sleep(0.1)
        os.killpg(os.getpgid(p.pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            p.kill()
        except OSError:
            pass
