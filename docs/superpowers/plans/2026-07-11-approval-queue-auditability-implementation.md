# Approval Queue Auditability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every pending approval independently reviewable before completing the real calculator demonstration.

**Architecture:** Preserve the existing approvals API and render its complete action metadata in `ApprovalView`. Replace the shared form strings with state keyed by approval ID.

**Tech Stack:** React, TypeScript, Vitest, Testing Library, Docker Compose, FastAPI

## Global Constraints

- Do not change approval transition semantics or delete historical requests.
- Render action arguments as escaped JSON text.
- Verify the real calculator task through the WebUI after rebuilding Docker.

---

### Task 1: Approval Card Context And Independent Forms

**Files:**
- Modify: `frontend/src/App.tsx`
- Test: `frontend/src/App.test.tsx`

**Interfaces:**
- Consumes: `ApprovalRecord` from `frontend/src/types.ts`
- Produces: one isolated reviewer/reason form and full action context per approval card

- [x] **Step 1: Write failing tests**

Add a two-approval fixture and assert that each card exposes its run ID, command arguments, model reason, expectation, and rules. Type different reviewer/reason values into each card and assert `decideApproval` receives only the selected card's values.

- [x] **Step 2: Verify the tests fail**

Run: `npm run test -- App.test.tsx`

Expected: FAIL because run/action details are absent and labels are not card-specific.

- [x] **Step 3: Implement the minimal UI change**

Store form values in `Record<string, { reviewer: string; reason: string }>` and render metadata from `approval.run_id`, `approval.action_id`, `approval.action`, and `approval.rules` inside each card.

- [x] **Step 4: Verify frontend and backend**

Run: `npm run test`, `npm run build`, and `pytest`.

Expected: all commands pass.

### Task 2: Runtime And Browser Verification

**Files:**
- Create: `docs/demo-video-script.md`

**Interfaces:**
- Consumes: Docker Compose service and real LLM configuration from `.env`
- Produces: verified calculator run evidence and a Chinese recording script

- [x] **Step 1: Rebuild and check service health**

Run: `docker compose up --build -d` and `docker compose ps`.

Expected: `coding-agent` is healthy on port 8000.

- [x] **Step 2: Complete the real calculator run**

In the WebUI, start the default task, inspect every requested action, approve only workspace-scoped read/write/test actions, and verify terminal status plus feedback and event evidence.

- [x] **Step 3: Write and review the recording script**

Document a 6-8 minute sequence covering project purpose, mock guardrail/feedback/memory, real LLM HITL flow, tests, GitHub CI, Docker/GHCR delivery, and secret-safe recording guidance.

### Task 3: Real Provider Observation Loop (Discovered During Browser Verification)

**Files:**
- Modify: `src/coding_agent/tools/commands.py`
- Modify: `src/coding_agent/guardrails.py`
- Modify: `src/coding_agent/feedback.py`
- Modify: `src/coding_agent/domain.py`
- Modify: `src/coding_agent/llm.py`
- Test: `tests/test_agent_loop.py`, `tests/test_command_tools.py`, `tests/test_credentials_llm.py`, `tests/test_feedback.py`, `tests/test_guardrails.py`

- [x] **Step 1: Reproduce string command execution and missing tool observations**

Observed that `"ls -la"` became character arguments and that successful `list_files`/`read_file` artifacts were absent from the next `LLMContext`.

- [x] **Step 2: Add failing deterministic tests**

Covered string/list normalization, dangerous string denial, successful tool observations, next-step context injection, and exact real-provider tool schemas.

- [x] **Step 3: Implement and verify the feedback loop**

Commit `0a7803e` added shell-free command normalization, guardrail checks for both input forms, `tool_observation`, and an accurate prompt schema. The final real run completed `list_files → read_file → write_file → run_tests` and reported `2 passed`.

## Completion Evidence

- Approval UI commits: `480bae4`, `897c50e`.
- Real observation-loop commit: `0a7803e`.
- Backend: `145 passed`.
- Frontend: `12 passed`; production build passed.
- Runtime: Docker service healthy; real run `run-ea1154bb1f8a` succeeded; browser console had no warnings or errors.
