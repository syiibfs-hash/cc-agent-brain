# Retrieval Policy

When the user asks about prior context, active projects, old decisions, personal preferences, reusable materials, or anything that may have been discussed before, search in this order:

1. `memory/MEMORY.md`
2. `memory/profile.md`
3. `memory/preferences.md`
4. `memory/active-projects.md`
5. `memory/stable-facts.md`
6. `wiki/index.md`
7. `wiki/projects/`
8. `wiki/decisions/`
9. `wiki/materials/`
10. `wiki/sessions/`

If nothing relevant is found, say that the local brain has no relevant record and answer based on current context.
