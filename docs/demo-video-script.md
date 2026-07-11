# CodingAgent 期末项目演示视频录制脚本

## 录制目标

- 建议时长：7 分钟，允许在 6-8 分钟内调整。
- 建议规格：1920×1080、30 FPS、浏览器缩放 90%、开启麦克风降噪。
- 核心顺序：项目定位 → mock 确定性机制演示 → 治理与记忆 → 真实 LLM → 测试、CI 与分发。
- 录制前先登录 WebUI，视频中不要展示管理员密码、`.env`、API Key、Cookie 或终端历史。

## 录制前准备

1. 在项目根目录执行：

   ```powershell
   docker compose up -d
   docker compose ps
   ```

   确认 `coding-agent` 为 `healthy`，端口为 `8000:8000`。

2. 打开以下页面并按顺序放置标签页：
   - WebUI：最终提交时优先使用阿里云公网地址；本地备选为 `http://127.0.0.1:8000`。
   - GitHub 仓库首页和 Pull Requests 页面。
   - GitHub Actions 最后一次绿色运行记录。
   - GHCR 镜像页面或仓库 README 的 Docker 获取命令。

3. 在 WebUI 中提前完成管理员登录，并确认右上角显示 `real LLM`。不要在录制中输入密码。

4. 真实模型输出具有少量不确定性。正式录制前先试跑一次默认 calculator 任务；录制时若等待超过 20 秒，可以剪掉中间等待，但不要剪掉动作、反馈和最终状态。

## 分镜与旁白

### 0:00-0:35 项目定位

**画面：** GitHub 仓库首页，缓慢展示 README 标题、功能摘要和目录结构。

**旁白：**

> 这是我的 AI4SE 期末项目 CodingAgent。它不是对现成 agent 框架的简单配置，而是我自己实现的一套 coding agent harness。项目将单次 LLM 决策封装成可运行的工程系统，包含 agent 主循环、动作解析、工具分发、治理护栏、人工审批、客观反馈、持久化记忆、WebUI 和 Docker 分发。我的重点贡献是治理护栏、反馈闭环、记忆和工具分发。

### 0:35-1:10 架构与可替换 LLM

**画面：** README 架构图或 `src/coding_agent` 目录，依次指向 `agent_loop.py`、`tools`、`guardrails.py`、`feedback.py`、`memory.py` 和 `llm.py`。

**旁白：**

> 主循环由项目代码完成：组织上下文、调用可替换的 LLM Provider、解析结构化动作、执行护栏检查、分发工具、回灌结果并判断停机。Mock Provider 用于离线、确定性测试；OpenAI-compatible Provider 用于真实模型。即使移除真实 LLM，工具、护栏、反馈、审批、记忆和停机机制仍可由单元测试独立验证。

### 1:10-2:00 Mock 治理护栏演示

**画面操作：**

1. 回到 WebUI Dashboard。
2. 保持 `Mock` 模式。
3. 点击 `Run guardrail demo`。
4. 在 Run Detail 中停留，展示 `guardrail.checked`、`guardrail_blocked` 和最终 `failed`。

**旁白：**

> 首先演示课程要求的危险动作拦截。Mock LLM 会稳定地产生越界危险动作，策略引擎在执行前检查工具、路径和命令规则。这里的 failed 是预期结果，表示危险动作没有执行；反馈中可以看到 guardrail blocked 及具体命中规则。这一行为由确定性代码和离线测试保证，不依赖模型是否遵守提示词。

### 2:00-3:00 Mock 反馈闭环与工具分发

**画面操作：**

1. 返回 Dashboard。
2. 点击 `Run bugfix demo`。
3. 在 Run Detail 中依次指出首次测试失败、文件修改、再次测试和 `test_passed`。
4. 展示最终 `succeeded`。

**旁白：**

> 第二个一键演示验证客观反馈闭环。系统先运行 pytest，解析失败数量和退出码，将 test failed 回灌给下一轮决策。Agent 随后修改 calculator，再次运行测试，只有收到确定性的 test passed 信号才标记成功。这里同时经过动作解析、工具注册表、文件沙箱、反馈分类和停机判断，证明模型输出并不会直接绕过 harness。

### 3:00-3:40 记忆与 HITL 治理

**画面操作：**

1. 打开 `Memory`，展示持久化记录、scope、tags 和来源 run。
2. 打开 `Policies`，展示 `strict_demo` 与 `balanced_dev`。
3. 打开 `Approvals`，只展示一张审批卡片的 run ID、动作参数、模型理由、预期结果和规则，不展示或批准无关历史请求。

**旁白：**

> 记忆不是把全部历史原样塞给模型，而是按 scope、标签和查询进行确定性检索，并记录来源与敏感标记。治理方面，策略文件声明允许工具、路径边界、命令白名单和需要人工审批的工具。审批卡片给出完整动作上下文，审核人必须填写身份和理由；后端使用状态机保证一次性执行，重复审批会被拒绝并留下事件记录。

### 3:40-5:15 真实 LLM Calculator 任务

**画面操作：**

1. 返回 Dashboard，选择 `Real`。
2. 保留默认任务 `Repair the calculator and verify the tests pass.`。
3. 点击 `Start real run`。
4. 在 Run Detail 中按出现顺序指出：
   - `list_files` 发现 `calculator.py` 和测试文件；
   - `read_file` 读到错误实现 `return a - b`；
   - `write_file` 产生 `file_diff`；
   - `run_tests` 产生 `pytest passed: 2 passed`；
   - 最终状态为 `succeeded`。

**旁白：**

> 现在切换到真实模型。API Key 只从安全配置源注入，页面只显示配置状态，不回显凭据。模型首先列出文件，再读取 calculator，实现中可以看到减法错误。工具结果以结构化 observation 回灌给下一轮模型，模型据此写入加法实现并运行 pytest。最终两项测试通过，运行状态变为 succeeded。真实模型用于证明可用性，而课程要求的机制正确性仍由前面的 mock 演示和单元测试保证。

### 5:15-5:45 凭据安全

**画面操作：** 打开 `Credentials`，展示 Provider、Base URL、Model、`configured` 和 `real enabled` 状态。不要打开 `.env`。

**旁白：**

> 凭据层支持环境变量和系统凭据存储，状态接口只返回是否配置、来源、模型和 Base URL，不返回明文 Key。仓库中的 `.env.example` 只有占位符，真实 `.env` 被 Git 忽略，日志和事件还会经过脱敏处理。

### 5:45-6:35 测试、CI 与 PR 工作流

**画面操作：**

1. 切换到终端，展示预先运行完成的 `pytest` 结果和前端测试结果，不必现场等待：后端应显示 `145 passed`，前端应显示 `11 passed`。
2. 切换 GitHub Actions，展示最后一次绿色运行。
3. 切换 Pull Requests，展示分支、评审和合并历史。

**旁白：**

> 项目采用 TDD，后端当前 145 项测试通过，前端 11 项测试通过，并完成生产构建。测试覆盖 action parser、agent loop、工具、guardrail、HITL 状态机、反馈、记忆、凭据和 API。GitHub Actions 在 push 和 PR 上自动运行测试并构建镜像；提交历史保留了 spec、plan、独立任务和人工修复记录。

### 6:35-7:05 Docker 分发与交付收尾

**画面操作：** 展示 README 中的 `docker compose up --build -d`、GHCR 镜像 `ghcr.io/xhy-nju/coding-agent:1.0.0`、公网 WebUI 地址，以及 `SPEC.md`、`PLAN.md`、`SPEC_PROCESS.md`、`AGENT_LOG.md`、`REFLECTION.md`。

**旁白：**

> 项目通过 Docker 和公开 GHCR 镜像分发，新机器只需要 Docker、Compose 和自己的安全配置即可运行。最终仓库包含 SPEC、PLAN、过程记录、Agent 日志、反思、完整源码、测试、CI 和部署说明。公网 WebUI 部署在阿里云主机上。以上完成了从 spec-driven 设计、subagent 与 TDD 开发，到治理、反馈、验证和分发的完整工程闭环。

## 可选的 HITL 单测补充画面

若审批队列没有合适的待审请求，可在终端运行下面的确定性测试，录制其通过结果：

```powershell
pytest tests/test_agent_loop.py::test_approved_action_executes_exactly_once_then_run_resumes -q
pytest tests/test_agent_loop.py::test_rejected_action_never_executes_and_rejection_is_feedback -q
```

旁白说明：第一项验证批准动作只执行一次且运行恢复；第二项验证拒绝动作从不执行，并将拒绝原因反馈给后续循环。

## 录制后检查清单

- [ ] 视频中没有 API Key、管理员密码、`.env` 内容、Cookie 或个人隐私信息。
- [ ] Mock guardrail 演示明确说明 `failed` 是预期拦截结果。
- [ ] Mock bugfix 演示清楚出现 `test_failed → file_diff → test_passed`。
- [ ] 真实任务清楚出现文件观察、修改、测试通过和 `succeeded`。
- [ ] 明确说明核心机制由自研代码完成，真实 LLM 只是可替换决策层。
- [ ] 展示测试数量、绿色 CI、PR 历史、Docker/GHCR 和公网 WebUI。
- [ ] 展示课程要求的主要文档，但不要快速滚动大段文字。
- [ ] 声音清晰，无超过 3 秒的无意义停顿；模型等待时间已适度剪辑。
- [ ] 导出 MP4，建议 H.264、1080p，文件名使用 `学号_姓名_CodingAgent_Demo.mp4`。
