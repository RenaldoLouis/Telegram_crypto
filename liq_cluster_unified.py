#!/usr/bin/env python
"""
liq_cluster_unified.py — Part B of the pre-registered side-fix re-run
(logs/backtest_reports/prereg_liq_side_fix_20261021.md): fork A's liquidation-cluster tag on the
UNIFIED engine's trades (operating discipline #7), with Bybit's side read correctly ("Buy" = a long
was liquidated).

Every live-rule trade of the 2026-10-16 unified run (same 19 symbols as the liquidation store) whose
signal close and full 48 h trailing window lie inside the symbol's liquidation coverage is tagged with
its distance to the nearest direction-aligned cluster (long -> long-liq cluster at/below entry, short ->
short-liq cluster at/above), using the cluster builder of `liq_cluster_backtest.py` unchanged.
Metric: the managed trade (`net_blended_rr`, `profitable`). Global chrono split 60/40.
Offline (trades file + liquidation store). RESEARCH ONLY (zero Claude tokens, no orders).

Run:  source venv/bin/activate && python liq_cluster_unified.py
Out:  logs/backtest_reports/liq_cluster_unified_YYYYMMDD.md
"""
import argparse
import json
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from liq_cluster_backtest import build_clusters, load_liquidations, nearest_aligned
from mtf_entry_study import LIVE

BASE = Path(__file__).resolve().parent
TRADES = BASE / "logs/backtest_reports/unified_20261016_cvd_trades.json"
LIQ_DIR = BASE / "logs/liquidations/ci"
REPORT_DIR = BASE / "logs/backtest_reports"
WIN_MS = 48 * 3_600_000
BIN_ATR, MIN_FRAC, SPLIT = 0.5, 0.05, 0.60
GAP_R, MIN_TEST_N = 0.05, 30
BUCKETS = ("at (≤0.5 ATR)", "near (0.5–1.5 ATR)", "far (>1.5 ATR)", "no aligned cluster")


def stats(rows):
    if not rows:
        return {"n": 0}
    n = len(rows)
    return {"n": n, "prof": 100 * sum(1 for r in rows if r["profitable"]) / n,
            "net": sum(r["net_blended_rr"] for r in rows) / n}


def fmt(s):
    return "n=0" if not s["n"] else f"n={s['n']} · {s['prof']:.1f}% · {s['net']:+.3f}R"


def bucket(d):
    if d is None:
        return BUCKETS[3]
    return BUCKETS[0] if d <= 0.5 else BUCKETS[1] if d <= 1.5 else BUCKETS[2]


def tag(trades, liq, global_hours, flip):
    rows = []
    for t in trades:
        ev = liq.get(t["symbol"])
        T = int(t["signal_ms"])
        if not ev or T - WIN_MS < ev[0][0] or T > ev[-1][0]:
            continue
        atr = float(t["atr"])
        clusters = build_clusters(ev, T - WIN_MS, T, BIN_ATR * atr, MIN_FRAC)
        d, _ = nearest_aligned(clusters, float(t["entry"]), t["direction"], atr, flip=flip)
        hours = range((T - WIN_MS) // 3_600_000, T // 3_600_000 + 1)
        rows.append({"sym": t["symbol"], "rule": f"{t['signal']} {t['tf']}", "dir": t["direction"],
                     "t": T, "bucket": bucket(d), "cov": sum(h in global_hours for h in hours) / len(hours),
                     "profitable": bool(t["result"]["profitable"]),
                     "net_blended_rr": float(t["result"]["net_blended_rr"])})
    rows.sort(key=lambda r: r["t"])
    cut = rows[int(len(rows) * SPLIT)]["t"] if rows else 0
    for r in rows:
        r["half"] = "TRAIN" if r["t"] < cut else "TEST"
    return rows, cut


def halves(rows):
    return {h: stats([r for r in rows if r["half"] == h]) for h in ("TRAIN", "TEST")}


def verdict(all_h, near_h):
    te, tr = near_h["TEST"], near_h["TRAIN"]
    if te["n"] < MIN_TEST_N:
        return f"INCONCLUSIVE (NEAR TEST n={te['n']} < {MIN_TEST_N})"
    checks = [te["net"] >= 0, te["net"] >= all_h["TEST"]["net"] + GAP_R,
              tr["n"] > 0 and tr["net"] > all_h["TRAIN"]["net"]]
    return "PASS" if all(checks) else "FAIL"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date-tag", default=datetime.now(timezone.utc).strftime("%Y%m%d"))
    args = ap.parse_args()
    t0 = time.time()
    trades = [t for t in json.loads(TRADES.read_text())
              if (t["signal"], t["tf"]) in LIVE and t["result"].get("filled")]
    liq, files = load_liquidations(str(LIQ_DIR))
    global_hours = {t // 3_600_000 for ev in liq.values() for (t, _, _, _) in ev}

    res = {}
    for label, flip in (("corrected", False), ("control (old, wrong side)", True)):
        rows, cut = tag(trades, liq, global_hours, flip)
        near = [r for r in rows if r["bucket"] in BUCKETS[:2]]
        res[label] = {"rows": rows, "cut": cut, "all": halves(rows), "near": halves(near)}
        res[label]["verdict"] = verdict(res[label]["all"], res[label]["near"])

    main_rows = res["corrected"]["rows"]
    cut_day = datetime.fromtimestamp(res["corrected"]["cut"] / 1000, timezone.utc).strftime("%Y-%m-%d %H:%M")
    span = [datetime.fromtimestamp(main_rows[i]["t"] / 1000, timezone.utc).strftime("%Y-%m-%d")
            for i in (0, -1)] if main_rows else ["–", "–"]

    L = [f"# Liquidation clusters on the unified engine, side corrected ({args.date_tag})", ""]
    L.append("Pre-registration: `logs/backtest_reports/prereg_liq_side_fix_20261021.md` (Part B, written before "
             f"this code). Trades: `{TRADES.name}`, six live rules at their live timeframes, filled, with the signal "
             f"close and its 48 h window inside liquidation coverage → **{len(main_rows)} trades**, {span[0]} → "
             f"{span[1]}; liquidation store {len(files)} files. TEST = signals from {cut_day} UTC (last 40%). "
             "Cells: n · profitable % · net R per trade (managed trade, net of costs).\n")
    c = res["corrected"]
    L.append(f"**Verdict: {c['verdict']}** — bar: NEAR-aligned (≤1.5 ATR) TEST net ≥ 0 AND ≥ ALL TEST + "
             f"{GAP_R:.2f}R AND n ≥ {MIN_TEST_N}, AND NEAR > ALL on TRAIN.\n")
    L.append("| cut | TRAIN | TEST |")
    L.append("|---|---|---|")
    for label, r in res.items():
        L.append(f"| ALL ({label}) | {fmt(r['all']['TRAIN'])} | {fmt(r['all']['TEST'])} |")
        L.append(f"| **NEAR-aligned ≤1.5 ATR** ({label}) | {fmt(r['near']['TRAIN'])} | {fmt(r['near']['TEST'])} |")
    L.append(f"\nControl verdict (same bar, wrong side): {res['control (old, wrong side)']['verdict']}.\n")

    L.append("## Descriptive only (not judged)\n")
    L.append("| bucket | ALL | TRAIN | TEST | coverage ≥50% of window | coverage <50% |")
    L.append("|---|---|---|---|---|---|")
    for b in BUCKETS:
        rs = [r for r in main_rows if r["bucket"] == b]
        h = halves(rs)
        L.append(f"| {b} | {fmt(stats(rs))} | {fmt(h['TRAIN'])} | {fmt(h['TEST'])} | "
                 f"{fmt(stats([r for r in rs if r['cov'] >= 0.5]))} | {fmt(stats([r for r in rs if r['cov'] < 0.5]))} |")
    L.append("\n| slice | NEAR-aligned ≤1.5 ATR | rest |")
    L.append("|---|---|---|")
    groups = defaultdict(list)
    for r in main_rows:
        groups[("direction", r["dir"])].append(r)
        groups[("rule", r["rule"])].append(r)
    for (kind, key), rs in sorted(groups.items()):
        L.append(f"| {kind}: {key} | {fmt(stats([r for r in rs if r['bucket'] in BUCKETS[:2]]))} | "
                 f"{fmt(stats([r for r in rs if r['bucket'] not in BUCKETS[:2]]))} |")
    L.append("\nTwo harnesses, one primary cut each (Part A: `liq_cluster_backtest.py` 1h). Nothing was varied "
             "after the run.\n")
    L.append(f"_Generated by `liq_cluster_unified.py` in {time.time() - t0:.0f}s._\n")
    out = REPORT_DIR / f"liq_cluster_unified_{args.date_tag}.md"
    out.write_text("\n".join(L))
    print("\n".join(L[2:]))
    print(f"report: {out}")


if __name__ == "__main__":
    main()
