#!/usr/bin/env python3
"""SessionStart hook: check onboarding state and surface engine status."""

from __future__ import annotations

from pathlib import Path

from _utils import brain_cli

ROOT = Path.cwd()
required = [
    ROOT / "memory" / "profile.md",
    ROOT / "memory" / "preferences.md",
    ROOT / "memory" / "MEMORY.md",
    ROOT / "memory" / "retrieval-policy.md",
]
missing = []
for path in required:
    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        missing.append(str(path.relative_to(ROOT)))

if missing:
    print(
        "CC Agent Brain notice: onboarding or memory setup is incomplete. "
        "Use the cc-agent-brain-onboard-user skill before continuing. "
        "Missing or empty files: " + ", ".join(missing)
    )
else:
    stats = brain_cli(["stats"])
    if isinstance(stats, dict):
        print(
            "CC Agent Brain loaded. Read memory/MEMORY.md and follow memory/retrieval-policy.md. "
            f"Local engine: {stats.get('memories_active', 0)} active memories, "
            f"{stats.get('events_total', 0)} captured events. "
            "Retrieval is automatic (FTS5); search wiki/ when deeper context is needed."
        )
    else:
        print(
            "CC Agent Brain loaded. Read memory/MEMORY.md and follow memory/retrieval-policy.md. "
            "Use wiki/ as the local second brain when memory is insufficient."
        )
