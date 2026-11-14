# Install from GitHub Prompt

```text
You are helping me install CC Agent Brain into the current Claude Code project.

Goal:
Install CC Agent Brain as an add-on to the existing project. Do not replace or overwrite my existing `.claude/` directory.

Source:
GitHub repository: https://github.com/syiibfs-hash/cc-agent-brain

Installation requirements:
1. Download or clone the repository to a temporary directory.
2. Inspect the current project structure.
3. If `.claude/` already exists, merge CC Agent Brain files into it.
4. Refresh existing CC Agent Brain framework files (`.claude/hooks/cc-agent-brain/**`, `.claude/skills/cc-agent-brain-*/**`, `.claude/agents/cc-agent-brain-*.md`). Do not overwrite `memory/`, `wiki/`, `private/`, `templates/`, or `.cc-agent-brain/brain.db`.
5. Add all CC Agent Brain skills under `.claude/skills/cc-agent-brain-*`.
6. Add all CC Agent Brain agents under `.claude/agents/cc-agent-brain-*.md`.
7. Add all CC Agent Brain hooks under `.claude/hooks/cc-agent-brain/`.
8. Merge hook configuration into `.claude/settings.json` instead of replacing the file.
9. If `brain.db` already exists, still run `brain_store.py --db <path> init` so the existing database is migrated.
10. Merge a stdio MCP server named `cc-agent-brain` into project `.mcp.json`, `.cursor/mcp.json`, and `.codex/config.toml`. Do not remove other MCP servers.
11. Before modifying `.claude/settings.json`, create a backup named `.claude/settings.backup.cc-agent-brain.json`.
12. Create local folders if they do not exist: `memory/`, `wiki/`, `private/`, `templates/`.
13. Do not commit or upload my generated `memory/`, `wiki/`, or `private/` content.
14. After installation, summarize files added, settings merged, files skipped, and next steps.

After installation, trigger the onboarding flow if `memory/profile.md` or `memory/preferences.md` is missing.
```
