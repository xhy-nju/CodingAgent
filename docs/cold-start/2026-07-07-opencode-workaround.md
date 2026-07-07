# opencode 敏感词过滤排障记录

> 日期：2026-07-07
> 现象：opencode 显示 `sensitive_words_detected`，并进入长时间 retry。

## 1. 结论

这不是 CodingAgent 仓库代码报错，也不是冷启动验证逻辑失败，而是 opencode 调用的上游模型或网关在请求发送阶段拦截了提示词。继续等待通常不会解决，因为 retry 会反复发送同一份被拦截的上下文。

## 2. 根因

冷启动验证原提示词要求外部 agent 实现 Task 4。Task 4 是治理护栏测试，原始计划里包含了若干安全测试样例，例如：

- 高风险命令样例。
- 越界路径样例。
- 凭据脱敏样例。
- provider token 形态样例。

这些内容对本项目是正常的安全机制测试，但 opencode 使用的模型网关会把这类上下文判定为敏感内容。

## 3. 已采取的修订

已将 `PLAN.md` 和 `docs/superpowers/plans/2026-07-07-coding-agent-harness-implementation.md` 中最容易触发过滤的显式样例改为中性占位写法，同时保留测试意图：

- 仍然测试“高风险动作被阻断”。
- 仍然测试“路径越界被拒绝”。
- 仍然测试“token 形态文本被脱敏”。
- 不再在计划文档中直接写出容易被网关拦截的命令或 token 样例。

## 4. 继续验证的推荐步骤

1. 在 opencode 中按 `Ctrl+C` 停止当前 retry。
2. 确认不要提交 opencode 已经生成的半成品文件。
3. 重新从最新 GitHub 仓库拉取或使用当前修订后的 `SPEC.md` 与 `PLAN.md`。
4. 重新发起冷启动验证。
5. 如果仍触发过滤，改用 Task 2 进行冷启动验证，或改用 Cursor Agent / Claude Code / ChatGPT 编程代理完成冷启动。

## 5. opencode 安全提示词

如果继续使用 opencode，建议使用下面这版更克制的提示词：

```text
你正在进行一个课程项目的冷启动验证。你没有历史对话上下文，只能依据我提供的 SPEC.md 和 PLAN.md 工作。

请严格遵守：
1. 先阅读 SPEC.md 和 PLAN.md。
2. 不要实现整个项目，只尝试 PLAN.md 中的 Task 4：Guardrails, Redaction, And HITL Approval State Machine。
3. 按 PLAN.md 的 TDD 步骤执行：先写失败测试，再运行确认失败，再写最小实现，再运行确认通过。
4. 如果 PLAN.md 的文件路径、接口、测试代码、依赖关系、命令或预期结果不清楚，请立即停止，并列出具体不清楚之处。
5. 如果 SPEC.md 与 PLAN.md 冲突，请立即停止，并指出冲突位置。
6. 不要使用真实 provider token，不要新增运行凭据，不要修改与 Task 4 无关的文件。
7. 最后请输出：
   - 你是否能独立理解 Task 4。
   - 你修改了哪些文件。
   - 哪些测试先失败、后通过。
   - 你遇到的文档缺陷或歧义。
   - 如果继续实现，你建议先修订哪些文档。
```

## 6. 如果 opencode 仍失败

如果 opencode 仍然报告 `sensitive_words_detected`，这说明该 provider 对本项目的安全测试主题过于敏感。此时不要继续调提示词，直接记录为冷启动环境限制，并换用另一个外部 agent。课程要求的是使用不同类型 agent 做冷启动验证，并不要求必须使用 opencode。
