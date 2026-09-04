#!/usr/bin/env python3
"""PreCompact hook: checkpoint before context compaction."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from _utils import brain_event

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
    "Claude Code is about to compact context. Review the recent session notes, "
    "run cc-agent-brain-memory-distill on anything durable, and update "
    "wiki/projects or memory if needed.\n",
    encoding="utf-8",
)
brain_event("system", "Pre-compact checkpoint created before context compaction.", tags=["pre_compact"])
print(f"CC Agent Brain created pre-compact checkpoint: {file.relative_to(root)}")
