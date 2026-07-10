import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "./App";

vi.mock("./api", () => ({
  createDemoRun: vi
    .fn()
    .mockResolvedValue({ run_id: "run-1", status: "succeeded", feedback: [] }),
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
  openRunEventSource: vi.fn(() => ({ close: vi.fn(), addEventListener: vi.fn() })),
}));

afterEach(() => {
  cleanup();
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
});
