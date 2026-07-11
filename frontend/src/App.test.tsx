import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import {
  createRealRun,
  decideApproval,
  fetchApprovals,
  fetchAuthStatus,
} from "./api";

vi.mock("./api", () => ({
  createDemoRun: vi
    .fn()
    .mockResolvedValue({ run_id: "run-1", status: "succeeded", feedback: [] }),
  createRealRun: vi
    .fn()
    .mockResolvedValue({ run_id: "run-real-1", status: "running", feedback: [] }),
  fetchRun: vi
    .fn()
    .mockResolvedValue({ run_id: "run-real-1", status: "succeeded", feedback: [] }),
  fetchAuthStatus: vi.fn().mockResolvedValue({ authenticated: true, expires_at: 4102444800 }),
  login: vi.fn().mockResolvedValue({ authenticated: true, expires_at: 4102444800 }),
  logout: vi.fn().mockResolvedValue({ authenticated: false, expires_at: null }),
  fetchPolicies: vi.fn().mockResolvedValue({ profiles: ["strict_demo", "balanced_dev"] }),
  fetchCredentialStatus: vi.fn().mockResolvedValue({
    provider: "openai-compatible",
    configured: false,
    source: "missing",
    base_url: "https://njusehub.info/v1",
    model: "glm-5.2",
    real_enabled: false,
  }),
  fetchApprovals: vi.fn().mockResolvedValue({ approvals: [] }),
  fetchMemory: vi.fn().mockResolvedValue({
    records: [
      {
        id: "mem-1",
        scope: "project",
        kind: "summary",
        tags: ["pytest"],
        content: "Use the focused calculator test",
        source_run_id: "run-1",
        confidence: 1,
        sensitive: false,
      },
    ],
  }),
  searchMemory: vi.fn().mockResolvedValue({ records: [] }),
  decideApproval: vi.fn().mockResolvedValue({
    approval_id: "approval-1",
    state: "approved_once",
    run: { run_id: "run-approval", status: "succeeded", feedback: [] },
  }),
  openRunEventSource: vi.fn(() => ({ close: vi.fn(), addEventListener: vi.fn() })),
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("App", () => {
  it("renders dashboard and demo controls", async () => {
    render(<App />);

    expect(await screen.findByText("CodingAgent")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Run bugfix demo/i })).toBeInTheDocument();
    expect(screen.getByText("Policy check and hard guardrail blocking")).toBeInTheDocument();
  });

  it("starts a demo from the dashboard", async () => {
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: /Run bugfix demo/i }));

    expect(await screen.findByText(/run-1/)).toBeInTheDocument();
  });

  it("shows credential model details", async () => {
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: /Credentials/i }));

    expect(await screen.findByText("glm-5.2")).toBeInTheDocument();
    expect(screen.getByText("https://njusehub.info/v1")).toBeInTheDocument();
  });

  it("shows persisted memory records instead of feedback-derived placeholders", async () => {
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: /^Memory$/i }));

    expect(await screen.findByText("Use the focused calculator test")).toBeInTheDocument();
  });

  it("requires login before starting a real run", async () => {
    vi.mocked(fetchAuthStatus).mockResolvedValueOnce({ authenticated: false, expires_at: null });
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "Real" }));
    await userEvent.click(screen.getByRole("button", { name: /Start real run/i }));

    expect(
      screen.getByRole("dialog", { name: /Administrator login/i }),
    ).toBeInTheDocument();
  });

  it("starts a real run for an authenticated administrator", async () => {
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "Real" }));
    await userEvent.click(screen.getByRole("button", { name: /Start real run/i }));

    expect(createRealRun).toHaveBeenCalled();
    expect(await screen.findByText(/run-real-1/)).toBeInTheDocument();
  });

  it("submits an approval with explicit reviewer and reason", async () => {
    vi.mocked(fetchApprovals).mockResolvedValueOnce({
      approvals: [
        {
          id: "approval-1",
          run_id: "run-approval",
          action_id: "action-1",
          state: "pending",
          rules: ["tool.requires_approval"],
          reason: "Manual review required",
          action: {
            kind: "tool",
            tool: "run_command",
            args: { command: ["pytest"] },
            reason: "run tests",
            expectation: "test result",
          },
        },
      ],
    });
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: /Approvals/i }));
    await userEvent.type(await screen.findByLabelText("Reviewer"), "course-admin");
    await userEvent.type(screen.getByLabelText("Reason"), "Command and workspace reviewed");
    await userEvent.click(screen.getByRole("button", { name: "Approve once" }));

    expect(decideApproval).toHaveBeenCalledWith(
      "approval-1",
      "approve",
      "course-admin",
      "Command and workspace reviewed",
    );
  });

  it("shows auditable action context and keeps approval forms independent", async () => {
    vi.mocked(fetchApprovals)
      .mockResolvedValueOnce({
        approvals: [
        {
          id: "approval-old",
          run_id: "run-old",
          action_id: "action-old",
          state: "pending",
          rules: ["tool.requires_approval"],
          reason: "Manual review required",
          action: {
            kind: "tool",
            tool: "run_command",
            args: { command: "ls -la" },
            reason: "inspect the workspace",
            expectation: "workspace listing",
          },
        },
        {
          id: "approval-current",
          run_id: "run-current",
          action_id: "action-current",
          state: "pending",
          rules: ["tool.requires_approval", "command.reviewed"],
          reason: "Manual review required",
          action: {
            kind: "tool",
            tool: "run_command",
            args: { command: ["python", "-m", "pytest"] },
            reason: "verify the calculator fix",
            expectation: "all tests pass",
          },
        },
        ],
      })
      .mockResolvedValueOnce({
        approvals: [
          {
            id: "approval-next",
            run_id: "run-current",
            action_id: "action-next",
            state: "pending",
            rules: ["tool.requires_approval"],
            reason: "Next manual review",
            action: {
              kind: "tool",
              tool: "run_command",
              args: { command: "cat calculator.py" },
              reason: "inspect calculator implementation",
              expectation: "calculator source",
            },
          },
        ],
      });
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: /Approvals/i }));

    const currentRun = await screen.findByText("run-current");
    const currentCard = currentRun.closest("article");
    expect(currentCard).not.toBeNull();
    const oldRun = screen.getByText("run-old");
    const oldCard = oldRun.closest("article");
    expect(oldCard).not.toBeNull();

    expect(within(currentCard!).getByText("action-current")).toBeInTheDocument();
    expect(within(currentCard!).getByText(/python/)).toBeInTheDocument();
    expect(within(currentCard!).getByText("verify the calculator fix")).toBeInTheDocument();
    expect(within(currentCard!).getByText("all tests pass")).toBeInTheDocument();
    expect(within(currentCard!).getByText("command.reviewed")).toBeInTheDocument();

    await userEvent.type(within(oldCard!).getByLabelText("Reviewer"), "old-reviewer");
    await userEvent.type(within(oldCard!).getByLabelText("Reason"), "Review old request later");
    await userEvent.type(within(currentCard!).getByLabelText("Reviewer"), "course-admin");
    await userEvent.type(
      within(currentCard!).getByLabelText("Reason"),
      "Safe test command in isolated workspace",
    );
    await userEvent.click(within(currentCard!).getByRole("button", { name: "Approve once" }));

    expect(decideApproval).toHaveBeenCalledWith(
      "approval-current",
      "approve",
      "course-admin",
      "Safe test command in isolated workspace",
    );
    expect(await screen.findByText("action-next")).toBeInTheDocument();
  });

  it("keeps a successful decision when the queue refresh fails", async () => {
    vi.mocked(fetchApprovals)
      .mockResolvedValueOnce({
        approvals: [
          {
            id: "approval-refresh",
            run_id: "run-refresh",
            action_id: "action-refresh",
            state: "pending",
            rules: ["tool.requires_approval"],
            reason: "Manual review required",
            action: {
              kind: "tool",
              tool: "run_command",
              args: { command: ["pytest"] },
              reason: "run tests",
              expectation: "test result",
            },
          },
        ],
      })
      .mockRejectedValueOnce(new Error("refresh offline"));
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: /Approvals/i }));
    const card = (await screen.findByText("action-refresh")).closest("article");
    expect(card).not.toBeNull();
    await userEvent.type(within(card!).getByLabelText("Reviewer"), "course-admin");
    await userEvent.type(within(card!).getByLabelText("Reason"), "Reviewed safe test command");
    await userEvent.click(within(card!).getByRole("button", { name: "Approve once" }));

    expect(await screen.findByText("Approval saved, but queue refresh failed")).toBeInTheDocument();
    expect(screen.queryByText("action-refresh")).not.toBeInTheDocument();
  });
});
