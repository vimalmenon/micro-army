import type { ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';

import { DashboardSection } from '../components/DashboardSection';
import { useHeliosData } from '../context/HeliosDataContext';
import { formatTime, scoreColor, sourceIcon, stateColor, urgencyColor } from '../lib/helios';
import type { Lead } from '../lib/types';

export function LeadsPage({
  leads,
}: Readonly<{
  leads?: Lead[];
}>) {
  const navigate = useNavigate();
  const { leads: allLeads, leadLoading, leadError, fetchLeads } = useHeliosData();
  const visibleLeads = leads ?? allLeads;
  let content: ReactNode;

  if (leadLoading) {
    content = (
      <div className="flex items-center justify-center py-16">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent" />
      </div>
    );
  } else if (leadError) {
    content = <div className="rounded-xl border border-red-500/20 bg-red-500/5 px-5 py-8 text-center text-sm text-red-300">{leadError}</div>;
  } else if (visibleLeads.length === 0) {
    content = <div className="rounded-xl border border-gray-800 bg-gray-950/40 px-5 py-8 text-center text-sm text-gray-500">No leads yet. Pythia runs daily at 12:00 HKT.</div>;
  } else {
    content = (
      <div className="space-y-3">
        {visibleLeads.map((lead) => (
          <button
            key={lead.id}
            onClick={() => navigate(`/leads/${lead.id}`)}
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
          onClick={fetchLeads}
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