#!/usr/bin/env python3
"""Stop hook: audit memory health.

Uses the engine's SQL-based audit (duplicate active memories, broken
supersede chains, stale entries, low confidence, undistilled backlog) and
falls back to file-presence checks when the engine is unavailable.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from _utils import brain_cli

parser = argparse.ArgumentParser()
parser.add_argument("--light", action="store_true")
args = parser.parse_args()

root = Path.cwd()
issues = []

for file_name in ["MEMORY.md", "profile.md", "preferences.md", "active-projects.md", "retrieval-policy.md"]:
    p = root / "memory" / file_name
    if not p.exists() or not p.read_text(encoding="utf-8").strip():
        issues.append(f"missing_or_empty:memory/{file_name}")

report = brain_cli(["audit"])
if isinstance(report, dict):
    for item in report.get("issues", []):
        issues.append(f"{item.get('code')}: {item.get('message')}")
else:
    session_dir = root / "wiki" / "sessions"
    if session_dir.exists() and len(list(session_dir.glob("*.md"))) >= 5:
        issues.append("many_session_notes: consider running cc-agent-brain-memory-distill")

if not issues:
    print("CC Agent Brain memory audit: no urgent issues found.")
elif args.light:
    print("CC Agent Brain memory audit: " + "; ".join(issues[:6]))
else:
    print("CC Agent Brain memory audit report")
    for i in issues:
        print("- " + i)
