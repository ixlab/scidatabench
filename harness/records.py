"""Result accumulators and message serialization.

A `PhaseRecord` captures one phase's full trace: input messages, every
turn the agent took, tool calls + results, token / latency stats, the
extracted JSON envelope, and any errors.

Token + latency numbers come from the LangChain/LangGraph message
metadata. Gemini's "thinking" output, when present, lives in a content
block of type `thinking` on AIMessage — we capture that separately.
`tokens.output` already includes thinking tokens; `tokens.thinking` is the
part of it that was thinking.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage


_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*\n(.*?)\n```", re.DOTALL)


# ---------------------------------------------------------------------------
# Message serialization
# ---------------------------------------------------------------------------

def serialize_message(msg) -> dict:
    """Return a JSON-safe dict capturing the salient bits of a LangChain
    message, including content blocks (text + thinking), tool calls, tool
    name (for ToolMessage), and any usage_metadata."""
    role = msg.__class__.__name__
    content = getattr(msg, "content", "")
    tool_calls = list(getattr(msg, "tool_calls", None) or [])
    name = getattr(msg, "name", None)
    usage = getattr(msg, "usage_metadata", None)
    additional_kwargs = getattr(msg, "additional_kwargs", None) or {}

    # Normalize content into a list of blocks.
    blocks: list[dict] = []
    if isinstance(content, list):
        for b in content:
            if isinstance(b, dict):
                blocks.append(b)
            else:
                blocks.append({"type": "text", "text": str(b)})
    elif isinstance(content, str):
        if content:
            blocks.append({"type": "text", "text": content})

    return {
        "role": role,
        "name": name,
        "blocks": blocks,
        "tool_calls": [
            {"name": tc.get("name"), "args": tc.get("args"), "id": tc.get("id")}
            for tc in tool_calls
        ],
        "usage_metadata": dict(usage) if usage else None,
        "additional_kwargs": _safe_jsonable(additional_kwargs),
    }


def _safe_jsonable(obj: Any) -> Any:
    """Best-effort coerce to JSON-serializable; fall back to str()."""
    try:
        json.dumps(obj)
        return obj
    except Exception:
        if isinstance(obj, dict):
            return {k: _safe_jsonable(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_safe_jsonable(v) for v in obj]
        return str(obj)


# ---------------------------------------------------------------------------
# Envelope extraction
# ---------------------------------------------------------------------------

def extract_envelope(text: str) -> dict | list | None:
    """Pull a JSON object/list from the agent's final message — fenced
    block first, else the last balanced {...} or [...] substring."""
    if not text:
        return None
    matches = _JSON_FENCE_RE.findall(text)
    if matches:
        for blob in reversed(matches):
            try:
                return json.loads(blob)
            except Exception:
                continue
    # Fallback: last balanced {...} or [...]
    for opener, closer in (("{", "}"), ("[", "]")):
        last = text.rfind(closer)
        if last == -1:
            continue
        depth = 0
        start = -1
        for i in range(last, -1, -1):
            ch = text[i]
            if ch == closer:
                depth += 1
            elif ch == opener:
                depth -= 1
                if depth == 0:
                    start = i
                    break
        if start != -1:
            try:
                return json.loads(text[start:last + 1])
            except Exception:
                pass
    return None


def _final_text(msg) -> str:
    content = getattr(msg, "content", "")
    if isinstance(content, list):
        parts: list[str] = []
        for b in content:
            if isinstance(b, dict) and b.get("type") == "text":
                t = b.get("text", "")
                if t:
                    parts.append(t)
            elif isinstance(b, str) and b:
                parts.append(b)
        return "\n".join(parts)
    return str(content) if content else ""


# ---------------------------------------------------------------------------
# Aggregations
# ---------------------------------------------------------------------------

def _sum_tokens(messages: list) -> dict:
    """Collect token counts from every AIMessage's usage_metadata."""
    pin, pout, pthink, ptotal = 0, 0, 0, 0
    cache_read = 0
    for m in messages:
        u = getattr(m, "usage_metadata", None) or {}
        if not u:
            continue
        pin += int(u.get("input_tokens") or 0)
        pout += int(u.get("output_tokens") or 0)
        ptotal += int(u.get("total_tokens") or 0)
        # Gemini reports thinking under input_token_details.cache_read or
        # output_token_details.reasoning depending on version.
        details = u.get("output_token_details") or {}
        pthink += int(details.get("reasoning") or 0)
        idet = u.get("input_token_details") or {}
        cache_read += int(idet.get("cache_read") or 0)
    return {
        "input": pin, "output": pout, "thinking": pthink,
        "total": ptotal or (pin + pout),
        "cache_read": cache_read,
    }


def _tool_summary(messages: list) -> dict:
    """Count tool invocations and capture each call/result inline."""
    invocations: list[dict] = []
    counts: dict[str, int] = {}
    pending_by_id: dict[str, dict] = {}
    for m in messages:
        if isinstance(m, AIMessage):
            for tc in (getattr(m, "tool_calls", None) or []):
                rec = {
                    "name": tc.get("name"),
                    "args": tc.get("args"),
                    "id": tc.get("id"),
                    "result": None,
                }
                pending_by_id[tc.get("id")] = rec
                invocations.append(rec)
                counts[rec["name"]] = counts.get(rec["name"], 0) + 1
        elif isinstance(m, ToolMessage):
            tc_id = getattr(m, "tool_call_id", None)
            rec = pending_by_id.get(tc_id)
            if rec is not None:
                content = getattr(m, "content", "")
                if isinstance(content, list):
                    content = json.dumps(content, default=str)
                # Truncate very long tool outputs
                if isinstance(content, str) and len(content) > 8000:
                    content = content[:8000] + "\n...[truncated]..."
                rec["result"] = content
    return {"counts": counts, "invocations": invocations}


def _thinking_traces(messages: list) -> list[str]:
    out: list[str] = []
    for m in messages:
        if not isinstance(m, AIMessage):
            continue
        content = getattr(m, "content", "")
        if not isinstance(content, list):
            continue
        for b in content:
            if isinstance(b, dict) and b.get("type") in ("thinking", "reasoning"):
                t = b.get("text") or b.get("thinking") or ""
                if t:
                    out.append(t)
    return out


# ---------------------------------------------------------------------------
# Phase record (the unit of output for one (scenario, phase) pair)
# ---------------------------------------------------------------------------

@dataclass
class PhaseRecord:
    scenario_id: str
    platform: str
    phase: int
    model_id: str
    started_at: str = ""
    finished_at: str = ""
    wall_time_s: float = 0.0
    input_messages: list[dict] = field(default_factory=list)
    output_messages: list[dict] = field(default_factory=list)
    final_text: str = ""
    envelope: Any = None
    thinking_traces: list[str] = field(default_factory=list)
    tool_calls: dict = field(default_factory=dict)
    tokens: dict = field(default_factory=dict)
    error: str | None = None
    # Comparison results, lifted to top level for fast aggregation.
    # Phase 2 is graded afterwards, on the data its calls return
    # (scripts/grade_phase2.py), so these stay None on phase-2 records.
    verdict: str | None = None        # "match" | "partial" | "mismatch" | "error"
    binary_pass: bool | None = None   # the pass criterion of the paper
    score: float | None = None        # secondary continuous metric in [0, 1]
    comparison: dict | None = None    # full per-comparator details

    def to_dict(self) -> dict:
        d = self.__dict__.copy()
        return _safe_jsonable(d)


def make_phase_record(*, scenario_id: str, platform: str, phase: int,
                      model_id: str) -> PhaseRecord:
    return PhaseRecord(scenario_id=scenario_id, platform=platform,
                       phase=phase, model_id=model_id)


def fill_record_from_run(record: PhaseRecord, *,
                         input_messages: list,
                         output_messages: list,
                         t_start: float, t_end: float,
                         error: str | None = None) -> PhaseRecord:
    record.started_at = time.strftime("%Y-%m-%dT%H:%M:%S",
                                      time.gmtime(t_start)) + "Z"
    record.finished_at = time.strftime("%Y-%m-%dT%H:%M:%S",
                                       time.gmtime(t_end)) + "Z"
    record.wall_time_s = round(t_end - t_start, 3)
    record.input_messages = [serialize_message(m) for m in input_messages]
    record.output_messages = [serialize_message(m) for m in output_messages]

    # `output_messages` returned by langgraph contains the full state =
    # (input_messages + new agent messages). We only extract the envelope
    # and tool/token stats from the NEW portion.
    new_msgs = output_messages[len(input_messages):]
    final = ""
    for m in reversed(new_msgs):
        if isinstance(m, AIMessage):
            t = _final_text(m)
            if t:
                final = t
                break
    record.final_text = final
    record.envelope = extract_envelope(final)
    record.thinking_traces = _thinking_traces(new_msgs)
    record.tool_calls = _tool_summary(new_msgs)
    record.tokens = _sum_tokens(new_msgs)
    record.error = error
    return record
