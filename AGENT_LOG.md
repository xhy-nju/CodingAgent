# AGENT_LOG.md

本文档按时间顺序记录与 AI 协作开发的关键节点。每条记录尽量包含时间、任务编号、触发的技能、关键 prompt/context、subagent 输出、commit hash、人工干预和经验教训。

## 2026-07-07 - 阶段 0 - 项目初始化

- 任务：从 0 开始初始化项目。
- 工具：Codex，本地工作区为 `D:\Projects\CodingAgent`。
- 人类所有者确认的决策：
  - 仓库/工作区名称：`CodingAgent`。
  - 技术栈：Python + Typer + FastAPI + pytest + JSON/SQLite。
  - 机制范围：治理护栏 + 反馈闭环 + 记忆 + 工具分发。
  - 分发方式：Docker。
- 人工干预：人类所有者选择了技术栈、机制范围和分发方式。
- 输出：初始化 Git 仓库，创建文档骨架和 `.gitignore`，在 `README.md` 中加入 GitHub 仓库设置说明，将主要文档改为中文叙述。
- 边界：未编写任何 harness 实现代码。

## 2026-07-07 - 阶段 0 - Superpowers 可用性检查

- 任务：确认当前 Codex 环境是否可以直接运行课程要求的 Superpowers 工作流。
- 搜索关键词：`superpowers`、`brainstorming`、`writing-plans`、`test-driven-development`、`subagent-driven-development`。
- 结果：初始 session 没有暴露匹配的 Superpowers 技能或可安装插件。
- 需要人类决策：启用/安装 Superpowers，或在另一个支持 Superpowers 的智能体中完成官方流程并保存证据。
- 边界：未编写任何 harness 实现代码。

## 2026-07-07 - 阶段 0 - GitHub 准备指导

- 任务：记录如何创建并关联 GitHub 仓库。
- 仓库名决策：`CodingAgent`，与本地工作区保持一致。
- 推荐 remote 设置：在 GitHub 创建空仓库，不初始化 README、license 或 `.gitignore`；将本地分支重命名为 `main`；添加 `origin` remote；推送本地规划文档。
- 边界：未编写任何 harness 实现代码。

## 2026-07-07 - 阶段 0 - GitHub 远程仓库关联

- 任务：将本地仓库与 GitHub 仓库关联。
- 本地分支：`main`。
- 远程仓库：`https://github.com/xhy-nju/CodingAgent.git`。
- remote 名称：`origin`。
- 阶段 0 中文文档提交：`8a8cb98`。
- 后续 Superpowers 设置提交：`8aa2a47`。
- 边界：未编写任何 harness 实现代码。

## 2026-07-07 - 阶段 0 - Superpowers 官方安装路径确认

- 任务：查阅 Superpowers 官方仓库，确认 Codex 环境的安装方式。
- 来源：`https://github.com/obra/superpowers`。
- 官方信息摘要：Codex App 在侧边栏 Plugins 中找到 `Superpowers` 并安装；Codex CLI 输入 `/plugins`，搜索 `superpowers`，选择 `Install Plugin`。
- 当前限制：本会话的插件发现工具当时没有暴露 `Superpowers`，因此无法由当前 agent 直接安装。
- 后续动作：人类所有者在 Codex App/CLI 中安装插件。
- 边界：未编写任何 harness 实现代码。

## 2026-07-07 - 阶段 0 - Superpowers 安装完成确认

- 任务：确认用户安装的 Superpowers 插件已经落地。
- 插件来源：`superpowers@openai-curated-remote`。
- 本地确认路径：`C:\Users\xhy\.codex\plugins\cache\openai-curated-remote\superpowers\6.1.1`。
- 已确认技能：`using-superpowers`、`brainstorming`、`writing-plans`、`test-driven-development`、`subagent-driven-development`。
- 结论：阶段 0 的 Superpowers 工具链阻塞解除，下一步进入阶段 1 的 Superpowers brainstorming。
- 边界：未编写任何 harness 实现代码。

## 2026-07-07 - 阶段 1 - Superpowers Brainstorming 与 SPEC

- 任务：完成阶段 1 设计澄清、正式设计稿和根目录规约。
- 使用技能：`superpowers:using-superpowers`、`superpowers:brainstorming`，收尾前读取 `superpowers:verification-before-completion` 以约束完成声明。
- 人类所有者关键选择：
  - 项目定位采用课程演示 + 治理研究原型。
  - 第一主贡献采用治理护栏 + HITL 审批 + 沙箱边界。
  - 已有真实 LLM API key，base URL 为 `https://njusehub.info/v1`，模型预期为 `glm-5.2`。
  - LLM 设计采用 mock 默认、real optional。
  - WebUI 要完整可用，并参考 Open Design 仓库。
  - 运行状态采用 SSE，演示入口要求 WebUI 一键演示。
  - 部署目标为阿里云 Ubuntu + Docker Compose。
  - CI 同时提供 `.gitlab-ci.yml` 和 GitHub Actions。
- 产出：
  - `docs/superpowers/specs/2026-07-07-coding-agent-harness-design.md`。
  - 完整中文 `SPEC.md`。
  - 更新 `SPEC_PROCESS.md`，记录八轮关键 brainstorming 迭代。
  - 更新 `PLAN.md`，保留阶段门禁但不提前写实现级任务。
  - 更新 `README.md`，同步当前状态和下一步。
- 人工干预：人类所有者逐节确认设计，并在多处技术/产品选择中给出 A/B 答案。
- 经验教训：mock LLM 是课程要求的可验证机制入口，不是对真实能力的放弃；WebUI 一键演示会显著提高展示质量，但后续 `PLAN.md` 必须严格控制任务颗粒度。
- 边界：未编写任何 harness 实现代码。下一步必须由人类所有者审阅 `SPEC.md` 和 Superpowers 设计稿，确认后才能进入 `writing-plans`。

## 2026-07-07 - 阶段 2 - Superpowers Writing Plans

- 任务：把已确认的 `SPEC.md` 拆成可执行实现计划。
- 使用技能：`superpowers:using-superpowers`、`superpowers:writing-plans`。
- 输入：阶段 1 的中文 `SPEC.md` 与 Superpowers 设计稿。
- 输出：
  - `docs/superpowers/plans/2026-07-07-coding-agent-harness-implementation.md`。
  - 同步后的根目录 `PLAN.md`。
- 计划内容：16 个任务，按 TDD 串起领域模型、Action Parser、SQLite store、guardrail、HITL、工具、反馈、记忆、mock LLM、agent loop、CLI、FastAPI/SSE、React WebUI、真实 LLM 凭据、Docker、CI 和交付证据。
- 人工决策：人类所有者确认进入下一阶段，因此开始 writing-plans；本阶段没有进入实现。
- 边界：未编写任何 harness 实现代码。正式实现前仍需要完成冷启动验证并按反馈修订文档。

## 2026-07-07 - 阶段 3 - 冷启动验证准备

- 任务：为正式实现前的 cold-start validation 准备操作指南与外部 agent 提示词。
- 使用技能：`superpowers:using-superpowers`，并按 `superpowers:verification-before-completion` 的要求保留验证证据边界。
- 输出：`docs/cold-start/2026-07-07-validation-guide.md`。
- 推荐验证任务：优先让外部 agent 尝试 `PLAN.md` 的 Task 4，检查它是否理解 deterministic guardrails、HITL 状态机和 TDD 流程。
- 人工动作：人类所有者需要在另一个不同类型 agent 中执行验证，并把结果发回当前会话。
- 边界：当前步骤没有执行实现，也没有声称冷启动验证已通过。