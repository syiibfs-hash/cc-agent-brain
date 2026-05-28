#!/usr/bin/env python3
"""PreCompact hook: create a lightweight checkpoint before context compaction."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

root = Path.cwd()
checkpoints = root / "wiki" / "sessions" / "checkpoints"
checkpoints.mkdir(parents=True, exist_ok=True)
now = datetime.now()
file = checkpoints / f"{now:%Y-%m-%d-%H%M%S}-pre-compact.md"
file.write_text(
    "---\n"
    "type: pre_compact_checkpoint\n"
    f"created: {now.isoformat(timespec='seconds')}\n"
    "---\n\n"
    "# Pre-compact checkpoint\n\n"
    "Claude Code is about to compact context. Review the recent session notes and update wiki/projects or memory if needed.\n",
    encoding="utf-8",
)
print(f"CC Agent Brain created pre-compact checkpoint: {file.relative_to(root)}")
