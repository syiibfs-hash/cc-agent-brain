---
name: cc-agent-brain-wiki-search
description: Search the local memory engine and Wiki when the user asks about prior context, active projects, decisions, preferences, or materials.
---

# CC Agent Brain Wiki Search

Use this skill before asking the user to repeat background.

## Step 1 — engine retrieval (FTS5/BM25, do this first)

Run from the project root (the hook directory is `.claude/hooks/cc-agent-brain/`):

```bash
python .claude/hooks/cc-agent-brain/brain_store.py search "<query>" --k 8 --human
```

- The engine searches compressed memories first, then the captured event stream.
- A project-local DB (`.cc-agent-brain/brain.db`) is searched first; a global DB
  (`~/.cc-agent-brain/brain.db`) is merged automatically when present.
- Filter by layer when appropriate: `--layer semantic|episodic|procedural|working`.
- Structured JSON (drop `--human`) is available when you need IDs for follow-ups.

## Step 2 — Wiki fallback (only if Step 1 is insufficient)

Read in this order:

1. `memory/MEMORY.md`
2. `memory/profile.md`
3. `memory/preferences.md`
4. `memory/active-projects.md`
5. `memory/retrieval-policy.md`
6. `memory/brain-index.generated.md` (engine projection, if present)
7. `wiki/index.md`
8. `wiki/projects/`, `wiki/decisions/`, `wiki/materials/`, `wiki/sessions/`

## Response rule

If relevant information is found, summarize it and state whether it came from
the engine (memory/event id) or a local file.

If nothing is found, say:

> I did not find a relevant record in the local engine, memory or Wiki. I will answer based on the current context.
