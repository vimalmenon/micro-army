import type { ReactNode } from 'react';

import { DashboardSection } from '../components/DashboardSection';
import { formatDate, formatTime } from '../lib/helios';
import type { Message } from '../lib/types';

export function MessagesPage({
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
        {messages.map((message) => (
          <div
            key={message.id}
            className="flex flex-col gap-4 rounded-2xl border border-gray-800/80 bg-gray-950/55 p-4 transition hover:border-gray-700 hover:bg-gray-950/80 lg:flex-row lg:items-center"
          >
            <button
              onClick={() => onOpen(message.id)}
              className="flex min-w-0 flex-1 items-start gap-4 text-left"
            >
              <div className={`mt-1 h-2.5 w-2.5 shrink-0 rounded-full ${message.read ? 'bg-gray-700' : 'bg-cyan-500'}`} />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                  <span className="truncate text-sm font-medium text-gray-100">{message.name}</span>
                  <span className="truncate text-xs uppercase tracking-[0.16em] text-gray-500">{message.subject}</span>
                </div>
                <p className="mt-2 line-clamp-2 text-sm text-gray-400">{message.message}</p>
              </div>
            </button>
            <div className="flex items-center justify-between gap-3 lg:justify-end">
              <span className="shrink-0 text-right text-xs text-gray-500">
                <div>{formatTime(message.created_at)}</div>
                <div className="text-gray-600">{formatDate(message.created_at)}</div>
              </span>
              <button
                onClick={() => {
                  if (globalThis.confirm(`Delete message from ${message.name}?`)) onDelete(message.id);
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