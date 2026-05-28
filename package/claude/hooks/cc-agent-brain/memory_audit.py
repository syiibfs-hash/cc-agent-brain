#!/usr/bin/env python3
"""Lightweight memory audit hook."""

from __future__ import annotations

import argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--light", action="store_true")
args = parser.parse_args()

root = Path.cwd()
memory = root / "memory"
wiki = root / "wiki"
issues = []

for file_name in ["MEMORY.md", "profile.md", "preferences.md", "active-projects.md", "retrieval-policy.md"]:
    p = memory / file_name
    if not p.exists() or not p.read_text(encoding="utf-8").strip():
        issues.append(f"missing_or_empty:{p.relative_to(root)}")

session_dir = wiki / "sessions"
if session_dir.exists():
    session_files = list(session_dir.glob("*.md"))
    if len(session_files) >= 5:
        issues.append("many_session_notes: consider running cc-agent-brain-memory-distill")

if issues:
    print("CC Agent Brain memory audit: " + "; ".join(issues))
else:
    print("CC Agent Brain memory audit: no urgent issues found.")
