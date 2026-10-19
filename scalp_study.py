"""Scalp / hold-time study (2026-10-19) — pre-registered, research-only.

User question (2026-10-19): would 1:1 (max 1:1.5) targets on 15m — shorter holds, less news
exposure — work better than today's 4h trade? Bars and design were fixed BEFORE the run in
`logs/backtest_reports/prereg_scalp_study_20261019.md`; this file implements exactly that.

  A  15m scalp — the 7 price-pattern rules detected on CLOSED 15m bars (rule logic unchanged,
     only the timeframe), whole position out at A1 = 1.0R or A2 = 1.5R (no partial, no BE, no
     trail), max hold 16 × 15m after the fill. One trade per (symbol, direction) per 4.5h.
     No-skill baseline: every 18th 15m bar, alternating long/short, stop 1.5 × ATR(15m).
  B  today's 4h/1h signals and management; B0 = today's window, B1 = max hold 12h,
     B2 = B1 + skip signals with a scheduled US release (CPI / NFP / FOMC) nearby.

Both run on the one trade model: `signal_rules.detect_at` + `unified_backtest.sim_trade_limit`
(limit at the next 15m open, 2-bar wait, maker entry/targets, taker stops) + `trade_sim`.
Zero trading decisions, no order API, no Claude calls.

Usage:
    venv/bin/python scalp_study.py                # fresh 180 d, harness default universe
    venv/bin/python scalp_study.py --skip-fetch   # cache only
"""

import argparse
import bisect
import json
import time
from collections import Counter
from datetime import datetime, timezone
from multiprocessing import Pool

from pybit.unified_trading import HTTP

import signal_rules as sr
import unified_backtest as ub

PRICE_RULES = ("trend_pullback_short", "failed_breakout_short", "liquidity_sweep_long",
               "rsi_bounce_long", "range_reversion_short", "range_reversion_long",
               "rsi_rejection_short")
SCALP_TARGETS = {"A1": 1.0, "A2": 1.5}
SCALP_HOLD_BARS = 16                                     # 4h of 15m bars after the fill
SCALP_LOCK_BARS = ub.LIMIT_WAIT_BARS + SCALP_HOLD_BARS   # longest a scalp can live
BAR_MS = ub.INTERVAL_MS["15"]
BASELINE_EVERY = 18
BASELINE_STOP_ATR = 1.5
HOLD_CAP_BARS = 48                                       # B1: 12h of 15m bars after the fill
NEWS_BEFORE_MS = 3_600_000                               # B2: event up to 1h before the signal close ...
NEWS_AFTER_MS = 12 * 3_600_000 + ub.LIMIT_WAIT_BARS * BAR_MS   # ... or until the latest exit

PASS_PCT, LEAD_PCT, MIN_N = 70.0, 60.0, 30
LEAD_BASELINE_PP = 5.0
HELP_LIFT_R = 0.03

# Scheduled US releases (UTC). CPI + jobs report 08:30 ET, FOMC statement 14:00 ET; US daylight
# time runs 2026-03-08 → 2026-11-01, so 12:30 / 18:00 UTC. Sources (checked 2026-10-19):
# bls.gov CPI and Employment Situation release schedules, federalreserve.gov FOMC calendar.
NEWS_EVENTS = [
    ("2026-04-03 12:30", "NFP"), ("2026-04-10 12:30", "CPI"), ("2026-04-29 18:00", "FOMC"),
    ("2026-05-08 12:30", "NFP"), ("2026-05-12 12:30", "CPI"),
    ("2026-06-05 12:30", "NFP"), ("2026-06-10 12:30", "CPI"), ("2026-06-17 18:00", "FOMC"),
    ("2026-07-02 12:30", "NFP"), ("2026-07-14 12:30", "CPI"), ("2026-07-29 18:00", "FOMC"),
    ("2026-08-07 12:30", "NFP"), ("2026-08-12 12:30", "CPI"),
    ("2026-09-04 12:30", "NFP"), ("2026-09-11 12:30", "CPI"), ("2026-09-16 18:00", "FOMC"),
    ("2026-10-02 12:30", "NFP"), ("2026-10-14 12:30", "CPI"),
]
NEWS_MS = sorted(int(datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).timestamp() * 1000)
                 for s, _ in NEWS_EVENTS)


def near_news(signal_ms):
    j = bisect.bisect_left(NEWS_MS, signal_ms - NEWS_BEFORE_MS)
    return j < len(NEWS_MS) and NEWS_MS[j] <= signal_ms + NEWS_AFTER_MS


# ─── Study A: 15m scalp ──────────────────────────────────────────────────────

def _bracket(t, r):
    """Whole position out at r × risk (T1 = T2, so the partial never splits), no trail."""
    res = ub.sim_trade_limit(t, ub.LIMIT_OFFSET_ATR, ub.LIMIT_WAIT_BARS, t1_r=r, t2_r=r,
                             trail=False, max_candles=SCALP_HOLD_BARS)
    return res if (res and res.get("filled")) else None


def _sim_all(t):
    out = {k: _bracket(t, r) for k, r in SCALP_TARGETS.items()}
    t.pop("_fwd")
    return out


def scalp_symbol(job):
    """Walk every closed 15m bar of one symbol. Returns (rule trades, baseline trades) with
    the forward candles dropped (results kept per target)."""
    sym, rows = job
    for name in PRICE_RULES:          # study-only: allow the 15m timeframe in this process
        sr.SIGNAL_TFS[name] = ("15m",)
    df = sr.compute_indicators(rows)
    m15_ts = [int(r[0]) for r in rows]
    m15_c = [{"open": float(r[1]), "high": float(r[2]), "low": float(r[3]),
              "close": float(r[4])} for r in rows]
    atr_col = df["atr"].tolist()
    enabled = set(PRICE_RULES)
    trades, base = [], []
    locked_until = {}
    for i in range(60, len(df) - 1):
        close_t = m15_ts[i] + BAR_MS
        j = bisect.bisect_left(m15_ts, close_t)
        fwd = m15_c[j:j + SCALP_LOCK_BARS]
        if len(fwd) < 4:
            continue
        if (i - 60) % BASELINE_EVERY == 0 and atr_col[i] and atr_col[i] > 0:
            direction = "long" if ((i - 60) // BASELINE_EVERY) % 2 == 0 else "short"
            entry = fwd[0]["open"]
            d = BASELINE_STOP_ATR * atr_col[i]
            t = {"symbol": sym, "signal": "baseline", "tf": "15m", "direction": direction,
                 "signal_ms": close_t, "entry": entry, "atr": atr_col[i], "target_r": 1.0,
                 "stop": entry - d if direction == "long" else entry + d, "_fwd": fwd}
            t["_res"] = _sim_all(t)
            base.append(t)
        sigs = sr.detect_at(df, i, "15m", enabled=enabled)
        for sig in sigs:
            direction = sig["direction"]
            if close_t < locked_until.get(direction, 0):
                continue
            atr = float(atr_col[i])
            entry = fwd[0]["open"]
            stop = sr.levels_for(sig, entry, atr)
            if (direction == "long" and stop >= entry) or (direction == "short" and stop <= entry):
                continue
            locked_until[direction] = close_t + SCALP_LOCK_BARS * BAR_MS
            t = {"symbol": sym, "signal": sig["signal"], "tf": "15m", "direction": direction,
                 "signal_ms": close_t, "entry": entry, "atr": atr, "target_r": 1.0,
                 "stop": stop, "_fwd": fwd}
            t["_res"] = _sim_all(t)
            trades.append(t)
    return sym, trades, base


# ─── Study B: 4h hold cap + news blackout ────────────────────────────────────

def hold_variants(t):
    """B0 = today's trade, B1 = same with a 12h hold cap. None = limit not filled."""
    b0 = ub.sim_trade_limit(t, ub.LIMIT_OFFSET_ATR, ub.LIMIT_WAIT_BARS)
    if not (b0 and b0.get("filled")):
        return None
    b1 = ub.sim_trade_limit(t, ub.LIMIT_OFFSET_ATR, ub.LIMIT_WAIT_BARS, max_candles=HOLD_CAP_BARS)
    return {"B0": b0, "B1": b1}


# ─── Readout helpers ─────────────────────────────────────────────────────────

def split_by_time(trades, cut_ms):
    return ([t for t in trades if t["signal_ms"] < cut_ms],
            [t for t in trades if t["signal_ms"] >= cut_ms])


def cut_at(trades, frac=0.6):
    ms = sorted(t["signal_ms"] for t in trades)
    return ms[int(len(ms) * frac)] if ms else 0


def stats_of(trades, key):
    return ub.stats([t["_res"][key] for t in trades if t["_res"].get(key)])


def month_rows(trades, key):
    by = {}
    for t in trades:
        r = t["_res"].get(key)
        if r:
            by.setdefault(datetime.fromtimestamp(t["signal_ms"] / 1000, tz=timezone.utc).strftime("%Y-%m"), []).append(r)
    out = ["| month | n | profitable% | net exp |", "|---|---|---|---|"]
    for m in sorted(by):
        s = ub.stats(by[m])
        out.append(f"| {m} | {s['n']} | {s['profitable_pct']} | {s['net_exp']:+.3f} |")
    return out


def slim(t):
    row = {k: t[k] for k in ("symbol", "signal", "tf", "direction", "signal_ms") if k in t}
    if "news" in t:
        row["news"] = t["news"]
    for key, r in t["_res"].items():
        if r:
            row[key] = [r["net_blended_rr"], r["profitable"], r["exit_reason"], r["hold_minutes"]]
    return row


def pass_verdict(s):
    if not s["n"]:
        return "FAIL (n=0)"
    if s["n"] >= MIN_N and s["profitable_pct"] >= PASS_PCT and s["net_exp"] > 0:
        return "PASS"
    return "FAIL"


def hold_mix(trades, key):
    rs = [t["_res"][key] for t in trades if t["_res"].get(key)]
    if not rs:
        return "n/a"
    holds = sorted(r["hold_minutes"] for r in rs)
    med = holds[len(holds) // 2]
    mix = Counter(r["exit_reason"] for r in rs)
    return f"median hold {med / 60:.1f}h; exits " + ", ".join(f"{k} {v}" for k, v in mix.most_common())


# ─── Run ─────────────────────────────────────────────────────────────────────

def run(args):
    t0 = time.time()
    symbols = ub.auto_universe(args.max_symbols)
    if "BTCUSDT" not in symbols:
        symbols.insert(0, "BTCUSDT")
    print(f"Universe ({len(symbols)}): {', '.join(symbols)}")
    client = HTTP(testnet=False, timeout=20)
    data, skipped = {}, []
    for n, sym in enumerate(symbols, 1):
        d = {iv: ub.fetch_closed_klines(client, sym, iv, args.days, skip_fetch=args.skip_fetch)
             for iv in ("240", "60", "D", "15")}
        h4 = d["240"]
        span = (int(h4[-1][0]) - int(h4[0][0])) / 86_400_000 if len(h4) > 1 else 0
        if span < ub.MIN_HISTORY_DAYS or len(d["15"]) < 500:
            skipped.append(f"{sym} ({span:.0f}d)")
            continue
        data[sym] = d
        print(f"  [{n}/{len(symbols)}] {sym}: 15m={len(d['15'])} 4h={len(d['240'])} ({span:.0f}d)")
    print(f"Data ready in {time.time() - t0:.0f}s; skipped: {', '.join(skipped) or 'none'}")

    # Study A (parallel over symbols)
    t1 = time.time()
    with Pool(args.workers) as pool:
        out = pool.map(scalp_symbol, [(s, d["15"]) for s, d in data.items()])
    a_trades = [t for _, tr, _ in out for t in tr]
    a_base = [t for _, _, b in out for t in b]
    print(f"Study A: {len(a_trades)} rule signals, {len(a_base)} baseline entries ({time.time() - t1:.0f}s)")

    # Study B (sequential; reuses the harness trade builder exactly)
    t1 = time.time()
    btc_h4 = None
    if "BTCUSDT" in data and len(data["BTCUSDT"]["240"]) >= 60:
        btc_h4 = ub.TrendIndex(sr.compute_indicators(data["BTCUSDT"]["240"]), "240")
    b_trades = []
    for sym, d in data.items():
        for t in ub.build_trades(sym, d, btc_h4, None, {"4h", "1h"}):
            res = hold_variants(t)
            t.pop("_fwd", None)
            if res:
                t["_res"] = res
                t["news"] = near_news(t["signal_ms"])
                b_trades.append(t)
    print(f"Study B: {len(b_trades)} filled trades ({time.time() - t1:.0f}s)")

    report, verdicts = build_report(data, args, a_trades, a_base, b_trades)
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    ub.REPORT_DIR.mkdir(parents=True, exist_ok=True)
    rp = ub.REPORT_DIR / f"scalp_study_{today}.md"
    rp.write_text(report, encoding="utf-8")
    # slim rows (the full result dicts for ~50k trades were 68 MB; logs/ is committed by the scans)
    tp = ub.REPORT_DIR / f"scalp_study_{today}_trades.json"
    tp.write_text(json.dumps({"A": [slim(t) for t in a_trades], "B": [slim(t) for t in b_trades]},
                             separators=(",", ":")), encoding="utf-8")
    print(report)
    print(f"\nVERDICTS: {json.dumps(verdicts)}")
    print(f"Saved {rp} and {tp} ({time.time() - t0:.0f}s total)")


def build_report(data, args, a_trades, a_base, b_trades):
    L, V = [], {}
    first = min(int(d["15"][0][0]) for d in data.values())
    last = max(int(d["15"][-1][0]) for d in data.values())
    span = (f"{datetime.fromtimestamp(first / 1000, tz=timezone.utc):%Y-%m-%d} → "
            f"{datetime.fromtimestamp(last / 1000, tz=timezone.utc):%Y-%m-%d}")
    L.append(f"# Scalp / hold-time study — {datetime.now(timezone.utc):%Y-%m-%d}")
    L.append(f"\nPre-registration: `logs/backtest_reports/prereg_scalp_study_20261019.md`. "
             f"Universe {len(data)} symbols ({', '.join(data)}); {span}. Entry: limit at next 15m open, "
             f"{ub.LIMIT_WAIT_BARS}-bar wait, maker entry/targets, taker+slippage stops/expiry, funding. "
             f"TRAIN = first 60% by signal time, TEST = last 40%. profitable = net R > 0.")

    # ── A
    cut = cut_at(a_trades + a_base)
    L.append(f"\n## Study A — 15m scalp, whole position at the target, max hold 4h\n")
    L.append(f"TRAIN/TEST cut: {datetime.fromtimestamp(cut / 1000, tz=timezone.utc):%Y-%m-%d %H:%M} UTC.\n")
    L.append("| book | target | ALL | TRAIN | TEST | verdict |")
    L.append("|---|---|---|---|---|---|")
    base_test = {}
    for key, r in SCALP_TARGETS.items():
        tr, te = split_by_time(a_base, cut)
        s_te = stats_of(te, key)
        base_test[key] = s_te
        L.append(f"| no-skill baseline | {r}R | {ub.fmt(stats_of(a_base, key))} | {ub.fmt(stats_of(tr, key))} | "
                 f"{ub.fmt(s_te)} | reference |")
    for key, r in SCALP_TARGETS.items():
        tr, te = split_by_time(a_trades, cut)
        s_te = stats_of(te, key)
        v = pass_verdict(s_te)
        V[f"A_pooled_{key}"] = v
        L.append(f"| all 7 rules pooled | {r}R | {ub.fmt(stats_of(a_trades, key))} | {ub.fmt(stats_of(tr, key))} | "
                 f"{ub.fmt(s_te)} | **{v}** |")
    for key in SCALP_TARGETS:
        L.append(f"\n- {key} rules: {hold_mix(a_trades, key)}")
        L.append(f"- {key} baseline: {hold_mix(a_base, key)}")

    L.append("\n### Per rule (informational — 14 cells, ~0.7 false positives expected)\n")
    L.append("| rule | target | ALL | TRAIN | TEST | lead? |")
    L.append("|---|---|---|---|---|---|")
    leads = []
    for rule in PRICE_RULES:
        rt = [t for t in a_trades if t["signal"] == rule]
        tr, te = split_by_time(rt, cut)
        for key, r in SCALP_TARGETS.items():
            s_tr, s_te = stats_of(tr, key), stats_of(te, key)
            bt = base_test[key]["profitable_pct"] or 0
            lead = (s_te["n"] >= MIN_N and s_te["profitable_pct"] >= LEAD_PCT and s_te["net_exp"] > 0
                    and s_tr["n"] and s_tr["profitable_pct"] >= LEAD_PCT and s_tr["net_exp"] > 0
                    and s_te["profitable_pct"] >= bt + LEAD_BASELINE_PP)
            if lead:
                leads.append(f"{rule} {key}")
            L.append(f"| {rule} | {r}R | {ub.fmt(stats_of(rt, key))} | {ub.fmt(s_tr)} | {ub.fmt(s_te)} | "
                     f"{'**LEAD**' if lead else ''} |")
    V["A_leads"] = leads
    for key, r in SCALP_TARGETS.items():
        L.append(f"\n**Pooled rules by month ({r}R):**\n")
        L.extend(month_rows(a_trades, key))

    # ── B
    L.append("\n## Study B — today's signals: hold cap and news blackout\n")
    cut_b = cut_at(b_trades)
    L.append(f"TRAIN/TEST cut: {datetime.fromtimestamp(cut_b / 1000, tz=timezone.utc):%Y-%m-%d %H:%M} UTC. "
             f"{sum(1 for t in b_trades if t['news'])}/{len(b_trades)} trades fall in a news window "
             f"({len(NEWS_EVENTS)} releases on the calendar).\n")
    b2_set = [t for t in b_trades if not t["news"]]
    books = {"B0": (b_trades, "B0"), "B1": (b_trades, "B1"), "B2": (b2_set, "B1")}
    L.append("| variant | ALL | TRAIN | TEST |")
    L.append("|---|---|---|---|")
    st = {}
    for name, (tl, key) in books.items():
        tr, te = split_by_time(tl, cut_b)
        st[name] = (stats_of(tr, key), stats_of(te, key))
        L.append(f"| {name} | {ub.fmt(stats_of(tl, key))} | {ub.fmt(st[name][0])} | {ub.fmt(st[name][1])} |")
    for new, old in (("B1", "B0"), ("B2", "B1")):
        d_te = st[new][1]["net_exp"] - st[old][1]["net_exp"]
        d_tr = st[new][0]["net_exp"] - st[old][0]["net_exp"]
        v = "HELPS" if (d_te >= HELP_LIFT_R and d_tr > 0) else ("HURTS" if (d_te <= -HELP_LIFT_R and d_tr < 0) else "NO EFFECT")
        V[f"{new}_vs_{old}"] = v
        L.append(f"\n- **{new} vs {old}: {v}** — TEST net {d_te:+.3f}R, TRAIN net {d_tr:+.3f}R, "
                 f"TEST hit rate {st[new][1]['profitable_pct'] - st[old][1]['profitable_pct']:+.1f}pp")
    L.append(f"\n- B0: {hold_mix(b_trades, 'B0')}")
    L.append(f"- B1: {hold_mix(b_trades, 'B1')}")
    news_tr = [t for t in b_trades if t["news"]]
    L.append(f"- the trades B2 removes, under B1: {ub.fmt(stats_of(news_tr, 'B1'))}")

    L.append("\n### Per rule × tf (each split 60/40 on its own trades, as the harness does)\n")
    L.append("| rule | tf | B0 TEST | B1 TEST | B2 TEST | ship? |")
    L.append("|---|---|---|---|---|---|")
    groups = {}
    for t in b_trades:
        groups.setdefault((t["signal"], t["tf"]), []).append(t)
    ships = []
    for (sig, tf), tl in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        _, te = ub.split_train_test(tl)
        s0, s1 = stats_of(te, "B0"), stats_of(te, "B1")
        s2 = stats_of([t for t in te if not t["news"]], "B1")
        ok = [n for n, s in (("B0", s0), ("B1", s1), ("B2", s2)) if pass_verdict(s) == "PASS"]
        ships += [f"{sig} {tf} {n}" for n in ok]
        L.append(f"| {sig} | {tf} | {ub.fmt(s0)} | {ub.fmt(s1)} | {ub.fmt(s2)} | {', '.join(ok) or 'NO'} |")
    V["B_ship"] = ships
    L.append("\nFrozen rule note: `range_reversion_short` 4h is forward test #1 — nothing here changes it "
             "while its clock runs.")
    return "\n".join(L), V


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--max-symbols", type=int, default=30)
    ap.add_argument("--days", type=int, default=180)
    ap.add_argument("--skip-fetch", action="store_true")
    ap.add_argument("--workers", type=int, default=6)
    run(ap.parse_args())


if __name__ == "__main__":
    main()
