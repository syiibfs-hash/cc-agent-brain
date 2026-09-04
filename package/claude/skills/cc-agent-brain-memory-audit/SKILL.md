---
name: cc-agent-brain-memory-audit
description: Audit local memory for stale, duplicated, conflicting, broken, or missing information using the engine.
---

# CC Agent Brain Memory Audit

Use when:

- many new events have accumulated
- the user says the assistant forgot something
- conflicting project information appears
- memory files are growing too large

## Engine audit (primary)

```bash
python .claude/hooks/cc-agent-brain/brain_store.py audit
python .claude/hooks/cc-agent-brain/brain_store.py timeline --limit 20
```

The engine reports:

1. `duplicate_active` — same layer+title with several active copies (potential conflict)
2. `broken_supersede_chain` — a memory supersedes an id that no longer exists
3. `stale_candidate` — active semantic/working memory untouched for 90+ days
4. `low_confidence` — count of active low-confidence memories to verify
5. `never_distilled` — large event backlog with zero distilled memories

## Markdown checks (secondary)

1. Duplicate preferences across memory files
2. Conflicting project status between engine and `memory/active-projects.md`
3. Important Wiki pages not reflected in memory
4. Sensitive information accidentally stored

## Remediation

- Resolve duplicates by keeping one and superseding/expiring the others (`memory expire <id>`).
- Repair or relink broken chains.
- Re-confirm stale items with the user, then update or expire.
- Run `sync-md` after cleanup.

## Output

Write a concise audit report to `wiki/tasks/memory-audit-YYYY-MM-DD.md` with
issue ids and the action taken for each.
