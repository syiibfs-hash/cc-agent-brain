# Installation

The installer copies the `cc-agent-brain` namespace into a project, registers
Claude Code hooks, and merges one local stdio MCP server into Claude Code,
Cursor, and Codex project config. Auto-capture after install is still the
Claude Code hook loop. The MCP entries start `serve-mcp`. They do not capture
Cursor or Codex sessions.

## Install

From a clone of this repository:

```bash
python installer/install.py --target /path/to/your/project
```

Or use the prompt in `prompts/install-from-github.md` or
`prompts/install-from-local-package.md` inside Claude Code.

What a non-dry-run does:

- Overwrites framework files that already exist:
  `.claude/hooks/cc-agent-brain/**`, `.claude/skills/cc-agent-brain-*/**`, and
  `.claude/agents/cc-agent-brain-*.md`. Files outside that namespace, such as
  another skill or another agent, are not replaced. The `.claude/` directory
  itself is not replaced.
- Copies memory, wiki, and writing templates only when the destination file
  is missing. Existing files under `memory/`, `wiki/`, `private/`, and
  `templates/` stay. Those paths are omitted from the uninstall manifest.
- Backs up `.claude/settings.json` to
  `.claude/settings.backup.cc-agent-brain.json` when a settings file exists
  and that backup does not.
- Appends Claude Code hook entries that are not already present. It does not
  rewrite hook commands that are already in the file.
- Writes `.cc-agent-brain/install-manifest.json`, including `files_updated`
  and an `mcp` status for each client.
- Runs `brain_store.py --db <project>/.cc-agent-brain/brain.db init` whether
  or not the database file already exists. A new file gets `engine_state`
  `initialized`. An existing file gets `migrated`. `init` opens the file in
  place and calls `BrainStore._migrate()`, which creates missing tables. The
  file is not replaced or deleted, and rows already stored in it stay.
- Merges one stdio server named `cc-agent-brain` into `.mcp.json`,
  `.cursor/mcp.json`, and `.codex/config.toml`. Other servers in those files
  stay. A file that does not parse is left untouched. Those entries still
  launch `serve-mcp` without `--global`, so they use the project database.
  They do not create `~/.cc-agent-brain/`. To point the three clients at the
  shared global library, add `--global` and `CC_AGENT_BRAIN_WRITER` as in
  [`docs/mcp.md`](mcp.md). Shapes of the default merge are in that doc too.

## Dry run

```bash
python installer/install.py --target /path/to/your/project --dry-run
```

Dry run prints a manifest and does not write settings, the database, the
manifest, framework files, or MCP config. `engine_state` is `skipped`. Each
MCP status in the report is `dry-run`.

## After installation

1. Restart Claude Code, or check `/hooks`, so the merged hook entries load.
2. SessionStart asks for onboarding when `memory/profile.md` and the other
   template files are missing or empty.
3. Check the project database:

```bash
python .claude/hooks/cc-agent-brain/brain_store.py stats
```

Auto-capture after this install is the Claude Code hook loop. Cursor and
Codex receive an MCP entry for `serve-mcp` and no capture hooks.

## Upgrade (`update.py`)

```bash
python installer/update.py --target /path/to/your/project
```

`update.py` executes `install.py` with the same arguments. That is the whole
wrapper. A second run does the upgrade described above: framework files are
overwritten, user data stays, `init` runs against the existing database, and
the three MCP entries are merged again. When an entry already matches,
its status is `unchanged`. Hook entries are not duplicated.

## Uninstall

```bash
python installer/uninstall.py --target /path/to/your/project
```

The uninstaller removes framework files recorded in the manifest and strips
hook entries whose JSON contains `cc-agent-brain`. It keeps `memory/`,
`wiki/`, `private/`, and `.cc-agent-brain/brain.db`. It does not rewrite
`.mcp.json`, `.cursor/mcp.json`, or `.codex/config.toml`, so servers in those
files, including `cc-agent-brain`, remain until you edit the file.
