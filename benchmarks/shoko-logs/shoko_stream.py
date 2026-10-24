#!/usr/bin/env python3
"""shoko_stream — parse the opencode NDJSON event stream a role turn emits."""

import json
import os
import re
import sys
import time

TOOL_LINE_RE = re.compile(r"^⚙ (\S+)")


def _decode(raw):
    return (
        bytes(raw).decode("utf-8", "replace")
        if isinstance(raw, (bytes, bytearray))
        else raw
    )


def _json_lines(text):
    for i, line in enumerate(text.splitlines(), start=1):
        obj = None
        s = line.strip()
        if s.startswith("{"):
            try:
                obj = json.loads(s)
            except ValueError:
                obj = None
        yield i, obj, line


class ParsedPass:
    def __init__(self):
        self.session_id = None
        self.finish = None
        self.finish_raw = None
        self.tool_calls = []
        self.text = ""
        self.reasoning = ""
        self.errors = []
        self.output_limit = False
        self.output_limit_message = None
        self.length_finishes = 0


def parse_stream(raw):
    """Fold one role turn's stdout into a ParsedPass.

    Recognises the opencode JSON event shapes that matter to the runner: the
    session id, text/reasoning parts, tool calls, step boundaries (which decide
    the finish reason) and errors (including the provider's output-token-limit
    error, which means the turn stopped at the cap rather than completing).
    """
    text = _decode(raw)
    p = ParsedPass()
    last_tool = None
    last_finish_reason = None
    last_finish_line = 0
    last_start_line = 0
    length_finishes = 0
    output_limit = False
    text_parts = []
    reasoning_parts = []

    for lineno, obj, raw_line in _json_lines(text):
        if obj is None:
            m = TOOL_LINE_RE.match(raw_line)
            if m:
                p.tool_calls.append(
                    {"name": m.group(1), "args_text": "", "line": lineno}
                )
                last_tool = m.group(1)
            if raw_line.strip():
                text_parts.append(raw_line)
            continue
        if isinstance(obj.get("sessionID"), str) and p.session_id is None:
            p.session_id = obj["sessionID"]
        etype = obj.get("type")
        part = obj.get("part") or {}
        if etype == "text":
            s = part.get("text")
            if isinstance(s, str):
                text_parts.append(s)
        elif etype == "reasoning":
            s = part.get("text")
            if isinstance(s, str):
                reasoning_parts.append(s)
        elif etype == "tool_use":
            name = part.get("tool") or part.get("name") or "?"
            state = part.get("state") or {}
            args = state.get("input")
            args_text = (
                args if isinstance(args, str) else json.dumps(args, sort_keys=True)
            )
            p.tool_calls.append({"name": name, "args_text": args_text, "line": lineno})
            last_tool = name
        elif etype == "step_start":
            last_start_line = lineno
        elif etype == "step_finish":
            reason = part.get("reason")
            p.finish_raw = reason
            last_finish_reason = reason
            last_finish_line = lineno
            if reason == "length":
                length_finishes += 1
        elif etype == "error":
            err = obj.get("error") or {}
            msg = err.get("message") if isinstance(err, dict) else str(err)
            msg = msg or "error"
            p.errors.append({"line": lineno, "text": msg, "after_tool": last_tool})
            etype_err = err.get("type") if isinstance(err, dict) else None
            if etype_err == "output-limit" or "output token limit" in msg:
                output_limit = True
                p.output_limit_message = msg

    p.text = "".join(text_parts)
    p.reasoning = "".join(reasoning_parts)
    p.length_finishes = length_finishes
    p.output_limit = output_limit

    continued_after_last_finish = (
        last_finish_line > 0 and last_start_line > last_finish_line
    )
    if output_limit:
        p.finish = "length"
        p.finish_raw = p.finish_raw or "length"
    elif last_finish_reason == "length" and not continued_after_last_finish:
        p.finish = "length"
        p.finish_raw = p.finish_raw or "length"
    elif last_finish_reason == "stop":
        p.finish = "stop"
    elif p.text.strip() and not p.errors:
        p.finish = "stop"
        p.finish_raw = p.finish_raw or "stop(derived)"
    return p


class TraceRenderer:
    """Render live NDJSON events as one-line progress for the run's output.

    This is for a human watching a run, not for grading: every event that
    carries nothing an operator can act on (a step boundary, an empty part)
    renders to nothing.  The raw bytes still land in the jsonl stream file
    unchanged -- the trace is a view of that record, never a substitute.
    Paths are shown relative to the run tree so a line stays readable.
    """

    def __init__(self, root=None, clip=96, out=None, label_width=9, event_width=7):
        self.root = os.path.abspath(root) if root else None
        self.clip = clip
        self.out = out
        self.label_width = label_width
        self.event_width = event_width

    def _clip(self, text, limit=None):
        s = " ".join(str(text or "").split())
        limit = self.clip if limit is None else limit
        return s[:limit] + ("…" if len(s) > limit else "")

    def _short(self, path):
        p = str(path or "")
        if not p:
            return ""
        if self.root and (p == self.root or p.startswith(self.root + os.sep)):
            p = "./" + os.path.relpath(p, self.root)
        home = os.path.expanduser("~")
        if home and p.startswith(home + os.sep):
            p = "~" + p[len(home) :]
        return self._clip(p, 88)

    def _tool(self, part):
        tool = part.get("tool") or "tool"
        state = part.get("state") or {}
        args = state.get("input") or {}
        status = state.get("status")
        if tool == "shell":
            lines = str(args.get("command") or "").strip().splitlines()
            detail = self._clip(lines[0], 110) if lines else ""
        elif tool in ("read", "edit", "write"):
            detail = self._short(args.get("filePath") or args.get("path"))
            if tool == "write" and args.get("content") is not None:
                detail += " (%d lines)" % len(str(args["content"]).splitlines())
            elif tool == "edit":
                detail += " (edit)"
        elif tool == "grep":
            detail = "%s in %s" % (
                self._clip(args.get("pattern"), 60),
                self._short(args.get("path") or "."),
            )
        elif tool == "glob":
            detail = self._clip(args.get("pattern"), 88)
        else:
            detail = self._clip(json.dumps(args, sort_keys=True), 88) if args else ""
        if status and status != "completed":
            detail = (detail + " [%s]" % status).strip()
        return tool, detail

    def line(self, obj):
        """(event, detail) for one event, or None when it says nothing."""
        part = obj.get("part") or {}
        kind = part.get("type")
        if kind == "reasoning":
            body = self._clip(part.get("text"))
            return ("think", '"%s"' % body) if body else None
        if kind == "text":
            body = self._clip(part.get("text"))
            return ("text", '"%s"' % body) if body else None
        if kind == "tool":
            return self._tool(part)
        if kind == "step-finish":
            tokens = part.get("tokens") or {}
            cache = tokens.get("cache") or {}
            return (
                "step",
                "finish=%s out=%s cache-read=%s"
                % (part.get("reason"), tokens.get("output"), cache.get("read")),
            )
        return None

    def emit(self, obj, prefix="", out=None):
        got = self.line(obj)
        if not got:
            return None
        event, detail = got
        stamp = time.strftime("%H:%M:%S")
        ts = obj.get("timestamp")
        if ts:
            try:
                stamp = time.strftime("%H:%M:%S", time.localtime(float(ts) / 1000.0))
            except (TypeError, ValueError, OSError):
                pass
        text = "%s  %-*s %-*s %s" % (
            stamp,
            self.label_width,
            prefix,
            self.event_width,
            event,
            detail,
        )
        fh = out or self.out or sys.stdout
        try:
            fh.write(text.rstrip() + "\n")
            fh.flush()
        except (BrokenPipeError, ValueError, OSError):
            # A trace line is never worth failing a run over: a closed or
            # full output stream must not take the turn down with it.
            return None
        return text


def trace_line(raw, prefix="", out=None, root=None):
    """Emit one trace line for a raw NDJSON stdout line; ignore anything else."""
    try:
        obj = json.loads(raw)
    except (ValueError, TypeError, UnicodeDecodeError):
        return None
    if not isinstance(obj, dict):
        return None
    return TraceRenderer(root=root, out=out).emit(obj, prefix=prefix)
