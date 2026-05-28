# CC Agent Brain / 第二大脑

**CC Agent Brain** is a local Wiki-first second brain system for Claude Code.

**CC Agent Brain** 是一个面向 Claude Code 的**本地 Wiki 优先第二大脑系统**。通过分支式初始化、自动信息收集、本地 Markdown Wiki、记忆精炼和主动检索，让 Claude Code 在**不依赖云同步**的情况下越用越懂你。

It installs as a **namespaced add-on** inside an existing Claude Code project. It does **not** replace your existing `.claude/` directory.

它以**命名空间附加组件**的形式安装到已有 Claude Code 项目中，**不会**替换你现有的 `.claude/` 目录。

---

## 为什么需要它 / Why this project exists

Many Claude Code users still work like this — 很多用户的日常是这样的：

```text
打开会话 → 重新交代背景 → 解决一个任务 → 有用的上下文全部丢失
open a session → explain the background again → solve one task → lose useful context
```

CC Agent Brain 把流程变成了：

```text
正常使用 Claude Code
    ↓
自动捕获到本地 Wiki
    ↓
结构化的项目 / 素材 / 决策页面
    ↓
蒸馏为压缩的长期记忆
    ↓
记忆不够时回退检索 Wiki
```

Core design — 核心设计原则：

- **本地优先 / Local-first**：一切知识留在本地，不上传云端。
- **Wiki 优先 / Wiki-first**：详细上下文先写入 `wiki/`，不做删减。
- **记忆是压缩的 / Memory is compressed**：只有稳定事实、偏好、活跃项目索引、可复用模式才进入 `memory/`。
- **v0.1 无云同步 / No cloud sync**：GitHub 私有备份是未来可选模块。
- **不冲突 / No conflict**：以 `cc-agent-brain-*` 命名空间安装进已有 `.claude/`。

---

## 快速安装 / Quick install with Claude Code

在你想启用第二大脑的 Claude Code 项目中，粘贴以下 prompt：

Open Claude Code in the project where you want to enable CC Agent Brain, then paste this prompt:

```text
You are helping me install CC Agent Brain into the current Claude Code project.

Goal / 目标:
Install CC Agent Brain as an add-on to the existing project. Do not replace or overwrite my existing `.claude/` directory.
将 CC Agent Brain 以附加组件形式安装到当前项目，不替换已有 .claude/ 目录。

Source / 来源:
GitHub repository: https://github.com/syiibfs-hash/cc-agent-brain

Installation requirements / 安装要求:
1. Download or clone the repository to a temporary directory. — 下载/克隆仓库到临时目录
2. Inspect the current project structure. — 检查当前项目结构
3. If `.claude/` already exists, merge CC Agent Brain files into it. — 合并入已有 .claude/
4. Do not overwrite existing user files. — 不覆盖用户已有文件
5. Add all CC Agent Brain skills under `.claude/skills/cc-agent-brain-*`.
6. Add all CC Agent Brain agents under `.claude/agents/cc-agent-brain-*.md`.
7. Add all CC Agent Brain hooks under `.claude/hooks/cc-agent-brain/`.
8. Merge hook configuration into `.claude/settings.json` instead of replacing the file. — 增量合并 settings
9. Before modifying `.claude/settings.json`, create a backup named `.claude/settings.backup.cc-agent-brain.json`.
10. Create local folders if they do not exist: `memory/`, `wiki/`, `private/`, `templates/`.
11. Do not commit or upload my generated `memory/`, `wiki/`, or `private/` content. — 不上传个人记忆/Wiki
12. After installation, summarize files added, settings merged, files skipped, and next steps.

After installation, trigger the onboarding flow if `memory/profile.md` or `memory/preferences.md` is missing.
安装后如果 memory/profile.md 或 memory/preferences.md 缺失，触发初始化流程。
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

## 安装后目录结构 / What gets installed

```text
my-project/
├── .claude/
│   ├── settings.json                    ← 增量合并，不覆盖
│   ├── settings.backup.cc-agent-brain.json  ← 安装前自动备份
│   ├── skills/
│   │   └── cc-agent-brain-*/           ← 6 个技能
│   ├── agents/
│   │   └── cc-agent-brain-*.md         ← 3 个代理
│   └── hooks/
│       └── cc-agent-brain/             ← 5 个钩子脚本
├── memory/          ← 压缩的长期记忆（profile, preferences, projects）
├── wiki/            ← 详细上下文（sessions, projects, decisions, materials）
├── private/         ← 本地敏感笔记（不参与常规检索）
└── templates/       ← 写作模板
```

CC Agent Brain does not replace your `.claude` directory. It installs as a namespaced add-on and safely merges into your existing Claude Code project configuration.

---

## 功能特性 / Features

### 1. 分支式初始化 / Branching onboarding

Claude Code 分四个阶段询问用户，而不是一次性抛出所有问题：

- 怎么称呼你 / 你想叫 Claude Code 什么 / 我主要扮演什么角色
- 回复风格偏好：简洁还是详细、什么时候可以自己判断、什么时候先问
- 有无长期项目要跟踪
- 捕获强度、记忆蒸馏模式、Wiki 检索偏好

### 2. 静默本地捕获 / Silent local capture

系统自动将**有意义的提示词、任务节点、决策、可复用素材**写入本地 Wiki，不需要用户手动说”记住这个”。

每次提示写入 `wiki/sessions/` 时自动打上标签：`source: user_prompt`、`memory_candidate: pending`，为后续蒸馏做准备。

### 3. Wiki 优先存储 / Wiki-first storage

详细上下文存入 `wiki/` 的七个子目录，不做删减：

```text
wiki/sessions/     ← 按日期记录每次用户提示
wiki/projects/     ← 长期项目页面
wiki/materials/    ← 可复用的 README 片段、演示文稿、提案文字等
wiki/decisions/    ← 关键决策及理由
wiki/prompts/      ← 可复用的提示词
wiki/concepts/     ← 概念解释
wiki/tasks/        ← 任务跟踪与审计报告
```

### 4. 压缩记忆 / Distilled memory

只有**高价值、稳定、可复用**的信息才从 Wiki 蒸馏到 memory：

```text
memory/MEMORY.md           ← 记忆总索引（Claude Code 优先加载）
memory/profile.md          ← 用户身份、称呼、角色
memory/preferences.md      ← 回复风格偏好
memory/active-projects.md  ← 活跃项目状态
memory/stable-facts.md     ← 长期稳定事实
memory/retrieval-policy.md ← 检索优先级策略
```

### 5. 回退检索 / Retrieval fallback

当 memory 找不到足够信息时，Claude Code 会**自动搜索本地 Wiki**，而不是让用户重新交代一遍背景。检索顺序：`memory/ → wiki/index.md → wiki/projects/ → wiki/decisions/ → wiki/materials/ → wiki/sessions/`。

---

## 仓库结构 / Repository structure

```text
cc-agent-brain/
├── installer/              ← install.py、uninstall.py、update.py
├── package/
│   ├── claude/
│   │   ├── hooks/cc-agent-brain/  ← 5 个钩子 + _utils.py
│   │   ├── skills/                ← 6 个 SKILL.md
│   │   ├── agents/                ← 3 个 agent .md
│   │   └── settings.patch.json    ← hook 配置模板
│   ├── memory_templates/          ← memory/ 初始模板
│   ├── wiki_templates/            ← wiki/ 初始模板
│   └── templates/                 ← 写作模板
├── prompts/                 ← 安装/卸载提示词
├── docs/                    ← 架构、内存设计、安装文档
├── examples/                ← 示例项目
├── CHECKLIST.md             ← 发布前检查清单
└── README.md
```

---

## 命令行安装 / Manual installation

```bash
git clone https://github.com/syiibfs-hash/cc-agent-brain.git
cd cc-agent-brain
python installer/install.py --target /path/to/your/project
```

预览模式（不写文件）：

```bash
python installer/install.py --target /path/to/your/project --dry-run
```

---

## 卸载 / Uninstall

```bash
python installer/uninstall.py --target /path/to/your/project
```

卸载器**只删除** `.cc-agent-brain/install-manifest.json` 中记录的框架文件，**不会删除**你个人的 `memory/`、`wiki/`、`private/` 内容。

---

## 路线图 / Roadmap

### v0.1 本地第二大脑 MVP（当前版本）

- 分支式初始化 onboarding
- 安全 `.claude` 增量合并安装器
- 本地 Wiki 目录结构
- 自动会话捕获
- Wiki 优先存储
- 记忆蒸馏
- Wiki 检索提示

### v0.2 记忆治理 / Memory governance

- 记忆审计
- 冲突检测
- 过期记忆检测
- 重复记忆清理

### v0.3 项目智能 / Project intelligence

- 项目状态机
- 决策记录
- 素材蒸馏
- 每周回顾

### v0.4 可选私有备份 / Optional private backup

- 私有 GitHub 备份
- 从备份恢复
- 备份完整性校验

---

## 隐私 / Privacy

本仓库是**开源框架**，不包含任何用户个人知识库数据。

用户项目中生成的 `memory/`、`wiki/`、`private/` 内容应通过 `.gitignore` 排除，无需也不应上传到公开仓库。

---

## 协议 / License

MIT
