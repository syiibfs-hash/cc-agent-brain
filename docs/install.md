# Installation Guide

## Recommended installation

Use the prompt in `prompts/install-from-github.md` or `prompts/install-from-local-package.md`.

## Manual installation

```bash
python installer/install.py --target /path/to/your/project
```

The installer merges skills, agents, and hooks without replacing `.claude/`.
It backs up `settings.json`, writes an install manifest, initializes
`.cc-agent-brain/brain.db`, and merges a local stdio MCP server into Claude
Code, Cursor, and Codex project config. See [MCP](mcp.md) for the exact shapes.

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

`update.py` re-runs `install.py`. A second run:

- overwrites framework files: `.claude/hooks/cc-agent-brain/**`,
  `.claude/skills/cc-agent-brain-*/**`, and `.claude/agents/cc-agent-brain-*.md`
- leaves `.cc-agent-brain/brain.db`, `memory/`, `wiki/`, `private/`, and
  existing template files untouched
- runs `brain_store.py --db <project>/.cc-agent-brain/brain.db init` even when
  the database already exists, so `BrainStore._migrate()` runs
- merges only the `cc-agent-brain` server into `.mcp.json`,
  `.cursor/mcp.json`, and `.codex/config.toml`
- merges hook entries into `.claude/settings.json` instead of replacing that file

Hook entries are not duplicated. `--dry-run` prints the same report and writes nothing.

## Uninstall

```bash
python installer/uninstall.py --target /path/to/your/project
```

The uninstaller preserves user-generated `memory/`, `wiki/`, `private/` and the
local engine database `.cc-agent-brain/brain.db`. It does not rewrite the MCP
client files, so other servers in those files cannot be removed by uninstall.
