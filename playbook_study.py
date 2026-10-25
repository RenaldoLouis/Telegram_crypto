"""Daily trader's playbook study (2026-10-25) — pre-registered, research-only.

The user asked to set the screener aside and test, the way a daily trader would, which classic
strategies make money month after month on old Bybit data. Eleven strategies with textbook
parameters, one cost model and one bar, all fixed BEFORE the run in
`logs/backtest_reports/prereg_playbook_20261025.md`:

  A trend           A1 time-series momentum L/S · A2 the same long/flat · A3 Turtle System 1
  B mean reversion  B1 Connors RSI(2) · B2 cross-sectional daily reversal · B3 fade 4h z ≥ 3
  C intraday        C1 volatility breakout (k 0.5) · C2 opening-range breakout ·
                    C3 session seasonality (fitted on TRAIN) · C4 CME-gap fill (BTC, ETH)
  D positioning     D1 funding extremes, contrarian

Data: the 3-year 4h + funding cache of the 15 majors written by `trend_study.py` (no network).
Every strategy becomes a 4h P&L series — marked to market on each close with a fixed notional
from the entry, taker + slippage on every fill, actual funding — summed per UTC day. TRAIN = the
first 60% of the days, TEST = the last 40%. Event strategies are also re-run with random entries
(same coin, half, side and exit) to show whether the entry adds anything.
Zero trading decisions, no order API, no hosted model.

Usage:
    venv/bin/python playbook_study.py            # → logs/backtest_reports/playbook_<date>.md
    venv/bin/python playbook_study.py --runs 5   # fewer random-entry runs (quick look)
"""

import argparse
import bisect
import json
import math
import random
import statistics
import time
from collections import defaultdict
from datetime import datetime, timezone

import config
import unified_backtest as ub

SYMBOLS = list(ub.MAJORS)
CACHE_TAG = "20231020_20261019"            # the 3-year cache trend_study.py wrote on 2026-10-19
H4_MS = ub.INTERVAL_MS["240"]
DAY_MS = ub.INTERVAL_MS["D"]
BPD = DAY_MS // H4_MS                      # 4h bars per UTC day
SIDE_COST = config.TAKER_FEE_PCT + config.SLIPPAGE_PCT
SPOT_SIDE_COST = 0.0010 + config.SLIPPAGE_PCT
TRAIN_FRAC = 0.6
EVENT_W = 1 / len(SYMBOLS)

TARGET_VOL, MAX_SCALE = 0.20, 5.0
RANDOM_RUNS, RANDOM_BEAT = 20, 18
PASS_SHARPE, PASS_GREEN, CAND_GREEN, PASS_DD = 1.0, 0.60, 0.55, 0.25

# Strategy parameters — textbook defaults, fixed in the pre-registration.
TSMOM_LOOKBACK = 30
TURTLE_ENTRY, TURTLE_EXIT, TURTLE_ATR, TURTLE_STOP_ATR = 20, 10, 20, 2.0
RSI_N, RSI_LOW, RSI_HIGH, RSI_TREND, RSI_EXIT_SMA, RSI_MAX_DAYS = 2, 10, 90, 200, 5, 10
REV_LEGS = 3
Z_LOOKBACK, Z_ENTRY, Z_HOLD = 180, 3.0, 6
VB_K = 0.5
SESSION_T = 2.0
GAP_SYMBOLS, GAP_MIN = ("BTCUSDT", "ETHUSDT"), 0.01
GAP_REF_BARS = 13                          # Friday 20:00 → Monday 00:00 UTC = 52 h
GAP_LAST = 28                              # Monday 00:00 + 28 bars = the Friday 16:00 bar
FUND_AVG, FUND_WINDOW_MS, FUND_PCT, FUND_MIN, FUND_HOLD, FUND_MIN_HISTORY = 3, 90 * DAY_MS, 0.95, 0.0002, 18, 100
CARRY_SYMBOLS, CARRY_LOOKBACK_MS = ("BTCUSDT", "ETHUSDT"), 7 * DAY_MS


# ─── Data ────────────────────────────────────────────────────────────────────

def load_panel(symbols=SYMBOLS):
    """The cached 4h bars of every symbol on one grid that starts and ends on whole UTC days."""
    raw = {}
    for s in symbols:
        bars = json.loads((ub.CACHE_DIR / f"{s}_240_{CACHE_TAG}.json").read_text())
        fund = json.loads((ub.CACHE_DIR / f"{s}_funding_{CACHE_TAG}.json").read_text())
        raw[s] = (bars, fund)
    stamps = sorted({int(b[0]) for bars, _ in raw.values() for b in bars})
    start = next(t for t in stamps if t % DAY_MS == 0)
    n_days = (stamps[-1] + H4_MS - start) // DAY_MS
    grid = [start + i * H4_MS for i in range(n_days * BPD)]
    return grid, {s: build_series(grid, bars, fund) for s, (bars, fund) in raw.items()}


def build_series(grid, bars, fund):
    """o/h/l/c per grid bar (None where the coin has no bar), the funding rate settled at each
    bar's start (`f`), the settlements themselves and the UTC-daily bars."""
    idx = {t: i for i, t in enumerate(grid)}
    n = len(grid)
    p = {k: [None] * n for k in "ohlc"}
    for b in bars:
        i = idx.get(int(b[0]))
        if i is not None:
            p["o"][i], p["h"][i], p["l"][i], p["c"][i] = (float(x) for x in b[1:5])
    p["f"] = [0.0] * n
    p["settle"] = []
    for ts, rate in sorted(fund):
        i = idx.get(int(ts) - int(ts) % H4_MS)
        if i is not None:
            p["f"][i] += float(rate)
            p["settle"].append((i, int(ts), float(rate)))
    p["daily"] = _daily(p)
    return p


def _daily(p):
    n_days = len(p["o"]) // BPD
    d = {k: [None] * n_days for k in "ohlc"}
    for day in range(n_days):
        bars = range(day * BPD, (day + 1) * BPD)
        if any(p["c"][k] is None for k in bars):
            continue
        d["o"][day] = p["o"][day * BPD]
        d["h"][day] = max(p["h"][k] for k in bars)
        d["l"][day] = min(p["l"][k] for k in bars)
        d["c"][day] = p["c"][(day + 1) * BPD - 1]
    return d


def _ind(p):
    """Daily indicators, computed once per series."""
    if "ind" not in p:
        c = p["daily"]["c"]
        p["ind"] = {"sma5": [sma(c, RSI_EXIT_SMA, i) for i in range(len(c))],
                    "sma200": [sma(c, RSI_TREND, i) for i in range(len(c))],
                    "rsi2": rsi_series(c, RSI_N)}
    return p["ind"]


def sma(xs, n, i):
    """Mean of xs[i-n+1..i]; None while warming up or across a gap."""
    if i < n - 1:
        return None
    w = xs[i - n + 1:i + 1]
    return None if None in w else sum(w) / n


def rsi_series(closes, n):
    """Wilder RSI; restarts its warm-up after a missing close."""
    out = [None] * len(closes)
    ag = al = None
    seed = []
    for i in range(1, len(closes)):
        a, b = closes[i - 1], closes[i]
        if a is None or b is None:
            ag = al = None
            seed = []
            continue
        g, l = max(b - a, 0.0), max(a - b, 0.0)
        if ag is None:
            seed.append((g, l))
            if len(seed) < n:
                continue
            ag, al = sum(x[0] for x in seed) / n, sum(x[1] for x in seed) / n
        else:
            ag, al = (ag * (n - 1) + g) / n, (al * (n - 1) + l) / n
        out[i] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    return out


def atr(d, i, n):
    """Simple average true range of the n days ending at day i."""
    if i < n:
        return None
    trs = []
    for k in range(i - n + 1, i + 1):
        h, l, pc = d["h"][k], d["l"][k], d["c"][k - 1]
        if None in (h, l, pc):
            return None
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return sum(trs) / n


# ─── Engine ──────────────────────────────────────────────────────────────────

def trade_net(t, p):
    """Net return of one trade per unit of notional: price move − fees − funding. Funding is
    paid on settlements strictly inside the hold (not at the entry bar's start)."""
    sg, e, x = t["side"], t["entry_px"], t["exit_px"]
    fund = sum(p["f"][k] for k in range(t["entry_bar"] + 1, t["exit_bar"] + 1))
    return sg * (x - e) / e - SIDE_COST * (1 + x / e) - sg * fund


def book_trade(pnl, t, p, cost=SIDE_COST):
    """Mark one trade to market on every 4h close with the notional fixed at the entry, so the
    bars sum to exactly weight × trade_net. `cost=0` gives the before-fees view."""
    w, sg, e = t["weight"], t["side"], t["entry_px"]
    i, j = t["entry_bar"], t["exit_bar"]
    prev = e
    for k in range(i, j + 1):
        px = t["exit_px"] if k == j else (p["c"][k] if p["c"][k] is not None else prev)
        pnl[k] += w * sg * (px - prev) / e
        prev = px
        if k > i:
            pnl[k] -= w * sg * p["f"][k]
    pnl[i] -= w * cost
    pnl[j] -= w * cost * t["exit_px"] / e


def book_positions(pnl, weights, panel, cost=SIDE_COST):
    """`weights` = {sym: [position held over each 4h bar, decided at its open]}. Each bar earns
    close-to-close; every weight change pays taker + slippage; funding is paid on the part of
    the position held across the settlement."""
    for s, ws in weights.items():
        p = panel[s]
        prev = 0.0
        for k, w in enumerate(ws):
            if w and k and p["c"][k] is not None and p["c"][k - 1] is not None:
                pnl[k] += w * (p["c"][k] / p["c"][k - 1] - 1)
            if prev and w and (prev > 0) == (w > 0):
                pnl[k] -= math.copysign(min(abs(prev), abs(w)), w) * p["f"][k]
            pnl[k] -= abs(w - prev) * cost
            prev = w


def to_daily(pnl):
    return [sum(pnl[d * BPD:(d + 1) * BPD]) for d in range(len(pnl) // BPD)]


def _trade(sym, side, bar, px, exit_fn, p, ctx, weight=EVENT_W):
    x = exit_fn(p, bar, px, side, ctx)
    if x is None:
        return None
    xb, xpx, why = x
    return {"sym": sym, "side": side, "entry_bar": bar, "entry_px": px, "exit_bar": xb,
            "exit_px": xpx, "reason": why, "weight": weight, "ctx": ctx}


def _stop_fill(p, k, side, stop):
    """Fill price when bar k touches the stop (a gap through it fills at the bar's open)."""
    if side > 0 and p["l"][k] <= stop:
        return min(p["o"][k], stop)
    if side < 0 and p["h"][k] >= stop:
        return max(p["o"][k], stop)
    return None


def _at_open_or_close(p, k):
    """Exit 'at the next open' after bar k, or at k's close when the data ends there."""
    if k + 1 < len(p["o"]) and p["o"][k + 1] is not None:
        return k, p["o"][k + 1]
    return k, p["c"][k]


# ─── Exits (shared by the real entries and the random-entry control) ─────────

def exit_hold(p, bar, px, side, ctx):
    j = min(bar + ctx["hold"] - 1, len(p["c"]) - 1)
    if any(p["c"][k] is None for k in range(bar, j + 1)):
        return None
    return j, p["c"][j], "time" if j == bar + ctx["hold"] - 1 else "end"


def exit_day_close(p, bar, px, side, ctx):
    """Out at the UTC day's close; with `stop_dist`, stopped out first if touched. An entry
    inside a bar (a trigger) only watches the stop from the next bar — the trigger bar was
    already required not to touch it."""
    j = (bar // BPD + 1) * BPD - 1
    if "stop_dist" in ctx:
        stop = px * (1 - side * ctx["stop_dist"])
        for k in range(bar + 1 if ctx.get("intrabar") else bar, j + 1):
            fill = _stop_fill(p, k, side, stop)
            if fill is not None:
                return k, fill, "stop"
    return j, p["c"][j], "close"


def exit_bracket(p, bar, px, side, ctx):
    """Target and stop at fixed distances until `last` bars after the entry; a bar that touches
    both counts as the stop."""
    target = px * (1 + side * ctx["target_dist"])
    stop = px * (1 - side * ctx["stop_dist"])
    j = min(bar + ctx["last"], len(p["c"]) - 1)
    for k in range(bar, j + 1):
        if p["c"][k] is None:
            return None
        fill = _stop_fill(p, k, side, stop)
        if fill is not None:
            return k, fill, "stop"
        if side > 0 and p["h"][k] >= target:
            return k, max(p["o"][k], target), "target"
        if side < 0 and p["l"][k] <= target:
            return k, min(p["o"][k], target), "target"
    return j, p["c"][j], "time" if j == bar + ctx["last"] else "end"


def exit_turtle(p, bar, px, side, ctx):
    """2-ATR stop on every 4h bar; out at the next open after a daily close beyond the
    10-day opposite channel."""
    d = p["daily"]
    stop = px * (1 - side * ctx["stop_dist"])
    last = len(p["c"]) - 1
    for k in range(bar, last + 1):
        if p["c"][k] is None:
            return None
        fill = _stop_fill(p, k, side, stop)
        if fill is not None:
            return k, fill, "stop"
        day = k // BPD
        if k % BPD == BPD - 1 and day >= TURTLE_EXIT and d["c"][day] is not None:
            lo, hi = d["l"][day - TURTLE_EXIT:day], d["h"][day - TURTLE_EXIT:day]
            if None not in lo and None not in hi and (
                    (side > 0 and d["c"][day] < min(lo)) or (side < 0 and d["c"][day] > max(hi))):
                return (*_at_open_or_close(p, k), "channel")
    return last, p["c"][last], "end"


def exit_rsi2(p, bar, px, side, ctx):
    """Out at the next open after a daily close beyond SMA(5), or after 10 days."""
    d, ind = p["daily"], _ind(p)
    first = bar // BPD
    for day in range(first, min(len(d["c"]), first + RSI_MAX_DAYS)):
        c, m = d["c"][day], ind["sma5"][day]
        if c is None:
            return None
        crossed = m is not None and (c > m if side > 0 else c < m)
        if crossed or day == first + RSI_MAX_DAYS - 1:
            return (*_at_open_or_close(p, (day + 1) * BPD - 1), "sma5" if crossed else "time")
    last = len(p["c"]) - 1
    return last, p["c"][last], "end"


# ─── Event strategies → trades ───────────────────────────────────────────────

def s_turtle(panel, grid):
    trades = []
    for s, p in panel.items():
        d, free = p["daily"], 0
        for day in range(TURTLE_ENTRY, len(d["c"]) - 1):
            bar = (day + 1) * BPD
            hi, lo, c = d["h"][day - TURTLE_ENTRY:day], d["l"][day - TURTLE_ENTRY:day], d["c"][day]
            if bar < free or c is None or None in hi or None in lo:
                continue
            side = 1 if c > max(hi) else -1 if c < min(lo) else 0
            a, px = atr(d, day, TURTLE_ATR), p["o"][bar]
            if not side or not a or px is None:
                continue
            t = _trade(s, side, bar, px, exit_turtle, p, {"stop_dist": TURTLE_STOP_ATR * a / px})
            if t:
                trades.append(t)
                free = t["exit_bar"] + 1
    return trades


def s_rsi2(panel, grid):
    trades = []
    for s, p in panel.items():
        d, ind, free = p["daily"], _ind(p), 0
        for day in range(len(d["c"]) - 1):
            bar = (day + 1) * BPD
            r, c, m = ind["rsi2"][day], d["c"][day], ind["sma200"][day]
            if bar < free or None in (r, c, m) or p["o"][bar] is None:
                continue
            side = 1 if (r < RSI_LOW and c > m) else -1 if (r > RSI_HIGH and c < m) else 0
            if side:
                t = _trade(s, side, bar, p["o"][bar], exit_rsi2, p, {})
                if t:
                    trades.append(t)
                    free = t["exit_bar"] + 1
    return trades


def s_fade(panel, grid):
    """4h return / stdev of the prior 180 returns beyond ±3 → fade it for 24h."""
    trades = []
    for s, p in panel.items():
        c, free = p["c"], 0
        window, s1, s2 = [], 0.0, 0.0
        for k in range(1, len(c) - 1):
            if c[k] is None or c[k - 1] is None:
                window, s1, s2 = [], 0.0, 0.0
                continue
            r = c[k] / c[k - 1] - 1
            if len(window) == Z_LOOKBACK and k + 1 >= free and p["o"][k + 1] is not None:
                var = s2 / Z_LOOKBACK - (s1 / Z_LOOKBACK) ** 2
                z = r / math.sqrt(var) if var > 0 else 0.0
                side = 1 if z <= -Z_ENTRY else -1 if z >= Z_ENTRY else 0
                if side:
                    t = _trade(s, side, k + 1, p["o"][k + 1], exit_hold, p, {"hold": Z_HOLD})
                    if t:
                        trades.append(t)
                        free = t["exit_bar"] + 1
            window.append(r)
            s1 += r
            s2 += r * r
            if len(window) > Z_LOOKBACK:
                old = window.pop(0)
                s1 -= old
                s2 -= old * old
    return trades


def s_vol_breakout(panel, grid, two_sided="worst"):
    """Larry Williams: open ± 0.5 × yesterday's range, first trigger, out at the day's close.

    A 4h bar that crosses both triggers hides which came first. The pre-registration skipped
    those days, but on average they lose (−0.5 × the trigger distance), so skipping flatters
    the rule; the default takes the side that loses more unless the bar's open settles it.
    `two_sided="skip"` reproduces the registered rule for the record."""
    trades = []
    for s, p in panel.items():
        d = p["daily"]
        for day in range(1, len(d["c"])):
            h1, l1, o = d["h"][day - 1], d["l"][day - 1], d["o"][day]
            if None in (h1, l1, o) or d["c"][day] is None or h1 <= l1:
                continue
            up, dn = o + VB_K * (h1 - l1), o - VB_K * (h1 - l1)
            for k in range(day * BPD, (day + 1) * BPD):
                hit_up, hit_dn = p["h"][k] >= up, p["l"][k] <= dn
                if not (hit_up or hit_dn):
                    continue
                if hit_up and hit_dn:
                    if two_sided == "skip":
                        break
                    close, ok = p["c"][(day + 1) * BPD - 1], p["o"][k]
                    if ok >= up or ok <= dn:                 # the open already sits past one trigger
                        hit_up, hit_dn = ok >= up, ok <= dn
                    else:
                        hit_up = (close - up) / up <= (dn - close) / dn
                side = 1 if hit_up else -1
                px = max(up, p["o"][k]) if hit_up else min(dn, p["o"][k])
                t = _trade(s, side, k, px, exit_day_close, p, {"intrabar": True})
                if t:
                    trades.append(t)
                break
    return trades


def s_orb(panel, grid, two_sided="loss"):
    """Range = the 00:00–04:00 UTC bar; break of it → trade, stop at the other side, out at
    the day's close.

    A 4h bar that crosses both sides of the range is a stopped-out trade whichever side broke
    first (the stop IS the other side). The pre-registration skipped those days, which drops
    guaranteed losers; the default books them as the loss (the larger of the two in %).
    `two_sided="skip"` reproduces the registered rule for the record."""
    trades = []
    for s, p in panel.items():
        for day in range(len(p["daily"]["c"])):
            k0 = day * BPD
            if p["daily"]["c"][day] is None:
                continue
            rh, rl = p["h"][k0], p["l"][k0]
            for k in range(k0 + 1, k0 + BPD):
                hit_up, hit_dn = p["h"][k] > rh, p["l"][k] < rl
                if hit_up and hit_dn:
                    if two_sided == "skip":
                        break
                    ok = p["o"][k]
                    side = 1 if ok > rh else -1               # opened above → the long came first
                    px = ok if (ok > rh or ok < rl) else (rh if side > 0 else rl)
                    stop = rl if side > 0 else rh
                    trades.append({"sym": s, "side": side, "entry_bar": k, "entry_px": px, "exit_bar": k,
                                   "exit_px": stop, "reason": "two-sided", "weight": EVENT_W,
                                   "ctx": {"stop_dist": abs(px - stop) / px, "intrabar": True}})
                    break
                if hit_up or hit_dn:
                    side = 1 if hit_up else -1
                    px = max(rh, p["o"][k]) if hit_up else min(rl, p["o"][k])
                    stop = rl if hit_up else rh
                    t = _trade(s, side, k, px, exit_day_close, p,
                               {"stop_dist": abs(px - stop) / px, "intrabar": True})
                    if t:
                        trades.append(t)
                    break
    return trades


def s_cme_gap(panel, grid):
    """Monday 00:00 UTC vs Friday 20:00 UTC; a gap ≥ 1% → trade toward the Friday price, 1:1."""
    trades = []
    for s in GAP_SYMBOLS:
        p = panel[s]
        for m in range(GAP_REF_BARS, len(grid) - 1):
            t0 = datetime.fromtimestamp(grid[m] / 1000, tz=timezone.utc)
            if t0.weekday() != 0 or t0.hour != 0:
                continue
            ref, e = p["o"][m - GAP_REF_BARS], p["o"][m]
            if ref is None or e is None:
                continue
            gap = e / ref - 1
            if abs(gap) < GAP_MIN:
                continue
            dist = abs(e - ref) / e
            t = _trade(s, -1 if gap > 0 else 1, m, e, exit_bracket, p,
                       {"target_dist": dist, "stop_dist": dist, "last": GAP_LAST},
                       weight=1 / len(GAP_SYMBOLS))
            if t:
                trades.append(t)
    return trades


def s_funding(panel, grid):
    """Average of the last 3 settlements beyond its own trailing-90-day 95th / 5th percentile
    → against the crowd for 72h, entered at the 4h open after the settlement."""
    trades = []
    for s, p in panel.items():
        st, free = p["settle"], 0
        stamps = [x[1] for x in st]
        avg = [None] * len(st)
        for j in range(FUND_AVG - 1, len(st)):
            avg[j] = sum(x[2] for x in st[j - FUND_AVG + 1:j + 1]) / FUND_AVG
        for j in range(len(st)):
            bar = st[j][0] + 1
            if avg[j] is None or bar < free or bar >= len(p["o"]) or p["o"][bar] is None:
                continue
            lo = bisect.bisect_left(stamps, stamps[j] - FUND_WINDOW_MS)
            hist = sorted(a for a in avg[lo:j] if a is not None)
            if len(hist) < FUND_MIN_HISTORY:
                continue
            hi_q, lo_q = hist[int(FUND_PCT * (len(hist) - 1))], hist[int((1 - FUND_PCT) * (len(hist) - 1))]
            a = avg[j]
            side = -1 if (a >= hi_q and a > FUND_MIN) else 1 if (a <= lo_q and a < 0) else 0
            if side:
                t = _trade(s, side, bar, p["o"][bar], exit_hold, p, {"hold": FUND_HOLD})
                if t:
                    trades.append(t)
                    free = t["exit_bar"] + 1
    return trades


# ─── Position strategies → weights ───────────────────────────────────────────

def _empty(panel, n):
    return {s: [0.0] * n for s in panel}


def w_tsmom(panel, grid, long_only=False):
    """Sign of the 30-day return, inverse-volatility weights, Σ|w| = 1 over the L/S book; the
    long/flat variant keeps the long legs at the same weights (shorts become cash)."""
    n = len(grid)
    W = _empty(panel, n)
    for day in range(TSMOM_LOOKBACK + 1, n // BPD):
        raw = {}
        for s, p in panel.items():
            w = p["daily"]["c"][day - TSMOM_LOOKBACK - 1:day]
            if None in w:
                continue
            vol = statistics.pstdev([w[i] / w[i - 1] - 1 for i in range(1, len(w))])
            sgn = (w[-1] > w[0]) - (w[-1] < w[0])
            if vol > 0 and sgn:
                raw[s] = sgn / vol
        tot = sum(abs(v) for v in raw.values())
        for s, v in raw.items():
            wt = v / tot
            if long_only and wt < 0:
                continue
            W[s][day * BPD:(day + 1) * BPD] = [wt] * BPD
    return W


def w_reversal(panel, grid):
    """Long the 3 worst coins of yesterday, short the 3 best, hold one UTC day."""
    n = len(grid)
    W = _empty(panel, n)
    for day in range(2, n // BPD):
        r = {s: p["daily"]["c"][day - 1] / p["daily"]["c"][day - 2] - 1 for s, p in panel.items()
             if p["daily"]["c"][day - 1] is not None and p["daily"]["c"][day - 2] is not None}
        if len(r) < 2 * REV_LEGS + 2:
            continue
        order = sorted(r, key=r.get)
        for s in order[:REV_LEGS]:
            W[s][day * BPD:(day + 1) * BPD] = [1 / (2 * REV_LEGS)] * BPD
        for s in order[-REV_LEGS:]:
            W[s][day * BPD:(day + 1) * BPD] = [-1 / (2 * REV_LEGS)] * BPD
    return W


def session_table(panel, grid, split_bar):
    """TRAIN-only mean equal-weight basket return per 4h session, with its t-stat."""
    by = defaultdict(list)
    for k in range(1, split_bar):
        rs = [p["c"][k] / p["c"][k - 1] - 1 for p in panel.values()
              if p["c"][k] is not None and p["c"][k - 1] is not None]
        if rs:
            by[(grid[k] % DAY_MS) // H4_MS].append(sum(rs) / len(rs))
    out = {}
    for sess, xs in sorted(by.items()):
        m, sd = statistics.mean(xs), statistics.stdev(xs)
        out[sess] = {"mean": m, "t": m / (sd / math.sqrt(len(xs))), "n": len(xs)}
    return out


def w_session(panel, grid, split_bar):
    table = session_table(panel, grid, split_bar)
    best = max(table, key=lambda k: table[k]["t"])
    worst = min(table, key=lambda k: table[k]["t"])
    pick = {}
    if table[best]["t"] >= SESSION_T:
        pick[best] = 1
    if table[worst]["t"] <= -SESSION_T:
        pick[worst] = -1
    W = _empty(panel, len(grid))
    for k in range(1, len(grid)):
        side = pick.get((grid[k] % DAY_MS) // H4_MS)
        if not side:
            continue
        live = [s for s, p in panel.items() if p["c"][k - 1] is not None]
        for s in live:
            W[s][k] = side / len(live)
    return W, table, pick


def w_buy_hold(panel, grid, only=None):
    W = _empty(panel, len(grid))
    for k in range(1, len(grid)):
        live = [s for s, p in panel.items() if p["c"][k - 1] is not None and (only is None or s in only)]
        for s in live:
            W[s][k] = 1 / len(live)
    return W


def carry_pnl(panel, grid):
    """Delta-neutral carry, 1/2 of capital each on BTC and ETH: short perp + long spot while the
    trailing 7-day funding is positive. Earns funding; basis changes are ignored."""
    pnl = [0.0] * len(grid)
    for s in CARRY_SYMBOLS:
        p = panel[s]
        stamps = [x[1] for x in p["settle"]]
        on_prev = False
        for day in range(len(grid) // BPD):
            t0 = grid[day * BPD]
            lo, hi = bisect.bisect_left(stamps, t0 - CARRY_LOOKBACK_MS), bisect.bisect_left(stamps, t0)
            recent = [x[2] for x in p["settle"][lo:hi]]
            on = bool(recent) and sum(recent) / len(recent) > 0
            if on != on_prev:
                pnl[day * BPD] -= 0.5 * (SIDE_COST + SPOT_SIDE_COST)
            if on:
                for k in range(day * BPD, (day + 1) * BPD):
                    if k > day * BPD or on_prev:
                        pnl[k] += 0.5 * p["f"][k]
            on_prev = on
    return pnl


# ─── Metrics ─────────────────────────────────────────────────────────────────

def month_of(grid, day):
    return datetime.fromtimestamp(grid[day * BPD] / 1000, tz=timezone.utc).strftime("%Y-%m")


def metrics(daily, days, grid, scale=1.0):
    """Net (unit sizing), Sharpe, calendar months green/red/flat and drawdown at `scale`."""
    xs = [daily[d] for d in days]
    sd = statistics.stdev(xs) if len(xs) > 1 else 0.0
    mu = statistics.mean(xs) if xs else 0.0
    months = defaultdict(float)
    for d in days:
        months[month_of(grid, d)] += daily[d]
    green = sum(1 for m, v in months.items() if v > 0)
    red = sum(1 for m, v in months.items() if v < 0)
    eq = peak = dd = 0.0
    for x in xs:
        eq += x * scale
        peak = max(peak, eq)
        dd = max(dd, peak - eq)
    return {"net": sum(xs), "ann": mu * 365, "vol": sd * math.sqrt(365),
            "sharpe": mu / sd * math.sqrt(365) if sd > 0 else 0.0,
            "months": len(months), "green": green, "red": red, "flat": len(months) - green - red,
            "green_pct": green / len(months) if months else 0.0,
            "worst": min(months.values()) if months else 0.0, "dd": dd, "scale": scale,
            "monthly": dict(months)}


def trade_stats(trades, panel):
    if not trades:
        return {"n": 0}
    nets = [trade_net(t, panel[t["sym"]]) for t in trades]
    wins, losses = [x for x in nets if x > 0], [x for x in nets if x <= 0]
    return {"n": len(nets), "win": len(wins) / len(nets), "avg": sum(nets) / len(nets),
            "pf": sum(wins) / -sum(losses) if losses and sum(losses) < 0 else float("inf"),
            "long": sum(1 for t in trades if t["side"] > 0),
            "long_avg": _avg([x for x, t in zip(nets, trades) if t["side"] > 0]),
            "short_avg": _avg([x for x, t in zip(nets, trades) if t["side"] < 0]),
            "hold_days": sorted((t["exit_bar"] - t["entry_bar"] + 1) / BPD for t in trades)[len(trades) // 2]}


def _avg(xs):
    return sum(xs) / len(xs) if xs else None


def alpha_beta(y, x):
    """OLS of daily strategy returns on daily market returns → (annualised alpha, beta)."""
    mx, my = statistics.mean(x), statistics.mean(y)
    vx = sum((a - mx) ** 2 for a in x)
    beta = sum((a - mx) * (b - my) for a, b in zip(x, y)) / vx if vx else 0.0
    return (my - beta * mx) * 365, beta


def random_trades(trades, panel, exit_fn, rng, split_bar, n_bars):
    """Every real trade → one at a random 4h open of the same coin in the same half, same side
    and the same exit rule (same stop / target distances)."""
    out = []
    for t in trades:
        p = panel[t["sym"]]
        lo, hi = (0, split_bar) if t["entry_bar"] < split_bar else (split_bar, n_bars - 1)
        for _ in range(50):
            b = rng.randrange(lo, hi)
            if p["o"][b] is None:
                continue
            x = _trade(t["sym"], t["side"], b, p["o"][b], exit_fn, p, dict(t["ctx"], intrabar=False), t["weight"])
            if x:
                out.append(x)
                break
    return out


def verdict(key, tr, te, chance_ok):
    """The pre-registered bar. CANDIDATE = condition 1 and ≥ 55% green months, but not PASS."""
    if te["net"] <= 0 or (key != "C3" and tr["net"] <= 0):
        return "NO", "net ≤ 0 on " + ("TEST" if te["net"] <= 0 else "TRAIN")
    misses = []
    if te["sharpe"] < PASS_SHARPE:
        misses.append(f"Sharpe {te['sharpe']:.2f} < {PASS_SHARPE}")
    if te["green_pct"] < PASS_GREEN:
        misses.append(f"green months {te['green_pct'] * 100:.0f}% < {PASS_GREEN * 100:.0f}%")
    if te["dd"] > PASS_DD:
        misses.append(f"DD {te['dd'] * 100:.0f}% > {PASS_DD * 100:.0f}%")
    if not chance_ok:
        misses.append("does not beat chance")
    if not misses:
        return "PASS", "all conditions met"
    if te["green_pct"] >= CAND_GREEN:
        return "CANDIDATE", "; ".join(misses)
    return "NO", "; ".join(misses)


# ─── Run ─────────────────────────────────────────────────────────────────────

EVENTS = [
    ("A3", "Turtle System 1 (20-day breakout, 10-day exit, 2-ATR stop)", s_turtle, exit_turtle),
    ("B1", "Connors RSI(2) with SMA(200) filter", s_rsi2, exit_rsi2),
    ("B3", "Fade a 4h move beyond 3 sigma, hold 24h", s_fade, exit_hold),
    ("C1", "Volatility breakout (open ± 0.5 × yesterday's range), out at the close", s_vol_breakout, exit_day_close),
    ("C2", "Opening-range breakout (first 4h of the UTC day), out at the close", s_orb, exit_day_close),
    ("C4", "CME-gap fill, BTC + ETH (Fri 20:00 → Mon 00:00 gap ≥ 1%)", s_cme_gap, exit_bracket),
    ("D1", "Funding extremes, contrarian, hold 72h", s_funding, exit_hold),
]
POSITIONS = [
    ("A1", "Time-series momentum 30d, long/short"),
    ("A2", "Time-series momentum 30d, long/flat"),
    ("B2", "Cross-sectional daily reversal (3 worst long / 3 best short)"),
    ("C3", "Session seasonality (session chosen on TRAIN)"),
]
ORDER = ["A1", "A2", "A3", "B1", "B2", "B3", "C1", "C2", "C3", "C4", "D1"]


def run(args):
    t0 = time.time()
    grid, panel = load_panel()
    n, n_days = len(grid), len(grid) // BPD
    split_day = int(TRAIN_FRAC * n_days)
    split_bar = split_day * BPD
    train_days, test_days = range(1, split_day), range(split_day, n_days)
    dt = lambda ms: datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    print(f"Grid {dt(grid[0])} → {dt(grid[-1] + H4_MS)} ({n_days} days), split {dt(grid[split_bar])}")

    series, gross, trades_by, info = {}, {}, {}, {}           # gross = before fees + slippage
    for key, name, build, exit_fn in EVENTS:
        tr = build(panel, grid)
        pnl, pnl0 = [0.0] * n, [0.0] * n
        for t in tr:
            book_trade(pnl, t, panel[t["sym"]])
            book_trade(pnl0, t, panel[t["sym"]], cost=0.0)
        series[key], gross[key], trades_by[key] = to_daily(pnl), to_daily(pnl0), tr
        info[key] = {"name": name, "kind": "event", "exit": exit_fn}
        print(f"  {key}: {len(tr)} trades ({time.time() - t0:.0f}s)")
    registered = {}                                         # the rule as written, two-sided bars skipped
    for key, build in (("C1", s_vol_breakout), ("C2", s_orb)):
        tr = build(panel, grid, two_sided="skip")
        pnl = [0.0] * n
        for t in tr:
            book_trade(pnl, t, panel[t["sym"]])
        daily = to_daily(pnl)
        registered[key] = {"n": len(tr), "train": metrics(daily, train_days, grid),
                           "test": metrics(daily, test_days, grid)}
    weights = {"A1": w_tsmom(panel, grid), "A2": w_tsmom(panel, grid, long_only=True),
               "B2": w_reversal(panel, grid)}
    weights["C3"], sess_table, sess_pick = w_session(panel, grid, split_bar)
    for key, name in POSITIONS:
        pnl, pnl0 = [0.0] * n, [0.0] * n
        book_positions(pnl, weights[key], panel)
        book_positions(pnl0, weights[key], panel, cost=0.0)
        series[key], gross[key] = to_daily(pnl), to_daily(pnl0)
        info[key] = {"name": name, "kind": "position"}
    refs = {}
    for key, W in (("BTC buy & hold", w_buy_hold(panel, grid, only={"BTCUSDT"})),
                   ("Equal-weight 15 buy & hold", w_buy_hold(panel, grid))):
        pnl = [0.0] * n
        book_positions(pnl, W, panel)
        refs[key] = to_daily(pnl)
    refs["Delta-neutral carry BTC+ETH"] = to_daily(carry_pnl(panel, grid))
    market = refs["Equal-weight 15 buy & hold"]
    print(f"Strategies built ({time.time() - t0:.0f}s); random-entry control × {args.runs}")

    res = {}
    for key in ORDER:
        daily = series[key]
        train_vol = statistics.stdev([daily[d] for d in train_days]) * math.sqrt(365)
        scale = min(MAX_SCALE, TARGET_VOL / train_vol) if train_vol > 0 else 1.0
        tr, te = metrics(daily, train_days, grid, scale), metrics(daily, test_days, grid, scale)
        r = {"train": tr, "test": te, "scale": scale}
        if info[key]["kind"] == "event":
            tl = trades_by[key]
            r["t_train"] = trade_stats([t for t in tl if t["entry_bar"] < split_bar], panel)
            r["t_test"] = trade_stats([t for t in tl if t["entry_bar"] >= split_bar], panel)
            rnd = []
            for i in range(args.runs):
                rt = random_trades(tl, panel, info[key]["exit"], random.Random(1000 + i), split_bar, n)
                pnl = [0.0] * n
                for t in rt:
                    book_trade(pnl, t, panel[t["sym"]])
                rnd.append(metrics(to_daily(pnl), test_days, grid)["sharpe"])
            beat = sum(1 for x in rnd if x < te["sharpe"])
            need = math.ceil(RANDOM_BEAT / RANDOM_RUNS * args.runs)
            r["chance"] = f"beats {beat}/{args.runs} random (median {statistics.median(rnd):+.2f})"
            r["chance_ok"] = beat >= need
            reasons = defaultdict(int)
            for t in tl:
                reasons[t["reason"]] += 1
            r["reasons"] = dict(reasons)
        else:
            a, b = alpha_beta([daily[d] for d in test_days], [market[d] for d in test_days])
            r["chance"] = f"alpha {a * 100:+.1f}%/y, beta {b:+.2f}"
            r["chance_ok"] = a > 0
        r["verdict"], r["why"] = verdict(key, tr, te, r["chance_ok"])
        res[key] = r
        print(f"  {key}: {r['verdict']} ({time.time() - t0:.0f}s)")

    report = render(grid, panel, res, info, series, refs, train_days, test_days, split_bar,
                    sess_table, sess_pick, trades_by, registered, gross, args)
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    rp = ub.REPORT_DIR / f"playbook_{today}.md"
    rp.write_text(report, encoding="utf-8")
    tp = ub.REPORT_DIR / f"playbook_{today}_trades.json"
    tp.write_text(json.dumps({k: [{x: t[x] for x in t if x != "ctx"} | {"ts": grid[t["entry_bar"]]}
                                  for t in v] for k, v in trades_by.items()}, separators=(",", ":")),
                  encoding="utf-8")
    print(report)
    print(f"\nVERDICTS: {json.dumps({k: r['verdict'] for k, r in res.items()})}")
    print(f"Saved {rp} and {tp} ({time.time() - t0:.0f}s total)")


def _pct(x, nd=1):
    return "—" if x is None else f"{x * 100:+.{nd}f}%"


def render(grid, panel, res, info, series, refs, train_days, test_days, split_bar,
           sess_table, sess_pick, trades_by, registered, gross, args):
    dt = lambda ms: datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    n_days = len(grid) // BPD
    L = [f"# Daily trader's playbook study — {datetime.now(timezone.utc):%Y-%m-%d}"]
    L.append(f"\nPre-registration: `logs/backtest_reports/prereg_playbook_20261025.md`. {len(panel)} Bybit USDT "
             f"perps ({', '.join(s.replace('USDT', '') for s in panel)}), 4h bars {dt(grid[0])} → "
             f"{dt(grid[-1] + H4_MS)} ({n_days} days). TRAIN = before {dt(grid[split_bar])}, TEST = from it "
             f"({len(test_days)} days). Costs: taker {config.TAKER_FEE_PCT * 100:.3f}% + slippage "
             f"{config.SLIPPAGE_PCT * 100:.2f}% on every fill, actual funding. Net = % of capital at the "
             f"strategy's own sizing (event trades 1/15 of capital each). \"@20% vol\" = scaled to 20% annual "
             f"volatility with the scale fixed on TRAIN (cap {MAX_SCALE:.0f}×). Months = calendar months inside "
             f"the half (the split month counts in both, partially).")

    L.append("\n## Verdict\n")
    L.append("| | strategy | TRAIN net | TEST net | TEST Sharpe | TEST months green | worst month @20% vol "
             "| TEST return @20% vol | TEST max DD @20% vol | TEST trades (PF) | chance | verdict |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for key in ORDER:
        r = res[key]
        tr, te, s = r["train"], r["test"], r["scale"]
        tt = r.get("t_test")
        trades = "—" if tt is None else (f"{tt['n']} (PF {tt['pf']:.2f})" if tt["n"] else "0")
        L.append(f"| {key} | {info[key]['name']} | {_pct(tr['net'])} | {_pct(te['net'])} | {te['sharpe']:+.2f} | "
                 f"{te['green']}/{te['months']} ({te['green_pct'] * 100:.0f}%) | {_pct(te['worst'] * s)} | "
                 f"{_pct(te['ann'] * s)}/y | {te['dd'] * 100:.0f}% | {trades} | {r['chance']} | "
                 f"**{r['verdict']}** — {r['why']} |")
    L.append("\n**Correction after the run (C1, C2).** The pre-registration skipped any day whose 4h bar "
             "crossed both triggers. For C2 that bar is a stopped-out trade whichever side broke first (the "
             "stop is the other side of the range); for C1 it loses on average. Skipping them dropped losers, "
             "so the table above books them conservatively (C2: the stop-out; C1: the side that loses more, "
             "unless the bar's open shows which came first). The rule as written, for the record:")
    for key, r in registered.items():
        extra = len(trades_by[key]) - r["n"]
        L.append(f"- {key} as registered: TRAIN {_pct(r['train']['net'])}, TEST {_pct(r['test']['net'])}, "
                 f"TEST Sharpe {r['test']['sharpe']:+.2f}, months green {r['test']['green']}/{r['test']['months']} "
                 f"— {extra} two-sided days ({extra / len(trades_by[key]) * 100:.0f}% of trades) were skipped.")

    L.append("\n## Before fees and slippage (informational — funding kept)\n")
    L.append("Would cheaper execution (maker fills, a VIP fee tier) save a strategy? Gross = the same trades "
             "with zero fees and slippage, so gross − net = what the costs took.\n")
    L.append("| | TRAIN gross | TEST gross | TEST costs paid | TEST gross Sharpe | TEST gross months green |")
    L.append("|---|---|---|---|---|---|")
    for key in ORDER:
        gtr, gte = metrics(gross[key], train_days, grid), metrics(gross[key], test_days, grid)
        L.append(f"| {key} | {_pct(gtr['net'])} | {_pct(gte['net'])} | {_pct(gte['net'] - res[key]['test']['net'])} | "
                 f"{gte['sharpe']:+.2f} | {gte['green']}/{gte['months']} |")

    L.append("\n## Reference lines (not strategies under test)\n")
    L.append("| line | TRAIN net | TEST net | TEST Sharpe | TEST months green | TEST max DD (unit) |")
    L.append("|---|---|---|---|---|---|")
    for name, daily in refs.items():
        tr, te = metrics(daily, train_days, grid), metrics(daily, test_days, grid)
        L.append(f"| {name} | {_pct(tr['net'])} | {_pct(te['net'])} | {te['sharpe']:+.2f} | "
                 f"{te['green']}/{te['months']} ({te['green_pct'] * 100:.0f}%) | {te['dd'] * 100:.0f}% |")

    years = sorted({month_of(grid, d)[:4] for d in range(n_days)})
    L.append("\n## Net per calendar year (unit sizing; 2023 = Oct 20 → Dec)\n")
    L.append("| | " + " | ".join(years) + " |")
    L.append("|---" * (len(years) + 1) + "|")
    for key in ORDER:
        by = defaultdict(float)
        for d in range(n_days):
            by[month_of(grid, d)[:4]] += series[key][d]
        L.append(f"| {key} | " + " | ".join(_pct(by[y]) for y in years) + " |")
    for name, daily in refs.items():
        by = defaultdict(float)
        for d in range(n_days):
            by[month_of(grid, d)[:4]] += daily[d]
        L.append(f"| {name} | " + " | ".join(_pct(by[y]) for y in years) + " |")

    L.append("\n## Month by month, TEST (% of capital at 20% vol; ✓ = green)\n")
    months = sorted({month_of(grid, d) for d in test_days})
    L.append("| month | " + " | ".join(ORDER) + " | BTC b&h (unit) |")
    L.append("|---" * (len(ORDER) + 2) + "|")
    btc = metrics(refs["BTC buy & hold"], test_days, grid)["monthly"]
    for m in months:
        cells = []
        for key in ORDER:
            v = res[key]["test"]["monthly"].get(m, 0.0) * res[key]["scale"]
            cells.append(f"{v * 100:+.1f}{' ✓' if v > 0 else ''}")
        L.append(f"| {m} | " + " | ".join(cells) + f" | {btc.get(m, 0.0) * 100:+.1f} |")

    L.append("\n## Event strategies — trades\n")
    L.append("| | half | n | win | avg net / trade | PF | long n | long avg | short avg | median hold (d) |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for key in ORDER:
        r = res[key]
        if "t_test" not in r:
            continue
        for half in ("t_train", "t_test"):
            t = r[half]
            if not t["n"]:
                L.append(f"| {key} | {half[2:].upper()} | 0 | | | | | | | |")
                continue
            pf = "inf" if t["pf"] == float("inf") else f"{t['pf']:.2f}"
            L.append(f"| {key} | {half[2:].upper()} | {t['n']} | {t['win'] * 100:.0f}% | {_pct(t['avg'], 2)} | {pf} | "
                     f"{t['long']} | {_pct(t['long_avg'], 2)} | {_pct(t['short_avg'], 2)} | {t['hold_days']:.1f} |")
    L.append("\nExit reasons: " + "; ".join(
        f"{k} " + ", ".join(f"{a} {b}" for a, b in sorted(res[k]["reasons"].items(), key=lambda kv: -kv[1]))
        for k in ORDER if "reasons" in res[k]) + ".")
    L.append(f"\nRound trip = {2 * SIDE_COST * 100:.2f}% of the position before funding: a strategy whose "
             f"average move per trade is below that cannot be profitable here.")

    L.append("\n## C3 — the sessions on TRAIN (equal-weight basket, mean 4h return)\n")
    L.append("| session (UTC) | mean | t | n |")
    L.append("|---|---|---|---|")
    for sess, v in sess_table.items():
        L.append(f"| {sess * 4:02d}:00–{sess * 4 + 4:02d}:00 | {v['mean'] * 100:+.3f}% | {v['t']:+.2f} | {v['n']} |")
    L.append("\nChosen: " + (", ".join(f"{'long' if v > 0 else 'short'} {k * 4:02d}:00" for k, v in sess_pick.items())
                             or f"none (no session with |t| ≥ {SESSION_T}) → C3 holds no position") + ".")

    keep = [k for k in ORDER if res[k]["verdict"] in ("PASS", "CANDIDATE")]
    if len(keep) > 1:
        L.append("\n## Correlation of TEST daily returns (PASS + CANDIDATE)\n")
        L.append("| | " + " | ".join(keep) + " |")
        L.append("|---" * (len(keep) + 1) + "|")
        for a in keep:
            xa = [series[a][d] for d in test_days]
            row = []
            for b in keep:
                xb = [series[b][d] for d in test_days]
                row.append(f"{statistics.correlation(xa, xb):+.2f}" if statistics.pstdev(xa) and statistics.pstdev(xb) else "—")
            L.append(f"| {a} | " + " | ".join(row) + " |")

    counts = defaultdict(int)
    for r in res.values():
        counts[r["verdict"]] += 1
    L.append("\n## Reading\n")
    L.append(f"- Verdicts: {counts['PASS']} PASS, {counts['CANDIDATE']} CANDIDATE, {counts['NO']} NO out of "
             f"{len(ORDER)}. With {len(ORDER)} strategies about 0.5 false PASS is expected by chance, so a PASS "
             f"earns a forward paper test, not real money.")
    L.append(f"- Random-entry control: {args.runs} runs per event strategy; PASS needs the strategy's TEST "
             f"Sharpe above {RANDOM_BEAT} of {RANDOM_RUNS}.")
    L.append("- Survivorship: the 15 coins are today's survivors; long-biased results are flattered.")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", type=int, default=RANDOM_RUNS, help="random-entry runs per event strategy")
    run(ap.parse_args())


if __name__ == "__main__":
    main()
