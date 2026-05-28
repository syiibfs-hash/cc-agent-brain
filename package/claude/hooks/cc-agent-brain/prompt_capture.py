#!/usr/bin/env python3
"""UserPromptSubmit hook: append prompt metadata to local Wiki sessions.

The hook captures every user prompt as-is. Secrets and credentials are not
filtered here — that belongs in the memory-distill skill layer, where a
human-curated rule ("Do not distill secrets, tokens, passwords, or
credentials") prevents sensitive data from entering long-term memory.

The local wiki/ and memory/ directories are excluded from git by the
project's .gitignore, so raw prompts remain local-only.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from _utils import read_stdin_json

data = read_stdin_json()
prompt = str(data.get("prompt") or data.get("raw_stdin") or "").strip()
if not prompt:
    sys.exit(0)

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

print("CC Agent Brain captured this prompt into local wiki/sessions.")
