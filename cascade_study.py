#!/usr/bin/env python
"""
cascade_study.py — pre-registered study (logs/backtest_reports/prereg_cascade_20261021.md):
the top-down cascade — 4h flow (EMA20 vs EMA50) → 1h confirms → a 30m liquidity sweep against the
flow, reclaimed → 15m entry trigger — simulated with the harness's `sim_trade_limit` (one trade
model) against random twins, over four periods of the 2026-10-21 365-day harness caches
(30m bars built from the 15m bars). Offline. RESEARCH ONLY (zero Claude tokens, no orders).

Run:  source venv/bin/activate && python cascade_study.py
Out:  logs/backtest_reports/cascade_YYYYMMDD.md
"""
import argparse
import json
import random
import time
from bisect import bisect_left
from datetime import datetime, timezone
from pathlib import Path

import checklist as ck
import signal_rules as sr
from mtf_entry_study import sim

BASE = Path(__file__).resolve().parent
CACHE = BASE / "logs/backtest_cache/unified"
REPORT_DIR = BASE / "logs/backtest_reports"
TAG = "20251021_20261021"
M15, M30 = 900_000, 1_800_000
_d = lambda y, m, d: int(datetime(y, m, d, tzinfo=timezone.utc).timestamp() * 1000)
PERIODS = (("OLDER", _d(2025, 11, 15)), ("TRAIN", _d(2026, 3, 27)), ("TEST", _d(2026, 7, 20)),
           ("H", _d(2026, 9, 24)))
SWEEP_BARS, PIERCE_ATR, WICK_FRAC = 20, 0.15, 0.5
WAIT_15M, TRIGGER_LOOKBACK = 8, 4
STOP_PAD_ATR, STOP_FLOOR_ATR = 0.1, 0.5
TARGET_R, WINDOW_15M = 2.0, 96
DEDUP_MS = 12 * 3_600_000
TWINS, SEED = 3, 31


def period(t_ms):
    name = None
    for p, start in PERIODS:
        if t_ms >= start:
            name = p
    return name


# ----------------------------------------------------------------------------- bars
def load(sym, iv):
    p = CACHE / f"{sym}_{iv}_{TAG}.json"
    return sorted({int(r[0]): r for r in json.loads(p.read_text())}.values(), key=lambda r: int(r[0])) if p.exists() else None


def to30(rows15):
    """Two consecutive 15m bars → one 30m bar [ts, o, h, l, c, volume, turnover]; incomplete pairs dropped."""
    by = {}
    for r in rows15:
        by.setdefault(int(r[0]) // M30 * M30, []).append(r)
    out = []
    for t in sorted(by):
        a = by[t]
        if len(a) != 2 or int(a[0][0]) != t:
            continue
        out.append([t, a[0][1], max(float(a[0][2]), float(a[1][2])), min(float(a[0][3]), float(a[1][3])),
                    a[1][4], float(a[0][5]) + float(a[1][5]), float(a[0][6]) + float(a[1][6])])
    return out


def sweeps(rows30):
    """Per 30m bar: (close_ms, long_sweep, short_sweep, low, high, close, atr)."""
    df = sr.compute_indicators(rows30)
    prior_low = df["low"].shift(1).rolling(SWEEP_BARS).min()
    prior_high = df["high"].shift(1).rolling(SWEEP_BARS).max()
    o, h, l, c, a = (df[k].tolist() for k in ("open", "high", "low", "close", "atr"))
    out = []
    for i, ts in enumerate(df["timestamp"].tolist()):
        rng, pl, ph = h[i] - l[i], prior_low.iloc[i], prior_high.iloc[i]
        ok = rng > 0 and a[i] > 0 and pl == pl and ph == ph
        lng = ok and pl - l[i] >= PIERCE_ATR * a[i] and c[i] > pl and min(o[i], c[i]) - l[i] >= WICK_FRAC * rng
        sht = ok and h[i] - ph >= PIERCE_ATR * a[i] and c[i] < ph and h[i] - max(o[i], c[i]) >= WICK_FRAC * rng
        out.append((int(ts) + M30, bool(lng), bool(sht), l[i], h[i], c[i], a[i]))
    return out


# ----------------------------------------------------------------------------- entry
def enter(ts, m, start_ms, direction, stop0, atr30, trigger=True):
    """(result | None, status). trigger=False → the next 15m open (diagnostic)."""
    j = bisect_left(ts, start_ms)
    short = direction == "short"

    def fill(i_entry):
        fwd = m[i_entry:i_entry + WINDOW_15M]
        if len(fwd) < 4:
            return None, "no_data"
        e, stop, floor = fwd[0]["open"], stop0, STOP_FLOOR_ATR * atr30
        if (short and stop - e < floor) or ((not short) and e - stop < floor):
            stop = e + floor if short else e - floor
        r = sim(direction, e, stop, atr30, TARGET_R, fwd)
        return r, ("filled" if r else "unfilled")

    if not trigger:
        return fill(j)
    for k in range(WAIT_15M):
        i = j + k
        if i >= len(m) - 1 or i - TRIGGER_LOOKBACK < 0:
            return None, "no_trigger"
        b = m[i]
        if (short and b["high"] >= stop0) or ((not short) and b["low"] <= stop0):
            return None, "invalidated"
        prior = m[i - TRIGGER_LOOKBACK:i]
        if (b["close"] < min(p["low"] for p in prior)) if short else (b["close"] > max(p["high"] for p in prior)):
            return fill(i + 1)
    return None, "no_trigger"


# ----------------------------------------------------------------------------- study
def stats(rs):
    rs = [r for r in rs if r]
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
    rng = random.Random(SEED)
    symbols = sorted({t["symbol"] for t in json.loads((REPORT_DIR / "unified_20261021_365d_trades.json").read_text())})
    setups, twins, status, skipped = [], [], {}, []
    for s in symbols:
        r4, r1, r15 = load(s, "240"), load(s, "60"), load(s, "15")
        if not (r4 and r1 and r15):
            skipped.append(s)
            continue
        f4, f1 = ck.frame(r4, "240"), ck.frame(r1, "60")
        ts = [int(r[0]) for r in r15]
        m = [{"ts": int(r[0]), "open": float(r[1]), "high": float(r[2]), "low": float(r[3]), "close": float(r[4])}
             for r in r15]
        sw = sweeps(to30(r15))
        by_per = {}
        for k, x in enumerate(sw):
            p = period(x[0])
            if p and k >= SWEEP_BARS + 14:
                by_per.setdefault(p, []).append(k)
        last = {}
        for k, (T, lng, sht, lo, hi, close, atr) in enumerate(sw):
            per = period(T)
            if not per or k < SWEEP_BARS + 14:
                continue
            j4, j1 = ck.idx(f4, T), ck.idx(f1, T)
            if j4 < 50 or j1 < 50:
                continue
            flow = "long" if f4["bull"][j4] else "short"
            if f1["bull"][j1] != (flow == "long"):
                continue
            if not (lng if flow == "long" else sht):
                continue
            if T - last.get(flow, -DEDUP_MS) < DEDUP_MS:
                continue
            last[flow] = T
            stop0 = lo - STOP_PAD_ATR * atr if flow == "long" else hi + STOP_PAD_ATR * atr
            r, st = enter(ts, m, T, flow, stop0, atr)
            status[st] = status.get(st, 0) + 1
            nxt, _ = enter(ts, m, T, flow, stop0, atr, trigger=False)
            setups.append({"sym": s, "t": T, "dir": flow, "per": per, "trig": r, "open": nxt})
            risk_pct = abs(close - stop0) / close
            for _ in range(TWINS):
                kk = rng.choice(by_per[per])
                T2, _, _, _, _, c2, a2 = sw[kk]
                d2 = rng.choice(("long", "short"))
                st2 = c2 * (1 - risk_pct) if d2 == "long" else c2 * (1 + risk_pct)
                twins.append({"per": per, "r": enter(ts, m, T2, d2, st2, a2)[0]})

    res = {}
    for p, _ in PERIODS:
        res[p] = {"n_setups": sum(1 for x in setups if x["per"] == p),
                  "trig": stats([x["trig"] for x in setups if x["per"] == p]),
                  "ctrl": stats([x["r"] for x in twins if x["per"] == p]),
                  "open": stats([x["open"] for x in setups if x["per"] == p]),
                  "dir": {d: stats([x["trig"] for x in setups if x["per"] == p and x["dir"] == d])
                          for d in ("long", "short")}}
    te, tr, old, h = (res[p]["trig"] for p in ("TEST", "TRAIN", "OLDER", "H"))
    a = te["n"] >= 30 and te["net"] > 0 and res["TEST"]["ctrl"]["n"] and te["net"] >= res["TEST"]["ctrl"]["net"] + 0.05
    b = tr["n"] > 0 and tr["net"] > 0
    c = old["n"] >= 30 and old["net"] > 0 and res["OLDER"]["ctrl"]["n"] and old["net"] >= res["OLDER"]["ctrl"]["net"] + 0.05
    h_thin = h["n"] < 15
    d = h_thin or h["net"] > 0
    verdict = ("PASS (holdout pending)" if h_thin else "PASS") if (a and b and c and d) else "NO"

    L = [f"# Top-down cascade study — 4h flow → 1h → 30m sweep → 15m entry ({args.date_tag})", ""]
    L.append("Pre-registration: `logs/backtest_reports/prereg_cascade_20261021.md` (written before this code). "
             f"Data: the 365-day harness caches (`*_{TAG}`), {len(symbols) - len(skipped)} symbols"
             + (f" (skipped, no complete cache: {', '.join(skipped)})" if skipped else "")
             + "; 30m bars built from 15m. Cells: n · profitable % · net R per trade (managed trade, limit entry, "
             "net of costs). Periods by the sweep bar's close: OLDER 2025-11-15 → 2026-03-26 · TRAIN → 07-19 · "
             "TEST → 09-23 · H → end.\n")
    L.append(f"## Verdict: **{verdict}**\n")
    L.append("Bar: TEST n ≥ 30, net > 0, ≥ control + 0.05R · TRAIN net > 0 · OLDER n ≥ 30, net > 0, ≥ control + 0.05R · "
             "H net > 0.\n")
    L.append("| period | setups | cascade, 15m trigger entry (judged) | random twins, same entry | next 15m open (diagnostic) |")
    L.append("|---|---|---|---|---|")
    for p, _ in PERIODS:
        r = res[p]
        L.append(f"| {p} | {r['n_setups']} | {fmt(r['trig'])} | {fmt(r['ctrl'])} | {fmt(r['open'])} |")
    L.append("\n| period | longs (judged entry) | shorts (judged entry) |")
    L.append("|---|---|---|")
    for p, _ in PERIODS:
        L.append(f"| {p} | {fmt(res[p]['dir']['long'])} | {fmt(res[p]['dir']['short'])} |")
    L.append("\n**15m entry outcomes:** " + ", ".join(f"{k} {v}" for k, v in sorted(status.items())) + ".\n")
    L.append(f"One judged trial; nothing was varied after the run. Control: {TWINS} random twins per setup, seed {SEED}.\n")
    L.append(f"_Generated by `cascade_study.py` in {time.time() - t0:.0f}s._\n")
    out = REPORT_DIR / f"cascade_{args.date_tag}.md"
    out.write_text("\n".join(L))
    print("\n".join(L[2:]))
    print(f"report: {out}")


if __name__ == "__main__":
    main()
