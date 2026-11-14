# MCP server

`brain_store.py serve-mcp` is a dependency-free JSON-RPC 2.0 process on stdio.
It reads and writes one SQLite file. It does not capture editor sessions.
Auto-capture remains the Claude Code hooks in `.claude/settings.json`.

The same process speaks two MCP eras. Which era a request uses depends on
`params._meta`, and on whether this process has already seen a modern envelope.

## Legacy era: `2024-11-05`

A request is legacy when `params._meta` is missing, is not an object, or does
not contain both of these keys:

- `io.modelcontextprotocol/protocolVersion`
- `io.modelcontextprotocol/clientCapabilities`

On that path, while this process has not yet seen a modern envelope:

| Method | Result |
|--------|--------|
| `initialize` | `protocolVersion` `2024-11-05`, `capabilities` `{ "tools": {} }`, `serverInfo` `{ "name": "cc-agent-brain", "version": "2" }`. `"2"` is `SCHEMA_VERSION`, not the product version |
| `ping` | `{}` |
| `tools/list` | `{ "tools": [ ...five tools... ] }` with no `resultType` and no modern `_meta` |
| `tools/call` | the tool handler result, with no `resultType` and no modern `_meta` |

Any other method returns JSON-RPC `-32601`. A message with no `id` gets no
response, including `notifications/initialized`.

## Modern era: `2026-07-28`

A request is modern when `params._meta` contains both keys above, the version
value is a string, and the capabilities value is an object. That classification
sticks for the rest of this stdio process, including when the version string is
not `2026-07-28`.

When the version string is `2026-07-28`:

| Method | Result |
|--------|--------|
| `server/discover` | `resultType` `"complete"`, `supportedVersions` `["2026-07-28", "2024-11-05"]`, `capabilities` `{ "tools": {} }`, `instructions`, `ttlMs` `3600000`, `cacheScope` `"public"`, and `_meta` |
| `tools/list` | `resultType` `"complete"`, the same five tools in `MCP_TOOLS` order, `ttlMs` `3600000`, `cacheScope` `"public"`, and `_meta`. No `nextCursor` |
| `tools/call` | the tool handler result plus `resultType` `"complete"` and `_meta`. This result does not add `ttlMs` or `cacheScope` |

`_meta` on those results is:

```json
{
  "io.modelcontextprotocol/serverInfo": {
    "name": "cc-agent-brain",
    "version": "0.2.0"
  }
}
```

`0.2.0` is `PRODUCT_VERSION`. It is not the schema id `"2"` returned by legacy
`initialize`.

`initialize` and `ping` inside a `2026-07-28` envelope return `-32601`. The
server does not answer them with the legacy payloads.

Any other version string on a modern envelope returns `-32022` with
`data.supported` equal to `["2026-07-28", "2024-11-05"]` and `data.requested`
equal to that string. The process still counts as modern after that error, so
a later `initialize` is also `-32022` (its `data.requested` is
`params.protocolVersion` when that value is a string, otherwise `""`).

Both envelope keys present with the wrong types (version not a string, or
capabilities not an object) return `-32602`. That request is not served as
`initialize`. One of the two keys alone stays on the legacy path.

A process that only ever sends `initialize` keeps the legacy handshake. The
sticky rejection applies only after a modern envelope on that same process.

## What this server does not implement

Resources, prompts, sampling, logging, completions, and pagination are absent.
`tools/list` has no `nextCursor`.

This repository does not ship a Cursor, Codex, Gemini CLI, or Claude Desktop
config, and it does not test those products. A client can open the process
when it speaks one of the two eras above. Opening it does not start
auto-capture.

## Start

```bash
python .claude/hooks/cc-agent-brain/brain_store.py serve-mcp
# shared global library (brain.db + library.md under the global directory):
python .claude/hooks/cc-agent-brain/brain_store.py --global serve-mcp
# same library, explicit directory (overrides CC_AGENT_BRAIN_GLOBAL_DIR):
python .claude/hooks/cc-agent-brain/brain_store.py --global-dir ~/.cc-agent-brain --global serve-mcp
# one SQLite file, not the shared pair (--db wins over --global):
python /abs/path/to/brain_store.py --db /abs/path/to/brain.db serve-mcp
```

The server speaks newline-delimited JSON-RPC itself. No MCP SDK is imported.

## Tools

The tool list is the same on both eras.

| Tool | Arguments | What the handler does |
|------|-----------|------------------------|
| `brain_search` | `query`, `k?`, `layer?` | lexical FTS search (BM25 lists fused with RRF) |
| `brain_add_memory` | `title`, `body`, `layer?`, `confidence?`, `tags?`, `source?`, `writer?` | insert one active memory row. No `supersedes` argument on this tool. `writer` is stored on the row |
| `brain_forget` | `id` | set that row to `expired` (row kept, removed from the FTS index). The original `writer` stays |
| `brain_timeline` | `limit?` | recent memory rows by `updated_at`, every status, including `writer`. Not an as-of query |
| `brain_stats` | — | counts by kind, layer, status, and writer |

`brain_search` is the same `BrainStore.search` as the CLI: keyword lists only,
no vector channel, no past-timestamp argument. Hits include the stored
`writer`.

`writer` on `brain_add_memory` is the caller-supplied identity. When the
argument is omitted, the process uses `CC_AGENT_BRAIN_WRITER`, then
`unspecified`. The server does not read the client name out of the handshake
and does not decide Cursor versus Codex for you. Put a different
`CC_AGENT_BRAIN_WRITER` in each client's server environment if you want the
rows labeled. `source` is still provenance (`mcp` by default on this tool),
not the writer.

A write through a `serve-mcp` that opened the global database also rewrites
`<global-dir>/library.md`. That file lists active memories and counts events
by kind and writer. It does not copy event text.

## Pointing clients at the shared library

The shared directory defaults to `~/.cc-agent-brain` (`brain.db` and
`library.md`). `CC_AGENT_BRAIN_GLOBAL_DIR` or `--global-dir` moves both files.
Project `.cc-agent-brain/brain.db` is unchanged.

Give every client the same directory and `--global`, and a writer label you
choose. Example shape for Claude Code `.mcp.json` and Cursor `.cursor/mcp.json`
(Cursor keeps `"type": "stdio"`):

```json
{
  "mcpServers": {
    "cc-agent-brain": {
      "command": "python",
      "args": ["/abs/path/to/brain_store.py", "--global", "serve-mcp"],
      "env": {
        "CC_AGENT_BRAIN_WRITER": "claude-code",
        "CC_AGENT_BRAIN_GLOBAL_DIR": "/home/you/.cc-agent-brain"
      }
    }
  }
}
```

Use `"cursor"` or `"codex"` (or any other label) as `CC_AGENT_BRAIN_WRITER`
on the other clients. Codex can pass the same variables on the server
environment, for example:

```toml
[mcp_servers.cc-agent-brain]
command = "python"
args = ["/abs/path/to/brain_store.py", "--global", "serve-mcp"]
cwd = "/abs/path/to/project"

[mcp_servers.cc-agent-brain.env]
CC_AGENT_BRAIN_WRITER = "codex"
CC_AGENT_BRAIN_GLOBAL_DIR = "/home/you/.cc-agent-brain"
```

`CC_AGENT_BRAIN_GLOBAL_DIR` may be omitted when the default directory is the
one you want. A tool call can still pass `writer` and that value wins over
the environment variable. This is one SQLite file on this machine. It is not
a daemon and it does not sync to another computer.

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

## Scope

- One process, one database path (`--db`, `--global`, or the project default
  `.cc-agent-brain/brain.db`). The installer entries above launch `serve-mcp`
  against the project file. The shared-library examples further up are how
  you point those same clients at one global file instead. Separate processes
  can open that file. This is not a shared daemon.
- stdio only. The server does not listen on a port.
- Write tools are enabled. There is no read-only mode.
