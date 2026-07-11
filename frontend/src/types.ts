export type FeedbackSignal = {
  type: string;
  severity: "info" | "warning" | "error";
  summary: string;
  details: Record<string, unknown>;
};

export type RunSummary = {
  run_id: string;
  status: string;
  feedback: FeedbackSignal[];
  pending_approval_id?: string | null;
};

export const RUN_EVENT_TYPES = [
  "run.started",
  "llm.action",
  "guardrail.checked",
  "approval.requested",
  "approval.approved",
  "approval.rejected",
  "tool.result",
  "memory.written",
  "feedback.recorded",
  "run.finished",
] as const;

export type MemoryRecord = {
  id: string;
  scope: string;
  kind: "event" | "summary";
  tags: string[];
  content: string;
  source_run_id: string | null;
  confidence: number;
  sensitive: boolean;
};

export type ApprovalRecord = {
  id: string;
  run_id: string;
  action_id: string;
  state: string;
  rules: string[];
  reason: string;
  reviewer?: string | null;
  reviewer_reason?: string | null;
  action?: {
    kind: string;
    tool?: string | null;
    args: Record<string, unknown>;
    reason: string;
    expectation: string;
  };
};

export type MemoryList = { records: MemoryRecord[] };
export type ApprovalList = { approvals: ApprovalRecord[] };

export type PolicyList = { profiles: string[] };

export type CredentialStatus = {
  provider: string;
  configured: boolean;
  source?: string;
  base_url?: string;
  model?: string;
  real_enabled: boolean;
};

export type AuthStatus = {
  authenticated: boolean;
  expires_at: number | null;
};

export type ApprovalDecisionResponse = {
  approval_id: string;
  state: string;
  run: RunSummary;
};
