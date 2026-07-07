# SPEC_PROCESS.md

> 本文档用于记录 `SPEC.md` 与 `PLAN.md` 的生成、迭代和冷启动验证过程。它是课程要求中的过程证据，不是最终宣传文档。

## 阶段 0 决策记录

- 日期：2026-07-07。
- 仓库/工作区名称：`CodingAgent`。
- 项目类型：A 类项目，Coding Agent Harness。
- 技术栈：Python + Typer CLI + FastAPI WebUI/API + pytest + JSON/SQLite 本地存储。
- 机制范围：治理护栏 + 反馈闭环 + 记忆 + 工具分发。
- 分发方式：Docker。
- GitHub 计划：创建名为 `CodingAgent` 的 GitHub 仓库，并将本地仓库关联为 `origin`。
- 范围说明：项目所有者希望四个机制维度都认真实现。为了评分清晰，后续 SPEC 应指定一个第一主贡献，同时保证四个维度都有可测试的代码机制。
- 实现边界：在 `SPEC.md`、`PLAN.md` 和冷启动验证完成前，不编写任何 harness 实现代码。

## 阶段 0：Superpowers 可用性检查

- 日期：2026-07-07。
- 检查内容：在当前 Codex 技能/插件环境中搜索 `superpowers`、`brainstorming`、`writing-plans`、`test-driven-development` 和 `subagent-driven-development`。
- 检查结果：当前 Codex session 没有暴露匹配的 Superpowers 技能，也没有可安装的 Superpowers 插件候选。
- 流程影响：这是阶段 0 的流程阻塞点。在 Superpowers 被启用前，或在另一个支持 Superpowers 的智能体中完成官方流程并记录证据前，本项目不能声称已经完成课程要求的 Superpowers brainstorming 或 writing-plans。

## 阶段 0：GitHub 准备

- 计划远程仓库名：`CodingAgent`。
- 计划默认分支：`main`。
- 计划 remote 名称：`origin`。
- 远程初始化规则：GitHub 上创建空仓库，不初始化 README、license 或 `.gitignore`，因为本地仓库已经包含规划文档。

## Brainstorming 关键迭代

TODO：记录至少三轮关键迭代。每轮应包含智能体提出的问题、人的回答、设计变化，以及为什么接受或拒绝某个建议。

## AI 建议中被采纳的部分

TODO：记录 AI 提出的、最终被采纳的建议，并说明采纳理由。

## AI 建议中被推翻或修正的部分

TODO：记录 AI 提出的但被人类所有者推翻或修改的建议，并说明原因。

## 冷启动验证

TODO：记录第二个不同类型 agent 在只读取 `SPEC.md` 和 `PLAN.md` 时暴露的问题、误解和产出偏差。

## 对规约过程的反思

TODO：反思 brainstorming 和 writing-plans 对项目清晰度的帮助，以及它们在哪些地方仍然不足。
