import type {
  ApprovalList,
  CredentialStatus,
  MemoryList,
  PolicyList,
  RunSummary,
} from "./types";

async function jsonRequest<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
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

export function openRunEventSource(runId: string): EventSource {
  return new EventSource(`/api/runs/${runId}/events`);
}
