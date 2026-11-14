# Install from Local Package Prompt

```text
You are helping me install CC Agent Brain into the current Claude Code project.

I have already downloaded the package locally.

Package path:
PASTE_THE_LOCAL_ZIP_OR_FOLDER_PATH_HERE

Please:
1. Inspect the package contents.
2. Extract it if it is a ZIP file.
3. Locate the CC Agent Brain installer or package directory.
4. Install it as an add-on to the current project.
5. Do not replace my existing `.claude/` directory.
6. Merge files into `.claude/` using the `cc-agent-brain` namespace. Refresh framework files already installed under that namespace.
7. Do not overwrite `memory/`, `wiki/`, `private/`, `templates/`, or `.cc-agent-brain/brain.db`.
8. Backup `.claude/settings.json` before editing it.
9. Merge hook settings instead of overwriting existing settings.
10. If `brain.db` already exists, still initialize it so the schema migrates.
11. Merge the local `cc-agent-brain` stdio MCP server into `.mcp.json`, `.cursor/mcp.json`, and `.codex/config.toml` without removing other servers.
12. Create `memory/`, `wiki/`, `private/`, and `templates/` if missing.
13. Keep my generated memory and Wiki content local.
14. After installation, show me what changed and whether onboarding is needed.
```
