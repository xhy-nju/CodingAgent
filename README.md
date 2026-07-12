# CodingAgent

## 项目信息

| 项目 | 地址或说明 |
| --- | --- |
| 项目名称 | CodingAgent Harness |
| 代码仓库 | [github.com/xhy-nju/CodingAgent](https://github.com/xhy-nju/CodingAgent) |
| 公网 WebUI | [http://47.96.99.58/](http://47.96.99.58/) |
| 演示视频 | [项目演示视频.mp4](项目演示视频.mp4) |
| 容器镜像 | `ghcr.io/xhy-nju/coding-agent:1.0.1` |
| 最新版本 | [`v1.0.1`](https://github.com/xhy-nju/CodingAgent/tree/v1.0.1) |
| 最新 main CI | [GitHub Actions #29197433911](https://github.com/xhy-nju/CodingAgent/actions/runs/29197433911) |

公网 WebUI 部署在按量计费的阿里云 ECS 上，课程提交与验收期间保持运行；实例停机时该地址不可访问。当前以 HTTP 地址提供课程演示，生产使用应按[阿里云部署文档](docs/deployment-aliyun.md)配置域名和 HTTPS。

CodingAgent 是 AI4SE 期末项目 A 类方向的 Coding Agent Harness。项目自行实现 Agent 主循环、严格动作协议、工具分发、治理护栏、HITL 审批、反馈闭环、记忆和审计机制，不使用现成 Agent 框架充当主体。

## 主要贡献

- **治理护栏**：所有模型动作先通过确定性策略检查，越界路径和危险命令在执行前阻断。
- **反馈闭环**：测试、命令、文件差异、审批和 Schema 错误统一转成结构化反馈回灌下一步。
- **记忆机制**：SQLite 持久化项目级摘要，按 scope、标签和关键词确定性检索。
- **工具分发**：严格 Action JSON 经解析、Guardrail 和 Dispatcher 后才能调用文件、测试、命令及 Memory 工具。

项目同时提供可重复的 Mock LLM 演示和真实 OpenAI-compatible LLM 模式。二者共用同一套 AgentLoop、护栏、工具、反馈、Memory、审批与审计链路。

## WebUI 功能

- Dashboard：Mock/Real 模式切换、策略和凭据状态、最近运行摘要。
- Mock 演示：一键执行 bugfix 反馈闭环和危险路径拦截。
- Real 运行：管理员登录后输入任务，真实模型在隔离示例工作区中驱动 Agent。
- Run Detail：SSE 实时事件、步骤状态和结构化反馈。
- Approvals：查看待审批动作，填写审核人和理由，批准一次或拒绝。
- Memory：按关键词和标签搜索项目记忆。
- Credentials：仅显示配置状态和来源，不接收、不回显 API Key。
- Policies/Settings：查看当前策略和运行配置。

匿名用户可以运行 Mock 演示。真实 LLM、审批、Memory 和管理操作要求管理员签名会话。

## 技术栈

- 后端：Python 3.11+、FastAPI、Pydantic v2、Typer、SQLite、httpx、keyring。
- 前端：React、TypeScript、Vite、Vitest、Lucide Icons。
- 测试：pytest、Vitest。
- 分发：Docker、Docker Compose、Nginx、GitHub Actions、GHCR。
- 默认模型接口：`https://njusehub.info/v1`，模型 `glm-5.2`。

## 目录结构

```text
.
├── src/coding_agent/       # AgentLoop、API、认证、凭据、Store、工具与策略
├── frontend/               # React 运维控制台
├── config/policies/        # strict_demo 与 balanced_dev 策略
├── demos/sample_workspace/ # 隔离 bugfix 示例工程
├── deploy/nginx.conf       # HTTPS 反向代理模板
├── tests/                  # 后端与机制测试
├── docs/                   # 设计、计划、部署与冷启动证据
├── Dockerfile
├── docker-compose.yml
└── docker-compose.production.yml
```

## 本地运行

```bash
pip install -e .[dev]
python -m coding_agent demo bugfix
python -m coding_agent demo dangerous-action
uvicorn coding_agent.api:app --reload
```

访问 `http://127.0.0.1:8000`。前端开发模式：

```bash
cd frontend
npm ci
npm run dev
```

## 凭据配置

本机推荐使用系统 Keyring。所有输入均隐藏，状态命令不会显示密钥片段：

```bash
python -m coding_agent credentials set
python -m coding_agent credentials status
python -m coding_agent credentials update
python -m coding_agent credentials clear
```

解析优先级为 Docker Secret、`OPENAI_API_KEY` 环境变量、系统 Keyring。真实连通性探针：

```bash
python -m coding_agent llm probe
```

`.env` 是服务器上的明文文件，只应用于本地或受控部署，必须限制权限且不得提交。生产环境优先使用 `OPENAI_API_KEY_FILE=/run/secrets/openai_api_key`。

## Docker 演示

```bash
cp .env.example .env
docker compose up --build -d
docker compose ps
docker compose logs -f coding-agent
```

在 `.env` 中至少修改：

```env
ADMIN_PASSWORD=使用高强度管理员密码
SESSION_SECRET=至少32位随机字符串
ENABLE_REAL_LLM=false
COOKIE_SECURE=false
```

需要真实模式时设置 `ENABLE_REAL_LLM=true` 并配置密钥。Mock 演示不依赖外部模型，适合课程现场展示。

## 生产部署

生产 Compose 从 GHCR 拉取镜像，仅把应用绑定到 `127.0.0.1:8000`，由 Nginx 提供公网 HTTPS：

```bash
docker compose -f docker-compose.production.yml pull
docker compose -f docker-compose.production.yml up -d
```

完整阿里云 Ubuntu 步骤见 [docs/deployment-aliyun.md](docs/deployment-aliyun.md)。生产环境必须使用 Docker Secret、非默认管理员密码、随机 Session Secret 和 HTTPS。

## 验证命令

```bash
pytest -q
cd frontend && npm test && npm run build
docker compose config --quiet
docker compose build
```

危险动作演示预期退出码为 1，因为 Guardrail 正确阻止了越界操作，这不代表程序异常。

## 课程机制演示

| 课程要求 | 演示入口 | 预期证据 |
| --- | --- | --- |
| 危险动作被代码阻断 | WebUI `Guardrail block`；或 `python -m coding_agent demo dangerous-action` | 状态为 `failed`，反馈含 `guardrail_blocked` 和 `path.outside_workspace` |
| 注入失败改变下一步动作 | WebUI `Feedback repair`；或 `python -m coding_agent demo bugfix` | 先观察失败测试，随后修复并复测为 `test_passed` |
| 主贡献的确定性行为 | `pytest tests/test_agent_loop.py::test_approved_action_executes_exactly_once_then_run_resumes -v` | HITL 批准动作只执行一次，运行随后恢复 |

前两个 Mock 场景无需 API Key，适合录制一键演示。第三项用自动化测试稳定证明治理主贡献的 exactly-once 语义；真实模型触发高风险 Action 时，也可在管理员 Approval Queue 中操作同一状态机。

## CI 与镜像

- GitHub Actions：后端、前端、Docker、Compose 和敏感信息扫描。
- `v*` 标签或手工触发 `publish-image.yml` 后发布 GHCR 镜像。

公开镜像：`ghcr.io/xhy-nju/coding-agent:1.0.1`，同时发布 `1.0` 和 `latest` 标签。课程部署建议固定使用 `1.0.1`，避免浮动标签带来版本差异。

交付证据：

- [完整工程 PR #1](https://github.com/xhy-nju/CodingAgent/pull/1)
- [字节码稳定性修复 PR #2](https://github.com/xhy-nju/CodingAgent/pull/2)
- [真实 LLM calculator 闭环修复 PR #4](https://github.com/xhy-nju/CodingAgent/pull/4)
- [公网部署配置修复 PR #5](https://github.com/xhy-nju/CodingAgent/pull/5)
- [演示视频 PR #6](https://github.com/xhy-nju/CodingAgent/pull/6)
- [最新 main 分支 CI](https://github.com/xhy-nju/CodingAgent/actions/runs/29197433911)
- [v1.0.1 镜像发布](https://github.com/xhy-nju/CodingAgent/actions/runs/29180966316)

公开 WebUI：[http://47.96.99.58/](http://47.96.99.58/)；健康检查为 `http://47.96.99.58/api/health`。演示视频见仓库根目录的[项目演示视频.mp4](项目演示视频.mp4)。

## 安全边界

- API Key 不进入浏览器、提示词、日志、事件、SQLite 或 Git 历史。
- Docker Secret、环境变量和 Keyring 密钥均在持久化前统一脱敏。
- 管理员会话使用 HMAC 签名、HttpOnly、SameSite=Strict Cookie；HTTPS 部署启用 Secure。
- 真实运行只操作复制到 `CODING_AGENT_DATA_DIR` 下的示例工程。
- HITL 批准使用状态机和数据库条件更新保证单次批准、单次执行。
- 跨域管理写请求被拒绝。

## 已知限制

- 当前是单管理员、单进程课程演示系统，不包含多用户 RBAC 和外部身份提供商。
- 后台执行器位于应用进程内；容器重启会将运行中任务标记失败，待审批任务可恢复。
- SQLite 适合单机部署，不面向多副本水平扩展。
- 真实模型行为受外部服务稳定性、额度和兼容性影响，因此 CI 和默认演示使用 Mock。

## 第三方依赖与许可证

项目运行时使用的主要开源依赖如下，许可证以各项目实际安装版本随附文本为准：

| 依赖 | 用途 | 许可证 |
| --- | --- | --- |
| [FastAPI](https://github.com/fastapi/fastapi) | Web API 与 SSE | MIT |
| [Pydantic](https://github.com/pydantic/pydantic) | 领域模型和协议校验 | MIT |
| [Typer](https://github.com/fastapi/typer) | CLI | MIT |
| [httpx](https://github.com/encode/httpx) | OpenAI-compatible HTTP 调用 | BSD-3-Clause |
| [keyring](https://github.com/jaraco/keyring) | 本机凭据存储 | MIT |
| [React](https://github.com/facebook/react) | WebUI | MIT |
| [Vite](https://github.com/vitejs/vite) | 前端构建 | MIT |
| [Vitest](https://github.com/vitest-dev/vitest) | 前端测试 | MIT |
| [Lucide](https://github.com/lucide-icons/lucide) | WebUI 图标 | ISC |

开发过程参考 [Open Design](https://github.com/nexu-io/open-design) 的设计组织方式，并使用 Superpowers 工作流技能。二者不作为运行时框架打包，项目没有复用现成 Agent 主循环或第三方项目源码。

## 仓库

[xhy-nju/CodingAgent](https://github.com/xhy-nju/CodingAgent)

代码托管、Pull Request、CI 和容器镜像发布均以 GitHub 为准。
