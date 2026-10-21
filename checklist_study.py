#!/usr/bin/env python
"""
checklist_study.py — pre-registered study (logs/backtest_reports/prereg_checklist_20261021.md):
the discretionary trader's checklist, computed mechanically — 4h and 1h trend, MA200, supply/demand
zones, trendlines, plus the Orion-style market numbers (BTC trend, funding, open interest, volume).

Arm A: the 9-point score as the selector of our live-rule candidates (primary 2026-03-29 → 09-23 +
an untouched holdout 09-24 → 10-19). Arm B: the trader's method on its own at every 4h close — trend
4h + 1h, MA200, at a zone or trendline, score ≥ 6 — entered on the 15m trigger of
`mtf_entry_study.py`, against random twins. One trade model (`ub.sim_trade_limit`).
Klines from the harness caches; funding/OI for the holdout and daily candles fetched from Bybit's
public API (cached). RESEARCH ONLY (zero Claude tokens, no orders).

Run:  source venv/bin/activate && python checklist_study.py
Out:  logs/backtest_reports/checklist_YYYYMMDD.md
"""
import argparse
import json
import math
import random
import time
from bisect import bisect_left
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from pybit.unified_trading import HTTP

import checklist as ck
import derivs_data as dd
import unified_backtest as ub
from checklist import ITEMS, idx
from mtf_entry_study import LIVE, STOP_FLOOR_ATR, SWING_BARS, TRIGGER_LOOKBACK, WAIT_BARS, sim

BASE = Path(__file__).resolve().parent
PRIMARY = BASE / "logs/backtest_reports/unified_20260923_trades.json"
HOLDOUT = BASE / "logs/backtest_reports/scalp_study_20261019_trades.json"
CACHE = BASE / "logs/backtest_cache/unified"
REPORT_DIR = BASE / "logs/backtest_reports"
P_TAG, H_TAG = "20260327_20260923", "20260422_20261019"
DAY, H4 = 86_400_000, 14_400_000
TEST_FROM = int(datetime(2026, 7, 20, tzinfo=timezone.utc).timestamp() * 1000)
H_FROM = int(datetime(2026, 9, 24, tzinfo=timezone.utc).timestamp() * 1000)
LOOKBACK = ck.LOOKBACK
B_STOP_ATR, B_TARGET_R, B_MIN_SCORE = 1.5, 2.0, 6
TWINS, SEED = 3, 21


# ----------------------------------------------------------------------------- data
def frame(sym, iv, tag):
    p = CACHE / f"{sym}_{iv}_{tag}.json"
    return ck.frame(json.loads(p.read_text()), iv) if p.exists() else None


def bars15(sym, tag):
    rows = sorted({int(r[0]): r for r in json.loads((CACHE / f"{sym}_15_{tag}.json").read_text())}.values(),
                  key=lambda r: int(r[0]))
    return ([int(r[0]) for r in rows],
            [{"ts": int(r[0]), "open": float(r[1]), "high": float(r[2]), "low": float(r[3]),
              "close": float(r[4])} for r in rows])


def daily_sma200(client, sym):
    return ck.daily_sma200(ub.fetch_closed_klines(client, sym, "D", 700))


def derivs(client, sym, tag):
    """Funding/OI from the harness cache of this period (`tag`), else fetched fresh (the holdout)."""
    fp, op = CACHE / f"{sym}_funding_{tag}.json", CACHE / f"{sym}_oi_1h_{tag}.json"
    if fp.exists() and op.exists():
        return dd.DerivIndex([tuple(x) for x in json.loads(fp.read_text())],
                             [tuple(x) for x in json.loads(op.read_text())], "1h")
    if tag == P_TAG:
        return None
    return dd.DerivIndex(dd.fetch_funding(client, sym, 185), dd.fetch_open_interest(client, sym, 185, "1h"), "1h")


class Ctx:
    """Everything the checklist needs for one symbol and one cache period."""

    def __init__(self, client, sym, tag, btc4, daily):
        self.f4, self.f1 = frame(sym, "240", tag), frame(sym, "60", tag)
        self.btc4, self.daily = btc4, daily
        self.deriv = derivs(client, sym, tag)
        self.zones = {d: ck.zones(self.f4, d == "long") for d in ("long", "short")}
        self.swings = {d: ck.swings(self.f4, d == "long") for d in ("long", "short")}


def checklist(ctx, T, direction, sig_tf):
    """(points dict, price, atr4) at signal close T — `checklist.points` on this symbol's context."""
    return ck.points(ctx.f4, ctx.f1, ctx.daily, ctx.btc4, ctx.deriv, T, direction, sig_tf,
                     zs=ctx.zones[direction], sw=ctx.swings[direction])


def period(t_ms):
    return "TRAIN" if t_ms < TEST_FROM else ("TEST" if t_ms < H_FROM else "H")


# ----------------------------------------------------------------------------- stats
def stats(rows):
    if not rows:
        return {"n": 0}
    n = len(rows)
    return {"n": n, "prof": 100 * sum(1 for r in rows if r["profitable"]) / n,
            "net": sum(r["net"] for r in rows) / n}


def fmt(s):
    return "n=0" if not s["n"] else f"n={s['n']} · {s['prof']:.1f}% · {s['net']:+.3f}R"


def spearman(x, y):
    if len(x) < 3:
        return float("nan")
    rx, ry = pd.Series(x).rank().to_numpy(), pd.Series(y).rank().to_numpy()
    return float(np.corrcoef(rx, ry)[0, 1])


# ----------------------------------------------------------------------------- arm A
def arm_a(client, btc, daily):
    rows, repro = [], {"trend_4h": [0, 0], "trend_1h": [0, 0], "funding": [0, 0], "oi_trapped": [0, 0],
                       "volume": [0, 0], "entry": [0, 0]}
    ctxs = {}
    want = {"long": "bullish", "short": "bearish"}
    prim = [t for t in json.loads(PRIMARY.read_text()) if (t["signal"], t["tf"]) in LIVE]
    for t in prim:
        s = t["symbol"]
        if (s, P_TAG) not in ctxs:
            ctxs[(s, P_TAG)] = Ctx(client, s, P_TAG, btc[P_TAG], daily[s])
        got = checklist(ctxs[(s, P_TAG)], t["signal_ms"], t["direction"], t["tf"])
        if got is None:
            continue
        pts, price, _ = got
        d = t["direction"]
        exp = {"trend_4h": t["h4_trend"] == want[d], "trend_1h": t["h1_trend"] == want[d],
               "funding": t["funding_side"] == "fading_crowd",
               "oi_trapped": t["oi_divergence"] == ("down_up" if d == "long" else "up_up"),
               "volume": t["vol_spike"] is not None and t["vol_spike"] >= 1.5}
        for k_, v in exp.items():
            repro[k_][0] += pts[k_] == v
            repro[k_][1] += 1
        repro["entry"][0] += abs(price - t["entry"]) <= 1e-9 * max(1.0, abs(price))
        repro["entry"][1] += 1
        rows.append({"t": t["signal_ms"], "dir": d, "rule": f"{t['signal']} {t['tf']}", "pts": pts,
                     "score": sum(pts.values()), "per": period(t["signal_ms"]),
                     "net": t["result"]["net_blended_rr"], "profitable": t["result"]["profitable"]})
    hold = json.loads(HOLDOUT.read_text())["B"]
    for b in hold:
        if b["signal_ms"] < H_FROM or (b["signal"], b["tf"]) not in LIVE or not b["B0"]:
            continue
        s = b["symbol"]
        if (s, H_TAG) not in ctxs:
            ctxs[(s, H_TAG)] = Ctx(client, s, H_TAG, btc[H_TAG], daily[s])
        got = checklist(ctxs[(s, H_TAG)], b["signal_ms"], b["direction"], b["tf"])
        if got is None:
            continue
        pts = got[0]
        rows.append({"t": b["signal_ms"], "dir": b["direction"], "rule": f"{b['signal']} {b['tf']}", "pts": pts,
                     "score": sum(pts.values()), "per": "H", "net": b["B0"][0], "profitable": b["B0"][1]})
    train_scores = [r["score"] for r in rows if r["per"] == "TRAIN"]
    n_thr = int(math.ceil(np.percentile(train_scores, 75)))
    res = {}
    for per in ("TRAIN", "TEST", "H"):
        rs = [r for r in rows if r["per"] == per]
        res[per] = {"all": stats(rs), "pick": stats([r for r in rs if r["score"] >= n_thr]),
                    "rho": spearman([r["score"] for r in rs], [r["net"] for r in rs])}
    tr, te, h = res["TRAIN"], res["TEST"], res["H"]
    a = (te["pick"]["n"] >= 30 and te["pick"]["net"] > 0 and te["pick"]["net"] >= te["all"]["net"] + 0.05)
    b_ = tr["pick"]["n"] > 0 and tr["pick"]["net"] > tr["all"]["net"]
    c = tr["rho"] > 0 and te["rho"] > 0
    h_thin = h["pick"]["n"] < 15
    d = h_thin or (h["pick"]["net"] > h["all"]["net"])
    if a and b_ and c and d:
        verdict = "PASS (holdout pending)" if h_thin else "PASS"
    elif b_ and c and te["pick"]["n"] and te["pick"]["net"] > te["all"]["net"]:
        verdict = "BETTER-BUT-NEGATIVE" if te["pick"]["net"] <= 0 else "NO"
    else:
        verdict = "NO"
    return rows, res, n_thr, verdict, repro


# ----------------------------------------------------------------------------- arm B
def trigger_entry(bars, close_ms, direction, stop0, atr, target_r):
    """mtf_entry_study.triggered on a given 15m series. (result | None, status)."""
    ts, m = bars
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
        fwd = m[i + 1:i + 1 + ub.WINDOW_CANDLES["4h"]]
        if len(fwd) < 4:
            return None, "no_trigger"
        entry = fwd[0]["open"]
        swing = m[i - SWING_BARS + 1:i + 1]
        stop = max(p["high"] for p in swing) if short else min(p["low"] for p in swing)
        if (short and stop > stop0) or ((not short) and stop < stop0):
            stop = stop0
        floor = STOP_FLOOR_ATR * atr
        if (short and stop - entry < floor) or ((not short) and entry - stop < floor):
            stop = entry + floor if short else entry - floor
        r = sim(direction, entry, stop, atr, target_r, fwd)
        return r, ("filled" if r else "unfilled")
    return None, "no_trigger"


def next_open_entry(bars, close_ms, direction, stop0, atr, target_r):
    ts, m = bars
    j = bisect_left(ts, close_ms)
    fwd = m[j:j + ub.WINDOW_CANDLES["4h"]]
    return sim(direction, fwd[0]["open"], stop0, atr, target_r, fwd) if len(fwd) >= 4 else None


def arm_b(client, btc, daily, symbols):
    rng = random.Random(SEED)
    setups, twins, status = [], [], {}
    for s in symbols:
        ctx = Ctx(client, s, H_TAG, btc[H_TAG], daily[s])
        bars = bars15(s, H_TAG)
        f4 = ctx.f4
        last = {}
        by_per = {}
        for j in range(LOOKBACK, len(f4["c"])):
            by_per.setdefault(period(f4["ms"][j]), []).append(j)
        for j in range(LOOKBACK, len(f4["c"])):
            T = f4["ms"][j]
            for d in ("long", "short"):
                if T - last.get(d, -DAY) < DAY:
                    continue
                got = checklist(ctx, T, d, "4h")
                if got is None:
                    continue
                pts, price, atr = got
                if not (pts["trend_4h"] and pts["trend_1h"] and pts["ma200_d"]
                        and (pts["sd_zone"] or pts["trendline"]) and sum(pts.values()) >= B_MIN_SCORE):
                    continue
                if not atr > 0:
                    continue
                last[d] = T
                stop0 = price - B_STOP_ATR * atr if d == "long" else price + B_STOP_ATR * atr
                r, st = trigger_entry(bars, T, d, stop0, atr, B_TARGET_R)
                status[st] = status.get(st, 0) + 1
                no = next_open_entry(bars, T, d, stop0, atr, B_TARGET_R)
                per = period(T)
                setups.append({"sym": s, "t": T, "dir": d, "per": per, "pts": pts, "trig": r, "open": no})
                risk_pct = B_STOP_ATR * atr / price
                for _ in range(TWINS):
                    jj = rng.choice(by_per[per])
                    rd = rng.choice(("long", "short"))
                    e0 = f4["c"][jj]
                    st0 = e0 * (1 - risk_pct) if rd == "long" else e0 * (1 + risk_pct)
                    twins.append({"per": per, "r": trigger_entry(bars, f4["ms"][jj], rd, st0, atr / price * e0,
                                                                B_TARGET_R)[0]})
    def st_of(rs):
        return stats([{"net": r["net_blended_rr"], "profitable": r["profitable"]} for r in rs if r])
    res = {}
    for per in ("TRAIN", "TEST", "H"):
        res[per] = {"trig": st_of([x["trig"] for x in setups if x["per"] == per]),
                    "open": st_of([x["open"] for x in setups if x["per"] == per]),
                    "ctrl": st_of([x["r"] for x in twins if x["per"] == per]),
                    "n_setups": sum(1 for x in setups if x["per"] == per),
                    "dir": {d: st_of([x["trig"] for x in setups if x["per"] == per and x["dir"] == d])
                            for d in ("long", "short")}}
    tr, te, h = res["TRAIN"]["trig"], res["TEST"]["trig"], res["H"]["trig"]
    ctrl = res["TEST"]["ctrl"]
    ok = (te["n"] >= 30 and te["net"] > 0 and tr["n"] and tr["net"] > 0
          and ctrl["n"] and te["net"] >= ctrl["net"] + 0.05)
    h_thin = h["n"] < 15
    if ok and (h_thin or h["net"] > 0):
        verdict = "PASS (holdout pending)" if h_thin else "PASS"
    else:
        verdict = "NO"
    return res, verdict, status


# ----------------------------------------------------------------------------- confirmation (older data)
C_TRADES = REPORT_DIR / "unified_20261021_365d_trades.json"
C_TAG = "20251021_20261021"
C_FROM = int(datetime(2025, 11, 15, tzinfo=timezone.utc).timestamp() * 1000)
C_TO = int(datetime(2026, 3, 27, tzinfo=timezone.utc).timestamp() * 1000)
C_MIN = 5


def confirm(date_tag):
    """prereg_checklist_confirm_20261021.md: score >= 5 on the 365-day run's signals 2025-11-15 → 2026-03-26."""
    t0 = time.time()
    client = HTTP(testnet=False, timeout=20)
    btc = frame("BTCUSDT", "240", C_TAG)
    want = {"long": "bullish", "short": "bearish"}
    trades = [t for t in json.loads(C_TRADES.read_text())
              if (t["signal"], t["tf"]) in LIVE and t["result"].get("filled") and C_FROM <= t["signal_ms"] < C_TO]
    ctxs, rows = {}, []
    repro = {k: [0, 0] for k in ("trend_4h", "trend_1h", "funding", "oi_trapped", "volume")}
    have_derivs = 0
    for t in trades:
        s, T, d = t["symbol"], t["signal_ms"], t["direction"]
        if s not in ctxs:
            ctxs[s] = Ctx(client, s, C_TAG, btc, daily_sma200(client, s))
        ctx = ctxs[s]
        got = checklist(ctx, T, d, t["tf"])
        if got is None:
            continue
        pts = got[0]
        exp = {"trend_4h": t["h4_trend"] == want[d], "trend_1h": t["h1_trend"] == want[d],
               "funding": t["funding_side"] == "fading_crowd",
               "oi_trapped": t["oi_divergence"] == ("down_up" if d == "long" else "up_up"),
               "volume": t["vol_spike"] is not None and t["vol_spike"] >= 1.5}
        for k_, v in exp.items():
            repro[k_][0] += pts[k_] == v
            repro[k_][1] += 1
        have_derivs += bool(ctx.deriv and ctx.deriv.funding_at(T) is not None
                            and ctx.deriv.oi_change_pct(T, 24) is not None)
        rows.append({"t": T, "dir": d, "rule": f"{t['signal']} {t['tf']}", "score": sum(pts.values()), "pts": pts,
                     "month": datetime.fromtimestamp(T / 1000, timezone.utc).strftime("%Y-%m"),
                     "net": t["result"]["net_blended_rr"], "profitable": t["result"]["profitable"]})
    n = len(rows)
    cov = have_derivs / n if n else 0.0
    rep_ok = all(v[1] and v[0] / v[1] >= 0.95 for v in repro.values())
    s_all, s_hi = stats(rows), stats([r for r in rows if r["score"] >= C_MIN])
    lsl = [r for r in rows if r["rule"] == "liquidity_sweep_long 1h"]
    l_all, l_hi = stats(lsl), stats([r for r in lsl if r["score"] >= C_MIN])
    if not n or cov < 0.90 or not rep_ok:
        primary = secondary = f"INVALID (funding/OI coverage {100 * cov:.0f}%, reproduction ok: {rep_ok})"
    else:
        primary = "PASS" if (s_hi["n"] >= 30 and s_hi["net"] > 0 and s_hi["net"] >= s_all["net"] + 0.05) else "FAIL"
        if l_hi["n"] < 30:
            secondary = f"thin (n={l_hi['n']} < 30), not judged"
        else:
            secondary = "PASS" if (l_hi["net"] > 0 and l_hi["net"] > l_all["net"]) else "FAIL"

    L = [f"# Trader's checklist — confirmation on older data ({date_tag})", ""]
    L.append("Pre-registration: `logs/backtest_reports/prereg_checklist_confirm_20261021.md` (written before the run). "
             f"Trades: `{C_TRADES.name}` (unified engine, 34 symbols), six live rules, filled, signals "
             f"2025-11-15 → 2026-03-26 → **{n} trades**. Checklist exactly as `checklist.py` / "
             "`prereg_checklist_20261021.md`. Cells: n · profitable % · net R per trade (managed trade, net of costs).\n")
    L.append(f"**Validity:** funding/OI present on {100 * cov:.0f}% of trades (need ≥ 90%); reproduction check "
             + ", ".join(f"{k} {v[0]}/{v[1]}" for k, v in repro.items()) + f" (need ≥ 95% each) → {'valid' if rep_ok and cov >= 0.9 else 'INVALID'}.\n")
    L.append("## Verdicts\n")
    L.append(f"- **Primary — score ≥ {C_MIN}: {primary}** — {fmt(s_hi)} vs all candidates {fmt(s_all)} "
             "(bar: n ≥ 30, net > 0, ≥ all + 0.05R)")
    L.append(f"- **Secondary — liquidity_sweep_long 1h, score ≥ {C_MIN}: {secondary}** — {fmt(l_hi)} vs all "
             f"liquidity_sweep_long {fmt(l_all)}\n")
    L.append("## Descriptive (not judged)\n")
    L.append("| cut | result |")
    L.append("|---|---|")
    for lo, hi, name in ((0, 2, "score 0–2"), (3, 3, "score 3"), (4, 4, "score 4"), (5, 5, "score 5"),
                         (6, 9, "score 6–9")):
        L.append(f"| {name} | {fmt(stats([r for r in rows if lo <= r['score'] <= hi]))} |")
    for d in ("long", "short"):
        rs = [r for r in rows if r["dir"] == d]
        L.append(f"| {d}s: all → score ≥ {C_MIN} | {fmt(stats(rs))} → {fmt(stats([r for r in rs if r['score'] >= C_MIN]))} |")
    for ru in sorted({r["rule"] for r in rows}):
        rs = [r for r in rows if r["rule"] == ru]
        L.append(f"| {ru}: all → score ≥ {C_MIN} | {fmt(stats(rs))} → {fmt(stats([r for r in rs if r['score'] >= C_MIN]))} |")
    for m in sorted({r["month"] for r in rows}):
        rs = [r for r in rows if r["month"] == m]
        L.append(f"| {m}: all → score ≥ {C_MIN} | {fmt(stats(rs))} → {fmt(stats([r for r in rs if r['score'] >= C_MIN]))} |")
    L.append(f"\nSurvivorship: the 34 symbols are today's; coins listed after the window add nothing. Nothing was varied after the run.\n")
    L.append(f"_Generated by `checklist_study.py --confirm` in {time.time() - t0:.0f}s._\n")
    out = REPORT_DIR / f"checklist_confirm_{date_tag}.md"
    out.write_text("\n".join(L))
    print("\n".join(L[2:]))
    print(f"report: {out}")


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date-tag", default=datetime.now(timezone.utc).strftime("%Y%m%d"))
    ap.add_argument("--confirm", action="store_true",
                    help="score >= 5 on the 365-day run's older window (prereg_checklist_confirm_20261021.md)")
    args = ap.parse_args()
    if args.confirm:
        return confirm(args.date_tag)
    t0 = time.time()
    client = HTTP(testnet=False, timeout=20)
    btc = {tag: frame("BTCUSDT", "240", tag) for tag in (P_TAG, H_TAG)}
    prim_syms = {t["symbol"] for t in json.loads(PRIMARY.read_text())}
    h_syms = sorted({b["symbol"] for b in json.loads(HOLDOUT.read_text())["B"]})
    daily = {s: daily_sma200(client, s) for s in sorted(prim_syms | set(h_syms))}

    rows, ra, n_thr, va, repro = arm_a(client, btc, daily)
    rb, vb, status = arm_b(client, btc, daily, h_syms)

    L = [f"# Trader's checklist study ({args.date_tag})", ""]
    L.append("Pre-registration: `logs/backtest_reports/prereg_checklist_20261021.md` (written before this code). "
             "Cells: n · profitable % · net R per trade (managed trade, limit entry, net of costs). "
             "TRAIN < 2026-07-20 ≤ TEST < 2026-09-24 ≤ H (holdout, untouched by every filter study).\n")
    L.append("**Reproduction check** (my checklist vs the harness's recorded fields, primary trades): "
             + ", ".join(f"{k} {v[0]}/{v[1]} ({100 * v[0] / max(1, v[1]):.1f}%)" for k, v in repro.items()) + ".\n")
    L.append("## Verdicts\n")
    L.append(f"- **Arm A — checklist score picks our candidates (score ≥ {n_thr}, the TRAIN 75th percentile): {va}**")
    L.append(f"- **Arm B — the trader's method on its own, 15m trigger entry: {vb}**\n")
    L.append("## Arm A — score as the selector\n")
    L.append("| period | all candidates | score ≥ N (pick) | Spearman ρ(score, net R) |")
    L.append("|---|---|---|---|")
    for per in ("TRAIN", "TEST", "H"):
        r = ra[per]
        L.append(f"| {per} | {fmt(r['all'])} | {fmt(r['pick'])} | {r['rho']:+.3f} |")
    L.append("\n### By score\n")
    L.append("| score | TRAIN | TEST | H |")
    L.append("|---|---|---|---|")
    for lo, hi, name in ((0, 2, "0–2"), (3, 3, "3"), (4, 4, "4"), (5, 5, "5"), (6, 6, "6"), (7, 9, "7–9")):
        cells = [fmt(stats([r for r in rows if r["per"] == per and lo <= r["score"] <= hi]))
                 for per in ("TRAIN", "TEST", "H")]
        L.append(f"| {name} | " + " | ".join(cells) + " |")
    L.append("\n### Each item alone (point earned vs not) — descriptive\n")
    L.append("| item | coverage | TRAIN with / without | TEST with / without | H with / without |")
    L.append("|---|---|---|---|---|")
    for it in ITEMS:
        cells = []
        for per in ("TRAIN", "TEST", "H"):
            rs = [r for r in rows if r["per"] == per]
            cells.append(f"{fmt(stats([r for r in rs if r['pts'][it]]))} / {fmt(stats([r for r in rs if not r['pts'][it]]))}")
        share = 100 * sum(1 for r in rows if r["pts"][it]) / len(rows)
        L.append(f"| {it} | {share:.0f}% earn it | " + " | ".join(cells) + " |")
    L.append("\n### By direction (pick vs all)\n")
    L.append("| period | longs: all → pick | shorts: all → pick |")
    L.append("|---|---|---|")
    for per in ("TRAIN", "TEST", "H"):
        cells = []
        for d in ("long", "short"):
            rs = [r for r in rows if r["per"] == per and r["dir"] == d]
            cells.append(f"{fmt(stats(rs))} → {fmt(stats([r for r in rs if r['score'] >= n_thr]))}")
        L.append(f"| {per} | " + " | ".join(cells) + " |")
    L.append("\n## Arm B — the trader's method on its own\n")
    L.append("Setup = 4h trend + 1h trend + MA200 side + (zone or trendline) + score ≥ 6, one per symbol and "
             "direction per 24 h, 30 symbols; entry = the 15m trigger; control = 3 random twins per setup.\n")
    L.append("| period | setups | 15m trigger entry (judged) | random twins, same entry | next-open entry (diagnostic) |")
    L.append("|---|---|---|---|---|")
    for per in ("TRAIN", "TEST", "H"):
        r = rb[per]
        L.append(f"| {per} | {r['n_setups']} | {fmt(r['trig'])} | {fmt(r['ctrl'])} | {fmt(r['open'])} |")
    L.append("\n| period | longs (trigger) | shorts (trigger) |")
    L.append("|---|---|---|")
    for per in ("TRAIN", "TEST", "H"):
        L.append(f"| {per} | {fmt(rb[per]['dir']['long'])} | {fmt(rb[per]['dir']['short'])} |")
    L.append("\n**Trigger outcomes:** " + ", ".join(f"{k} {v}" for k, v in sorted(status.items())) + ".\n")
    L.append(f"Two judged trials (Arm A, Arm B); everything else is descriptive. Nothing was varied after the run. "
             f"Control seed {SEED}. Daily candles cached by `ub.fetch_closed_klines` (logs/backtest_cache/unified/).\n")
    L.append(f"_Generated by `checklist_study.py` in {time.time() - t0:.0f}s._\n")
    out = REPORT_DIR / f"checklist_{args.date_tag}.md"
    out.write_text("\n".join(L))
    print("\n".join(L[2:]))
    print(f"report: {out}")


if __name__ == "__main__":
    main()
