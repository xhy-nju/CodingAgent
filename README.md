# CodingAgent

CodingAgent 是 AI4SE 期末项目 A 类方向的 Coding Agent Harness。项目目标是从零实现一个可治理、可测试、可复现、可演示的 coding agent 运行外壳，而不是把现成 agent 框架简单配置后作为交付物。

核心机制包括：严格 Action Protocol、mock/real LLM 抽象、工具分发、治理护栏、HITL 审批、反馈闭环、记忆机制、WebUI 和 Docker 分发。

## 当前状态

已完成的主线能力：

- Python 核心 agent loop、SQLite 审计/记忆存储、事件流。
- Guardrail、redaction、approval、反馈信号与记忆写入。
- Typer CLI 与 FastAPI API。
- React + Vite + TypeScript WebUI。
- Mock LLM 默认演示与可选 OpenAI-compatible 真实 LLM gate。
- Docker、Compose、GitHub Actions、GitLab CI 分发骨架。

## 技术栈

- 后端与核心：Python 3.11+、Pydantic v2、FastAPI、Typer、SQLite。
- 前端：React、Vite、TypeScript、Vitest。
- 测试：pytest、Vitest。
- 分发：Docker、Docker Compose。
- 真实 LLM 接口：OpenAI-compatible API，默认 `OPENAI_BASE_URL=https://njusehub.info/v1`，默认模型 `glm-5.2`。

## 本地运行

先安装 Python 包：

```bash
pip install -e .[dev]
```

运行两个确定性演示：

```bash
python -m coding_agent demo bugfix
python -m coding_agent demo dangerous-action
```

启动 API：

```bash
uvicorn coding_agent.api:app --reload
```

前端开发模式：

```bash
cd frontend
npm install --no-package-lock
npm run dev
```

## Docker 演示

创建本地环境文件：

```bash
cp .env.example .env
```

编辑 `.env`，至少把 `ADMIN_PASSWORD` 改成非默认值。公开演示时建议保持：

```env
ENABLE_REAL_LLM=false
```

启动 Docker Compose：

```bash
docker compose up --build
```

## 真实 LLM 连通性验证

在 `.env` 中配置 `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_MODEL`，并设置：

```env
ENABLE_REAL_LLM=true
```

重新构建容器后执行一次安全探测：

```bash
docker compose up --build -d
docker compose exec coding-agent python -m coding_agent llm probe
```

探测只发送固定的低 token 请求并验证严格 Action Protocol，不会创建 Agent
运行、执行工具或修改工作区。输出不会包含 API Key 或模型原始响应。Mock 演示仍使用：

```bash
docker compose exec coding-agent python -m coding_agent demo bugfix
docker compose exec coding-agent python -m coding_agent demo dangerous-action
```

查看日志：

```bash
docker compose logs -f coding-agent
```

Docker 版本会在 `8000` 端口同时提供 API 和构建后的 WebUI。

## 阿里云 Ubuntu 部署要点

1. 在安全组中开放选定端口，默认示例是 `8000`。
2. 服务器上只保留 `.env`，不要把真实 key 提交到仓库。
3. 设置非默认 `ADMIN_PASSWORD`。
4. 公开演示保持 `ENABLE_REAL_LLM=false`，避免误消耗真实模型额度。
5. 使用 `docker compose logs -f coding-agent` 查看运行日志。
6. 如需启用真实模型，设置 `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_MODEL`，并显式设置 `ENABLE_REAL_LLM=true`。

## CI

GitHub Actions 覆盖后端测试、前端测试/构建和 Docker build。GitLab CI 提供课程平台常见的 `unit-test` job，运行：

```bash
pytest -q
```

## 安全边界

真实 provider token 和任何凭据都不能提交到仓库。`.env`、本地数据库、运行日志、本地 keyring 缓存和导出报告中的敏感字段都必须保持在本地并被 `.gitignore` 或 `.dockerignore` 排除。

## GitHub 仓库

远程仓库：`https://github.com/xhy-nju/CodingAgent.git`

常用检查命令：

```bash
git status
git remote -v
git branch --show-current
```
