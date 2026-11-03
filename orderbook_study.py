"""Pre-registered study: resting order-book depth as a new input (2026-11-03).

Pre-registration: logs/backtest_reports/prereg_orderbook_20261103.md (written before this
code). Two tests on Binance depth snapshots (the free proxy; Bybit publishes none):

  A. the book as a FILTER on the six live rules' recorded trades (365-day harness file):
     aligned / neutral / against buckets of imb_b / tilt_b at the signal close, 8 variants,
     selected on the fit half (OLDER + TRAIN), graded on the unseen half (TEST + H);
  B. the book as a SIGNAL of its own at every closed 4h bar: imb_2 / tilt_2 beyond a
     threshold → trade in the book's direction with the live trade shape, 4 variants,
     random-side control and the flipped sign reported; same halves.

Offline: reads logs/backtest_cache/orderbook/ (orderbook_data.py) and the unified 15m/4h
caches. RESEARCH ONLY — zero trading decisions, no order API, zero hosted-model tokens.
Report → logs/backtest_reports/orderbook_<date>.md (+ _rows.json).
"""
from __future__ import annotations

import argparse
import json
import random
import time
from bisect import bisect_left
from collections import defaultdict
from datetime import datetime, timezone

import config
import orderbook_data as od
import trade_sim as ts
import unified_backtest as ub
from checklist_study import C_FROM, C_TAG, C_TRADES, REPORT_DIR, bars15, frame
from mtf_entry_study import LIVE
from quality_study import CUTOFF, PERIODS, quality

FIT, UNSEEN = ("OLDER", "TRAIN"), ("TEST", "H")
# Test A variants: (feature, band, threshold)
A_VARIANTS = tuple((f, b, thr) for f in ("imb", "tilt") for b in (1.0, 2.0) for thr in (0.10, 0.20))
A_FIT_MIN_ALIGNED, A_UNSEEN_MIN_ALIGNED, A_MIN_GAP, A_MIN_PF = 60, 30, 0.05, 1.3
# Test B variants: (feature, threshold) at band 2 %
B_VARIANTS = (("imb", 0.20), ("imb", 0.30), ("tilt", 0.10), ("tilt", 0.20))
B_BAND, B_STOP_ATR, B_T1_R, B_T2_R, B_WINDOW = 2.0, 1.0, 0.75, 2.0, ub.WINDOW_CANDLES["4h"]
B_MIN_N, B_MIN_PF, B_MIN_WEEKS, B_MIN_EDGE_OVER_RANDOM = 100, 1.3, 55.0, 0.05
CONTROL_DRAWS, SEED = 3, 7
TILT_BARS = 4           # 1 hour of 15m boundaries per side of the tilt
SCAN_LAG_MS = config.UB_SCAN_LAG_MIN * 60_000


# ----------------------------------------------------------------------------- features
def feature(idx: od.OrderBookIndex, sym: str, t_ms: int, kind: str, band: float):
    """imb_b(T) or tilt_b(T) per the pre-registration; None = no data."""
    if kind == "imb":
        row = idx.at(sym, t_ms)
        return od.imbalance(row, band) if row else None
    rows = idx.window(sym, t_ms, 2 * TILT_BARS)
    if len(rows) < 2 * TILT_BARS:
        return None
    vals = [od.imbalance(r, band) for r in rows]
    if any(v is None for v in vals):
        return None
    return sum(vals[TILT_BARS:]) / TILT_BARS - sum(vals[:TILT_BARS]) / TILT_BARS


def bucket(x, direction: str, thr: float) -> str:
    """aligned = the book leans the trade's way beyond thr (bid-heavy for a long, ask-heavy
    for a short); against = the opposite beyond thr; neutral otherwise; no_data if None."""
    if x is None:
        return "no_data"
    s = x if direction == "long" else -x
    return "aligned" if s > thr else ("against" if s < -thr else "neutral")


def period_of(t_ms: int):
    name = None
    for p, start in PERIODS:
        if t_ms >= start:
            name = p
    return name


def half_of(t_ms: int):
    p = period_of(t_ms)
    return "fit" if p in FIT else ("unseen" if p in UNSEEN else None)


def q(rows):
    return quality([r for r in rows if r])


# ----------------------------------------------------------------------------- test A
def run_test_a(idx: od.OrderBookIndex, trades: list[dict]):
    """Bucket every recorded live-rule trade under each variant. Returns (rows, table, verdict)."""
    rows = []
    for t in trades:
        T = t["signal_ms"]
        rec = {"t": T, "sym": t["symbol"], "rule": f"{t['signal']} {t['tf']}", "dir": t["direction"],
               "per": period_of(T), "half": half_of(T), "net": t["result"]["net_blended_rr"],
               "profitable": t["result"]["profitable"], "hold": t["result"]["hold_minutes"], "b": {}}
        for f, b, thr in A_VARIANTS:
            rec["b"][f"{f}_{b:g}_{thr:g}"] = bucket(feature(idx, t["symbol"], T, f, b), t["direction"], thr)
        rows.append(rec)

    def cell(sub, name, which):
        return q([r for r in sub if r["b"][name] == which])

    def with_data(sub, name):
        return [r for r in sub if r["b"][name] != "no_data"]

    table = {}
    for f, b, thr in A_VARIANTS:
        name = f"{f}_{b:g}_{thr:g}"
        ent = {}
        for half in ("fit", "unseen"):
            sub = with_data([r for r in rows if r["half"] == half], name)
            ent[half] = {"all": q(sub), "aligned": cell(sub, name, "aligned"),
                         "against": cell(sub, name, "against"), "neutral": cell(sub, name, "neutral")}
        for per, _ in PERIODS:
            sub = with_data([r for r in rows if r["per"] == per], name)
            ent[per] = {"all": q(sub), "aligned": cell(sub, name, "aligned")}
        ent["by_rule"] = {}
        for rule in sorted({r["rule"] for r in rows}):
            sub = with_data([r for r in rows if r["half"] == "unseen" and r["rule"] == rule], name)
            ent["by_rule"][rule] = {"all": q(sub), "aligned": cell(sub, name, "aligned"),
                                    "against": cell(sub, name, "against")}
        ent["by_dir"] = {}
        for d in ("long", "short"):
            sub = with_data([r for r in rows if r["half"] == "unseen" and r["dir"] == d], name)
            ent["by_dir"][d] = {"all": q(sub), "aligned": cell(sub, name, "aligned"),
                                "against": cell(sub, name, "against")}
        table[name] = ent

    # selection on the fit half: largest (aligned − all) gap with aligned n ≥ 60
    def gap(ent, half):
        a, al = ent[half]["all"], ent[half]["aligned"]
        return (al["net"] - a["net"]) if (a["n"] and al["n"]) else None

    eligible = [(gap(e, "fit"), name) for name, e in table.items()
                if e["fit"]["aligned"]["n"] >= A_FIT_MIN_ALIGNED and gap(e, "fit") is not None]
    verdict = {"selected": None, "pass": False, "checks": {}, "fit_gap": None}
    if eligible:
        fit_gap, sel = max(eligible)
        e = table[sel]
        u = e["unseen"]
        g = gap(e, "unseen")
        checks = {
            "aligned_n_ge_30": u["aligned"]["n"] >= A_UNSEEN_MIN_ALIGNED,
            "gap_ge_0.05": g is not None and g >= A_MIN_GAP,
            "aligned_net_gt_0": bool(u["aligned"]["n"]) and u["aligned"]["net"] > 0,
            "aligned_pf_ge_1.3": bool(u["aligned"]["n"]) and u["aligned"]["pf"] >= A_MIN_PF,
            "gap_ge_0_in_TEST_and_H": all((gap(e, p) or -1) >= 0 for p in UNSEEN),
            "against_not_better": not (u["against"]["n"] and u["aligned"]["n"]
                                       and u["against"]["net"] > u["aligned"]["net"]),
        }
        verdict = {"selected": sel, "fit_gap": fit_gap, "unseen_gap": g, "checks": checks,
                   "pass": all(checks.values())}
    return rows, table, verdict


# ----------------------------------------------------------------------------- test B
def sim_book_trade(fwd, direction, atr):
    """The live trade shape from the first scored 15m open: limit at the open, stop 1 ATR,
    T1 0.75R, T2 2R, trail/lock on, 2-day window. None if unfilled or invalid."""
    if len(fwd) < 8 or not atr or atr <= 0:
        return None
    e = fwd[0]["open"]
    risk = B_STOP_ATR * atr
    sgn = 1 if direction == "long" else -1
    r = ts.simulate_limit(fwd, direction, e - sgn * risk, e + sgn * B_T1_R * risk, e + sgn * B_T2_R * risk,
                          atr=atr, limit_offset_atr=ub.LIMIT_OFFSET_ATR, limit_wait_bars=ub.LIMIT_WAIT_BARS,
                          max_candles=B_WINDOW, candle_minutes=15, trail=True)
    return r if r and r.get("filled") else None


def row_of(r, t_ms):
    return None if r is None else {"t": t_ms, "net": r["net_blended_rr"], "profitable": r["profitable"],
                                   "hold": r["hold_minutes"]}


def run_test_b(idx: od.OrderBookIndex, symbols: list[str], log=print):
    """Signal at every closed 4h bar per variant; one open trade per symbol; random-side
    control (3 draws, seed 7) and the flipped sign on the same closes. Returns (rows, table, verdict)."""
    rng = random.Random(SEED)
    rows = {name: [] for name in [f"{f}_{thr:g}" for f, thr in B_VARIANTS]}
    ctrl = {name: [] for name in rows}
    flip = {name: [] for name in rows}
    no_data = defaultdict(int)
    for sym in symbols:
        f4 = frame(sym, "240", C_TAG)
        try:
            ts15, m15 = bars15(sym, C_TAG)
        except FileNotFoundError:
            log(f"  {sym}: no 15m cache, skipped")
            continue
        if not f4:
            continue
        busy = {name: 0 for name in rows}
        for i, T in enumerate(f4["ms"]):
            if T < C_FROM or T >= CUTOFF:
                continue
            atr = f4["atr"][i]
            feats = {"imb": feature(idx, sym, T, "imb", B_BAND), "tilt": feature(idx, sym, T, "tilt", B_BAND)}
            j = bisect_left(ts15, T + SCAN_LAG_MS)
            fwd = m15[j:j + ub.LIMIT_WAIT_BARS + B_WINDOW]
            for f, thr in B_VARIANTS:
                name = f"{f}_{thr:g}"
                x = feats[f]
                if x is None:
                    no_data[name] += 1
                    continue
                if abs(x) <= thr or T < busy[name]:
                    continue
                d = "long" if x > 0 else "short"
                r = sim_book_trade(fwd, d, atr)
                if r is None:
                    continue
                busy[name] = ts15[j + r["fill_bar"]] + r["hold_minutes"] * 60_000
                rows[name].append({**row_of(r, T), "sym": sym, "dir": d, "per": period_of(T), "half": half_of(T)})
                fl = sim_book_trade(fwd, "short" if d == "long" else "long", atr)
                flip[name].append({**(row_of(fl, T) or {"t": T, "net": 0.0, "profitable": False, "hold": 0}),
                                   "per": period_of(T), "half": half_of(T)} if fl else None)
                for _ in range(CONTROL_DRAWS):
                    c = sim_book_trade(fwd, rng.choice(("long", "short")), atr)
                    if c:
                        ctrl[name].append({**row_of(c, T), "per": period_of(T), "half": half_of(T)})
        log(f"  {sym}: " + ", ".join(f"{n} {sum(1 for r in rows[n] if r['sym'] == sym)}" for n in rows))

    table = {}
    for name in rows:
        ent = {"no_data": no_data[name]}
        for half in ("fit", "unseen"):
            ent[half] = {"book": q([r for r in rows[name] if r["half"] == half]),
                         "random": q([r for r in ctrl[name] if r["half"] == half]),
                         "flipped": q([r for r in flip[name] if r and r["half"] == half])}
        for per, _ in PERIODS:
            ent[per] = {"book": q([r for r in rows[name] if r["per"] == per]),
                        "random": q([r for r in ctrl[name] if r["per"] == per])}
        ent["by_dir"] = {d: q([r for r in rows[name] if r["half"] == "unseen" and r["dir"] == d])
                         for d in ("long", "short")}
        table[name] = ent

    eligible = [(e["fit"]["book"]["net"], name) for name, e in table.items() if e["fit"]["book"]["n"] >= B_MIN_N]
    verdict = {"selected": None, "pass": False, "checks": {}}
    if eligible:
        _, sel = max(eligible)
        u = table[sel]["unseen"]
        b, c = u["book"], u["random"]
        checks = {
            "n_ge_100": b["n"] >= B_MIN_N,
            "net_gt_0": bool(b["n"]) and b["net"] > 0,
            "pf_ge_1.3": bool(b["n"]) and b["pf"] >= B_MIN_PF,
            "weeks_green_ge_55": bool(b["n"]) and b["weeks"] >= B_MIN_WEEKS,
            "beats_random_by_0.05": bool(b["n"] and c["n"]) and b["net"] >= c["net"] + B_MIN_EDGE_OVER_RANDOM,
            "net_gt_0_in_TEST_and_H": all(table[sel][p]["book"]["n"] and table[sel][p]["book"]["net"] > 0
                                          for p in UNSEEN),
        }
        verdict = {"selected": sel, "checks": checks, "pass": all(checks.values())}
    return {"book": rows, "random": ctrl, "flipped": flip}, table, verdict


# ----------------------------------------------------------------------------- report
def fmt(s):
    if not s or not s.get("n"):
        return "n=0"
    return (f"n={s['n']} · {s['prof']:.0f}% · {s['net']:+.3f}R · PF {s['pf']:.2f}"
            + (f" · wk {s['weeks']:.0f}%" if "weeks" in s else ""))


def short(s):
    return "n=0" if not s or not s.get("n") else f"n={s['n']} {s['net']:+.3f}R"


def write_report(date_tag, cov, a_table, a_verdict, b_table, b_verdict, n_trades, elapsed):
    L = [f"# Order-book depth as a new input ({date_tag})", ""]
    L.append("Pre-registration: `logs/backtest_reports/prereg_orderbook_20261103.md` (written before this code). "
             "Data: Binance USDT-M `bookDepth` snapshots (PROXY — Bybit publishes none), reduced by "
             "`orderbook_data.py`. Cells: n · profitable % · net R per trade (the managed trade, maker entry) · "
             "net profit factor (· % of weeks green). Fit half = OLDER + TRAIN; unseen half = TEST + H.\n")
    L.append("**Depth coverage:** " + ", ".join(f"{s} {c:.0f}%" for s, c in sorted(cov.items())) + "\n")

    L.append(f"## Test A — the book as a filter on the live rules ({n_trades} recorded trades)\n")
    L.append("| variant | fit: all | fit: aligned | fit: against | unseen: all | unseen: aligned | unseen: against | unseen gap |")
    L.append("|---|---|---|---|---|---|---|---|")
    for name, e in a_table.items():
        u = e["unseen"]
        g = (u["aligned"]["net"] - u["all"]["net"]) if (u["all"].get("n") and u["aligned"].get("n")) else None
        mark = " **←selected**" if name == a_verdict.get("selected") else ""
        L.append(f"| {name}{mark} | {short(e['fit']['all'])} | {short(e['fit']['aligned'])} | "
                 f"{short(e['fit']['against'])} | {short(u['all'])} | {short(u['aligned'])} | "
                 f"{short(u['against'])} | {'n/a' if g is None else f'{g:+.3f}R'} |")
    if a_verdict.get("selected"):
        sel = a_verdict["selected"]
        e = a_table[sel]
        L.append(f"\n**Selected on the fit half:** `{sel}` (fit gap {a_verdict['fit_gap']:+.3f}R). Unseen half: "
                 f"aligned {fmt(e['unseen']['aligned'])} vs all {fmt(e['unseen']['all'])}; against "
                 f"{fmt(e['unseen']['against'])}.")
        L.append("\nChecks: " + ", ".join(f"{k} {'✓' if v else '✗'}" for k, v in a_verdict["checks"].items()))
        L.append(f"\n### Verdict A: **{'PASS' if a_verdict['pass'] else 'NO'}**\n")
        L.append("Per period (aligned vs all):")
        L.append("| period | all | aligned |")
        L.append("|---|---|---|")
        for p, _ in PERIODS:
            L.append(f"| {p} | {short(e[p]['all'])} | {short(e[p]['aligned'])} |")
        L.append("\nUnseen half by rule (descriptive, not selected on):")
        L.append("| rule | all | aligned | against |")
        L.append("|---|---|---|---|")
        for rule, c in e["by_rule"].items():
            L.append(f"| {rule} | {short(c['all'])} | {short(c['aligned'])} | {short(c['against'])} |")
        L.append("\nUnseen half by direction:")
        L.append("| direction | all | aligned | against |")
        L.append("|---|---|---|---|")
        for d, c in e["by_dir"].items():
            L.append(f"| {d} | {short(c['all'])} | {short(c['aligned'])} | {short(c['against'])} |")
    else:
        L.append("\n### Verdict A: **NO** (no variant reached aligned n ≥ 60 on the fit half)\n")

    L.append("\n## Test B — the book as a signal of its own (every closed 4h bar, band 2 %)\n")
    L.append("| variant | no-data closes | fit: book | fit: random | unseen: book | unseen: random | unseen: flipped |")
    L.append("|---|---|---|---|---|---|---|")
    for name, e in b_table.items():
        mark = " **←selected**" if name == b_verdict.get("selected") else ""
        L.append(f"| {name}{mark} | {e['no_data']} | {fmt(e['fit']['book'])} | {short(e['fit']['random'])} | "
                 f"{fmt(e['unseen']['book'])} | {short(e['unseen']['random'])} | {short(e['unseen']['flipped'])} |")
    if b_verdict.get("selected"):
        sel = b_verdict["selected"]
        e = b_table[sel]
        L.append(f"\n**Selected on the fit half:** `{sel}`. " + "Checks: "
                 + ", ".join(f"{k} {'✓' if v else '✗'}" for k, v in b_verdict["checks"].items()))
        L.append(f"\n### Verdict B: **{'PASS' if b_verdict['pass'] else 'NO'}**\n")
        L.append("| period | book | random |")
        L.append("|---|---|---|")
        for p, _ in PERIODS:
            L.append(f"| {p} | {fmt(e[p]['book'])} | {short(e[p]['random'])} |")
        L.append("\nUnseen half by direction: " + ", ".join(f"{d} {fmt(s)}" for d, s in e["by_dir"].items()))
    else:
        L.append("\n### Verdict B: **NO** (no variant reached n ≥ 100 on the fit half)\n")

    L.append(f"\n---\n12 selected trials in total (≈ 0.6 false PASS expected at 5 % with no edge). "
             f"Nothing was varied after the run. Run time {elapsed:.0f}s.\n")
    out = REPORT_DIR / f"orderbook_{date_tag}.md"
    out.write_text("\n".join(L))
    return out


def coverage(idx, symbols, start_ms, end_ms):
    """Share of 15m boundaries in [start, end) that carry a snapshot, per symbol."""
    out = {}
    total = (end_ms - start_ms) // od.BAR_MS
    for s in symbols:
        ts = idx._ts.get(s, [])
        have = sum(1 for t in ts if start_ms <= t < end_ms)
        out[s] = 100.0 * have / total if total else 0.0
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--date-tag", default=datetime.now(timezone.utc).strftime("%Y%m%d"))
    a = ap.parse_args(argv)
    t0 = time.time()
    idx = od.OrderBookIndex()
    symbols = idx.symbols()
    print(f"depth store: {len(symbols)} symbols")
    trades = [t for t in json.loads(C_TRADES.read_text())
              if (t["signal"], t["tf"]) in LIVE and t["result"].get("filled") and C_FROM <= t["signal_ms"] < CUTOFF
              and t["symbol"] in symbols]
    print(f"test A population: {len(trades)} trades")
    a_rows, a_table, a_verdict = run_test_a(idx, trades)
    print(f"A: {a_verdict}")
    b_rows, b_table, b_verdict = run_test_b(idx, symbols)
    print(f"B: {b_verdict}")
    cov = coverage(idx, symbols, C_FROM, CUTOFF)
    out = write_report(a.date_tag, cov, a_table, a_verdict, b_table, b_verdict, len(trades), time.time() - t0)
    (REPORT_DIR / f"orderbook_{a.date_tag}_rows.json").write_text(
        json.dumps({"A": a_rows, "B": b_rows, "A_verdict": a_verdict, "B_verdict": b_verdict}, default=str))
    print(f"report → {out}")


if __name__ == "__main__":
    main()
