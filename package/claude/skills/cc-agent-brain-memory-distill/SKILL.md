---
name: cc-agent-brain-memory-distill
description: Distill stable, reusable, long-term information from the captured event stream and Wiki into versioned engine memories.
---

# CC Agent Brain Memory Distillation

Use when:

- a session contains stable user preferences
- an active project changes state
- repeated patterns or corrections appear
- the Stop hook suggests distillation, or `candidates` shows a backlog

## Step 1 — inspect what accumulated

```bash
python .claude/hooks/cc-agent-brain/brain_store.py candidates --days 3
python .claude/hooks/cc-agent-brain/brain_store.py search "<topic>" --k 10
```

## Step 2 — write versioned memories

```bash
python .claude/hooks/cc-agent-brain/brain_store.py memory add \
  --title "..." --body "..." \
  --layer semantic|procedural|working|episodic \
  --confidence high|medium|low \
  --tags "tag1,tag2" --source "wiki/..."
```

Layers:

- `semantic` — stable facts, preferences, project state (the default)
- `procedural` — reusable workflows, checklists, prompt patterns
- `working` — short-lived active-task context
- `episodic` — dated events that must keep their time anchor

## Step 3 — supersede, never overwrite

When a new fact replaces an old one, write the new memory with `--supersedes <old-id>`.
The old memory is kept as `superseded` with `valid_to` set, and leaves active
retrieval. `timeline` and `memory list` can show that row. `search` has no
as-of argument and cannot return the store as of a past time.

When a fact is simply no longer true, expire it:

```bash
python .claude/hooks/cc-agent-brain/brain_store.py memory expire <id>
```

## Step 4 — refresh projections

```bash
python .claude/hooks/cc-agent-brain/brain_store.py sync-md
```

Also keep `memory/MEMORY.md` and the relevant memory markdown files aligned.

## Do not distill

- raw conversation, temporary tasks, uncertain guesses
- secrets or credentials (the engine redacts common key shapes at capture time,
  but do not deliberately store sensitive material)
- information likely to expire soon — use `working` layer instead

## Memory item contract

Every memory carries: id, layer, title, body, tags, confidence, status,
valid_from, valid_to, source, supersedes, timestamps.
