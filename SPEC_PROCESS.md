# SPEC_PROCESS.md

> 本文档用于记录 `SPEC.md` 与 `PLAN.md` 的生成、迭代和冷启动验证过程。它是课程要求中的过程证据，不是最终宣传文档。

## 阶段 0 决策记录

- 日期：2026-07-07。
- 仓库/工作区名称：`CodingAgent`。
- 项目类型：A 类项目，Coding Agent Harness。
- 技术栈：Python + Typer CLI + FastAPI WebUI/API + React/Vite/TypeScript 前端 + pytest + SQLite/JSON 本地存储。
- 机制范围：治理护栏 + 反馈闭环 + 记忆 + 工具分发。
- 第一主贡献：治理护栏 + HITL 审批 + 沙箱边界。
- 第二重点：反馈闭环。
- 分发方式：Docker / Docker Compose。
- 远程仓库：`https://github.com/xhy-nju/CodingAgent.git`。
- 默认分支：`main`。
- 实现边界：在 `SPEC.md`、`PLAN.md` 和冷启动验证完成前，不编写任何 harness 实现代码。

## 阶段 0：Superpowers 可用性检查

- 日期：2026-07-07。
- 检查内容：在当前 Codex 技能/插件环境中搜索 `superpowers`、`brainstorming`、`writing-plans`、`test-driven-development` 和 `subagent-driven-development`。
- 初始结果：当时的 Codex session 没有暴露匹配的 Superpowers 技能，也没有可安装的 Superpowers 插件候选。
- 影响：阶段 0 出现流程阻塞，不能直接声称完成官方 workflow。

## 阶段 0：Superpowers 官方安装路径确认

- 日期：2026-07-07。
- 来源：Superpowers 官方仓库 `https://github.com/obra/superpowers`。
- 官方信息摘要：Codex App 应通过侧边栏 Plugins 安装 `Superpowers`；Codex CLI 应通过 `/plugins` 搜索 `superpowers` 并选择安装。
- 处理方式：由人类所有者在 Codex App 中安装插件，再由 Codex 读取本地插件缓存确认。

## 阶段 0：Superpowers 安装完成确认

- 日期：2026-07-07。
- 安装来源：Codex 插件 `superpowers@openai-curated-remote`。
- 本地确认路径：`C:\Users\xhy\.codex\plugins\cache\openai-curated-remote\superpowers\6.1.1`。
- 已确认存在的关键技能：`using-superpowers`、`brainstorming`、`writing-plans`、`test-driven-development`、`subagent-driven-development`。
- 流程状态：阶段 0 的 Superpowers 工具链阻塞解除，可以进入阶段 1 的正式 brainstorming。

## 阶段 1：Brainstorming 总览

- 日期：2026-07-07。
- 使用技能：`superpowers:using-superpowers`、`superpowers:brainstorming`。
- 目标：在不写实现代码的前提下，完成项目定位、主贡献、技术栈、WebUI、LLM、凭据、部署和验收路径设计。
- 产物：`docs/superpowers/specs/2026-07-07-coding-agent-harness-design.md`、更新后的 `SPEC.md`、本过程记录和 `AGENT_LOG.md`。

## Brainstorming 关键迭代

### 迭代 1：项目定位与贡献维度

- 智能体问题：项目更偏课程演示、真实个人开发工具，还是安全/治理研究原型。
- 人类回答：选择课程演示 + 治理研究组合；主贡献维度包括治理护栏、反馈闭环、记忆、工具分发。
- 设计变化：把“治理护栏 + HITL + 沙箱边界”定为第一主贡献，反馈闭环作为第二重点，记忆和工具分发保持完整但克制。
- 接受原因：这样既覆盖用户希望的四个维度，又能让评分点集中，避免范围过散。

### 迭代 2：LLM 与测试策略

- 智能体问题：是否使用真实 LLM，如何处理课程要求中的 mock/stub LLM。
- 人类回答：拥有可调用大模型的 provider token，base URL 为 `https://njusehub.info/v1`，预估使用 `glm-5.2`。
- 设计变化：采用双模式 LLM。mock LLM 是测试、CI 和一键演示默认路径；real LLM 是管理员显式启用的可选模式。
- 接受原因：课程明确要求可用 mock/stub LLM 测试机制，但没有禁止真实 LLM。双模式兼顾可复现验收和真实体验。

### 迭代 3：凭据安全

- 智能体问题：provider token 应该如何保存，是否允许 `.env`。
- 人类回答：同意本地 keyring + Docker/CI/server 环境变量或 `.env` 的组合方案。
- 设计变化：本地开发优先使用 OS keyring；Docker、CI 和服务器部署使用环境变量或挂载 `.env`。WebUI 只显示配置状态，不回显明文。
- 接受原因：keyring 更适合本机安全，环境变量更适合容器部署；同时明确 `.env` 明文风险。

### 迭代 4：前端目标与设计资源

- 智能体问题：WebUI 做最小面板还是完整可用前端。
- 人类回答：希望做成完整可用的前端，并参考 Open Design 仓库。
- 设计变化：选定 React + Vite + TypeScript + FastAPI。WebUI 页面包括 Dashboard、New Run、Run Detail、Demo Center、Approval Queue、Memory、Policies、Credentials、Settings。
- 接受原因：完整 WebUI 能直接支撑课程要求中的 WebUI URL 和演示说明，也能让治理与反馈机制可见。

### 迭代 5：实时事件与一键演示

- 智能体问题：运行状态用轮询、SSE 还是 WebSocket；演示放在 CLI、pytest 还是 WebUI。
- 人类回答：希望能在 WebUI 上一键演示。
- 设计变化：选择 SSE 事件流；机制演示同时提供 WebUI 一键、CLI 脚本和 pytest 测试。WebUI 是演示主入口，pytest 是客观验证。
- 接受原因：SSE 足够表达 run timeline，复杂度低；WebUI 一键演示更适合展示，pytest 更适合评分验证。

### 迭代 6：部署方式

- 智能体问题：是否可以利用阿里云主机部署，服务器环境如何。
- 人类回答：有阿里云主机，Ubuntu 已安装 Docker。
- 设计变化：部署路径确定为阿里云 Ubuntu + Docker Compose。公开部署默认 mock LLM，real LLM 需 `ENABLE_REAL_LLM=true` 和管理员登录。
- 接受原因：Docker Compose 与课程分发要求一致，也能让部署步骤可复现。

### 迭代 7：CI 平台兼容

- 智能体问题：课程材料同时提到 GitHub 仓库和 `.gitlab-ci.yml`，要选一个还是都做。
- 人类回答：两者都写。
- 设计变化：`.gitlab-ci.yml` 提供课程要求的 `unit-test` job；GitHub Actions 运行 Python 测试、前端构建和 Docker 构建。
- 接受原因：避免平台表述冲突造成扣分，同时保持 GitHub 仓库的自动检查。

### 迭代 8：治理策略强度

- 智能体问题：工具权限采用严格 demo 默认，还是更宽松的开发默认。
- 人类回答：同意严格 demo 默认，同时保留开发 profile。
- 设计变化：默认 `strict_demo`，仅允许内置示例工作区和少量安全命令；可选 `balanced_dev` 用于本地开发。
- 接受原因：课程验收更看重确定性和安全边界，开发便利性可以作为显式选择。

## AI 建议中被采纳的部分

- 采用 Python + Typer + FastAPI + React/Vite/TypeScript：理由是后端、CLI、WebUI 和测试生态成熟，适合课程项目快速闭环。
- 采用 mock primary + real optional：理由是课程测试可复现，同时不浪费用户已有 provider token。
- 使用严格 JSON Action Protocol：理由是 action parser 可测试，能把 LLM 输出错误转为反馈。
- 用 SSE 做实时事件流：理由是实现简单、适合单向 run timeline。
- 把治理作为第一主贡献：理由是最能体现 harness 相比普通 prompt agent 的工程价值。
- 同时提供 WebUI、CLI 和 pytest 演示：理由是兼顾展示体验、自动化和客观评分。
- Docker Compose 部署到阿里云 Ubuntu：理由是符合用户已有基础设施和课程分发要求。
- 同时写 `.gitlab-ci.yml` 和 GitHub Actions：理由是兼容课程文本和实际仓库托管平台。

## AI 建议中被推翻或修正的部分

- 初始倾向是先做最小 WebUI 面板；人类所有者希望完整可用前端。最终改为完整 dashboard 方案。
- 初始可选方案中曾考虑 CLI/pytest 为主要演示入口；人类所有者要求 WebUI 一键演示。最终改为 WebUI 主入口，CLI/pytest 作为验证补充。
- 对于真实 LLM，初始方案强调 mock-first。人类所有者说明有 provider token 后，方案修正为 dual-mode，但仍保持 mock 为验收默认。
- 对部署目标，初始只确认 Docker 分发。人类所有者提出已有阿里云 Ubuntu 主机后，方案细化为 Docker Compose 服务器部署。

## 冷启动验证计划

冷启动验证属于阶段 3，尚未执行。阶段 2 完成 `PLAN.md` 后，将选择一个不同类型 agent 的全新 session，只提供 `SPEC.md` 和 `PLAN.md`，让它尝试实现 1-2 个任务。需要记录：

- 它是否理解第一主贡献是治理护栏。
- 它是否能按 TDD 先写失败测试。
- 它是否把 mock LLM 当作测试默认路径。
- 它是否误解 WebUI、Docker、CI 或凭据要求。
- 它提出的问题暴露出哪些 spec 或 plan 缺陷。

冷启动反馈将用于修订 `SPEC.md` 和 `PLAN.md`。

## 对规约过程的阶段性反思

本阶段 brainstorming 的价值在于先锁定“课程演示 + 治理研究”的定位，避免项目同时追求真实智能、复杂前端、通用插件和生产部署。最关键的澄清是：mock LLM 不是偷懒，而是课程要求的可测试机制入口；真实 LLM 可以存在，但不能成为唯一验收路径。

另一个收获是 WebUI 从“状态面板”升级为“演示和审批工作台”。这会增加实现工作量，但能让治理护栏、反馈闭环和记忆机制被直观看见。后续 writing-plans 必须控制任务颗粒度，优先交付 Dashboard、Demo Center、Run Detail 和 Approval Queue，再补齐较低优先级页面。

## 阶段 1 自检记录

- 已把设计写入 `docs/superpowers/specs/2026-07-07-coding-agent-harness-design.md`。
- 已把根目录 `SPEC.md` 从骨架改为完整中文规约。
- 已记录至少三轮 brainstorming 迭代；实际记录八轮关键迭代。
- 已明确第一主贡献、mock/real LLM、WebUI、部署、CI 和凭据策略。
- 已保留阶段门禁：用户审阅后才能进入 `writing-plans`，冷启动验证前不写实现代码。

## 阶段 2：Writing Plans 记录

- 日期：2026-07-07。
- 使用技能：`superpowers:writing-plans`。
- 输入文档：`SPEC.md` 与 `docs/superpowers/specs/2026-07-07-coding-agent-harness-design.md`。
- 输出文档：`docs/superpowers/plans/2026-07-07-coding-agent-harness-implementation.md` 与同步后的 `PLAN.md`。
- 计划结构：16 个任务，覆盖 Python 核心、Action Protocol、策略加载、SQLite 事件存储、治理护栏、审批状态机、工具分发、反馈解析、记忆、mock LLM、agent loop、CLI、FastAPI/SSE、React WebUI、真实 LLM 凭据、Docker/CI 和最终课程证据。
- 任务粒度：每个任务包含失败测试、红灯验证、最小实现、绿灯验证和提交点；任务内部步骤以 2-5 分钟行动为单位。
- 范围处理：虽然项目包含多个子系统，但它们都服务于同一个可运行 harness 纵向闭环，因此阶段 2 采用一个总实现计划，并按任务保持可独立审查。
- 下一门禁：正式执行 Task 1 前，必须先做冷启动验证。冷启动 agent 只读取 `SPEC.md` 和 `PLAN.md`，尝试实现 1-2 个小任务，并把误解和卡点记录回本文件。

## 阶段 3：冷启动验证准备

- 日期：2026-07-07。
- 状态：准备完成，实际冷启动验证尚未执行。
- 准备文档：`docs/cold-start/2026-07-07-validation-guide.md`。
- 验证方式：选择一个不同于当前 Codex 会话的外部 coding agent，只提供 `SPEC.md` 与 `PLAN.md`。
- 推荐验证任务：优先验证 `PLAN.md` 中的 Task 4：Guardrails, Redaction, And HITL Approval State Machine；也可以选择 Task 2：Policy Profiles And Strict Action Parser。
- 记录要求：外部 agent 的名称、执行任务、是否遵守 TDD、是否误解主贡献、是否试图扩大范围、暴露出的文档歧义和关键输出摘要。
- 下一步：人类所有者运行外部冷启动验证，并把结果发回当前会话；当前 Codex 再根据结果修订 `SPEC.md` 或 `PLAN.md`。
## 阶段 3：opencode 冷启动中断记录

- 日期：2026-07-07。
- 外部 agent：opencode。
- 执行任务：按冷启动提示词尝试 Task 4。
- 现象：运行中显示 `sensitive_words_detected` 并进入 retry。
- 初步产物：opencode 已在本地生成 `tests/test_guardrails.py` 与 `tests/test_approvals.py` 两个未跟踪文件，内容与 `PLAN.md` Task 4 的失败测试基本一致。
- 根因判断：上游模型/网关对安全测试上下文中的高风险命令、越界路径和 token 脱敏样例触发过滤；这不是项目代码失败。
- 处理：新增 `docs/cold-start/2026-07-07-opencode-workaround.md`，并将 `PLAN.md` 与 Superpowers plan 中最容易触发过滤的显式样例改成中性占位写法。
- 当前结论：本次 opencode 冷启动未完成，不能算通过。需要停止当前 retry，避免提交半成品测试文件，并用修订后的文档重跑，或换用 Cursor/Claude/ChatGPT 编程代理完成冷启动。

## 阶段 3：opencode 冷启动验证完成与修订

- 日期：2026-07-07。
- 外部 agent：opencode。
- 执行任务：`PLAN.md` Task 4，Guardrails, Redaction, And HITL Approval State Machine。
- 验证结论：opencode 能独立理解 Task 4 的目标和第一主贡献，但 Task 4 依赖 Task 1/2 的领域模型、策略加载和策略配置，原计划对此提示不足。
- opencode 产物：生成了 Task 4 自身文件，以及 Task 1/2 的前置依赖文件；这些文件未提交，作为冷启动证据处理。
- 测试结果：opencode 报告 Red 阶段为导入失败，Green 阶段为 3 passed / 2 failed。失败点分别是 `strict_demo` 对 `run_command` 的白名单/审批语义冲突，以及脱敏测试输入与正则模式不匹配。
- 本地复核：运行 `pytest tests/test_guardrails.py tests/test_approvals.py -v --basetemp pytest-tmp`，退出码为 1，结果为 3 passed / 2 failed；失败点与 opencode 报告一致。
- 修订 1：在 `PLAN.md` 与 Superpowers plan 中将 `run_command` 加入 `strict_demo.allowed_tools`，使需要审批的工具能够到达 `require_approval_tools` 检查。
- 修订 2：在 Task 4 的 `SECRET_PATTERNS` 示例中增加 `token=...` 形态，保证脱敏测试样例与实现一致。
- 修订 3：在 Task 4 开头增加前置依赖说明，允许冷启动 agent 为 Task 4 精确创建 Task 1/2 依赖文件，但这些文件只属于验证脚手架。
- 修订 4：在冷启动提示词中将范围限制改为“不要修改 Task 4 依赖链之外的文件”。
- 修订 5：新增 `docs/cold-start/2026-07-07-opencode-validation-result.md`，记录完整验证结论和处置决定。
- 当前结论：冷启动验证已产生有效反馈并完成文档修订。opencode 生成的实现文件不进入正式提交；下一阶段应从 Task 1 按 TDD 顺序正式实现。

## 阶段 4：正式实现与任务提交记录

- 日期：2026-07-07 至 2026-07-08。
- 使用技能：`superpowers:executing-plans`、`superpowers:test-driven-development`、`superpowers:systematic-debugging`、`superpowers:verification-before-completion`。
- 执行方式：在 linked worktree `D:\Projects\CodingAgent\.worktrees\task1-domain-models` 上按 `PLAN.md` Task 1-15 顺序实现，每个主要任务以测试或可验证命令收尾，并形成独立提交。
- 关键提交：
  - `4c510f9 feat: add core domain models`
  - `325156f feat: add policies and action parser`
  - `5332a36 feat: add sqlite audit store`
  - `3d1a07e feat: add deterministic guardrails and approvals`
  - `3501b46 feat: add guarded file tools`
  - `7c76f1a feat: parse objective feedback signals`
  - `6e53ec2 feat: add command tools and sample workspace`
  - `cc65025 feat: add deterministic memory service`
  - `ac5137c feat: add mock-driven agent loop`
  - `3a2de65 feat: add mock demo cli`
  - `b829da6 feat: expose harness api and sse`
  - `7132695 feat: scaffold frontend api client`
  - `3af238d feat: add operational frontend dashboard`
  - `b220983 fix: keep api demo workspaces in runtime dir`
  - `47aee7c feat: gate optional real llm credentials`
  - `392672d chore: add docker ci and deployment docs`
- 人工确认点：人类所有者在 WebUI 可访问、demo 按钮不再返回 500 后确认“均正常”，随后进入 Task 15 和 Task 16。

## 阶段 4：最终验证证据

- 日期：2026-07-08。
- 工作区：`D:\Projects\CodingAgent\.worktrees\task1-domain-models`。
- 后端测试命令：`pytest -q`。
- 观察结果：退出码 0，`45 passed in 17.08s`。
- 前端测试命令：`cd frontend && npm run test -- run`。
- 观察结果：退出码 0，`Test Files 2 passed (2)`，`Tests 5 passed (5)`。
- 前端构建命令：`cd frontend && npm run build`。
- 观察结果：退出码 0，Vite 构建成功，生成 `dist/index.html` 与 assets。
- mock bugfix demo 命令：`$env:PYTHONPATH='src'; D:\Anaconda\python.exe -m coding_agent demo bugfix`。
- 观察结果：退出码 0，输出 `status: succeeded`，run id 为 `run-86a9f8114175`，反馈包含 `test_passed`。
- guardrail demo 命令：`$env:PYTHONPATH='src'; D:\Anaconda\python.exe -m coding_agent demo dangerous-action`。
- 观察结果：退出码 1，输出 `status: failed`，反馈包含 `guardrail_blocked`，规则为 `path.outside_workspace`。该失败是预期的治理拦截结果，不是系统错误。
- Docker 构建命令：`docker compose build`。
- 观察结果：退出码 0，输出 `coding-agent  Built`，镜像名为 `task1-domain-models-coding-agent`。
- WebUI URL 验证：`http://127.0.0.1:5174/`。
- 观察结果：HTTP 200。
- WebUI API 代理验证：`http://127.0.0.1:5174/api/credentials/status`。
- 观察结果：HTTP 200，返回 `provider=openai-compatible`、`configured=false`、`source=missing`、`base_url=https://njusehub.info/v1`、`model=glm-5.2`、`real_enabled=false`。
- 敏感信息检查：真实 `OPENAI_API_KEY` 未写入仓库；`.env`、本地数据、日志、数据库和运行导出由 `.gitignore` 与 `.dockerignore` 排除。

## 阶段 5：工程交付补全

- 日期：2026-07-11。
- 设计规范：`docs/superpowers/specs/2026-07-11-engineering-delivery-design.md`，提交 `3381340`。
- 实施计划：`docs/superpowers/plans/2026-07-11-engineering-delivery-implementation.md`，提交 `f472b9b`。
- 人工决策：公开部署采用“匿名 Mock、管理员登录后使用 Real/审批/Memory”的访问边界。
- 实现结果：
  - 凭据支持 Docker Secret、环境变量和 Keyring，提供隐藏设置、状态、更新、清除命令。
  - 管理员会话采用 HMAC 签名及 HttpOnly、SameSite Cookie。
  - 真实模型通过与 Mock 相同的 AgentLoop、Action、Guardrail、工具、反馈、Memory、HITL 和审计链路。
  - SSE 支持事件序号与断线续读；待审批运行可在进程重启后重建上下文。
  - WebUI 支持 Mock/Real、登录、真实任务、审批、Memory 搜索与实时状态。
  - 生产分发增加 Docker Secret、健康检查、Nginx HTTPS、GHCR 和敏感信息扫描。
- 关键提交：`e57a2f9..b078521`、`9a542b4`、`5473d04`、`35111d0`、`0c2b9d7`、`79361b5`、`90a00ff`。
- 过程调整：早期凭据任务使用多轮独立审查，定位了审批字段、Keyring 可用性和提示词脱敏缺口。人类所有者随后要求提高效率，后续任务改为直接实现、集中测试、仅在失败时修正。

## 阶段 5：最终验收证据

- 后端：`pytest -q`，退出码 0，`139 passed in 27.95s`。
- 前端：`npm run test`，退出码 0，`2` 个测试文件、`10` 项测试通过。
- 前端构建：`npm run build`，退出码 0，Vite 成功生成生产 assets。
- Compose：`docker compose config --quiet`，退出码 0。
- Docker：`docker compose build`，退出码 0，镜像 `task1-domain-models-coding-agent` 构建成功。
- 容器：`docker compose ps` 显示 `healthy`；`http://127.0.0.1:8000/api/health` 与 WebUI 均返回 HTTP 200。
- Mock bugfix：状态 `succeeded`，反馈为 `test_passed`，2 项示例测试通过。
- Mock guardrail：状态 `failed`，反馈为 `guardrail_blocked`，规则 `path.outside_workspace`；退出码 1 是预期治理结果。
- 真实模型：容器内凭据状态为 `configured=true`、`real_enabled=true`；`llm probe` 返回 `ok=true`、`model=glm-5.2`、`protocol_valid=true`、`action_kind=final`，延迟 3793 ms。
- 浏览器：Mock 一键运行进入 `succeeded`，SSE 时间线完整，管理员登录对话框可访问，浏览器控制台无错误。
- 响应式验收限制：前端测试和 CSS 包含 720/760 px 移动断点，生产构建通过；in-app 浏览器的临时 viewport override 未改变其固定 1280×720 视口，因此最终阿里云部署后仍需用真实手机或 DevTools 补一张移动端截图作为外部证据。
