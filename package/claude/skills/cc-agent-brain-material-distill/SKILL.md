---
name: cc-agent-brain-material-distill
description: Extract reusable text snippets, prompts, project explanations, README copy and presentation materials into wiki/materials and the procedural memory layer.
---

# CC Agent Brain Material Distillation

Use when a conversation produces copy-ready text the user will reuse.

## Outputs

1. Save the full copy-ready material to `wiki/materials/<topic>.md`.
2. Index a short pointer in the engine as a `procedural` memory:

```bash
python .claude/hooks/cc-agent-brain/brain_store.py memory add \
  --title "Material: <topic>" \
  --body "Reusable <kind> snippet. Full text: wiki/materials/<topic>.md" \
  --layer procedural --confidence high --tags "material,<topic>" \
  --source "wiki/materials/<topic>.md"
```

## Rules

1. Preserve wording when the text will be reused verbatim — do not over-summarize.
2. Record the original context and related project links.
3. Tag by reuse type: readme, proposal, talking-point, prompt, email, slide.
4. When an older version of the same material is replaced, supersede its memory
   (`--supersedes <old-id>`) instead of creating a duplicate active entry.
5. Never store secrets or credentials in materials.
