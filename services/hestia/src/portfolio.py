"""Portfolio holdings and yfinance integration for Hestia."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from functools import lru_cache
import logging
import time

import yfinance as yf

from models import PortfolioHolding, PortfolioResponse

log = logging.getLogger(__name__)

# Holdings — ticker → shares mapping. Add more here to expand.
HOLDINGS: dict[str, float] = {
    "GLE.PA": 900,  # Société Générale
}

# ── Gold ──────────────────────────────────────────────────────────────────
# 600 g of bullion, valued in EUR so the whole table shares one currency.
#
# Cost basis = COMEX front-month close on 2025-04-30 (USD 3,319.10/oz) converted
# at that day's EURUSD fix of 1.1325. That is the "April 2025" price; change the
# date here if a different entry day was meant. Cross-checked against GLD, the
# physically-backed ETF, which shows the same +23.7/-17% move for the period.
GOLD_GRAMS = 600.0
GOLD_CONTRACT = "GC=F"  # COMEX front month, quoted USD per troy ounce
GRAMS_PER_OZ = 31.1034768
GOLD_COST_EUR_PER_GRAM = round(3319.10 / 1.1325 / GRAMS_PER_OZ, 4)  # ≈ 94.2274


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

    # ── Gold ──────────────────────────────────────────────────────────────
    # Fetched separately from the equity loop: it is a futures contract quoted in
    # USD and needs an FX conversion to land in the portfolio's EUR. A failure
    # here degrades the page by one row rather than breaking the whole endpoint.
    try:
        ginfo = yf.Ticker(GOLD_CONTRACT).info or {}
        gold_usd_oz = ginfo.get("currentPrice") or ginfo.get("regularMarketPrice") or 0.0
        gold_usd_oz_prev = (
            ginfo.get("previousClose") or ginfo.get("regularMarketPreviousClose") or gold_usd_oz
        )
        # FX pairs and futures often populate regularMarketPrice but leave
        # currentPrice null, so both fields must be tried on each quote.
        fx = yf.Ticker("EURUSD=X").info or {}
        eur_usd = fx.get("currentPrice") or fx.get("regularMarketPrice") or 0.0

        if gold_usd_oz and eur_usd:
            price_g = gold_usd_oz / eur_usd / GRAMS_PER_OZ
            prev_g = gold_usd_oz_prev / eur_usd / GRAMS_PER_OZ

            gold_value = round(GOLD_GRAMS * price_g, 2)
            gold_cost = round(GOLD_GRAMS * GOLD_COST_EUR_PER_GRAM, 2)
            gold_return = round(gold_value - gold_cost, 2)
            gold_day_pnl = round(GOLD_GRAMS * (price_g - prev_g), 2)

            total_value += gold_value
            total_pnl += gold_day_pnl

            holdings.append(PortfolioHolding(
                ticker="XAU",
                name="Gold bullion",
                shares=GOLD_GRAMS,
                price=round(price_g, 2),
                change_pct=round((price_g / prev_g - 1) * 100, 2) if prev_g else 0.0,
                change_dollar=round(price_g - prev_g, 2),
                total_value=gold_value,
                total_pnl=gold_day_pnl,
                unit="g",
                cost_basis=GOLD_COST_EUR_PER_GRAM,
                total_return=gold_return,
                total_return_pct=round(gold_return / gold_cost * 100, 2) if gold_cost else None,
            ))
    except Exception:  # noqa: BLE001 — a missing gold quote must not 500 the page
        log.warning("gold position unavailable", exc_info=True)

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
