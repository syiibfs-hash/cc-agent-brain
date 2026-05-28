---
name: cc-agent-brain-memory-distill
description: Distill stable, reusable, long-term information from the local Wiki into compressed memory files.
---

# CC Agent Brain Memory Distillation

Use when:

- a session contains stable user preferences
- an active project changes
- repeated patterns appear
- wiki notes contain high-value memory candidates

## Distill into

- `memory/profile.md`
- `memory/preferences.md`
- `memory/active-projects.md`
- `memory/stable-facts.md`
- `memory/MEMORY.md`

## Do not distill

- raw conversation
- temporary tasks
- uncertain guesses
- secrets or credentials
- sensitive details that do not need long-term recall
- information likely to expire soon

## Memory item format

```markdown
## Title

- value:
- type:
- status: active
- confidence: high|medium|low
- source: wiki/...
- updated: YYYY-MM-DD
```
