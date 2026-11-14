#!/usr/bin/env python3
"""Update CC Agent Brain by re-running the installer.

install.py refreshes framework files, migrates an existing brain.db, and
merges the Claude Code, Cursor, and Codex MCP entries. User memory, wiki,
private data, templates, and the database file stay in place. This wrapper
does not add a second copy path.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    installer = Path(__file__).with_name("install.py")
    return subprocess.call([sys.executable, str(installer), *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(main())
