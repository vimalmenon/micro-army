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

# Optional purchase price per share, ticker → price paid per share. Populate an
# entry to light up the Cost / Invested / Return columns for that holding; leave
# it out and those columns stay blank rather than showing a fabricated basis.
COSTS: dict[str, float] = {
    # "GLE.PA": 0.00,  # ← put the price you actually paid here
}

# ── Gold ──────────────────────────────────────────────────────────────────
# 600 g of bullion, valued in EUR so the whole table shares one currency.
#
# Cost basis = COMEX front-month close on 2025-04-30 (USD 3,319.10/oz) converted
# at THAT SAME DAY's EURUSD close of 1.1389. Both legs must come from the same
# date: an earlier version of this line used the 30 Apr gold price with the 1 May
# FX rate (1.1325), which overstated the basis by EUR 0.53/g — EUR 318 on 600 g.
#
# This is the end-of-April-2025 market price, not a receipt. It is the best
# available anchor for a purchase made "end of April 2025"; if the actual price
# paid is ever known, replace the constant with it.
GOLD_GRAMS = 600.0
GOLD_CONTRACT = "GC=F"  # COMEX front month, quoted USD per troy ounce
GRAMS_PER_OZ = 31.1034768
GOLD_COST_EUR_PER_GRAM = round(3319.10 / 1.1389 / GRAMS_PER_OZ, 4)  # ≈ 93.6970
#   600 g × 93.6970 = EUR 56,218.20 invested


# ── Precious metals ───────────────────────────────────────────────────────
# Both are COMEX futures quoted in USD per troy ounce, so each needs an FX
# conversion to land in the portfolio's EUR. Fetched outside the equity loop so
# a failed metal quote degrades one row instead of 500-ing the whole endpoint.
SILVER_GRAMS = 1000.0  # 1 kg

# (ticker, display name, contract, grams held, cost per gram or None)
# A None cost means the purchase price is unknown — the page shows an em dash
# for Cost, Invested and Return rather than inventing a basis.
METALS: list[tuple[str, str, str, float, float | None]] = [
    ("XAU", "Gold bullion", GOLD_CONTRACT, GOLD_GRAMS, GOLD_COST_EUR_PER_GRAM),
    ("XAG", "Silver bullion", "SI=F", SILVER_GRAMS, None),
]


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

        # Cost basis is optional per ticker — see COSTS above.
        unit_cost = COSTS.get(ticker)
        invested: float | None = None
        gain: float | None = None
        gain_pct: float | None = None
        if unit_cost:
            invested = round(unit_cost * shares, 2)
            gain = round(total - invested, 2)
            gain_pct = round(gain / invested * 100, 2) if invested else None

        total_value += total
        total_pnl += pnl

        if market_open is None:
            market_open = info.get("marketState") == "REGULAR"

        holdings.append(
            PortfolioHolding(
                ticker=ticker,
                name=name,
                shares=shares,
                price=round(price, 2),
                change_pct=round(change_pct, 2),
                change_dollar=round(change_dollar, 2),
                total_value=total,
                total_pnl=pnl,
                cost_basis=unit_cost,
                cost_value=invested,
                total_return=gain,
                total_return_pct=gain_pct,
            )
        )

    # ── Precious metals ───────────────────────────────────────────────────
    # Each metal is its own try/except: a missing silver quote must not remove
    # the gold row, and vice versa.
    try:
        fx = yf.Ticker("EURUSD=X").info or {}
        # FX pairs and futures often populate regularMarketPrice but leave
        # currentPrice null, so both fields must be tried on each quote.
        eur_usd = fx.get("currentPrice") or fx.get("regularMarketPrice") or 0.0
    except Exception:  # noqa: BLE001
        log.warning("EURUSD quote unavailable", exc_info=True)
        eur_usd = 0.0

    for metal_ticker, metal_name, contract, grams, cost_per_g in METALS:
        if not eur_usd:
            break
        try:
            minfo = yf.Ticker(contract).info or {}
            usd_oz = minfo.get("currentPrice") or minfo.get("regularMarketPrice") or 0.0
            usd_oz_prev = (
                minfo.get("previousClose") or minfo.get("regularMarketPreviousClose") or usd_oz
            )
            if not usd_oz:
                log.warning("%s quote empty, skipping", metal_ticker)
                continue

            price_g = usd_oz / eur_usd / GRAMS_PER_OZ
            prev_g = usd_oz_prev / eur_usd / GRAMS_PER_OZ

            metal_value = round(grams * price_g, 2)
            metal_day_pnl = round(grams * (price_g - prev_g), 2)
            # cost_per_g is None where the purchase price is unknown; in that
            # case Cost, Invested and Return all stay null and render as em dashes.
            metal_cost = round(grams * cost_per_g, 2) if cost_per_g else None
            metal_return: float | None = None
            metal_pct: float | None = None
            if metal_cost:
                metal_return = round(metal_value - metal_cost, 2)
                metal_pct = round(metal_return / metal_cost * 100, 2)

            total_value += metal_value
            total_pnl += metal_day_pnl

            holdings.append(
                PortfolioHolding(
                    ticker=metal_ticker,
                    name=metal_name,
                    shares=grams,
                    price=round(price_g, 2),
                    change_pct=round((price_g / prev_g - 1) * 100, 2) if prev_g else 0.0,
                    change_dollar=round(price_g - prev_g, 2),
                    total_value=metal_value,
                    total_pnl=metal_day_pnl,
                    unit="g",
                    cost_basis=cost_per_g,
                    cost_value=metal_cost,
                    total_return=metal_return,
                    total_return_pct=metal_pct,
                )
            )
        except Exception:  # noqa: BLE001 — one metal must not 500 the page
            log.warning("%s position unavailable", metal_ticker, exc_info=True)

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
