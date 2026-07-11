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
  - 已有真实 LLM provider token，base URL 为 `https://njusehub.info/v1`，模型预期为 `glm-5.2`。
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
## 2026-07-07 - 阶段 3 - opencode 敏感词过滤排障

- 任务：分析用户在 opencode 冷启动验证中遇到的 `sensitive_words_detected`。
- 使用技能：`superpowers:systematic-debugging`。
- 证据：截图显示 opencode 在请求阶段被上游过滤并 retry；本地仓库出现 opencode 生成的未跟踪 `tests/test_guardrails.py` 与 `tests/test_approvals.py`。
- 根因：原 `PLAN.md` Task 4 包含安全测试所需的高风险命令、越界路径和 token 脱敏样例；opencode 的 provider 对这些上下文过敏。
- 修订：新增 opencode workaround 文档，并把 `PLAN.md` 与 Superpowers plan 中的显式样例改为中性占位写法。
- 边界：没有进入正式实现；opencode 生成的未跟踪测试文件不应提交为项目实现。

## 2026-07-07 - 阶段 3 - opencode 冷启动验证结果处理

- 任务：根据 opencode 返回的 Task 4 冷启动验证报告完成文档修订和阶段收口。
- 使用技能：`superpowers:receiving-code-review`、`superpowers:verification-before-completion`。
- 外部反馈摘要：opencode 能理解 Task 4，但发现 `PLAN.md` 内部存在 `run_command` 白名单/审批冲突、provider-token 脱敏样例与正则不匹配、Task 4 对 Task 1/2 依赖说明不足，以及 Task 4 脱敏范围需要标注为最小切片。
- 处理结果：修订 `PLAN.md` 与 Superpowers plan 的 `strict_demo.allowed_tools`，修订 Task 4 的 provider-token 脱敏正则示例，为 Task 4 增加前置依赖和最小脱敏范围说明，修订冷启动提示词的范围边界，新增 `docs/cold-start/2026-07-07-opencode-validation-result.md`。
- 取舍：不提交 opencode 生成的 `src/`、`tests/`、`config/` 和 `pyproject.toml`，因为这些文件是冷启动验证脚手架，且未按 Task 1/2/4 的正式 TDD 顺序完成。
- 下一步：清理未跟踪验证脚手架，提交文档修订，然后从 Task 1 开始正式实现。

## 2026-07-08 - 阶段 4 - 正式实现 Task 1-12

- 任务：按 `PLAN.md` 从核心领域模型推进到 API/SSE 和前端 API client。
- 使用技能：`superpowers:executing-plans`、`superpowers:test-driven-development`、`superpowers:verification-before-completion`。
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
- 人工干预：人类所有者多次确认继续下一部分；实现保持每个任务独立提交，避免一次性大爆炸。
- 经验教训：TDD 红绿循环让 action parser、guardrail、approval、store、memory 和 CLI 的边界比较清晰；越靠近 Web/API，越需要同步人工演示需求和自动测试。

## 2026-07-08 - 阶段 4 - WebUI Dashboard 与 500 排障

- 任务：实现完整 WebUI Dashboard、Demo Center、Run Detail、Approvals、Memory、Policies、Credentials、Settings。
- 关键提交：`3af238d feat: add operational frontend dashboard`。
- 人工反馈：人类所有者在浏览器中遇到“无法访问此站点”和按钮 500。
- 调试技能：`superpowers:systematic-debugging`。
- 排障结论 1：`无法访问此站点` 的直接原因是 Vite dev server 未运行；后续启动并验证 `http://127.0.0.1:5174/` 返回 200。
- 排障结论 2：按钮 500 的根因是 API demo workspace 使用系统 Temp 目录，Windows 当前运行上下文拒绝创建目录。
- 修复提交：`b220983 fix: keep api demo workspaces in runtime dir`。
- 验证：`tests/test_api.py` 新增 workspace 位置回归测试；真实 HTTP demo 请求不再返回 500。

## 2026-07-08 - 阶段 4 - Task 14 真实 LLM Gate

- 任务：实现凭据状态与可选真实 LLM provider。
- 关键提交：`47aee7c feat: gate optional real llm credentials`。
- 实现内容：新增 `CredentialService`、`RealLLMProvider`、API `/api/credentials/status` 完整状态、CLI `credentials status`，WebUI Credentials 页显示 `base_url` 与 `model`。
- 安全边界：真实 provider token 只从环境变量读取；状态接口和 WebUI 不回显 key。
- 验证：`pytest` 通过 41 个测试；前端测试和构建通过；`/api/credentials/status` 通过前端代理返回 HTTP 200。

## 2026-07-08 - 阶段 4 - Task 15 Docker、CI 与部署文档

- 任务：增加 Docker 分发、GitHub Actions、GitLab CI、阿里云 Ubuntu 部署说明。
- 关键提交：`392672d chore: add docker ci and deployment docs`。
- 实现内容：新增 `Dockerfile`、`docker-compose.yml`、`.dockerignore`、`.env.example`、`.github/workflows/ci.yml`、`.gitlab-ci.yml`，并将 README 重写为可读中文。
- 额外接线：FastAPI 在 `frontend/dist` 存在时挂载静态 WebUI，使 Docker 镜像在 8000 端口同时提供 API 和前端。
- 人工/环境干预：本地 Docker CLI 已安装但 Docker Desktop 未运行；由 Codex 启动 Docker Desktop 后完成 `docker compose build`。
- 验证：`pytest -q` 45 passed；`npm run build` 通过；`docker compose build` 生成 `task1-domain-models-coding-agent` 镜像。

## 2026-07-08 - 阶段 4 - Task 16 最终验证证据

- 任务：运行最终验证命令并记录课程证据。
- 验证命令与结果：
  - `pytest -q`：退出码 0，45 passed。
  - `cd frontend && npm run test -- run`：退出码 0，2 个测试文件、5 个测试通过。
  - `cd frontend && npm run build`：退出码 0，Vite 构建成功。
  - `$env:PYTHONPATH='src'; D:\Anaconda\python.exe -m coding_agent demo bugfix`：退出码 0，`status=succeeded`。
  - `$env:PYTHONPATH='src'; D:\Anaconda\python.exe -m coding_agent demo dangerous-action`：退出码 1，包含 `guardrail_blocked`，这是预期拦截。
  - `docker compose build`：退出码 0，`coding-agent Built`。
  - `http://127.0.0.1:5174/`：HTTP 200。
  - `http://127.0.0.1:5174/api/credentials/status`：HTTP 200。
- 经验教训：最终证据文档应记录命令、退出码和观察结果，不应只写“已通过”；对预期 exit code 1 的护栏演示必须解释其语义。

## 2026-07-10 - Real LLM Probe

- Spec: `docs/superpowers/specs/2026-07-10-real-llm-probe-design.md`.
- Added the TDD-built `python -m coding_agent llm probe` command.
- The probe validates one strict `final` Action without constructing an Agent Loop or executing tools.
- Automated verification: backend tests, frontend tests/build, and Docker build passed.
- Mock verification: bugfix succeeded; dangerous-action was blocked as designed.
- Sanitized real-provider verification: `ok=true`, `model=glm-5.2`, `protocol_valid=true`, `action_kind=final`.
- Secret hygiene: no API key, Authorization header, or raw model response was added to Git.

## 2026-07-11 - 完整工程交付

- 人类所有者选择：匿名开放 Mock 演示，真实 LLM、审批和管理能力要求管理员登录。
- Codex 使用 Superpowers 完成设计和实施计划，随后在 linked worktree 中实施。
- 凭据任务先由子代理实现并独立审查；审查发现非环境变量密钥未贯穿脱敏、审批字段遗漏和提示词泄露路径，修复后全量测试达到 115 项。
- 人类所有者要求减少重复复核后，Codex 直接完成管理员认证、运行恢复、真实 Agent、SSE/HITL、WebUI 和生产分发，每项仅在实现后集中运行测试并修正失败。
- 提交：
  - `e57a2f9..b078521`：安全凭据生命周期与全链路脱敏。
  - `9a542b4`：管理员签名会话。
  - `5473d04`：持久化运行生命周期与恢复。
  - `35111d0`：真实模型驱动受治理 AgentLoop。
  - `0c2b9d7`：实时 SSE 与持久化审批恢复。
  - `79361b5`：完整 Mock/Real WebUI。
  - `90a00ff`：生产 Compose、Nginx、CI 与 GHCR。
- 未伪造的外部证据：公开镜像、PR/CI 链接和阿里云公网 URL 要在实际推送和部署成功后补写。
- 最终本地验收：后端 139 项、前端 10 项通过，生产构建、Docker 构建和 Compose 配置成功；容器健康，Mock 演示和真实 `glm-5.2` 探针成功，浏览器控制台无错误。

## 2026-07-11 - 提交文档收敛

- 人类所有者明确选择 GitHub 作为唯一仓库、PR、CI 和镜像发布平台，当前不执行 NJU GitLab 相关操作。
- Codex 对照课程要求和代码现状修订 `SPEC.md`、`PLAN.md`、`README.md`、`REFLECTION.md` 与过程记录。
- 修订重点：消除尚未实现的 WebUI/CLI 承诺，补齐领域机制、技术选型、三项可复现演示和第三方许可证。
- 学术边界：Codex 未代写最终个人反思，只整理可核验事实、建议结构与 AI 使用披露模板。

## 2026-07-11 - GitHub 交付与 v1.0.0 发布

- 在人类所有者确认课堂允许 AI 辅助反思撰写后，Codex 根据既有事实材料整理第一人称最终反思，并保留 AI 使用披露。
- 分支 `task1-domain-models` 推送后创建 PR #1；gitleaks PR 扫描缺少 `GITHUB_TOKEN`，通过提交 `1c170cc` 修复并获得 8 项 CI 全绿。
- PR #1 合并后，main CI 暴露 Python 同 mtime、同文件长度重写导致的陈旧 `.pyc` 问题。
- 在分支 `codex/fix-demo-pycache` 以 TDD 添加确定性复现，提交 `62cd484` 清理可变工作区字节码；PR #2 的 8 项 CI 全绿后合并。
- main CI 成功后推送 `v1.0.0`，GHCR workflow 成功发布 `ghcr.io/xhy-nju/coding-agent:1.0.0`、`1.0` 和 `latest`。
- 真实外部链接已写入 README；阿里云公网部署和视频仍待完成。
