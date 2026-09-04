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

## Scope notes

- The server is read/write by design; run it against a project DB for project
  memory, or `--global` for the shared profile.
- It stays local (stdio, no listening port), consistent with local-first.
- Protocol version advertised: `2024-11-05`.
