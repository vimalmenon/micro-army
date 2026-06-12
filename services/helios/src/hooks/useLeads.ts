import { useCallback, useEffect, useState } from 'react';

import { API_BASE } from '../lib/helios';
import type { Lead } from '../lib/types';

export function useLeads() {
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

  const fetchLeadDetail = useCallback(async (id: string) => {
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
  }, []);

  const updateState = async (id: string, newState: string) => {
    try {
      const resp = await fetch(`${API_BASE}/leads/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ state: newState }),
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      setLeads((prev) =>
        prev.map((lead) => (lead.id === id ? { ...lead, state: newState } : lead))
      );
      setLeadDetail((prev) => (prev?.id === id ? { ...prev, state: newState } : prev));
    } catch (e) {
      console.error('Failed to update lead state', e);
    }
  };

  return { leads, loading, error, leadDetail, detailLoading, fetchLeads, fetchLeadDetail, updateState };
}