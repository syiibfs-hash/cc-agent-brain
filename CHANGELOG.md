# Changelog

## Unreleased

### Fixed
- Upgrades overwrite CC Agent Brain framework files (`.claude/hooks/cc-agent-brain/**`, `.claude/skills/cc-agent-brain-*/**`, `.claude/agents/cc-agent-brain-*.md`) so an existing install receives the current engine.
- `brain_store.py init` runs again when `brain.db` already exists, so `BrainStore._migrate()` is not skipped on upgrade.
- `memory/`, `wiki/`, `private/`, user-edited templates, and `brain.db` are still never overwritten or deleted.

### Added
- The installer merges one local stdio MCP server, `cc-agent-brain`, into Claude Code `.mcp.json`, Cursor `.cursor/mcp.json`, and Codex `.codex/config.toml`. Other servers in those files are left in place.
- Shared global library: `~/.cc-agent-brain/brain.db` and `library.md`, or another directory via `--global-dir` / `CC_AGENT_BRAIN_GLOBAL_DIR`. `serve-mcp --global` and MCP writes use that SQLite file. `library.md` is rebuilt from active memories and from event counts, not from raw event text. Project `.cc-agent-brain/brain.db` stays the project store. The installer does not retarget the three MCP entries at the global file.
- Writer on inserts: explicit `--writer` or `brain_add_memory` `writer`, else `CC_AGENT_BRAIN_WRITER`, else `unspecified`. Claude Code hooks pass `claude-code` when the variable is unset. `search`, `timeline`, and `stats` return it. Existing databases gain the column in `_migrate`; old rows keep an empty writer. `source` is unchanged.

## 0.2.0 — Local memory engine

Theme: upgrade from prompt-based scaffold to a real local memory engine. Zero
third-party dependencies added (Python stdlib only).

### Added
- `brain_store.py`: SQLite + FTS5 (BM25) engine with CJK bigram tokenization,
  covering events, versioned memories, retrieval, audit, stats and timeline.
- Four-layer memory columns (working / episodic / semantic / procedural) with
  `valid_from` / `valid_to` stored on the row, plus supersede/expire (old row
  kept). Search has no as-of / time-travel query.
- `transcript_capture.py` Stop hook: indexes Claude Code assistant text and
  `tool_use` inputs from the transcript, idempotent via a cursor file. Tool
  results are skipped. Capture hooks are Claude Code only.
- Capture-time secret redaction (OpenAI/Anthropic/GitHub/AWS/Google keys, JWT,
  Bearer, PEM, credential assignments).
- Reciprocal Rank Fusion of lexical FTS lists (memories, events, and the
  global DB's lists when that file exists). Not lexical-plus-vector hybrid
  retrieval.
- Dependency-free MCP server (`serve-mcp`, JSON-RPC over stdio) exposing
  brain_search / brain_add_memory / brain_forget / brain_timeline /
  brain_stats. The original 0.2.0 engine spoke `initialize` / `ping` /
  `tools/list` / `tools/call` at protocol `2024-11-05`. Current master also
  speaks `2026-07-28`; see the note below.
- `sync-md` generates `memory/brain-index.generated.md` projection.
- Installer initializes the engine DB and records `engine_state`; docs:
  memory-engine.md, mcp.md, product-analysis.md.

### Changed
- `wiki_context_hint.py` replaces the hard-coded keyword list with real FTS recall.
- `memory_audit.py` uses SQL audit (duplicate active, broken supersede chains,
  stale entries, low confidence, never-distilled backlog).
- `session_start.py` / `pre_compact_save.py` report and record engine state.
- Skills and agents realigned to the engine CLI and versioned schema.
- README rewritten (bilingual) around the engine + MCP positioning.

### Notes
- Personal `memory/`, `wiki/`, `private/` and `*.db` remain git-ignored and are
  never removed by the uninstaller.
- The original 0.2.0 installer skipped framework files that already existed.
  That behavior is no longer what `install.py` does. See Unreleased.
- Documentation after 0.2.0 was corrected to the capture, retrieval, and
  as-of limits above. Vector search, as-of queries, and a shared multi-agent
  memory service are still absent.
- Master commit `6208cd3` (not a new tag and not a GitHub Release) teaches the
  same `serve-mcp` process a second era. `initialize` still returns
  `2024-11-05` with `serverInfo.version` `"2"`. A `params._meta` envelope
  carrying both `io.modelcontextprotocol/protocolVersion` and
  `io.modelcontextprotocol/clientCapabilities`, with version `2026-07-28`,
  handles `server/discover`, `tools/list`, and `tools/call`, and puts product
  version `0.2.0` in `_meta["io.modelcontextprotocol/serverInfo"]`. Another
  version string on that envelope returns JSON-RPC `-32022`. `PRODUCT_VERSION`
  stays `0.2.0`.
- Master commit `facc0db` (not a new tag and not a GitHub Release) makes a
  second install overwrite namespaced framework files, run `init` against an
  existing `brain.db`, and merge Claude Code, Cursor, and Codex MCP entries
  for that `serve-mcp`. `memory/`, `wiki/`, `private/`, existing templates,
  and the database file stay.

## 0.1.0

Initial local-first MVP scaffold.

- Added safe installer.
- Added namespaced Claude Code skills, agents, and hooks.
- Added local Wiki-first memory design.
- Added onboarding, capture, search, distillation, audit, and material skills.
- Added README, docs, prompts, and release checklist.
