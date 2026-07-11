import {
  Activity,
  Bot,
  CheckCircle2,
  ClipboardList,
  Database,
  Gauge,
  KeyRound,
  LogIn,
  LogOut,
  LucideIcon,
  MemoryStick,
  Play,
  Settings,
  Shield,
  Search,
  TerminalSquare,
  XCircle,
} from "lucide-react";
import { type FormEvent, useEffect, useState } from "react";
import {
  createDemoRun,
  createRealRun,
  decideApproval,
  fetchApprovals,
  fetchAuthStatus,
  fetchCredentialStatus,
  fetchMemory,
  fetchPolicies,
  fetchRun,
  login,
  logout,
  openRunEventSource,
  searchMemory,
} from "./api";
import {
  RUN_EVENT_TYPES,
  type ApprovalRecord,
  type AuthStatus,
  type CredentialStatus,
  type FeedbackSignal,
  type MemoryRecord,
  type PolicyList,
  type RunSummary,
} from "./types";

type Tab =
  | "dashboard"
  | "run"
  | "approvals"
  | "memory"
  | "policies"
  | "credentials"
  | "settings";

type DemoName = "bugfix" | "dangerous-action";
type RunMode = "mock" | "real";

type RunEvent = {
  type: string;
  payload: string;
};

type TabSpec = {
  id: Tab;
  label: string;
  Icon: LucideIcon;
};

const tabs: TabSpec[] = [
  { id: "dashboard", label: "Dashboard", Icon: Gauge },
  { id: "run", label: "Run Detail", Icon: Activity },
  { id: "approvals", label: "Approvals", Icon: ClipboardList },
  { id: "memory", label: "Memory", Icon: MemoryStick },
  { id: "policies", label: "Policies", Icon: Shield },
  { id: "credentials", label: "Credentials", Icon: KeyRound },
  { id: "settings", label: "Settings", Icon: Settings },
];

const demoOptions: Array<{
  name: DemoName;
  title: string;
  subtitle: string;
  Icon: LucideIcon;
}> = [
  {
    name: "bugfix",
    title: "Run bugfix demo",
    subtitle: "Agent loop, tests, memory, feedback",
    Icon: Play,
  },
  {
    name: "dangerous-action",
    title: "Run guardrail demo",
    subtitle: "Policy check and hard guardrail blocking",
    Icon: Shield,
  },
];

function parsePayload(data: string | undefined): string {
  if (!data) {
    return "event received";
  }

  try {
    const parsed = JSON.parse(data) as unknown;
    if (typeof parsed === "string") {
      return parsed;
    }
    return JSON.stringify(parsed);
  } catch {
    return data;
  }
}

function statusClass(status: string | undefined): string {
  if (!status) {
    return "status neutral";
  }
  if (status === "succeeded" || status === "approved") {
    return "status success";
  }
  if (status === "failed" || status === "blocked") {
    return "status danger";
  }
  return "status warning";
}

function StatusIcon({ status }: { status: string | undefined }) {
  if (status === "succeeded" || status === "approved") {
    return <CheckCircle2 aria-hidden="true" />;
  }
  if (status === "failed" || status === "blocked") {
    return <XCircle aria-hidden="true" />;
  }
  return <Activity aria-hidden="true" />;
}

function FeedbackList({ feedback }: { feedback: FeedbackSignal[] }) {
  if (feedback.length === 0) {
    return <p className="empty-state">No feedback signals recorded.</p>;
  }

  return (
    <div className="feedback-list">
      {feedback.map((signal, index) => (
        <article className={`feedback-item ${signal.severity}`} key={`${signal.type}-${index}`}>
          <div>
            <span className="eyebrow">{signal.type}</span>
            <h3>{signal.summary}</h3>
          </div>
          <span className="detail-count">{Object.keys(signal.details).length} details</span>
        </article>
      ))}
    </div>
  );
}

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>("dashboard");
  const [policies, setPolicies] = useState<PolicyList | null>(null);
  const [credentials, setCredentials] = useState<CredentialStatus | null>(null);
  const [run, setRun] = useState<RunSummary | null>(null);
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [approvals, setApprovals] = useState<ApprovalRecord[]>([]);
  const [memories, setMemories] = useState<MemoryRecord[]>([]);
  const [auth, setAuth] = useState<AuthStatus>({ authenticated: false, expires_at: null });
  const [runMode, setRunMode] = useState<RunMode>("mock");
  const [realTask, setRealTask] = useState("Repair the calculator and verify the tests pass.");
  const [loginOpen, setLoginOpen] = useState(false);
  const [password, setPassword] = useState("");
  const [loginBusy, setLoginBusy] = useState(false);
  const [approvalBusy, setApprovalBusy] = useState<string | null>(null);
  const [memoryQuery, setMemoryQuery] = useState("");
  const [memoryTags, setMemoryTags] = useState("");
  const [busyDemo, setBusyDemo] = useState<DemoName | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    Promise.all([fetchPolicies(), fetchCredentialStatus(), fetchAuthStatus()])
      .then(async ([policyList, credentialStatus, authStatus]) => {
        if (!isMounted) {
          return;
        }
        setPolicies(policyList);
        setCredentials(credentialStatus);
        setAuth(authStatus);
        if (authStatus.authenticated) {
          const memoryList = await fetchMemory();
          if (isMounted) {
            setMemories(memoryList.records);
          }
        }
      })
      .catch((reason: unknown) => {
        if (isMounted) {
          setError(reason instanceof Error ? reason.message : "Unable to load dashboard data");
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    if (!run?.run_id || run.status !== "running") {
      return undefined;
    }
    const timer = window.setInterval(() => {
      fetchRun(run.run_id)
        .then(setRun)
        .catch(() => undefined);
    }, 1000);
    return () => window.clearInterval(timer);
  }, [run?.run_id, run?.status]);

  useEffect(() => {
    if (!run?.run_id) {
      return undefined;
    }

    const source = openRunEventSource(run.run_id);
    const handleEvent = (event: Event) => {
      const message = event as MessageEvent<string>;
      setEvents((current) =>
        [
          {
            type: message.type,
            payload: parsePayload(message.data),
          },
          ...current,
        ].slice(0, 8),
      );
    };

    RUN_EVENT_TYPES.forEach((eventType) => source.addEventListener(eventType, handleEvent));

    return () => {
      source.close();
    };
  }, [run?.run_id]);

  const startDemo = async (name: DemoName) => {
    setBusyDemo(name);
    setError(null);
    setEvents([]);

    try {
      const nextRun = await createDemoRun(name);
      setRun(nextRun);
      setActiveTab("run");
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to start demo run");
    } finally {
      setBusyDemo(null);
    }
  };

  const startReal = async () => {
    if (!auth.authenticated) {
      setLoginOpen(true);
      return;
    }
    setBusyDemo("bugfix");
    setError(null);
    setEvents([]);
    try {
      const nextRun = await createRealRun(realTask.trim());
      setRun(nextRun);
      setActiveTab("run");
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to start real run");
    } finally {
      setBusyDemo(null);
    }
  };

  const submitLogin = async (event: FormEvent) => {
    event.preventDefault();
    setLoginBusy(true);
    setError(null);
    try {
      const nextAuth = await login(password);
      setAuth(nextAuth);
      setPassword("");
      setLoginOpen(false);
      const memoryList = await fetchMemory();
      setMemories(memoryList.records);
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Login failed");
    } finally {
      setLoginBusy(false);
    }
  };

  const signOut = async () => {
    const nextAuth = await logout();
    setAuth(nextAuth);
    setApprovals([]);
    setMemories([]);
    setRunMode("mock");
  };

  const submitApproval = async (
    approvalId: string,
    decision: "approve" | "reject",
    reviewer: string,
    reviewReason: string,
  ) => {
    setApprovalBusy(approvalId);
    setError(null);
    try {
      const result = await decideApproval(
        approvalId,
        decision,
        reviewer.trim(),
        reviewReason.trim(),
      );
      setRun(result.run);
      const approvalList = await fetchApprovals();
      setApprovals(approvalList.approvals);
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Approval failed");
    } finally {
      setApprovalBusy(null);
    }
  };

  const submitMemorySearch = async () => {
    try {
      const result = await searchMemory("project", memoryQuery.trim(), memoryTags.trim());
      setMemories(result.records);
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Memory search failed");
    }
  };

  const selectTab = async (nextTab: Tab) => {
    setActiveTab(nextTab);
    if (nextTab !== "approvals" || !auth.authenticated) {
      return;
    }
    try {
      const approvalList = await fetchApprovals();
      setApprovals(approvalList.approvals);
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to refresh approvals");
    }
  };

  const policyProfiles = policies?.profiles ?? [];
  const primaryPolicy = policyProfiles[0] ?? "loading";
  const credentialMode = credentials?.real_enabled
    ? "real LLM"
    : credentials?.configured
      ? "configured mock"
      : "mock LLM";

  return (
    <>
    <main className="app-shell">
      <aside className="sidebar" aria-label="Primary">
        <div className="brand-block">
          <div className="brand-mark">CA</div>
          <div>
            <h1>CodingAgent</h1>
            <p>Agent harness</p>
          </div>
        </div>

        <nav className="nav-list">
          {tabs.map(({ id, label, Icon }) => (
            <button
              className={activeTab === id ? "nav-button active" : "nav-button"}
              key={id}
              onClick={() => void selectTab(id)}
              type="button"
            >
              <Icon aria-hidden="true" />
              <span>{label}</span>
            </button>
          ))}
        </nav>
      </aside>

      <div className="content-shell">
        <header className="topbar">
          <div>
            <span className="eyebrow">Operational Console</span>
            <h2>{tabs.find((tab) => tab.id === activeTab)?.label}</h2>
          </div>
          <div className="topbar-status">
            <span className="status neutral">
              <Shield aria-hidden="true" />
              {primaryPolicy}
            </span>
            <span className={credentials?.real_enabled ? "status success" : "status warning"}>
              <KeyRound aria-hidden="true" />
              {credentialMode}
            </span>
            <button
              className="icon-text-button"
              onClick={auth.authenticated ? signOut : () => setLoginOpen(true)}
              type="button"
            >
              {auth.authenticated ? <LogOut aria-hidden="true" /> : <LogIn aria-hidden="true" />}
              {auth.authenticated ? "Log out" : "Admin login"}
            </button>
          </div>
        </header>

        {error ? (
          <section className="alert-panel" role="alert">
            {error}
          </section>
        ) : null}

        <section className="tab-body">
          {activeTab === "dashboard" ? (
            <DashboardView
              busyDemo={busyDemo}
              credentialMode={credentialMode}
              onStartDemo={startDemo}
              onStartReal={startReal}
              policyCount={policyProfiles.length}
              realTask={realTask}
              run={run}
              runMode={runMode}
              setRealTask={setRealTask}
              setRunMode={setRunMode}
            />
          ) : null}
          {activeTab === "run" ? <RunDetailView events={events} run={run} /> : null}
          {activeTab === "approvals" ? (
            <ApprovalView
              approvalBusy={approvalBusy}
              approvals={approvals}
              onDecision={submitApproval}
            />
          ) : null}
          {activeTab === "memory" ? (
            <MemoryView
              memories={memories}
              onSearch={submitMemorySearch}
              query={memoryQuery}
              setQuery={setMemoryQuery}
              setTags={setMemoryTags}
              tags={memoryTags}
            />
          ) : null}
          {activeTab === "policies" ? <PoliciesView policies={policyProfiles} /> : null}
          {activeTab === "credentials" ? <CredentialsView credentials={credentials} /> : null}
          {activeTab === "settings" ? (
            <SettingsView credentialMode={credentialMode} primaryPolicy={primaryPolicy} />
          ) : null}
        </section>
      </div>
    </main>
    {loginOpen ? (
      <div className="dialog-backdrop" role="presentation">
        <section aria-labelledby="login-title" aria-modal="true" className="dialog" role="dialog">
          <div className="panel-heading">
            <div><span className="eyebrow">Protected operations</span><h3 id="login-title">Administrator login</h3></div>
            <KeyRound aria-hidden="true" className="panel-icon" />
          </div>
          <form className="form-stack" onSubmit={submitLogin}>
            <label htmlFor="admin-password">Password</label>
            <input
              autoFocus
              id="admin-password"
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
            <div className="button-row">
              <button className="secondary-button" onClick={() => setLoginOpen(false)} type="button">Cancel</button>
              <button className="primary-button" disabled={loginBusy} type="submit"><LogIn aria-hidden="true" />{loginBusy ? "Signing in..." : "Sign in"}</button>
            </div>
          </form>
        </section>
      </div>
    ) : null}
    </>
  );
}

function DashboardView({
  busyDemo,
  credentialMode,
  onStartDemo,
  onStartReal,
  policyCount,
  realTask,
  run,
  runMode,
  setRealTask,
  setRunMode,
}: {
  busyDemo: DemoName | null;
  credentialMode: string;
  onStartDemo: (name: DemoName) => void;
  onStartReal: () => void;
  policyCount: number;
  realTask: string;
  run: RunSummary | null;
  runMode: RunMode;
  setRealTask: (task: string) => void;
  setRunMode: (mode: RunMode) => void;
}) {
  return (
    <div className="dashboard-layout">
      <section className="metric-grid" aria-label="Overview">
        <div className="metric-card">
          <span className="metric-label">Current run</span>
          <strong>{run?.run_id ?? "No run"}</strong>
          <span className={statusClass(run?.status)}>
            <StatusIcon status={run?.status} />
            {run?.status ?? "idle"}
          </span>
        </div>
        <div className="metric-card">
          <span className="metric-label">Policies</span>
          <strong>{policyCount}</strong>
          <span className="status neutral">
            <Shield aria-hidden="true" />
            loaded
          </span>
        </div>
        <div className="metric-card">
          <span className="metric-label">LLM mode</span>
          <strong>{credentialMode}</strong>
          <span className="status warning">
            <KeyRound aria-hidden="true" />
            runtime
          </span>
        </div>
        <div className="metric-card">
          <span className="metric-label">Feedback</span>
          <strong>{run?.feedback.length ?? 0}</strong>
          <span className="status neutral">
            <Database aria-hidden="true" />
            signals
          </span>
        </div>
      </section>

      <section className="workbench-grid">
        <div className="panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">Demo Center</span>
              <h3>{runMode === "mock" ? "One-click runs" : "Real model run"}</h3>
            </div>
            <div className="segmented-control" aria-label="Run mode">
              <button
                aria-pressed={runMode === "mock"}
                className={runMode === "mock" ? "active" : ""}
                onClick={() => setRunMode("mock")}
                type="button"
              >
                Mock
              </button>
              <button
                aria-pressed={runMode === "real"}
                className={runMode === "real" ? "active" : ""}
                onClick={() => setRunMode("real")}
                type="button"
              >
                Real
              </button>
            </div>
          </div>
          {runMode === "mock" ? <div className="demo-actions">
            {demoOptions.map(({ name, title, subtitle, Icon }) => (
              <button
                className="demo-button"
                disabled={busyDemo !== null}
                key={name}
                onClick={() => onStartDemo(name)}
                type="button"
              >
                <Icon aria-hidden="true" />
                <span>
                  <strong>{busyDemo === name ? "Running..." : title}</strong>
                  <small>{subtitle}</small>
                </span>
              </button>
            ))}
          </div> : (
            <div className="form-stack">
              <label htmlFor="real-task">Task</label>
              <textarea
                id="real-task"
                maxLength={4000}
                onChange={(event) => setRealTask(event.target.value)}
                rows={5}
                value={realTask}
              />
              <button
                className="primary-button"
                disabled={busyDemo !== null || !realTask.trim()}
                onClick={onStartReal}
                type="button"
              >
                <Bot aria-hidden="true" />
                {busyDemo ? "Starting..." : "Start real run"}
              </button>
            </div>
          )}
        </div>

        <div className="panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">Run Snapshot</span>
              <h3>{run?.run_id ?? "No active run"}</h3>
            </div>
            <span className={statusClass(run?.status)}>
              <StatusIcon status={run?.status} />
              {run?.status ?? "idle"}
            </span>
          </div>
          <FeedbackList feedback={run?.feedback ?? []} />
        </div>
      </section>
    </div>
  );
}

function RunDetailView({ events, run }: { events: RunEvent[]; run: RunSummary | null }) {
  return (
    <div className="detail-grid">
      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">Run</span>
            <h3>{run?.run_id ?? "No run selected"}</h3>
          </div>
          <span className={statusClass(run?.status)}>
            <StatusIcon status={run?.status} />
            {run?.status ?? "idle"}
          </span>
        </div>
        <FeedbackList feedback={run?.feedback ?? []} />
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">SSE</span>
            <h3>Event stream</h3>
          </div>
          <TerminalSquare aria-hidden="true" className="panel-icon" />
        </div>
        {events.length === 0 ? (
          <p className="empty-state">Waiting for run events.</p>
        ) : (
          <ol className="event-list">
            {events.map((event, index) => (
              <li key={`${event.type}-${index}`}>
                <span>{event.type}</span>
                <code>{event.payload}</code>
              </li>
            ))}
          </ol>
        )}
      </section>
    </div>
  );
}

function ApprovalView({
  approvalBusy,
  approvals,
  onDecision,
}: {
  approvalBusy: string | null;
  approvals: ApprovalRecord[];
  onDecision: (
    id: string,
    decision: "approve" | "reject",
    reviewer: string,
    reason: string,
  ) => void;
}) {
  const [drafts, setDrafts] = useState<
    Record<string, { reviewer: string; reason: string }>
  >({});

  const updateDraft = (
    approvalId: string,
    field: "reviewer" | "reason",
    value: string,
  ) => {
    setDrafts((current) => ({
      ...current,
      [approvalId]: {
        reviewer: current[approvalId]?.reviewer ?? "",
        reason: current[approvalId]?.reason ?? "",
        [field]: value,
      },
    }));
  };

  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">Approval Queue</span>
          <h3>{approvals.length} pending</h3>
        </div>
        <ClipboardList aria-hidden="true" className="panel-icon" />
      </div>
      {approvals.length === 0 ? (
        <p className="empty-state">No pending approvals.</p>
      ) : (
        <div className="feedback-list">
          {approvals.map((approval) => {
            const draft = drafts[approval.id] ?? { reviewer: "", reason: "" };
            return (
              <article className="approval-item" key={approval.id}>
                <div>
                  <span className="eyebrow">{approval.state}</span>
                  <h3>{approval.reason}</h3>
                  <code>{approval.action?.tool ?? "tool action"}</code>
                </div>
                <span className="detail-count">{approval.rules.length} rules</span>

                <dl className="approval-context">
                  <div>
                    <dt>Run</dt>
                    <dd><code>{approval.run_id}</code></dd>
                  </div>
                  <div>
                    <dt>Action</dt>
                    <dd><code>{approval.action_id}</code></dd>
                  </div>
                  <div className="approval-context-wide">
                    <dt>Proposed arguments</dt>
                    <dd><pre>{JSON.stringify(approval.action?.args ?? {}, null, 2)}</pre></dd>
                  </div>
                  <div>
                    <dt>Model reason</dt>
                    <dd>{approval.action?.reason ?? "Not provided"}</dd>
                  </div>
                  <div>
                    <dt>Expected result</dt>
                    <dd>{approval.action?.expectation ?? "Not provided"}</dd>
                  </div>
                  <div className="approval-context-wide">
                    <dt>Triggered rules</dt>
                    <dd className="approval-rules">
                      {approval.rules.map((rule) => <code key={rule}>{rule}</code>)}
                    </dd>
                  </div>
                </dl>

                <div className="approval-form">
                  <label htmlFor={`reviewer-${approval.id}`}>Reviewer</label>
                  <input
                    id={`reviewer-${approval.id}`}
                    onChange={(event) => updateDraft(approval.id, "reviewer", event.target.value)}
                    value={draft.reviewer}
                  />
                  <label htmlFor={`reason-${approval.id}`}>Reason</label>
                  <textarea
                    id={`reason-${approval.id}`}
                    onChange={(event) => updateDraft(approval.id, "reason", event.target.value)}
                    rows={3}
                    value={draft.reason}
                  />
                  <div className="button-row">
                    <button
                      className="secondary-button danger-button"
                      disabled={approvalBusy !== null || !draft.reviewer.trim() || !draft.reason.trim()}
                      onClick={() => onDecision(
                        approval.id,
                        "reject",
                        draft.reviewer,
                        draft.reason,
                      )}
                      type="button"
                    >
                      <XCircle aria-hidden="true" /> Reject
                    </button>
                    <button
                      className="primary-button"
                      disabled={approvalBusy !== null || !draft.reviewer.trim() || !draft.reason.trim()}
                      onClick={() => onDecision(
                        approval.id,
                        "approve",
                        draft.reviewer,
                        draft.reason,
                      )}
                      type="button"
                    >
                      <CheckCircle2 aria-hidden="true" />
                      {approvalBusy === approval.id ? "Submitting..." : "Approve once"}
                    </button>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}

function MemoryView({
  memories,
  onSearch,
  query,
  setQuery,
  setTags,
  tags,
}: {
  memories: MemoryRecord[];
  onSearch: () => void;
  query: string;
  setQuery: (query: string) => void;
  setTags: (tags: string) => void;
  tags: string;
}) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">Memory</span>
          <h3>Workspace memory</h3>
        </div>
        <MemoryStick aria-hidden="true" className="panel-icon" />
      </div>
      <div className="search-row">
        <input
          aria-label="Memory query"
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search memory"
          value={query}
        />
        <input
          aria-label="Memory tags"
          onChange={(event) => setTags(event.target.value)}
          placeholder="pytest, policy"
          value={tags}
        />
        <button className="secondary-button" onClick={onSearch} type="button">
          <Search aria-hidden="true" /> Search
        </button>
      </div>
      {memories.length === 0 ? (
        <div className="memory-grid">
          <div>
            <span className="metric-label">Run lessons</span>
            <strong>0</strong>
          </div>
          <div>
            <span className="metric-label">Policy hints</span>
            <strong>0</strong>
          </div>
          <div>
            <span className="metric-label">Tool notes</span>
            <strong>0</strong>
          </div>
        </div>
      ) : (
        <div className="feedback-list">
          {memories.map((memory) => (
            <article className="feedback-item info" key={memory.id}>
              <div>
                <span className="eyebrow">{memory.tags.join(", ") || memory.kind}</span>
                <h3>{memory.content}</h3>
              </div>
              <span className="detail-count">{memory.scope}</span>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function PoliciesView({ policies }: { policies: string[] }) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">Policy Profiles</span>
          <h3>{policies.length} loaded</h3>
        </div>
        <Shield aria-hidden="true" className="panel-icon" />
      </div>
      <div className="chip-grid">
        {policies.length === 0 ? (
          <span className="chip">loading</span>
        ) : (
          policies.map((policy) => (
            <span className="chip" key={policy}>
              {policy}
            </span>
          ))
        )}
      </div>
    </section>
  );
}

function CredentialsView({ credentials }: { credentials: CredentialStatus | null }) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">Credentials</span>
          <h3>{credentials?.provider ?? "openai-compatible"}</h3>
        </div>
        <KeyRound aria-hidden="true" className="panel-icon" />
      </div>
      <dl className="definition-grid">
        <div>
          <dt>Configured</dt>
          <dd>{credentials?.configured ? "yes" : "no"}</dd>
        </div>
        <div>
          <dt>Real enabled</dt>
          <dd>{credentials?.real_enabled ? "yes" : "no"}</dd>
        </div>
        <div>
          <dt>Provider</dt>
          <dd>{credentials?.provider ?? "openai-compatible"}</dd>
        </div>
        <div>
          <dt>Source</dt>
          <dd>{credentials?.source ?? "missing"}</dd>
        </div>
        <div>
          <dt>Base URL</dt>
          <dd>{credentials?.base_url ?? "https://njusehub.info/v1"}</dd>
        </div>
        <div>
          <dt>Model</dt>
          <dd>{credentials?.model ?? "glm-5.2"}</dd>
        </div>
      </dl>
      <p className="inline-note">
        Configure credentials on the server with the CLI, an environment variable, or a
        Docker Secret. Secret values are never accepted or displayed in this console.
      </p>
    </section>
  );
}

function SettingsView({
  credentialMode,
  primaryPolicy,
}: {
  credentialMode: string;
  primaryPolicy: string;
}) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">Settings</span>
          <h3>Runtime defaults</h3>
        </div>
        <Settings aria-hidden="true" className="panel-icon" />
      </div>
      <dl className="definition-grid">
        <div>
          <dt>Policy</dt>
          <dd>{primaryPolicy}</dd>
        </div>
        <div>
          <dt>Credential mode</dt>
          <dd>{credentialMode}</dd>
        </div>
        <div>
          <dt>Stream endpoint</dt>
          <dd>/api/runs/:id/events</dd>
        </div>
      </dl>
    </section>
  );
}
