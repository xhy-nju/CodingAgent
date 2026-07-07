# PLAN.md

> 状态：阶段计划骨架。本文档还不是实现计划。正式实现计划必须在用户审阅 `SPEC.md` 后，通过 Superpowers `writing-plans` 生成，并拆到 2-5 分钟粒度。

## 阶段 0：项目初始化

- [x] 确认仓库/工作区名称：`CodingAgent`。
- [x] 确认技术栈：Python + Typer + FastAPI + React/Vite/TypeScript + pytest + SQLite/JSON。
- [x] 确认机制范围：治理护栏 + 反馈闭环 + 记忆 + 工具分发。
- [x] 确认第一主贡献：治理护栏 + HITL 审批 + 沙箱边界。
- [x] 确认分发方式：Docker / Docker Compose。
- [x] 初始化 Git 仓库。
- [x] 创建文档骨架和 Git 忽略规则。
- [x] 将文档改为中文叙述。
- [x] 在 `README.md` 中加入 GitHub 仓库关联说明。
- [x] 安装并确认 Superpowers 插件。

## 阶段 0：GitHub 仓库设置

- [x] 在 GitHub 创建名为 `CodingAgent` 的仓库。
- [x] 将本地分支命名为 `main`。
- [x] 将 GitHub 仓库添加为 `origin` remote。
- [x] 将本地规划文档首次推送到 GitHub。
- [x] 在 `AGENT_LOG.md` 中记录 remote URL 和关键 commit。

## 阶段 1：Brainstorming 与 SPEC

- [x] 使用 `superpowers:using-superpowers` 确认技能调用规则。
- [x] 使用 `superpowers:brainstorming` 完成项目设计澄清。
- [x] 完成至少三轮关键 brainstorming 迭代；实际记录八轮关键迭代。
- [x] 确认 mock LLM 为测试和演示默认路径，real LLM 为可选路径。
- [x] 确认 WebUI 为完整可用前端，并支持一键演示。
- [x] 确认 Docker Compose 可用于阿里云 Ubuntu 部署。
- [x] 写入 Superpowers 设计稿：`docs/superpowers/specs/2026-07-07-coding-agent-harness-design.md`。
- [x] 补全 `SPEC.md`。
- [x] 补全 `SPEC_PROCESS.md`。
- [x] 更新 `AGENT_LOG.md`。
- [ ] 用户审阅并确认 `SPEC.md` 与 Superpowers 设计稿。

## 阶段 2：Writing Plans 与正式实现计划

阶段 2 必须等用户确认阶段 1 文档后启动。

- [ ] 调用 Superpowers `writing-plans`。
- [ ] 将实现拆分为 2-5 分钟粒度的 task。
- [ ] 每个 task 写清目标、涉及文件、实现要点、预期失败测试和验证步骤。
- [ ] 标注 task 之间的依赖关系。
- [ ] 标注可并行 worktree 或 subagent 的任务。
- [ ] 明确每个 task 的 TDD 红-绿-重构路径。
- [ ] 写入完整 `PLAN.md`。
- [ ] 用户审阅并确认 `PLAN.md`。

## 阶段 3：冷启动验证

- [ ] 选择一个与主开发智能体不同类型的 agent。
- [ ] 开启全新 session，不导入历史上下文或 memory。
- [ ] 只提供 `SPEC.md` 和 `PLAN.md`。
- [ ] 要求它选择 1-2 个 task 尝试实现，并在遇到不确定之处时暂停提问。
- [ ] 在 `SPEC_PROCESS.md` 中记录它的误解、卡点和暴露出的 spec/plan 缺陷。
- [ ] 根据冷启动反馈修订 `SPEC.md` 和 `PLAN.md`。
- [ ] 用户确认冷启动修订完成。

## 阶段 4：正式实现

阶段 4 暂不展开实现级任务。进入本阶段前必须满足：

- [ ] `SPEC.md` 已由用户确认。
- [ ] `PLAN.md` 已由 writing-plans 生成并由用户确认。
- [ ] 冷启动验证已完成并记录。
- [ ] 已按冷启动反馈修订文档。

正式进入实现后，所有 task 必须遵循 TDD：先写失败测试并确认红灯，再写最小实现并确认绿灯，最后重构并保留验证证据。

## 阶段 5：代码审查、分发与收尾

- [ ] 使用 Superpowers code review 流程请求审查。
- [ ] 修复审查发现的问题。
- [ ] 完成 Docker / Docker Compose 验证。
- [ ] 完成 `.gitlab-ci.yml` 与 GitHub Actions 验证。
- [ ] 完成 README、AGENT_LOG、REFLECTION 和部署说明。
- [ ] 使用 Superpowers finishing branch 流程完成最终提交与交付。
