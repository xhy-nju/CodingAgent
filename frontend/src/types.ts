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
};

export type PolicyList = { profiles: string[] };

export type CredentialStatus = {
  provider: string;
  configured: boolean;
  source?: string;
  base_url?: string;
  model?: string;
  real_enabled: boolean;
};
