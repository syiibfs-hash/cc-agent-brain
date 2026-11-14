# Memory design

## Principle

The event table records captured Claude Code text. A memory row records a fact
someone chose to store with `memory add`. Markdown files under `memory/` and
`wiki/` stay readable. SQLite is what `search` queries.

Distillation is not automatic. No hook calls `add_memory`. The distill skill
is a prompt that tells the agent to run the CLI.

## Four layers

| Layer | Intended contents | How it gets there | Retention |
|-------|-------------------|-------------------|-----------|
| working | short-lived task notes | `memory add --layer working` | until you expire or supersede it |
| episodic | timestamped event text | hooks insert `events` rows; a memory row is still a separate `memory add` | events are insert-only |
| semantic | facts and preferences | `memory add` | until superseded, expired, or archived |
| procedural | workflows you choose to store | `memory add` | until superseded, expired, or archived |

```text
Claude Code user prompt / assistant text / tool_use input
   ↓ hooks
events table + wiki/sessions notes
   ↓ a person or skill runs `memory add`
memories table
   ↓ `memory add --supersedes` or `memory expire`
old row stays, status changes, valid_to is set, row leaves memories_fts
```

## Columns on a memory row

- `id`, `layer`, `scope` (stored string, default `project`; `search` does not filter on it)
- `title`, `body`, `tags`
- `confidence`: `high` / `medium` / `low`
- `status`: `active` / `superseded` / `expired` / `archived`
- `valid_from`, `valid_to` — set at insert and when the row leaves active status
- `source`, `writer`, `supersedes`
- `writer` is the caller-supplied identity for that insert (`--writer`, else
  `CC_AGENT_BRAIN_WRITER`, else `unspecified`). Hooks pass `claude-code` when
  the environment variable is unset. The engine does not detect which MCP
  client connected. `source` remains provenance, separate from `writer`.
- `created_at`, `updated_at`

`valid_from` is the insert timestamp. `valid_to` stays null while the row is
active and is set when the row is superseded, expired, or archived. These
columns are a record of that write. They are not a query interface.

## What supersede and expire do

- `memory add --supersedes <old-id>` inserts a new active row and marks
  `<old-id>` as `superseded` with `valid_to` set to the same timestamp. The
  old row remains in `memories` and is deleted from `memories_fts`.
- `memory expire <id>` marks that row `expired`, sets `valid_to` if empty, and
  removes it from `memories_fts`. The row is not deleted.
- `timeline` returns recent memory rows ordered by `updated_at`, including
  non-active statuses. It does not take a timestamp.

There is no as-of query. You cannot ask the engine for the active set, or for
any other snapshot, as of a past time. Reading `timeline`, `memory list`, or a
row by id shows stored columns. `search` applies `status='active'` and ignores
`valid_from` / `valid_to`.

## What the hooks do not put in `memories`

- raw transcripts (user prompts, assistant text, and tool-call inputs go to
  `events`; tool results are skipped)
- secrets that match the redaction patterns (replaced at write time; this is
  best-effort)
- a fact you did not explicitly add

## Retrieval

1. `search` ranks active memories and events with FTS5 `bm25()`, then fuses
   those lexical lists with RRF. When the global `brain.db` exists and is a
   different file, its memory and event lists are fused in the same call.
   The global directory is `CC_AGENT_BRAIN_GLOBAL_DIR` or `--global-dir`,
   otherwise `~/.cc-agent-brain`. There is no vector list. Hits include the
   stored `writer`.
2. The wiki-search skill then tells the agent to open Markdown files in a
   fixed order if the engine output is not enough.
3. The skill text says to report a miss instead of inventing a past decision.
   The engine itself only returns hits or an empty list.
