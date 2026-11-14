# CC Agent Brain 发布前检查清单

## 1. 项目定位检查

- [ ] README 第一屏说明：这是编码 Agent 的本地记忆引擎（本地优先、零依赖、MCP 跨工具）。
- [ ] README 明确说明：不会替换已有 `.claude/`，只做增量合并。
- [ ] README 明确说明：全程本地运行，无云同步、无遥测、无网络请求。
- [ ] README 明确说明：GitHub 只开源框架，不开源用户个人 Wiki / memory / 数据库。

## 2. 目录结构检查

- [ ] `installer/` 存在（install/uninstall/update/merge_settings）。
- [ ] `package/claude/skills/` 下 6 个技能齐全。
- [ ] `package/claude/agents/` 下 3 个代理齐全。
- [ ] `package/claude/hooks/cc-agent-brain/` 下 6 个钩子 + `brain_store.py` + `_utils.py`。
- [ ] `package/memory_templates/`、`package/wiki_templates/`、`package/templates/` 齐全。
- [ ] `prompts/`、`docs/`、`examples/` 存在。

## 3. 安装器检查

- [ ] 不替换用户已有 `.claude/` 目录；升级覆盖 `hooks/cc-agent-brain/**`、`skills/cc-agent-brain-*/**`、`agents/cc-agent-brain-*.md`。不覆盖 memory/、wiki/、private/、已有模板与 brain.db。安装前备份 settings。
- [ ] settings 只增量合并且重复安装不产生重复 hook。
- [ ] 生成 `.cc-agent-brain/install-manifest.json`，版本号与 CHANGELOG 一致。
- [ ] 安装和升级都执行 `brain_store.py --db <path> init`。新库的 `engine_state` 为 `initialized`，已有库为 `migrated`。
- [ ] 合并 Claude Code `.mcp.json`、Cursor `.cursor/mcp.json`、Codex `.codex/config.toml`，只更新 `cc-agent-brain` 这一条。
- [ ] 支持 `--dry-run`，预览不写盘。
- [ ] 卸载只删框架文件，保留 memory/ wiki/ private/ 与 brain.db。

## 4. 引擎与 Hook 检查

- [ ] `python -m py_compile` 全部脚本通过。
- [ ] `brain_store.py init/stats/event/memory/search/audit/timeline/sync-md` 可用。
- [ ] 中文与英文检索都能命中（CJK bigram 分词）。
- [ ] supersede/expire 后旧记忆不再被 active 检索命中，timeline 保留历史。
- [ ] `serve-mcp` 能完成 initialize / tools/list / tools/call 握手。
- [ ] 捕获层对常见密钥形态脱敏（构造样例验证）。
- [ ] `prompt_capture.py` 双写 Markdown 与事件流。
- [ ] `transcript_capture.py` 能解析助手回复/工具调用且二次运行幂等。
- [ ] `wiki_context_hint.py` 走真实检索而非关键词表。
- [ ] `memory_audit.py` 能报重复、断链、过期、积压。
- [ ] 引擎不可用时各 hook 静默降级，不阻塞用户。

## 5. Skill / Agent 检查

- [ ] 6 个 skill 均指向引擎 CLI，工作流与版本化记忆 schema 一致。
- [ ] 3 个 agent 的职责与工具声明正确。

## 6. 隐私检查

- [ ] `.gitignore` 忽略 memory/ wiki/ private/ .cc-agent-brain/ 与 *.db*。
- [ ] README 提醒不要上传真实个人数据。
- [ ] 引擎在写入时脱敏，文档说明其为尽力而为、不能替代"不存密钥"。

## 7. GitHub 发布检查

- [ ] 仓库 Description 与 README 定位一致，topics 覆盖 memory / mcp / claude-code / agent。
- [ ] MIT License 在位。
- [ ] 上传前跑全部自测脚本与一次 `--dry-run`、一次真实安装。
- [ ] 上传后检查 README 双语渲染、文档相对链接可达。

## 8. 后续版本规划

- [ ] v0.3：可选本地向量（sqlite-vec）+ RRF，内置召回评测集。
- [ ] v0.4：Marketplace 打包、一行安装、导入导出。
- [ ] v0.5：可选端到端加密私有备份。
