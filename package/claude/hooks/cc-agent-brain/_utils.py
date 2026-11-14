from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Claude Code hooks are this code path. Other clients are not inferred.
HOOK_WRITER = "claude-code"
WRITER_ENV = "CC_AGENT_BRAIN_WRITER"

HOOK_DIR = Path(__file__).resolve().parent
BRAIN_SCRIPT = HOOK_DIR / "brain_store.py"


def read_stdin_json() -> Dict[str, Any]:
    raw_bytes = sys.stdin.buffer.read()
    if not raw_bytes:
        return {}
    raw = raw_bytes.decode("utf-8", errors="replace").strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw_stdin": raw}


def project_root() -> Path:
    return Path.cwd()


def ensure_text_file(path: Path, default: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(default, encoding="utf-8")


def brain_cli(args: List[str], stdin_text: Optional[str] = None, timeout: float = 8.0) -> Optional[Any]:
    """Invoke brain_store.py in a subprocess. Never raises — hooks must not
    block the user's prompt if the engine is unavailable. Returns parsed JSON
    on success, raw text for --human, or None on any failure."""
    if not BRAIN_SCRIPT.exists():
        return None
    try:
        proc = subprocess.run(
            [sys.executable, str(BRAIN_SCRIPT), *args],
            input=stdin_text,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    out = (proc.stdout or "").strip()
    if not out:
        return None
    if "--human" in args:
        return out
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return out


def hook_writer(explicit: Optional[str] = None) -> str:
    """Identity these Claude Code hooks record.

    An explicit value wins, then ``CC_AGENT_BRAIN_WRITER``, then ``claude-code``.
    The last one names this hook code path. It is not a guess about Cursor or Codex.
    """
    if explicit is not None and str(explicit).strip():
        return " ".join(str(explicit).split())
    env = os.environ.get(WRITER_ENV, "").strip()
    if env:
        return " ".join(env.split())
    return HOOK_WRITER


def brain_event(
    kind: str,
    content: str,
    tags: Optional[List[str]] = None,
    source: str = "hook",
    writer: Optional[str] = None,
) -> Optional[Any]:
    args = ["event", "--kind", kind, "--content", content, "--source", source, "--writer", hook_writer(writer)]
    if tags:
        args += ["--tags", ",".join(tags)]
    return brain_cli(args)


def brain_search_human(query: str, k: int = 6) -> str:
    res = brain_cli(["search", query, "--k", str(k), "--human"])
    return res if isinstance(res, str) else ""
