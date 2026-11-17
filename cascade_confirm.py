#!/usr/bin/env python
"""
cascade_confirm.py — pre-registered confirmation (logs/backtest_reports/prereg_cascade_wide_stop_20261117.md):
the top-down cascade of `cascade_study.py` (4h flow → 1h confirms → 30m liquidity sweep → 15m trigger)
with the stop at 2 × its original distance and T1 / T2 at 0.75R / 2R of the new risk, on the 2024-25
year (kline cache tag 20240701_20251019, written by orderbook_fade_confirm.py), against random twins.
Offline. RESEARCH ONLY (zero Claude tokens, no orders).

Run:  source venv/bin/activate && python cascade_confirm.py
Out:  logs/backtest_reports/cascade_wide_stop_YYYYMMDD.md
"""
import argparse
import json
import random
import time
from bisect import bisect_left
from collections import defaultdict
from datetime import datetime, timezone

import cascade_study as cs
import checklist as ck
import unified_backtest as ub

TAG = "20240701_20251019"
_d = lambda y, m, d: int(datetime(y, m, d, tzinfo=timezone.utc).timestamp() * 1000)
WIN_START, HALF_SPLIT, WIN_END = _d(2024, 10, 20), _d(2025, 4, 20), _d(2025, 10, 19)
SYMBOLS = ("1000BONKUSDT,1000PEPEUSDT,ADAUSDT,AKEUSDT,ARBUSDT,BTCUSDT,DOGEUSDT,ENAUSDT,ETHUSDT,"
           "FARTCOINUSDT,HBARUSDT,INJUSDT,NEARUSDT,ONDOUSDT,OPUSDT,PENGUUSDT,PUMPFUNUSDT,SANDUSDT,"
           "SOLUSDT,STRKUSDT,SUIUSDT,TRXUSDT,USELESSUSDT,USUSDT,WLDUSDT,XLMUSDT,XPLUSDT,XRPUSDT,"
           "ZECUSDT").split(",")
STOP_SCALE, T1_R, T2_R = 2.0, 0.75, cs.TARGET_R
# the frozen bar
MIN_N, MIN_GAP, MIN_PF, MIN_GREEN_WEEKS = 100, 0.05, 1.3, 0.55
WEEK_MS = 7 * 86_400_000


def half_of(t_ms):
    """'H1' / 'H2' inside the window, None outside."""
    if not (WIN_START <= t_ms < WIN_END):
        return None
    return "H1" if t_ms < HALF_SPLIT else "H2"


def load(sym, iv):
    p = cs.CACHE / f"{sym}_{iv}_{TAG}.json"
    return sorted({int(r[0]): r for r in json.loads(p.read_text())}.values(), key=lambda r: int(r[0])) if p.exists() else None


def trade(ts, m, start_ms, direction, stop0, atr):
    """The cascade's 15m-trigger fill (cs.enter's logic), then the ×2 stop. None when no trade."""
    j = bisect_left(ts, start_ms)
    short = direction == "short"
    for k in range(cs.WAIT_15M):
        i = j + k
        if i >= len(m) - 1 or i - cs.TRIGGER_LOOKBACK < 0:
            return None
        b = m[i]
        if (short and b["high"] >= stop0) or ((not short) and b["low"] <= stop0):
            return None                                   # the original stop invalidates the setup
        prior = m[i - cs.TRIGGER_LOOKBACK:i]
        if (b["close"] < min(p["low"] for p in prior)) if short else (b["close"] > max(p["high"] for p in prior)):
            return simulate(m[i + 1:i + 1 + cs.WINDOW_15M], direction, stop0, atr)
    return None


def simulate(fwd, direction, stop0, atr, scale=STOP_SCALE):
    """Floor the original stop (0.5 × ATR30 from the fill, as cascade_study), scale its distance, simulate."""
    if len(fwd) < 4:
        return None
    e, floor = fwd[0]["open"], cs.STOP_FLOOR_ATR * atr
    stop = stop0
    if direction == "short" and stop - e < floor:
        stop = e + floor
    if direction == "long" and e - stop < floor:
        stop = e - floor
    t = {"entry": e, "ref_price": e, "stop": stop, "atr": atr, "target_r": T2_R, "direction": direction, "_fwd": fwd}
    r = ub.sim_trade_limit(t, 0.0, ub.LIMIT_WAIT_BARS, t1_r=T1_R, t2_r=T2_R, stop_scale=scale)
    return r if r and r.get("filled") else None


def build(symbols=SYMBOLS):
    """(setups, twins, skipped): rows {t, sym, dir, half, net, profitable}."""
    rng = random.Random(cs.SEED)
    setups, twins, skipped = [], [], []
    for s in symbols:
        r4, r1, r15 = load(s, "240"), load(s, "60"), load(s, "15")
        if not (r4 and r1 and r15):
            skipped.append(s)
            continue
        f4, f1 = ck.frame(r4, "240"), ck.frame(r1, "60")
        ts = [int(r[0]) for r in r15]
        m = [{"ts": int(r[0]), "open": float(r[1]), "high": float(r[2]), "low": float(r[3]), "close": float(r[4])}
             for r in r15]
        sw = cs.sweeps(cs.to30(r15))
        by_half = defaultdict(list)
        for k, x in enumerate(sw):
            h = half_of(x[0])
            if h and k >= cs.SWEEP_BARS + 14:
                by_half[h].append(k)
        last = {}
        for k, (T, lng, sht, lo, hi, close, atr) in enumerate(sw):
            h = half_of(T)
            if not h or k < cs.SWEEP_BARS + 14:
                continue
            j4, j1 = ck.idx(f4, T), ck.idx(f1, T)
            if j4 < 50 or j1 < 50:
                continue
            flow = "long" if f4["bull"][j4] else "short"
            if f1["bull"][j1] != (flow == "long") or not (lng if flow == "long" else sht):
                continue
            if T - last.get(flow, -cs.DEDUP_MS) < cs.DEDUP_MS:
                continue
            last[flow] = T
            stop0 = lo - cs.STOP_PAD_ATR * atr if flow == "long" else hi + cs.STOP_PAD_ATR * atr
            r = trade(ts, m, T, flow, stop0, atr)
            if r:
                setups.append(_row(T, s, flow, h, r))
            risk_pct = abs(close - stop0) / close
            for _ in range(cs.TWINS):
                kk = rng.choice(by_half[h])
                T2, _, _, _, _, c2, a2 = sw[kk]
                d2 = rng.choice(("long", "short"))
                st2 = c2 * (1 - risk_pct) if d2 == "long" else c2 * (1 + risk_pct)
                r2 = trade(ts, m, T2, d2, st2, a2)
                if r2:
                    twins.append(_row(T2, s, d2, h, r2))
    return setups, twins, skipped


def _row(t, sym, direction, half, r):
    return {"t": t, "sym": sym, "dir": direction, "half": half,
            "net": float(r["net_blended_rr"]), "profitable": bool(r["profitable"])}


def stats(rows):
    n = len(rows)
    if not n:
        return {"n": 0}
    net = [r["net"] for r in rows]
    gain, loss = sum(x for x in net if x > 0), -sum(x for x in net if x < 0)
    weeks = defaultdict(float)
    for r in rows:
        weeks[r["t"] // WEEK_MS] += r["net"]
    return {"n": n, "prof": sum(r["profitable"] for r in rows) / n, "net": sum(net) / n,
            "pf": gain / loss if loss else float("inf"),
            "green_weeks": sum(1 for v in weeks.values() if v > 0) / len(weeks)}


def grade(setups, twins):
    """(verdict, checks) under the frozen bar."""
    a, c = stats(setups), stats(twins)
    halves = {h: stats([r for r in setups if r["half"] == h]) for h in ("H1", "H2")}
    checks = {
        "n": a["n"] >= MIN_N,
        "net": a["n"] > 0 and a["net"] > 0,
        "beats_random": a["n"] > 0 and c["n"] > 0 and a["net"] >= c["net"] + MIN_GAP,
        "pf": a["n"] > 0 and a["pf"] >= MIN_PF,
        "green_weeks": a["n"] > 0 and a["green_weeks"] >= MIN_GREEN_WEEKS,
        "both_halves": all(s["n"] > 0 and s["net"] > 0 for s in halves.values()),
    }
    if all(checks.values()):
        return "PASS", checks
    if checks["n"] and checks["net"] and checks["beats_random"] and checks["both_halves"]:
        return "WEAK", checks
    return "NO", checks


def fmt(s):
    if not s["n"]:
        return "n=0"
    return (f"n={s['n']} · {100 * s['prof']:.1f}% · {s['net']:+.3f}R · PF {s['pf']:.2f} · "
            f"weeks+ {100 * s['green_weeks']:.0f}%")


def write_report(date_tag, setups, twins, skipped, verdict, checks, elapsed):
    L = [f"# Cascade with a 2× stop — confirmation on the 2024-25 year ({date_tag})", "",
         "Pre-registration: `logs/backtest_reports/prereg_cascade_wide_stop_20261117.md` (committed before this code). "
         f"Data: kline cache `*_{TAG}`, {len(SYMBOLS) - len(skipped)} symbols"
         + (f" (skipped, no cache: {', '.join(skipped)})" if skipped else "")
         + ". Window: 30m sweep bars closing 2024-10-20 → 2025-10-19 (H1 < 2025-04-20 ≤ H2). "
           "Cells: n · profitable % · net R per trade (managed trade, limit entry, net of costs) · PF · weeks green.", "",
         f"## Verdict: **{verdict}**", "",
         f"Bar: n ≥ {MIN_N} · net > 0 · ≥ random + {MIN_GAP}R · PF ≥ {MIN_PF} · ≥ {100 * MIN_GREEN_WEEKS:.0f}% weeks green · "
         "net > 0 in both halves (PASS); the first, second, third and last only → WEAK.", "",
         "| check | result |", "|---|---|"]
    L += [f"| {k} | {'✓' if v else '✗'} |" for k, v in checks.items()]
    L += ["", "| slice | cascade, ×2 stop | random twins, same rules | gap |", "|---|---|---|---|"]

    def line(name, f):
        a, c = stats([r for r in setups if f(r)]), stats([r for r in twins if f(r)])
        gap = f"{a['net'] - c['net']:+.3f}R" if a["n"] and c["n"] else "–"
        L.append(f"| {name} | {fmt(a)} | {fmt(c)} | {gap} |")

    line("all", lambda r: True)
    for h in ("H1", "H2"):
        line(h, lambda r, h=h: r["half"] == h)
    for d in ("long", "short"):
        line(f"{d}s", lambda r, d=d: r["dir"] == d)
        for h in ("H1", "H2"):
            line(f"{d}s {h}", lambda r, d=d, h=h: r["dir"] == d and r["half"] == h)
    L += ["", "One judged trial; nothing was varied after the run. Control: 3 random twins per setup, seed 31.",
          "", f"_Generated by `cascade_confirm.py` in {elapsed:.0f}s._"]
    out = cs.REPORT_DIR / f"cascade_wide_stop_{date_tag}.md"
    out.write_text("\n".join(L) + "\n")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--date-tag", default=datetime.now(timezone.utc).strftime("%Y%m%d"))
    args = ap.parse_args(argv)
    t0 = time.time()
    setups, twins, skipped = build()
    verdict, checks = grade(setups, twins)
    out = write_report(args.date_tag, setups, twins, skipped, verdict, checks, time.time() - t0)
    print(f"verdict {verdict} → {out}")


if __name__ == "__main__":
    main()
