# CodingAgent 工程交付设计

日期：2026-07-11

状态：已确认，待实施

目标分支：`task1-domain-models`

## 1. 背景与目标

当前项目已经具备严格 Action Protocol、工具分发、确定性 Guardrail、HITL、反馈闭环、Memory、SQLite 审计、Mock 演示、真实 LLM 探针、React WebUI、Docker 与基础 CI。工程交付阶段需要补齐以下闭环：

1. 让真实 LLM 驱动既有 AgentLoop，而不是仅能执行独立探针。
2. 在同一 WebUI 中同时支持匿名 Mock 演示和受保护的真实 LLM 运行。
3. 实现凭据设置、状态、更新、清除、隐藏输入和多来源解析。
4. 为真实运行、审批及敏感数据增加管理员认证和公网安全边界。
5. 补齐实时运行状态、完整审批操作、错误恢复、生产部署、镜像发布及交付文档。

本阶段不引入多用户、角色权限、Redis、Celery 或外部身份提供商。系统仍是面向课程演示和单管理员部署的单体应用。

## 2. 方案选择

采用单体安全控制台：FastAPI 同时提供 API、会话认证和 React 静态页面，SQLite 保存运行、事件、审批和 Memory，后台线程执行真实模型任务。

没有采用仅依靠 Nginx Basic Auth 的方案，因为它无法同时满足“Mock 匿名、真实操作受保护”的细粒度边界。没有采用独立认证服务和任务队列，因为它会显著增加部署复杂度，并超出单管理员课程项目的需求。

## 3. 访问边界

### 3.1 匿名访问

- 启动两个确定性 Mock 演示。
- 查看 Mock 运行摘要和脱敏事件。
- 查看策略名称。
- 查看不包含密钥内容的凭据配置状态。
- 查看服务健康状态。

### 3.2 管理员访问

- 启动真实 LLM 运行。
- 查看真实运行摘要和事件。
- 查看及处理审批。
- 查看和检索项目 Memory。
- 查看管理设置和退出登录。

API 必须根据运行记录中的 `llm_mode` 判断事件和详情是否需要认证，不能由客户端声明访问级别。

## 4. 真实 LLM Agent 运行

### 4.1 运行入口

新增统一运行创建接口。请求包含 `mode`、任务文本和受支持的演示工作区名称。Mock 模式仍保留现有快捷入口；Real 模式要求有效管理员会话、真实模式已启用且凭据已配置。

真实运行只允许使用系统复制出的示例工作区。API 不接受任意宿主路径，模型也不能改变工作区根目录。

### 4.2 后台执行

API 先创建运行记录并返回 `run_id`，再由进程内后台执行器调用 AgentLoop。并发真实运行数量使用小型有界执行器限制，避免模型请求和测试命令耗尽服务器资源。

AgentLoop 支持使用预先创建的 `run_id` 继续执行。Mock 和 Real 共用：

- Action 解析器；
- GuardrailEngine；
- ToolDispatcher；
- FeedbackSignal；
- MemoryService；
- ApprovalService；
- EventBus 和 SQLite 审计。

Real 模式唯一替换的核心依赖是 `LLMProvider`。不得创建绕过 Guardrail 或直接执行模型文本的真实模式旁路。

### 4.3 模型上下文

RealLLMProvider 的系统提示明确列出：

- 唯一允许的 Action JSON Schema；
- 可用工具、参数和行为边界；
- 一次只返回一个 Action；
- 当前任务、步骤编号和最大步骤；
- 最近一次结构化反馈；
- 最多五条相关 Memory；
- 工作区隔离、禁止泄露秘密和禁止输出 Markdown 代码块的约束。

模型响应仍由严格解析器验证。Schema 错误变成反馈并进入下一步；达到最大步数后运行失败。

### 4.4 状态与实时事件

新增运行状态查询接口，返回 `created`、`running`、`waiting_approval`、`succeeded`、`failed` 或 `cancelled`。SSE 按 SQLite 事件序号增量轮询，在运行结束前保持连接，并支持客户端通过最后事件序号继续读取。

容器启动时将遗留的 `created` 或 `running` 运行标记为失败并记录中断原因，避免重启后永久显示运行中。`waiting_approval` 可保留，因为审批请求和 Action 已持久化；批准时根据运行记录重建执行上下文。

## 5. 凭据生命周期

### 5.1 解析优先级

统一由 CredentialService 返回凭据快照：

1. `OPENAI_API_KEY_FILE` 指向的 Docker Secret；
2. `OPENAI_API_KEY` 环境变量；
3. 操作系统 Keyring 中的项目凭据；
4. 未配置。

Docker Secret 文件读取时限制文件大小、去除首尾换行并拒绝空值。Keyring 仅用于本机 CLI；容器部署优先使用 Docker Secret，兼容服务器 `.env`。

### 5.2 CLI

提供以下命令：

- `coding-agent credentials set`：隐藏输入、二次确认并写入 Keyring；
- `coding-agent credentials update`：执行同样流程并覆盖已有值；
- `coding-agent credentials status`：仅返回是否配置、来源、Base URL、模型和真实模式开关；
- `coding-agent credentials clear`：删除 Keyring 值，不影响显式环境变量或 Docker Secret；
- `coding-agent llm probe`：使用统一解析结果发起最小真实调用。

缺少凭据时，状态和探针输出必须给出下一步命令，但不得回显任何密钥片段。

### 5.3 脱敏

凭据快照向 Store、事件公开层和异常转换层提供当前密钥，仅用于精确值脱敏。密钥不得进入模型任务、事件原文、SQLite、HTTP 响应、日志或前端状态。已知 Token 格式仍由通用规则脱敏。

## 6. 管理员认证

### 6.1 会话

新增：

- `POST /api/auth/login`；
- `GET /api/auth/status`；
- `POST /api/auth/logout`。

服务端用 `hmac.compare_digest` 校验 `ADMIN_PASSWORD`。登录成功后生成包含签发时间、过期时间和随机会话标识的载荷，并用独立 `SESSION_SECRET` 进行 HMAC-SHA256 签名。

会话保存在 `HttpOnly`、`SameSite=Strict` Cookie 中。`COOKIE_SECURE=true` 时启用 Secure，生产 HTTPS 部署必须开启。登出使 Cookie 立即过期。签名错误、格式错误和过期会话统一视为未登录。

### 6.2 配置安全

生产启动拒绝默认 `ADMIN_PASSWORD` 或默认 `SESSION_SECRET`。开发和 Mock 本地模式可使用显式开发值，但凭据状态必须显示部署是否安全就绪。状态接口不返回密码、Secret 或签名。

状态变更接口检查 `Origin` 或同源上下文。登录失败返回统一 401，不区分密码错误和服务端未配置。认证错误经过相同脱敏层处理。

## 7. WebUI

保留现有紧凑运维控制台和响应式布局。

### 7.1 Dashboard

- 使用 `Mock / Real` 分段控制切换模式。
- Mock 模式展示 bugfix 与 guardrail 两个一键演示。
- Real 模式展示受控任务输入、模型状态、登录状态和启动按钮。
- 未登录进入 Real 模式时允许查看说明，但启动操作打开登录对话框。

### 7.2 Run Detail

- 展示运行模式、状态、步骤、反馈和时间线。
- SSE 到达时增量更新，不倒序覆盖已有事件。
- 网络断开时显示重连状态；终态后关闭连接并获取最终摘要。

### 7.3 Approvals

- 管理员可查看待审批 Action、触发规则和原因。
- 批准或拒绝都必须输入审核人和理由。
- 提交期间禁用按钮，成功后刷新审批队列和运行状态。
- 服务端继续保证单次批准、单次执行；重复请求返回 409。

### 7.4 Memory 与 Credentials

- Memory 支持 scope、关键词和标签查询。
- Credentials 仅展示来源和状态，指向 CLI、环境变量或 Docker Secret 配置方式。
- WebUI 不提供 API Key 输入和更新表单。

## 8. 错误处理

- 模型连接、超时、HTTP 错误、无效响应结构和后台异常均转换为脱敏运行失败事件。
- API 使用稳定状态码：401 未认证，403 禁止操作，404 资源不存在，409 状态冲突，422 输入错误，503 真实模式或凭据未就绪。
- 后台任务的异常不得使工作线程静默退出，也不得让运行停留在 `running`。
- SSE 不发送 `llm.output` 原始事件名，继续使用面向前端的允许列表和脱敏载荷。
- 所有输入设置长度上限；任务、审核人和理由拒绝空白内容。

## 9. 测试与验收

### 9.1 后端

- 凭据来源优先级、Keyring 设置/更新/清除和隐藏状态；
- 会话签名、过期、Cookie 属性、错误密码和权限矩阵；
- Real Agent 使用伪 HTTP 响应驱动同一 AgentLoop；
- 后台成功、失败、重启恢复和运行状态接口；
- Mock 匿名、Real 受保护、真实事件受保护；
- SSE 增量事件、终态关闭和脱敏；
- HITL 批准与拒绝的单次执行语义。

CI 中禁止访问真实模型服务，真实调用仅通过人工 `llm probe` 验收。

### 9.2 前端

- 模式切换和匿名 Mock；
- 登录、退出和受保护 Real 启动；
- Run Detail 实时更新；
- 审批表单和冲突错误；
- Memory 搜索和凭据状态；
- 桌面与移动视口无重叠、无溢出。

### 9.3 最终命令

- `pytest -q`；
- `npm test`；
- `npm run build`；
- `python -m coding_agent demo bugfix`；
- `python -m coding_agent demo dangerous-action`；
- `python -m coding_agent llm probe`，仅在人工配置真实凭据时执行；
- `docker compose config --quiet`；
- `docker compose build`；
- 容器健康检查和浏览器桌面/移动验收。

## 10. 分发与部署

- Dockerfile 保持非 root 运行和锁文件构建。
- Compose 增加健康检查、Docker Secret 挂载和生产配置校验。
- 提供 Nginx HTTPS 反向代理模板，不在应用容器中终止 TLS。
- GitHub Actions 执行后端测试、前端测试与构建、Docker 构建和敏感信息扫描。
- 增加 GHCR 发布工作流，为版本标签和手工触发构建公开镜像。
- README 给出源码构建与公开镜像拉取两种部署方式。
- 阿里云部署必须配置安全组、防火墙、HTTPS、非默认管理员密码、随机会话 Secret 和只读 Docker Secret。

公开 URL、公开镜像标签和最终 CI 链接只有在实际发布成功后写入交付文档，不预填虚假地址。

## 11. 文档与课程证据

- README：中文功能说明、目录结构、Mock/Real 操作、凭据生命周期、已知限制、部署和公开地址。
- SPEC：更新版本状态和本阶段安全、真实运行需求。
- PLAN：添加本阶段任务，完成后逐项记录提交哈希。
- SPEC_PROCESS：记录设计决策、验证命令和观测结果。
- AGENT_LOG：记录代理分工、关键提交和人工决策。
- REFLECTION：仅提供实施事实和可引用证据，最终 1500 至 2500 字个人反思由学生本人完成；使用 AI 润色时按课程要求披露。

## 12. 完成定义

满足以下条件才算工程交付完成：

1. 匿名用户可一键完成两个 Mock 演示。
2. 管理员可登录并从 WebUI 启动真实 LLM Agent 运行。
3. 真实运行经过与 Mock 相同的 Action、护栏、工具、反馈、Memory、审批和审计链路。
4. API Key 具备设置、状态、更新、清除和隐藏输入流程，且不会泄露。
5. 管理员可在 WebUI 完成批准或拒绝，并保持 exactly-once 执行语义。
6. 后端、前端、Docker 和安全测试全部通过。
7. 公开镜像、CI、中文文档和可复现部署说明齐备。
8. 在获得服务器信息并实际部署后，公开 WebUI URL 可从外部访问。
