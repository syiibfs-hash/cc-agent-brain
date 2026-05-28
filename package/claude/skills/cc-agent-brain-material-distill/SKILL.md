---
name: cc-agent-brain-material-distill
description: Distill reusable materials from conversations, projects, documents, and code work into the local Wiki.
---

# CC Agent Brain Material Distillation

Use to capture reusable content such as:

- project introduction text
- README snippets
- presentation talking points
- paper-writing materials
- proposal sections
- prompts
- decision rationales
- implementation notes

## Destination

Write to `wiki/materials/<topic>.md` or update an existing material page.

## Material card format

```markdown
---
type: material
created: YYYY-MM-DD
source: session/project/document
reusable_for:
  - README
  - proposal
  - presentation
---

# Material title

## Ready-to-use text

## Context

## Related pages
```
