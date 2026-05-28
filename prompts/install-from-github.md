# Install from GitHub Prompt

```text
You are helping me install CC Agent Brain into the current Claude Code project.

Goal:
Install CC Agent Brain as an add-on to the existing project. Do not replace or overwrite my existing `.claude/` directory.

Source:
GitHub repository: https://github.com/syiibfs-hash/cc-agent-brain

Installation requirements:
1. Download or clone the repository to a temporary directory.
2. Inspect the current project structure.
3. If `.claude/` already exists, merge CC Agent Brain files into it.
4. Do not overwrite existing user files.
5. Add all CC Agent Brain skills under `.claude/skills/cc-agent-brain-*`.
6. Add all CC Agent Brain agents under `.claude/agents/cc-agent-brain-*.md`.
7. Add all CC Agent Brain hooks under `.claude/hooks/cc-agent-brain/`.
8. Merge hook configuration into `.claude/settings.json` instead of replacing the file.
9. Before modifying `.claude/settings.json`, create a backup named `.claude/settings.backup.cc-agent-brain.json`.
10. Create local folders if they do not exist: `memory/`, `wiki/`, `private/`, `templates/`.
11. Do not commit or upload my generated `memory/`, `wiki/`, or `private/` content.
12. After installation, summarize files added, settings merged, files skipped, and next steps.

After installation, trigger the onboarding flow if `memory/profile.md` or `memory/preferences.md` is missing.
```
