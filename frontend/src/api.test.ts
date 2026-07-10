import { describe, expect, it, vi } from "vitest";
import { createDemoRun, fetchApprovals, fetchMemory, fetchPolicies } from "./api";

describe("api client", () => {
  it("creates a bugfix demo run", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ run_id: "run-1", status: "succeeded", feedback: [] }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const run = await createDemoRun("bugfix");

    expect(run.status).toBe("succeeded");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/runs/demo",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("fetches policy profiles", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ profiles: ["strict_demo"] }),
      }),
    );

    const policies = await fetchPolicies();

    expect(policies.profiles).toContain("strict_demo");
  });

  it("fetches persisted approvals and scoped memory", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ approvals: [{ id: "approval-1", state: "pending" }] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ records: [{ id: "mem-1", content: "Focused pytest first" }] }),
      });
    vi.stubGlobal("fetch", fetchMock);

    const approvals = await fetchApprovals();
    const memory = await fetchMemory("project");

    expect(approvals.approvals[0].state).toBe("pending");
    expect(memory.records[0].content).toBe("Focused pytest first");
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/api/memory?scope=project", undefined);
  });
});
