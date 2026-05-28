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

Do not ask all questions at once. Ask in stages. The local Wiki is mandatory and should not be presented as optional.

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

Write results into `memory/preferences.md`.

## Stage 3: Long-term projects

Ask whether the user has long-term projects to track.

If yes, ask:

1. Project name
2. Project type
3. Local path
4. Current stage
5. What should be tracked long term
6. Sensitive boundaries

If no, skip project details and create an empty `memory/active-projects.md`.

## Stage 4: Capture and distillation mode

Explain: the local Wiki is the core second brain and is always enabled.

Ask:

1. Capture intensity:
   - cautious: short summaries only
   - standard: recommended, captures key decisions and materials silently
   - active: fuller context and task rationale
2. Memory distillation:
   - automatic
   - ask before writing
   - wiki only
3. Wiki retrieval:
   - proactive
   - on request only

Update:

- `memory/MEMORY.md`
- `memory/retrieval-policy.md`
- `wiki/index.md`
