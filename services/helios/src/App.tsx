import { useEffect, type ReactNode } from 'react';
import { NavLink, Navigate, useLocation, useMatch } from 'react-router-dom';

import { useHeliosData } from './context/HeliosDataContext';
import { getPageTitle } from './lib/helios';
import type { Lead, Message, ViewState } from './lib/types';
import { DashboardPage } from './pages/DashboardPage';
import { LeadDetailPage } from './pages/LeadDetailPage';
import { LeadsPage } from './pages/LeadsPage';
import { MessageDetailPage } from './pages/MessageDetailPage';
import { MessagesPage } from './pages/MessagesPage';

function getViewFromPath(pathname: string, messageId?: string, leadId?: string): ViewState {
  if (pathname === '/messages') return { tab: 'messages' };
  if (pathname === '/leads') return { tab: 'leads' };
  if (messageId) return { tab: 'message-detail', messageId };
  if (leadId) return { tab: 'lead-detail', leadId };
  return { tab: 'dashboard' };
}

function LoadingIndicator() {
  return (
    <div className="flex items-center justify-center py-16">
      <div className="h-6 w-6 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent" />
    </div>
  );
}

function getPageTabs(unreadCount: number, hotCount: number) {
  return [
    {
      key: 'dashboard' as const,
      label: 'Overview',
      description: 'High-level system status',
      to: '/',
      badge: undefined,
    },
    {
      key: 'messages' as const,
      label: 'Inbox',
      description: 'Message triage and follow-up',
      to: '/messages',
      badge: unreadCount > 0 ? unreadCount : undefined,
    },
    {
      key: 'leads' as const,
      label: 'Pipeline',
      description: 'Qualified prospects and urgency',
      to: '/leads',
      badge: hotCount > 0 ? hotCount : undefined,
    },
  ];
}

function getPrimaryContent(pathname: string): ReactNode {
  if (pathname === '/') {
    return <DashboardPage />;
  }

  if (pathname === '/messages') {
    return <MessagesPage />;
  }

  if (pathname === '/leads') {
    return <LeadsPage />;
  }

  return <Navigate to="/" replace />;
}

function getMainContent({
  messageDetailMatch,
  leadDetailMatch,
  selectedMessage,
  selectedLead,
  msgLoading,
  detailLoading,
  primaryContent,
}: Readonly<{
  messageDetailMatch: ReturnType<typeof useMatch>;
  leadDetailMatch: ReturnType<typeof useMatch>;
  selectedMessage: Message | null;
  selectedLead: Lead | null;
  msgLoading: boolean;
  detailLoading: boolean;
  primaryContent: ReactNode;
}>): ReactNode {
  if (messageDetailMatch) {
    if (selectedMessage) {
      return <MessageDetailPage message={selectedMessage} />;
    }

    return msgLoading ? <LoadingIndicator /> : <Navigate to="/messages" replace />;
  }

  if (leadDetailMatch) {
    if (selectedLead) {
      return <LeadDetailPage lead={selectedLead} />;
    }

    return detailLoading ? <LoadingIndicator /> : <Navigate to="/leads" replace />;
  }

  return primaryContent;
}

export default function App() {
  const { messages, msgLoading, unreadCount, leads, leadDetail, detailLoading, fetchLeadDetail, hotCount } = useHeliosData();
  const location = useLocation();
  const messageDetailMatch = useMatch('/messages/:messageId');
  const leadDetailMatch = useMatch('/leads/:leadId');

  const currentView = getViewFromPath(
    location.pathname,
    messageDetailMatch?.params.messageId,
    leadDetailMatch?.params.leadId,
  );
  const selectedMessage = messageDetailMatch?.params.messageId
    ? messages.find((message: Message) => message.id === messageDetailMatch.params.messageId) ?? null
    : null;
  const selectedLead = leadDetailMatch?.params.leadId
    ? (leadDetail || leads.find((lead: Lead) => lead.id === leadDetailMatch.params.leadId) || null)
    : null;

  const isMessagesRoute = location.pathname === '/messages' || Boolean(messageDetailMatch);
  const isLeadsRoute = location.pathname === '/leads' || Boolean(leadDetailMatch);
  const isKnownRoute = location.pathname === '/' || isMessagesRoute || isLeadsRoute;

  useEffect(() => {
    const leadId = leadDetailMatch?.params.leadId;
    if (leadId) {
      fetchLeadDetail(leadId);
    }
  }, [fetchLeadDetail, leadDetailMatch]);

  const isDetailView = Boolean(messageDetailMatch || leadDetailMatch);
  const pageTitle = getPageTitle(currentView.tab);
  const pageDescription = isDetailView
    ? 'Review a single record with full context, then step back into the larger workflow when needed.'
    : 'The app is split into overview, inbox, and pipeline sections so navigation stays stable as the data changes.';

  const pageTabs = getPageTabs(unreadCount, hotCount);
  const primaryContent = getPrimaryContent(location.pathname);
  const mainContent = getMainContent({
    messageDetailMatch,
    leadDetailMatch,
    selectedMessage,
    selectedLead,
    msgLoading,
    detailLoading,
    primaryContent,
  });

  return (
    <div className="flex min-h-screen bg-[radial-gradient(circle_at_top,rgba(14,165,233,0.16),transparent_24%),linear-gradient(180deg,#020617_0%,#020617_42%,#111827_100%)] text-gray-100">
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
          <NavLink
            to="/"
            end
            className={({ isActive }) => `flex items-center gap-3 rounded-xl px-4 py-3 text-sm transition ${
              isActive ? 'bg-cyan-600/20 text-cyan-300 ring-1 ring-cyan-500/30' : 'text-gray-400 hover:bg-gray-900 hover:text-gray-200'
            }`}
          >
            <span>📊</span>
            <div className="flex flex-col items-start">
              <span>Overview</span>
              <span className="text-xs text-gray-500">Metrics and recent movement</span>
            </div>
          </NavLink>

          <NavLink
            to="/messages"
            className={({ isActive }) => `flex items-center justify-between rounded-xl px-4 py-3 text-sm transition ${
              isActive ? 'bg-cyan-600/20 text-cyan-300 ring-1 ring-cyan-500/30' : 'text-gray-400 hover:bg-gray-900 hover:text-gray-200'
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
          </NavLink>

          <NavLink
            to="/leads"
            className={({ isActive }) => `flex items-center justify-between rounded-xl px-4 py-3 text-sm transition ${
              isActive ? 'bg-cyan-600/20 text-cyan-300 ring-1 ring-cyan-500/30' : 'text-gray-400 hover:bg-gray-900 hover:text-gray-200'
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
          </NavLink>
        </nav>

        <div className="mt-auto rounded-2xl border border-gray-800 bg-gray-900/50 p-4 text-sm text-gray-400">
          <p className="font-medium text-gray-200">Workflow split</p>
          <p className="mt-2">Use the sidebar for workspace navigation and the page header for section-level movement inside the current screen.</p>
        </div>
      </aside>

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
                    <NavLink
                      key={tab.key}
                      to={tab.to}
                      end={tab.key === 'dashboard'}
                      className={({ isActive }) => `rounded-2xl border px-4 py-3 text-left transition ${
                        isActive
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
                    </NavLink>
                  ))}
                </div>
              )}
            </div>
          </header>

          {isKnownRoute ? mainContent : <Navigate to="/" replace />}
        </div>
      </main>
    </div>
  );
}
