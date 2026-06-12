import { createContext, useContext, useMemo, type ReactNode } from 'react';

import { useLeads } from '../hooks/useLeads';
import { useMessages } from '../hooks/useMessages';

type HeliosDataContextValue = {
  messages: ReturnType<typeof useMessages>['messages'];
  msgLoading: ReturnType<typeof useMessages>['loading'];
  msgError: ReturnType<typeof useMessages>['error'];
  unreadCount: ReturnType<typeof useMessages>['unreadCount'];
  fetchMessages: ReturnType<typeof useMessages>['fetchMessages'];
  markRead: ReturnType<typeof useMessages>['markRead'];
  deleteMessage: ReturnType<typeof useMessages>['deleteMessage'];
  leads: ReturnType<typeof useLeads>['leads'];
  leadLoading: ReturnType<typeof useLeads>['loading'];
  leadError: ReturnType<typeof useLeads>['error'];
  leadDetail: ReturnType<typeof useLeads>['leadDetail'];
  detailLoading: ReturnType<typeof useLeads>['detailLoading'];
  fetchLeads: ReturnType<typeof useLeads>['fetchLeads'];
  fetchLeadDetail: ReturnType<typeof useLeads>['fetchLeadDetail'];
  updateState: ReturnType<typeof useLeads>['updateState'];
  hotCount: number;
  warmCount: number;
};

const HeliosDataContext = createContext<HeliosDataContextValue | null>(null);

export function HeliosDataProvider({ children }: Readonly<{ children: ReactNode }>) {
  const { messages, loading: msgLoading, error: msgError, unreadCount, fetchMessages, markRead, deleteMessage } = useMessages();
  const { leads, loading: leadLoading, error: leadError, leadDetail, detailLoading, fetchLeads, fetchLeadDetail, updateState } = useLeads();

  const hotCount = leads.filter((lead) => lead.score >= 8).length;
  const warmCount = leads.filter((lead) => lead.score >= 5 && lead.score < 8).length;
  const value = useMemo(
    () => ({
      messages,
      msgLoading,
      msgError,
      unreadCount,
      fetchMessages,
      markRead,
      deleteMessage,
      leads,
      leadLoading,
      leadError,
      leadDetail,
      detailLoading,
      fetchLeads,
      fetchLeadDetail,
      updateState,
      hotCount,
      warmCount,
    }),
    [
      messages,
      msgLoading,
      msgError,
      unreadCount,
      fetchMessages,
      markRead,
      deleteMessage,
      leads,
      leadLoading,
      leadError,
      leadDetail,
      detailLoading,
      fetchLeads,
      fetchLeadDetail,
      updateState,
      hotCount,
      warmCount,
    ],
  );

  return (
    <HeliosDataContext.Provider value={value}>
      {children}
    </HeliosDataContext.Provider>
  );
}

export function useHeliosData() {
  const context = useContext(HeliosDataContext);

  if (!context) {
    throw new Error('useHeliosData must be used within HeliosDataProvider');
  }

  return context;
}