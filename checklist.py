"""
checklist.py — the trader's checklist (pre-registered 2026-10-21: logs/backtest_reports/prereg_checklist_20261021.md).

Nine points read at a signal close T from CLOSED bars only: 4h trend, 1h trend, daily MA200 side,
a fresh 4h supply/demand zone, a 4h trendline, BTC's 4h trend, funding against the crowd, open
interest trapping the other side, and a volume spike. ONE implementation, shared by
`checklist_study.py` (backtest) and `main.py` (live), so the live score is by construction the
backtested score (operating discipline #7).

Live use is instrumentation only: the score is stamped on every candidate and changes no pick until
the forward test in prereg_checklist_confirm_20261021.md has run and the user decides.
Pure Python, zero Claude tokens, no order API.
"""
import math
from bisect import bisect_right

import pandas as pd

import signal_rules as sr

ITEMS = ("trend_4h", "trend_1h", "ma200_d", "sd_zone", "trendline", "btc_4h", "funding", "oi_trapped", "volume")
VERSION = "v1"
INTERVAL_MS = {"15": 900_000, "60": 3_600_000, "240": 14_400_000, "D": 86_400_000}
LOOKBACK = 120          # 4h bars searched for zones / swings
IMPULSE_ATR = 1.5       # impulse body vs the ATR of the bar before it
SWING_ORDER = 3         # swing = extreme of the 3 bars on each side
MIN_SWING_GAP = 5
FUNDING_MIN = 0.00005   # 0.005%
MOVE_EPS = 0.5          # % for the 24h price / OI moves


# ----------------------------------------------------------------------------- frames
def frame(rows, interval):
    """Closed kline rows (oldest first, [ts, o, h, l, c, volume, ...]) → the arrays the checklist reads.
    `ms` is each bar's CLOSE time."""
    rows = sorted({int(r[0]): r for r in rows}.values(), key=lambda r: int(r[0]))
    df = sr.compute_indicators([r[:7] for r in rows])
    num = lambda col: [float(x) for x in df[col].tolist()]
    return {"ms": [int(x) + INTERVAL_MS[interval] for x in df["timestamp"].tolist()],
            "o": num("open"), "h": num("high"), "l": num("low"), "c": num("close"), "atr": num("atr"),
            "vs": num("vol_spike"), "bull": (df["ema20"] > df["ema50"]).tolist()}


def daily_sma200(rows):
    """Closed daily rows → (close times, SMA200 of the close; NaN until 200 bars)."""
    close = pd.Series([float(r[4]) for r in rows])
    return [int(r[0]) + INTERVAL_MS["D"] for r in rows], close.rolling(200).mean().tolist()


def idx(f, t_ms):
    """Index of the last bar of `f` closed at or before t_ms (-1 if none)."""
    return bisect_right(f["ms"], t_ms) - 1


# ----------------------------------------------------------------------------- levels
def zones(f, long):
    """Supply/demand zones: impulse bar k (body >= 1.5 ATR of bar k-1, closing beyond bar k-1's extreme);
    zone = bar k-1's range; first close beyond the far side (broken) and first touch after k."""
    o, h, l, c, atr = f["o"], f["h"], f["l"], f["c"], f["atr"]
    n, out = len(c), []
    for k in range(1, n):
        a0 = atr[k - 1]
        if not a0 > 0:
            continue
        if long and not (c[k] - o[k] >= IMPULSE_ATR * a0 and c[k] > h[k - 1]):
            continue
        if not long and not (o[k] - c[k] >= IMPULSE_ATR * a0 and c[k] < l[k - 1]):
            continue
        zl, zh = l[k - 1], h[k - 1]
        broken = next((m for m in range(k + 1, n) if (c[m] < zl if long else c[m] > zh)), n)
        touch = next((m for m in range(k + 1, n) if (l[m] <= zh if long else h[m] >= zl)), n)
        out.append((k, zl, zh, broken, touch))
    return out


def at_zone(f, zs, j, price, long):
    a = f["atr"][j]
    if not a > 0:
        return False
    for k, zl, zh, broken, touch in zs:
        if not (j - LOOKBACK <= k <= j - 2) or broken <= j:
            continue
        lo, hi = (zl - 0.25 * a, zh + 0.5 * a) if long else (zl - 0.5 * a, zh + 0.25 * a)
        if not lo <= price <= hi:
            continue
        s = j                                   # start of the current visit
        while s - 1 > k and ((f["l"][s - 1] <= hi) if long else (f["h"][s - 1] >= lo)):
            s -= 1
        if s > k + 1 and touch >= s:            # price left and came back; first touch is this visit
            return True
    return False


def swings(f, long):
    x = f["l"] if long else f["h"]
    pick = min if long else max
    return [s for s in range(SWING_ORDER, len(x) - SWING_ORDER)
            if x[s] == pick(x[s - SWING_ORDER:s + SWING_ORDER + 1])]


def at_trendline(f, sw, j, price, long):
    a = f["atr"][j]
    if not a > 0:
        return False
    conf = [s for s in sw[:bisect_right(sw, j - SWING_ORDER)] if s >= j - LOOKBACK]
    if not conf:
        return False
    s2 = conf[-1]
    earlier = [s for s in conf if s <= s2 - MIN_SWING_GAP]
    if not earlier:
        return False
    s1 = earlier[-1]
    x = f["l"] if long else f["h"]
    if (x[s2] <= x[s1]) if long else (x[s2] >= x[s1]):
        return False                            # support must rise / resistance must fall
    line = lambda m: x[s1] + (x[s2] - x[s1]) * (m - s1) / (s2 - s1)
    for m in range(s2 + 1, j):
        am = f["atr"][m]
        if am > 0 and ((f["c"][m] < line(m) - 0.25 * am) if long else (f["c"][m] > line(m) + 0.25 * am)):
            return False
    d = (price - line(j)) / a
    return -0.25 <= d <= 0.75 if long else -0.75 <= d <= 0.25


# ----------------------------------------------------------------------------- the checklist
def points(f4, f1, daily, btc4, deriv, T, direction, sig_tf, zs=None, sw=None):
    """(points dict, price, 4h ATR) at signal close T, or None without enough bars.
    f4 / f1: `frame()` of the symbol's 4h / 1h bars; daily: `daily_sma200()`; btc4: BTC's 4h `frame()`
    (None → no point); deriv: `derivs_data.DerivIndex` (None → no funding / OI points); sig_tf '4h' / '1h'.
    zs / sw: precomputed `zones()` / `swings()` of f4 for this direction (computed here if None)."""
    long = direction == "long"
    sf = f4 if sig_tf == "4h" else f1
    i, j, i1 = idx(sf, T), idx(f4, T), idx(f1, T)
    if i < 24 or j < 1 or i1 < 0:
        return None
    price = sf["c"][i]
    p = {"trend_4h": f4["bull"][j] == long, "trend_1h": f1["bull"][i1] == long}
    dms, dsma = daily
    k = bisect_right(dms, T) - 1
    p["ma200_d"] = k >= 0 and not math.isnan(dsma[k]) and ((price > dsma[k]) if long else (price < dsma[k]))
    p["sd_zone"] = at_zone(f4, zones(f4, long) if zs is None else zs, j, price, long)
    p["trendline"] = at_trendline(f4, swings(f4, long) if sw is None else sw, j, price, long)
    b = idx(btc4, T) if btc4 else -1
    p["btc_4h"] = b >= 0 and btc4["bull"][b] == long
    fr = deriv.funding_at(T) if deriv else None
    p["funding"] = fr is not None and abs(fr) >= FUNDING_MIN and ((fr < 0) if long else (fr > 0))
    oi24 = deriv.oi_change_pct(T, 24) if deriv else None
    back = 6 if sig_tf == "4h" else 24
    px24 = (price / sf["c"][i - back] - 1) * 100 if sf["c"][i - back] else None
    p["oi_trapped"] = (oi24 is not None and px24 is not None and oi24 > MOVE_EPS
                       and ((px24 < -MOVE_EPS) if long else (px24 > MOVE_EPS)))
    p["volume"] = not math.isnan(sf["vs"][i]) and sf["vs"][i] >= 1.5
    return {k_: bool(v) for k_, v in p.items()}, price, f4["atr"][j]


def stamp(rows4, rows1, rows_d, btc_rows4, deriv, direction, sig_tf):
    """Live: the checklist on the scan's closed bars for a signal that fired on the last closed bar of
    `sig_tf`. Returns {"version", "t_ms", "score", "points"} or None."""
    f4, f1 = frame(rows4, "240"), frame(rows1, "60")
    sf = f4 if sig_tf == "4h" else f1
    if not sf["ms"]:
        return None
    T = sf["ms"][-1]
    got = points(f4, f1, daily_sma200(rows_d), frame(btc_rows4, "240") if btc_rows4 else None,
                 deriv, T, direction, sig_tf)
    if got is None:
        return None
    pts = got[0]
    return {"version": VERSION, "t_ms": T, "score": sum(pts.values()), "points": pts}
