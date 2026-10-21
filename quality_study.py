#!/usr/bin/env python
"""
quality_study.py — pre-registered study (logs/backtest_reports/prereg_quality_20261021.md):
quality trades with winners allowed to run. The checklist-score >= 5 candidates of the six live rules
(365-day unified run) traded three ways on one trade model (`trade_sim.simulate_limit`):
M0 today's trade (reference), Q1 a 2 x 4h-ATR trailing stop held up to 7 days, Q2 a 3R bracket held
up to 7 days — judged on the new quality yardstick (net R > 0, profit factor >= 1.3, >= 55% green weeks,
beats random twins) over four periods. Offline (harness caches). RESEARCH ONLY (zero Claude tokens, no orders).

Run:  source venv/bin/activate && python quality_study.py
Out:  logs/backtest_reports/quality_YYYYMMDD.md
"""
import argparse
import json
import random
import time
from bisect import bisect_left
from datetime import datetime, timezone

from pybit.unified_trading import HTTP

import trade_sim as ts
import unified_backtest as ub
from checklist_study import C_FROM, C_TAG, C_TRADES, CACHE, REPORT_DIR, Ctx, checklist, daily_sma200, frame
from mtf_entry_study import LIVE

_d = lambda y, m, d: int(datetime(y, m, d, tzinfo=timezone.utc).timestamp() * 1000)
CUTOFF = _d(2026, 10, 14)                 # every trade keeps a full 7-day window
PERIODS = (("OLDER", C_FROM), ("TRAIN", _d(2026, 3, 27)), ("TEST", _d(2026, 7, 20)), ("H", _d(2026, 9, 24)))
MIN_SCORE = 5
HOLD_15M = 7 * 96
TRAIL_ATR4, BRACKET_R = 2.0, 3.0
TWINS, SEED = 3, 41
VARIANTS = ("M0", "Q1", "Q2")


def period(t_ms):
    name = None
    for p, start in PERIODS:
        if t_ms >= start:
            name = p
    return name


def bars15(sym):
    p = CACHE / f"{sym}_15_{C_TAG}.json"
    if not p.exists():
        return None
    rows = sorted({int(r[0]): r for r in json.loads(p.read_text())}.values(), key=lambda r: int(r[0]))
    return ([int(r[0]) for r in rows],
            [{"ts": int(r[0]), "open": float(r[1]), "high": float(r[2]), "low": float(r[3]),
              "close": float(r[4])} for r in rows])


def run_q(fwd, direction, entry, stop, atr, atr4, variant):
    """Q1 / Q2 from the same limit entry and initial stop (prereg). None if unfilled."""
    risk = abs(entry - stop)
    if variant == "Q1":
        kw = {"target_2": None, "trail_dist": TRAIL_ATR4 * atr4}
    else:
        kw = {"target_2": entry + BRACKET_R * risk if direction == "long" else entry - BRACKET_R * risk}
    r = ts.simulate_limit(fwd, direction, stop, None, atr=atr, limit_offset_atr=ub.LIMIT_OFFSET_ATR,
                          limit_wait_bars=ub.LIMIT_WAIT_BARS, max_candles=HOLD_15M, candle_minutes=15,
                          trail=False, **kw)
    return r if r and r.get("filled") else None


# ----------------------------------------------------------------------------- yardstick
def quality(rows):
    """rows: [{"t", "net", "profitable", "hold"}] → the quality-yardstick readout."""
    rows = sorted((r for r in rows if r), key=lambda r: r["t"])
    n = len(rows)
    if not n:
        return {"n": 0}
    nets = [r["net"] for r in rows]
    wins, losses = [x for x in nets if x > 0], [x for x in nets if x <= 0]
    weeks = {}
    for r in rows:
        k = datetime.fromtimestamp(r["t"] / 1000, timezone.utc).isocalendar()[:2]
        weeks[k] = weeks.get(k, 0.0) + r["net"]
    eq = peak = dd = 0.0
    for x in nets:
        eq += x
        peak = max(peak, eq)
        dd = max(dd, peak - eq)
    return {"n": n, "net": sum(nets) / n, "prof": 100 * sum(1 for r in rows if r["profitable"]) / n,
            "pf": (sum(wins) / -sum(losses)) if losses and sum(losses) < 0 else float("inf"),
            "weeks": 100 * sum(1 for v in weeks.values() if v > 0) / len(weeks), "n_weeks": len(weeks),
            "dd": dd, "avg_w": sum(wins) / len(wins) if wins else 0.0,
            "avg_l": sum(losses) / len(losses) if losses else 0.0,
            "hold": sum(r["hold"] for r in rows) / n / 1440}


def fmt(s):
    if not s["n"]:
        return "n=0"
    return (f"n={s['n']} · {s['prof']:.0f}% · **{s['net']:+.3f}R** · PF {s['pf']:.2f} · "
            f"weeks+ {s['weeks']:.0f}% · DD {s['dd']:.1f}R")


def short(s):
    return "n=0" if not s["n"] else f"n={s['n']} · {s['prof']:.0f}% · {s['net']:+.3f}R"


def row(r, t_ms):
    return None if r is None else {"t": t_ms, "net": r["net_blended_rr"], "profitable": r["profitable"],
                                   "hold": r["hold_minutes"]}


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date-tag", default=datetime.now(timezone.utc).strftime("%Y%m%d"))
    args = ap.parse_args()
    t0 = time.time()
    rng = random.Random(SEED)
    client = HTTP(testnet=False, timeout=20)
    btc = frame("BTCUSDT", "240", C_TAG)
    trades = [t for t in json.loads(C_TRADES.read_text())
              if (t["signal"], t["tf"]) in LIVE and t["result"].get("filled") and C_FROM <= t["signal_ms"] < CUTOFF]
    ctxs, bars, out, twins, repro, skipped = {}, {}, [], [], [], set()
    for t in sorted(trades, key=lambda x: x["signal_ms"]):
        s, T, d = t["symbol"], t["signal_ms"], t["direction"]
        if s not in bars:
            bars[s] = bars15(s)
            if bars[s]:
                ctxs[s] = Ctx(client, s, C_TAG, btc, daily_sma200(client, s))
        if not bars[s]:
            skipped.add(s)
            continue
        got = checklist(ctxs[s], T, d, t["tf"])
        if got is None:
            continue
        pts, _, atr4 = got
        score = sum(pts.values())
        ts15, m = bars[s]
        j = bisect_left(ts15, T)
        t0_ = dict(t, _fwd=m[j:j + ub.WINDOW_CANDLES[t["tf"]]])
        m0 = ub.sim_trade_limit(t0_, ub.LIMIT_OFFSET_ATR, ub.LIMIT_WAIT_BARS)
        m0 = m0 if m0 and m0.get("filled") else None
        if m0:
            repro.append(abs(m0["net_blended_rr"] - t["result"]["net_blended_rr"]))
        fwd = m[j:j + ub.LIMIT_WAIT_BARS + HOLD_15M]
        res = {"M0": m0, **{v: run_q(fwd, d, t["entry"], t["stop"], t["atr"], atr4, v) for v in ("Q1", "Q2")}}
        per = period(T)
        out.append({"t": T, "per": per, "dir": d, "rule": f"{t['signal']} {t['tf']}", "score": score,
                    **{v: row(res[v], T) for v in VARIANTS}})
        if score >= MIN_SCORE:
            f4 = ctxs[s].f4
            lo, hi = dict(PERIODS)[per], next((st for p, st in PERIODS if st > dict(PERIODS)[per]), CUTOFF)
            k_lo, k_hi = bisect_left(f4["ms"], lo), bisect_left(f4["ms"], min(hi, CUTOFF))
            risk_pct = abs(t["entry"] - t["stop"]) / t["entry"]
            atr4_pct = atr4 / t["entry"]
            for _ in range(TWINS):
                if k_hi <= k_lo:
                    break
                kk = rng.randrange(k_lo, k_hi)
                T2 = f4["ms"][kk]
                j2 = bisect_left(ts15, T2)
                fwd2 = m[j2:j2 + ub.LIMIT_WAIT_BARS + HOLD_15M]
                if len(fwd2) < 8:
                    continue
                e2, d2 = fwd2[0]["open"], rng.choice(("long", "short"))
                st2 = e2 * (1 - risk_pct) if d2 == "long" else e2 * (1 + risk_pct)
                twins.append({"per": per, **{v: row(run_q(fwd2, d2, e2, st2, atr4_pct * e2, atr4_pct * e2, v), T2)
                                             for v in ("Q1", "Q2")}})

    hi_rows = [x for x in out if x["score"] >= MIN_SCORE]
    verdicts = {}
    for v in ("Q1", "Q2"):
        pooled = quality([x[v] for x in hi_rows])
        ctrl = quality([x[v] for x in twins])
        both = [x for x in hi_rows if x[v] and x["M0"]]
        m0_same = quality([x["M0"] for x in both])
        v_same = quality([x[v] for x in both])
        per_pos = sum(1 for p, _ in PERIODS
                      if (q := quality([x[v] for x in hi_rows if x["per"] == p]))["n"] and q["net"] > 0)
        ok = (pooled["n"] >= 100 and pooled["net"] > 0 and pooled["pf"] >= 1.3 and pooled["weeks"] >= 55
              and ctrl["n"] and pooled["net"] >= ctrl["net"] + 0.05 and v_same["net"] > m0_same["net"]
              and per_pos >= 3)
        verdicts[v] = ("PASS" if ok else "NO", pooled, ctrl, m0_same, v_same, per_pos)

    L = [f"# Quality trades, winners allowed to run ({args.date_tag})", ""]
    L.append("Pre-registration: `logs/backtest_reports/prereg_quality_20261021.md` (written before this code). "
             f"Trades: `{C_TRADES.name}`, six live rules, filled, signals 2025-11-15 → 2026-10-13; "
             f"checklist score ≥ {MIN_SCORE} = the judged population ({len(hi_rows)} of {len(out)} trades)"
             + (f"; skipped (no 15m cache): {', '.join(sorted(skipped))}" if skipped else "") + ". "
             "Cells: n · profitable % · net R per trade · profit factor · % of weeks green · max drawdown "
             "(sequential, R). One trade model (`trade_sim.simulate_limit`, maker entry, taker stops, funding).\n")
    L.append(f"**Reproduction check (M0 vs the recorded results):** {len(repro)} re-simulated, "
             f"max |Δ net| = {max(repro) if repro else float('nan'):.4f}R.\n")
    L.append("## Verdicts (new yardstick: net > 0, PF ≥ 1.3, ≥ 55% weeks green, ≥ random + 0.05R, > M0, "
             "net > 0 in ≥ 3 of 4 periods; pooled n ≥ 100)\n")
    L.append("| variant | verdict | score ≥ 5, pooled | random twins, same management | M0 on the same trades | periods net > 0 |")
    L.append("|---|---|---|---|---|---|")
    names = {"Q1": "Q1 — 2×ATR(4h) trailing stop, ≤ 7 days", "Q2": "Q2 — 3R bracket, ≤ 7 days"}
    for v, (verdict, pooled, ctrl, m0_same, v_same, per_pos) in verdicts.items():
        L.append(f"| {names[v]} | **{verdict}** | {fmt(pooled)} | {fmt(ctrl)} | {short(m0_same)} (vs {short(v_same)}) | "
                 f"{per_pos}/4 |")
    L.append(f"\nReference — M0 (today's trade) on the score ≥ 5 trades: {fmt(quality([x['M0'] for x in hi_rows]))}.\n")
    L.append("## By period (score ≥ 5)\n")
    L.append("| period | M0 today's trade | Q1 trailing | Q2 3R bracket | Q1 random | Q2 random |")
    L.append("|---|---|---|---|---|---|")
    for p, _ in PERIODS:
        rs = [x for x in hi_rows if x["per"] == p]
        tw = [x for x in twins if x["per"] == p]
        L.append(f"| {p} | {short(quality([x['M0'] for x in rs]))} | {short(quality([x['Q1'] for x in rs]))} | "
                 f"{short(quality([x['Q2'] for x in rs]))} | {short(quality([x['Q1'] for x in tw]))} | "
                 f"{short(quality([x['Q2'] for x in tw]))} |")
    L.append("\n## Shape of the trades (score ≥ 5, pooled)\n")
    L.append("| variant | avg win | avg loss | avg hold (days) |")
    L.append("|---|---|---|---|")
    for v in VARIANTS:
        q = quality([x[v] for x in hi_rows])
        if q["n"]:
            L.append(f"| {v} | {q['avg_w']:+.2f}R | {q['avg_l']:+.2f}R | {q['hold']:.1f} |")
    L.append("\n## Descriptive (not judged)\n")
    L.append("| cut | M0 | Q1 | Q2 |")
    L.append("|---|---|---|---|")
    cuts = [("all candidates (any score)", out)]
    cuts += [(f"score ≥ 5, {d}s", [x for x in hi_rows if x["dir"] == d]) for d in ("long", "short")]
    cuts += [(f"score ≥ 5, {ru}", [x for x in hi_rows if x["rule"] == ru]) for ru in sorted({x["rule"] for x in hi_rows})]
    for name, rs in cuts:
        L.append(f"| {name} | " + " | ".join(short(quality([x[v] for x in rs])) for v in VARIANTS) + " |")
    L.append(f"\nTrades overlap in time (up to 7-day holds); figures are per trade, not a portfolio. Two judged trials; "
             f"nothing was varied after the run. Control: {TWINS} random twins per score ≥ 5 trade, seed {SEED}.\n")
    L.append(f"_Generated by `quality_study.py` in {time.time() - t0:.0f}s._\n")
    out_p = REPORT_DIR / f"quality_{args.date_tag}.md"
    out_p.write_text("\n".join(L))
    print("\n".join(L[2:]))
    print(f"report: {out_p}")


if __name__ == "__main__":
    main()
