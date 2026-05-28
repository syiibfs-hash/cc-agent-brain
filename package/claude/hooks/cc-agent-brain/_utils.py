from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def read_stdin_json() -> Dict[str, Any]:
    import sys
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
