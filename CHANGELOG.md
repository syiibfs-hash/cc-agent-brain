# Changelog

## 0.2.0 — Local memory engine

Theme: upgrade from prompt-based scaffold to a real local memory engine. Zero
third-party dependencies added (Python stdlib only).

### Added
- `brain_store.py`: SQLite + FTS5 (BM25) engine with CJK bigram tokenization,
  covering events, versioned memories, retrieval, audit, stats and timeline.
- Four-layer memory model (working / episodic / semantic / procedural) with
  bi-temporal validity and supersede/expire lifecycle (history retained).
- `transcript_capture.py` Stop hook: indexes assistant replies and tool calls
  from the Claude Code transcript, idempotent via a cursor file.
- Capture-time secret redaction (OpenAI/Anthropic/GitHub/AWS/Google keys, JWT,
  Bearer, PEM, credential assignments).
- Reciprocal Rank Fusion helper, with project-DB-first / global-DB fallback.
- Dependency-free MCP server (`serve-mcp`, JSON-RPC over stdio) exposing
  brain_search / brain_add_memory / brain_forget / brain_timeline / brain_stats.
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

## 0.1.0

Initial local-first MVP scaffold.

- Added safe installer.
- Added namespaced Claude Code skills, agents, and hooks.
- Added local Wiki-first memory design.
- Added onboarding, capture, search, distillation, audit, and material skills.
- Added README, docs, prompts, and release checklist.
