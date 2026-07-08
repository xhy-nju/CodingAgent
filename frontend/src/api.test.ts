import { describe, expect, it, vi } from "vitest";
import { createDemoRun, fetchPolicies } from "./api";

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
});
