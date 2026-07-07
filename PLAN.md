# PLAN.md

Status: draft scaffold. This plan must be produced through the writing-plans workflow after `SPEC.md` is approved.

## Planning Rules

- No implementation code before `SPEC.md`, `PLAN.md`, and cold-start validation are completed.
- Each task must be small enough for one subagent session.
- Each task must include target files, expected changes, failing tests, and validation commands.
- Every core harness mechanism must be testable with a mock or stub LLM.
- `PLAN.md` must be updated after every completed task with the relevant commit hash.

## Phase 0: Project Initialization

- [x] Confirm project directory: `D:\Projects\CodingAgent`.
- [x] Initialize Git repository.
- [x] Confirm technology stack: Python, Typer, FastAPI, pytest.
- [x] Confirm distribution: Docker.
- [x] Confirm main contribution dimensions: governance guardrails, feedback loop, memory, and tool dispatch.
- [x] Create required document scaffolds.

## Phase 1: Brainstorming and SPEC

- [ ] Run brainstorming workflow.
- [ ] Finalize project problem statement.
- [ ] Finalize user stories.
- [ ] Finalize functional and non-functional requirements.
- [ ] Finalize domain and mechanism design.
- [ ] Finalize credential and distribution design.

## Phase 2: Implementation Plan

- [ ] Run writing-plans workflow.
- [ ] Split work into small TDD tasks.
- [ ] Mark task dependencies and parallel worktree candidates.

## Phase 3: Cold-Start Validation

- [ ] Use a different agent type.
- [ ] Provide only `SPEC.md` and `PLAN.md`.
- [ ] Ask it to attempt one or two tasks.
- [ ] Record misunderstandings and blockers in `SPEC_PROCESS.md`.
- [ ] Revise `SPEC.md` and `PLAN.md`.

## Phase 4: Implementation

TBD after phase 3.

## Phase 5: Distribution, CI, and Delivery

TBD after phase 3.

