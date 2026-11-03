"""Fade-the-book confirmation on untouched data (pre-registered 2026-11-03).

Pre-registration: logs/backtest_reports/prereg_orderbook_fade_20261103.md — written before any
kline or depth data of the window existed locally. One test, one variant, no selection:

    trades of the six live rules taken AGAINST the resting Binance book (band 2 %, thr 0.10)
    vs all trades with data, signals closing in [2024-10-20, 2025-10-19) UTC.

Data: Bybit klines fetched for a FIXED historical window into the unified cache (tag
`20240701_20251019`; the engine's own `fetch_closed_klines` always ends at "now"), Binance
bookDepth for the same year from `orderbook_data.py`. Trades come from the current engine
(`unified_backtest.build_trades` + `sim_trade`), the feature and bucket from
`orderbook_study` — the identical code paths of the first study.

    python orderbook_fade_confirm.py fetch   # klines for the window (VPN), idempotent
    python orderbook_fade_confirm.py run     # build trades, bucket, grade → report

Research only: no trade decision, no order API, no hosted model.
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone

from pybit.unified_trading import HTTP

import orderbook_data as od
import orderbook_study as obs
import signal_rules as sr
import unified_backtest as ub
from checklist_study import REPORT_DIR
from mtf_entry_study import LIVE
from quality_study import fmt, quality

PREREG = "prereg_orderbook_fade_20261103.md"
TAG = "20240701_20251019"                      # kline cache tag (warm-up from July 2024)
FETCH_START = datetime(2024, 7, 1, tzinfo=timezone.utc)
FETCH_END = datetime(2025, 10, 19, tzinfo=timezone.utc)
WIN_START = int(datetime(2024, 10, 20, tzinfo=timezone.utc).timestamp() * 1000)
WIN_MID = int(datetime(2025, 4, 20, tzinfo=timezone.utc).timestamp() * 1000)
WIN_END = int(FETCH_END.timestamp() * 1000)
BAND, THR = 2.0, 0.10                          # the lead's cell: imb_2_0.1, bucket "against"
MIN_N, MIN_GAP, MIN_PF, MIN_WEEKS = 100, 0.05, 1.3, 55.0
TFS = {"4h", "1h"}
SYMBOLS = ("1000BONKUSDT,1000PEPEUSDT,ADAUSDT,AKEUSDT,ARBUSDT,BTCUSDT,DOGEUSDT,ENAUSDT,ETHUSDT,"
           "FARTCOINUSDT,HBARUSDT,INJUSDT,NEARUSDT,ONDOUSDT,OPUSDT,PENGUUSDT,PUMPFUNUSDT,SANDUSDT,"
           "SOLUSDT,STRKUSDT,SUIUSDT,TRXUSDT,USELESSUSDT,USUSDT,WLDUSDT,XLMUSDT,XPLUSDT,XRPUSDT,"
           "ZECUSDT").split(",")


# ----------------------------------------------------------------------------- data
def fetch_window(client, symbol, interval, start_ms, end_ms, tag=TAG, log=print):
    """Closed klines of a FIXED window, oldest first, cached as `<sym>_<iv>_<tag>.json` in the
    unified cache (same row layout as `fetch_closed_klines`). A failed page is never cached."""
    ub.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cp = ub.CACHE_DIR / f"{symbol}_{interval}_{tag}.json"
    if cp.exists():
        return json.loads(cp.read_text())
    step = ub.INTERVAL_MS[interval]
    by_ts, cursor_end, pages, failed = {}, end_ms, 0, False
    while cursor_end > start_ms and pages < 120:
        try:
            res = client.get_kline(category="linear", symbol=symbol, interval=interval,
                                   start=start_ms, end=cursor_end, limit=1000)
        except Exception as e:  # noqa: BLE001 — network: report, never cache
            log(f"    ! {symbol} {interval} fetch error: {e}")
            failed = True
            break
        rows = res.get("result", {}).get("list", []) or []
        if not rows:
            break
        rows.reverse()
        for r in rows:
            t = int(r[0])
            if start_ms <= t and t + step <= end_ms:
                by_ts[t] = [str(t)] + [str(x) for x in r[1:7]]
        first_t = int(rows[0][0])
        if first_t <= start_ms or len(rows) < 1000:
            break
        cursor_end = first_t - 1
        pages += 1
        time.sleep(0.1)
    out = [by_ts[k] for k in sorted(by_ts)]
    if failed:
        log(f"    ! {symbol} {interval}: incomplete ({len(out)} bars) — not cached")
        return out
    cp.write_text(json.dumps(out))
    return out


def load_data(client, log=print):
    """Klines of every symbol for the window; symbols with too little history are skipped."""
    start_ms, end_ms = int(FETCH_START.timestamp() * 1000), WIN_END
    data, skipped = {}, []
    for n, sym in enumerate(SYMBOLS, 1):
        d = {iv: fetch_window(client, sym, iv, start_ms, end_ms, log=log) for iv in ("240", "60", "D", "15")}
        h4 = d["240"]
        span = (int(h4[-1][0]) - int(h4[0][0])) / 86_400_000 if len(h4) > 1 else 0
        if span < ub.MIN_HISTORY_DAYS or len(d["15"]) < 500:
            skipped.append(f"{sym} ({span:.0f}d 4h, {len(d['15'])} 15m bars)")
            continue
        data[sym] = d
        log(f"  [{n}/{len(SYMBOLS)}] {sym}: 4h={len(d['240'])} 1h={len(d['60'])} D={len(d['D'])} "
            f"15m={len(d['15'])} ({span:.0f}d)")
    return data, skipped


def build_window_trades(data):
    """The six live rules on the window, filled trades only, signals inside [WIN_START, WIN_END)."""
    btc_h4 = None
    if "BTCUSDT" in data and len(data["BTCUSDT"]["240"]) >= 60:
        btc_h4 = ub.TrendIndex(sr.compute_indicators(data["BTCUSDT"]["240"]), "240")
    out = []
    for sym, d in data.items():
        for t in ub.build_trades(sym, d, btc_h4, None, TFS, deriv=None):
            if (t["signal"], t["tf"]) not in LIVE or not (WIN_START <= t["signal_ms"] < WIN_END):
                continue
            res = ub.sim_trade(t)
            if not res or not res.get("filled", True):
                continue
            s = {k: v for k, v in t.items() if not k.startswith("_")}
            s["result"] = res
            out.append(s)
    return sorted(out, key=lambda t: t["signal_ms"])


# ----------------------------------------------------------------------------- the test
def half_of(t_ms):
    return "H1" if t_ms < WIN_MID else "H2"


def tag_trades(idx, trades):
    """One row per trade with the pre-registered bucket (+ descriptive mirrors)."""
    rows = []
    for t in trades:
        T, sym, d = t["signal_ms"], t["symbol"], t["direction"]
        rows.append({"t": T, "sym": sym, "rule": f"{t['signal']} {t['tf']}", "dir": d, "half": half_of(T),
                     "net": t["result"]["net_blended_rr"], "profitable": t["result"]["profitable"],
                     "hold": t["result"]["hold_minutes"],
                     "b": obs.bucket(obs.feature(idx, sym, T, "imb", BAND), d, THR),
                     "b_tilt": obs.bucket(obs.feature(idx, sym, T, "tilt", BAND), d, THR)})
    return rows


def grade(rows):
    """Apply the frozen bar. Returns (table, checks, verdict)."""
    def q(sub):
        return quality(sub)

    with_data = [r for r in rows if r["b"] != "no_data"]
    cells = {"all": q(with_data), "against": q([r for r in with_data if r["b"] == "against"]),
             "aligned": q([r for r in with_data if r["b"] == "aligned"]),
             "neutral": q([r for r in with_data if r["b"] == "neutral"])}
    halves = {}
    for h in ("H1", "H2"):
        sub = [r for r in with_data if r["half"] == h]
        halves[h] = {"all": q(sub), "against": q([r for r in sub if r["b"] == "against"]),
                     "aligned": q([r for r in sub if r["b"] == "aligned"])}
    ag, al = cells["against"], cells["all"]
    gap = (ag["net"] - al["net"]) if ag["n"] and al["n"] else None
    half_gap_ok = all(halves[h]["against"]["n"] > 0 and halves[h]["all"]["n"] > 0 and
                      halves[h]["against"]["net"] - halves[h]["all"]["net"] >= 0 for h in ("H1", "H2"))
    checks = {"against_n_ge_100": ag["n"] >= MIN_N,
              "against_net_gt_0": bool(ag["n"]) and ag["net"] > 0,
              "gap_ge_0.05": gap is not None and gap >= MIN_GAP,
              "against_pf_ge_1.3": bool(ag["n"]) and ag["pf"] >= MIN_PF,
              "against_weeks_ge_55": bool(ag["n"]) and ag["weeks"] >= MIN_WEEKS,
              "gap_ge_0_in_both_halves": half_gap_ok}
    core = all(checks[k] for k in ("against_n_ge_100", "against_net_gt_0", "gap_ge_0.05", "gap_ge_0_in_both_halves"))
    if core and checks["against_pf_ge_1.3"] and checks["against_weeks_ge_55"]:
        verdict = "PASS"
    elif core:
        verdict = "REPLICATED, BELOW BAR"
    else:
        verdict = "NO"
    # descriptive mirrors (never graded)
    desc = {"by_rule": {}, "by_dir": {}, "tilt_against": q([r for r in rows if r["b_tilt"] == "against"]),
            "tilt_all": q([r for r in rows if r["b_tilt"] != "no_data"]), "no_data": sum(1 for r in rows if r["b"] == "no_data")}
    for rule in sorted({r["rule"] for r in with_data}):
        sub = [r for r in with_data if r["rule"] == rule]
        desc["by_rule"][rule] = {"all": q(sub), "against": q([r for r in sub if r["b"] == "against"])}
    for d in ("long", "short"):
        sub = [r for r in with_data if r["dir"] == d]
        desc["by_dir"][d] = {"all": q(sub), "against": q([r for r in sub if r["b"] == "against"])}
    return {"cells": cells, "halves": halves, "gap": gap, "desc": desc}, checks, verdict


def write_report(date_tag, table, checks, verdict, n_trades, skipped, cov, elapsed):
    c, h, d = table["cells"], table["halves"], table["desc"]
    L = [f"# Fade the book — confirmation on untouched data ({date_tag})", "",
         f"Pre-registration: `logs/backtest_reports/{PREREG}` (frozen before the data was downloaded). "
         f"Window: signals {datetime.fromtimestamp(WIN_START / 1000, timezone.utc):%Y-%m-%d} → "
         f"{datetime.fromtimestamp(WIN_END / 1000, timezone.utc):%Y-%m-%d} UTC; six live rules, "
         f"unified engine (limit-open entry, live levels), Binance bookDepth band {BAND:g} % / thr {THR:g}. "
         f"{n_trades} filled trades, {d['no_data']} without a snapshot.", ""]
    if skipped:
        L.append(f"Skipped (insufficient history in the window): {', '.join(skipped)}\n")
    L.append("**Depth coverage (window):** " + ", ".join(f"{s} {v:.0f}%" for s, v in sorted(cov.items())) + "\n")
    L.append("## The one test — against the book vs all\n")
    L.append("| bucket | result |")
    L.append("|---|---|")
    for k in ("all", "against", "aligned", "neutral"):
        L.append(f"| {k} | {fmt(c[k])} |")
    L.append(f"\nGap (against − all): **{table['gap']:+.3f}R**" if table["gap"] is not None else "\nGap: n/a")
    L.append("\n| half | all | against | aligned |")
    L.append("|---|---|---|---|")
    for hk, e in h.items():
        L.append(f"| {hk} | {fmt(e['all'])} | {fmt(e['against'])} | {fmt(e['aligned'])} |")
    L.append("\nChecks: " + ", ".join(f"{k} {'✓' if v else '✗'}" for k, v in checks.items()))
    L.append(f"\n### Verdict: **{verdict}**\n")
    L.append("## Descriptive only (not graded)\n")
    L.append("| rule | all | against |")
    L.append("|---|---|---|")
    for rule, e in d["by_rule"].items():
        L.append(f"| {rule} | {fmt(e['all'])} | {fmt(e['against'])} |")
    L.append("\n| direction | all | against |")
    L.append("|---|---|---|")
    for dk, e in d["by_dir"].items():
        L.append(f"| {dk} | {fmt(e['all'])} | {fmt(e['against'])} |")
    L.append(f"\n`tilt_2_0.1` against: {fmt(d['tilt_against'])} vs all-with-tilt {fmt(d['tilt_all'])}")
    L.append(f"\n---\n1 trial. Nothing was varied after the run. Run time {elapsed:.0f}s.")
    out = REPORT_DIR / f"orderbook_fade_{date_tag}.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fetch")
    r = sub.add_parser("run")
    r.add_argument("--date-tag", default=datetime.now(timezone.utc).strftime("%Y%m%d"))
    a = ap.parse_args(argv)
    t0 = time.time()
    client = HTTP(testnet=False, timeout=20)
    data, skipped = load_data(client)
    print(f"symbols with data: {len(data)}; skipped: {skipped}")
    if a.cmd == "fetch":
        print(f"done in {time.time() - t0:.0f}s")
        return
    trades = build_window_trades(data)
    print(f"window trades: {len(trades)}")
    (REPORT_DIR / f"orderbook_fade_{a.date_tag}_trades.json").write_text(json.dumps(trades))
    idx = od.OrderBookIndex(SYMBOLS)
    rows = tag_trades(idx, trades)
    table, checks, verdict = grade(rows)
    cov = obs.coverage(idx, [s for s in SYMBOLS if s in idx.symbols()], WIN_START, WIN_END)
    out = write_report(a.date_tag, table, checks, verdict, len(trades), skipped, cov, time.time() - t0)
    (REPORT_DIR / f"orderbook_fade_{a.date_tag}_rows.json").write_text(json.dumps({"rows": rows, "verdict": verdict}))
    print(f"verdict: {verdict}\nreport → {out}")


if __name__ == "__main__":
    main()
