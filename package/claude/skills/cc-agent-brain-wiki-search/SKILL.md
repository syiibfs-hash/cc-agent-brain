---
name: cc-agent-brain-wiki-search
description: Search the local memory and Wiki when the user asks about prior context, active projects, decisions, preferences, or materials.
---

# CC Agent Brain Wiki Search

Use this skill before asking the user to repeat background.

## Search order

1. `memory/MEMORY.md`
2. `memory/profile.md`
3. `memory/preferences.md`
4. `memory/active-projects.md`
5. `memory/retrieval-policy.md`
6. `wiki/index.md`
7. `wiki/projects/`
8. `wiki/decisions/`
9. `wiki/materials/`
10. `wiki/sessions/`

## Response rule

If relevant information is found, summarize it and mention which local file it came from.

If nothing is found, say:

> I did not find a relevant record in the local memory or Wiki. I will answer based on the current context.
