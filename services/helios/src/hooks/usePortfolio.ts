import { useCallback, useEffect, useState } from 'react';
import { API_BASE } from '../lib/helios';

export interface PortfolioHolding {
  ticker: string;
  name: string;
  shares: number;
  price: number;
  change_pct: number;
  change_dollar: number;
  total_value: number;
  total_pnl: number;
}

export interface PortfolioData {
  holdings: PortfolioHolding[];
  total_value: number;
  total_pnl: number;
  updated_at: string;
  market_open: boolean | null;
}

export function usePortfolio() {
  const [data, setData] = useState<PortfolioData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPortfolio = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(`${API_BASE}/portfolio`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const json = await resp.json();
      setData(json);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load portfolio');
    }
    setLoading(false);
  }, []);

  useEffect(() => { fetchPortfolio(); }, [fetchPortfolio]);

  return { data, loading, error, refresh: fetchPortfolio };
}
