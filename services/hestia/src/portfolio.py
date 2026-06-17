"""Portfolio holdings and yfinance integration for Hestia."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from functools import lru_cache
import time

import yfinance as yf

from models import PortfolioHolding, PortfolioResponse

# Holdings — ticker → shares mapping. Add more here to expand.
HOLDINGS: dict[str, float] = {
    "GLE.PA": 710,  # Société Générale
}


# Simple in-memory cache (5 min TTL)
_cache: dict[str, tuple[float, PortfolioResponse]] = {}
_CACHE_TTL = 300  # seconds


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_holdings() -> PortfolioResponse:
    """Fetch portfolio data from yfinance, with 5-min caching."""
    cache_key = "portfolio"
    now_ts = time.time()

    if cache_key in _cache:
        cached_at, cached = _cache[cache_key]
        if now_ts - cached_at < _CACHE_TTL:
            return cached

    tickers = list(HOLDINGS.keys())
    yf_tickers = yf.Tickers(" ".join(tickers))

    holdings: list[PortfolioHolding] = []
    total_value = 0.0
    total_pnl = 0.0
    market_open = None

    for ticker in tickers:
        shares = HOLDINGS[ticker]
        t = yf_tickers.tickers.get(ticker)
        if t is None:
            continue

        info = t.info or {}
        name = info.get("longName") or info.get("shortName") or ticker
        price = info.get("currentPrice") or info.get("regularMarketPrice") or 0.0
        prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose") or price
        change_dollar = price - prev_close
        change_pct = round((change_dollar / prev_close) * 100, 2) if prev_close else 0.0
        total = round(shares * price, 2)
        pnl = round(shares * change_dollar, 2)

        total_value += total
        total_pnl += pnl

        if market_open is None:
            market_open = info.get("marketState") == "REGULAR"

        holdings.append(PortfolioHolding(
            ticker=ticker,
            name=name,
            shares=shares,
            price=round(price, 2),
            change_pct=round(change_pct, 2),
            change_dollar=round(change_dollar, 2),
            total_value=total,
            total_pnl=pnl,
        ))

    result = PortfolioResponse(
        holdings=holdings,
        total_value=round(total_value, 2),
        total_pnl=round(total_pnl, 2),
        updated_at=_now(),
        market_open=market_open,
    )

    _cache[cache_key] = (now_ts, result)
    return result


async def get_portfolio() -> PortfolioResponse:
    """Async wrapper — runs yfinance in a thread to avoid blocking the event loop."""
    return await asyncio.to_thread(_get_holdings)
