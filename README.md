# CC Agent Brain

**CC Agent Brain** is a local Wiki-first second brain system for Claude Code.

It installs as a **namespaced add-on** inside an existing Claude Code project. It does **not** replace your existing `.claude/` directory.

> 中文定位：面向 Claude Code 的本地第二大脑系统。通过分支式初始化、自动信息收集、本地 Markdown Wiki、记忆精炼和主动检索，让 Claude Code 在不依赖云同步的情况下，越用越懂用户。

---

## Why this project exists

Many Claude Code users still work like this:

```text
open a session → explain the background again → solve one task → lose useful context
```

CC Agent Brain changes the workflow into:

```text
normal Claude Code work
↓
automatic local Wiki capture
↓
structured project / material / decision pages
↓
distilled long-term memory
↓
future retrieval when memory is not enough
```

Core design:

- **Local-first**: user knowledge stays on the local machine.
- **Wiki-first**: detailed context goes into `wiki/` first.
- **Memory is compressed**: only stable facts, preferences, active project indexes, and reusable patterns enter `memory/`.
- **No cloud sync in v0.1**: GitHub/private backup is a future optional module.
- **No `.claude` conflict**: installs into the existing `.claude/` with the `cc-agent-brain-*` namespace.

---

## Quick install with Claude Code

Open Claude Code in the project where you want to enable CC Agent Brain, then paste this prompt:

```text
You are helping me install CC Agent Brain into the current Claude Code project.

Goal:
Install CC Agent Brain as an add-on to the existing project. Do not replace or overwrite my existing `.claude/` directory.

Source:
GitHub repository: https://github.com/lifuguan/cc-agent-brain

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

Then run the installer if Claude Code asks for a concrete command:

```bash
python installer/install.py --target /path/to/your/project
```

After installation, restart Claude Code or check `/hooks` so the new hooks are loaded.

---

## Install from a local ZIP or folder

If you already downloaded the ZIP file, open Claude Code in your target project and paste:

```text
You are helping me install CC Agent Brain into the current Claude Code project.

I have already downloaded the package locally.

Package path:
PASTE_THE_LOCAL_ZIP_OR_FOLDER_PATH_HERE

Please:
1. Inspect the package contents.
2. Extract it if it is a ZIP file.
3. Locate the CC Agent Brain installer or package directory.
4. Install it as an add-on to the current project.
5. Do not replace my existing `.claude/` directory.
6. Merge files into `.claude/` using the `cc-agent-brain` namespace.
7. Backup `.claude/settings.json` before editing it.
8. Merge hook settings instead of overwriting existing settings.
9. Create `memory/`, `wiki/`, `private/`, and `templates/` if missing.
10. Keep my generated memory and Wiki content local.
11. After installation, show me what changed and whether onboarding is needed.
```

---

## What gets installed into your project

```text
my-project/
├── .claude/
│   ├── settings.json
│   ├── settings.backup.cc-agent-brain.json
│   ├── skills/
│   │   └── cc-agent-brain-*/
│   ├── agents/
│   │   └── cc-agent-brain-*.md
│   └── hooks/
│       └── cc-agent-brain/
├── memory/
├── wiki/
├── private/
└── templates/
```

CC Agent Brain does not replace your `.claude` directory. It installs as a namespaced add-on and safely merges into your existing Claude Code project configuration.

---

## Features

### 1. Branching onboarding

Claude Code asks the user:

- how to address the user
- what the user wants to call Claude Code
- what role Claude Code should play
- preferred response style
- whether there are long-term projects
- automatic capture mode
- memory distillation mode
- Wiki retrieval preference

### 2. Silent local capture

The system captures meaningful prompts, task checkpoints, decisions, and reusable materials into the local Wiki without requiring the user to manually say “remember this.”

### 3. Wiki-first storage

Detailed context is stored in:

```text
wiki/sessions/
wiki/projects/
wiki/materials/
wiki/decisions/
wiki/prompts/
wiki/concepts/
wiki/tasks/
```

### 4. Distilled memory

Only high-value, stable, reusable information is distilled into:

```text
memory/MEMORY.md
memory/profile.md
memory/preferences.md
memory/active-projects.md
memory/stable-facts.md
memory/retrieval-policy.md
```

### 5. Retrieval fallback

When Claude Code does not find enough information in memory, it should search the local Wiki before asking the user to repeat background information.

---

## Repository structure

```text
cc-agent-brain/
├── installer/
├── package/
│   ├── claude/
│   ├── memory_templates/
│   ├── wiki_templates/
│   └── templates/
├── prompts/
├── docs/
├── examples/
├── CHECKLIST.md
└── README.md
```

---

## Manual installation

```bash
git clone https://github.com/lifuguan/cc-agent-brain.git
cd cc-agent-brain
python installer/install.py --target /path/to/your/project
```

For a dry run:

```bash
python installer/install.py --target /path/to/your/project --dry-run
```

---

## Uninstall

```bash
python installer/uninstall.py --target /path/to/your/project
```

The uninstaller removes only files listed in `.cc-agent-brain/install-manifest.json`. It does not delete your personal `memory/`, `wiki/`, or `private/` content unless you explicitly do so yourself.

---

## Roadmap

### v0.1 Local second brain MVP

- Branching onboarding
- Safe `.claude` merge installer
- Local Wiki structure
- Automatic session capture
- Wiki-first storage
- Memory distillation
- Wiki retrieval hints

### v0.2 Memory governance

- Memory audit
- Conflict detection
- Stale memory detection
- Duplicate memory cleanup

### v0.3 Project intelligence

- Project state machine
- Decision records
- Material distillation
- Weekly review

### v0.4 Optional private backup

- Private GitHub backup
- Restore from backup
- Backup integrity check

---

## Privacy

This repository is a framework. It is not intended to publish a user's actual personal knowledge base.

By default, generated user files under `memory/`, `wiki/`, and `private/` should be excluded from git in the user’s own project.

---

## License

MIT
