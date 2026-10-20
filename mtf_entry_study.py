#!/usr/bin/env python
"""
mtf_entry_study.py — pre-registered study (logs/backtest_reports/prereg_mtf_entry_20261020.md):
top-down entry — 4h + 1h trends agree with the signal, then enter on a 15m confirmation.

V1 today's entry (limit at the next 15m open) · V2 + 4h/1h agreement · V3 V2 + 15m trigger
(judged) · V3b trigger without agreement + a random-entry control (diagnostics). Every variant is
simulated by the harness's own `sim_trade_limit` (trade_sim, one trade model). Offline: reads the
2026-09-23 unified trades and the harness's 15m cache. RESEARCH ONLY (zero Claude tokens, no orders).

Run:  source venv/bin/activate && python mtf_entry_study.py
Out:  logs/backtest_reports/mtf_entry_YYYYMMDD.md
"""
import argparse
import json
import random
import time
from bisect import bisect_left
from datetime import datetime, timezone
from pathlib import Path

import unified_backtest as ub

BASE = Path(__file__).resolve().parent
TRADES = BASE / "logs/backtest_reports/unified_20260923_trades.json"
CACHE = BASE / "logs/backtest_cache/unified"
REPORT_DIR = BASE / "logs/backtest_reports"
LIVE = {("range_reversion_short", "4h"), ("range_reversion_long", "4h"), ("failed_breakout_short", "4h"),
        ("trend_pullback_short", "4h"), ("liquidity_sweep_long", "1h"), ("rsi_bounce_long", "4h")}
WAIT_BARS = 16          # 4 hours of 15m bars to wait for the trigger
TRIGGER_LOOKBACK = 4    # close beyond the previous 4 bars' extreme
SWING_BARS = 8          # stop at the extreme of the trigger bar + the 7 before it
STOP_FLOOR_ATR = 0.25   # never closer than 0.25 x the signal timeframe's ATR
TWINS = 3
SEED = 11

_bars = {}


def bars(sym):
    if sym not in _bars:
        rows = json.loads((CACHE / f"{sym}_15_20260327_20260923.json").read_text())
        rows = sorted({int(r[0]): r for r in rows}.values(), key=lambda r: int(r[0]))
        _bars[sym] = ([int(r[0]) for r in rows],
                      [{"ts": int(r[0]), "open": float(r[1]), "high": float(r[2]), "low": float(r[3]),
                        "close": float(r[4])} for r in rows])
    return _bars[sym]


def sim(direction, entry, stop, atr, target_r, fwd):
    """The harness's default trade (limit at fwd[0].open, ENTRY_MODEL fill rules). None if unfilled."""
    if len(fwd) < 4:
        return None
    r = ub.sim_trade_limit({"entry": entry, "stop": stop, "atr": atr, "target_r": target_r,
                            "direction": direction, "_fwd": fwd}, 0.0, ub.LIMIT_WAIT_BARS)
    return r if r and r.get("filled") else None


def next_open(sym, close_ms, direction, stop, atr, target_r, tf):
    ts, m = bars(sym)
    j = bisect_left(ts, close_ms)
    fwd = m[j:j + ub.WINDOW_CANDLES[tf]]
    return sim(direction, fwd[0]["open"], stop, atr, target_r, fwd) if fwd else None


def triggered(sym, close_ms, direction, stop0, atr, target_r, tf):
    """(result | None, status) for the 15m-trigger entry. status: filled / no_trigger / invalidated / unfilled."""
    ts, m = bars(sym)
    j = bisect_left(ts, close_ms)
    short = direction == "short"
    for k in range(WAIT_BARS):
        i = j + k
        if i >= len(m) - 1 or i - SWING_BARS + 1 < 0:
            return None, "no_trigger"
        b = m[i]
        if (short and b["high"] >= stop0) or ((not short) and b["low"] <= stop0):
            return None, "invalidated"
        prior = m[i - TRIGGER_LOOKBACK:i]
        fired = (b["close"] < min(p["low"] for p in prior)) if short else (b["close"] > max(p["high"] for p in prior))
        if not fired:
            continue
        fwd = m[i + 1:i + 1 + ub.WINDOW_CANDLES[tf]]
        if len(fwd) < 4:
            return None, "no_trigger"
        entry = fwd[0]["open"]
        swing = m[i - SWING_BARS + 1:i + 1]
        stop = max(p["high"] for p in swing) if short else min(p["low"] for p in swing)
        if (short and stop > stop0) or ((not short) and stop < stop0):
            stop = stop0                                   # never more risk than the original stop
        floor = STOP_FLOOR_ATR * atr
        if (short and stop - entry < floor) or ((not short) and entry - stop < floor):
            stop = entry + floor if short else entry - floor
        r = sim(direction, entry, stop, atr, target_r, fwd)
        return r, ("filled" if r else "unfilled")
    return None, "no_trigger"


def stats(rows):
    rs = [r for r in rows if r]
    if not rs:
        return {"n": 0}
    n = len(rs)
    return {"n": n, "prof": 100 * sum(1 for r in rs if r["profitable"]) / n,
            "net": sum(r["net_blended_rr"] for r in rs) / n}


def fmt(s):
    return "n=0" if not s["n"] else f"n={s['n']} · {s['prof']:.1f}% · {s['net']:+.3f}R"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date-tag", default=datetime.now(timezone.utc).strftime("%Y%m%d"))
    args = ap.parse_args()
    t0 = time.time()
    trades = sorted((t for t in json.loads(TRADES.read_text()) if (t["signal"], t["tf"]) in LIVE),
                    key=lambda t: t["signal_ms"])
    test_start = trades[int(len(trades) * 0.6)]["signal_ms"]
    want = {"short": "bearish", "long": "bullish"}

    rows = []
    for t in trades:
        agree = t.get("h4_trend") == want[t["direction"]] and t.get("h1_trend") == want[t["direction"]]
        args_ = (t["symbol"], t["signal_ms"], t["direction"], t["stop"], t["atr"], t["target_r"], t["tf"])
        v1 = next_open(*args_)
        v3b, st = triggered(*args_)
        rows.append({"t": t, "test": t["signal_ms"] >= test_start, "agree": agree, "v1": v1,
                     "v3b": v3b, "trig_status": st})

    # reproduction check: V1 must match the recorded harness results
    diffs = [abs(r["v1"]["net_blended_rr"] - r["t"]["result"]["net_blended_rr"]) for r in rows if r["v1"]]
    n_unrep = sum(1 for r in rows if not r["v1"])

    # random-entry control
    rng = random.Random(SEED)
    ctrl = []
    for t in trades:
        ts, m = bars(t["symbol"])
        risk_pct, atr_pct = t["risk_pct"], t["atr"] / t["entry"]
        lo, hi = ts[SWING_BARS + 1], ts[-1] - (WAIT_BARS + ub.WINDOW_CANDLES[t["tf"]] + 4) * 900_000
        for _ in range(TWINS):
            c = rng.randrange(lo, hi) // 14_400_000 * 14_400_000
            d = rng.choice(("long", "short"))
            e0 = m[bisect_left(ts, c)]["open"]
            stop0 = e0 * (1 - risk_pct) if d == "long" else e0 * (1 + risk_pct)
            a = (t["symbol"], c, d, stop0, atr_pct * e0, t["target_r"], t["tf"])
            ctrl.append({"test": t["signal_ms"] >= test_start, "r1": next_open(*a), "r3": triggered(*a)[0]})

    def part(sel, key, src=rows):
        return stats([r[key] for r in src if sel(r)])

    periods = {"ALL": lambda r: True, "TRAIN": lambda r: not r["test"], "TEST": lambda r: r["test"]}
    res = {}
    for p, f in periods.items():
        res[("V1", p)] = part(f, "v1")
        res[("V2", p)] = part(lambda r, f=f: f(r) and r["agree"], "v1")
        res[("V3", p)] = part(lambda r, f=f: f(r) and r["agree"], "v3b")
        res[("V3b", p)] = part(f, "v3b")
        res[("R1", p)] = part(f, "r1", ctrl)
        res[("R3", p)] = part(f, "r3", ctrl)

    def dnet(a, b, p):
        return res[(a, p)]["net"] - res[(b, p)]["net"]

    d_sig, d_rnd = dnet("V3b", "V1", "TEST"), dnet("R3", "R1", "TEST")

    def verdict(v):
        te, tr = res[(v, "TEST")], res[(v, "TRAIN")]
        better = te["n"] and tr["n"] and te["net"] > res[("V1", "TEST")]["net"] and tr["net"] > res[("V1", "TRAIN")]["net"]
        control_ok = v != "V3" or d_sig > d_rnd
        if better and te["n"] >= 30 and te["net"] > 0 and control_ok:
            return "ADOPT-CANDIDATE"
        if better:
            return "BETTER-BUT-NEGATIVE" if te["net"] <= 0 else "NO (fails the control check)"
        return "NO"

    status = {}
    for r in rows:
        if r["agree"]:
            status[r["trig_status"]] = status.get(r["trig_status"], 0) + 1
    n_agree = sum(1 for r in rows if r["agree"])

    L = [f"# Top-down entry study — 4h + 1h direction, 15m trigger ({args.date_tag})", ""]
    L.append("Pre-registration: `logs/backtest_reports/prereg_mtf_entry_20261020.md` (written before this code). "
             f"{len(trades)} signals of the six live rule/timeframes, 2026-03-29 → 09-23, 29 symbols; "
             f"TEST from {datetime.fromtimestamp(test_start / 1000, tz=timezone.utc):%Y-%m-%d} (chronological 60/40). "
             "Net = managed trade net of costs (trade_sim, limit entry).\n")
    L.append(f"**Reproduction check (V1 vs recorded harness results):** {len(diffs)} re-simulated, {n_unrep} not "
             f"reproduced (unfilled); max |Δ net| = {max(diffs):.4f}R.\n")
    L.append("## Verdict\n")
    L.append("| variant | verdict | TRAIN | TEST |")
    L.append("|---|---|---|---|")
    for v, name in (("V2", "V2 — 4h + 1h agree"), ("V3", "V3 — agree + 15m trigger")):
        L.append(f"| {name} | **{verdict(v)}** | {fmt(res[(v, 'TRAIN')])} | {fmt(res[(v, 'TEST')])} |")
    L.append(f"\nBaseline V1 (today's entry): TRAIN {fmt(res[('V1', 'TRAIN')])} · TEST {fmt(res[('V1', 'TEST')])}.\n")
    L.append("## All variants (n · profitable % · net R per trade)\n")
    L.append("| variant | ALL | TRAIN | TEST |")
    L.append("|---|---|---|---|")
    names = {"V1": "V1 today's entry (next 15m open)", "V2": "V2 + 4h/1h agree (judged)",
             "V3": "V3 + agree + 15m trigger (judged)", "V3b": "V3b 15m trigger, no agreement (diagnostic)",
             "R1": "R1 random entries, next open (control)", "R3": "R3 random entries, 15m trigger (control)"}
    for v, name in names.items():
        L.append(f"| {name} | {fmt(res[(v, 'ALL')])} | {fmt(res[(v, 'TRAIN')])} | {fmt(res[(v, 'TEST')])} |")
    L.append(f"\n**Trigger outcomes on the {n_agree} agreeing signals:** "
             + ", ".join(f"{k} {v}" for k, v in sorted(status.items())) + ".\n")
    L.append(f"**Control (TEST):** the 15m trigger changes our signals' net by {d_sig:+.3f}R (V3b − V1) and random "
             f"entries' net by {d_rnd:+.3f}R (R3 − R1). V3 needs the first to exceed the second.\n")
    L.append("## By direction (TEST)\n")
    L.append("| variant | shorts | longs |")
    L.append("|---|---|---|")
    for v, key, agree_only in (("V1", "v1", False), ("V2", "v1", True), ("V3", "v3b", True)):
        cells = [fmt(stats([r[key] for r in rows if r["test"] and r["t"]["direction"] == d and (r["agree"] or not agree_only)]))
                 for d in ("short", "long")]
        L.append(f"| {v} | {cells[0]} | {cells[1]} |")
    L.append(f"\nTwo judged trials (V2, V3); V3b and the control are diagnostics; nothing was varied after the run. "
             f"Control: {TWINS} random twins per signal, seed {SEED}.\n")
    L.append(f"_Generated by `mtf_entry_study.py` in {time.time() - t0:.0f}s._\n")
    out = REPORT_DIR / f"mtf_entry_{args.date_tag}.md"
    out.write_text("\n".join(L))
    print("\n".join(L[2:]))
    print(f"report: {out}")


if __name__ == "__main__":
    main()
