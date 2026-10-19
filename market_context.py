"""BTC + market context for the daily brief (user request 2026-10-19).

"A trader looks at BTC first: trend, volume, candles, who got liquidated." Everything here is
read from data the scan already has (the snapshot's tickers + multi-TF indicators + the momentum
pulse's breadth metrics) plus ONE extra public call (BTC open interest, 1h, last 25 points) and
the committed liquidation summary (`liq_summary.py`). Description only: nothing in this module
changes which trades are picked or how they are scored. Every field degrades to None.
"""

import time

import config
import liq_summary

BTC = "BTCUSDT"


def _find(rows, sym):
    return next((r for r in rows or [] if r.get("symbol") == sym), None)


def _oi_change_24h(fetcher, symbol=BTC):
    """% change of open interest over the last 24h (25 hourly points), or None."""
    if fetcher is None:
        return None
    try:
        res = fetcher._api("get_open_interest", category=config.BYBIT_CATEGORY, symbol=symbol,
                           intervalTime="1h", limit=25)
        pts = res["result"]["list"]          # newest first
        new, old = float(pts[0]["openInterest"]), float(pts[-1]["openInterest"])
        return round((new / old - 1) * 100, 2) if old else None
    except Exception as e:
        print(f"  context: open-interest fetch failed ({type(e).__name__}: {e})")
        return None


def build(market, fetcher=None, now_ms=None):
    now_ms = now_ms or int(time.time() * 1000)
    tick = _find(market.get("top_movers"), BTC) or {}
    tech = (_find(market.get("technicals"), BTC) or {}).get("timeframes", {})
    d1, h4 = tech.get("1D") or {}, tech.get("4h") or {}
    regime = market.get("market_regime") or {}
    metrics = regime.get("metrics") or {}

    liq24 = liq_summary.window(liq_summary.load_summary(), now_ms, 24)
    liq4 = liq_summary.window(liq_summary.load_summary(), now_ms, 4)
    btc24 = liq24["by_symbol"].get(BTC) or [0.0, 0.0]

    return {
        "price": tick.get("last_price") or h4.get("current_price"),
        "chg_24h": tick.get("price_change_24h_pct"),
        "turnover_24h": tick.get("turnover_24h_usd"),
        "funding_pct": tick.get("funding_rate_pct"),
        "oi_chg_24h": _oi_change_24h(fetcher),
        "trend_1d": d1.get("trend"), "trend_4h": h4.get("trend"),
        "rsi_1d": d1.get("rsi_14"), "adx_1d": d1.get("adx_14"),
        "vol_ratio_1d": d1.get("volume_spike_ratio"),        # yesterday's volume vs its 20-day average
        "prev_high": d1.get("last_high"), "prev_low": d1.get("last_low"),
        "high_20d": d1.get("high_20"), "low_20d": d1.get("low_20"),
        "regime": regime.get("regime"),
        "pct_declining": metrics.get("pct_declining"),
        "median_chg": metrics.get("median_change_pct"),
        "liq_hours_covered": liq24["covered_hours"],
        "liq_long_24h": liq24["total"][0], "liq_short_24h": liq24["total"][1],
        "liq_long_4h": liq4["total"][0], "liq_short_4h": liq4["total"][1],
        "liq_btc_long_24h": btc24[0], "liq_btc_short_24h": btc24[1],
        "liq_coins": len(liq24["by_symbol"]),
    }
