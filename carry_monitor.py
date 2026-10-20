"""Carry line for the Monday weekly review (user request 2026-10-19 night).

Cash-and-carry = hold the coin spot and short the same amount of perp (or of a dated future), so
price moves cancel and the position earns the funding (or the basis, locked if held to expiry).
This module only DESCRIBES what that pays on Bybit right now: BTC and ETH perp funding over the
last 7 and 30 days, and each coin's next quarterly USDT future held to expiry, against a stated
round-trip fee. Nothing here picks or scores a trade; every field degrades to None. Evidence and
risks: research/edge_sources_20261019.md §7.
"""

import time
from datetime import datetime, timezone

SYMBOLS = ("BTCUSDT", "ETHUSDT")
QUARTER_MONTHS = (3, 6, 9, 12)
MIN_DAYS_TO_EXPIRY = 30
THIN_TURNOVER_USD = 5e6
# Bybit non-VIP fees, open + close of both legs: spot 0.10% each way, perp/futures taker 0.055% each way
ROUND_TRIP_PCT = 2 * (0.10 + 0.055)
DAY_MS = 86_400_000


def funding_apr(rows, now_ms, days):
    """Annualised % paid to a short by the settlements [(ts_ms, rate)] of the last `days` days, or None."""
    sel = [rate for ts, rate in rows if now_ms - days * DAY_MS < ts <= now_ms]
    return round(sum(sel) * 365 / days * 100, 2) if sel else None


def next_quarterly(instruments, coin, now_ms):
    """The coin's nearest quarterly USDT future with >= MIN_DAYS_TO_EXPIRY days left: (symbol, delivery_ms) or None."""
    best = None
    for x in instruments:
        if x.get("contractType") != "LinearFutures" or x.get("baseCoin") != coin or x.get("quoteCoin") != "USDT":
            continue
        dms = int(x.get("deliveryTime") or 0)
        exp = datetime.fromtimestamp(dms / 1000, tz=timezone.utc)
        if exp.month in QUARTER_MONTHS and dms - now_ms >= MIN_DAYS_TO_EXPIRY * DAY_MS:
            if best is None or dms < best[1]:
                best = (x["symbol"], dms)
    return best


def basis_apr(mark, index, delivery_ms, now_ms):
    """Annualised % the future trades above the index, earned by a short held to expiry."""
    days = (delivery_ms - now_ms) / DAY_MS
    return round((mark / index - 1) * 365 / days * 100, 2) if index and days > 0 else None


def fetch(fetcher, now_ms=None):
    """{'funding': {sym: {'apr_7d', 'apr_30d'}}, 'quarterly': {coin: {...}}} from public endpoints; parts that fail are None."""
    now_ms = now_ms or int(time.time() * 1000)
    out = {"funding": {}, "quarterly": {}}
    for sym in SYMBOLS:
        try:
            res = fetcher._api("get_funding_rate_history", category="linear", symbol=sym,
                               startTime=now_ms - 30 * DAY_MS, endTime=now_ms, limit=200)
            rows = [(int(r["fundingRateTimestamp"]), float(r["fundingRate"])) for r in res["result"]["list"]]
            out["funding"][sym] = {"apr_7d": funding_apr(rows, now_ms, 7), "apr_30d": funding_apr(rows, now_ms, 30)}
        except Exception as e:
            print(f"  carry: {sym} funding fetch failed ({type(e).__name__}: {e})")
            out["funding"][sym] = None
    for sym in SYMBOLS:
        coin = sym[:-4]
        try:
            inst = fetcher._api("get_instruments_info", category="linear", baseCoin=coin, limit=100)["result"]["list"]
            q = next_quarterly(inst, coin, now_ms)
            if q is None:
                out["quarterly"][coin] = None
                continue
            t = fetcher._api("get_tickers", category="linear", symbol=q[0])["result"]["list"][0]
            out["quarterly"][coin] = {
                "symbol": q[0], "days": int((q[1] - now_ms) / DAY_MS),
                "apr": basis_apr(float(t["markPrice"]), float(t["indexPrice"]), q[1], now_ms),
                "turnover_24h": float(t.get("turnover24h") or 0)}
        except Exception as e:
            print(f"  carry: {coin} quarterly fetch failed ({type(e).__name__}: {e})")
            out["quarterly"][coin] = None
    return out


def _pct(v):
    return "n/a" if v is None else f"{v:.1f}%"


def format_lines(data):
    """Markdown block for the weekly review. `data` = fetch() output, or None when it could not run."""
    L = ["## Carry — cash-and-carry yield on Bybit (description only, not a trade)",
         "_Hold the coin spot and short the same amount of perp or quarterly future: price moves cancel and the "
         "position earns the funding or basis. Evidence and risks: `research/edge_sources_20261019.md` §7._"]
    if not data:
        L.append("- Data unavailable this week (Bybit fetch failed).")
        return L
    for sym in SYMBOLS:
        f = (data.get("funding") or {}).get(sym)
        L.append(f"- {sym[:-4]} perp funding paid to shorts, a year: last 7 days {_pct(f['apr_7d'])} · "
                 f"last 30 days {_pct(f['apr_30d'])}" if f else f"- {sym[:-4]} perp funding: n/a")
    for coin in (s[:-4] for s in SYMBOLS):
        q = (data.get("quarterly") or {}).get(coin)
        if q:
            to = q["turnover_24h"]
            to_s = f"${to / 1e6:.1f}M" if to >= 1e6 else f"${to / 1e3:.0f}k"
            thin = " — thin, use limit orders" if to < THIN_TURNOVER_USD else ""
            L.append(f"- {coin} quarterly `{q['symbol']}` ({q['days']} days to expiry): basis {_pct(q['apr'])} a year, "
                     f"locked if held to expiry · 24h turnover {to_s}{thin}")
        else:
            L.append(f"- {coin} quarterly: n/a")
    btc = (data.get("funding") or {}).get("BTCUSDT") or {}
    apr30 = btc.get("apr_30d")
    if apr30 is not None and apr30 > 0:
        cover = f" ≈ {ROUND_TRIP_PCT / (apr30 / 52):.0f} weeks of BTC's 30-day funding"
    elif apr30 is not None:
        cover = " — BTC funding is negative: holding the perp short currently costs money"
    else:
        cover = ""
    L.append(f"- Round trip ≈ {ROUND_TRIP_PCT:.2f}% of notional (spot 0.10% + perp 0.055% taker, in and out){cover}")
    L.append("- Risks: exchange failure or hack (both legs sit on Bybit), auto-deleveraging of the short in a crash, "
             "funding turning negative.")
    return L
