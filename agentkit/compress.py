"""Deterministic context compression for agent message histories.

Implements the lightest-touch techniques first (see notes/05-context-compression.md):
  1. tool-result clearing: replace all but the most recent K tool results with a stub
  2. head/tail truncation of oversized tool outputs
  3. exact-duplicate tool-result collapsing

Messages are plain dicts: {"role": "user"|"assistant"|"tool", "content": str, ...}.
Everything here is deterministic (same input -> same output), so compressed
transcripts can be hashed and cached.

Token counts here are a rough chars/4 ESTIMATE for budgeting only; it is a
heuristic, not a tokenizer. Use your provider's token-counting endpoint when
accuracy matters.
"""

from __future__ import annotations

import hashlib

CLEARED = "[tool result cleared to save context; re-run the tool if needed] sha256:{digest}"


def estimate_tokens(text: str, chars_per_token: float = 4.0) -> int:
    return int(len(text) / chars_per_token) + 1 if text else 0


def history_tokens(messages: list[dict]) -> int:
    return sum(estimate_tokens(m.get("content", "")) for m in messages)


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def truncate_middle(text: str, max_chars: int, marker: str = "\n... [{n} chars elided] ...\n") -> str:
    if len(text) <= max_chars:
        return text
    keep = max(0, max_chars - len(marker))
    head = keep * 2 // 3
    tail = keep - head
    elided = len(text) - head - tail
    return text[:head] + marker.format(n=elided) + (text[-tail:] if tail else "")


def clear_old_tool_results(messages: list[dict], keep_last: int = 3) -> list[dict]:
    tool_idx = [i for i, m in enumerate(messages) if m.get("role") == "tool"]
    to_clear = set(tool_idx[:-keep_last] if keep_last else tool_idx)
    out = []
    for i, m in enumerate(messages):
        if i in to_clear and not m.get("pinned"):
            m = {**m, "content": CLEARED.format(digest=_digest(m.get("content", "")))}
        out.append(m)
    return out


def dedupe_tool_results(messages: list[dict]) -> list[dict]:
    seen: dict[str, int] = {}
    out = []
    for i, m in enumerate(messages):
        if m.get("role") == "tool":
            d = _digest(m.get("content", ""))
            if d in seen:
                m = {**m, "content": f"[identical to tool result #{seen[d]}] sha256:{d}"}
            else:
                seen[d] = i
        out.append(m)
    return out


def compress(messages: list[dict], max_tool_chars: int = 4000, keep_last_tools: int = 3,
             target_tokens: int | None = None) -> list[dict]:
    """Apply truncation + dedupe; clear old tool results only if still over target."""
    msgs = [
        {**m, "content": truncate_middle(m.get("content", ""), max_tool_chars)} if m.get("role") == "tool" else m
        for m in messages
    ]
    msgs = dedupe_tool_results(msgs)
    if target_tokens is None or history_tokens(msgs) > target_tokens:
        msgs = clear_old_tool_results(msgs, keep_last_tools)
    return msgs
