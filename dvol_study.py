"""Options-implied volatility (Deribit DVOL) as a new input — pre-registered study (2026-11-17).

Pre-registration: logs/backtest_reports/prereg_dvol_20261117.md (frozen before this file).
Three market-wide features from BTC's DVOL (`dvol_data.py`), all read as "fade the fear" (positive =
favours a LONG): `dvol_z` (30-day z of implied vol), `dvol_chg` (24-hour change in sd units), `vrp_z`
(30-day z of implied minus 7-day realised vol). Same protocol as `venue_study.py`: Test A = the input as a
filter on the 3,531 recorded live-rule trades (6 variants, selected on the fit half, graded on the unseen
half); Test B = the input as a 4h signal of its own (3 variants, random-side + flipped controls). 9 trials.

    python dvol_data.py fetch && python dvol_study.py   # → logs/backtest_reports/dvol_<date>.md (+ _rows.json)

Research only: no trade decision, no order API, no hosted model.
"""
from __future__ import annotations

import argparse
import json
import random
import time
from bisect import bisect_left
from collections import defaultdict
from datetime import datetime, timezone

import dvol_data as dd
import orderbook_study as obs
import unified_backtest as ub
from checklist_study import C_FROM, C_TAG, C_TRADES, REPORT_DIR, bars15, frame
from mtf_entry_study import LIVE
from quality_study import CUTOFF, PERIODS

PREREG = "prereg_dvol_20261117.md"
KINDS = dd.FEATURES
A_VARIANTS = tuple((k, thr) for k in KINDS for thr in (0.5, 1.0))
B_VARIANTS = tuple((k, 1.0) for k in KINDS)


def bucket(x, direction: str, thr: float) -> str:
    """Positive feature favours a LONG (fade the fear) — obs.bucket's convention as-is."""
    return obs.bucket(x, direction, thr)


# ----------------------------------------------------------------------------- test A
def run_test_a(idx, trades):
    rows = []
    for t in trades:
        T = t["signal_ms"]
        rec = {"t": T, "sym": t["symbol"], "rule": f"{t['signal']} {t['tf']}", "dir": t["direction"],
               "per": obs.period_of(T), "half": obs.half_of(T), "net": t["result"]["net_blended_rr"],
               "profitable": t["result"]["profitable"], "hold": t["result"]["hold_minutes"], "b": {}}
        feats = {k: idx.at(k, T) for k in KINDS}
        for k, thr in A_VARIANTS:
            rec["b"][f"{k}_{thr:g}"] = bucket(feats[k], t["direction"], thr)
        rows.append(rec)
    return rows, *grade_a(rows)


def grade_a(rows):
    def cell(sub, name, which):
        return obs.q([r for r in sub if r["b"][name] == which])

    def with_data(sub, name):
        return [r for r in sub if r["b"][name] != "no_data"]

    table = {}
    for k, thr in A_VARIANTS:
        name = f"{k}_{thr:g}"
        ent = {}
        for half in ("fit", "unseen"):
            sub = with_data([r for r in rows if r["half"] == half], name)
            ent[half] = {"all": obs.q(sub), "aligned": cell(sub, name, "aligned"),
                         "against": cell(sub, name, "against"), "neutral": cell(sub, name, "neutral")}
        for per, _ in PERIODS:
            sub = with_data([r for r in rows if r["per"] == per], name)
            ent[per] = {"all": obs.q(sub), "aligned": cell(sub, name, "aligned")}
        ent["by_rule"], ent["by_dir"] = {}, {}
        for rule in sorted({r["rule"] for r in rows}):
            sub = with_data([r for r in rows if r["half"] == "unseen" and r["rule"] == rule], name)
            ent["by_rule"][rule] = {"all": obs.q(sub), "aligned": cell(sub, name, "aligned"),
                                    "against": cell(sub, name, "against")}
        for d in ("long", "short"):
            sub = with_data([r for r in rows if r["half"] == "unseen" and r["dir"] == d], name)
            ent["by_dir"][d] = {"all": obs.q(sub), "aligned": cell(sub, name, "aligned"),
                                "against": cell(sub, name, "against")}
        table[name] = ent

    def gap(ent, half):
        a, al = ent[half]["all"], ent[half]["aligned"]
        return (al["net"] - a["net"]) if (a["n"] and al["n"]) else None

    eligible = [(gap(e, "fit"), name) for name, e in table.items()
                if e["fit"]["aligned"]["n"] >= obs.A_FIT_MIN_ALIGNED and gap(e, "fit") is not None]
    verdict = {"selected": None, "pass": False, "checks": {}, "fit_gap": None}
    if eligible:
        fit_gap, sel = max(eligible)
        e, u = table[sel], table[sel]["unseen"]
        g = gap(e, "unseen")
        checks = {
            "aligned_n_ge_30": u["aligned"]["n"] >= obs.A_UNSEEN_MIN_ALIGNED,
            "gap_ge_0.05": g is not None and g >= obs.A_MIN_GAP,
            "aligned_net_gt_0": bool(u["aligned"]["n"]) and u["aligned"]["net"] > 0,
            "aligned_pf_ge_1.3": bool(u["aligned"]["n"]) and u["aligned"]["pf"] >= obs.A_MIN_PF,
            "gap_ge_0_in_TEST_and_H": all((gap(e, p) if gap(e, p) is not None else -1) >= 0 for p in obs.UNSEEN),
            "against_not_better": not (u["against"]["n"] and u["aligned"]["n"]
                                       and u["against"]["net"] > u["aligned"]["net"]),
        }
        dir_gaps = {d: (c["aligned"]["net"] - c["all"]["net"]) if (c["all"]["n"] and c["aligned"]["n"]) else None
                    for d, c in e["by_dir"].items()}
        verdict = {"selected": sel, "fit_gap": fit_gap, "unseen_gap": g, "checks": checks,
                   "pass": all(checks.values()), "dir_gaps": dir_gaps,
                   "one_sided": sum(1 for v in dir_gaps.values() if v is not None and v > 0) < 2}
    return table, verdict


# ----------------------------------------------------------------------------- test B
def run_test_b(idx, symbols, log=print):
    """Signal at every closed 4h bar per variant; one open trade per symbol; random-side + flipped controls."""
    rng = random.Random(obs.SEED)
    names = [f"{k}_{thr:g}" for k, thr in B_VARIANTS]
    rows, ctrl, flip = ({n: [] for n in names} for _ in range(3))
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
        busy = {n: 0 for n in names}
        for i, T in enumerate(f4["ms"]):
            if T < C_FROM or T >= CUTOFF:
                continue
            atr = f4["atr"][i]
            feats = {k: idx.at(k, T) for k in KINDS}
            j = bisect_left(ts15, T + obs.SCAN_LAG_MS)
            fwd = m15[j:j + ub.LIMIT_WAIT_BARS + obs.B_WINDOW]
            for k, thr in B_VARIANTS:
                name = f"{k}_{thr:g}"
                x = feats[k]
                if x is None:
                    no_data[name] += 1
                    continue
                if abs(x) <= thr or T < busy[name]:
                    continue
                d = "long" if x > 0 else "short"
                r = obs.sim_book_trade(fwd, d, atr)
                if r is None:
                    continue
                busy[name] = ts15[j + r["fill_bar"]] + r["hold_minutes"] * 60_000
                meta = {"per": obs.period_of(T), "half": obs.half_of(T)}
                rows[name].append({**obs.row_of(r, T), "sym": sym, "dir": d, **meta})
                fl = obs.sim_book_trade(fwd, "short" if d == "long" else "long", atr)
                if fl:
                    flip[name].append({**obs.row_of(fl, T), **meta})
                for _ in range(obs.CONTROL_DRAWS):
                    c = obs.sim_book_trade(fwd, rng.choice(("long", "short")), atr)
                    if c:
                        ctrl[name].append({**obs.row_of(c, T), **meta})
        log(f"  {sym}: " + ", ".join(f"{n} {sum(1 for r in rows[n] if r['sym'] == sym)}" for n in names))
    return {"book": rows, "random": ctrl, "flipped": flip}, *grade_b(rows, ctrl, flip, no_data)


def grade_b(rows, ctrl, flip, no_data):
    table = {}
    for name in rows:
        ent = {"no_data": no_data.get(name, 0)}
        for half in ("fit", "unseen"):
            ent[half] = {"book": obs.q([r for r in rows[name] if r["half"] == half]),
                         "random": obs.q([r for r in ctrl[name] if r["half"] == half]),
                         "flipped": obs.q([r for r in flip[name] if r["half"] == half])}
        for per, _ in PERIODS:
            ent[per] = {"book": obs.q([r for r in rows[name] if r["per"] == per]),
                        "random": obs.q([r for r in ctrl[name] if r["per"] == per])}
        ent["by_dir"] = {d: obs.q([r for r in rows[name] if r["half"] == "unseen" and r["dir"] == d])
                         for d in ("long", "short")}
        table[name] = ent
    eligible = [(e["fit"]["book"]["net"], name) for name, e in table.items() if e["fit"]["book"]["n"] >= obs.B_MIN_N]
    verdict = {"selected": None, "pass": False, "checks": {}}
    if eligible:
        _, sel = max(eligible)
        u = table[sel]["unseen"]
        b, c = u["book"], u["random"]
        checks = {
            "n_ge_100": b["n"] >= obs.B_MIN_N,
            "net_gt_0": bool(b["n"]) and b["net"] > 0,
            "pf_ge_1.3": bool(b["n"]) and b["pf"] >= obs.B_MIN_PF,
            "weeks_green_ge_55": bool(b["n"]) and b["weeks"] >= obs.B_MIN_WEEKS,
            "beats_random_by_0.05": bool(b["n"] and c["n"]) and b["net"] >= c["net"] + obs.B_MIN_EDGE_OVER_RANDOM,
            "net_gt_0_in_TEST_and_H": all(table[sel][p]["book"]["n"] and table[sel][p]["book"]["net"] > 0
                                          for p in obs.UNSEEN),
        }
        verdict = {"selected": sel, "checks": checks, "pass": all(checks.values())}
    return table, verdict


# ----------------------------------------------------------------------------- report
def coverage(idx, start_ms, end_ms):
    hours = range(start_ms, end_ms, dd.HOUR_MS)
    return {k: 100.0 * sum(1 for h in hours if idx.at(k, h) is not None) / len(hours) for k in KINDS}


def write_report(date_tag, cov, a_table, a_verdict, b_table, b_verdict, n_trades, elapsed):
    fmt, short = obs.fmt, obs.short
    L = [f"# Options-implied volatility (Deribit DVOL) as a new input ({date_tag})", "",
         f"Pre-registration: `logs/backtest_reports/{PREREG}` (written before this code). Data: BTC DVOL hourly "
         "(`dvol_data.py`), one market-wide value for every coin; every feature is read as FADE THE FEAR "
         "(positive = favours a LONG). Cells: n · profitable % · net R per trade (the managed trade) · net PF "
         "(· % of weeks green). Fit half = OLDER + TRAIN; unseen half = TEST + H.\n",
         "**Coverage (hours of the study window with the feature defined):** "
         + ", ".join(f"{k} {v:.0f}%" for k, v in cov.items()) + "\n",
         f"## Test A — DVOL as a filter on the live rules ({n_trades} recorded trades)\n",
         "| variant | fit: all | fit: aligned | fit: against | unseen: all | unseen: aligned | unseen: against | unseen gap |",
         "|---|---|---|---|---|---|---|---|"]
    for name, e in a_table.items():
        f, u = e["fit"], e["unseen"]
        g = (u["aligned"]["net"] - u["all"]["net"]) if (u["all"]["n"] and u["aligned"]["n"]) else None
        L.append(f"| {name}{' **←selected**' if name == a_verdict.get('selected') else ''} | {short(f['all'])} | "
                 f"{short(f['aligned'])} | {short(f['against'])} | {short(u['all'])} | {short(u['aligned'])} | "
                 f"{short(u['against'])} | {'n/a' if g is None else f'{g:+.3f}R'} |")
    sel = a_verdict.get("selected")
    if sel:
        e, u = a_table[sel], a_table[sel]["unseen"]
        L.append(f"\n**Selected on the fit half:** `{sel}` (fit gap {a_verdict['fit_gap']:+.3f}R). Unseen half: "
                 f"aligned {fmt(u['aligned'])} vs all {fmt(u['all'])}; against {fmt(u['against'])}.")
        L.append("\nChecks: " + ", ".join(f"{k} {'✓' if v else '✗'}" for k, v in a_verdict["checks"].items()))
        dg = ", ".join(f"{d} {'n/a' if v is None else f'{v:+.3f}R'}" for d, v in a_verdict["dir_gaps"].items())
        L.append(f"\nComposition: unseen gap by direction — {dg}"
                 + (" → **carried by one direction only**" if a_verdict["one_sided"] else " → both directions"))
        L.append(f"\n### Verdict A: **{'PASS' if a_verdict['pass'] else 'NO'}**\n")
        L.append("Per period (aligned vs all):\n| period | all | aligned |\n|---|---|---|")
        for p, _ in PERIODS:
            L.append(f"| {p} | {short(e[p]['all'])} | {short(e[p]['aligned'])} |")
        L.append("\nUnseen half by rule (descriptive, not selected on):\n| rule | all | aligned | against |\n|---|---|---|---|")
        for rule, c in e["by_rule"].items():
            L.append(f"| {rule} | {short(c['all'])} | {short(c['aligned'])} | {short(c['against'])} |")
        L.append("\nUnseen half by direction:\n| direction | all | aligned | against |\n|---|---|---|---|")
        for d, c in e["by_dir"].items():
            L.append(f"| {d} | {short(c['all'])} | {short(c['aligned'])} | {short(c['against'])} |")
    else:
        L.append("\n### Verdict A: **NO** (no variant reached the fit-half floor)\n")

    L.append("\n## Test B — DVOL as a signal of its own (every closed 4h bar)\n")
    L.append("| variant | no-data closes | fit: signal | fit: random | unseen: signal | unseen: random | unseen: flipped |")
    L.append("|---|---|---|---|---|---|---|")
    for name, e in b_table.items():
        f, u = e["fit"], e["unseen"]
        L.append(f"| {name}{' **←selected**' if name == b_verdict.get('selected') else ''} | {e['no_data']} | "
                 f"{fmt(f['book'])} | {short(f['random'])} | {fmt(u['book'])} | {short(u['random'])} | {short(u['flipped'])} |")
    sel = b_verdict.get("selected")
    if sel:
        L.append(f"\n**Selected on the fit half:** `{sel}`. Checks: "
                 + ", ".join(f"{k} {'✓' if v else '✗'}" for k, v in b_verdict["checks"].items()))
        L.append(f"\n### Verdict B: **{'PASS' if b_verdict['pass'] else 'NO'}**\n")
        L.append("| period | signal | random |\n|---|---|---|")
        for p, _ in PERIODS:
            L.append(f"| {p} | {fmt(b_table[sel][p]['book'])} | {short(b_table[sel][p]['random'])} |")
        L.append("\nUnseen half by direction: " + ", ".join(f"{d} {fmt(c)}" for d, c in b_table[sel]["by_dir"].items()))
    else:
        L.append("\n### Verdict B: **NO** (no variant reached n ≥ 100 on the fit half)\n")
    n = len(A_VARIANTS) + len(B_VARIANTS)
    L.append(f"\n---\n{n} selected trials in total (≈ {0.05 * n:.2f} false PASS expected at 5 % with no edge). "
             f"Nothing was varied after the run. Run time {elapsed:.0f}s.")
    out = REPORT_DIR / f"dvol_{date_tag}.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--date-tag", default=datetime.now(timezone.utc).strftime("%Y%m%d"))
    a = ap.parse_args(argv)
    t0 = time.time()
    idx = dd.DvolIndex.load()
    trades = [t for t in json.loads(C_TRADES.read_text())
              if (t["signal"], t["tf"]) in LIVE and t["result"].get("filled") and C_FROM <= t["signal_ms"] < CUTOFF]
    symbols = sorted({t["symbol"] for t in trades})
    print(f"test A population: {len(trades)} trades, {len(symbols)} symbols")
    a_rows, a_table, a_verdict = run_test_a(idx, trades)
    print(f"A: {a_verdict}")
    b_rows, b_table, b_verdict = run_test_b(idx, symbols)
    print(f"B: {b_verdict}")
    out = write_report(a.date_tag, coverage(idx, C_FROM, CUTOFF), a_table, a_verdict, b_table, b_verdict,
                       len(trades), time.time() - t0)
    (REPORT_DIR / f"dvol_{a.date_tag}_rows.json").write_text(
        json.dumps({"A": a_rows, "B": b_rows, "A_verdict": a_verdict, "B_verdict": b_verdict}, default=str))
    print(f"report → {out}")


if __name__ == "__main__":
    main()
