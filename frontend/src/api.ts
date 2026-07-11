import type {
  ApprovalList,
  ApprovalDecisionResponse,
  AuthStatus,
  CredentialStatus,
  MemoryList,
  PolicyList,
  RunSummary,
} from "./types";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

async function jsonRequest<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, { credentials: "same-origin", ...init });
  if (!response.ok) {
    let detail = `Request failed: ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      detail = body.detail ?? detail;
    } catch {
      // Keep the stable status fallback for non-JSON proxy errors.
    }
    throw new ApiError(response.status, detail);
  }
  return (await response.json()) as T;
}

export function createDemoRun(name: "bugfix" | "dangerous-action"): Promise<RunSummary> {
  return jsonRequest<RunSummary>("/api/runs/demo", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
}

export function fetchPolicies(): Promise<PolicyList> {
  return jsonRequest<PolicyList>("/api/policies");
}

export function fetchCredentialStatus(): Promise<CredentialStatus> {
  return jsonRequest<CredentialStatus>("/api/credentials/status");
}

export function fetchApprovals(): Promise<ApprovalList> {
  return jsonRequest<ApprovalList>("/api/approvals?state=pending");
}

export function fetchMemory(scope = "project"): Promise<MemoryList> {
  return jsonRequest<MemoryList>(`/api/memory?scope=${encodeURIComponent(scope)}`);
}

export function searchMemory(scope: string, query: string, tags: string): Promise<MemoryList> {
  const params = new URLSearchParams({ scope, query, tags });
  return jsonRequest<MemoryList>(`/api/memory?${params.toString()}`);
}

export function fetchAuthStatus(): Promise<AuthStatus> {
  return jsonRequest<AuthStatus>("/api/auth/status");
}

export function login(password: string): Promise<AuthStatus> {
  return jsonRequest<AuthStatus>("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });
}

export function logout(): Promise<AuthStatus> {
  return jsonRequest<AuthStatus>("/api/auth/logout", { method: "POST" });
}

export function createRealRun(task: string): Promise<RunSummary> {
  return jsonRequest<RunSummary>("/api/runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode: "real", task }),
  });
}

export function fetchRun(runId: string): Promise<RunSummary> {
  return jsonRequest<RunSummary>(`/api/runs/${encodeURIComponent(runId)}`);
}

export function decideApproval(
  approvalId: string,
  decision: "approve" | "reject",
  reviewer: string,
  reason: string,
): Promise<ApprovalDecisionResponse> {
  return jsonRequest<ApprovalDecisionResponse>(
    `/api/approvals/${encodeURIComponent(approvalId)}/decision`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision, reviewer, reason }),
    },
  );
}

export function openRunEventSource(runId: string): EventSource {
  return new EventSource(`/api/runs/${runId}/events`);
}
