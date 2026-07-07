# SPEC.md

> 状态：阶段 1 规约文档，基于 Superpowers brainstorming 产出。
> 日期：2026-07-07。
> 实现边界：本文档完成后仍不能直接写实现代码，必须先完成 `PLAN.md` 的 writing-plans 流程和冷启动验证。

## 1. 问题陈述

CodingAgent 要解决的问题是：如何构建一个可治理、可测试、可复现的 coding agent harness，而不是把全部责任交给 LLM prompt。项目面向 AI4SE 课程评分者、学生开发者和希望研究 coding agent 工程机制的使用者。它要证明，一个可靠的 coding agent 不只是“会说代码”的模型，而是由主循环、动作协议、工具分发、反馈闭环、记忆、治理护栏、审批和审计共同组成的工程系统。

本项目属于 A 类 Coding Agent Harness。核心要求是自己实现 harness，不使用现成 agent 框架作为主体。LLM 只负责生成下一步结构化动作；是否允许执行、如何执行、如何解析结果、如何回灌反馈、如何保存记忆，都由确定性代码实现。

项目默认通过 mock LLM 完成课程验收和一键演示。真实 LLM 是可选扩展，使用 OpenAI-compatible API，默认 base URL 为 `https://njusehub.info/v1`，预期模型为 `glm-5.2`。真实 API key 永远不提交到仓库，不写入日志，不在 WebUI 回显。

## 2. 项目范围

### 2.1 第一主贡献

第一主贡献是治理护栏、HITL 审批和沙箱边界。项目必须能用代码规则阻断危险动作，并把阻断原因、规则命中、审批状态和后续反馈展示出来。安全判断不能只依赖 prompt。

### 2.2 支撑贡献

反馈闭环是第二重点。工具执行结果必须被解析成结构化反馈，并影响下一轮动作。记忆和工具分发必须完整实现，但控制复杂度，避免扩展成通用插件市场或复杂 RAG 系统。

### 2.3 非目标

- 不实现生产级多人协作 SaaS。
- 不默认允许 agent 修改任意本地仓库。
- 不依赖真实 LLM 完成单元测试或课程验收。
- 不实现向量数据库、复杂语义检索或自动云端发布。
- 不把 WebUI 做成宣传页，第一屏必须是可操作工作台。

## 3. 用户故事

- 作为课程评分者，我希望在没有真实 LLM key 的情况下运行一键演示，以验证项目核心机制不是依赖外部服务。
- 作为项目维护者，我希望危险命令在执行前被确定性规则拦截，以避免误删文件、越界访问或泄露凭据。
- 作为学生开发者，我希望看到每一步 LLM 动作、工具调用、反馈和记忆写入，以便解释 harness 为什么这么做。
- 作为 reviewer，我希望通过日志和 WebUI 审查 guardrail 的命中规则，以判断安全机制是否是代码实现。
- 作为使用者，我希望在 WebUI 中审批或拒绝危险动作，并把我的决定反馈给 agent。
- 作为演示者，我希望点击一个按钮即可运行“危险动作阻断、失败反馈修复、越界工具调用拒绝”三类机制演示。
- 作为真实模式使用者，我希望可以配置 OpenAI-compatible API，但 key 不被提交、打印或回显。
- 作为部署者，我希望用 Docker Compose 在 Ubuntu 主机启动完整 WebUI，并能用环境变量控制 mock/real LLM 模式。
- 作为 CI 维护者，我希望项目提供 mock LLM 测试，不因为网络或模型波动导致测试不稳定。

## 4. 功能规约

### 4.1 Agent 主循环

输入：用户任务、工作区、策略 profile、LLM 模式、最大步数、相关记忆。
行为：构造上下文，调用 LLM provider，解析 action，交给 guardrail 审查，执行工具或进入审批，把结果转为反馈并进入下一轮。
输出：run 状态、step 列表、工具结果、反馈、记忆更新、最终结果。
边界：达到最大步数、用户取消、不可恢复错误、LLM 输出 `final` 时停止。协议错误不能让进程崩溃，而应转为反馈。

### 4.2 LLM 抽象层

输入：结构化上下文、系统规则、任务状态、反馈和相关记忆。
行为：mock provider 根据预设脚本和反馈生成确定性动作；real provider 调用 OpenAI-compatible API。
输出：原始模型输出和解析后的候选 action。
边界：测试和课程验收默认使用 mock provider；真实 provider 需要管理员启用和凭据存在。

### 4.3 Action Protocol

输入：LLM 原始输出。
行为：要求严格 JSON，校验 `kind`、`tool`、`args`、`reason`、`expectation` 等字段。
输出：合法 action 或 `schema_error` 反馈。
边界：未知工具、缺字段、类型错误、额外危险参数、非 JSON 文本都视为协议错误。

示例：

```json
{
  "kind": "tool",
  "tool": "run_tests",
  "args": { "target": "sample_app" },
  "reason": "确认当前失败测试",
  "expectation": "得到可解析的 pytest 失败摘要"
}
```

### 4.4 工具分发

输入：合法 action、工作区、策略 profile。
行为：根据工具注册表查找工具，校验参数，执行前调用 guardrail，执行后生成统一 `ToolResult`。
输出：工具状态、stdout/stderr 摘要、结构化 artifacts、耗时、diff 摘要和候选反馈。
边界：所有工具必须限制在声明工作区；shell 工具只能执行策略允许的命令。

第一版工具：`list_files`、`read_file`、`write_file`、`run_command`、`run_tests`、`run_lint`、`memory_search`、`memory_write`。

### 4.5 治理护栏

输入：action、工具 schema、工作区、策略 profile、凭据保护规则、命令规则。
行为：检查路径、命令、凭据文件、网络发布、递归删除、超时和输出脱敏。
输出：`allow`、`deny`、`needs_approval` 或 `rewrite`。
边界：硬规则命中的危险动作直接拒绝；可由人类承担风险的动作进入审批队列。

`strict_demo` 是默认 profile，只允许内置示例工作区和少量安全命令。`balanced_dev` 是本地开发可选 profile，允许更多只读命令和测试命令，但仍保护凭据与路径边界。

### 4.6 HITL 审批

输入：`needs_approval` 决策、原始 action、命中规则、run 上下文。
行为：创建审批请求，暂停当前动作，在 WebUI 展示风险和上下文。用户可批准一次、拒绝、要求修改、取消或等待过期。
输出：审批状态和反馈信号。
边界：审批只对当前 action 生效，不自动放宽整个策略；审批记录必须可审计。

状态机：`pending`、`approved_once`、`rejected`、`revision_requested`、`expired`、`cancelled`。

### 4.7 反馈闭环

输入：工具结果、测试输出、lint 输出、guardrail 决策、审批结果、协议错误。
行为：解析为结构化 `FeedbackSignal`，写入事件流和下一轮上下文。
输出：`test_failed`、`test_passed`、`lint_failed`、`command_failed`、`guardrail_blocked`、`approval_rejected`、`schema_error`、`timeout`、`file_diff` 等信号。
边界：反馈必须来自可观察结果，不能由 LLM 自称成功替代。

### 4.8 记忆

输入：运行事件、用户决策、工具失败、修复摘要、项目约定、策略说明。
行为：写入事件记忆和摘要记忆；下一轮根据标签、关键词、任务类型、时间和优先级做确定性检索。
输出：可注入 prompt 的相关记忆和可在 WebUI 浏览的记忆记录。
边界：不使用向量数据库；敏感记忆不能进入 prompt 或公开日志。

### 4.9 WebUI/API

输入：用户创建 run、点击演示、审批动作、查看状态、配置凭据。
行为：FastAPI 提供 REST API 和 SSE 事件流；React 前端展示可操作 dashboard。
输出：运行详情、事件时间线、审批队列、记忆视图、策略视图、凭据状态。
边界：公开部署默认 mock LLM；real LLM 需要管理员登录和环境变量启用。

### 4.10 CLI

输入：命令行参数，包括 demo 名称、工作区、策略 profile、LLM 模式和导出路径。
行为：创建 run、执行 demo、导出审计日志、检查配置状态。
输出：终端摘要、JSON 报告和退出码。
边界：CLI 不绕过 guardrail；CLI 和 WebUI 使用同一套 core。

## 5. 非功能性需求

### 5.1 性能

- WebUI 普通 API 请求在本地开发环境下应保持可交互，目标响应时间小于 500ms。
- SSE 事件应在步骤状态变化后尽快推送，避免长时间无反馈。
- 单个工具调用必须有超时配置，默认不超过 30 秒；测试命令可以由策略放宽。
- 文件读取和输出摘要必须限制大小，避免大文件或海量日志拖垮界面。

### 5.2 安全与凭据威胁模型

主要威胁包括：API key 被提交到 Git、被写入日志、被 WebUI 回显、被 agent 读取、被导出报告携带、被容器镜像固化、被终端历史泄露。

控制措施：

- `.env`、本地数据库、运行日志、keyring 缓存、导出报告默认不提交。
- WebUI 只显示 key 是否配置，不显示明文。
- 日志和事件流对疑似 key、token、Authorization header 做脱敏。
- guardrail 拒绝读取 `.env`、凭据文件、SSH key、云服务配置等敏感路径。
- Docker 镜像不包含真实 key，只通过运行时环境变量注入。
- 公开部署默认禁用真实 LLM。

### 5.3 可用性

用户应能通过两条路径完成核心体验：

- WebUI：打开 dashboard，点击 Demo Center 的一键演示，查看事件流、审批队列和最终报告。
- CLI：运行 demo 命令，得到 JSON 报告和可提交的日志证据。

### 5.4 可观测性

每次 run 都必须记录：创建参数、LLM 模式、策略 profile、每步 action、解析结果、guardrail 决策、审批状态、工具调用、反馈信号、记忆写入、最终状态和错误摘要。记录应能导出用于课程提交。

## 6. 系统架构

组件边界如下：

- `frontend`：React + Vite + TypeScript，负责 dashboard、demo、审批、记忆和设置界面。
- `api`：FastAPI，负责 HTTP API、SSE、静态资源和认证。
- `core`：agent 主循环、action parser、context builder。
- `llm`：mock provider 和 real provider。
- `tools`：工具注册、参数校验、执行适配器。
- `guardrails`：路径、命令、凭据、审批和脱敏规则。
- `feedback`：pytest/lint/命令/guardrail/协议错误解析。
- `memory`：SQLite 存储、检索和导出。
- `config`：策略 profile、环境变量、模型配置和工作区配置。
- `demos`：内置示例项目和 mock LLM 脚本。

数据流：用户入口创建 run，API 调用 core，core 调用 LLM，action 经过 parser 和 guardrail，dispatcher 执行工具，feedback 解析结果，memory 保存和检索，事件通过 SSE 推送给 WebUI。

## 7. 数据模型

主要实体：

| 实体 | 关键字段 | 说明 |
| --- | --- | --- |
| `Run` | `id`、`task`、`workspace`、`policy_profile`、`llm_mode`、`status`、`created_at`、`finished_at` | 一次 agent 运行 |
| `Step` | `id`、`run_id`、`index`、`status`、`raw_llm_output`、`parsed_action_id` | 一轮 agent 决策 |
| `Action` | `id`、`kind`、`tool`、`args`、`reason`、`expectation`、`schema_status` | LLM 请求的结构化动作 |
| `ToolCall` | `id`、`run_id`、`step_id`、`tool`、`status`、`duration_ms`、`summary` | 工具执行记录 |
| `GuardrailDecision` | `id`、`action_id`、`decision`、`rules`、`message` | 安全决策 |
| `ApprovalRequest` | `id`、`action_id`、`state`、`reviewer`、`reason`、`expires_at` | 人工审批 |
| `FeedbackSignal` | `id`、`run_id`、`step_id`、`type`、`severity`、`summary`、`details` | 可回灌反馈 |
| `MemoryRecord` | `id`、`scope`、`kind`、`tags`、`content`、`sensitive`、`confidence` | 事件或摘要记忆 |
| `ConfigProfile` | `name`、`tool_permissions`、`path_rules`、`command_rules` | 策略配置 |
| `CredentialStatus` | `provider`、`configured`、`source`、`last_checked_at` | 凭据状态，不保存明文 |

## 8. WebUI 页面要求

WebUI 必须完整可用，第一屏是 dashboard。

- Dashboard：运行概览、最近 run、失败反馈、待审批数量、当前策略和演示入口。
- New Run：选择内置示例或自定义工作区，选择 mock/real LLM，选择 `strict_demo` 或 `balanced_dev`。
- Run Detail：SSE 实时事件流、step、action、工具结果、反馈、diff 摘要、最终状态。
- Demo Center：一键运行三类机制演示，并展示每个演示的通过/失败证据。
- Approval Queue：查看风险、命中规则、原始 action，并批准、拒绝或要求修改。
- Memory：按标签、类型、run 和时间筛选记忆。
- Policies：查看策略 profile、工具权限、路径规则和命令规则。
- Credentials：本地模式可录入/清除 key；服务器模式只显示配置状态。
- Settings：管理员密码状态、真实 LLM 开关、base URL、模型名、导出选项。

视觉风格参考 Open Design 的设计文档化思路，但采用适合开发工具的克制 dashboard 形式。避免营销页、空泛英雄区和装饰性视觉堆叠。

## 9. 内置示例与一键演示

内置示例采用一个小型 Python bugfix 项目，包含故意失败的 pytest 测试。mock LLM 脚本必须支持以下演示：

1. 危险动作阻断：mock LLM 尝试执行递归删除或越界读取，guardrail 阻断并生成 `guardrail_blocked`。
2. 失败反馈修复：mock LLM 第一次做出错误修复，pytest 失败；第二轮读取反馈摘要后做出正确修复。
3. 工具边界：mock LLM 尝试读取工作区外文件，dispatcher/guardrail 拒绝并记录规则。
4. HITL 审批：mock LLM 发起需要审批的动作，WebUI 出现审批请求，用户决定会进入下一轮反馈。

这些演示必须能从 WebUI 点击运行，也必须能由 CLI 和 pytest 验证。

## 10. 部署与分发

Docker Compose 是主分发方式。后续实现必须提供：

- `Dockerfile`：构建后端、前端静态资源和运行时依赖。
- `docker-compose.yml`：启动 WebUI/API 服务并挂载数据目录。
- `.env.example`：列出可配置项，不包含真实 key。
- README 部署章节：包含本地 Docker、阿里云 Ubuntu、端口、安全组、防火墙、日志查看和更新流程。

服务器默认配置：

```env
LLM_MODE=mock
ENABLE_REAL_LLM=false
OPENAI_BASE_URL=https://njusehub.info/v1
OPENAI_MODEL=glm-5.2
ADMIN_PASSWORD=<server-local-secret>
```

## 11. CI 要求

必须同时提供两套 CI：

- `.gitlab-ci.yml`：至少包含 `unit-test` job，运行后端单元测试和核心机制测试。
- `.github/workflows/ci.yml`：运行 Python 测试、前端构建和 Docker 构建检查。

CI 不依赖真实 LLM，不需要 API key。所有机制测试使用 mock LLM。

## 12. 验收标准

- `pytest` 中包含并通过 action parser、guardrail、dispatcher、feedback、memory 和 approval 的单元测试。
- mock LLM 集成测试能完成内置 bugfix run。
- 机制测试证明危险动作被代码阻断。
- 机制测试证明失败反馈改变下一步动作。
- 机制测试证明越界工具调用被拒绝。
- WebUI 可以一键触发机制演示并实时显示事件。
- CLI 可以运行同样的 demo 并导出 JSON 报告。
- Docker Compose 可以启动完整应用。
- README 清楚说明 mock/real LLM、凭据、Docker 和阿里云部署。
- `SPEC_PROCESS.md` 记录 brainstorming、writing-plans、冷启动验证和修订过程。
- `AGENT_LOG.md` 记录 AI 协作、关键技能、commit、人工决策和偏差修正。
- `REFLECTION.md` 最终由人类所有者完成 1500-2500 字反思。

## 13. 风险与应对

- 范围过大：以治理为第一主贡献，优先交付机制闭环和一键演示。
- 真实 LLM 不稳定：默认 mock，真实模式只作为可选演示。
- 凭据泄露：keyring/env 注入、日志脱敏、敏感路径拒绝、公开部署默认禁用真实 LLM。
- WebUI 开发量大：优先 Dashboard、Demo Center、Run Detail、Approval Queue，再补齐 Memory、Policies、Credentials、Settings。
- Shell 跨平台差异：核心工具用 Python 封装，测试命令通过 `run_tests` 工具执行。
- 课程平台要求不一致：同时保留 GitHub Actions 和 `.gitlab-ci.yml`。

## 14. 冷启动验证要求

完成 `PLAN.md` 后，必须开启一个不同类型 agent 的全新 session，只提供 `SPEC.md` 和 `PLAN.md`，让它尝试实现 1-2 个任务。记录它的误解、缺失信息和暂停问题。根据结果修订 `SPEC.md` 与 `PLAN.md`。冷启动验证前不进入正式实现。

## 15. 版本门禁

当前版本只完成阶段 1 规约。下一步是用户审核本文档和 Superpowers 设计稿。审核通过后，进入 Superpowers `writing-plans`，生成细粒度 `PLAN.md`。只有 `SPEC.md`、`PLAN.md` 和冷启动验证都完成后，才能开始写 harness 实现代码。
