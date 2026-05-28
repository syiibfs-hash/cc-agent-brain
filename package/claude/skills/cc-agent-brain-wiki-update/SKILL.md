---
name: cc-agent-brain-wiki-update
description: Update the local Markdown Wiki with session notes, project updates, decisions, materials, prompts, concepts, and tasks.
---

# CC Agent Brain Wiki Update

Use after meaningful conversations, project decisions, or task checkpoints.

## Destinations

- Session notes: `wiki/sessions/YYYY-MM-DD.md`
- Project updates: `wiki/projects/<project-name>.md`
- Decisions: `wiki/decisions/YYYY-MM-DD-<decision>.md`
- Materials: `wiki/materials/<topic>.md`
- Prompts: `wiki/prompts/<topic>.md`
- Concepts: `wiki/concepts/<concept>.md`
- Tasks: `wiki/tasks/<project-name>.md`

## Rules

1. Prefer concise structured notes over full transcripts.
2. Preserve important raw snippets only when useful.
3. Link related pages.
4. Mark memory candidates clearly.
5. Do not write secrets, tokens, passwords, or credentials.

## Minimal session note format

```markdown
---
type: session_note
created: YYYY-MM-DD HH:MM
project: unknown
importance: medium
memory_candidate: true
---

# Session note

## User intent

## Key decisions

## Useful materials

## Next actions
```
