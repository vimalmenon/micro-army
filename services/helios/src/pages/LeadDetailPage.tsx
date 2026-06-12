import { useNavigate } from 'react-router-dom';

import { useHeliosData } from '../context/HeliosDataContext';
import { LEAD_STATES, formatDate, formatTime, scoreColor, sourceIcon, stateColor, urgencyColor } from '../lib/helios';
import type { Lead } from '../lib/types';

export function LeadDetailPage({
  lead,
}: Readonly<{
  lead: Lead;
}>) {
  const navigate = useNavigate();
  const { updateState } = useHeliosData();

  return (
    <div className="space-y-6">
      <button
        onClick={() => navigate('/leads')}
        className="flex items-center gap-2 text-sm text-gray-400 transition hover:text-gray-200"
      >
        ← Leads
      </button>

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

      <div className="rounded-xl border border-gray-800 bg-gray-900/40 p-5">
        <div className="mb-2 text-xs font-medium uppercase tracking-wide text-gray-500">Change State</div>
        <div className="flex flex-wrap gap-2">
          {LEAD_STATES.map((state) => (
            <button
              key={state}
              onClick={() => updateState(lead.id, state)}
              className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${
                lead.state === state
                  ? 'bg-cyan-600/30 text-cyan-400 ring-1 ring-cyan-500/50'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-gray-200'
              }`}
            >
              {state}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="rounded-xl border border-gray-800 bg-gray-900/40 p-5">
          <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-gray-500">Pain Point</h3>
          <p className="text-sm text-gray-300">{lead.pain_point}</p>
        </div>
        <div className="rounded-xl border border-gray-800 bg-gray-900/40 p-5">
          <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-gray-500">Fit Reason</h3>
          <p className="text-sm text-gray-300">{lead.fit_reason}</p>
        </div>
      </div>

      {lead.angle && (
        <div className="rounded-xl border border-gray-800 bg-gray-900/40 p-5">
          <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-gray-500">Suggested Angle</h3>
          <p className="text-sm italic text-gray-400">{lead.angle}</p>
        </div>
      )}

      <div className="rounded-xl border border-gray-800 bg-gray-900/40 p-5">
        <h3 className="mb-3 text-xs font-medium uppercase tracking-wide text-gray-500">
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

      {lead.history.length > 1 && (
        <div className="rounded-xl border border-gray-800 bg-gray-900/40 p-5">
          <h3 className="mb-3 text-xs font-medium uppercase tracking-wide text-gray-500">State History</h3>
          <div className="space-y-1">
            {lead.history.map((historyItem) => (
              <div key={`${historyItem.state}-${historyItem.at}`} className="flex items-center gap-3 text-xs">
                <span className={`rounded px-2 py-0.5 ${stateColor(historyItem.state)}`}>{historyItem.state}</span>
                <span className="text-gray-600">{formatDate(historyItem.at)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}