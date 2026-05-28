#!/usr/bin/env python3
"""UserPromptSubmit hook: suggest local Wiki retrieval when the prompt depends on history."""

from __future__ import annotations

import sys
from pathlib import Path

from _utils import read_stdin_json

data = read_stdin_json()

prompt = str(data.get("prompt") or "")
keywords = [
    "之前", "上次", "历史", "我们说过", "继续", "项目", "素材", "决策", "偏好", "记得", "查一下", "复盘",
    "previous", "last time", "project", "decision", "preference", "continue", "remember",
]
if not any(k.lower() in prompt.lower() for k in keywords):
    sys.exit(0)

root = Path.cwd()
candidates = [
    root / "memory" / "MEMORY.md",
    root / "memory" / "active-projects.md",
    root / "memory" / "retrieval-policy.md",
    root / "wiki" / "index.md",
    root / "wiki" / "projects",
    root / "wiki" / "decisions",
    root / "wiki" / "materials",
    root / "wiki" / "sessions",
]
existing = [str(p.relative_to(root)) for p in candidates if p.exists()]
if existing:
    print("CC Agent Brain retrieval hint: this prompt may depend on past context. Check: " + ", ".join(existing))
