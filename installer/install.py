#!/usr/bin/env python3
"""Install CC Agent Brain into an existing Claude Code project.

This installer is intentionally conservative:
- It never replaces the whole `.claude/` directory.
- It installs files under the `cc-agent-brain` namespace.
- It backs up `.claude/settings.json` before merging hook settings.
- It records installed files in `.cc-agent-brain/install-manifest.json`.
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from merge_settings import dump_json, load_json, merge_settings

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "package"


def copy_file(src: Path, dst: Path, dry_run: bool, files_added: List[str], files_skipped: List[str]) -> None:
    rel_dst = str(dst)
    if dst.exists():
        files_skipped.append(rel_dst)
        return
    if not dry_run:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    files_added.append(rel_dst)


def copy_tree_contents(src_dir: Path, dst_dir: Path, dry_run: bool, files_added: List[str], files_skipped: List[str]) -> None:
    if not src_dir.exists():
        return
    for src in src_dir.rglob("*"):
        if src.is_dir():
            continue
        if "__pycache__" in src.parts or src.suffix in {".pyc", ".pyo"}:
            continue
        rel = src.relative_to(src_dir)
        dst = dst_dir / rel
        copy_file(src, dst, dry_run, files_added, files_skipped)


def ensure_dir(path: Path, dry_run: bool, dirs_created: List[str]) -> None:
    if not path.exists():
        if not dry_run:
            path.mkdir(parents=True, exist_ok=True)
        dirs_created.append(str(path))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", default=".", help="Target Claude Code project directory")
    parser.add_argument("--python-command", default="python", help="Python command used in Claude Code hooks")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing files")
    args = parser.parse_args()

    target = Path(args.target).resolve()
    claude_dir = target / ".claude"

    files_added: List[str] = []
    files_skipped: List[str] = []
    dirs_created: List[str] = []

    for d in [claude_dir, claude_dir / "skills", claude_dir / "agents", claude_dir / "hooks" / "cc-agent-brain"]:
        ensure_dir(d, args.dry_run, dirs_created)

    copy_tree_contents(PACKAGE / "claude" / "skills", claude_dir / "skills", args.dry_run, files_added, files_skipped)
    copy_tree_contents(PACKAGE / "claude" / "agents", claude_dir / "agents", args.dry_run, files_added, files_skipped)
    copy_tree_contents(PACKAGE / "claude" / "hooks", claude_dir / "hooks", args.dry_run, files_added, files_skipped)

    # Local brain directories.
    for d in [target / "memory", target / "wiki", target / "wiki" / "sessions", target / "wiki" / "projects", target / "wiki" / "materials", target / "wiki" / "decisions", target / "wiki" / "prompts", target / "wiki" / "concepts", target / "wiki" / "tasks", target / "wiki" / "archive", target / "private", target / "templates"]:
        ensure_dir(d, args.dry_run, dirs_created)

    copy_tree_contents(PACKAGE / "memory_templates", target / "memory", args.dry_run, files_added, files_skipped)
    copy_tree_contents(PACKAGE / "wiki_templates", target / "wiki", args.dry_run, files_added, files_skipped)
    copy_tree_contents(PACKAGE / "templates", target / "templates", args.dry_run, files_added, files_skipped)

    # Merge settings.
    settings_path = claude_dir / "settings.json"
    settings_backup = claude_dir / "settings.backup.cc-agent-brain.json"
    settings_merged = False
    if not args.dry_run:
        if settings_path.exists() and not settings_backup.exists():
            shutil.copy2(settings_path, settings_backup)
        existing = load_json(settings_path)
        merged = merge_settings(existing, python_command=args.python_command)
        dump_json(settings_path, merged)
        settings_merged = True
    else:
        settings_merged = True

    # User-data directories contain templates that users will personalise.
    # They must not be tracked in the manifest, otherwise the uninstaller
    # would delete user-modified content.
    _USER_DATA_DIRS = {"memory", "wiki", "templates", "private"}

    def _in_user_data(file_path: str) -> bool:
        try:
            rel = Path(file_path).relative_to(target)
            return len(rel.parts) > 0 and rel.parts[0] in _USER_DATA_DIRS
        except ValueError:
            return False

    files_added = [f for f in files_added if not _in_user_data(str(f))]
    files_skipped = [f for f in files_skipped if not _in_user_data(str(f))]
    dirs_created = [d for d in dirs_created if Path(d).relative_to(target).parts[0] not in _USER_DATA_DIRS]

    # Manifest — merge with existing to survive idempotent re-installs.
    manifest_dir = target / ".cc-agent-brain"
    manifest_path = manifest_dir / "install-manifest.json"
    existing_added: List[str] = []
    existing_skipped: List[str] = []
    existing_dirs: List[str] = []
    if manifest_path.exists():
        try:
            prev = json.loads(manifest_path.read_text(encoding="utf-8"))
            existing_added = [str(x) for x in prev.get("files_added", [])]
            existing_skipped = [str(x) for x in prev.get("files_skipped", [])]
            existing_dirs = [str(x) for x in prev.get("dirs_created", [])]
        except (json.JSONDecodeError, KeyError):
            pass
    merged_added = sorted(set(files_added + existing_added))
    merged_skipped = sorted(set(s for s in files_skipped + existing_skipped if s not in merged_added))
    merged_dirs = sorted(set(dirs_created + existing_dirs))
    manifest: Dict[str, object] = {
        "version": "0.1.0",
        "installed_at": datetime.now().isoformat(timespec="seconds"),
        "target": str(target),
        "files_added": merged_added,
        "files_skipped": merged_skipped,
        "dirs_created": merged_dirs,
        "settings_path": str(settings_path),
        "settings_backup": str(settings_backup),
        "settings_merged": settings_merged,
    }
    if not args.dry_run:
        manifest_dir.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    print("\nCC Agent Brain installation preview complete." if args.dry_run else "\nCC Agent Brain installed.")
    print("Restart Claude Code or check /hooks so new hooks are loaded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
