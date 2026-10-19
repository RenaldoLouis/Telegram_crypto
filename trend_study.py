"""Single-coin trend-following study (2026-10-19) — pre-registered, research-only.

Every rule tested so far fades or buys a pullback, takes a small fixed target and is out in
two days. This study tests the opposite shape — breakout entry, trailing stop, let winners
run — judged on PROFIT (user decision 2026-10-19), not win rate. Bars and design were fixed
BEFORE the run in `logs/backtest_reports/prereg_trend_study_20261019.md`.

  Signal  daily close above the prior N-day high (long) / below the prior N-day low (short),
          N = 20 (primary) and 55; only when the coin has no open position
  Entry   next day's open, market (taker + slippage)
  Stop    3 × ATR(20, daily); chandelier trail after every daily close (extreme since entry
          − 3 × ATR), never loosens; checked on 4h bars (gap → filled at the open)
  Exit    stop, or market after 60 days
  Costs   taker + slippage both sides, actual Bybit funding at every settlement
  1R      the initial stop distance

A separate product if it passes (like `xs_momentum_paper.py`): trade_sim's fixed-target model
cannot express an open-ended trailing exit, so a PASS must be followed by a forward paper test
with its own pre-registration. Zero trading decisions, no order API, no Claude calls.

Usage:
    venv/bin/python trend_study.py                # 15 majors, 1,095 days, fresh data
    venv/bin/python trend_study.py --skip-fetch   # cache only
"""

import argparse
import bisect
import json
import random
import time
from collections import defaultdict
from datetime import datetime, timezone

from pybit.unified_trading import HTTP

import config
import derivs_data as dd
import unified_backtest as ub

SYMBOLS = list(ub.MAJORS)
DAYS = 1095
LOOKBACKS = (20, 55)
ATR_N = 20
STOP_ATR = 3.0
MAX_HOLD_DAYS = 60
TRAIN_FRAC = 0.6
BASELINE_EVERY = 10
RISK_PER_TRADE = 0.005                     # portfolio view only: 0.5% of equity per trade
SIDE_COST = config.TAKER_FEE_PCT + config.SLIPPAGE_PCT
DAY_MS = ub.INTERVAL_MS["D"]
H4_MS = ub.INTERVAL_MS["240"]

PASS_MIN_N, PASS_PF, CAND_PF, MAX_DD_R = 30, 1.3, 1.1, 20.0


# ─── Data ────────────────────────────────────────────────────────────────────

def _bars(rows):
    return [{"ts": int(r[0]), "o": float(r[1]), "h": float(r[2]), "l": float(r[3]), "c": float(r[4])}
            for r in rows]


def add_atr(daily):
    trs = []
    for i, b in enumerate(daily):
        pc = daily[i - 1]["c"] if i else b["c"]
        trs.append(max(b["h"] - b["l"], abs(b["h"] - pc), abs(b["l"] - pc)))
        b["atr"] = sum(trs[-ATR_N:]) / ATR_N if i >= ATR_N else None


def load(client, sym, skip_fetch):
    """Daily + 4h bars and funding for one symbol. A 4h series that does not cover the daily
    one (a failed page — never cached since 2026-10-19) is fetched once more."""
    for attempt in range(2):
        daily = _bars(ub.fetch_closed_klines(client, sym, "D", DAYS, skip_fetch=skip_fetch))
        h4 = _bars(ub.fetch_closed_klines(client, sym, "240", DAYS, skip_fetch=skip_fetch))
        if daily and len(h4) >= 5.8 * len(daily) - 12:
            break
    funding = dd.fetch_funding(client, sym, DAYS, skip_fetch=skip_fetch, max_pages=200)
    add_atr(daily)
    return {"daily": daily, "h4": h4, "funding": funding}


# ─── Simulation ──────────────────────────────────────────────────────────────

def breakout_rule(n):
    def decide(daily, d, _state):
        if d < n or daily[d]["atr"] is None:
            return None
        if daily[d]["c"] > max(b["h"] for b in daily[d - n:d]):
            return "long"
        if daily[d]["c"] < min(b["l"] for b in daily[d - n:d]):
            return "short"
        return None
    return decide


def baseline_rule(daily, d, state):
    """No-skill entry with the same exit: every 10th flat day, alternating long/short."""
    if daily[d]["atr"] is None:
        return None
    state["flat"] = state.get("flat", 0) + 1
    if state["flat"] % BASELINE_EVERY:
        return None
    state["side"] = "short" if state.get("side") == "long" else "long"
    return state["side"]


def run_trade(sym, data, d, direction):
    """Enter at the open after daily bar `d`, trail, exit. Returns a trade dict or None."""
    daily, h4, funding = data["daily"], data["h4"], data["funding"]
    if d + 1 >= len(daily):
        return None
    entry_ts = daily[d + 1]["ts"]
    h4_ts = data["h4_ts"]
    j = bisect.bisect_left(h4_ts, entry_ts)
    if j >= len(h4) or h4[j]["ts"] - entry_ts >= DAY_MS:
        return None
    long = direction == "long"
    sgn = 1 if long else -1
    entry = h4[j]["o"]
    risk = STOP_ATR * daily[d]["atr"]
    if risk <= 0:
        return None
    stop = entry - sgn * risk
    extreme = entry
    next_close = entry_ts + DAY_MS
    exit_px = exit_ts = reason = None
    for k in range(j, len(h4)):
        b = h4[k]
        while next_close <= b["ts"]:                       # trail from days CLOSED before this bar
            di = data["day_idx"].get(next_close - DAY_MS)
            if di is not None and daily[di]["atr"]:
                extreme = max(extreme, daily[di]["h"]) if long else min(extreme, daily[di]["l"])
                cand = extreme - sgn * STOP_ATR * daily[di]["atr"]
                stop = max(stop, cand) if long else min(stop, cand)
            next_close += DAY_MS
        if (long and b["l"] <= stop) or ((not long) and b["h"] >= stop):
            exit_px = min(b["o"], stop) if long else max(b["o"], stop)
            exit_ts, reason = b["ts"], "stop"
            break
        if b["ts"] + H4_MS >= entry_ts + MAX_HOLD_DAYS * DAY_MS:
            exit_px, exit_ts, reason = b["c"], b["ts"] + H4_MS, "max_hold"
            break
    if exit_px is None:                                     # still open at the end of the data
        exit_px, exit_ts, reason = h4[-1]["c"], h4[-1]["ts"] + H4_MS, "open_at_end"

    paid = 0.0                                              # funding, in price units, + = paid
    f_ts = data["f_ts"]
    for i in range(bisect.bisect_right(f_ts, entry_ts), bisect.bisect_right(f_ts, exit_ts)):
        ts_f, rate = funding[i]
        p = h4[min(bisect.bisect_right(h4_ts, ts_f) - 1, len(h4) - 1)]["o"]
        paid += sgn * rate * p
    gross = sgn * (exit_px - entry) / risk
    fee = SIDE_COST * (entry + exit_px) / risk
    fund = -paid / risk
    return {"symbol": sym, "direction": direction, "entry_ts": entry_ts, "exit_ts": exit_ts,
            "hold_days": round((exit_ts - entry_ts) / DAY_MS, 2), "entry": entry, "exit": exit_px,
            "risk_pct": round(risk / entry * 100, 2), "gross_r": round(gross, 4),
            "fee_r": round(fee, 4), "funding_r": round(fund, 4),
            "net_r": round(gross - fee + fund, 4), "reason": reason}


def simulate(sym, data, decide):
    daily = data["daily"]
    trades, state, d = [], {}, 1
    while d < len(daily) - 1:
        direction = decide(daily, d, state)
        if not direction:
            d += 1
            continue
        t = run_trade(sym, data, d, direction)
        if t is None:
            d += 1
            continue
        trades.append(t)
        if t["reason"] == "open_at_end":
            break
        d = max(d + 1, bisect.bisect_right(data["day_ts"], t["exit_ts"]) - 1)
    return trades


# ─── Stats ───────────────────────────────────────────────────────────────────

def stats(trades):
    if not trades:
        return {"n": 0}
    r = [t["net_r"] for t in trades]
    n = len(r)
    wins = [x for x in r if x > 0]
    losses = [x for x in r if x <= 0]
    best = max(r)
    seq = [t["net_r"] for t in sorted(trades, key=lambda t: t["exit_ts"])]
    eq = peak = dd_max = 0.0
    streak = worst = 0
    for x in seq:
        eq += x
        peak = max(peak, eq)
        dd_max = max(dd_max, peak - eq)
        streak = streak + 1 if x <= 0 else 0
        worst = max(worst, streak)
    rng = random.Random(7)
    boots = sorted(sum(rng.choice(r) for _ in range(n)) / n for _ in range(2000))
    return {
        "n": n, "exp": sum(r) / n, "total": sum(r),
        "pf": (sum(wins) / -sum(losses)) if losses and sum(losses) < 0 else float("inf"),
        "win_pct": 100 * len(wins) / n,
        "avg_win": (sum(wins) / len(wins)) if wins else 0.0,
        "avg_loss": (sum(losses) / len(losses)) if losses else 0.0,
        "best": best, "exp_wo_best": (sum(r) - best) / (n - 1) if n > 1 else 0.0,
        "max_dd": dd_max, "streak": worst, "ci": (boots[50], boots[1949]),
        "fee": sum(t["fee_r"] for t in trades) / n, "fund": sum(t["funding_r"] for t in trades) / n,
        "hold": sorted(t["hold_days"] for t in trades)[n // 2],
    }


def fmt(s):
    if not s.get("n"):
        return "n=0"
    pf = "inf" if s["pf"] == float("inf") else f"{s['pf']:.2f}"
    return (f"n={s['n']} exp={s['exp']:+.3f}R [{s['ci'][0]:+.2f}..{s['ci'][1]:+.2f}] total={s['total']:+.1f}R "
            f"PF={pf} win={s['win_pct']:.0f}% avgW={s['avg_win']:+.2f} avgL={s['avg_loss']:+.2f} "
            f"maxDD={s['max_dd']:.1f}R streak={s['streak']} hold={s['hold']:.1f}d")


def verdict(train, test, whole):
    if not test.get("n") or test["n"] < PASS_MIN_N:
        return "FAIL", f"TEST n={test.get('n', 0)} < {PASS_MIN_N}"
    misses = []
    if test["exp"] <= 0:
        misses.append("TEST net ≤ 0")
    if test["pf"] < PASS_PF:
        misses.append(f"TEST PF {test['pf']:.2f} < {PASS_PF}")
    if test["exp_wo_best"] <= 0:
        misses.append("TEST ≤ 0 without its best trade")
    if not train.get("n") or train["exp"] <= 0:
        misses.append("TRAIN net ≤ 0")
    if whole["max_dd"] > MAX_DD_R:
        misses.append(f"max DD {whole['max_dd']:.1f}R > {MAX_DD_R:.0f}R")
    if not misses:
        return "PASS", "all conditions met"
    if test["exp"] > 0 and test["pf"] >= CAND_PF:
        return "CANDIDATE", "; ".join(misses)
    return "FAIL", "; ".join(misses)


def max_concurrent(trades):
    ev = sorted([(t["entry_ts"], 1) for t in trades] + [(t["exit_ts"], -1) for t in trades])
    cur = top = 0
    for _, x in ev:
        cur += x
        top = max(top, cur)
    return top


# ─── Run ─────────────────────────────────────────────────────────────────────

def run(args):
    t0 = time.time()
    client = HTTP(testnet=False, timeout=20)
    data, notes = {}, []
    for n, sym in enumerate(SYMBOLS, 1):
        dsym = load(client, sym, args.skip_fetch)
        daily, h4, fnd = dsym["daily"], dsym["h4"], dsym["funding"]
        if len(daily) < 200 or len(h4) < 5.8 * len(daily) - 12:
            notes.append(f"{sym} skipped (daily {len(daily)}, 4h {len(h4)})")
            continue
        dsym["h4_ts"] = [b["ts"] for b in h4]
        dsym["day_ts"] = [b["ts"] for b in daily]
        dsym["day_idx"] = {b["ts"]: i for i, b in enumerate(daily)}
        dsym["f_ts"] = [f[0] for f in fnd]
        cov = 0.0
        if fnd:
            cov = (daily[-1]["ts"] + DAY_MS - max(fnd[0][0], daily[0]["ts"])) / (daily[-1]["ts"] + DAY_MS - daily[0]["ts"])
        if cov < 0.95:
            notes.append(f"{sym} funding covers {cov * 100:.0f}% of its history (the rest counted as zero)")
        data[sym] = dsym
        print(f"  [{n}/{len(SYMBOLS)}] {sym}: daily={len(daily)} 4h={len(h4)} funding={len(fnd)} "
              f"from {datetime.fromtimestamp(daily[0]['ts'] / 1000, tz=timezone.utc):%Y-%m-%d}")
    print(f"Data ready in {time.time() - t0:.0f}s")

    span_lo = min(d["daily"][0]["ts"] for d in data.values())
    span_hi = max(d["daily"][-1]["ts"] + DAY_MS for d in data.values())
    cut = span_lo + int(TRAIN_FRAC * (span_hi - span_lo))
    books = {f"N={n}": breakout_rule(n) for n in LOOKBACKS}
    books["baseline"] = baseline_rule
    results = {name: [t for s, d in data.items() for t in simulate(s, d, rule)] for name, rule in books.items()}

    L, V = [], {}
    dt = lambda ms: datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    years = (span_hi - span_lo) / DAY_MS / 365.25
    L.append(f"# Single-coin trend-following study — {datetime.now(timezone.utc):%Y-%m-%d}")
    L.append(f"\nPre-registration: `logs/backtest_reports/prereg_trend_study_20261019.md`. {len(data)} symbols "
             f"({', '.join(data)}); {dt(span_lo)} → {dt(span_hi)}; TRAIN = entries before {dt(cut)}, TEST after. "
             f"Breakout on the daily close, entry next open (taker {config.TAKER_FEE_PCT * 100:.3f}% + slippage "
             f"{config.SLIPPAGE_PCT * 100:.2f}% per side), stop {STOP_ATR} × ATR({ATR_N}) trailed after every daily "
             f"close, checked on 4h bars, max hold {MAX_HOLD_DAYS} d, actual funding. R = initial stop distance; "
             f"all figures net. [a..b] = bootstrap 95% CI of the mean.")
    if notes:
        L.append("\nData notes: " + "; ".join(notes) + ".")

    L.append("\n## Verdict\n")
    L.append("| book | TRAIN | TEST | verdict |")
    L.append("|---|---|---|---|")
    for name, tr in results.items():
        s_tr = stats([t for t in tr if t["entry_ts"] < cut])
        s_te = stats([t for t in tr if t["entry_ts"] >= cut])
        if name == "baseline":
            v, why = "reference", "random entry, same exit"
        else:
            v, why = verdict(s_tr, s_te, stats(tr))
            V[name] = v
        L.append(f"| {name} | {fmt(s_tr)} | {fmt(s_te)} | **{v}** — {why} |")

    for name, tr in results.items():
        s_all = stats(tr)
        L.append(f"\n## {name}\n")
        L.append(f"- ALL: {fmt(s_all)}")
        if s_all.get("n"):
            L.append(f"- costs per trade: fees {s_all['fee']:.3f}R, funding {s_all['fund']:+.3f}R "
                     f"(+ = received); {len(tr) / (years * 52.18):.1f} trades/week on {len(data)} coins; "
                     f"max {max_concurrent(tr)} open at once")
            L.append(f"- portfolio at {RISK_PER_TRADE * 100:.1f}% risk per trade: {s_all['total'] * RISK_PER_TRADE * 100:+.1f}% "
                     f"over {years:.1f} y ({s_all['total'] * RISK_PER_TRADE * 100 / years:+.1f}%/y, simple), "
                     f"max drawdown {s_all['max_dd'] * RISK_PER_TRADE * 100:.1f}% (closed trades)")
            reasons = defaultdict(int)
            for t in tr:
                reasons[t["reason"]] += 1
            L.append("- exits: " + ", ".join(f"{k} {v}" for k, v in sorted(reasons.items(), key=lambda kv: -kv[1])))
        L.append("\n| slice | result |")
        L.append("|---|---|")
        for side in ("long", "short"):
            L.append(f"| {side} — TRAIN | {fmt(stats([t for t in tr if t['direction'] == side and t['entry_ts'] < cut]))} |")
            L.append(f"| {side} — TEST | {fmt(stats([t for t in tr if t['direction'] == side and t['entry_ts'] >= cut]))} |")
        by_y = defaultdict(list)
        for t in tr:
            by_y[dt(t["entry_ts"])[:4]].append(t)
        for y in sorted(by_y):
            L.append(f"| entries {y} | {fmt(stats(by_y[y]))} |")
        by_s = defaultdict(list)
        for t in tr:
            by_s[t["symbol"]].append(t["net_r"])
        L.append("\nPer coin (total net R, n): " + ", ".join(
            f"{s} {sum(v):+.1f} ({len(v)})" for s, v in sorted(by_s.items(), key=lambda kv: -sum(kv[1]))))

    report = "\n".join(L)
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    rp = ub.REPORT_DIR / f"trend_study_{today}.md"
    rp.write_text(report, encoding="utf-8")
    tp = ub.REPORT_DIR / f"trend_study_{today}_trades.json"
    tp.write_text(json.dumps(results, separators=(",", ":")), encoding="utf-8")
    print(report)
    print(f"\nVERDICTS: {json.dumps(V)}")
    print(f"Saved {rp} and {tp} ({time.time() - t0:.0f}s total)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skip-fetch", action="store_true")
    run(ap.parse_args())


if __name__ == "__main__":
    main()
