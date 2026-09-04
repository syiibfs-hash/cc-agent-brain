# Architecture

CC Agent Brain is an installable, local-first add-on that gives coding agents
a durable, retrievable memory. It never replaces `.claude/`.

## Main flow

```text
user prompt / assistant reply / tool action
        ↓ (hooks, automatic)
append-only event stream (SQLite)  +  human-readable Wiki (Markdown)
        ↓ (distill skill / curator agent)
versioned long-term memories (bi-temporal, layered)
        ↓ (FTS5/BM25 + RRF; project DB first, global DB fallback)
automatic recall injected into future sessions
        ↓ optional
MCP server: the same memory for any MCP-compatible client
```

## Layers

### 1. Installer layer

`installer/` merges skills, agents, hooks and templates into an existing
project without replacing `.claude/`, backs up settings, records a manifest,
and initializes the engine database.

### 2. Capture layer (hooks)

| Hook | Event | Responsibility |
|------|-------|----------------|
| `session_start.py` | SessionStart | onboarding check + engine stats |
| `prompt_capture.py` | UserPromptSubmit | user prompt → Markdown projection + event stream |
| `wiki_context_hint.py` | UserPromptSubmit | real FTS recall against the prompt |
| `transcript_capture.py` | Stop | index assistant replies & tool calls from the transcript (idempotent) |
| `pre_compact_save.py` | PreCompact | checkpoint before compaction |
| `memory_audit.py` | Stop | SQL audit: duplicates, broken chains, stale entries |

### 3. Engine layer (`brain_store.py`)

Zero third-party dependencies (Python stdlib only):

- SQLite tables `events` / `memories` with FTS5 virtual tables (BM25 ranking).
- CJK-bigram tokenizer so Chinese/English retrieval both work without a model.
- Versioned memories: layer, status, valid_from/valid_to, supersedes chain.
- Capture-time secret redaction.
- RRF fusion helper reserved for an optional vector channel.
- Dependency-free MCP server (`serve-mcp`, JSON-RPC over stdio).

### 4. Skill / Agent layer

Skills define reusable workflows (onboard, wiki update/search, distill, audit,
material distill); agents handle curation, compilation and material extraction
through the engine CLI.

### 5. Knowledge layer

- `.cc-agent-brain/brain.db` — structured project store (git-ignored).
- `~/.cc-agent-brain/brain.db` — optional global identity/preferences store.
- `wiki/` — detailed, human-readable context.
- `memory/` — compressed Markdown memory + generated engine projection.
- `private/` — local-only sensitive notes.

## Design constraints

- Local-first: nothing leaves the machine; no cloud account, no telemetry.
- Markdown remains the human-readable projection; SQLite is the index of record.
- Hooks never block the user: engine failures degrade silently.
- History is append-only and auditable; facts are superseded/expired, never
  silently rewritten.
