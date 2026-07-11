import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen } from "@testing-library/react";
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
});
