# Installation Guide

## Recommended installation

Use the prompt in `prompts/install-from-github.md` or `prompts/install-from-local-package.md`.

## Manual installation

```bash
python installer/install.py --target /path/to/your/project
```

## Dry run

```bash
python installer/install.py --target /path/to/your/project --dry-run
```

## After installation

Restart Claude Code or check `/hooks` to confirm that hook settings were loaded.

## Uninstall

```bash
python installer/uninstall.py --target /path/to/your/project
```

The uninstaller preserves user-generated `memory/`, `wiki/`, and `private/` folders.
