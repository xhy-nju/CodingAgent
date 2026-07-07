# CodingAgent Harness 设计规约

> 日期：2026-07-07
> 阶段：Superpowers brainstorming 已完成并获得人类所有者确认。
> 边界：本文档只定义设计，不包含实现代码。进入实现前仍需完成 `PLAN.md`、冷启动验证和 TDD 计划。

## 1. 项目定位

CodingAgent 是 AI4SE 期末项目 A 类方向的 Coding Agent Harness。它的目标不是把一个现成 agent 框架套壳后交付，而是自己实现一个可观察、可治理、可复现的 coding agent 运行外壳。LLM 在系统中只负责提出下一步动作；动作协议、工具分发、治理护栏、反馈解析、记忆检索、审批状态机和审计日志全部由确定性的代码承担。

项目采用“课程演示 + 治理研究原型”的组合定位。默认演示路径面向课程评分者和学生开发者，要求在没有真实 LLM、没有外部网络的情况下也能通过 mock LLM 复现关键机制。扩展路径面向真实开发实验，可以在管理员显式启用后接入 OpenAI-compatible API。

第一主贡献维度是“治理护栏 + HITL 审批 + 沙箱边界”。反馈闭环是第二重点，用来证明工具执行结果会改变 agent 的下一步行为。记忆和工具分发必须完整实现并有测试覆盖，但不把它们扩展成复杂 RAG 或通用插件市场。

## 2. 目标与非目标

### 2.1 目标

- 实现一个自编码 agent 主循环：构造上下文、调用 LLM provider、解析动作、执行工具、回灌结果、判断停止。
- 提供可替换 LLM 抽象：mock provider 是测试和一键演示默认路径；real provider 通过 OpenAI-compatible API 可选启用。
- 实现严格 JSON Action Protocol：LLM 输出必须经过 schema 校验，解析失败转为反馈信号。
- 实现工具分发：文件读写、文件列表、受限 shell、pytest/lint 运行、记忆读写等工具统一走 dispatcher。
- 实现确定性治理：路径边界、命令白名单/黑名单、凭据文件保护、危险动作拦截、输出脱敏、超时和审批状态机。
- 实现反馈闭环：测试失败、lint 失败、命令退出码、guardrail 阻断、schema 错误都会成为下一轮上下文中的结构化反馈。
- 实现事件记忆和摘要记忆：保存项目决策、偏好、失败模式、工具约束和运行摘要，并用确定性检索注入上下文。
- 实现完整 WebUI：支持一键演示、运行创建、实时事件流、审批队列、记忆查看、策略查看、凭据状态和设置。
- 提供 Docker / Docker Compose 分发，支持在阿里云 Ubuntu 主机部署。
- 同时提供 `.gitlab-ci.yml` 和 GitHub Actions，满足课程中对 GitLab unit-test job 以及 GitHub 仓库托管的双重要求。

### 2.2 非目标

- 不实现面向公网多租户的 SaaS 权限体系。
- 不把真实 LLM 行为作为课程验收的唯一依据。
- 不默认允许 agent 修改任意本地仓库或执行任意 shell 命令。
- 不在第一版实现向量数据库、复杂语义检索或自动云端发布。
- 不要求 WebUI 具备团队协作、评论、通知等产品化功能。

## 3. 关键技术决策

- 后端与核心：Python。原因是便于实现 CLI、FastAPI、工具执行、pytest 解析和 mock 测试。
- CLI：Typer。用于本地启动 run、运行 demo、导出日志和执行课程验收脚本。
- API/Web 后端：FastAPI。提供 REST API、Server-Sent Events 事件流和静态前端托管。
- 前端：React + Vite + TypeScript。WebUI 不是宣传页，而是密集、克制、面向操作的 dashboard。
- 设计参考：Open Design 仓库作为 UI 项目参考，主要吸收其设计文档化和 dashboard/artifact/prototype 思路。
- 存储：SQLite 为运行状态、审批、事件和记忆的默认存储；保留 JSON 导出，便于课程检查。
- LLM：mock provider 默认启用；real provider 使用 OpenAI-compatible API，默认 `OPENAI_BASE_URL=https://njusehub.info/v1`，模型配置预期为 `glm-5.2`。
- 凭据：本地开发优先使用 OS keyring；Docker、CI、服务器使用环境变量或挂载 `.env`。任何模式都不得提交、打印或写入真实 API key。
- 实时通信：WebUI 使用 SSE，而不是轮询或 WebSocket。SSE 足够表达 run 事件流，复杂度较低。
- 分发：Docker Compose 是主分发路径。公开部署默认只启用 mock LLM；真实 LLM 需要 `ENABLE_REAL_LLM=true` 和管理员登录。

## 4. 系统架构

系统由四层组成。

第一层是用户入口，包括 React WebUI 和 Typer CLI。WebUI 负责一键演示、运行状态、审批和配置查看；CLI 负责自动化脚本、课程验收和本地快速调试。

第二层是 FastAPI 服务层。它提供运行管理 API、SSE 事件流、审批 API、记忆 API、策略 API、凭据状态 API 和静态资源服务。服务层不直接执行危险动作，所有 agent 行为都进入 core。

第三层是 harness core。核心模块包括 `AgentLoop`、`LLMProvider`、`ActionParser`、`ToolDispatcher`、`GuardrailEngine`、`ApprovalService`、`FeedbackEngine`、`MemoryStore`、`PolicyLoader` 和 `AuditLogger`。这些模块通过结构化数据通信，避免把安全判断隐藏在 prompt 字符串里。

第四层是运行环境。它包括受限工作区、内置示例项目、SQLite 数据库、环境变量、OS keyring、Docker 容器和 CI runner。

## 5. 主流程

1. 用户在 WebUI 点击“一键演示”，或通过 CLI 创建 run。
2. API 创建 `Run` 记录，加载策略、工作区、LLM 模式和相关记忆。
3. `AgentLoop` 构造上下文，调用 `LLMProvider`。
4. provider 返回 JSON 动作；`ActionParser` 做 schema 校验。
5. `GuardrailEngine` 在工具执行前检查路径、命令、凭据、网络、超时和策略等级。
6. 安全动作由 `ToolDispatcher` 执行；危险动作进入审批状态机；被拒绝或被阻断的动作转为结构化反馈。
7. 工具结果由 `FeedbackEngine` 解析为 `FeedbackSignal`，例如测试失败、lint 错误、退出码、超时或 diff 摘要。
8. `MemoryStore` 根据策略写入事件记忆或摘要记忆，并检索与下一步相关的记录。
9. 下一轮上下文包含反馈和相关记忆，mock LLM 或 real LLM 根据这些信息产生下一步动作。
10. 当 LLM 输出 `final` 动作、达到最大步数、发生不可恢复错误或用户取消时，run 结束并写入审计日志。

## 6. Action Protocol

LLM 输出必须是严格 JSON。自由文本、Markdown 代码块、字段缺失、未知工具或参数类型错误都视为协议错误。

最小动作结构如下：

```json
{
  "kind": "tool",
  "tool": "read_file",
  "args": { "path": "sample_app/calculator.py" },
  "reason": "查看失败测试涉及的实现",
  "expectation": "找到加法函数的当前逻辑"
}
```

动作类型包括：

- `tool`：请求执行一个受支持工具。
- `remember`：请求写入一条结构化记忆。
- `final`：声明任务完成或无法继续，并给出原因。
- `request_user`：在真实模式下请求用户澄清；mock 演示中尽量避免使用。

协议错误不会直接崩溃 run，而是生成 `schema_error` 反馈并进入下一轮。这样可以测试“LLM 输出不合规时，harness 如何恢复”。

## 7. 工具分发

工具必须通过统一 dispatcher 注册和调用。每个工具声明名称、输入 schema、输出 schema、权限需求、超时、是否允许在 strict demo 模式中运行，以及可能产生的反馈类型。

第一版工具清单：

- `list_files`：列出工作区内文件，默认忽略 `.git`、凭据文件、缓存和运行状态目录。
- `read_file`：读取工作区内文本文件，限制大小并做凭据路径检查。
- `write_file`：写入工作区内允许路径，返回 diff 摘要。
- `run_command`：执行受限命令，只允许策略白名单中的命令和参数模式。
- `run_tests`：封装 pytest，解析测试数量、失败用例、错误摘要和退出码。
- `run_lint`：封装 lint 命令，解析错误摘要。
- `memory_search`：按标签、关键词和任务类型检索记忆。
- `memory_write`：写入结构化记忆，经过 schema 校验和敏感信息过滤。

工具输出统一封装为 `ToolResult`，包含 `status`、`stdout_summary`、`stderr_summary`、`artifacts`、`duration_ms`、`feedback_candidates` 和 `redactions`。

## 8. 治理护栏与 HITL

治理模块是项目第一主贡献。它必须由代码实现，不接受“在 prompt 中提醒 agent 小心”作为安全机制。

策略分为两个 profile：

- `strict_demo`：默认模式，只允许内置示例工作区和少量安全命令。递归删除、工作区外路径、凭据文件访问、网络发布、数据库删除、包管理安装等动作被拒绝或进入审批。
- `balanced_dev`：本地开发可选模式，允许更多只读命令和测试命令，但仍然保护凭据、路径边界和高风险操作。

Guardrail 决策类型：

- `allow`：动作安全，直接执行。
- `deny`：动作违反硬规则，直接阻断。
- `needs_approval`：动作可由人类承担风险，进入审批队列。
- `rewrite`：在有限场景下把动作改写成更安全形式，例如把通用 shell 测试改为 `run_tests`。

HITL 状态机包括 `pending`、`approved_once`、`rejected`、`revision_requested`、`expired` 和 `cancelled`。审批记录必须保存原始动作、命中的规则、审批人、理由、时间和后续执行结果。WebUI 审批队列是用户参与治理的主要界面。

## 9. 反馈闭环

反馈闭环负责把客观结果转成下一轮可用的结构化信号。第一版反馈类型包括：

- `test_passed` / `test_failed`
- `lint_passed` / `lint_failed`
- `command_failed`
- `guardrail_blocked`
- `approval_rejected`
- `schema_error`
- `timeout`
- `file_diff`

课程机制演示必须包含三条确定性路径：

1. mock LLM 提出危险动作，guardrail 以代码规则阻断，并在 WebUI/日志中可见。
2. mock LLM 第一次修复代码后测试失败，反馈被注入下一轮，mock LLM 根据失败摘要改变下一步动作。
3. 工具分发只能访问声明工作区，越界访问被拒绝并生成反馈。

## 10. 记忆设计

记忆分两类。

事件记忆记录事实：run、step、工具调用、guardrail 决策、审批、反馈和用户选择。摘要记忆记录可复用经验：项目约定、用户偏好、失败原因、有效修复、工具限制和策略解释。

检索采用确定性规则：标签、关键词、任务类型、最近更新时间和优先级加权。不引入向量数据库，避免测试不可复现。每条记忆包含 `id`、`scope`、`kind`、`tags`、`content`、`source_run_id`、`created_at`、`updated_at`、`confidence` 和 `sensitive`。标记为敏感的记录不会进入 prompt，也不会导出到公开日志。

## 11. WebUI 体验

WebUI 是完整可用的操作界面，不是最小状态面板。第一屏直接进入工作台，而不是营销式 landing page。

页面清单：

- Dashboard：运行概览、最近反馈、待审批数量、策略状态和演示入口。
- New Run：选择内置示例或自定义工作区，选择 mock/real LLM，选择策略 profile。
- Run Detail：SSE 实时事件流、当前 step、工具调用、反馈、diff 摘要和最终结果。
- Demo Center：一键运行课程三类机制演示。
- Approval Queue：查看、批准、拒绝或要求修改危险动作。
- Memory：浏览和筛选记忆记录。
- Policies：查看策略 profile、命中规则和工具权限。
- Credentials：录入/清除本机凭据，服务器模式只显示配置状态。
- Settings：管理员密码、真实 LLM 开关、模型名、base URL 和导出选项。

视觉风格应贴近开发运维 dashboard：信息密度较高、层级清晰、色彩克制、适合扫描和反复操作。

## 12. 部署与凭据

本地开发时，用户可通过 CLI 或 WebUI 把 API key 写入 OS keyring。Docker、CI 和阿里云 Ubuntu 部署时，通过环境变量或挂载 `.env` 注入。`.env` 是明文文件，只能放在服务器本地并通过 `.gitignore` 排除。

公开部署默认设置：

- `LLM_MODE=mock`
- `ENABLE_REAL_LLM=false`
- `ADMIN_PASSWORD` 必填
- `OPENAI_BASE_URL=https://njusehub.info/v1`
- `OPENAI_MODEL=glm-5.2`

真实 LLM 只有在管理员登录且 `ENABLE_REAL_LLM=true` 时才可选。UI 只显示“已配置/未配置”，不显示 key 明文。

阿里云 Ubuntu 主机部署采用 Docker Compose。后续 README 需要包含镜像构建、容器启动、端口暴露、防火墙、安全组、日志查看和更新流程。

## 13. 测试与 CI

测试策略以 mock LLM 为中心。

- 单元测试：action parser、guardrail rules、tool dispatcher、feedback parser、memory retrieval、approval state machine。
- 集成测试：mock LLM 驱动内置示例项目完成一次 bugfix run。
- 机制演示测试：危险动作阻断、反馈改变动作、越界工具调用被拒绝。
- API 测试：创建 run、读取事件、审批动作、查询记忆和策略。
- 前端测试：关键页面渲染、Demo Center 一键触发、审批操作。
- Docker 验证：镜像可构建，Compose 可启动服务。

CI 同时提供：

- `.gitlab-ci.yml`：必须包含 `unit-test` job，运行 Python 单元测试。
- GitHub Actions：运行后端测试、前端构建和 Docker 构建。

## 14. 验收标准

- 无真实 LLM 和无网络条件下，mock LLM 可以驱动完整 run。
- 危险动作由 guardrail 代码阻断，日志可追溯具体规则。
- 测试失败反馈会改变 mock LLM 下一步动作。
- 记忆可以跨 run 保存、检索和注入。
- 工具调用不能越过声明工作区边界。
- WebUI 可以一键运行机制演示，并实时展示事件。
- Docker Compose 可以在 Ubuntu 主机启动可访问 WebUI。
- 课程文档包含 `SPEC.md`、`PLAN.md`、`SPEC_PROCESS.md`、`AGENT_LOG.md`、`REFLECTION.md`、CI 配置、测试记录和部署说明。

## 15. 主要风险与控制

- 范围过大：把治理作为第一主贡献，反馈为第二重点，记忆和工具分发保持可测试但克制。
- 真实 LLM 不稳定：验收和 CI 默认使用 mock LLM；real provider 只作为扩展演示。
- Windows 与 Linux 命令差异：工具层封装 pytest/lint，避免测试依赖复杂 shell。
- 凭据泄露：不提交 `.env`，日志脱敏，UI 不回显 key，公开部署默认 mock。
- WebUI 占用时间：优先实现课程演示闭环页面，再补齐配置和浏览页面。
- 课程平台要求冲突：同时保留 GitHub Actions 和 `.gitlab-ci.yml`。

## 16. 下一步门禁

本文档写入并自检后，需要人类所有者审核。审核通过后，才能调用 Superpowers `writing-plans`，把设计拆成 2-5 分钟粒度的实现任务。即使设计已经确认，在 `PLAN.md` 和冷启动验证完成前仍不开始写实现代码。
