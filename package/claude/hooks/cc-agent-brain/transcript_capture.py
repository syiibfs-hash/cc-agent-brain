#!/usr/bin/env python3
"""Stop hook: close the capture loop.

UserPromptSubmit only sees what the user typed. This hook reads Claude
Code's transcript JSONL (path provided on stdin) and indexes what the
assistant actually did — text replies and tool calls — so decisions and
their outcomes survive across sessions.

Idempotent: processed message UUIDs are remembered in a cursor file.
Best-effort throughout: any failure is silent and never blocks the stop.
"""

from __future__ import annotations

import json
from pathlib import Path

from _utils import brain_cli, read_stdin_json

MAX_TEXT = 4000
MAX_TOOL_INPUT = 800
MAX_NEW_PER_RUN = 200
CURSOR = Path.cwd() / ".cc-agent-brain" / "transcript-cursor.json"


def load_cursor() -> dict:
    try:
        return json.loads(CURSOR.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"processed": []}


def save_cursor(cursor: dict) -> None:
    # Keep the cursor bounded.
    cursor["processed"] = cursor.get("processed", [])[-500:]
    try:
        CURSOR.parent.mkdir(parents=True, exist_ok=True)
        CURSOR.write_text(json.dumps(cursor, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def clip(text: str, limit: int) -> str:
    text = (text or "").strip().replace("\n", " ")
    return text if len(text) <= limit else text[:limit] + "…"


def extract(msg: dict):
    """Yield (kind, content, tags) tuples from one transcript message."""
    message = msg.get("message")
    if not isinstance(message, dict):
        return
    if message.get("role") != "assistant":
        # User text is already captured by prompt_capture; tool_result blobs
        # are too noisy and are skipped on purpose.
        return
    content = message.get("content")
    if isinstance(content, str):
        if content.strip():
            yield "assistant", clip(content, MAX_TEXT), ["assistant_reply"]
        return
    if not isinstance(content, list):
        return
    for block in content:
        if not isinstance(block, dict):
            continue
        btype = block.get("type")
        if btype == "text":
            text = block.get("text", "")
            if text.strip():
                yield "assistant", clip(text, MAX_TEXT), ["assistant_reply"]
        elif btype == "tool_use":
            name = block.get("name", "tool")
            inp = block.get("input", {})
            try:
                raw = json.dumps(inp, ensure_ascii=False)
            except (TypeError, ValueError):
                raw = str(inp)
            yield "tool", f"{name}: {clip(raw, MAX_TOOL_INPUT)}", [f"tool:{name}"]


def main() -> int:
    data = read_stdin_json()
    transcript = data.get("transcript_path")
    if not transcript or not Path(transcript).exists():
        return 0

    cursor = load_cursor()
    processed = set(cursor.get("processed", []))
    new_count = 0

    with open(transcript, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            uuid = msg.get("uuid")
            if not uuid or uuid in processed:
                continue
            for kind, content, tags in extract(msg):
                brain_cli(["event", "--kind", kind, "--content", content, "--tags", ",".join(tags), "--source", "transcript"])
            processed.add(uuid)
            new_count += 1
            if new_count >= MAX_NEW_PER_RUN:
                break

    cursor["processed"] = list(processed)
    save_cursor(cursor)

    # Gentle consolidation nudge when work accumulated.
    candidates = brain_cli(["candidates", "--days", "1"])
    if isinstance(candidates, dict):
        counts = {r["kind"]: r["n"] for r in candidates.get("counts_by_kind", [])}
        if counts.get("assistant", 0) + counts.get("tool", 0) >= 6:
            print(
                "CC Agent Brain: several assistant actions were just indexed. "
                "Consider running cc-agent-brain-memory-distill to keep long-term memory current."
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
