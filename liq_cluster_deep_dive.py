"""Robustness companion to liq_cluster_backtest.py (first run 2026-09-10).

Re-runs the harness's exact tagging loop but captures per-trade rows, then
slices the NEAR (0.5-1.5 ATR) bucket the ways every past prototype was judged:
per-symbol concentration, per-direction, per-month, collector-uptime
sensitivity (is the effect a data-gap artifact?), and an alternate global
time-rank chrono split (the harness splits on per-symbol candle position).

Keep the slices IDENTICAL between runs so the ~2026-10-08 re-run is comparable
to the 2026-09-10 first pass. ANALYSIS ONLY — zero trading decisions.

Run:  venv/bin/python liq_cluster_deep_dive.py
"""
import os
import statistics as st
from collections import defaultdict

import historical_backtester as hb
from liq_cluster_backtest import (SYMBOLS, COST, load_liquidations,
                                  build_clusters, nearest_aligned)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "logs", "liquidations", "ci")
TARGET, WIN_H, BIN_ATR, MIN_FRAC, SPLIT = 1.5, 48.0, 0.5, 0.05, 0.60
SEP1_MS = 1788134400000  # 2026-09-01 00:00 UTC (Aug/Sep month cut)

liq, _files = load_liquidations(DATA_DIR)
# global uptime proxy: hours (any symbol) with >=1 collected event
global_hours = {t // 3600000 for ev in liq.values() for (t, _, _, _) in ev}

SIGS = {"tp_long": hb.signal_trend_pullback_long,
        "tp_short": hb.signal_trend_pullback_short}


def run(interval):
    win_ms = int(WIN_H * 3600 * 1000)
    rows = []
    for sym in SYMBOLS:
        ev = liq.get(sym)
        if not ev:
            continue
        cov_lo, cov_hi = ev[0][0], ev[-1][0]
        candles = hb.fetch_klines(sym, interval, limit=1000, use_cache=True)
        if not candles or len(candles) < 200:
            continue
        df = hb.compute_indicators_df(candles)
        for name, fn in SIGS.items():
            last = -13
            for i in range(50, len(df) - 48):
                if i - last < 12:
                    continue
                T = int(df.iloc[i]["timestamp"])
                if T - win_ms < cov_lo or T > cov_hi:
                    continue
                s = fn(df, i)
                if s is None:
                    continue
                last = i
                res = hb.evaluate_forward(df, i, s, TARGET, 48)
                if res is None:
                    continue
                atr = float(df.iloc[i]["atr_14"])
                clusters = build_clusters(ev, T - win_ms, T, BIN_ATR * atr, MIN_FRAC)
                d, _n = nearest_aligned(clusters, s["entry"], s["direction"], atr)
                b = ("none" if d is None else "at" if d <= 0.5
                     else "near" if d <= 1.5 else "far")
                wh = range(int((T - win_ms) // 3600000), int(T // 3600000) + 1)
                cov = sum(1 for h in wh if h in global_hours) / len(wh)
                rows.append(dict(sym=sym, dir=s["direction"], t=T, bucket=b,
                                 rr=res["actual_rr"], cov=cov,
                                 month=8 if T < SEP1_MS else 9))
    # global time-rank chrono position (harness uses per-symbol i/len(df))
    ts = sorted(x["t"] for x in rows)
    rank = {t: k for k, t in enumerate(ts)}
    for x in rows:
        x["pos"] = rank[x["t"]] / max(1, len(ts) - 1)
    return rows


def net(rs):
    if not rs:
        return "n=0"
    e = st.mean(x["rr"] for x in rs)
    wr = round(100 * sum(1 for x in rs if x["rr"] > 0) / len(rs))
    return f"n={len(rs):>3} wr{wr:>3} net {e - COST:+.3f}"


for ivl in ("60", "240"):
    rows = run(ivl)
    near = [x for x in rows if x["bucket"] == "near"]
    at = [x for x in rows if x["bucket"] == "at"]
    print(f"\n======== interval {ivl} — tagged {len(rows)} ========")
    print("NEAR by direction:  long:", net([x for x in near if x['dir'] == 'long']),
          "| short:", net([x for x in near if x['dir'] == 'short']))
    per = defaultdict(list)
    for x in near:
        per[x["sym"]].append(x)
    top = sorted(per.items(), key=lambda kv: -len(kv[1]))[:6]
    print("NEAR per-symbol:", "; ".join(f"{s}:{net(v)}" for s, v in top))
    print("NEAR by month:   Aug:", net([x for x in near if x['month'] == 8]),
          "| Sep:", net([x for x in near if x['month'] == 9]))
    hi = [x for x in rows if x["cov"] >= 0.5]
    lo = [x for x in rows if x["cov"] < 0.5]
    print(f"coverage>=50% of window hours: {len(hi)} trades | <50%: {len(lo)}")
    for lbl, grp in (("HIcov", hi), ("LOcov", lo)):
        b = {k: [x for x in grp if x["bucket"] == k] for k in ("at", "near", "far", "none")}
        print(f"  {lbl}: at {net(b['at'])} | near {net(b['near'])} | "
              f"far {net(b['far'])} | none {net(b['none'])}")
    trN = [x for x in near if x["pos"] < SPLIT]
    teN = [x for x in near if x["pos"] >= SPLIT]
    trA = [x for x in rows if x["pos"] < SPLIT]
    teA = [x for x in rows if x["pos"] >= SPLIT]
    print("chrono(by-time) split — ALL:", net(trA), "->", net(teA),
          "| NEAR:", net(trN), "->", net(teN))
    nh = [x for x in near if x["cov"] >= 0.5]
    print("NEAR & HIcov chrono:", net([x for x in nh if x['pos'] < SPLIT]),
          "->", net([x for x in nh if x['pos'] >= SPLIT]))
    if ivl == "240" and at:
        print("4h AT-bucket composition:",
              "; ".join(f"{x['sym']}/{x['dir'][0]}/{x['rr']:+.1f}" for x in at))
