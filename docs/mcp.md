# MCP Server (cross-tool memory)

The engine ships a minimal, dependency-free **Model Context Protocol** server
(JSON-RPC 2.0 over stdio). The same local memory can therefore serve Claude
Code, Claude Desktop, Cursor, Codex, Gemini CLI or any MCP-compatible client —
the memory is no longer locked into one editor.

## Start

```bash
python .claude/hooks/cc-agent-brain/brain_store.py serve-mcp
# global store instead:
python .claude/hooks/cc-agent-brain/brain_store.py --global serve-mcp
# explicit path:
python /abs/path/to/brain_store.py --db /abs/path/to/brain.db serve-mcp
```

No SDK is required: the server speaks newline-delimited JSON-RPC directly.

## Exposed tools

| Tool | Arguments | Purpose |
|------|-----------|---------|
| `brain_search` | `query`, `k?`, `layer?` | BM25 search over memories + events |
| `brain_add_memory` | `title`, `body`, `layer?`, `confidence?`, `tags?`, `source?` | persist a versioned memory |
| `brain_forget` | `id` | mark a memory expired (history retained) |
| `brain_timeline` | `limit?` | recent memory changes incl. superseded history |
| `brain_stats` | — | size and coverage summary |

## Example client config

Claude Desktop / other stdio MCP clients (adjust the absolute paths):

```json
{
  "mcpServers": {
    "cc-agent-brain": {
      "command": "python",
      "args": ["/abs/path/to/.claude/hooks/cc-agent-brain/brain_store.py", "serve-mcp"]
    }
  }
}
```

## What the installer writes

`installer/install.py` (and `update.py`, which only calls it) merges one
stdio server named `cc-agent-brain` into three project files. Other servers
in those files are left in place. JSON comments outside strings are accepted
on read, and a URL such as `https://example.com` is left intact. The file is
rewritten as plain JSON. A file that still does not parse is left untouched.

The server selects `.cc-agent-brain/brain.db` from its process working
directory. Codex sets `cwd` to the project. Claude Code and Cursor are given
the same `serve-mcp` command; this installer does not add a `--db` argument,
because the Claude Code stdio shape below has none.

### Claude Code — project `.mcp.json`

[Claude Code MCP](https://code.claude.com/docs/en/mcp) stores project servers
in `.mcp.json`. A stdio entry is `command` plus `args`. Omitting `type` means
stdio. An entry with `url` and no `type` is a configuration error, so the
installer never writes a URL server.

```json
{
  "mcpServers": {
    "cc-agent-brain": {
      "command": "python",
      "args": ["/abs/path/to/project/.claude/hooks/cc-agent-brain/brain_store.py", "serve-mcp"]
    }
  }
}
```

### Cursor — project `.cursor/mcp.json`

[Cursor MCP](https://cursor.com/docs/mcp) reads project config from
`.cursor/mcp.json`. The STDIO reference requires `type`, `command`, and
`args`. Some overview examples omit `type`; the installer follows the STDIO
reference and writes `"type": "stdio"`. The script path uses
`${workspaceFolder}`, which Cursor resolves to the directory that contains
`.cursor/mcp.json`. User-level `~/.cursor/mcp.json` is not written, because
this database belongs to one project.

```json
{
  "mcpServers": {
    "cc-agent-brain": {
      "type": "stdio",
      "command": "python",
      "args": ["${workspaceFolder}/.claude/hooks/cc-agent-brain/brain_store.py", "serve-mcp"]
    }
  }
}
```

### Codex — project `.codex/config.toml`

The [Codex config sample](https://learn.chatgpt.com/docs/config-file/config-sample.md)
shows `~/.codex/config.toml` and also a project-scoped `.codex/config.toml`.
Project config is a higher layer than the user file and is loaded only for a
trusted project. The installer writes the project file so this server stays
with this project's database and the user file is not edited. The merge
updates only `[mcp_servers.cc-agent-brain]`. It does not use JSON.

```toml
[mcp_servers.cc-agent-brain]
command = "python"
args = ["/abs/path/to/project/.claude/hooks/cc-agent-brain/brain_store.py", "serve-mcp"]
cwd = "/abs/path/to/project"
```

## Scope notes

- The server is read/write by design; run it against a project DB for project
  memory, or `--global` for the shared profile.
- It stays local (stdio, no listening port), consistent with local-first.
- Dual-era protocol on the same stdio process:
  - Legacy clients send `initialize` and receive `protocolVersion`
    `2024-11-05`, `capabilities.tools`, and `serverInfo`.
  - Modern clients (MCP `2026-07-28`) send `io.modelcontextprotocol/protocolVersion`
    and `io.modelcontextprotocol/clientCapabilities` on each request. The
    server implements `server/discover` and puts `resultType: "complete"` on
    modern `tools/list` and `tools/call` results. A version other than
    `2026-07-28` on that envelope returns JSON-RPC `-32022` with
    `data.supported` and `data.requested`.
  - Once a valid modern envelope has been seen, a later `initialize` is
    rejected. Legacy clients that speak only `initialize` are unaffected.
  - `serverInfo` in modern `_meta` uses the product version (`0.2.0`), not the
    SQLite schema version.
