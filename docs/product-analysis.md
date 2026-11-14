# 产品笔记：CC Agent Brain 当前代码能做什么

本文只描述这个仓库里已经落地的行为。竞品表格是早期笔记里的背景，本次没有重新核对 star 数或对方产品版本。下面凡是写「已实现」的句子，都以仓库里的钩子、`brain_store.py` 和 `installer/` 为准。

## 当前代码事实

1. **自动捕获只覆盖 Claude Code。** 钩子事件是 `SessionStart`、`UserPromptSubmit`、`PreCompact`、`Stop`，写进 `.claude/settings.json`。`transcript_capture.py` 读 Claude Code 的 transcript JSONL，索引助手正文和 `tool_use` 入参，跳过 `tool_result`。Cursor、Codex、Gemini CLI、Claude Desktop 在本仓库里没有捕获实现，也没有自动召回。
2. **检索是多路词法 FTS，再用 RRF 融合。** `bm25()` 给活跃记忆和事件打分，`rrf_fuse` 把这些列表合在一起；全局库文件若已存在，它的记忆和事件列表也进入同一次融合。没有向量通道，不是词法加向量的混合检索。
3. **有时间列，没有 as-of 查询。** `valid_from`、`valid_to`、`created_at`、`updated_at` 会写在行上。取代和失效会保留旧行。`search` 只看 `status='active'`。`timeline` 按 `updated_at` 列最近的行。不能按某个过去时点回放当时的库。
4. **MCP 是同一个 stdio 进程上的两个时代。** 没有现代信封时，`initialize` 仍返回 `2024-11-05`，并继续提供 `ping`、`tools/list`、`tools/call`。`params._meta` 同时带上 `io.modelcontextprotocol/protocolVersion`（字符串）和 `io.modelcontextprotocol/clientCapabilities`（对象），且版本为 `2026-07-28` 时，处理 `server/discover`、`tools/list`、`tools/call`，结果带 `resultType: "complete"` 和 `_meta` 里的 `serverInfo`（版本 `0.2.0`）。其他版本字符串返回 `-32022`。接上一个客户端仍然不等于自动捕获。
5. **再次安装会升级框架文件。** `update.py` 再次调用 `install.py`。命名空间里的钩子、skill、agent 会被覆盖。`brain.db`、`memory/`、`wiki/`、`private/` 和已有模板保留。已有库仍会执行 `init`（`engine_state` 为 `migrated`），文件本身不替换。同一次运行把 `cc-agent-brain` 这一条 stdio 配置合并进 Claude Code、Cursor、Codex 的项目配置。
6. **没有多 Agent 共享记忆服务。** 钩子只写当前工作目录的项目库。多个本地 MCP 进程可以用 `--global` 打开同一份全局 SQLite（默认 `~/.cc-agent-brain/brain.db`，旁边是 `library.md`），写入时记下调用方给出的 `writer`。这不是共享守护进程，也没有跨机器同步。安装器默认的三条 MCP 配置仍指向项目库。长期记忆不会自动蒸馏，要显式 `memory add`。

未交付、本仓库没有的能力：其他客户端的自动捕获、向量或混合检索、as-of 查询、共享守护进程、跨机器同步。可以记在以后的工作里，不能写成现在的功能。`2026-07-28` 的 `server/discover` 和 `_meta` 已经在 `serve-mcp` 里。框架文件升级和三份 MCP 配置合并也已经在安装器里。可选的本机全局库和 writer 已经在引擎里。MCP 配置默认不是把三个客户端接到那份全局库上。

## 1. 定位（按代码，不按口号）

给 Claude Code 项目用的本地附加组件：用标准库 SQLite + FTS5 记下钩子看见的文本，用 CLI 保存你明确写入的长期记忆，并用一个很小的 stdio MCP 进程暴露同一份库。

- 安装形态：命名空间合并进已有 `.claude/`，不整目录替换。
- 自动闭环停在 Claude Code 钩子。MCP 是另一条手动启动的 stdio 通道。
- 向量混合检索和双时态 as-of 查询仍然不是本仓库的现状。MCP `server/discover` 已经在 stdio 服务里，见 `docs/mcp.md`。

## 2. 谁会碰到它

| 情况 | 本仓库实际提供的 |
|------|------------------|
| 主要在 Claude Code 里干活，希望换会话后还能关键词召回刚才索引过的内容 | 钩子捕获 + `wiki_context_hint.py` 打印 FTS 命中 |
| 不想把原文交给托管记忆 API | 库文件在本机，进程不联网 |
| 同时开着 Cursor、Codex、Gemini CLI，希望一套自动记忆喂给所有工具 | 本仓库做不到自动捕获。stdio 服务能说 `2024-11-05` 和 `2026-07-28`，但仓库不带这些客户端的配置，连上也不等于自动记 |

## 3. 代码对应的痛点，以及对应不到的

1. Claude Code 跨会话：用户提示、助手正文、工具调用入参会进事件表，下一轮 Claude Code 提示可以打出关键词命中。
2. 旧结论还在不在：supersede/expire 留行，审计能看到重复 active 标题和断开的 supersede。不能回答「上周三当时有效的集合是什么」。
3. 关键词还能不能找到：FTS5 + 中文 bigram。语义近义、向量近邻不在检索里。
4. 换工具还记不记得：记不住。捕获绑在 Claude Code 钩子上。
5. 密钥明文：写入时按一批常见形态替换。这是尽力匹配，不是完整扫描。

## 4. 和外部方案的关系（背景，未复核）

下表保留早期对照笔记，避免把别人的能力写成我们的能力。

| 方案 | 笔记里的特征 | 和本仓库的差别 |
|------|----------------|----------------|
| claude-mem 一类 Claude Code 插件 | 自动捕获、语义检索、插件安装 | 本仓库也只有 Claude Code 自动捕获，但是词法 FTS，且没有对方的压缩模型 |
| 各类 Memory skill | 文件记忆、多工具分发 | 本仓库的 skill 是 Claude Code 提示词，不是已上架的多工具包 |
| Mem0 一类 | 向量 + 图 + BM25、官方 MCP、可托管 | 本仓库没有混合检索，也没有托管 |
| Zep / Graphiti 一类 | 双时间图谱、按失效时间推理 | 本仓库有 `valid_from` / `valid_to` 列和失效操作，没有 as-of 查询 |
| 纯 Markdown | 人读文件 | 本仓库额外有 SQLite FTS；长期记忆仍要显式写入 |

空位可以继续存在。v0.2 这份代码没有填上「Mem0 级自动捕获 + 混合检索 + 时序查询 + 跨工具记忆」。

## 5. 现在真正站得住的差异

1. **依赖面小**：引擎是 Python 标准库 `sqlite3` 和 FTS5，外加自写的中文 bigram。没有 pip 依赖，没有向量库。
2. **Markdown 还在**：`wiki/sessions` 有提示副本，`sync-md` 会导出当前 active 记忆。机器检索走 SQLite。
3. **旧行留得下来**：supersede/expire 改状态并写 `valid_to`，`timeline` 能列出最近变更。这是留档，不是历史时点查询。
4. **有一个很小的 MCP 进程**：同一进程说 `2024-11-05`（`initialize`）和 `2026-07-28`（`server/discover` 与 `_meta`），五个 tools。它不是跨工具自动记忆。
5. **安装不整夹替换 `.claude/`**：会备份 settings、按清单卸载框架文件。再次安装会覆盖命名空间里的钩子、skill 和 agent，并保留用户数据。

## 6. 功能对照（本仓库）

| 功能 | 状态 |
|------|------|
| Claude Code：用户提示、助手正文、`tool_use` 入参进入事件表 | 已实现。`tool_result` 跳过 |
| 其他客户端自动捕获 | 未实现 |
| FTS5/BM25，中文 bigram，多路词法 RRF | 已实现。不是向量混合 |
| 向量检索 | 未实现 |
| supersede/expire，行上保留，并带 `valid_from` / `valid_to` | 已实现 |
| as-of / 按过去时点查询 | 未实现 |
| 写入时按常见密钥形态替换 | 已实现（尽力而为） |
| SQL 审计（重复 active、断链、90 天未更新、低置信、有事件无记忆） | 已实现 |
| MCP stdio，`initialize` 返回 `2024-11-05`，并处理 `ping` / `tools/list` / `tools/call` | 已实现 |
| MCP `2026-07-28`：`server/discover`、结果上的 `resultType` 与 `_meta` | 已实现。不是其他客户端的自动捕获 |
| 钩子自动写全局库、共享守护进程、跨机器同步 | 未实现。钩子仍只写项目库 |
| 多个 MCP 客户端打开同一份本机全局库，并在写入时记下调用方给出的 writer | 已实现。`--global` 或 `CC_AGENT_BRAIN_GLOBAL_DIR`，外加 `library.md`。安装器默认不把三条 MCP 配置改指过去。`search` 仍在该文件已存在且不是当前文件时融合它的词法列表 |
| 自动把事件蒸馏成长期记忆 | 未实现。要 `memory add` |
| 升级时覆盖命名空间钩子、skill、agent，并保留 brain.db / memory / wiki / private | 已实现 |
| 合并 Claude Code、Cursor、Codex 的项目 MCP 配置，指向同一个 `serve-mcp` | 已实现。不是多 Agent 共享记忆，也不是这些客户端的自动捕获 |

## 7. 以后可以做、现在不能写进「已发布」

- 可选的本地向量通道，以及一套召回评测。做完之前，文档里的 RRF 仍然只是词法多路融合。
- 打包分发、导入导出。
- 可选的加密备份。
- 共享守护进程、按 Agent 分命名空间、跨机器同步。

## 8. 还说得清的使用信号

钩子失败时会静默退出，所以「装上了」不等于「每一轮都写入了」。能直接观察的是：`stats` 里的事件数、`search` 是否打出命中、`audit` 的 issue 列表、清单里的 `engine_state`。跨工具接入数、Marketplace 安装量，本仓库没有埋点，也没有对应的分发物。

## 9. 风险（按现在的实现）

| 风险 | 说明 |
|------|------|
| 文档把 Claude Code 钩子说成所有编码工具的自动记忆 | 会直接误导安装预期。README 必须以钩子范围为准 |
| 把 RRF 说成混合检索 | 用户会以为有向量。当前融合的是若干 FTS 列表 |
| 把 `valid_to` 说成能查询上周的信念 | `timeline` 只是最近变更列表 |
| Claude Code 钩子协议变化 | 引擎 CLI 仍可手工调用；钩子本身绑在当前这组事件名上 |
| 中文 bigram 的精度 | 这是当前唯一的中文检索手段 |
| 用户以为记忆会自己长出来 | 长期记忆依赖 `memory add` |
| 数据库文件里仍有对话原文 | 脱敏是模式替换；`*.db` 被 gitignore |

## 10. 代码还没替产品做的选择

1. 全局库默认不创建。钩子也不写它。
2. 向量依赖没有接进 `search`。核心路径仍然是标准库。
3. 没有 Marketplace 包，也没有随仓库发布的演示视频。
