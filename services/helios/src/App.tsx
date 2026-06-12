import { useCallback, useEffect, useState, type ReactNode } from 'react';

const API_BASE = 'https://messages.completeautomate.com';

// ── Types ──────────────────────────────────────────

interface Message {
  id: string;
  name: string;
  email: string;
  subject: string;
  message: string;
  read: boolean;
  created_at: string;
  updated_at: string;
}

interface StateTransition {
  state: string;
  at: string;
}

interface Lead {
  id: string;
  source: string;
  url: string;
  title: string;
  company: string | null;
  score: number;
  pain_point: string;
  fit_reason: string;
  angle: string;
  urgency: string;
  state: string;
  seen_at: string;
  website: string | null;
  linkedin: string | null;
  contact_name: string | null;
  contact_email: string | null;
  recent_news: string[];
  tech_stack: string[];
  funding: string | null;
  budget_min: number | null;
  budget_max: number | null;
  budget_confidence: string | null;
  enriched_at: string | null;
  history: StateTransition[];
}

type ViewState =
  | { tab: 'dashboard' }
  | { tab: 'messages' }
  | { tab: 'message-detail'; messageId: string }
  | { tab: 'leads' }
  | { tab: 'lead-detail'; leadId: string };

// ── Helpers ────────────────────────────────────────

function formatTime(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  return d.toLocaleDateString();
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  const month = d.toLocaleString('en-US', { month: 'short' });
  const day = d.getDate();
  const year = d.getFullYear();
  const hours = d.getHours().toString().padStart(2, '0');
  const mins = d.getMinutes().toString().padStart(2, '0');
  return `${month} ${day}, ${year} at ${hours}:${mins}`;
}

function sourceIcon(source: string): string {
  switch (source) {
    case 'reddit': return '🤖';
    case 'hackernews': return '💬';
    case 'google_news': return '📰';
    case 'indeed': return '💼';
    case 'crunchbase': return '📊';
    case 'producthunt': return '🚀';
    default: return '📡';
  }
}

function urgencyColor(urgency: string): string {
  switch (urgency) {
    case 'high': return 'text-red-400 bg-red-600/20';
    case 'medium': return 'text-yellow-400 bg-yellow-600/20';
    case 'low': return 'text-gray-400 bg-gray-600/20';
    default: return 'text-gray-500 bg-gray-600/10';
  }
}

function stateColor(state: string): string {
  switch (state) {
    case 'discovery': return 'text-cyan-400 bg-cyan-600/20';
    case 'contacted': return 'text-blue-400 bg-blue-600/20';
    case 'qualified': return 'text-green-400 bg-green-600/20';
    case 'not_interested': return 'text-gray-500 bg-gray-600/20';
    case 'won': return 'text-yellow-400 bg-yellow-600/20';
    default: return 'text-gray-400 bg-gray-600/15';
  }
}

function scoreColor(score: number): string {
  if (score >= 8) return 'text-green-400';
  if (score >= 5) return 'text-yellow-400';
  return 'text-gray-500';
}

function getPageTitle(tab: ViewState['tab']): string {
  if (tab === 'dashboard') return 'Signals and sections';
  if (tab === 'messages' || tab === 'message-detail') return 'Inbox workspace';
  return 'Pipeline workspace';
}

// ── Hooks ──────────────────────────────────────────

function useMessages() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [unreadCount, setUnreadCount] = useState(0);

  const fetchMessages = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(`${API_BASE}/messages`, {
        headers: { 'Content-Type': 'application/json' },
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      setMessages(data.messages);
      setUnreadCount(data.messages.filter((m: Message) => !m.read).length);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load messages');
    }
    setLoading(false);
  }, []);

  useEffect(() => { fetchMessages(); }, [fetchMessages]);

  const markRead = async (id: string) => {
    try {
      const resp = await fetch(`${API_BASE}/messages/${id}/read`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      setMessages((prev) =>
        prev.map((m) => (m.id === id ? { ...m, read: true } : m))
      );
      setUnreadCount((c) => Math.max(0, c - 1));
    } catch (e) {
      console.error('Failed to mark as read', e);
    }
  };

  const deleteMessage = async (id: string) => {
    try {
      const resp = await fetch(`${API_BASE}/messages/${id}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      setMessages((prev) => prev.filter((m) => m.id !== id));
      setUnreadCount((c) => Math.max(0, c - 1));
    } catch (e) {
      console.error('Failed to delete message', e);
    }
  };

  return { messages, loading, error, unreadCount, fetchMessages, markRead, deleteMessage };
}

function useLeads() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [leadDetail, setLeadDetail] = useState<Lead | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const fetchLeads = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(`${API_BASE}/leads`, {
        headers: { 'Content-Type': 'application/json' },
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      setLeads(data.leads || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load leads');
    }
    setLoading(false);
  }, []);

  useEffect(() => { fetchLeads(); }, [fetchLeads]);

  const fetchLeadDetail = async (id: string) => {
    setDetailLoading(true);
    try {
      const resp = await fetch(`${API_BASE}/leads/${id}`, {
        headers: { 'Content-Type': 'application/json' },
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      setLeadDetail(data);
    } catch (e) {
      console.error('Failed to load lead detail', e);
      setLeadDetail(null);
    }
    setDetailLoading(false);
  };

  const updateState = async (id: string, newState: string) => {
    try {
      const resp = await fetch(`${API_BASE}/leads/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ state: newState }),
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      // Update local state
      setLeads((prev) =>
        prev.map((l) => (l.id === id ? { ...l, state: newState } : l))
      );
      setLeadDetail((prev) => (prev?.id === id ? { ...prev, state: newState } : prev));
    } catch (e) {
      console.error('Failed to update lead state', e);
    }
  };

  return { leads, loading, error, leadDetail, detailLoading, fetchLeads, fetchLeadDetail, updateState };
}

// ── Message Detail ─────────────────────────────────

function MessageDetailView({
  message,
  onBack,
  onMarkRead,
  onDelete,
}: Readonly<{
  message: Message;
  onBack: () => void;
  onMarkRead: (id: string) => void;
  onDelete: (id: string) => void;
}>) {
  return (
    <div className="space-y-6">
      <button
        onClick={onBack}
        className="flex items-center gap-2 text-sm text-gray-400 transition hover:text-gray-200"
      >
        ← Messages
      </button>

      <div className="rounded-xl border border-gray-800 bg-gray-900/60 p-6">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-lg font-bold">{message.subject}</h2>
            <p className="mt-1 text-sm text-gray-400">
              {message.name} &lt;{message.email}&gt;
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-right text-xs text-gray-500">
              <div>{formatTime(message.created_at)}</div>
              <div className="text-gray-600">{formatDate(message.created_at)}</div>
            </span>
            {!message.read && (
              <button
                onClick={() => onMarkRead(message.id)}
                className="rounded-md bg-cyan-600/20 px-3 py-1 text-xs font-medium text-cyan-400 transition hover:bg-cyan-600/30"
              >
                Mark Read
              </button>
            )}
            <button
              onClick={() => {
                if (globalThis.confirm('Delete this message?')) onDelete(message.id);
              }}
              className="rounded-md bg-red-600/20 px-3 py-1 text-xs font-medium text-red-400 transition hover:bg-red-600/30"
            >
              Delete
            </button>
          </div>
        </div>
        <div className="mt-6 whitespace-pre-wrap rounded-lg border border-gray-800 bg-gray-950/50 p-4 text-sm leading-7 text-gray-300">
          {message.message}
        </div>
      </div>
    </div>
  );
}

// ── Lead Detail ────────────────────────────────────

const LEAD_STATES = ['discovery', 'contacted', 'qualified', 'won', 'not_interested'];

function LeadDetailView({
  lead,
  onBack,
  onUpdateState,
}: Readonly<{
  lead: Lead;
  onBack: () => void;
  onUpdateState: (id: string, state: string) => void;
}>) {
  return (
    <div className="space-y-6">
      <button
        onClick={onBack}
        className="flex items-center gap-2 text-sm text-gray-400 transition hover:text-gray-200"
      >
        ← Leads
      </button>

      {/* Header */}
      <div className="rounded-xl border border-gray-800 bg-gray-900/60 p-6">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-lg">{sourceIcon(lead.source)}</span>
              <h2 className="text-lg font-bold">{lead.company || lead.title}</h2>
            </div>
            <p className="mt-1 text-xs text-gray-500">
              {lead.source} · {lead.url ? <a href={lead.url} target="_blank" className="text-cyan-500 hover:underline">source</a> : 'no URL'}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className={`rounded-md px-2.5 py-1 text-xs font-medium ${stateColor(lead.state)}`}>
              {lead.state}
            </span>
            <span className={`rounded-md px-2.5 py-1 text-xs font-bold ${scoreColor(lead.score)}`}>
              {lead.score}/10
            </span>
            <span className={`rounded-md px-2.5 py-1 text-xs font-medium ${urgencyColor(lead.urgency)}`}>
              {lead.urgency}
            </span>
          </div>
        </div>
        <div className="mt-2 text-xs text-gray-500">
          <span>{formatTime(lead.seen_at)}</span>
          <span className="ml-2 text-gray-600">{formatDate(lead.seen_at)}</span>
        </div>
      </div>

      {/* State update */}
      <div className="rounded-xl border border-gray-800 bg-gray-900/40 p-5">
        <div className="mb-2 text-xs font-medium uppercase tracking-wide text-gray-500">Change State</div>
        <div className="flex flex-wrap gap-2">
          {LEAD_STATES.map((s) => (
            <button
              key={s}
              onClick={() => onUpdateState(lead.id, s)}
              className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${
                lead.state === s
                  ? 'bg-cyan-600/30 text-cyan-400 ring-1 ring-cyan-500/50'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-gray-200'
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Pain point & fit */}
      <div className="grid grid-cols-2 gap-4">
        <div className="rounded-xl border border-gray-800 bg-gray-900/40 p-5">
          <h3 className="mb-2 text-xs font-medium text-gray-500 uppercase tracking-wide">Pain Point</h3>
          <p className="text-sm text-gray-300">{lead.pain_point}</p>
        </div>
        <div className="rounded-xl border border-gray-800 bg-gray-900/40 p-5">
          <h3 className="mb-2 text-xs font-medium text-gray-500 uppercase tracking-wide">Fit Reason</h3>
          <p className="text-sm text-gray-300">{lead.fit_reason}</p>
        </div>
      </div>

      {/* Outreach angle */}
      {lead.angle && (
        <div className="rounded-xl border border-gray-800 bg-gray-900/40 p-5">
          <h3 className="mb-2 text-xs font-medium text-gray-500 uppercase tracking-wide">Suggested Angle</h3>
          <p className="text-sm italic text-gray-400">{lead.angle}</p>
        </div>
      )}

      {/* Enrichment data */}
      <div className="rounded-xl border border-gray-800 bg-gray-900/40 p-5">
        <h3 className="mb-3 text-xs font-medium text-gray-500 uppercase tracking-wide">
          Enrichment {lead.enriched_at ? <span className="text-green-500">✓</span> : <span className="text-gray-600">(none yet)</span>}
        </h3>
        <div className="grid grid-cols-2 gap-4 text-sm">
          {lead.website && (
            <div>
              <span className="text-gray-500">Website:</span>{' '}
              <a href={lead.website} target="_blank" className="text-cyan-500 hover:underline">{lead.website}</a>
            </div>
          )}
          {lead.linkedin && (
            <div>
              <span className="text-gray-500">LinkedIn:</span>{' '}
              <a href={lead.linkedin} target="_blank" className="text-cyan-500 hover:underline">profile</a>
            </div>
          )}
          {lead.contact_name && <div><span className="text-gray-500">Contact:</span> {lead.contact_name}{lead.contact_email ? ` (${lead.contact_email})` : ''}</div>}
          {lead.funding && <div><span className="text-gray-500">Funding:</span> {lead.funding}</div>}
          {lead.budget_min != null && <div><span className="text-gray-500">Budget:</span> ${lead.budget_min.toLocaleString()}{lead.budget_max ? ` – $${lead.budget_max.toLocaleString()}` : ''} <span className="text-gray-600">({lead.budget_confidence || 'unknown'})</span></div>}
          {lead.tech_stack.length > 0 && <div className="col-span-2"><span className="text-gray-500">Tech Stack:</span> {lead.tech_stack.join(', ')}</div>}
          {lead.recent_news.length > 0 && (
            <div className="col-span-2">
              <span className="text-gray-500">Recent News:</span>
              <ul className="mt-1 list-inside list-disc text-gray-400">
                {lead.recent_news.slice(0, 5).map((newsItem) => <li key={newsItem} className="truncate">{newsItem}</li>)}
              </ul>
            </div>
          )}
        </div>
      </div>

      {/* History */}
      {lead.history.length > 1 && (
        <div className="rounded-xl border border-gray-800 bg-gray-900/40 p-5">
          <h3 className="mb-3 text-xs font-medium text-gray-500 uppercase tracking-wide">State History</h3>
          <div className="space-y-1">
            {lead.history.map((h) => (
              <div key={`${h.state}-${h.at}`} className="flex items-center gap-3 text-xs">
                <span className={`rounded px-2 py-0.5 ${stateColor(h.state)}`}>{h.state}</span>
                <span className="text-gray-600">{formatDate(h.at)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function SectionHeader({
  eyebrow,
  title,
  description,
  action,
}: Readonly<{
  eyebrow: string;
  title: string;
  description: string;
  action?: ReactNode;
}>) {
  return (
    <div className="flex flex-col gap-3 border-b border-gray-800/80 px-5 py-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-cyan-400/80">{eyebrow}</p>
        <h2 className="mt-2 text-lg font-semibold text-white">{title}</h2>
        <p className="mt-1 max-w-2xl text-sm text-gray-400">{description}</p>
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}

function DashboardSection({
  id,
  title,
  description,
  children,
  action,
}: Readonly<{
  id: string;
  title: string;
  description: string;
  children: ReactNode;
  action?: ReactNode;
}>) {
  return (
    <section id={id} className="overflow-hidden rounded-2xl border border-gray-800 bg-gray-900/45 shadow-[0_24px_80px_rgba(2,6,23,0.45)]">
      <SectionHeader eyebrow={id} title={title} description={description} action={action} />
      <div className="p-5">{children}</div>
    </section>
  );
}

function OverviewSection({
  messageCount,
  unreadCount,
  leadCount,
  hotCount,
  warmCount,
}: Readonly<{
  messageCount: number;
  unreadCount: number;
  leadCount: number;
  hotCount: number;
  warmCount: number;
}>) {
  const stats = [
    { label: 'Total Messages', value: messageCount, tone: 'text-white' },
    { label: 'Unread Inbox', value: unreadCount, tone: 'text-cyan-400' },
    { label: 'Lead Pipeline', value: leadCount, tone: 'text-white' },
    { label: 'Hot Leads', value: hotCount, tone: 'text-green-400' },
    { label: 'Warm Leads', value: warmCount, tone: 'text-yellow-400' },
  ];

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
      {stats.map((stat) => (
        <div
          key={stat.label}
          className="rounded-2xl border border-gray-800/80 bg-gray-950/60 p-4"
        >
          <p className={`text-3xl font-semibold ${stat.tone}`}>{stat.value}</p>
          <p className="mt-2 text-xs uppercase tracking-[0.18em] text-gray-500">{stat.label}</p>
        </div>
      ))}
    </div>
  );
}

function MessagesSection({
  messages,
  loading,
  error,
  onRefresh,
  onOpen,
  onDelete,
}: Readonly<{
  messages: Message[];
  loading: boolean;
  error: string | null;
  onRefresh: () => void;
  onOpen: (id: string) => void;
  onDelete: (id: string) => void;
}>) {
  let content: ReactNode;

  if (loading) {
    content = (
      <div className="flex items-center justify-center py-16">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent" />
      </div>
    );
  } else if (error) {
    content = <div className="rounded-xl border border-red-500/20 bg-red-500/5 px-5 py-8 text-center text-sm text-red-300">{error}</div>;
  } else if (messages.length === 0) {
    content = <div className="rounded-xl border border-gray-800 bg-gray-950/40 px-5 py-8 text-center text-sm text-gray-500">No messages yet.</div>;
  } else {
    content = (
      <div className="space-y-3">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className="flex flex-col gap-4 rounded-2xl border border-gray-800/80 bg-gray-950/55 p-4 transition hover:border-gray-700 hover:bg-gray-950/80 lg:flex-row lg:items-center"
          >
            <button
              onClick={() => onOpen(msg.id)}
              className="flex min-w-0 flex-1 items-start gap-4 text-left"
            >
              <div className={`mt-1 h-2.5 w-2.5 shrink-0 rounded-full ${msg.read ? 'bg-gray-700' : 'bg-cyan-500'}`} />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                  <span className="truncate text-sm font-medium text-gray-100">{msg.name}</span>
                  <span className="truncate text-xs uppercase tracking-[0.16em] text-gray-500">{msg.subject}</span>
                </div>
                <p className="mt-2 line-clamp-2 text-sm text-gray-400">{msg.message}</p>
              </div>
            </button>
            <div className="flex items-center justify-between gap-3 lg:justify-end">
              <span className="shrink-0 text-right text-xs text-gray-500">
                <div>{formatTime(msg.created_at)}</div>
                <div className="text-gray-600">{formatDate(msg.created_at)}</div>
              </span>
              <button
                onClick={() => {
                  if (globalThis.confirm(`Delete message from ${msg.name}?`)) onDelete(msg.id);
                }}
                className="shrink-0 rounded-md bg-red-600/15 px-2.5 py-1 text-xs font-medium text-red-300 transition hover:bg-red-600/25"
              >
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <DashboardSection
      id="messages"
      title="Inbox"
      description="Recent contact form submissions with fast access to detail and cleanup actions."
      action={
        <button
          onClick={onRefresh}
          className="rounded-md border border-gray-700 bg-gray-900 px-3 py-1.5 text-xs font-medium text-gray-300 transition hover:border-gray-600 hover:text-white"
        >
          Refresh inbox
        </button>
      }
    >
      {content}
    </DashboardSection>
  );
}

function LeadsSection({
  leads,
  loading,
  error,
  onRefresh,
  onOpen,
}: Readonly<{
  leads: Lead[];
  loading: boolean;
  error: string | null;
  onRefresh: () => void;
  onOpen: (id: string) => void;
}>) {
  let content: ReactNode;

  if (loading) {
    content = (
      <div className="flex items-center justify-center py-16">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent" />
      </div>
    );
  } else if (error) {
    content = <div className="rounded-xl border border-red-500/20 bg-red-500/5 px-5 py-8 text-center text-sm text-red-300">{error}</div>;
  } else if (leads.length === 0) {
    content = <div className="rounded-xl border border-gray-800 bg-gray-950/40 px-5 py-8 text-center text-sm text-gray-500">No leads yet. Pythia runs daily at 12:00 HKT.</div>;
  } else {
    content = (
      <div className="space-y-3">
        {leads.map((lead) => (
          <button
            key={lead.id}
            onClick={() => onOpen(lead.id)}
            className="flex w-full flex-col gap-3 rounded-2xl border border-gray-800/80 bg-gray-950/55 p-4 text-left transition hover:border-gray-700 hover:bg-gray-950/80 lg:flex-row lg:items-center"
          >
            <div className="flex min-w-0 flex-1 items-start gap-3">
              <span className="mt-0.5 text-lg">{sourceIcon(lead.source)}</span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="truncate text-sm font-medium text-gray-100">{lead.company || lead.title}</span>
                  <span className={`shrink-0 rounded px-1.5 py-0.5 text-xs font-medium ${stateColor(lead.state)}`}>
                    {lead.state}
                  </span>
                </div>
                <p className="mt-2 line-clamp-2 text-sm text-gray-400">{lead.pain_point}</p>
              </div>
            </div>
            <div className="flex shrink-0 flex-wrap items-center gap-2 text-xs">
              <span className={`rounded px-2 py-0.5 font-bold ${scoreColor(lead.score)}`}>{lead.score}/10</span>
              <span className={`rounded px-2 py-0.5 ${urgencyColor(lead.urgency)}`}>{lead.urgency}</span>
              <span className="text-gray-500">{formatTime(lead.seen_at)}</span>
            </div>
          </button>
        ))}
      </div>
    );
  }

  return (
    <DashboardSection
      id="leads"
      title="Pipeline"
      description="Prioritized prospects, scored by urgency and fit so outreach can move without context switching."
      action={
        <button
          onClick={onRefresh}
          className="rounded-md border border-gray-700 bg-gray-900 px-3 py-1.5 text-xs font-medium text-gray-300 transition hover:border-gray-600 hover:text-white"
        >
          Refresh pipeline
        </button>
      }
    >
      {content}
    </DashboardSection>
  );
}

// ── Main App ───────────────────────────────────────

export default function App() {
  const [view, setView] = useState<ViewState>({ tab: 'dashboard' });
  const { messages, loading: msgLoading, error: msgError, unreadCount, fetchMessages, markRead, deleteMessage } = useMessages();
  const { leads, loading: leadLoading, error: leadError, leadDetail, detailLoading, fetchLeads, fetchLeadDetail, updateState } = useLeads();

  const selectedMessage = view.tab === 'message-detail' ? messages.find((m) => m.id === view.messageId) : null;
  const selectedLead = view.tab === 'lead-detail' ? (leadDetail || leads.find((l) => l.id === view.leadId)) : null;

  // Load lead detail when navigating to it
  useEffect(() => {
    if (view.tab === 'lead-detail') {
      fetchLeadDetail(view.leadId);
    }
  }, [fetchLeadDetail, view]);

  const handleDelete = (id: string) => {
    deleteMessage(id);
    if (view.tab === 'message-detail' && view.messageId === id) setView({ tab: 'dashboard' });
  };

  const hotCount = leads.filter((l) => l.score >= 8).length;
  const warmCount = leads.filter((l) => l.score >= 5 && l.score < 8).length;
  const isDetailView = view.tab === 'message-detail' || view.tab === 'lead-detail';
  const pageTitle = getPageTitle(view.tab);
  const pageDescription = isDetailView
    ? 'Review a single record with full context, then step back into the larger workflow when needed.'
    : 'The app is split into overview, inbox, and pipeline sections so navigation stays stable as the data changes.';

  const pageTabs = [
    {
      key: 'dashboard' as const,
      label: 'Overview',
      description: 'High-level system status',
    },
    {
      key: 'messages' as const,
      label: 'Inbox',
      description: 'Message triage and follow-up',
      badge: unreadCount > 0 ? unreadCount : undefined,
    },
    {
      key: 'leads' as const,
      label: 'Pipeline',
      description: 'Qualified prospects and urgency',
      badge: hotCount > 0 ? hotCount : undefined,
    },
  ];

  const renderPrimaryContent = () => {
    if (view.tab === 'dashboard') {
      return (
        <div className="space-y-6">
          <div className="grid gap-3 rounded-2xl border border-gray-800 bg-gray-900/45 p-4 md:grid-cols-3">
            {[
              { label: 'Overview', href: '#overview' },
              { label: 'Inbox', href: '#messages' },
              { label: 'Pipeline', href: '#leads' },
            ].map((item) => (
              <a
                key={item.href}
                href={item.href}
                className="rounded-xl border border-gray-800 bg-gray-950/60 px-4 py-3 text-sm text-gray-300 transition hover:border-cyan-500/40 hover:text-white"
              >
                {item.label}
              </a>
            ))}
          </div>

          <DashboardSection
            id="overview"
            title="Signal overview"
            description="A single scan of inbox volume, pipeline pressure, and lead temperature."
          >
            <OverviewSection
              messageCount={messages.length}
              unreadCount={unreadCount}
              leadCount={leads.length}
              hotCount={hotCount}
              warmCount={warmCount}
            />
          </DashboardSection>

          <MessagesSection
            messages={messages.slice(0, 5)}
            loading={msgLoading}
            error={msgError}
            onRefresh={fetchMessages}
            onOpen={(id) => setView({ tab: 'message-detail', messageId: id })}
            onDelete={handleDelete}
          />

          <LeadsSection
            leads={leads.slice(0, 6)}
            loading={leadLoading}
            error={leadError}
            onRefresh={fetchLeads}
            onOpen={(id) => setView({ tab: 'lead-detail', leadId: id })}
          />
        </div>
      );
    }

    if (view.tab === 'messages') {
      return (
        <MessagesSection
          messages={messages}
          loading={msgLoading}
          error={msgError}
          onRefresh={fetchMessages}
          onOpen={(id) => setView({ tab: 'message-detail', messageId: id })}
          onDelete={handleDelete}
        />
      );
    }

    return (
      <LeadsSection
        leads={leads}
        loading={leadLoading}
        error={leadError}
        onRefresh={fetchLeads}
        onOpen={(id) => setView({ tab: 'lead-detail', leadId: id })}
      />
    );
  };

  let mainContent: ReactNode;

  if (view.tab === 'message-detail' && selectedMessage) {
    mainContent = (
      <MessageDetailView
        message={selectedMessage}
        onBack={() => setView({ tab: 'messages' })}
        onMarkRead={(id) => {
          markRead(id);
          setView({ tab: 'messages' });
        }}
        onDelete={handleDelete}
      />
    );
  } else if (view.tab === 'lead-detail' && selectedLead) {
    mainContent = (
      <LeadDetailView
        lead={selectedLead}
        onBack={() => setView({ tab: 'leads' })}
        onUpdateState={(id, state) => updateState(id, state)}
      />
    );
  } else {
    mainContent = renderPrimaryContent();
  }

  return (
    <div className="flex min-h-screen bg-[radial-gradient(circle_at_top,rgba(14,165,233,0.16),transparent_24%),linear-gradient(180deg,#020617_0%,#020617_42%,#111827_100%)] text-gray-100">
      {/* Sidebar */}
      <aside className="hidden w-72 flex-col border-r border-gray-800/80 bg-gray-950/80 p-5 lg:flex">
        <div className="mb-8 flex items-center gap-3">
          <span className="text-xl">☀️</span>
          <div>
            <span className="text-lg font-bold">Helios</span>
            <p className="text-xs uppercase tracking-[0.24em] text-gray-500">Lead intelligence desk</p>
          </div>
        </div>

        <div className="mb-6 rounded-2xl border border-gray-800 bg-gray-900/60 p-4">
          <p className="text-xs uppercase tracking-[0.2em] text-gray-500">Today</p>
          <p className="mt-3 text-3xl font-semibold text-white">{hotCount}</p>
          <p className="mt-1 text-sm text-gray-400">High-priority prospects ready for outreach.</p>
        </div>

        <nav className="flex flex-col gap-2">
          <button
            onClick={() => setView({ tab: 'dashboard' })}
            className={`flex items-center gap-3 rounded-xl px-4 py-3 text-sm transition ${
              view.tab === 'dashboard' ? 'bg-cyan-600/20 text-cyan-300 ring-1 ring-cyan-500/30' : 'text-gray-400 hover:bg-gray-900 hover:text-gray-200'
            }`}
          >
            <span>📊</span>
            <div className="flex flex-col items-start">
              <span>Overview</span>
              <span className="text-xs text-gray-500">Metrics and recent movement</span>
            </div>
          </button>
          <button
            onClick={() => setView({ tab: 'messages' })}
            className={`flex items-center justify-between rounded-xl px-4 py-3 text-sm transition ${
              view.tab === 'messages' || view.tab === 'message-detail' ? 'bg-cyan-600/20 text-cyan-300 ring-1 ring-cyan-500/30' : 'text-gray-400 hover:bg-gray-900 hover:text-gray-200'
            }`}
          >
            <div className="flex items-center gap-2">
              <span>✉️</span>
              <div className="flex flex-col items-start">
                <span>Inbox</span>
                <span className="text-xs text-gray-500">Form traffic and replies</span>
              </div>
            </div>
            {unreadCount > 0 && (
              <span className="rounded-full bg-cyan-600 px-2 py-0.5 text-xs font-bold text-white">
                {unreadCount}
              </span>
            )}
          </button>
          <button
            onClick={() => setView({ tab: 'leads' })}
            className={`flex items-center justify-between rounded-xl px-4 py-3 text-sm transition ${
              view.tab === 'leads' || view.tab === 'lead-detail' ? 'bg-cyan-600/20 text-cyan-300 ring-1 ring-cyan-500/30' : 'text-gray-400 hover:bg-gray-900 hover:text-gray-200'
            }`}
          >
            <div className="flex items-center gap-2">
              <span>🎯</span>
              <div className="flex flex-col items-start">
                <span>Pipeline</span>
                <span className="text-xs text-gray-500">Scored prospects and next steps</span>
              </div>
            </div>
            {hotCount > 0 && (
              <span className="rounded-full bg-green-600 px-2 py-0.5 text-xs font-bold text-white">
                {hotCount}
              </span>
            )}
          </button>
        </nav>

        <div className="mt-auto rounded-2xl border border-gray-800 bg-gray-900/50 p-4 text-sm text-gray-400">
          <p className="font-medium text-gray-200">Workflow split</p>
          <p className="mt-2">Use the sidebar for workspace navigation and the page header for section-level movement inside the current screen.</p>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-7xl p-4 sm:p-6 lg:p-8">
          <header className="mb-6 rounded-3xl border border-gray-800/80 bg-gray-900/55 p-5 shadow-[0_24px_80px_rgba(2,6,23,0.45)] sm:p-6">
            <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.28em] text-cyan-400/80">Operations console</p>
                <h1 className="mt-3 text-3xl font-semibold text-white sm:text-4xl">{pageTitle}</h1>
                <p className="mt-3 max-w-3xl text-sm text-gray-400 sm:text-base">{pageDescription}</p>
              </div>

              {!isDetailView && (
                <div className="grid gap-3 sm:grid-cols-3">
                  {pageTabs.map((tab) => (
                    <button
                      key={tab.key}
                      onClick={() => setView({ tab: tab.key })}
                      className={`rounded-2xl border px-4 py-3 text-left transition ${
                        view.tab === tab.key
                          ? 'border-cyan-500/40 bg-cyan-500/10 text-white'
                          : 'border-gray-800 bg-gray-950/55 text-gray-400 hover:border-gray-700 hover:text-gray-200'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-4">
                        <span className="text-sm font-medium">{tab.label}</span>
                        {tab.badge != null && (
                          <span className="rounded-full bg-white/10 px-2 py-0.5 text-xs font-semibold text-white">{tab.badge}</span>
                        )}
                      </div>
                      <p className="mt-1 text-xs text-gray-500">{tab.description}</p>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </header>

        {mainContent}

        {detailLoading && view.tab === 'lead-detail' && (
          <div className="mt-4 flex items-center justify-center py-8">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent" />
          </div>
        )}
        </div>
      </main>
    </div>
  );
}
