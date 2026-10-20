#!/usr/bin/env python
"""
indicator_study.py — pre-registered study (logs/backtest_reports/prereg_indicators_20261020.md):
MA200 (daily / 4h), Bollinger Bands (stretch, width) and Accumulation/Distribution (Chaikin A/D, OBV).

Part A: each indicator as a filter on the 1,884 live-rule signals of the 2026-09-23 unified backtest —
the best bucket is chosen on TRAIN and read on TEST. Part B: two stand-alone Bollinger rules on 4h bars
(band fade, squeeze breakout), simulated with the harness's trade model, plus a random-entry reference.
Offline (harness caches + the xs daily cache). RESEARCH ONLY (zero Claude tokens, no orders).

Run:  source venv/bin/activate && python indicator_study.py
Out:  logs/backtest_reports/indicators_YYYYMMDD.md
"""
import argparse
import json
import random
import time
from bisect import bisect_left, bisect_right
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import signal_rules as sr
import unified_backtest as ub
from mtf_entry_study import LIVE, bars, sim

BASE = Path(__file__).resolve().parent
TRADES = BASE / "logs/backtest_reports/unified_20260923_trades.json"
CACHE = BASE / "logs/backtest_cache"
REPORT_DIR = BASE / "logs/backtest_reports"
TEST_FROM = int(datetime(2026, 7, 20, tzinfo=timezone.utc).timestamp() * 1000)
BB_N, BB_K = 20, 2.0
WIDTH_RANK_BARS = 120
SLOPE_BARS = 10
MIN_TRAIN_BUCKET = 50
B_START = 130
B_STOP_ATR = 1.5
TWINS = 3
SEED = 17
H4 = 14_400_000
DAY = 86_400_000


# ----------------------------------------------------------------------------- indicators
def frame(sym, iv):
    rows = json.loads((CACHE / "unified" / f"{sym}_{iv}_20260327_20260923.json").read_text())
    rows = sorted({int(r[0]): r for r in rows}.values(), key=lambda r: int(r[0]))
    df = sr.compute_indicators([r[:7] for r in rows])
    mid = df["close"].rolling(BB_N).mean()
    sd = df["close"].rolling(BB_N).std(ddof=0)
    df["bb_up"], df["bb_lo"] = mid + BB_K * sd, mid - BB_K * sd
    df["pctb"] = (df["close"] - df["bb_lo"]) / (df["bb_up"] - df["bb_lo"])
    df["width"] = (df["bb_up"] - df["bb_lo"]) / mid
    df["width_rank"] = df["width"].rolling(WIDTH_RANK_BARS).apply(lambda x: float((x <= x[-1]).mean()), raw=True)
    hl = (df["high"] - df["low"]).replace(0, np.nan)
    mfm = (((df["close"] - df["low"]) - (df["high"] - df["close"])) / hl).fillna(0.0)
    df["ad"] = (mfm * df["volume"]).cumsum()
    df["obv"] = (np.sign(df["close"].diff()).fillna(0.0) * df["volume"]).cumsum()
    df["ad_chg"] = df["ad"] - df["ad"].shift(SLOPE_BARS)
    df["obv_chg"] = df["obv"] - df["obv"].shift(SLOPE_BARS)
    df["sma200"] = df["close"].rolling(200).mean()
    df["close_ms"] = df["timestamp"] + ub.INTERVAL_MS[iv]
    return df


def daily_sma200(sym):
    rows = sorted(json.loads((CACHE / f"xs_{sym}_D.json").read_text()), key=lambda r: int(r[0]))
    close = pd.Series([float(r[4]) for r in rows])
    return [int(r[0]) + DAY for r in rows], close.rolling(200).mean().tolist()


def at_close(df, ms):
    """Row of the last bar of `df` closed at or before `ms` (None if none)."""
    k = bisect_right(df["close_ms"].tolist(), ms) - 1
    return df.iloc[k] if k >= 0 else None


# ----------------------------------------------------------------------------- stats
def stats(rows):
    if not rows:
        return {"n": 0}
    n = len(rows)
    return {"n": n, "prof": 100 * sum(1 for r in rows if r["profitable"]) / n,
            "net": sum(r["net_blended_rr"] for r in rows) / n}


def fmt(s):
    return "n=0" if not s["n"] else f"n={s['n']} · {s['prof']:.1f}% · {s['net']:+.3f}R"


# ----------------------------------------------------------------------------- part A
def tag_signals(trades):
    frames, dsma = {}, {}
    for t in trades:
        s = t["symbol"]
        if s not in frames:
            frames[s] = {"240": frame(s, "240"), "60": frame(s, "60")}
            dsma[s] = daily_sma200(s)
        iv = "240" if t["tf"] == "4h" else "60"
        row = at_close(frames[s][iv], t["signal_ms"])
        h4 = at_close(frames[s]["240"], t["signal_ms"])
        short = t["direction"] == "short"
        tags = {}
        if row is not None:
            c = float(row["close"])
            dms, dvals = dsma[s]
            k = bisect_right(dms, t["signal_ms"]) - 1
            d200 = dvals[k] if k >= 0 else float("nan")
            if not np.isnan(d200):
                tags["ma200_d"] = "with" if (c < d200) == short else "against"
            if h4 is not None and pd.notna(h4["sma200"]):
                tags["ma200_4h"] = "with" if (c < float(h4["sma200"])) == short else "against"
            if pd.notna(row["pctb"]):
                st = float(row["pctb"]) if short else 1.0 - float(row["pctb"])
                tags["bb_stretch"] = "<0.5" if st < 0.5 else ("0.5-1.0" if st <= 1.0 else ">1.0")
            if pd.notna(row["width_rank"]):
                wr = float(row["width_rank"])
                tags["bb_width"] = "squeeze" if wr <= 0.2 else ("wide" if wr >= 0.8 else "normal")
            for k_, col in (("ad_slope", "ad_chg"), ("obv_slope", "obv_chg")):
                if pd.notna(row[col]):
                    tags[k_] = "confirming" if (float(row[col]) < 0) == short and float(row[col]) != 0 else "not"
        t["_tags"] = tags
    return trades


FILTERS = {"ma200_d": ["with", "against"], "ma200_4h": ["with", "against"],
           "bb_stretch": ["<0.5", "0.5-1.0", ">1.0"], "bb_width": ["squeeze", "normal", "wide"],
           "ad_slope": ["confirming", "not"], "obv_slope": ["confirming", "not"]}


def part_a(trades):
    res = lambda ts: stats([t["result"] for t in ts])
    train = [t for t in trades if t["signal_ms"] < TEST_FROM]
    test = [t for t in trades if t["signal_ms"] >= TEST_FROM]
    base = {"TRAIN": res(train), "TEST": res(test)}
    out = {}
    for f, buckets in FILTERS.items():
        cells = {b: {"TRAIN": res([t for t in train if t["_tags"].get(f) == b]),
                     "TEST": res([t for t in test if t["_tags"].get(f) == b])} for b in buckets}
        ok = [b for b in buckets if cells[b]["TRAIN"]["n"] >= MIN_TRAIN_BUCKET]
        pick = max(ok, key=lambda b: cells[b]["TRAIN"]["net"]) if ok else None
        te = cells[pick]["TEST"] if pick else {"n": 0}
        if pick and te["n"] >= 30 and te["net"] > base["TEST"]["net"]:
            v = "KEEP-CANDIDATE" if te["net"] > 0 else "HELPS-BUT-NEGATIVE"
        else:
            v = "NO"
        cov = sum(1 for t in trades if f in t["_tags"])
        out[f] = {"cells": cells, "pick": pick, "verdict": v, "coverage": cov}
    return base, out


# ----------------------------------------------------------------------------- part B
def part_b(symbols):
    rng = random.Random(SEED)
    trades = {"bb_fade": [], "bb_squeeze_break": []}
    ref = []
    for s in symbols:
        df = frame(s, "240")
        ts, m = bars(s)
        last = {}
        for i in range(B_START, len(df)):
            c, p = df.iloc[i], df.iloc[i - 1]
            if not (pd.notna(c["bb_up"]) and pd.notna(c["atr"]) and c["atr"] > 0):
                continue
            close = float(c["close"])
            fired = []
            if close > c["bb_up"]:
                fired.append(("bb_fade", "short", 1.5))
            elif close < c["bb_lo"]:
                fired.append(("bb_fade", "long", 1.5))
            if pd.notna(p["width_rank"]) and p["width_rank"] <= 0.2:
                if close > c["bb_up"]:
                    fired.append(("bb_squeeze_break", "long", 2.0))
                elif close < c["bb_lo"]:
                    fired.append(("bb_squeeze_break", "short", 2.0))
            close_ms = int(c["close_ms"])
            for rule, d, tr in fired:
                key = (rule, d)
                if key in last and close_ms < last[key] + ub.DEDUP_DAYS * DAY:
                    continue
                j = bisect_left(ts, close_ms)
                fwd = m[j:j + ub.WINDOW_CANDLES["4h"]]
                if len(fwd) < 4:
                    continue
                atr = float(c["atr"])
                entry = fwd[0]["open"]
                stop = entry - B_STOP_ATR * atr if d == "long" else entry + B_STOP_ATR * atr
                r = sim(d, entry, stop, atr, tr, fwd)
                if r is None:
                    continue
                last[key] = close_ms
                trades[rule].append(dict(r, _ms=close_ms, _dir=d))
                for _ in range(TWINS):            # random reference: same symbol, stop size and target
                    k = rng.randrange(B_START, len(df) - 2)
                    rc = df.iloc[k]
                    if not (pd.notna(rc["atr"]) and rc["atr"] > 0):
                        continue
                    jj = bisect_left(ts, int(rc["close_ms"]))
                    f2 = m[jj:jj + ub.WINDOW_CANDLES["4h"]]
                    if len(f2) < 4:
                        continue
                    rd = rng.choice(("long", "short"))
                    e2, a2 = f2[0]["open"], float(rc["atr"])
                    r2 = sim(rd, e2, e2 - B_STOP_ATR * a2 if rd == "long" else e2 + B_STOP_ATR * a2, a2, tr, f2)
                    if r2:
                        ref.append(dict(r2, _ms=int(rc["close_ms"]), _rule=rule))
    out = {}
    for rule, rs in trades.items():
        tr_, te_ = [r for r in rs if r["_ms"] < TEST_FROM], [r for r in rs if r["_ms"] >= TEST_FROM]
        s_tr, s_te = stats(tr_), stats(te_)
        ok = s_te["n"] >= 30 and s_te["prof"] >= 60 and s_te["net"] > 0 and s_tr["n"] and s_tr["net"] > 0
        out[rule] = {"ALL": stats(rs), "TRAIN": s_tr, "TEST": s_te, "verdict": "CANDIDATE" if ok else "NO",
                     "dir": {d: stats([r for r in te_ if r["_dir"] == d]) for d in ("short", "long")},
                     "ref_TEST": stats([r for r in ref if r["_rule"] == rule and r["_ms"] >= TEST_FROM])}
    return out


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date-tag", default=datetime.now(timezone.utc).strftime("%Y%m%d"))
    args = ap.parse_args()
    t0 = time.time()
    trades = sorted((t for t in json.loads(TRADES.read_text()) if (t["signal"], t["tf"]) in LIVE),
                    key=lambda t: t["signal_ms"])
    tag_signals(trades)
    base, a = part_a(trades)
    b = part_b(sorted({t["symbol"] for t in trades}))

    L = [f"# Indicator study — MA200, Bollinger, Accumulation/Distribution ({args.date_tag})", ""]
    L.append("Pre-registration: `logs/backtest_reports/prereg_indicators_20261020.md` (written before this code). "
             f"Part A: {len(trades)} live-rule signals, 29 symbols, 2026-03-29 → 09-23; TEST from 2026-07-20. "
             "Cells: n · profitable % · net R per trade (managed trade, net of costs).\n")
    L.append(f"Baseline (all signals): TRAIN {fmt(base['TRAIN'])} · TEST {fmt(base['TEST'])}.\n")
    L.append("## Part A — filters on the live signals\n")
    L.append("| filter | picked on TRAIN | TRAIN (picked) | TEST (picked) | verdict | coverage |")
    L.append("|---|---|---|---|---|---|")
    for f, r in a.items():
        p = r["pick"]
        L.append(f"| `{f}` | {p or '–'} | {fmt(r['cells'][p]['TRAIN']) if p else '–'} | "
                 f"{fmt(r['cells'][p]['TEST']) if p else '–'} | **{r['verdict']}** | {r['coverage']}/{len(trades)} |")
    L.append("\n### Every bucket\n")
    L.append("| filter | bucket | TRAIN | TEST |")
    L.append("|---|---|---|---|")
    for f, r in a.items():
        for bkt, c in r["cells"].items():
            L.append(f"| `{f}` | {bkt}{' ←' if bkt == r['pick'] else ''} | {fmt(c['TRAIN'])} | {fmt(c['TEST'])} |")
    L.append("\n## Part B — stand-alone Bollinger rules (4h, trade model of the harness)\n")
    L.append("| rule | verdict | ALL | TRAIN | TEST | TEST shorts | TEST longs | random reference (TEST) |")
    L.append("|---|---|---|---|---|---|---|---|")
    for rule, r in b.items():
        L.append(f"| `{rule}` | **{r['verdict']}** | {fmt(r['ALL'])} | {fmt(r['TRAIN'])} | {fmt(r['TEST'])} | "
                 f"{fmt(r['dir']['short'])} | {fmt(r['dir']['long'])} | {fmt(r['ref_TEST'])} |")
    L.append("\n8 judged trials (6 filters, 2 rules); about one chance 'winner' is expected at 5%. Nothing was varied "
             f"after the run. Random reference: {TWINS} twins per trade (same symbol, 1.5 ATR stop, same target), seed {SEED}.\n")
    L.append(f"_Generated by `indicator_study.py` in {time.time() - t0:.0f}s._\n")
    out = REPORT_DIR / f"indicators_{args.date_tag}.md"
    out.write_text("\n".join(L))
    print("\n".join(L[2:]))
    print(f"report: {out}")


if __name__ == "__main__":
    main()
