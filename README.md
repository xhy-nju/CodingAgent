# CodingAgent

CodingAgent 是 AI4SE 期末项目 A 类方向的 Coding Agent Harness。项目目标是自己实现一个可治理、可测试、可复现的 coding agent 运行外壳，而不是把现成 agent 框架配置后作为交付物。

核心机制包括 agent 主循环、严格 Action Protocol、mock/real LLM 抽象、工具分发、治理护栏、HITL 审批、反馈闭环、记忆机制、WebUI 和 Docker 分发。

## 当前状态

项目处于阶段 1：Superpowers brainstorming 与 SPEC 规约阶段。

已完成：

- 阶段 0 项目初始化。
- GitHub remote 关联：`https://github.com/xhy-nju/CodingAgent.git`。
- Superpowers 插件安装确认。
- 阶段 1 brainstorming 关键决策确认。
- 正式设计稿：`docs/superpowers/specs/2026-07-07-coding-agent-harness-design.md`。
- 根目录中文规约：`SPEC.md`。

仍然禁止：在 `SPEC.md`、`PLAN.md` 和冷启动验证完成前，不编写任何 harness 实现代码。

## 已确认技术栈

- 后端与核心：Python。
- CLI：Typer。
- Web/API：FastAPI。
- 前端：React + Vite + TypeScript。
- 测试：pytest。
- 存储：SQLite，辅以 JSON 导出。
- 分发：Docker / Docker Compose。
- 真实 LLM 接口：OpenAI-compatible API，默认 `OPENAI_BASE_URL=https://njusehub.info/v1`，预期模型 `glm-5.2`。

## 项目主贡献

第一主贡献是治理护栏、HITL 审批和沙箱边界。反馈闭环是第二重点，记忆和工具分发完整实现并接受 mock LLM 驱动的确定性测试。

课程验收默认使用 mock LLM。真实 LLM 仅作为可选扩展，公开部署默认禁用真实 LLM。

## 关键文档

- `SPEC.md`：完整项目规约。
- `PLAN.md`：阶段计划骨架，后续由 Superpowers writing-plans 补全为细粒度任务。
- `SPEC_PROCESS.md`：规约生成、迭代和冷启动验证过程记录。
- `AGENT_LOG.md`：AI 协作开发全过程日志。
- `REFLECTION.md`：最终反思报告草稿。
- `docs/superpowers/specs/2026-07-07-coding-agent-harness-design.md`：Superpowers brainstorming 正式设计稿。

## 安全边界

真实 API key 和任何凭据都不能提交到仓库。`.env`、本地数据库、运行日志、本地 keyring 缓存和导出报告中的敏感字段都必须保持在本地并被 `.gitignore` 排除。后续实现必须提供安全录入、状态查看、更新和清除流程，并在日志和 WebUI 中避免明文回显。

## GitHub 仓库

远程仓库：`https://github.com/xhy-nju/CodingAgent.git`
默认分支：`main`
remote 名称：`origin`

常用检查命令：

```bash
git status
git remote -v
git branch --show-current
```

## 下一步

请先审阅 `SPEC.md` 和 Superpowers 设计稿。确认后进入阶段 2：调用 Superpowers `writing-plans`，把设计拆成 2-5 分钟粒度的 TDD 实现任务。阶段 2 和冷启动验证完成前，不进入正式实现。
