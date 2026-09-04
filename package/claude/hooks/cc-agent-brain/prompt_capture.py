#!/usr/bin/env python3
"""UserPromptSubmit hook: capture every prompt.

Two sinks:
  1. Append a human-readable copy to wiki/sessions/YYYY-MM-DD.md (projection).
  2. Insert an event into the local brain engine (SQLite FTS5 index).

Secret redaction happens inside the engine at write time. The raw Markdown
copy stays local and wiki/ is git-ignored.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from _utils import brain_event, read_stdin_json

data = read_stdin_json()
prompt = str(data.get("prompt") or data.get("raw_stdin") or "").strip()
if not prompt:
    raise SystemExit(0)

root = Path.cwd()
sessions = root / "wiki" / "sessions"
sessions.mkdir(parents=True, exist_ok=True)
now = datetime.now()
file = sessions / f"{now:%Y-%m-%d}.md"

with file.open("a", encoding="utf-8") as f:
    f.write(f"\n\n## {now:%H:%M} User Prompt\n\n")
    f.write("### Raw Prompt\n")
    f.write(prompt + "\n\n")
    f.write("### Auto Tags\n")
    f.write("- source: user_prompt\n")
    f.write("- memory_candidate: pending\n")

# Structured sink — indexed for real retrieval (best-effort, never blocks).
brain_event("user", prompt, tags=["user_prompt"], source="prompt_capture")

print("CC Agent Brain captured this prompt into wiki/sessions and the local engine.")
