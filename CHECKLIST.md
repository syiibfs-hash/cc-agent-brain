# CC Agent Brain 发布前检查清单

## 1. 项目定位检查

- [ ] README 第一屏说明：这是 Claude Code 的本地第二大脑系统。
- [ ] README 明确说明：不会替换已有 `.claude/`，只做增量合并。
- [ ] README 明确说明：v0.1 不做云同步，不做 GitHub 私有备份。
- [ ] README 明确说明：GitHub 只开源框架，不开源用户个人 Wiki / memory。

## 2. 目录结构检查

- [ ] `installer/` 存在。
- [ ] `package/claude/skills/` 存在。
- [ ] `package/claude/agents/` 存在。
- [ ] `package/claude/hooks/cc-agent-brain/` 存在。
- [ ] `package/memory_templates/` 存在。
- [ ] `package/wiki_templates/` 存在。
- [ ] `package/templates/` 存在。
- [ ] `prompts/` 存在。
- [ ] `docs/` 存在。
- [ ] `examples/` 存在。

## 3. 安装器检查

- [ ] `installer/install.py` 不覆盖用户已有 `.claude/`。
- [ ] 安装器会创建 `.claude/skills/cc-agent-brain-*`。
- [ ] 安装器会创建 `.claude/agents/cc-agent-brain-*.md`。
- [ ] 安装器会创建 `.claude/hooks/cc-agent-brain/`。
- [ ] 安装器会备份 `.claude/settings.json`。
- [ ] 安装器只合并 settings，不整体覆盖 settings。
- [ ] 安装器会生成 `.cc-agent-brain/install-manifest.json`。
- [ ] 安装器支持 `--dry-run`。

## 4. Hook 检查

- [ ] `session_start.py` 能检测 onboarding 是否缺失。
- [ ] `prompt_capture.py` 能写入 `wiki/sessions/YYYY-MM-DD.md`。
- [ ] `wiki_context_hint.py` 能在用户提到历史、项目、上次、之前时提示检索 Wiki。
- [ ] `pre_compact_save.py` 能在上下文压缩前生成 checkpoint。
- [ ] `memory_audit.py` 能做轻量审计。

## 5. Skill 检查

- [ ] `cc-agent-brain-onboard-user` 写明分支式初始化问题。
- [ ] `cc-agent-brain-wiki-update` 写明 Wiki 更新规则。
- [ ] `cc-agent-brain-wiki-search` 写明检索顺序。
- [ ] `cc-agent-brain-memory-distill` 写明从 Wiki 精炼 memory 的规则。
- [ ] `cc-agent-brain-memory-audit` 写明冲突、过期、重复检查。
- [ ] `cc-agent-brain-material-distill` 写明素材沉淀规则。

## 6. 隐私检查

- [ ] `.gitignore` 不会忽略开源包里的模板文件。
- [ ] 用户个人 `memory/`、`wiki/`、`private/` 被说明为本地内容。
- [ ] README 提醒用户不要上传真实个人 Wiki。
- [ ] `private/` 不会被默认安装为可公开内容。

## 7. GitHub 发布检查

- [ ] 仓库名建议为 `cc-agent-brain`。
- [ ] Description 建议为：`A local Wiki-first second brain system for Claude Code`。
- [ ] 选择 MIT License。
- [ ] 上传前运行 `python -m py_compile` 检查脚本语法。
- [ ] 上传前运行一次 `python installer/install.py --target <测试项目> --dry-run`。
- [ ] 上传后检查 README 首页显示是否正常。

## 8. 后续版本规划

- [ ] v0.2：Memory governance。
- [ ] v0.3：Project intelligence。
- [ ] v0.4：Optional private backup。
