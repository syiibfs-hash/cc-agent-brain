---
name: cc-agent-brain-onboard-user
description: Initialize the user's local second brain profile, assistant identity, response preferences, active projects, and memory settings.
---

# CC Agent Brain Onboarding

Use this skill when:

- `memory/profile.md` is missing or incomplete
- `memory/preferences.md` is missing or incomplete
- the user asks to configure CC Agent Brain
- the SessionStart hook says onboarding is incomplete

## Rule

Do not ask all questions at once. Ask in stages. The local Wiki and engine are
mandatory and should not be presented as optional.

## Stage 0 — initialize the engine

```bash
python .claude/hooks/cc-agent-brain/brain_store.py init
```

## Stage 1: Identity relationship

Ask:

1. How should I address you?
2. What would you like to call me in this project?
3. What role should I mainly play?
   - coding assistant
   - research/paper assistant
   - project manager
   - writing/material organizer
   - personal knowledge curator
   - general personal agent

Write results into `memory/profile.md`.

## Stage 2: Response preferences

Ask:

1. Do you prefer concise answers, detailed analysis, conclusion-first answers, copy-ready text, tables, or proactive consulting?
2. When should I ask clarifying questions?
3. When should I make a best-effort plan directly?

Write results into `memory/preferences.md`, then persist the durable ones in the
engine (`memory add --layer semantic --tags preference`).

## Stage 3: Long-term projects

Ask whether the user has long-term projects to track.

If yes, ask: name, type, local path, current stage, what to track long term,
sensitive boundaries. If no, create an empty `memory/active-projects.md`.

## Stage 4: Capture scope and distillation mode

Explain: the local Wiki + engine are the core second brain and always enabled.

Ask:

1. Memory scope:
   - project only (default): `.cc-agent-brain/brain.db`
   - project + global profile: also use `~/.cc-agent-brain/brain.db` (or `CC_AGENT_BRAIN_GLOBAL_DIR`). That directory's `library.md` is maintained from the global store. Writes record `writer` (`--writer`, else `CC_AGENT_BRAIN_WRITER`, else `unspecified`)
2. Capture intensity:
   - cautious: short summaries only
   - standard (recommended): key decisions, replies and tool actions silently indexed
   - active: fuller context and task rationale
3. Memory distillation:
   - automatic suggestions (default) / ask before writing / wiki only
4. Retrieval:
   - proactive (default, automatic on every prompt) / on request only

Update:

- `memory/MEMORY.md`
- `memory/retrieval-policy.md`
- `wiki/index.md`
- run `brain_store.py sync-md`
