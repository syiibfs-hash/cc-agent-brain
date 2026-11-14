#!/usr/bin/env python3
"""Install or upgrade CC Agent Brain in an existing project.

This installer is intentionally conservative:
- It never replaces the whole `.claude/` directory.
- It refreshes framework files under the `cc-agent-brain` namespace.
- It never overwrites `memory/`, `wiki/`, `private/`, user templates, or `brain.db`.
- It backs up `.claude/settings.json` before merging hook settings.
- It records installed files in `.cc-agent-brain/install-manifest.json`.
- It runs `brain_store.py init` even when `brain.db` already exists, so `_migrate()` runs.
- It merges one local stdio MCP server into Claude Code, Cursor, and Codex config.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from mcp_config import write_mcp_configs
from merge_settings import dump_json, load_json, merge_settings

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "package"
VERSION = "0.2.0"


def is_framework_file(target: Path, dst: Path) -> bool:
    """Framework files are replaced on upgrade. User memory and templates are not."""
    try:
        parts = dst.resolve().relative_to(target.resolve()).parts
    except ValueError:
        return False
    if len(parts) >= 4 and parts[0] == ".claude" and parts[1] == "hooks" and parts[2] == "cc-agent-brain":
        return True
    if len(parts) >= 3 and parts[0] == ".claude" and parts[1] == "skills" and parts[2].startswith("cc-agent-brain-"):
        return True
    if (
        len(parts) == 3
        and parts[0] == ".claude"
        and parts[1] == "agents"
        and parts[2].startswith("cc-agent-brain-")
        and parts[2].endswith(".md")
    ):
        return True
    return False


def copy_file(
    src: Path,
    dst: Path,
    dry_run: bool,
    files_added: List[str],
    files_skipped: List[str],
    files_updated: List[str],
    overwrite: bool,
) -> None:
    rel_dst = str(dst)
    existed = dst.exists()
    if existed and not overwrite:
        files_skipped.append(rel_dst)
        return
    if not dry_run:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    if existed:
        files_updated.append(rel_dst)
    else:
        files_added.append(rel_dst)


def copy_tree_contents(
    src_dir: Path,
    dst_dir: Path,
    target: Path,
    dry_run: bool,
    files_added: List[str],
    files_skipped: List[str],
    files_updated: List[str],
) -> None:
    if not src_dir.exists():
        return
    for src in src_dir.rglob("*"):
        if src.is_dir():
            continue
        if "__pycache__" in src.parts or src.suffix in {".pyc", ".pyo"}:
            continue
        rel = src.relative_to(src_dir)
        dst = dst_dir / rel
        copy_file(
            src,
            dst,
            dry_run,
            files_added,
            files_skipped,
            files_updated,
            overwrite=is_framework_file(target, dst),
        )


def ensure_dir(path: Path, dry_run: bool, dirs_created: List[str]) -> None:
    if not path.exists():
        if not dry_run:
            path.mkdir(parents=True, exist_ok=True)
        dirs_created.append(str(path))


def init_engine(target: Path, dry_run: bool) -> str:
    """Create the project database, or migrate it when it already exists.

    ``BrainStore`` calls ``_migrate()`` from its constructor. ``init`` always
    constructs one, so an upgrade must run it against the existing file.
    Returning early when ``brain.db`` exists would leave the old schema in place.
    The database file is opened in place and is never replaced or deleted.
    """
    engine = (target / ".claude" / "hooks" / "cc-agent-brain" / "brain_store.py").resolve()
    db_path = (target / ".cc-agent-brain" / "brain.db").resolve()
    if dry_run or not engine.exists():
        return "skipped"
    existed = db_path.exists()
    try:
        result = subprocess.run(
            [sys.executable, str(engine), "--db", str(db_path), "init"],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=str(target),
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unavailable"
    if result.returncode != 0:
        return "unavailable"
    return "migrated" if existed else "initialized"


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
    files_updated: List[str] = []
    dirs_created: List[str] = []

    for d in [claude_dir, claude_dir / "skills", claude_dir / "agents", claude_dir / "hooks" / "cc-agent-brain"]:
        ensure_dir(d, args.dry_run, dirs_created)

    # Framework trees are refreshed. Memory, wiki, and templates are not.
    copy_tree_contents(
        PACKAGE / "claude" / "skills", claude_dir / "skills", target, args.dry_run, files_added, files_skipped, files_updated
    )
    copy_tree_contents(
        PACKAGE / "claude" / "agents", claude_dir / "agents", target, args.dry_run, files_added, files_skipped, files_updated
    )
    copy_tree_contents(
        PACKAGE / "claude" / "hooks", claude_dir / "hooks", target, args.dry_run, files_added, files_skipped, files_updated
    )

    # Local brain directories.
    for d in [target / "memory", target / "wiki", target / "wiki" / "sessions", target / "wiki" / "projects", target / "wiki" / "materials", target / "wiki" / "decisions", target / "wiki" / "prompts", target / "wiki" / "concepts", target / "wiki" / "tasks", target / "wiki" / "archive", target / "private", target / "templates"]:
        ensure_dir(d, args.dry_run, dirs_created)

    copy_tree_contents(
        PACKAGE / "memory_templates", target / "memory", target, args.dry_run, files_added, files_skipped, files_updated
    )
    copy_tree_contents(
        PACKAGE / "wiki_templates", target / "wiki", target, args.dry_run, files_added, files_skipped, files_updated
    )
    copy_tree_contents(
        PACKAGE / "templates", target / "templates", target, args.dry_run, files_added, files_skipped, files_updated
    )

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

    # Initialize or migrate after the framework copy, so the new engine runs.
    engine_state = init_engine(target, args.dry_run)
    mcp = write_mcp_configs(target, python_command=args.python_command, dry_run=args.dry_run)

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
    files_updated = [f for f in files_updated if not _in_user_data(str(f))]
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
    # Overwritten framework files stay tracked so uninstall still removes them.
    merged_added = sorted(set(files_added + files_updated + existing_added))
    merged_skipped = sorted(set(s for s in files_skipped + existing_skipped if s not in merged_added))
    merged_dirs = sorted(set(dirs_created + existing_dirs))
    manifest: Dict[str, object] = {
        "version": VERSION,
        "installed_at": datetime.now().isoformat(timespec="seconds"),
        "target": str(target),
        "files_added": merged_added,
        "files_updated": sorted(set(files_updated)),
        "files_skipped": merged_skipped,
        "dirs_created": merged_dirs,
        "settings_path": str(settings_path),
        "settings_backup": str(settings_backup),
        "settings_merged": settings_merged,
        "engine_state": engine_state,
        "mcp": mcp,
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
