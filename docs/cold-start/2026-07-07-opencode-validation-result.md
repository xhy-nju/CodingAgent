# opencode 冷启动验证结果

> 日期：2026-07-07
> 外部 agent：opencode
> 验证任务：`PLAN.md` Task 4，Guardrails, Redaction, And HITL Approval State Machine

## 1. 总体结论

opencode 能够在只依据 `SPEC.md` 和 `PLAN.md` 的情况下理解 Task 4 的目标：实现治理护栏、脱敏和 HITL 审批状态机。它也识别出 Task 4 是项目第一主贡献“治理护栏”的核心切片。

本次冷启动验证不视为可合并实现。opencode 生成了 Task 4 文件及 Task 1/2 前置依赖文件，但最终测试没有全部通过，并暴露出 `PLAN.md` 中两处内部冲突和两处文档歧义。因此本次产物用于修订文档，不进入正式实现提交。

## 2. opencode 生成的文件

Task 4 自身文件：

- `tests/test_guardrails.py`
- `tests/test_approvals.py`
- `src/coding_agent/redaction.py`
- `src/coding_agent/guardrails.py`
- `src/coding_agent/approvals.py`

Task 4 前置依赖文件：

- `pyproject.toml`
- `src/coding_agent/__init__.py`
- `src/coding_agent/domain.py`
- `src/coding_agent/policies.py`
- `config/policies/strict_demo.json`
- `config/policies/balanced_dev.json`

这些文件均保持未提交状态，仅作为冷启动验证证据。

## 3. 测试结果摘要

opencode 报告的 Red 阶段结果：

- `tests/test_guardrails.py` 因缺少 `coding_agent.guardrails` 收集失败。
- `tests/test_approvals.py` 因缺少 `coding_agent.approvals` 收集失败。

opencode 报告的 Green 阶段结果：

- 3 个测试通过。
- 2 个测试失败。

通过的测试覆盖路径越界拒绝、命令黑名单拒绝和审批状态机流转。失败测试分别来自 `run_command` 审批策略冲突和 provider-token 脱敏样例与正则不同步。

本地复核命令：

```powershell
pytest tests/test_guardrails.py tests/test_approvals.py -v --basetemp pytest-tmp
```

本地复核结果：退出码为 1，结果为 3 passed / 2 failed。两个失败分别是 `run_command` 返回 `DENY` 而非 `NEEDS_APPROVAL`，以及 `token=demo-redaction-value-123456` 未被脱敏。该结果确认 opencode 产物不是可直接合并的正式实现。

## 4. 暴露出的文档问题

### 问题 1：`strict_demo` 策略与 Task 4 测试冲突

`PLAN.md` Task 2 中 `strict_demo.json` 的 `allowed_tools` 未包含 `run_command`，但 `require_approval_tools` 包含 `run_command`。Task 4 的测试期望 `run_command` 返回 `NEEDS_APPROVAL`，而 guardrail 实现会先因为工具不在白名单中返回 `DENY`。

修订：已在 `PLAN.md` 和 Superpowers plan 中将 `run_command` 加入 `strict_demo.allowed_tools`。

### 问题 2：脱敏测试样例与正则模式冲突

Task 4 测试输入为 `token=demo-redaction-value-123456`，但原计划中的 `SECRET_PATTERNS` 只匹配 `demo-token-...` 或 `Token ...` 形态。

修订：已在 `PLAN.md` 和 Superpowers plan 中加入 `token=...` 形态的 provider-token 正则。

### 问题 3：Task 4 依赖关系不够明确

Task 4 的接口依赖 Task 1 的领域模型和 Task 2 的策略加载/策略配置。原冷启动提示词要求“不要修改与 Task 4 无关的文件”，会让外部 agent 在“创建前置依赖”和“遵守范围限制”之间冲突。

修订：已在 Task 4 中加入前置依赖说明，并将冷启动提示词改为“不要修改 Task 4 依赖链之外的文件”。

### 问题 4：Task 4 脱敏范围需要标注为最小切片

`SPEC.md` 要求日志和事件流覆盖疑似 key、token、Authorization header 脱敏。Task 4 只实现 provider-token 最小切片，原计划未说明其余覆盖会在后续任务补齐。

修订：已在 Task 4 前置说明中标注 provider-token 是当前任务的最小脱敏切片，HTTP header 和通用凭据脱敏将在后续凭据/API 任务中覆盖。

## 5. 处置决定

- 接受 opencode 对 `PLAN.md` 内部冲突和冷启动提示词歧义的反馈。
- 不接受 opencode 生成代码作为正式实现提交，因为它绕过了 Task 1 和 Task 2 的正式 TDD 顺序，且测试未全部通过。
- 清理 opencode 生成的未跟踪实现文件。
- 文档修订提交后，阶段 3 可视为完成，下一阶段从 Task 1 开始正式实现。
