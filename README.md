# CC Agent Brain

[English](#english) | [中文](#中文)

A local Wiki-first second brain system for Claude Code. Installs as a namespaced add-on — never replaces your existing `.claude/` directory.

---

## English

### What is CC Agent Brain

CC Agent Brain turns Claude Code from a stateless tool into one that **remembers you across sessions** — all locally, no cloud sync required.

The workflow:

```text
normal Claude Code work
    ↓
automatic local Wiki capture (every prompt saved)
    ↓
structured project / material / decision pages
    ↓
distilled long-term memory (compressed, high-value only)
    ↓
future retrieval — search Wiki when memory is not enough
```

**Core principles:**

- **Local-first**: user knowledge never leaves the machine.
- **Wiki-first**: detailed context goes into `wiki/` first, unfiltered.
- **Memory is compressed**: only stable facts, preferences, active project indexes, and reusable patterns enter `memory/`.
- **No cloud sync in v0.1**: private backup is a future optional module.
- **No `.claude` conflict**: everything uses the `cc-agent-brain-*` namespace.

---

### Quick install

Open Claude Code in your project and paste:

```text
You are helping me install CC Agent Brain into the current Claude Code project.

Goal: Install CC Agent Brain as an add-on to the existing project.
Do not replace or overwrite my existing `.claude/` directory.

Source: GitHub repository: https://github.com/syiibfs-hash/cc-agent-brain

Requirements:
1. Clone the repo to a temp directory.
2. Inspect the current project structure.
3. Merge CC Agent Brain files into existing `.claude/` — never overwrite.
4. Skills go under `.claude/skills/cc-agent-brain-*`.
5. Agents go under `.claude/agents/cc-agent-brain-*.md`.
6. Hooks go under `.claude/hooks/cc-agent-brain/`.
7. Merge hook config into `.claude/settings.json` — do not replace.
8. Backup settings as `.claude/settings.backup.cc-agent-brain.json` first.
9. Create local folders: `memory/`, `wiki/`, `private/`, `templates/`.
10. Never commit `memory/`, `wiki/`, or `private/` content.
11. Summarize what was added, merged, skipped, and next steps.

Trigger onboarding if `memory/profile.md` or `memory/preferences.md` is missing.
```

Or run the installer directly:

```bash
git clone https://github.com/syiibfs-hash/cc-agent-brain.git
cd cc-agent-brain
python installer/install.py --target /path/to/your/project
```

Dry-run preview:

```bash
python installer/install.py --target /path/to/your/project --dry-run
```

---

### What gets installed

```text
my-project/
├── .claude/
│   ├── settings.json                         ← merged, not replaced
│   ├── settings.backup.cc-agent-brain.json   ← auto-backup
│   ├── skills/
│   │   └── cc-agent-brain-*/                 ← 6 skills
│   ├── agents/
│   │   └── cc-agent-brain-*.md               ← 3 agents
│   └── hooks/
│       └── cc-agent-brain/                   ← 5 hook scripts
├── memory/     ← compressed long-term memory
├── wiki/       ← detailed context
├── private/    ← local sensitive notes
└── templates/  ← writing templates
```

---

### Features

**1. Branching onboarding** — 4-stage setup: identity → preferences → projects → capture mode.

**2. Silent local capture** — Every prompt is saved to `wiki/sessions/` with auto-tags. No manual "remember this" needed.

**3. Wiki-first storage** — Seven subdirectories for different knowledge types:

```text
wiki/sessions/     daily prompt logs
wiki/projects/     long-term project pages
wiki/materials/    reusable README snippets, proposals, talking points
wiki/decisions/    key decisions and rationale
wiki/prompts/      reusable prompts
wiki/concepts/     concept explanations
wiki/tasks/        task tracking and audit reports
```

**4. Distilled memory** — Only high-value, stable information enters memory:

```text
memory/MEMORY.md           memory index (loaded every session)
memory/profile.md          user identity, name, role
memory/preferences.md      response style preferences
memory/active-projects.md  active project status
memory/stable-facts.md     durable long-term facts
memory/retrieval-policy.md search priority policy
```

**5. Retrieval fallback** — When memory is insufficient, Claude Code searches the local Wiki before asking you to repeat yourself. Search order: `memory/ → wiki/index.md → projects → decisions → materials → sessions`.

---

### Hooks, Skills, and Agents

**5 Hooks** — automatic triggers:

| Hook | Event | Purpose |
|------|-------|---------|
| `session_start.py` | SessionStart | Check onboarding, prompt loading memory |
| `prompt_capture.py` | UserPromptSubmit | Save every prompt to `wiki/sessions/` |
| `wiki_context_hint.py` | UserPromptSubmit | Suggest Wiki lookup on history-related prompts |
| `pre_compact_save.py` | PreCompact | Create checkpoint before context compaction |
| `memory_audit.py` | Stop | Lightweight audit of memory file health |

**6 Skills** — reusable workflows:

| Skill | Purpose |
|-------|---------|
| `cc-agent-brain-onboard-user` | 4-stage branching initialization |
| `cc-agent-brain-wiki-update` | Update Wiki pages with structured notes |
| `cc-agent-brain-wiki-search` | Search memory and Wiki before asking user |
| `cc-agent-brain-memory-distill` | Distill Wiki into compressed memory |
| `cc-agent-brain-memory-audit` | Audit for duplicates, conflicts, stale entries |
| `cc-agent-brain-material-distill` | Extract reusable text snippets to `wiki/materials/` |

**3 Agents** — specialized sub-agents:

| Agent | Purpose |
|-------|---------|
| `cc-agent-brain-memory-curator` | Decide what to distill, detect conflicts |
| `cc-agent-brain-wiki-compiler` | Organize Wiki pages, maintain index |
| `cc-agent-brain-material-distiller` | Extract copy-ready materials from conversations |

---

### Repository structure

```text
cc-agent-brain/
├── installer/              install.py, uninstall.py, update.py
├── package/
│   ├── claude/
│   │   ├── hooks/cc-agent-brain/   5 hooks + _utils.py
│   │   ├── skills/                 6 SKILL.md
│   │   ├── agents/                 3 agent .md
│   │   └── settings.patch.json     hook config template
│   ├── memory_templates/           memory/ seed files
│   ├── wiki_templates/             wiki/ seed files
│   └── templates/                  writing templates
├── prompts/                 install / uninstall prompts
├── docs/                    architecture, memory design, install guide
├── examples/                demo project placeholder
├── CHECKLIST.md             pre-release checklist
└── README.md
```

---

### Uninstall

```bash
python installer/uninstall.py --target /path/to/your/project
```

The uninstaller removes only framework files tracked in `.cc-agent-brain/install-manifest.json`. Your personal `memory/`, `wiki/`, and `private/` content is **never deleted**.

---

### Roadmap

| Version | Theme | Highlights |
|---------|-------|------------|
| **v0.1** (current) | Local second brain MVP | Onboarding, Wiki capture, memory distillation, retrieval hints |
| v0.2 | Memory governance | Audit, conflict detection, stale & duplicate cleanup |
| v0.3 | Project intelligence | State machine, decision records, weekly review |
| v0.4 | Optional private backup | Private GitHub backup, restore, integrity check |

---

### Privacy

This repository is an open-source **framework**. It contains no personal knowledge base data. User-generated files under `memory/`, `wiki/`, and `private/` should be excluded from git via `.gitignore`.

---

### License

MIT

---

## 中文

### CC Agent Brain 是什么

CC Agent Brain 让 Claude Code 从一个每次会话都要重新交代背景的无状态工具，变成一个**跨会话记住你的本地第二大脑** —— 全程本地运行，无需云同步。

数据流：

```text
正常使用 Claude Code
    ↓
自动捕获到本地 Wiki（每次提示都保存）
    ↓
结构化的项目 / 素材 / 决策页面
    ↓
蒸馏为压缩的长期记忆（只保留高价值信息）
    ↓
记忆不够时回退检索 Wiki
```

**核心原则：**

- **本地优先**：用户知识从不出机器。
- **Wiki 优先**：详细上下文先原样写入 `wiki/`，不做删减。
- **记忆是压缩的**：只有稳定事实、偏好、活跃项目索引、可复用模式才进 `memory/`。
- **v0.1 无云同步**：私有备份是未来可选模块。
- **不冲突**：所有组件使用 `cc-agent-brain-*` 命名空间。

---

### 快速安装

在 Claude Code 中粘贴以下 prompt：

```text
You are helping me install CC Agent Brain into the current Claude Code project.

Goal: Install CC Agent Brain as an add-on to the existing project.
Do not replace or overwrite my existing `.claude/` directory.

Source: GitHub repository: https://github.com/syiibfs-hash/cc-agent-brain

Requirements:
1. Clone the repo to a temp directory.
2. Inspect the current project structure.
3. Merge CC Agent Brain files into existing `.claude/` — never overwrite.
4. Skills go under `.claude/skills/cc-agent-brain-*`.
5. Agents go under `.claude/agents/cc-agent-brain-*.md`.
6. Hooks go under `.claude/hooks/cc-agent-brain/`.
7. Merge hook config into `.claude/settings.json` — do not replace.
8. Backup settings as `.claude/settings.backup.cc-agent-brain.json` first.
9. Create local folders: `memory/`, `wiki/`, `private/`, `templates/`.
10. Never commit `memory/`, `wiki/`, or `private/` content.
11. Summarize what was added, merged, skipped, and next steps.

Trigger onboarding if `memory/profile.md` or `memory/preferences.md` is missing.
```

或者直接命令行安装：

```bash
git clone https://github.com/syiibfs-hash/cc-agent-brain.git
cd cc-agent-brain
python installer/install.py --target /path/to/your/project
```

预览模式：

```bash
python installer/install.py --target /path/to/your/project --dry-run
```

---

### 安装后的目录结构

```text
my-project/
├── .claude/
│   ├── settings.json                         ← 增量合并，不覆盖
│   ├── settings.backup.cc-agent-brain.json   ← 安装前自动备份
│   ├── skills/
│   │   └── cc-agent-brain-*/                 ← 6 个技能
│   ├── agents/
│   │   └── cc-agent-brain-*.md               ← 3 个代理
│   └── hooks/
│       └── cc-agent-brain/                   ← 5 个钩子脚本
├── memory/     ← 压缩的长期记忆
├── wiki/       ← 详细上下文
├── private/    ← 本地敏感笔记
└── templates/  ← 写作模板
```

---

### 功能特性

**1. 分支式初始化** — 4 阶段渐进式问答：身份关系 → 回复偏好 → 长期项目 → 捕获/蒸馏模式。不一上来就抛出所有问题。

**2. 静默本地捕获** — 每次用户提示自动写入 `wiki/sessions/`，打上标签 `source: user_prompt`、`memory_candidate: pending`，无需手动说"记住这个"。

**3. Wiki 优先存储** — 七个子目录各司其职：

```text
wiki/sessions/     按日期的提示日志
wiki/projects/     长期项目页面
wiki/materials/    可复用的 README 片段、演示文稿、提案文字
wiki/decisions/    关键决策及理由
wiki/prompts/      可复用的提示词
wiki/concepts/     概念解释
wiki/tasks/        任务跟踪与审计报告
```

**4. 压缩记忆** — 只有高价值、稳定的信息才从 Wiki 蒸馏到 memory：

```text
memory/MEMORY.md           记忆总索引（每次会话优先加载）
memory/profile.md          用户身份、称呼、角色
memory/preferences.md      回复风格偏好
memory/active-projects.md  活跃项目状态
memory/stable-facts.md     长期稳定事实
memory/retrieval-policy.md 检索优先级策略
```

**5. 回退检索** — 当 memory 找不到足够信息时，Claude Code 自动搜索本地 Wiki，而不是让你重新交代背景。检索顺序：`memory/ → wiki/index.md → projects → decisions → materials → sessions`。

---

### Hooks、Skills 和 Agents

**5 个 Hooks** — 自动化触发：

| Hook | 触发点 | 功能 |
|------|--------|------|
| `session_start.py` | SessionStart | 检查 onboarding 状态，提示加载记忆 |
| `prompt_capture.py` | UserPromptSubmit | 每次提示写入 `wiki/sessions/` |
| `wiki_context_hint.py` | UserPromptSubmit | 检测到"继续""上次""之前"等关键词时建议检索 Wiki |
| `pre_compact_save.py` | PreCompact | 上下文压缩前创建检查点 |
| `memory_audit.py` | Stop | 轻量审计 memory 文件健康状态 |

**6 个 Skills** — 可复用工作流：

| Skill | 用途 |
|-------|------|
| `cc-agent-brain-onboard-user` | 4 阶段分支式初始化 |
| `cc-agent-brain-wiki-update` | 结构化更新 Wiki 页面 |
| `cc-agent-brain-wiki-search` | 先检索 memory/Wiki，再回答用户 |
| `cc-agent-brain-memory-distill` | 从 Wiki 蒸馏信息到 memory |
| `cc-agent-brain-memory-audit` | 审计重复、冲突、过期条目 |
| `cc-agent-brain-material-distill` | 提取可复用文本到 `wiki/materials/` |

**3 个 Agents** — 专项子代理：

| Agent | 用途 |
|-------|------|
| `cc-agent-brain-memory-curator` | 判断哪些 Wiki 内容应蒸馏，检测冲突 |
| `cc-agent-brain-wiki-compiler` | 整理 Wiki 页面，维护索引和交叉链接 |
| `cc-agent-brain-material-distiller` | 从对话中提取可复用素材 |

---

### 仓库结构

```text
cc-agent-brain/
├── installer/              install.py、uninstall.py、update.py
├── package/
│   ├── claude/
│   │   ├── hooks/cc-agent-brain/   5 个钩子 + _utils.py
│   │   ├── skills/                 6 个 SKILL.md
│   │   ├── agents/                 3 个 agent .md
│   │   └── settings.patch.json     hook 配置模板
│   ├── memory_templates/           memory/ 初始模板
│   ├── wiki_templates/             wiki/ 初始模板
│   └── templates/                  写作模板
├── prompts/                 安装/卸载提示词
├── docs/                    架构、内存设计、安装文档
├── examples/                示例项目
├── CHECKLIST.md             发布前检查清单
└── README.md
```

---

### 卸载

```bash
python installer/uninstall.py --target /path/to/your/project
```

卸载器只删除 `.cc-agent-brain/install-manifest.json` 中记录的框架文件。你个人的 `memory/`、`wiki/`、`private/` 内容**不会被删除**。

---

### 路线图

| 版本 | 主题 | 要点 |
|------|------|------|
| **v0.1**（当前） | 本地第二大脑 MVP | 初始化、Wiki 捕获、记忆蒸馏、检索提示 |
| v0.2 | 记忆治理 | 审计、冲突检测、过期与重复清理 |
| v0.3 | 项目智能 | 状态机、决策记录、每周回顾 |
| v0.4 | 可选私有备份 | 私有 GitHub 备份、恢复、完整性校验 |

---

### 隐私

本仓库是**开源框架**，不含任何用户个人知识库数据。用户生成的 `memory/`、`wiki/`、`private/` 应通过 `.gitignore` 排除，不应上传到公开仓库。

---

### 协议

MIT
