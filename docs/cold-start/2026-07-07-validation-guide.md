# 冷启动验证指南

> 日期：2026-07-07
> 目标：在正式实现前，验证一个无历史上下文的不同类型 agent 仅凭 `SPEC.md` 和 `PLAN.md` 是否能理解任务。
> 边界：冷启动验证只用于暴露文档缺陷，不要求产出可合并代码。

## 1. 为什么必须做

课程要求在实现前进行 cold-start validation。它要模拟一个新 agent 没有读过对话历史、没有项目记忆、不了解我们之前的决策，只依赖 `SPEC.md` 和 `PLAN.md` 开始工作。如果它误解项目目标、遗漏安全门禁、跳过 TDD、默认使用真实 LLM，说明文档还不够清楚，必须先修订文档再进入实现。

## 2. 推荐使用的外部 agent

优先选择一个与当前 Codex 会话不同类型的工具，例如：

- Cursor Agent
- Claude Code
- ChatGPT 网页版的编程代理模式
- 通义灵码、GitHub Copilot Workspace 或其他可读文件的 coding agent

不要使用当前同一个 Codex 会话继续验证，因为它已经拥有完整历史上下文，不能代表冷启动。

如果使用 opencode 时出现 sensitive_words_detected，请先阅读 docs/cold-start/2026-07-07-opencode-workaround.md。这是上游模型网关对安全测试上下文的过滤，不代表项目代码失败。

## 3. 提供给外部 agent 的材料

只提供这两个文件：

- `SPEC.md`
- `PLAN.md`

不要提供：

- 本对话历史
- `AGENT_LOG.md`
- `SPEC_PROCESS.md`
- Superpowers 设计稿
- 你对项目的额外解释
- 我的总结或口头补充

如果外部 agent 需要仓库文件，可以让它读取整个仓库，但提示词中必须要求它主要依据 `SPEC.md` 和 `PLAN.md`，并在缺信息时暂停提问。

## 4. 推荐验证任务

请选择下面两个任务之一进行冷启动验证。

### 任务 A：验证 Task 2

让外部 agent 尝试实现 `PLAN.md` 中的 Task 2：Policy Profiles And Strict Action Parser。

这个任务适合检查：

- 是否理解严格 JSON Action Protocol。
- 是否按 TDD 先写失败测试。
- 是否理解 mock/real LLM 不是本任务范围。
- 是否能按计划创建 `config/policies/*.json`、`policies.py`、`action_parser.py`。

### 任务 B：验证 Task 4

让外部 agent 尝试实现 `PLAN.md` 中的 Task 4：Guardrails, Redaction, And HITL Approval State Machine。

这个任务适合检查：

- 是否理解第一主贡献是 deterministic guardrails。
- 是否把危险动作阻断写成代码，而不是 prompt。
- 是否理解 HITL 状态机。
- 是否能正确处理路径越界、命令黑名单、凭据脱敏。

推荐先选任务 B，因为它最贴近项目第一主贡献。

## 5. 给外部 agent 的提示词

把下面内容作为外部 agent 的第一条消息，并附上 `SPEC.md` 与 `PLAN.md`。

```text
你正在进行一个课程项目的冷启动验证。你没有任何历史对话上下文，只能依据我提供的 SPEC.md 和 PLAN.md 工作。

请严格遵守：
1. 先阅读 SPEC.md 和 PLAN.md。
2. 不要实现整个项目，只尝试 PLAN.md 中的 Task 4：Guardrails, Redaction, And HITL Approval State Machine。
3. 按 PLAN.md 的 TDD 步骤执行：先写失败测试，再运行确认失败，再写最小实现，再运行确认通过。
4. 如果你发现 PLAN.md 中的文件路径、接口、测试代码、依赖关系、命令或预期结果不清楚，请立即停止，并列出具体不清楚之处，不要自行脑补。
5. 如果你发现 SPEC.md 与 PLAN.md 冲突，请立即停止，并指出冲突位置。
6. 不要使用真实 LLM provider token，不要新增真实凭据，不要修改 Task 4 依赖链之外的文件。Task 4 依赖 Task 1/2 的基础模型和策略文件时，可以按 PLAN.md 精确创建这些前置文件。
7. 最后请输出：
   - 你是否能独立理解 Task 4。
   - 你修改了哪些文件。
   - 哪些测试先失败、后通过。
   - 你遇到的文档缺陷或歧义。
   - 如果继续实现，你建议先修订哪些文档。
```

如果你希望验证 Task 2，把提示词第 2 条中的任务名称替换为：

```text
Task 2：Policy Profiles And Strict Action Parser
```

## 6. 你需要记录的结果

外部 agent 完成或停止后，请把以下内容发回当前 Codex 会话：

- 使用的外部 agent 名称。
- 它选择执行的任务编号。
- 它是否在没有额外解释的情况下开始。
- 它是否遵守 TDD。
- 它是否试图跳过冷启动门禁或直接实现更多任务。
- 它是否误用真实 LLM、凭据、WebUI 或 Docker。
- 它指出的歧义、缺失、冲突。
- 它生成的关键输出摘要。

## 7. 判定标准

通过冷启动验证的最低标准：

- 外部 agent 能明确说出第一主贡献是治理护栏。
- 外部 agent 能识别 mock LLM 是默认测试路径。
- 外部 agent 能按 `PLAN.md` 找到目标文件和测试文件。
- 外部 agent 知道先写失败测试。
- 外部 agent 遇到不清楚处会暂停提问，而不是扩大范围。

如果不满足以上任一项，需要先修订 `SPEC.md` 或 `PLAN.md`。

## 8. 验证后下一步

你把外部 agent 的结果发回后，当前 Codex 会：

1. 把冷启动结果写入 `SPEC_PROCESS.md`。
2. 根据暴露的问题修订 `SPEC.md` 或 `PLAN.md`。
3. 提交修订。
4. 再次请求你确认是否进入正式实现。

只有冷启动验证完成并修订文档后，才能进入 Task 1 的实际代码实现。
