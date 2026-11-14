# Architecture

CC Agent Brain is an installable add-on that stores Claude Code session text
in a local SQLite file and can print keyword matches back into Claude Code.
It merges files under the `cc-agent-brain` namespace and does not replace
`.claude/`.

## What runs today

```text
Claude Code hooks only
        ↓
append-only events (SQLite) + Markdown notes under wiki/ and memory/
        ↓
long-term memory rows only after an explicit `memory add`
        ↓
FTS5 bm25() lists fused with RRF (lexical paths only)
        ↓
Claude Code UserPromptSubmit hook prints those hits
        ↓
optional stdio process: MCP 2024-11-05 via initialize, and 2026-07-28 via _meta
```

## Current limits

- Auto-capture is the Claude Code hook set below. This repository has no
  Cursor, Codex, Gemini CLI, or Claude Desktop capture integration.
- RRF fuses FTS lists (project memories, project events, and the global file's
  memories and events when `~/.cc-agent-brain/brain.db` exists). It does not
  fuse a vector ranker. No vector index is built or queried.
- Memory rows store `valid_from`, `valid_to`, `created_at`, and `updated_at`.
  Search returns `status='active'` rows. There is no as-of query.
- `serve-mcp` speaks both MCP eras on one stdio process. `initialize` still
  returns protocol `2024-11-05`. A `params._meta` envelope with both
  `io.modelcontextprotocol/protocolVersion` and
  `io.modelcontextprotocol/clientCapabilities` speaks `2026-07-28`
  (`server/discover`, `resultType`, `_meta`). See `docs/mcp.md`. That
  handshake does not capture Cursor, Codex, or other clients.
- `installer/update.py` re-runs `install.py`. A second run overwrites the
  namespaced hooks, skills, and agents, leaves `brain.db`, `memory/`, `wiki/`,
  `private/`, and existing templates in place, and merges Claude Code, Cursor,
  and Codex MCP entries that launch the same `serve-mcp`. That is not a
  shared multi-agent memory service.
- Hooks write the project DB of the current working directory. They do not
  pass `--global`. There is no shared daemon and no cross-machine sync.
  `serve-mcp --global` (or `CC_AGENT_BRAIN_GLOBAL_DIR`) opens one on-disk
  library, `<global-dir>/brain.db` plus `<global-dir>/library.md`, default
  `~/.cc-agent-brain`. Inserts store a caller-supplied `writer`. `search`
  still fuses that file when it exists and is not the file already open.

## Layers

### 1. Installer layer

`installer/install.py` overwrites namespaced hooks, skills, and agents, and
copies templates only when the destination is missing. It backs up
`.claude/settings.json` once, merges Claude Code hook entries, writes
`.cc-agent-brain/install-manifest.json`, and runs `brain_store.py init` even
when `brain.db` already exists. It also merges one stdio MCP server into
`.mcp.json`, `.cursor/mcp.json`, and `.codex/config.toml`.
`installer/update.py` is that same script invoked again.

### 2. Capture layer (Claude Code hooks)

| Hook | Claude Code event | Responsibility |
|------|-------------------|----------------|
| `session_start.py` | SessionStart | onboarding check + engine stats |
| `prompt_capture.py` | UserPromptSubmit | user prompt → Markdown session note + event |
| `wiki_context_hint.py` | UserPromptSubmit | FTS recall printed for Claude Code |
| `transcript_capture.py` | Stop | assistant text and `tool_use` inputs from the Claude Code transcript JSONL (idempotent). Tool results are skipped |
| `pre_compact_save.py` | PreCompact | marker file + system event. The conversation body is not copied |
| `memory_audit.py` | Stop | SQL audit: duplicate active rows, broken supersede links, stale rows |

Nothing here calls `memory add`. Distillation is a skill the agent runs later.

### 3. Engine layer (`brain_store.py`)

Python standard library only:

- Tables `events` and `memories`, plus FTS5 virtual tables ranked with `bm25()`.
- CJK-bigram tokenizer shared by indexing and queries.
- Memory status lifecycle: `active` / `superseded` / `expired` / `archived`,
  with `valid_from` / `valid_to` stored on the row. Search does not evaluate
  those timestamps.
- Capture-time secret redaction (pattern replacement).
- `rrf_fuse` over the lexical lists described above.
- `serve-mcp`: newline-delimited JSON-RPC. Legacy `initialize` returns
  protocol `2024-11-05`. Modern `_meta` requests at `2026-07-28` use
  `server/discover` and put `serverInfo` version `0.2.0` in `_meta`.

### 4. Skill / agent layer

Skills are instructions for Claude Code (onboard, wiki update/search, distill,
audit, material distill). Agents are curator, compiler, and material
extractor prompts. They call the engine CLI. They are not other products'
auto-capture.

### 5. Files

- `.cc-agent-brain/brain.db` — project store written by the hooks (git-ignored).
- `~/.cc-agent-brain/brain.db` and `library.md` — optional shared library.
  Override the directory with `CC_AGENT_BRAIN_GLOBAL_DIR` or `--global-dir`.
  Hooks do not create it. `library.md` lists active memories and event counts,
  not raw event text.
- `wiki/` — notes, including raw prompt copies from `prompt_capture.py`.
- `memory/` — Markdown the onboarding skill fills, plus project `sync-md` output.
- `private/` — local notes. The engine does not read this directory by itself.

## Design constraints that the code follows

- Hook failures are swallowed. `_utils.brain_cli` returns `None` on error and
  the hooks still exit 0.
- Events are insert-only. A changed long-term fact is a new memory row;
  supersede/expire updates the old row's status and `valid_to` and drops it
  from `memories_fts`.
- The process does not open sockets. MCP is stdio.
