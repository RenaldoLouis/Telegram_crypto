"""Confirmation of the basis-tilt fade filter on the untouched 2024-25 year — pre-registered (2026-11-04).

Pre-registration: logs/backtest_reports/prereg_venue_confirm_20261104.md (frozen before this file). One
variant, `basis_disp_tilt` at threshold 1.0, fade orientation, exactly as `venue_study.feature` defines it,
tagged onto the 3,687 live-rule trades of `orderbook_fade_20261103_trades.json` (signals 2024-10-20 →
2025-10-19, rebuilt by the current engine). Eight pre-registered checks → PASS / REPLICATED, BELOW BAR / NO.

    python venue_confirm.py fetch    # the three venues' series for 2024-10-01 → 2025-10-20 (tag 20241001_20251020)
    python venue_confirm.py run      # → logs/backtest_reports/venue_confirm_<date>.md (+ _rows.json)

Research only: no trade decision, no order API, no hosted model.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date, datetime, timezone

import orderbook_study as obs
import venue_data as vd
import venue_study as vs
from checklist_study import REPORT_DIR
from mtf_entry_study import LIVE

PREREG = "prereg_venue_confirm_20261104.md"
TRADES = REPORT_DIR / "orderbook_fade_20261103_trades.json"
TAG = "20241001_20251020"
FETCH_START, FETCH_END = date(2024, 10, 1), date(2025, 10, 20)
_ms = lambda y, m, d: int(datetime(y, m, d, tzinfo=timezone.utc).timestamp() * 1000)
WIN_START, WIN_MID, WIN_END = _ms(2024, 10, 20), _ms(2025, 4, 20), _ms(2025, 10, 20)
KIND, THR = "basis_disp_tilt", 1.0
MIN_N, MIN_GAP, MIN_PF, MIN_WEEKS = 100, 0.05, 1.3, 55.0
REPLICATED_CHECKS = ("aligned_n_ge_100", "gap_ge_0.05", "aligned_net_gt_0", "gap_ge_0_in_both_halves",
                     "against_not_better", "gap_ge_0_in_both_directions")


def load_trades():
    return [t for t in json.loads(TRADES.read_text())
            if (t["signal"], t["tf"]) in LIVE and t["result"].get("filled") and WIN_START <= t["signal_ms"] < WIN_END]


def half_of(t_ms: int) -> str:
    return "H1" if t_ms < WIN_MID else "H2"


def tag_trades(idx, trades):
    """One row per trade with the bucket of the single pre-registered variant."""
    rows = []
    for t in trades:
        T = t["signal_ms"]
        x = vs.feature(idx, t["symbol"], T, KIND)
        rows.append({"t": T, "sym": t["symbol"], "rule": f"{t['signal']} {t['tf']}", "dir": t["direction"],
                     "half": half_of(T), "net": t["result"]["net_blended_rr"],
                     "profitable": t["result"]["profitable"], "hold": t["result"]["hold_minutes"],
                     "x": x, "b": vs.bucket(x, t["direction"], THR)})
    return rows


def grade(rows):
    """→ (table, checks, verdict) per the pre-registration; `all` = rows with data."""
    data = [r for r in rows if r["b"] != "no_data"]

    def cells(sub):
        return {"all": obs.q(sub), "aligned": obs.q([r for r in sub if r["b"] == "aligned"]),
                "against": obs.q([r for r in sub if r["b"] == "against"]),
                "neutral": obs.q([r for r in sub if r["b"] == "neutral"])}

    def gap(c):
        return (c["aligned"]["net"] - c["all"]["net"]) if (c["all"]["n"] and c["aligned"]["n"]) else None

    table = {"year": cells(data), "no_data": len(rows) - len(data),
             "by_half": {h: cells([r for r in data if r["half"] == h]) for h in ("H1", "H2")},
             "by_dir": {d: cells([r for r in data if r["dir"] == d]) for d in ("long", "short")},
             "by_rule": {rule: cells([r for r in data if r["rule"] == rule]) for rule in sorted({r["rule"] for r in data})}}
    y = table["year"]
    g = gap(y)
    checks = {
        "aligned_n_ge_100": y["aligned"]["n"] >= MIN_N,
        "gap_ge_0.05": g is not None and g >= MIN_GAP,
        "aligned_net_gt_0": bool(y["aligned"]["n"]) and y["aligned"]["net"] > 0,
        "aligned_pf_ge_1.3": bool(y["aligned"]["n"]) and y["aligned"]["pf"] >= MIN_PF,
        "aligned_weeks_ge_55": bool(y["aligned"]["n"]) and y["aligned"]["weeks"] >= MIN_WEEKS,
        "gap_ge_0_in_both_halves": all((gap(c) if gap(c) is not None else -1) >= 0 for c in table["by_half"].values()),
        "against_not_better": not (y["against"]["n"] and y["aligned"]["n"] and y["against"]["net"] > y["aligned"]["net"]),
        "gap_ge_0_in_both_directions": all((gap(c) if gap(c) is not None else -1) >= 0 for c in table["by_dir"].values()),
    }
    if all(checks.values()):
        verdict = "PASS"
    elif all(checks[k] for k in REPLICATED_CHECKS):
        verdict = "REPLICATED, BELOW BAR"
    else:
        verdict = "NO"
    table["gap"] = g
    return table, checks, verdict


def write_report(date_tag, table, checks, verdict, n_rows, elapsed):
    fmt, short = obs.fmt, obs.short
    y = table["year"]
    L = [f"# Basis-tilt fade filter — confirmation on the untouched 2024-25 year ({date_tag})", "",
         f"Pre-registration: `logs/backtest_reports/{PREREG}` (written before this code and before the venue series of "
         "this window were downloaded). Population: `orderbook_fade_20261103_trades.json` (six live rules, signals "
         "2024-10-20 → 2025-10-19, 26 symbols). One variant: `basis_disp_tilt` at 1.0, faded (a 4-hour rise of Bybit's "
         "premium over the other venues → short aligned; a fall → long aligned). Cells: n · profitable % · net R per "
         "trade (the managed trade) · net PF · % of weeks green.\n",
         f"Trades: {n_rows} ({table['no_data']} without a feature, excluded).\n",
         "| bucket | n | profitable | net R | PF | weeks green |", "|---|---|---|---|---|---|"]
    for k in ("all", "aligned", "against", "neutral"):
        c = y[k]
        if c["n"]:
            L.append(f"| {k} | {c['n']} | {c['prof']:.0f}% | {c['net']:+.3f} | {c['pf']:.2f} | {c['weeks']:.0f}% |")
    L.append(f"\nGap (aligned − all): **{table['gap']:+.3f}R**" if table["gap"] is not None else "\nGap: n/a")
    L.append("\nChecks: " + ", ".join(f"{k} {'✓' if v else '✗'}" for k, v in checks.items()))
    L.append(f"\n## Verdict: **{verdict}**\n")
    L.append("| half | all | aligned | against |\n|---|---|---|---|")
    for h, c in table["by_half"].items():
        L.append(f"| {h} | {short(c['all'])} | {fmt(c['aligned'])} | {short(c['against'])} |")
    L.append("\n| direction | all | aligned | against |\n|---|---|---|---|")
    for d, c in table["by_dir"].items():
        L.append(f"| {d} | {short(c['all'])} | {fmt(c['aligned'])} | {short(c['against'])} |")
    L.append("\nBy rule (descriptive):\n| rule | all | aligned | against |\n|---|---|---|---|")
    for rule, c in table["by_rule"].items():
        L.append(f"| {rule} | {short(c['all'])} | {short(c['aligned'])} | {short(c['against'])} |")
    L.append(f"\n---\n1 trial. Nothing was varied after the run. Run time {elapsed:.0f}s.")
    out = REPORT_DIR / f"venue_confirm_{date_tag}.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fetch")
    r = sub.add_parser("run")
    r.add_argument("--date-tag", default=datetime.now(timezone.utc).strftime("%Y%m%d"))
    a = ap.parse_args(argv)
    trades = load_trades()
    symbols = sorted({t["symbol"] for t in trades})
    if a.cmd == "fetch":
        t0 = time.time()
        for sym in symbols:
            vd.fetch_symbol(sym, FETCH_START, FETCH_END, tag=TAG)
            sys.stdout.flush()
        print(f"done in {time.time() - t0:.0f}s")
        return
    t0 = time.time()
    idx = vd.VenueIndex(symbols, tag=TAG)
    print(f"population: {len(trades)} trades, {len(symbols)} symbols")
    rows = tag_trades(idx, trades)
    table, checks, verdict = grade(rows)
    print(f"verdict: {verdict} checks: {checks}")
    out = write_report(a.date_tag, table, checks, verdict, len(rows), time.time() - t0)
    (REPORT_DIR / f"venue_confirm_{a.date_tag}_rows.json").write_text(
        json.dumps({"rows": rows, "checks": checks, "verdict": verdict}, default=str))
    print(f"report → {out}")


if __name__ == "__main__":
    main()
