#!/usr/bin/env python3
"""Utilities for safely merging CC Agent Brain hook settings."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict, List

HOOKS_TO_ADD = {
    "SessionStart": [
        {"hooks": [{"type": "command", "command": "{python} .claude/hooks/cc-agent-brain/session_start.py"}]}
    ],
    "UserPromptSubmit": [
        {"hooks": [
            {"type": "command", "command": "{python} .claude/hooks/cc-agent-brain/prompt_capture.py"},
            {"type": "command", "command": "{python} .claude/hooks/cc-agent-brain/wiki_context_hint.py"},
        ]}
    ],
    "PreCompact": [
        {"hooks": [{"type": "command", "command": "{python} .claude/hooks/cc-agent-brain/pre_compact_save.py"}]}
    ],
    "Stop": [
        {"hooks": [{"type": "command", "command": "{python} .claude/hooks/cc-agent-brain/memory_audit.py --light"}]}
    ],
}


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return {}
    return json.loads(text)


def dump_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _render_hook(hook: Dict[str, Any], python_command: str) -> Dict[str, Any]:
    rendered = copy.deepcopy(hook)
    for item in rendered.get("hooks", []):
        command = item.get("command")
        if isinstance(command, str):
            item["command"] = command.format(python=python_command)
    return rendered


def _hook_key(hook: Dict[str, Any]) -> str:
    return json.dumps(hook, sort_keys=True, ensure_ascii=False)


def merge_settings(existing: Dict[str, Any], python_command: str = "python") -> Dict[str, Any]:
    merged = copy.deepcopy(existing)
    hooks = merged.setdefault("hooks", {})
    for event_name, entries in HOOKS_TO_ADD.items():
        current: List[Dict[str, Any]] = hooks.setdefault(event_name, [])
        current_keys = {_hook_key(item) for item in current}
        for entry in entries:
            rendered = _render_hook(entry, python_command)
            key = _hook_key(rendered)
            if key not in current_keys:
                current.append(rendered)
                current_keys.add(key)
    return merged


def remove_cc_agent_brain_hooks(existing: Dict[str, Any]) -> Dict[str, Any]:
    merged = copy.deepcopy(existing)
    hooks = merged.get("hooks", {})
    for event_name, entries in list(hooks.items()):
        kept = []
        for entry in entries:
            text = json.dumps(entry, ensure_ascii=False)
            if "cc-agent-brain" not in text:
                kept.append(entry)
        if kept:
            hooks[event_name] = kept
        else:
            hooks.pop(event_name, None)
    if not hooks:
        merged.pop("hooks", None)
    return merged
