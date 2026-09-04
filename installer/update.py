#!/usr/bin/env python3
"""Update CC Agent Brain by re-running the installer.

This is intentionally simple. It delegates to install.py so the same
safe merge rules are used.
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
