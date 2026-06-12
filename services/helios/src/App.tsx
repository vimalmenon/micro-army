import { useEffect, useState, type ReactNode } from 'react';

import { useLeads } from './hooks/useLeads';
import { useMessages } from './hooks/useMessages';
import { getPageTitle } from './lib/helios';
import type { ViewState } from './lib/types';
import { DashboardPage } from './pages/DashboardPage';
import { LeadDetailPage } from './pages/LeadDetailPage';
import { LeadsPage } from './pages/LeadsPage';
import { MessageDetailPage } from './pages/MessageDetailPage';
import { MessagesPage } from './pages/MessagesPage';

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
  }, []);

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
        <DashboardPage
          messages={messages}
          msgLoading={msgLoading}
          msgError={msgError}
          leads={leads}
          leadLoading={leadLoading}
          leadError={leadError}
          unreadCount={unreadCount}
          hotCount={hotCount}
          warmCount={warmCount}
          onRefreshMessages={fetchMessages}
          onRefreshLeads={fetchLeads}
          onOpenMessage={(id) => setView({ tab: 'message-detail', messageId: id })}
          onDeleteMessage={handleDelete}
          onOpenLead={(id) => setView({ tab: 'lead-detail', leadId: id })}
        />
      );
    }

    if (view.tab === 'messages') {
      return (
        <MessagesPage
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
      <LeadsPage
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
      <MessageDetailPage
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
      <LeadDetailPage
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
