# PLAN.md

> 状态：计划草稿骨架。本文档必须通过课程要求的 writing-plans 流程继续细化。正式实现任务必须拆到 2-5 分钟粒度，并写清文件路径、失败测试和验证步骤。

## 阶段 0：项目初始化

- [x] 确认仓库/工作区名称：`CodingAgent`。
- [x] 确认技术栈：Python + Typer + FastAPI + pytest + JSON/SQLite。
- [x] 确认机制范围：治理护栏 + 反馈闭环 + 记忆 + 工具分发。
- [x] 确认分发方式：Docker。
- [x] 初始化 Git 仓库。
- [x] 创建文档骨架和 Git 忽略规则。
- [x] 将文档改为中文叙述。
- [x] 在 `README.md` 中加入 GitHub 仓库关联说明。
- [x] 检查当前 Codex 环境是否暴露 Superpowers 技能。
- [ ] 在正式 brainstorming 前启用/安装 Superpowers，或在另一个支持 Superpowers 的智能体中完成官方流程并记录证据。

## 阶段 0：GitHub 仓库设置

- [ ] 在 GitHub 创建名为 `CodingAgent` 的空仓库。
- [ ] 如果课程允许，仓库设为 Public；如果必须私有，则添加助教或老师为协作者。
- [ ] 创建远程仓库时不要初始化 README、license 或 `.gitignore`，因为本地已经有项目文件。
- [ ] 将本地分支重命名为 `main`。
- [ ] 将 GitHub 仓库添加为 `origin` remote。
- [ ] 将本地规划文档首次推送到 GitHub。
- [ ] 在 `AGENT_LOG.md` 中记录 remote URL 和首次 push 的 commit hash。

## 阶段 1：Brainstorming 与 SPEC

- [ ] 运行课程要求的 Superpowers `brainstorming` 流程。
- [ ] 补全 `SPEC.md`。
- [ ] 在 `SPEC_PROCESS.md` 中记录至少三轮关键 brainstorming 迭代。
- [ ] 记录 AI 提出的建议、被采纳的建议、被推翻或修正的建议及原因。
- [ ] 更新 `AGENT_LOG.md`。

## 阶段 2：Writing Plans 与 PLAN

- [ ] 运行课程要求的 Superpowers `writing-plans` 流程。
- [ ] 将实现拆分为 2-5 分钟粒度的 task。
- [ ] 每个 task 写清目标、涉及文件、实现要点、预期失败测试和验证步骤。
- [ ] 标注 task 之间的依赖关系。
- [ ] 标注可并行 worktree 的任务。
- [ ] 明确每个 task 的 TDD 红-绿-重构路径。

## 阶段 3：冷启动验证

- [ ] 选择一个与主开发智能体不同类型的 agent。
- [ ] 开启全新 session，不导入历史上下文或 memory。
- [ ] 只提供 `SPEC.md` 和 `PLAN.md`。
- [ ] 要求它选择 1-2 个 task 尝试实现，并在遇到不确定之处时暂停提问。
- [ ] 在 `SPEC_PROCESS.md` 中记录它的误解、卡点和暴露出的 spec 缺陷。
- [ ] 根据冷启动反馈修订 `SPEC.md` 和 `PLAN.md`。

## 阶段 4：正式实现

本阶段暂不展开具体实现任务。按照课程要求，在阶段 1-3 完成之前，不允许编写 harness 实现代码。

正式进入实现后，所有 task 必须遵循：先写失败测试，确认红灯；再写最小实现，确认绿灯；最后重构并保留测试通过证据。

## 阶段 0：Superpowers 工具链阻塞记录

- [x] 已检查当前 Codex 环境是否有 Superpowers 技能。
- [x] 已搜索 `superpowers`、`brainstorming`、`writing-plans`、`test-driven-development` 和 `subagent-driven-development`。
- [x] 已确认当前 Codex session 没有暴露匹配的 Superpowers 技能或可安装插件。
- [ ] 必须在实现前启用/安装 Superpowers，或在另一个支持 Superpowers 的智能体中完成官方流程并记录证据。

## 阶段 0：Superpowers 官方安装待办

- [x] 已查阅 Superpowers 官方仓库，确认 Codex App/CLI 的官方安装入口。
- [ ] 人类所有者在 Codex App 插件侧边栏或 Codex CLI `/plugins` 中安装 `Superpowers`。
- [ ] 安装后开启新会话，确认 `brainstorming`、`writing-plans` 和 `test-driven-development` 等技能可用。
- [ ] 将安装证据和首次触发 Superpowers 的记录写入 `SPEC_PROCESS.md` 与 `AGENT_LOG.md`。
