# CC Agent Brain

[English](#english) | [中文](#中文)

A local memory add-on for **Claude Code**. Hooks under `.claude/` append
prompts, assistant text, and tool-call inputs to a SQLite + FTS5 file, and a
`UserPromptSubmit` hook prints keyword matches back into later Claude Code
sessions. Long-term memories are written only when you or a skill runs
`memory add`. A stdio MCP server and a CLI read the same file. The installer
merges a `cc-agent-brain` namespace into an existing project and does not
replace `.claude/`.

Python standard library only (`sqlite3`). No network calls, no API key.

---

## English

### What this tree does

```text
Claude Code hooks (.claude/settings.json)
  UserPromptSubmit  prompt_capture.py       user prompt → event + wiki/sessions
  UserPromptSubmit  wiki_context_hint.py    FTS recall printed for Claude Code
  Stop              transcript_capture.py   assistant text + tool_use inputs
  Stop              memory_audit.py         SQL audit report
  PreCompact        pre_compact_save.py     marker file + system event
  SessionStart      session_start.py        onboarding check + engine stats
        ↓
.cc-agent-brain/brain.db   (events + memories, FTS5 / BM25)
        ↓
search fuses lexical hit lists with RRF
  active memories, events, and the same two lists from
  ~/.cc-agent-brain/brain.db when that file already exists
        ↓
long-term rows appear after an explicit `memory add`
(no model in this repository distills them for you)
        ↓
optional `serve-mcp`   stdio; initialize → 2024-11-05, or 2026-07-28 via _meta
```

### Current scope

These limits match `package/claude/hooks/cc-agent-brain/` and `installer/` in
this repository.

1. **Auto-capture is Claude Code.** The six hooks are Claude Code events
   (`SessionStart`, `UserPromptSubmit`, `PreCompact`, `Stop`) merged into
   `.claude/settings.json`. `transcript_capture.py` reads the Claude Code
   transcript JSONL (`transcript_path`) and indexes assistant text plus
   `tool_use` name/input. It skips `tool_result` payloads. Cursor, Codex,
   Gemini CLI, and Claude Desktop have no capture hooks and no automatic
   recall. The installer does write project MCP entries for Claude Code,
   Cursor, and Codex that launch this same `serve-mcp`. Those entries do not
   capture sessions. Gemini CLI and Claude Desktop get no config from the
   installer.
2. **Retrieval is lexical multi-path FTS.** Active memories and events are
   ranked with FTS5 `bm25()` after CJK-bigram tokenization. Reciprocal rank
   fusion (`rrf_fuse`) merges those ranked lists: project memories, project
   events, and, when `~/.cc-agent-brain/brain.db` exists, the global memories
   and events as well. Both sides are keyword search. This is not
   lexical-plus-vector hybrid retrieval. No embedding model and no vector
   index are queried. A vector channel is later work and is not part of
   `search` today. "Project first, global fallback" is also inaccurate: when
   the global file exists, its lists are fused in the same RRF call, not used
   only after the project search misses.
3. **Validity columns are stored. As-of queries are not implemented.** Each
   memory row has `valid_from`, `valid_to`, `created_at`, and `updated_at`.
   `memory add --supersedes` and `memory expire` keep the old row, set its
   status, and fill `valid_to`. `search` returns rows with `status='active'`
   only. `timeline` lists recent memory rows ordered by `updated_at`. No
   command takes a past timestamp and returns the store as of that time.
4. **The MCP server speaks both `2024-11-05` and `2026-07-28` on one stdio
   process.** `initialize`, with no modern envelope, still returns
   `protocolVersion` `2024-11-05`, `capabilities: {tools: {}}`, and
   `serverInfo.version` `"2"` (the schema id). `ping`, `tools/list`, and
   `tools/call` on that path omit `resultType`. A request whose `params._meta`
   has both `io.modelcontextprotocol/protocolVersion` (string) and
   `io.modelcontextprotocol/clientCapabilities` (object) is the modern era.
   When that version is `2026-07-28`, `server/discover`, `tools/list`, and
   `tools/call` return `resultType: "complete"` and
   `_meta["io.modelcontextprotocol/serverInfo"]` with version `0.2.0`.
   `server/discover` lists `supportedVersions` as `2026-07-28` then
   `2024-11-05`. Any other version string on that envelope returns JSON-RPC
   `-32022` with `data.supported` and `data.requested`. Either kind of modern
   envelope sticks for that process, so a later `initialize` returns `-32022`
   too. A process that only sends `initialize` is unchanged. Messages without
   an `id` get no response. Details:
   [`docs/mcp.md`](docs/mcp.md). Speaking the protocol does not add
   auto-capture for other clients.
5. **A second run upgrades framework files and merges MCP config.**
   `installer/update.py` calls `install.py` again. It overwrites
   `.claude/hooks/cc-agent-brain/`, `.claude/skills/cc-agent-brain-*/`, and
   `.claude/agents/cc-agent-brain-*.md` with the copies from this package. It
   does not replace the rest of `.claude/`. `memory/`, `wiki/`, `private/`,
   and template files that already exist stay as they are.
   `.cc-agent-brain/brain.db` is not replaced or deleted. The installer runs
   `brain_store.py init` on that file even when it already exists
   (`engine_state` is `migrated` when the file was already there, and
   `initialized` when it was created). `_migrate()` creates missing tables;
   rows already in the file stay. Hook merge appends Claude Code hook entries
   that are not already in `settings.json`. The same run merges one stdio
   server named `cc-agent-brain` into `.mcp.json`, `.cursor/mcp.json`, and
   `.codex/config.toml`, and leaves other servers in those files alone. A
   config that does not parse is left untouched. See
   [`docs/install.md`](docs/install.md).
6. **There is no shared multi-agent memory service.** Hooks write the project
   database for the current working directory. They never pass `--global`.
   Nothing in this tree namespaces memory per agent or runs a shared daemon.
   Several local MCP processes can still open one global SQLite file. Point
   `serve-mcp` at it with `--global` or `CC_AGENT_BRAIN_GLOBAL_DIR` (default
   `~/.cc-agent-brain/`, which also holds `library.md`). Set
   `CC_AGENT_BRAIN_WRITER`, or pass `writer` on the write. The engine stores
   that string. It does not detect Cursor versus Codex. `library.md` is
   rebuilt from active memories and from event counts. Event text stays in
   SQLite. The installer does not create this directory and does not retarget
   the three project MCP entries. There is no cross-machine sync. `search`
   still fuses the global file when it exists and is not the file already
   open. See [`docs/mcp.md`](docs/mcp.md).

### Quick install

```bash
git clone https://github.com/syiibfs-hash/cc-agent-brain.git
cd cc-agent-brain
python installer/install.py --target /path/to/your/project
# preview first:
python installer/install.py --target /path/to/your/project --dry-run
```

Or paste the install prompt from `prompts/install-from-github.md` into Claude Code.

Hooks are Claude Code. The same install also writes the Cursor and Codex MCP
entries described below. See [`docs/install.md`](docs/install.md).

### What gets installed

```text
my-project/
├── .claude/
│   ├── settings.json                         ← Claude Code hooks merged (+ backup)
│   ├── skills/cc-agent-brain-*/              ← 6 skills
│   ├── agents/cc-agent-brain-*.md            ← 3 agents
│   └── hooks/cc-agent-brain/                 ← 6 hooks + engine + _utils
│       ├── brain_store.py                    ← SQLite/FTS5 engine + dual-era MCP
│       ├── transcript_capture.py             ← Claude Code transcript → events
│       └── …
├── .cc-agent-brain/brain.db                  ← project DB (git-ignored; not replaced on upgrade)
├── .mcp.json                                 ← Claude Code stdio MCP, this server only
├── .cursor/mcp.json                          ← Cursor stdio MCP, this server only
├── .codex/config.toml                        ← Codex MCP table, this server only
├── memory/     Markdown memory (existing files kept)
├── wiki/       human-readable notes (existing files kept)
├── private/    local notes (existing files kept)
└── templates/  writing templates (existing files kept)
```

A second run overwrites the namespaced hooks, skills, and agents, runs
`init` against an existing `brain.db`, and merges the three MCP entries. It
does not overwrite `memory/`, `wiki/`, `private/`, existing templates, or the
database file.

`~/.cc-agent-brain/brain.db` is not created by the installer. Create and write
it yourself with `--global` if you want `search` to fuse that file in. The
same directory's `library.md` is maintained from that store. See
[`docs/mcp.md`](docs/mcp.md).

### The engine CLI

```bash
BRAIN="python .claude/hooks/cc-agent-brain/brain_store.py"
$BRAIN init
$BRAIN search "deployment decision" --human
$BRAIN memory add --title "..." --body "..." --layer semantic --confidence high
$BRAIN memory add ... --supersedes <old-id>   # new row; old row kept as superseded
$BRAIN audit / timeline / stats / candidates
$BRAIN sync-md                                # regenerate memory/brain-index.generated.md
$BRAIN serve-mcp                              # stdio MCP: 2024-11-05 and 2026-07-28
```

Reference: [`docs/memory-engine.md`](docs/memory-engine.md). MCP methods and
the protocol version: [`docs/mcp.md`](docs/mcp.md).

### Components

**6 hooks, all Claude Code**

| Hook | Claude Code event | What it does |
|------|-------------------|--------------|
| `session_start.py` | SessionStart | onboarding check, engine counts |
| `prompt_capture.py` | UserPromptSubmit | user prompt → `wiki/sessions` + an event |
| `wiki_context_hint.py` | UserPromptSubmit | FTS recall printed for this Claude Code turn |
| `transcript_capture.py` | Stop | assistant text and `tool_use` inputs from the Claude Code transcript (idempotent). Skips tool results |
| `pre_compact_save.py` | PreCompact | writes a marker note and a system event. Does not copy the conversation |
| `memory_audit.py` | Stop | SQL audit: duplicate active rows, broken supersede links, stale rows, empty memory set |

**6 skills** — onboarding, wiki update/search, memory distill/audit, material distill.
Distill skills tell the agent to call `memory add`. They are not an automatic
capture pipeline.

**3 agents** — memory curator, wiki compiler, material distiller.

### Memory records

Layers: `working`, `episodic`, `semantic`, `procedural`.
Status: `active`, `superseded`, `expired`, `archived`.
Columns include `valid_from`, `valid_to`, `confidence`, `source`, `writer`, `supersedes`,
`created_at`, `updated_at`. Active search does not filter on the validity
columns, and there is no as-of query. See [`docs/memory-design.md`](docs/memory-design.md).

### Uninstall

```bash
python installer/uninstall.py --target /path/to/your/project
```

The uninstaller removes framework files recorded in the install manifest and
strips Claude Code hook entries whose JSON contains `cc-agent-brain`. It
leaves `memory/`, `wiki/`, `private/`, and `brain.db` in place. It does not
rewrite `.mcp.json`, `.cursor/mcp.json`, or `.codex/config.toml`.

### Shipped, and what is still absent

Shipped today is the Claude Code hook loop, the SQLite/FTS5 engine, lexical
RRF across those FTS lists, supersede/expire rows, the audit CLI, the
dual-era stdio MCP server (`initialize` → `2024-11-05`; `2026-07-28` via
`server/discover` and `_meta`), an upgrade that overwrites the namespaced
framework files, the three project MCP config merges, and an optional shared
global library (`--global`, writer on inserts, `library.md`). The installer
does not point those MCP entries at the global file.

Still unshipped, and not implemented in this repository:

- auto-capture or automatic recall for Cursor, Codex, Gemini CLI, Claude Desktop, or other clients
- vector search, embeddings, or lexical-plus-vector hybrid retrieval
- as-of / time-travel queries
- a shared daemon, per-agent namespaces, or cross-machine sync (local MCP processes can open one global SQLite file; see [`docs/mcp.md`](docs/mcp.md))

Older roadmap notes (not a commitment, and not a description of this tree):

| Label | Idea | Status |
|-------|------|--------|
| v0.1 | Markdown scaffold, capture hints | released earlier |
| v0.2 | SQLite + FTS5, Claude Code capture hooks, versioned rows, audit, dual-era MCP (`2024-11-05` and `2026-07-28`) | this tree (`installer` / `PRODUCT_VERSION` `0.2.0`) |
| v0.3 idea | optional local vector channel, recall eval set | not shipped |
| v0.4 idea | marketplace packaging, import/export | not shipped |
| v0.5 idea | optional encrypted backup | not shipped |

### Privacy

The framework ships no personal data. Engine and hooks do not open network
connections. `memory/`, `wiki/`, `private/`, and `*.db` are git-ignored.
Secret redaction at write time is best-effort pattern replacement. See
[`docs/memory-engine.md`](docs/memory-engine.md). Product notes:
[`docs/product-analysis.md`](docs/product-analysis.md).

### License

MIT

---

## 中文

### 这个仓库现在做什么

给 **Claude Code** 用的本地记忆附加组件。`.claude/` 里的钩子把用户提示、助手正文和工具调用入参写进 SQLite + FTS5；`UserPromptSubmit` 钩子会在后续 Claude Code 回合里打印关键词命中。长期记忆只有在你或某个 skill 执行 `memory add` 时才会写入。同一个库可以用命令行读，也可以用一个 stdio MCP 服务读。安装器把 `cc-agent-brain` 命名空间合并进现有项目，不替换整个 `.claude/`。

只依赖 Python 标准库 `sqlite3`。引擎和钩子不发起网络请求，也不需要 API key。

```text
Claude Code 钩子（.claude/settings.json）
  UserPromptSubmit  prompt_capture.py       用户提示 → 事件 + wiki/sessions
  UserPromptSubmit  wiki_context_hint.py    把 FTS 命中打印给 Claude Code
  Stop              transcript_capture.py   助手正文 + tool_use 入参
  Stop              memory_audit.py         SQL 审计输出
  PreCompact        pre_compact_save.py     标记文件 + 一条 system 事件
  SessionStart      session_start.py        初始化检查 + 引擎计数
        ↓
.cc-agent-brain/brain.db   （事件 + 记忆，FTS5 / BM25）
        ↓
search 用 RRF 融合多路词法命中
  活跃记忆、事件；若 ~/.cc-agent-brain/brain.db 已存在，全局库的两路列表也一起融合
        ↓
长期记忆行来自显式的 `memory add`
（本仓库里没有模型会自动蒸馏）
        ↓
可选 `serve-mcp`   stdio；initialize → 2024-11-05，或经 _meta 走 2026-07-28
```

### 当前范围

下面每条都对得上本仓库的 `package/claude/hooks/cc-agent-brain/` 和 `installer/`。

1. **自动捕获只服务 Claude Code。** 六个钩子都是 Claude Code 事件（`SessionStart`、`UserPromptSubmit`、`PreCompact`、`Stop`），合并进 `.claude/settings.json`。`transcript_capture.py` 读取 Claude Code transcript JSONL（`transcript_path`），索引助手正文和 `tool_use` 的名称与入参，并跳过 `tool_result`。Cursor、Codex、Gemini CLI、Claude Desktop 没有捕获钩子，也没有自动召回。安装器会给 Claude Code、Cursor、Codex 写入指向同一个 `serve-mcp` 的项目 MCP 配置，这些条目不捕获会话。Gemini CLI 和 Claude Desktop 不会得到配置文件。
2. **检索是多路词法 FTS，再用 RRF 融合。** 活跃记忆和事件用 FTS5 `bm25()` 排序（含中文 bigram）。`rrf_fuse` 合并这些词法列表：项目库的记忆、项目库的事件，以及 `~/.cc-agent-brain/brain.db` 已经存在时的全局记忆和全局事件。每一路都是关键词检索，不是词法加向量的混合检索。没有任何 embedding 或向量索引参与 `search`。向量通道是以后的工作，现在不在检索路径里。所谓「项目库优先、全局库兜底」也不准确：全局库文件存在时，它的列表会进入同一次 RRF，而不是等项目库没有命中再用。
3. **表里有时间字段，没有 as-of 历史查询。** 每条记忆有 `valid_from`、`valid_to`、`created_at`、`updated_at`。`memory add --supersedes` 和 `memory expire` 会留下旧行、改状态并写入 `valid_to`。`search` 只返回 `status='active'` 的行。`timeline` 按 `updated_at` 列出最近的记忆行。没有任何命令接受一个过去的时间点并返回当时的库内容。
4. **MCP 服务器在同一个 stdio 进程上同时说 `2024-11-05` 和 `2026-07-28`。** 没有现代信封时，`initialize` 仍返回 `protocolVersion` `2024-11-05`、`capabilities: {tools: {}}`，以及 `serverInfo.version` `"2"`（这是 schema id）。这条路径上的 `ping`、`tools/list`、`tools/call` 不带 `resultType`。`params._meta` 里同时有字符串 `io.modelcontextprotocol/protocolVersion` 和对象 `io.modelcontextprotocol/clientCapabilities` 时走现代协议。版本是 `2026-07-28` 时，`server/discover`、`tools/list`、`tools/call` 返回 `resultType: "complete"`，并在 `_meta["io.modelcontextprotocol/serverInfo"]` 里放版本 `0.2.0`。`server/discover` 的 `supportedVersions` 先是 `2026-07-28`，然后是 `2024-11-05`。该信封上的其他版本字符串返回 JSON-RPC `-32022`，`data` 里有 `supported` 和 `requested`。成功的 `2026-07-28` 请求和这种被拒绝的现代信封都会把该进程固定在现代时代，之后的 `initialize` 也返回 `-32022`。只发 `initialize` 的进程保持旧握手。没有 `id` 的消息不会得到响应。细节见 [`docs/mcp.md`](docs/mcp.md)。协议能对上，并不等于其他客户端有了自动捕获。
5. **再次运行会升级框架文件，并合并 MCP 配置。** `installer/update.py` 再次调用 `install.py`。它覆盖 `.claude/hooks/cc-agent-brain/`、`.claude/skills/cc-agent-brain-*/` 和 `.claude/agents/cc-agent-brain-*.md`。它不替换整个 `.claude/`。已存在的 `memory/`、`wiki/`、`private/` 和模板文件保持原样。`.cc-agent-brain/brain.db` 不会被替换或删除。即使库已经存在，安装器也会对它执行 `brain_store.py init`（文件已存在时 `engine_state` 为 `migrated`，新建时为 `initialized`）。`_migrate()` 只补建缺失的表，已有记忆行还在。settings 合并只追加还没有的 Claude Code 钩子。同一次运行把名为 `cc-agent-brain` 的一条 stdio 服务合并进 `.mcp.json`、`.cursor/mcp.json` 和 `.codex/config.toml`，其他服务保留。解析失败的配置文件保持不动。详见 [`docs/install.md`](docs/install.md)。
6. **没有多 Agent 共享记忆服务。** 钩子写入当前工作目录下的项目库，并且不会传 `--global`。本仓库没有按 Agent 分命名空间，也没有共享守护进程。多个本地 MCP 进程仍然可以打开同一份全局 SQLite。用 `--global` 或 `CC_AGENT_BRAIN_GLOBAL_DIR` 把 `serve-mcp` 指过去（默认目录是 `~/.cc-agent-brain/`，里面还有 `library.md`）。设置 `CC_AGENT_BRAIN_WRITER`，或在写入时传 `writer`。引擎只保存这个字符串，不会判断当前是 Cursor 还是 Codex。`library.md` 由活跃记忆和事件计数重新生成，事件原文留在 SQLite。安装器不会创建这个目录，也不会把三条项目 MCP 配置改指到全局库。没有跨机器同步。全局库文件存在、且不是当前打开的那个文件时，`search` 仍会把它的列表融合进去。详见 [`docs/mcp.md`](docs/mcp.md)。

### 快速安装

```bash
git clone https://github.com/syiibfs-hash/cc-agent-brain.git
cd cc-agent-brain
python installer/install.py --target /path/to/your/project
# 先预览：
python installer/install.py --target /path/to/your/project --dry-run
```

也可以把 `prompts/install-from-github.md` 里的提示词粘贴到 Claude Code。钩子属于 Claude Code。同一次安装还会写入下面的 Cursor 和 Codex MCP 条目。详见 [`docs/install.md`](docs/install.md)。

### 安装内容

```text
my-project/
├── .claude/
│   ├── settings.json                         ← 合并 Claude Code 钩子（并备份）
│   ├── skills/cc-agent-brain-*/              ← 6 个技能
│   ├── agents/cc-agent-brain-*.md            ← 3 个代理
│   └── hooks/cc-agent-brain/                 ← 6 个钩子 + 引擎 + 工具库
│       ├── brain_store.py                    ← SQLite/FTS5 引擎 + 双协议 MCP
│       ├── transcript_capture.py             ← Claude Code transcript → 事件
│       └── …
├── .cc-agent-brain/brain.db                  ← 项目库（git 忽略；升级不替换这个文件）
├── .mcp.json                                 ← Claude Code stdio MCP，只合并本服务
├── .cursor/mcp.json                          ← Cursor stdio MCP，只合并本服务
├── .codex/config.toml                        ← Codex MCP 表，只合并本服务
├── memory/     Markdown 记忆（已有文件保留）
├── wiki/       可读笔记（已有文件保留）
├── private/    本地笔记（已有文件保留）
└── templates/  写作模板（已有文件保留）
```

再次运行会覆盖命名空间里的钩子、技能和代理，对已有 `brain.db` 执行 `init`，并合并上面三个 MCP 条目。它不覆盖 `memory/`、`wiki/`、`private/`、已有模板或数据库文件本身。

安装器不会创建 `~/.cc-agent-brain/brain.db`。只有你自己用 `--global` 建好并写入之后，`search` 才会把这个文件融合进去。同一目录下的 `library.md` 会跟着这份库更新。详见 [`docs/mcp.md`](docs/mcp.md)。

### 引擎命令行

```bash
BRAIN="python .claude/hooks/cc-agent-brain/brain_store.py"
$BRAIN init
$BRAIN search "部署方案的决策" --human
$BRAIN memory add --title "..." --body "..." --layer semantic --confidence high
$BRAIN memory add ... --supersedes <旧id>     # 新行；旧行保留为 superseded
$BRAIN audit / timeline / stats / candidates
$BRAIN sync-md                                # 重新生成 memory/brain-index.generated.md
$BRAIN serve-mcp                              # stdio MCP：2024-11-05 与 2026-07-28
```

完整说明见 [`docs/memory-engine.md`](docs/memory-engine.md)。MCP 方法与协议版本见 [`docs/mcp.md`](docs/mcp.md)。

### 组件

**6 个钩子，全部是 Claude Code 事件**

| Hook | Claude Code 事件 | 实际行为 |
|------|------------------|----------|
| `session_start.py` | SessionStart | 初始化检查、引擎计数 |
| `prompt_capture.py` | UserPromptSubmit | 用户提示写入 `wiki/sessions` 和事件流 |
| `wiki_context_hint.py` | UserPromptSubmit | 把 FTS 命中打印到当前 Claude Code 回合 |
| `transcript_capture.py` | Stop | 从 Claude Code transcript 索引助手正文和 `tool_use` 入参（幂等），跳过 tool result |
| `pre_compact_save.py` | PreCompact | 写一份标记笔记和一条 system 事件，不复制对话内容 |
| `memory_audit.py` | Stop | SQL 审计：重复的 active 行、断开的 supersede、陈旧行、还没有任何记忆 |

**6 个 Skills**：初始化、Wiki 更新/检索、记忆蒸馏/审计、素材蒸馏。蒸馏 skill 是让 Agent 去执行 `memory add`，不是自动捕获流水线。

**3 个 Agents**：记忆策展人、Wiki 编纂者、素材提炼者。

### 记忆记录

四层：`working`、`episodic`、`semantic`、`procedural`。状态：`active`、`superseded`、`expired`、`archived`。列里包括 `valid_from`、`valid_to`、置信度、来源、`writer`、`supersedes`、`created_at`、`updated_at`。活跃检索不按这些时间列过滤，也没有 as-of 查询。详见 [`docs/memory-design.md`](docs/memory-design.md)。

### 卸载

```bash
python installer/uninstall.py --target /path/to/your/project
```

卸载器删除安装清单里记录的框架文件，并去掉 JSON 里含 `cc-agent-brain` 的 Claude Code 钩子。`memory/`、`wiki/`、`private/` 和 `brain.db` 保留。它不改写 `.mcp.json`、`.cursor/mcp.json` 或 `.codex/config.toml`。

### 已经交付，以及仍然没有的

当前交付的是：Claude Code 钩子闭环、SQLite/FTS5 引擎、对这些 FTS 列表做的词法 RRF、supersede/expire 行、审计 CLI、双协议 stdio MCP（`initialize` → `2024-11-05`；`2026-07-28` 走 `server/discover` 和 `_meta`）、会覆盖命名空间框架文件的升级、三份项目 MCP 配置的合并，以及可选的本机全局库（`--global`、写入时的 writer、`library.md`）。安装器不会把那三条 MCP 配置改指到全局库。

下面这些还没有实现，不要当成已有能力：

- Cursor、Codex、Gemini CLI、Claude Desktop 或其他客户端的自动捕获与自动召回
- 向量检索、embedding，或词法加向量的混合检索
- as-of / 按历史时点查询
- 共享守护进程、按 Agent 分命名空间，或跨机器同步（多个本地 MCP 进程可以打开同一份全局 SQLite，见 [`docs/mcp.md`](docs/mcp.md)）

旧路线图里的想法只是笔记，不是本仓库的现状，也不是交付承诺：

| 标记 | 想法 | 状态 |
|------|------|------|
| v0.1 | Markdown 脚手架与捕获提示 | 更早发布 |
| v0.2 | SQLite + FTS5、Claude Code 捕获钩子、带版本的行、审计、双协议 MCP（`2024-11-05` 与 `2026-07-28`） | 本仓库（安装器 / `PRODUCT_VERSION` `0.2.0`） |
| v0.3 想法 | 可选本地向量通道、召回评测集 | 未交付 |
| v0.4 想法 | Marketplace 打包、导入导出 | 未交付 |
| v0.5 想法 | 可选加密备份 | 未交付 |

### 隐私

框架本身不含个人数据。引擎和钩子不发起网络连接。`memory/`、`wiki/`、`private/` 和 `*.db` 被 git 忽略。写入时的密钥脱敏是按常见形态做的替换，不是完整的秘密扫描。说明见 [`docs/memory-engine.md`](docs/memory-engine.md)。产品笔记见 [`docs/product-analysis.md`](docs/product-analysis.md)。

### 协议

MIT
