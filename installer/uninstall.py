#!/usr/bin/env python3
"""Uninstall CC Agent Brain from a target project."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from merge_settings import dump_json, load_json, remove_cc_agent_brain_hooks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", default=".")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    target = Path(args.target).resolve()
    manifest_path = target / ".cc-agent-brain" / "install-manifest.json"
    if not manifest_path.exists():
        print("No install manifest found. Nothing removed.")
        return 1

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    removed = []
    skipped = []

    for file_name in manifest.get("files_added", []):
        path = Path(file_name)
        if path.exists() and path.is_file():
            if not args.dry_run:
                path.unlink()
            removed.append(str(path))
        else:
            skipped.append(str(path))

    settings_path = target / ".claude" / "settings.json"
    settings_backup = target / ".claude" / "settings.backup.before-uninstall-cc-agent-brain.json"
    if settings_path.exists():
        if not args.dry_run:
            shutil.copy2(settings_path, settings_backup)
            settings = load_json(settings_path)
            cleaned = remove_cc_agent_brain_hooks(settings)
            dump_json(settings_path, cleaned)

    install_backup = target / ".claude" / "settings.backup.cc-agent-brain.json"
    if install_backup.exists():
        if not args.dry_run:
            install_backup.unlink()
        removed.append(str(install_backup))

    if not args.dry_run:
        manifest_path.unlink(missing_ok=True)

    print(json.dumps({"removed": removed, "skipped": skipped, "preserved": ["memory/", "wiki/", "private/"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
