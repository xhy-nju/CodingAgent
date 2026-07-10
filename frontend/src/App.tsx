import {
  Activity,
  CheckCircle2,
  ClipboardList,
  Database,
  Gauge,
  KeyRound,
  LucideIcon,
  MemoryStick,
  Play,
  Settings,
  Shield,
  TerminalSquare,
  XCircle,
} from "lucide-react";
import { useEffect, useState } from "react";
import {
  createDemoRun,
  fetchApprovals,
  fetchCredentialStatus,
  fetchMemory,
  fetchPolicies,
  openRunEventSource,
} from "./api";
import {
  RUN_EVENT_TYPES,
  type ApprovalRecord,
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
    subtitle: "Policy check, redaction, HITL approval",
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
  const [busyDemo, setBusyDemo] = useState<DemoName | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    Promise.all([fetchPolicies(), fetchCredentialStatus(), fetchApprovals(), fetchMemory()])
      .then(([policyList, credentialStatus, approvalList, memoryList]) => {
        if (!isMounted) {
          return;
        }
        setPolicies(policyList);
        setCredentials(credentialStatus);
        setApprovals(approvalList.approvals);
        setMemories(memoryList.records);
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

  const policyProfiles = policies?.profiles ?? [];
  const primaryPolicy = policyProfiles[0] ?? "loading";
  const credentialMode = credentials?.real_enabled
    ? "real LLM"
    : credentials?.configured
      ? "configured mock"
      : "mock LLM";

  return (
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
              onClick={() => setActiveTab(id)}
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
              policyCount={policyProfiles.length}
              run={run}
            />
          ) : null}
          {activeTab === "run" ? <RunDetailView events={events} run={run} /> : null}
          {activeTab === "approvals" ? (
            <ApprovalView approvals={approvals} />
          ) : null}
          {activeTab === "memory" ? <MemoryView memories={memories} /> : null}
          {activeTab === "policies" ? <PoliciesView policies={policyProfiles} /> : null}
          {activeTab === "credentials" ? <CredentialsView credentials={credentials} /> : null}
          {activeTab === "settings" ? (
            <SettingsView credentialMode={credentialMode} primaryPolicy={primaryPolicy} />
          ) : null}
        </section>
      </div>
    </main>
  );
}

function DashboardView({
  busyDemo,
  credentialMode,
  onStartDemo,
  policyCount,
  run,
}: {
  busyDemo: DemoName | null;
  credentialMode: string;
  onStartDemo: (name: DemoName) => void;
  policyCount: number;
  run: RunSummary | null;
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
              <h3>One-click runs</h3>
            </div>
          </div>
          <div className="demo-actions">
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
          </div>
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
  approvals,
}: {
  approvals: ApprovalRecord[];
}) {
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
          {approvals.map((approval) => (
            <article className="feedback-item warning" key={approval.id}>
              <div>
                <span className="eyebrow">{approval.state}</span>
                <h3>{approval.reason}</h3>
              </div>
              <span className="detail-count">{approval.rules.length} rules</span>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function MemoryView({
  memories,
}: {
  memories: MemoryRecord[];
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
