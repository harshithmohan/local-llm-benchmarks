#!/usr/bin/env python3
"""shoko_stream — parse the opencode NDJSON event stream a role turn emits."""

import json
import re

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
