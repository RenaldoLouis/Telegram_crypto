"""Bybit on-venue CVD (taker-flow) features from the cvd_collector minute buckets (2026-10-16).

`cvd_collector.py` writes one row per (minute, symbol): taker buy/sell base + quote volume and
trade count. This module turns that store into the per-bar flow feature the 2026-08-17 Binance
study found promising — `cvd_slope`, normalized net-flow momentum over K bars — so the unified
harness can test it on-venue, on the v13 rules, with the same trade simulator (roadmap fork #4,
Phase 2; pre-registered bar in progress.md 2026-10-16).

Definition (identical to cvd_backtest.add_deep_flow, k=6, 20-bar denominator), on VALID bars:
    delta_quote(bar) = taker buy quote − taker sell quote           (bar coverage ≥ MIN_COVERAGE)
    cvd_slope(bar)   = Σ delta over the last K valid bars / (mean |delta| over the last DENOM_WINDOW
                       valid bars × K)
A bar is valid when ≥ MIN_COVERAGE of its minutes carry a bucket (collector gaps → NaN, never 0),
and its delta is scaled by 1/coverage (the captured minutes are treated as a sample of the bar).
The K valid bars must lie within MAX_SPAN_BARS calendar bars, so a slope is always *recent*
momentum, not a sum across a collector outage. Research-only: no trading decision lives here.

Amendment 2026-10-16 (same day, BEFORE any bucket outcome was read — data-quality repair, see
progress.md): the first run used MIN_COVERAGE = 0.8 with raw deltas and produced ZERO valid 4h
bars (and 8% of 1h bars): within covered hours the collector captured a median 45 of 60 minutes
(pybit WS dropouts of 6–60 min), so only 12% of 4h bars reached 80% and no run of K valid bars
ever formed. MIN_COVERAGE = 0.5 + coverage-scaled deltas makes the test runnable; nothing else
changed.
"""
from __future__ import annotations

import bisect
import json
import math
from collections import defaultdict
from pathlib import Path

STORE_DIR = Path("logs/cvd/ci")
MINUTE_MS = 60_000
K_BARS = 6              # cvd_backtest.add_deep_flow default
DENOM_WINDOW = 20       # bars in the |delta| normaliser
MIN_DENOM_BARS = 10     # valid bars required before a slope is computed
MIN_COVERAGE = 0.5      # share of a bar's minutes that must carry a bucket (0.8 → 0.5, amendment above)
MAX_SPAN_BARS = 2 * K_BARS
NAN = float("nan")

_CACHE = {}


class CvdIndex:
    """Per-symbol sorted minute buckets with bisect lookup."""

    def __init__(self, per_symbol):
        # per_symbol: sym -> sorted list of (minute_ms, buy_q, sell_q)
        self.ts, self.buy, self.sell = {}, {}, {}
        for sym, rows in per_symbol.items():
            rows = sorted(rows)
            self.ts[sym] = [r[0] for r in rows]
            self.buy[sym] = [float(r[1]) for r in rows]
            self.sell[sym] = [float(r[2]) for r in rows]

    @property
    def symbols(self):
        return sorted(s for s in self.ts if self.ts[s])

    def span_ms(self):
        lo = min((t[0] for t in self.ts.values() if t), default=None)
        hi = max((t[-1] for t in self.ts.values() if t), default=None)
        return lo, hi

    def bar(self, symbol, start_ms, interval_ms):
        """(delta_quote, quote_volume, coverage) for the bar [start, start+interval), or None
        when the symbol is not in the store at all."""
        ts = self.ts.get(symbol)
        if not ts:
            return None
        i = bisect.bisect_left(ts, int(start_ms))
        j = bisect.bisect_left(ts, int(start_ms) + int(interval_ms))
        if j <= i:
            return (0.0, 0.0, 0.0)
        b = sum(self.buy[symbol][i:j])
        s = sum(self.sell[symbol][i:j])
        return (b - s, b + s, (j - i) / (interval_ms / MINUTE_MS))


def load_store(store_dir=None):
    """Load logs/cvd/ci/cvd_*.jsonl into a CvdIndex (cached per directory). Exact repeats of a
    (minute, symbol) bucket — the CI artifacts overlap at chain hand-overs — collapse to one."""
    d = Path(store_dir or STORE_DIR)
    key = str(d.resolve())
    if key in _CACHE:
        return _CACHE[key]
    per = defaultdict(dict)
    for f in sorted(d.glob("cvd_*.jsonl")):
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                t, sym = r.get("t"), r.get("sym")
                if not isinstance(t, (int, float)) or not sym:
                    continue
                per[sym][int(t)] = (float(r.get("buy_q", 0.0)), float(r.get("sell_q", 0.0)))
    idx = CvdIndex({sym: [(t, bq, sq) for t, (bq, sq) in m.items()] for sym, m in per.items()})
    _CACHE[key] = idx
    return idx


def slope_series(delta, k=K_BARS, win=DENOM_WINDOW, min_denom=MIN_DENOM_BARS, max_span=MAX_SPAN_BARS):
    """cvd_slope per bar from a per-bar delta list (NaN = invalid bar). Valid bars only; the K
    bars summed must sit within `max_span` calendar bars of the current bar."""
    n = len(delta)
    out = [NAN] * n
    valid = [i for i in range(n) if delta[i] == delta[i]]  # NaN != NaN
    for p, i in enumerate(valid):
        if p + 1 < k or p + 1 < min_denom:
            continue
        lastk = valid[p - k + 1:p + 1]
        if i - lastk[0] + 1 > max_span:
            continue
        den_idx = valid[max(0, p - win + 1):p + 1]
        den = sum(abs(delta[j]) for j in den_idx) / len(den_idx) * k
        if den <= 0:
            continue
        out[i] = sum(delta[j] for j in lastk) / den
    return out


def attach_to_df(df, index, symbol, interval_ms, k=K_BARS, win=DENOM_WINDOW, min_cov=MIN_COVERAGE):
    """Add cvd_delta / cvd_cov / cvd_slope columns to an indicator DataFrame whose `timestamp`
    is the bar OPEN time (same convention derivs_data.attach_to_df uses)."""
    ts = df["timestamp"].astype("int64").tolist()
    delta, cov = [], []
    for t in ts:
        r = index.bar(symbol, t, interval_ms) if index else None
        if r is None:
            delta.append(NAN)
            cov.append(0.0)
            continue
        d, _q, c = r
        cov.append(c)
        # captured minutes are a sample of the bar: scale to a full bar (amendment 2026-10-16)
        delta.append(d / c if c >= min_cov and c > 0 else NAN)
    df["cvd_delta"] = delta
    df["cvd_cov"] = cov
    df["cvd_slope"] = slope_series(delta, k, win)
    return df


def confirm_bucket(slope, direction, thr):
    """'confirm' = flow momentum aligned with the trade and |slope| >= thr; 'contra' = opposed;
    'neutral' = inside ±thr; 'na' = no valid slope (bar failed coverage or no data)."""
    if slope is None or (isinstance(slope, float) and math.isnan(slope)):
        return "na"
    if (direction == "long" and slope >= thr) or (direction == "short" and slope <= -thr):
        return "confirm"
    if (direction == "long" and slope <= -thr) or (direction == "short" and slope >= thr):
        return "contra"
    return "neutral"


def coverage_summary(index):
    """Hour coverage per symbol (share of hours in the store span with any bucket)."""
    lo, hi = index.span_ms()
    if lo is None:
        return {}
    span_h = int((hi - lo) // 3_600_000) + 1
    out = {}
    for sym in index.symbols:
        hours = {t // 3_600_000 for t in index.ts[sym]}
        out[sym] = round(len(hours) / span_h, 3)
    return out
