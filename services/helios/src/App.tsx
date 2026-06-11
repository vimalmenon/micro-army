import { useCallback, useEffect, useState } from 'react';

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
      setLeadDetail((prev) => (prev && prev.id === id ? { ...prev, state: newState } : prev));
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
}: {
  message: Message;
  onBack: () => void;
  onMarkRead: (id: string) => void;
  onDelete: (id: string) => void;
}) {
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
                if (window.confirm('Delete this message?')) onDelete(message.id);
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
}: {
  lead: Lead;
  onBack: () => void;
  onUpdateState: (id: string, state: string) => void;
}) {
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
        <label className="mb-2 block text-xs font-medium text-gray-500 uppercase tracking-wide">Change State</label>
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
                {lead.recent_news.slice(0, 5).map((n, i) => <li key={i} className="truncate">{n}</li>)}
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
            {lead.history.map((h, i) => (
              <div key={i} className="flex items-center gap-3 text-xs">
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
  }, [view, fetchLeadDetail]);

  const handleDelete = (id: string) => {
    deleteMessage(id);
    if (view.tab === 'message-detail' && view.messageId === id) setView({ tab: 'dashboard' });
  };

  const hotCount = leads.filter((l) => l.score >= 8).length;
  const warmCount = leads.filter((l) => l.score >= 5 && l.score < 8).length;

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="flex w-56 flex-col border-r border-gray-800 bg-gray-950 p-4">
        <div className="mb-6 flex items-center gap-2">
          <span className="text-xl">☀️</span>
          <span className="text-lg font-bold">Helios</span>
        </div>
        <nav className="flex flex-col gap-1">
          <button
            onClick={() => setView({ tab: 'dashboard' })}
            className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition ${
              view.tab === 'dashboard' ? 'bg-cyan-600/20 text-cyan-400' : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            <span>📊</span>
            <span>Dashboard</span>
          </button>
          <button
            onClick={() => setView({ tab: 'messages' })}
            className={`flex items-center justify-between rounded-lg px-3 py-2 text-sm transition ${
              view.tab === 'messages' || view.tab === 'message-detail' ? 'bg-cyan-600/20 text-cyan-400' : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            <div className="flex items-center gap-2">
              <span>✉️</span>
              <span>Messages</span>
            </div>
            {unreadCount > 0 && (
              <span className="rounded-full bg-cyan-600 px-2 py-0.5 text-xs font-bold text-white">
                {unreadCount}
              </span>
            )}
          </button>
          <button
            onClick={() => setView({ tab: 'leads' })}
            className={`flex items-center justify-between rounded-lg px-3 py-2 text-sm transition ${
              view.tab === 'leads' || view.tab === 'lead-detail' ? 'bg-cyan-600/20 text-cyan-400' : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            <div className="flex items-center gap-2">
              <span>🎯</span>
              <span>Leads</span>
            </div>
            {hotCount > 0 && (
              <span className="rounded-full bg-green-600 px-2 py-0.5 text-xs font-bold text-white">
                {hotCount}
              </span>
            )}
          </button>
        </nav>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-y-auto p-6">
        {view.tab === 'message-detail' && selectedMessage ? (
          <MessageDetailView
            message={selectedMessage}
            onBack={() => setView({ tab: 'messages' })}
            onMarkRead={(id) => {
              markRead(id);
              setView({ tab: 'messages' });
            }}
            onDelete={handleDelete}
          />
        ) : view.tab === 'lead-detail' && selectedLead ? (
          <LeadDetailView
            lead={selectedLead}
            onBack={() => setView({ tab: 'leads' })}
            onUpdateState={(id, state) => updateState(id, state)}
          />
        ) : (
          <div className="space-y-6">
            {/* Stats */}
            <div className="flex gap-4">
              <div className="flex-1 rounded-xl border border-gray-800 bg-gray-900/60 p-4">
                <p className="text-2xl font-bold">{messages.length}</p>
                <p className="text-xs text-gray-500">Total Messages</p>
              </div>
              <div className="flex-1 rounded-xl border border-gray-800 bg-gray-900/60 p-4">
                <p className="text-2xl font-bold text-cyan-400">{unreadCount}</p>
                <p className="text-xs text-gray-500">Unread</p>
              </div>
              <div className="flex-1 rounded-xl border border-gray-800 bg-gray-900/60 p-4">
                <p className="text-2xl font-bold">{leads.length}</p>
                <p className="text-xs text-gray-500">Total Leads</p>
              </div>
              <div className="flex-1 rounded-xl border border-gray-800 bg-gray-900/60 p-4">
                <p className="text-2xl font-bold text-green-400">{hotCount}</p>
                <p className="text-xs text-gray-500">Hot</p>
              </div>
              <div className="flex-1 rounded-xl border border-gray-800 bg-gray-900/60 p-4">
                <p className="text-2xl font-bold text-yellow-400">{warmCount}</p>
                <p className="text-xs text-gray-500">Warm</p>
              </div>
            </div>

            {/* Messages Table */}
            {view.tab !== 'leads' && view.tab !== 'lead-detail' && (
              <div className="rounded-xl border border-gray-800 bg-gray-900/40">
                <div className="flex items-center justify-between border-b border-gray-800 px-5 py-3">
                  <h2 className="text-sm font-bold tracking-wide text-gray-300 uppercase">Messages</h2>
                  <button
                    onClick={fetchMessages}
                    className="rounded-md bg-gray-800 px-3 py-1.5 text-xs text-gray-400 transition hover:text-gray-200"
                  >
                    Refresh
                  </button>
                </div>

                {msgLoading ? (
                  <div className="flex items-center justify-center py-16">
                    <div className="h-6 w-6 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent" />
                  </div>
                ) : msgError ? (
                  <div className="px-5 py-8 text-center text-sm text-red-400">{msgError}</div>
                ) : messages.length === 0 ? (
                  <div className="px-5 py-8 text-center text-sm text-gray-500">No messages yet.</div>
                ) : (
                  <div className="divide-y divide-gray-800/50">
                    {messages.map((msg) => (
                      <div
                        key={msg.id}
                        className="flex w-full items-center gap-4 px-5 py-3.5 transition hover:bg-gray-800/40"
                      >
                        <button
                          onClick={() => setView({ tab: 'message-detail', messageId: msg.id })}
                          className="flex min-w-0 flex-1 items-center gap-4 text-left"
                        >
                          <div className={`h-2 w-2 shrink-0 rounded-full ${msg.read ? 'bg-transparent' : 'bg-cyan-500'}`} />
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-3">
                              <span className="truncate text-sm font-medium text-gray-200">{msg.name}</span>
                              <span className="truncate text-xs text-gray-500">{msg.subject}</span>
                            </div>
                            <p className="mt-0.5 truncate text-xs text-gray-600">{msg.message}</p>
                          </div>
                          <span className="shrink-0 text-right text-xs text-gray-600">
                            <div>{formatTime(msg.created_at)}</div>
                            <div className="text-gray-700">{formatDate(msg.created_at)}</div>
                          </span>
                        </button>
                        <button
                          onClick={() => {
                            if (window.confirm(`Delete message from ${msg.name}?`)) handleDelete(msg.id);
                          }}
                          className="shrink-0 rounded-md bg-red-600/20 px-2.5 py-1 text-xs font-medium text-red-400 transition hover:bg-red-600/30"
                        >
                          Delete
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Leads Table */}
            {(view.tab === 'leads' || view.tab === 'lead-detail') && (
              <div className="rounded-xl border border-gray-800 bg-gray-900/40">
                <div className="flex items-center justify-between border-b border-gray-800 px-5 py-3">
                  <h2 className="text-sm font-bold tracking-wide text-gray-300 uppercase">Leads</h2>
                  <button
                    onClick={fetchLeads}
                    className="rounded-md bg-gray-800 px-3 py-1.5 text-xs text-gray-400 transition hover:text-gray-200"
                  >
                    Refresh
                  </button>
                </div>

                {leadLoading ? (
                  <div className="flex items-center justify-center py-16">
                    <div className="h-6 w-6 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent" />
                  </div>
                ) : leadError ? (
                  <div className="px-5 py-8 text-center text-sm text-red-400">{leadError}</div>
                ) : leads.length === 0 ? (
                  <div className="px-5 py-8 text-center text-sm text-gray-500">No leads yet. Pythia runs daily at 12:00 HKT.</div>
                ) : (
                  <div className="divide-y divide-gray-800/50">
                    {leads.map((lead) => (
                      <div
                        key={lead.id}
                        className="flex w-full items-center gap-4 px-5 py-3 transition hover:bg-gray-800/40"
                      >
                        <button
                          onClick={() => {
                            setView({ tab: 'lead-detail', leadId: lead.id });
                          }}
                          className="flex min-w-0 flex-1 items-center gap-3 text-left"
                        >
                          <span className="text-base">{sourceIcon(lead.source)}</span>
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2">
                              <span className="truncate text-sm font-medium text-gray-200">
                                {lead.company || lead.title}
                              </span>
                              <span className={`shrink-0 rounded px-1.5 py-0.5 text-xs font-medium ${stateColor(lead.state)}`}>
                                {lead.state}
                              </span>
                            </div>
                            <p className="mt-0.5 truncate text-xs text-gray-500">{lead.pain_point}</p>
                          </div>
                          <div className="flex shrink-0 items-center gap-2">
                            <span className={`rounded px-2 py-0.5 text-xs font-bold ${scoreColor(lead.score)}`}>
                              {lead.score}
                            </span>
                            <span className={`rounded px-2 py-0.5 text-xs ${urgencyColor(lead.urgency)}`}>
                              {lead.urgency}
                            </span>
                            <span className="text-right text-xs text-gray-600">
                              <div>{formatTime(lead.seen_at)}</div>
                            </span>
                          </div>
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {detailLoading && view.tab === 'lead-detail' && (
          <div className="mt-4 flex items-center justify-center py-8">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent" />
          </div>
        )}
      </main>
    </div>
  );
}
