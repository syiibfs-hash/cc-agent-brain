# Memory Design

## Principle

The event stream records what happened; compressed memory records what is
durably true. Markdown stays human-readable; the SQLite engine is what makes
memory searchable, versioned and auditable.

## Four memory layers

| Layer | Holds | Analogy | Retention |
|-------|-------|---------|-----------|
| working | current task state, short-lived | scratchpad | days |
| episodic | timestamped events (prompt, reply, tool action) | what happened & when | append-only |
| semantic | stable facts, preferences, project state | distilled knowledge | long, versioned |
| procedural | reusable workflows, prompts, materials | muscle memory | long |

Flow:

```text
working context
   ↓ captured automatically
episodic events (SQLite + wiki/sessions)
   ↓ distill (skill / curator)
semantic & procedural memories
   ↓ updated over time
new facts supersede / expire old ones (timeline kept)
```

## Memory record schema

Every memory carries:

- `id`, `layer`, `scope` (project/global)
- `title`, `body`, `tags`
- `confidence`: high / medium / low
- `status`: active / superseded / expired / archived
- `valid_from`, `valid_to` — bi-temporal validity
- `source` — Wiki page or event it came from
- `supersedes` — id of the memory it replaces
- `created_at`, `updated_at`

## Versioning rules

- A changed fact creates a **new** memory with `supersedes=<old-id>`; the old one
  becomes `superseded`, gets `valid_to`, and leaves active retrieval.
- A fact that simply stops being true is `expired`, never physically deleted
  (unless the user explicitly purges).
- This produces an auditable timeline (`brain_store.py timeline`) and is what
  lets temporal questions ("what did we believe last week?") be answered.

## What does NOT belong in long-term memory

- raw transcripts (they live in the episodic stream)
- one-off tasks, uncertain guesses
- secrets and credentials (common key shapes are redacted at capture time)
- information that expires soon — use the working layer

## Retrieval policy

1. Engine search: active memories first, episodic events second; the project DB
   is searched before the optional global DB; lists are fused with RRF.
2. Fallback to Markdown files in the fixed order documented in the
   cc-agent-brain-wiki-search skill.
3. Say so when nothing is found — never invent a past decision.
