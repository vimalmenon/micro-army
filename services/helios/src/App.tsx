import { useCallback, useEffect, useState } from 'react';

const API_BASE = 'https://messages.completeautomate.com';

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

function getAuthHeaders(): Record<string, string> {
  const stored = sessionStorage.getItem('helios_auth');
  if (stored) {
    const parsed = JSON.parse(stored);
    return { Authorization: `Basic ${btoa(`${parsed.user}:${parsed.pass}`)}` };
  }
  return {};
}

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
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
      });
      if (resp.status === 401 || resp.status === 403) {
        setError('auth');
        setLoading(false);
        return;
      }
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
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
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
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
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

function LoginForm({ onLogin }: { onLogin: (user: string, pass: string) => void }) {
  const [user, setUser] = useState('');
  const [pass, setPass] = useState('');

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-sm rounded-2xl border border-gray-800 bg-gray-900/80 p-8 backdrop-blur">
        <div className="mb-6 text-center">
          <div className="text-4xl">☀️</div>
          <h1 className="mt-3 text-xl font-bold">Helios</h1>
          <p className="mt-1 text-sm text-gray-400">Admin Dashboard</p>
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            onLogin(user, pass);
          }}
          className="space-y-4"
        >
          <input
            className="w-full rounded-lg border border-gray-700 bg-gray-800/50 px-4 py-2.5 text-sm text-gray-100 placeholder-gray-500 outline-none focus:border-cyan-500"
            placeholder="Username"
            value={user}
            onChange={(e) => setUser(e.target.value)}
          />
          <input
            className="w-full rounded-lg border border-gray-700 bg-gray-800/50 px-4 py-2.5 text-sm text-gray-100 placeholder-gray-500 outline-none focus:border-cyan-500"
            type="password"
            placeholder="Password"
            value={pass}
            onChange={(e) => setPass(e.target.value)}
          />
          <button
            type="submit"
            className="w-full rounded-lg bg-cyan-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-cyan-500"
          >
            Sign In
          </button>
        </form>
      </div>
    </div>
  );
}

function MessageDetail({
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
        ← Back to Messages
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
            <span className="text-xs text-gray-500">{formatTime(message.created_at)}</span>
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

export default function App() {
  const [authed, setAuthed] = useState(() => !!sessionStorage.getItem('helios_auth'));
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const { messages, loading, error, unreadCount, fetchMessages, markRead, deleteMessage } = useMessages();

  const handleLogin = (user: string, pass: string) => {
    sessionStorage.setItem('helios_auth', JSON.stringify({ user, pass }));
    setAuthed(true);
  };

  const handleLogout = () => {
    sessionStorage.removeItem('helios_auth');
    setAuthed(false);
  };

  if (!authed || error === 'auth') {
    return <LoginForm onLogin={handleLogin} />;
  }

  const selected = selectedId ? messages.find((m) => m.id === selectedId) : null;

  const handleDelete = (id: string) => {
    deleteMessage(id);
    if (selectedId === id) setSelectedId(null);
  };

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
            onClick={() => setSelectedId(null)}
            className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition ${
              !selectedId ? 'bg-cyan-600/20 text-cyan-400' : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            <span>📊</span>
            <span>Dashboard</span>
          </button>
          <button
            onClick={() => setSelectedId(null)}
            className={`flex items-center justify-between rounded-lg px-3 py-2 text-sm transition ${
              !selectedId ? 'bg-cyan-600/20 text-cyan-400' : 'text-gray-400 hover:text-gray-200'
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
        </nav>
        <div className="mt-auto">
          <button
            onClick={handleLogout}
            className="w-full rounded-lg px-3 py-2 text-left text-sm text-gray-500 transition hover:text-gray-300"
          >
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-y-auto p-6">
        {selected ? (
          <MessageDetail
            message={selected}
            onBack={() => setSelectedId(null)}
            onMarkRead={(id) => {
              markRead(id);
              setSelectedId(null);
            }}
            onDelete={handleDelete}
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
            </div>

            {/* Messages Table */}
            <div className="rounded-xl border border-gray-800 bg-gray-900/40">
              <div className="flex items-center justify-between border-b border-gray-800 px-5 py-3">
                <h2 className="text-sm font-bold tracking-wide text-gray-300 uppercase">
                  Messages
                </h2>
                <button
                  onClick={fetchMessages}
                  className="rounded-md bg-gray-800 px-3 py-1.5 text-xs text-gray-400 transition hover:text-gray-200"
                >
                  Refresh
                </button>
              </div>

              {loading ? (
                <div className="flex items-center justify-center py-16">
                  <div className="h-6 w-6 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent" />
                </div>
              ) : error ? (
                <div className="px-5 py-8 text-center text-sm text-red-400">{error}</div>
              ) : messages.length === 0 ? (
                <div className="px-5 py-8 text-center text-sm text-gray-500">
                  No messages yet.
                </div>
              ) : (
                <div className="divide-y divide-gray-800/50">
                  {messages.map((msg) => (
                    <div
                      key={msg.id}
                      className="flex w-full items-center gap-4 px-5 py-3.5 transition hover:bg-gray-800/40"
                    >
                      <button
                        onClick={() => setSelectedId(msg.id)}
                        className="flex min-w-0 flex-1 items-center gap-4 text-left"
                      >
                        <div
                          className={`h-2 w-2 shrink-0 rounded-full ${
                            msg.read ? 'bg-transparent' : 'bg-cyan-500'
                          }`}
                        />
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-3">
                            <span className="truncate text-sm font-medium text-gray-200">
                              {msg.name}
                            </span>
                            <span className="truncate text-xs text-gray-500">{msg.subject}</span>
                          </div>
                          <p className="mt-0.5 truncate text-xs text-gray-600">{msg.message}</p>
                        </div>
                        <span className="shrink-0 text-xs text-gray-600">
                          {formatTime(msg.created_at)}
                        </span>
                      </button>
                      <button
                        onClick={() => {
                          if (window.confirm(`Delete message from ${msg.name}?`)) {
                            handleDelete(msg.id);
                          }
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
          </div>
        )}
      </main>
    </div>
  );
}
