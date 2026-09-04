# CC Agent Brain

[English](#english) | [中文](#中文)

A **local-first memory engine** for coding agents. It captures what you and the
agent actually do, distills it into versioned long-term memory, and recalls it
automatically — fully offline, with **zero third-party dependencies**, and
exposed to any tool through **MCP**. Installs as a namespaced add-on and never
replaces your existing `.claude/` directory.

---

## English

### What is CC Agent Brain

CC Agent Brain turns a stateless coding agent into one that remembers you across
sessions and across tools — all locally, no cloud, no API key.

```text
user prompts / assistant replies / tool actions
        ↓ automatic hooks
append-only event stream (SQLite + FTS5)  +  readable Wiki (Markdown)
        ↓ distill
versioned long-term memory (layered, bi-temporal, auditable)
        ↓ BM25 + RRF retrieval, project DB first / global DB fallback
automatic recall in future sessions
        ↓ MCP server
the same memory in Claude Code, Cursor, Codex, Gemini CLI, Claude Desktop…
```

### Why it exists (2026 memory landscape)

Agent memory is becoming standard infrastructure, but existing choices force a
trade-off: cloud memory APIs send your data away; heavy self-hosted stacks need
vector/graph databases; plain Markdown memory does not actually search or
version itself. CC Agent Brain occupies the middle:

- **Zero-dependency engine** — Python stdlib `sqlite3` + FTS5 (BM25), including
  CJK bigram tokenization, so Chinese and English retrieval both work offline.
- **Real capture loop** — user prompts *and* assistant replies / tool calls are
  indexed (Stop hook reads the transcript; idempotent).
- **Versioned, trustworthy memory** — facts are *superseded/expired*, never
  silently overwritten; a timeline shows what changed and when.
- **MCP-native, tool-agnostic** — one memory store for every MCP client.
- **Human-readable projection** — Markdown Wiki and generated indexes keep you
  in control; the DB is a single portable file.
- **Private by construction** — common secret shapes are redacted at capture
  time; personal data is git-ignored.

### Quick install

```bash
git clone https://github.com/syiibfs-hash/cc-agent-brain.git
cd cc-agent-brain
python installer/install.py --target /path/to/your/project
# preview first:
python installer/install.py --target /path/to/your/project --dry-run
```

Or paste the install prompt from `prompts/install-from-github.md` into Claude Code.

### What gets installed

```text
my-project/
├── .claude/
│   ├── settings.json                         ← merged, not replaced (+ backup)
│   ├── skills/cc-agent-brain-*/              ← 6 skills
│   ├── agents/cc-agent-brain-*.md            ← 3 agents
│   └── hooks/cc-agent-brain/                 ← 6 hooks + engine + _utils
│       ├── brain_store.py                    ← SQLite/FTS5 engine + MCP server
│       ├── transcript_capture.py             ← indexes assistant/tool actions
│       └── …
├── .cc-agent-brain/brain.db                  ← local engine DB (git-ignored)
├── memory/     compressed long-term memory + generated index
├── wiki/       detailed human-readable context
├── private/    local sensitive notes
└── templates/  writing templates
```

### The engine CLI

```bash
BRAIN="python .claude/hooks/cc-agent-brain/brain_store.py"
$BRAIN init
$BRAIN search "deployment decision" --human
$BRAIN memory add --title "..." --body "..." --layer semantic --confidence high
$BRAIN memory add ... --supersedes <old-id>   # replace, keep history
$BRAIN audit / timeline / stats / candidates
$BRAIN sync-md                                # regenerate memory projection
$BRAIN serve-mcp                              # MCP server over stdio
```

Full reference: [`docs/memory-engine.md`](docs/memory-engine.md), MCP setup:
[`docs/mcp.md`](docs/mcp.md).

### Components

**6 Hooks**

| Hook | Event | Purpose |
|------|-------|---------|
| `session_start.py` | SessionStart | onboarding check, engine status |
| `prompt_capture.py` | UserPromptSubmit | prompt → Wiki projection + event stream |
| `wiki_context_hint.py` | UserPromptSubmit | real FTS recall for the current prompt |
| `transcript_capture.py` | Stop | index assistant replies & tool calls |
| `pre_compact_save.py` | PreCompact | checkpoint before compaction |
| `memory_audit.py` | Stop | SQL audit: duplicates, broken chains, stale entries |

**6 Skills** — onboarding, wiki update/search, memory distill/audit, material distill.
**3 Agents** — memory curator, wiki compiler, material distiller.

### Memory model

Four layers — `working` (current task), `episodic` (timestamped events),
`semantic` (distilled facts/preferences), `procedural` (reusable workflows).
Each memory has status (`active/superseded/expired/archived`), validity window,
confidence, source and supersede chain. See [`docs/memory-design.md`](docs/memory-design.md).

### Uninstall

```bash
python installer/uninstall.py --target /path/to/your/project
```

Only framework files tracked by the manifest are removed. Your `memory/`,
`wiki/`, `private/` and `brain.db` are preserved.

### Roadmap

| Version | Theme | Status |
|---------|-------|--------|
| v0.1 | Local second-brain MVP (capture/wiki/distill hints) | released |
| **v0.2** | **Local engine: SQLite+FTS5, full capture, versioned memory, audit, MCP** | **current** |
| v0.3 | Recall quality: optional local embeddings + RRF, built-in recall eval set | planned |
| v0.4 | Portability: Marketplace packaging, one-line install, import/export | planned |
| v0.5 | Optional E2E-encrypted private backup (local-first by default) | planned |

### Privacy

Open-source framework, no personal data inside. Everything runs on your machine;
there is no telemetry and no network call. `memory/`, `wiki/`, `private/` and
`*.db` are git-ignored. See [`docs/product-analysis.md`](docs/product-analysis.md)
for the product rationale.

### License

MIT

---

## 中文

### CC Agent Brain 是什么

给编码 Agent 用的**本地记忆引擎**：自动捕获你和 Agent 的真实工作过程，蒸馏成带版本的长期记忆，并在后续会话自动召回——全程离线、**零第三方依赖**，并通过 **MCP** 把同一份记忆提供给任意工具。以命名空间插件方式安装，**绝不覆盖**你已有的 `.claude/`。

```text
用户提示 / 助手回复 / 工具动作
        ↓ 钩子自动捕获
只增事件流（SQLite + FTS5） + 可读 Wiki（Markdown）
        ↓ 蒸馏
带版本的长期记忆（分层、双时间、可审计）
        ↓ BM25 + RRF 检索，项目库优先 / 全局库兜底
后续会话自动召回
        ↓ MCP 服务
同一套记忆服务 Claude Code、Cursor、Codex、Gemini CLI、Claude Desktop…
```

### 为什么做它（2026 记忆赛道现状）

Agent 记忆正在成为基础设施，但现有方案都要你做取舍：云记忆 API 要上传数据；重型自建方案要装向量/图数据库；纯 Markdown 记忆既不能真正检索也没有版本。CC Agent Brain 取中间路线：

- **零依赖引擎**：仅用 Python 标准库 sqlite3 + FTS5（BM25），内置中文 bigram 分词，中英文检索全部离线可用。
- **完整捕获闭环**：不只存用户提问，Stop 钩子读取会话记录，把助手回复与工具调用一并索引（幂等）。
- **可信的版本化记忆**：事实变更走"取代/失效"而非静默覆盖，时间线可查"何时因为什么改了结论"。
- **MCP 原生、不绑工具**：一套记忆，所有 MCP 客户端复用。
- **人类可读投影**：Markdown Wiki 与生成式索引让你始终掌控；数据库只是一个可拷贝的文件。
- **隐私内建**：常见密钥形态在捕获时即脱敏，个人数据默认 git 忽略。

### 快速安装

```bash
git clone https://github.com/syiibfs-hash/cc-agent-brain.git
cd cc-agent-brain
python installer/install.py --target /path/to/your/project
# 先预览：
python installer/install.py --target /path/to/your/project --dry-run
```

也可以把 `prompts/install-from-github.md` 中的安装提示词粘贴给 Claude Code。

### 安装内容

```text
my-project/
├── .claude/
│   ├── settings.json                         ← 增量合并（自动备份）
│   ├── skills/cc-agent-brain-*/              ← 6 个技能
│   ├── agents/cc-agent-brain-*.md            ← 3 个代理
│   └── hooks/cc-agent-brain/                 ← 6 个钩子 + 引擎 + 工具库
│       ├── brain_store.py                    ← SQLite/FTS5 引擎 + MCP 服务
│       ├── transcript_capture.py             ← 索引助手回复/工具动作
│       └── …
├── .cc-agent-brain/brain.db                  ← 本地引擎库（git 忽略）
├── memory/     压缩长期记忆 + 生成式索引
├── wiki/       详细的人类可读上下文
├── private/    本地敏感笔记
└── templates/  写作模板
```

### 引擎命令行

```bash
BRAIN="python .claude/hooks/cc-agent-brain/brain_store.py"
$BRAIN init
$BRAIN search "部署方案的决策" --human
$BRAIN memory add --title "..." --body "..." --layer semantic --confidence high
$BRAIN memory add ... --supersedes <旧id>     # 取代并保留历史
$BRAIN audit / timeline / stats / candidates
$BRAIN sync-md                                # 重新生成记忆投影
$BRAIN serve-mcp                              # 以 stdio 启动 MCP 服务
```

完整说明见 [`docs/memory-engine.md`](docs/memory-engine.md)，MCP 接入见 [`docs/mcp.md`](docs/mcp.md)。

### 组件

**6 个 Hooks**

| Hook | 触发点 | 功能 |
|------|--------|------|
| `session_start.py` | SessionStart | 初始化检查、引擎状态 |
| `prompt_capture.py` | UserPromptSubmit | 提示写入 Wiki 投影与事件流 |
| `wiki_context_hint.py` | UserPromptSubmit | 对当前问题做真实 FTS 召回 |
| `transcript_capture.py` | Stop | 索引助手回复与工具调用 |
| `pre_compact_save.py` | PreCompact | 压缩前检查点 |
| `memory_audit.py` | Stop | SQL 审计：重复、断链、过期、积压 |

**6 个 Skills**：初始化、Wiki 更新/检索、记忆蒸馏/审计、素材蒸馏。
**3 个 Agents**：记忆策展人、Wiki 编纂者、素材提炼者。

### 记忆模型

四层——`working`（当前任务）、`episodic`（带时间戳的事件）、`semantic`（蒸馏事实与偏好）、`procedural`（可复用流程）。每条记忆带状态（active/superseded/expired/archived）、有效期、置信度、来源与取代链。详见 [`docs/memory-design.md`](docs/memory-design.md)。

### 卸载

```bash
python installer/uninstall.py --target /path/to/your/project
```

只删除清单中记录的框架文件；`memory/`、`wiki/`、`private/` 与 `brain.db` 全部保留。

### 路线图

| 版本 | 主题 | 状态 |
|------|------|------|
| v0.1 | 本地第二大脑 MVP（捕获/Wiki/蒸馏提示） | 已发布 |
| **v0.2** | **本地引擎：SQLite+FTS5、全量捕获、版本化记忆、审计、MCP** | **当前** |
| v0.3 | 召回质量：可选本地向量 + RRF、内置召回评测集 | 规划中 |
| v0.4 | 可移植：Marketplace 打包、一行安装、导入导出 | 规划中 |
| v0.5 | 可选端到端加密私有备份（默认仍纯本地） | 规划中 |

### 隐私

开源框架，仓库内不含任何个人数据。所有计算在本机完成，无遥测、无网络请求。`memory/`、`wiki/`、`private/` 与 `*.db` 均被 git 忽略。产品层面的完整分析见 [`docs/product-analysis.md`](docs/product-analysis.md)。

### 协议

MIT
