# Architecture

CC Agent Brain is an installable Claude Code add-on.

## Main idea

```text
Conversation / project work
↓
local Wiki capture
↓
structured Wiki pages
↓
distilled memory
↓
future retrieval
```

## Layers

### 1. Installer layer

Installs skills, agents, hooks, templates, and memory/Wiki skeletons into an existing project without replacing `.claude/`.

### 2. Hook layer

Captures prompts, emits retrieval hints, checks onboarding state, and creates checkpoints before compaction.

### 3. Skill layer

Defines reusable workflows: onboarding, Wiki update, Wiki search, memory distillation, memory audit, and material distillation.

### 4. Agent layer

Handles specialized tasks such as curating memory, compiling Wiki pages, and distilling materials.

### 5. Local knowledge layer

- `wiki/` stores detailed context.
- `memory/` stores compressed long-term indexes.
- `private/` stores local-only sensitive notes.
