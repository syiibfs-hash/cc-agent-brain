# Installation Guide

## Recommended installation

Use the prompt in `prompts/install-from-github.md` or `prompts/install-from-local-package.md`.

## Manual installation

```bash
python installer/install.py --target /path/to/your/project
```

The installer merges skills/agents/hooks without replacing `.claude/`, backs up
`settings.json`, writes an install manifest, and initializes the local engine
database `.cc-agent-brain/brain.db`.

## Dry run

```bash
python installer/install.py --target /path/to/your/project --dry-run
```

## After installation

1. Restart Claude Code or check `/hooks` to confirm hook settings were loaded.
2. Run onboarding (the SessionStart hook prompts you) so `memory/` is populated.
3. Verify the engine:

```bash
python .claude/hooks/cc-agent-brain/brain_store.py stats
```

## Update

```bash
python installer/update.py --target /path/to/your/project
```

Re-running the installer is idempotent: existing user files are kept and hook
entries are not duplicated.

## Uninstall

```bash
python installer/uninstall.py --target /path/to/your/project
```

The uninstaller preserves user-generated `memory/`, `wiki/`, `private/` and the
local engine database `.cc-agent-brain/brain.db`.
