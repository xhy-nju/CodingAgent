# CodingAgent

CodingAgent 是 AI4SE 期末项目 A 类方向的 Coding Agent Harness。项目计划使用 Python 实现一个由我们自己编码的 harness 内核，而不是把现成 agent 框架简单配置后作为交付物。这个 harness 将包含 agent 主循环、确定性的工具分发、治理护栏、反馈闭环、记忆机制，以及 Docker 分发能力。

## 当前状态

项目目前处于阶段 0：项目初始化与流程准备。按照课程要求，在 `SPEC.md`、`PLAN.md` 完成并通过冷启动验证之前，不允许编写任何 harness 实现代码。

当前 Codex 环境暂未暴露课程要求中的 Superpowers 技能，包括 `brainstorming`、`writing-plans`、`test-driven-development` 等。因此，在正式声称符合 Superpowers 工作流之前，必须先启用 Superpowers，或在另一个支持 Superpowers 的编码智能体中完成对应流程，并把证据记录到 `SPEC_PROCESS.md` 和 `AGENT_LOG.md`。

## 计划技术栈

- Python
- Typer CLI
- FastAPI WebUI/API
- pytest
- 本地 JSON/SQLite 存储
- Docker 分发

## 必需文档

- `SPEC.md`：项目规约与设计文档。
- `PLAN.md`：实现计划与任务拆分。
- `SPEC_PROCESS.md`：规约生成、迭代和冷启动验证过程记录。
- `AGENT_LOG.md`：与 AI 协作开发的全过程日志。
- `REFLECTION.md`：最终反思报告草稿。

## 安全边界

真实 API Key 和任何凭据都不能提交到仓库。`.env`、本地密钥文件、日志、运行时状态等都必须留在本地，并通过 `.gitignore` 排除。后续实现中也必须提供安全录入、查看状态、更新和清除凭据的流程。

## 仓库设置

GitHub 仓库名计划为 `CodingAgent`，与本地工作区目录保持一致。

创建 GitHub 空仓库后，在本地工作区执行：

```bash
git branch -M main
git remote add origin https://github.com/<your-account>/CodingAgent.git
git push -u origin main
```

创建远程仓库时不要初始化 README、`.gitignore` 或 license，因为本地仓库已经包含这些项目文件。提交前也要再次确认没有真实凭据、`.env` 文件、本地凭据存储、日志或生成的运行时状态进入仓库。
