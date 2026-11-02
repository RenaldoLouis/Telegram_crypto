"""failed_breakout_short forward-record check (2026-11-02) — research only.

Pre-registration: logs/backtest_reports/prereg_fbs_check_20261102.md (written before the run).
Question: is the live record of `failed_breakout_short` (81 v2 trades, +0.275R in head_to_head)
an edge, or clustering + market direction? Answers Q1–Q5 of the pre-registration with the live
eval rows and the unified engine (`unified_backtest.build_trades` + `sim_trade`, limit_open).

Changes no rule, gate or pick. No order API, no hosted model.

Usage:  python fbs_check.py [--skip-fetch]   → logs/backtest_reports/fbs_check_<date>.md
"""

import argparse
import json
import random
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from pybit.unified_trading import HTTP

import config
import trade_sim
import unified_backtest as ub

BASE = Path(__file__).parent
EVALS = BASE / "logs" / "evaluations"
SETUPS = BASE / "logs" / "setups"
REPORTS = BASE / "logs" / "backtest_reports"
HIST_FILE = REPORTS / "unified_20261021_365d_trades.json"

SIGNAL = "failed_breakout_short"
H4_MS = 14_400_000
DAY_MS = 86_400_000
RANDOM_HALF_WINDOW_MS = int(3.5 * DAY_MS)     # Q2: other 4h closes within ±3.5 days
FETCH_DAYS = 125                               # live span (from 09-23) + indicator warm-up
PARITY_TOL_R = 0.05                            # Q3
PARITY_MIN_SHARE = 0.90                        # Q3
BEAT_RANDOM_R = 0.05                           # Q2 margin (quality yardstick)
GREEN_WEEKS_MIN = 0.55                         # Q1
BOOT_N = 5000
SEED = 20261102


# ─── Live record ─────────────────────────────────────────────────────────────

def _bar_close_ms(run_ts):
    t = datetime.fromisoformat(run_ts)
    ms = int(t.timestamp() * 1000)
    return ms - ms % H4_MS


def load_live():
    """v2-era, evaluated, non-duplicate rows of the signal, joined to their setup (stop)."""
    setups = {}
    for f in SETUPS.glob("setups_*.json"):
        try:
            rec = json.loads(f.read_text())
        except Exception:
            continue
        setups[rec["run_tag"]] = rec
    out = []
    for f in sorted(EVALS.glob("eval_*.json")):
        ev = json.loads(f.read_text())
        rec = setups.get(ev["run_tag"])
        for r in ev.get("results", []):
            if (r.get("signal_name") != SIGNAL or r.get("eval_engine") != "v2_market_open"
                    or r.get("status") != "evaluated"):
                continue
            s = None
            if rec:
                s = next((x for x in rec["setups"] if x.get("symbol") == r["symbol"]
                          and x.get("source", "claude") == r.get("source", "claude")), None)
            out.append({
                "symbol": r["symbol"], "source": r.get("source"),
                "bar_ms": _bar_close_ms(ev["run_timestamp_utc"]),
                "run_ms": int(datetime.fromisoformat(ev["run_timestamp_utc"]).timestamp() * 1000),
                "net": float(r["net_blended_rr"]), "profitable": bool(r["profitable"]),
                "stop": float(s["stop_loss"]) if s else None,
                "t1": float(s["target_1"]) if s else None,
                "t2": float(s["target_2"]) if s and s.get("target_2") else None,
                "daily_pick": bool(r.get("daily_pick")),
            })
    return out


# ─── Stats helpers ───────────────────────────────────────────────────────────

def bets(rows, key="net"):
    """Same 4h signal bar = one bet (mean of the group)."""
    g = defaultdict(list)
    for r in rows:
        g[r["bar_ms"]].append(r[key])
    return {b: statistics.mean(v) for b, v in g.items()}


def boot_ci(values, n=BOOT_N, seed=SEED):
    rng = random.Random(seed)
    k = len(values)
    means = sorted(statistics.mean(rng.choices(values, k=k)) for _ in range(n))
    return means[int(0.025 * n)], means[int(0.975 * n) - 1]


def week_of(ms):
    d = datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isocalendar()
    return f"{d[0]}-W{d[1]:02d}"


def summary(nets):
    if not nets:
        return "n=0"
    wins = sum(1 for x in nets if x > 0)
    gp = sum(x for x in nets if x > 0)
    gl = -sum(x for x in nets if x < 0)
    pf = gp / gl if gl else float("inf")
    return (f"n={len(nets)} · {100 * wins / len(nets):.1f}% profitable · "
            f"net {statistics.mean(nets):+.3f}R · PF {pf:.2f}")


# ─── Engine ──────────────────────────────────────────────────────────────────

def load_data(symbols, skip_fetch):
    client = HTTP(testnet=False, timeout=20)
    data, missing = {}, []
    for sym in symbols:
        d = {iv: ub.fetch_closed_klines(client, sym, iv, FETCH_DAYS, skip_fetch=skip_fetch)
             for iv in ("240", "60", "D", "15")}
        if len(d["240"]) < 70 or len(d["15"]) < 500:
            missing.append(sym)
            continue
        data[sym] = d
    return data, missing


def sim(entry_trade):
    r = ub.sim_trade(entry_trade)
    return r["net_blended_rr"] if r else None


def trade_at(sym, bar_ms, stop_k=None, stop_price=None, delay_ms=0):
    """A short entered after the 4h bar closing at bar_ms, on the live trade model.
    Stop = explicit price, or entry + stop_k × ATR(bar). `delay_ms` starts the window at the
    first 15m candle opening at or after bar_ms + delay_ms (the live scan's lag; 0 = the
    engine's convention). None when the window is incomplete."""
    m15_ts, m15_c, dfs = ub._PREP_CACHE[sym]
    df = dfs["240"]
    idx = {int(t) + H4_MS: i for i, t in enumerate(df["timestamp"].tolist())}
    i = idx.get(bar_ms)
    if i is None:
        return None
    j = ub.bisect.bisect_left(m15_ts, bar_ms + delay_ms)
    fwd = m15_c[j:j + ub.WINDOW_CANDLES["4h"]]
    if len(fwd) < ub.WINDOW_CANDLES["4h"]:
        return None
    atr = float(df["atr"].iat[i])
    entry = fwd[0]["open"]
    stop = stop_price if stop_price is not None else entry + stop_k * atr
    if stop <= entry or atr <= 0:
        return None
    return {"entry": entry, "stop": stop, "direction": "short", "target_r": 2.0,
            "atr": atr, "_fwd": fwd, "_k": (stop - entry) / atr}


def replay_levels(sym, start_ms, stop, t1, t2):
    """The evaluator's trade (weekly_eval.evaluate_setup): the setup's FIXED stop/T1/T2 prices,
    candles from the first 15m bar opening at or after start_ms, 2-day window, limit_open."""
    m15_ts, m15_c, _ = ub._PREP_CACHE[sym]
    j = ub.bisect.bisect_left(m15_ts, start_ms)
    candles = m15_c[j:j + ub.WINDOW_CANDLES["4h"]]
    if len(candles) < ub.WINDOW_CANDLES["4h"] or t1 is None:
        return None
    first = candles[0]["open"]
    if first >= stop or first <= t1:
        return None  # the evaluator gap-skips these
    r = trade_sim.simulate_limit(
        candles, "short", stop, t1, t2, atr=None,
        limit_offset_atr=getattr(config, "LIMIT_OFFSET_ATR", 0.0),
        limit_wait_bars=getattr(config, "LIMIT_WAIT_BARS", 2),
        max_candles=ub.WINDOW_CANDLES["4h"], candle_minutes=15)
    return r["net_blended_rr"] if r and r.get("filled") else None


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-fetch", action="store_true")
    args = ap.parse_args()

    live = load_live()
    syms = sorted({r["symbol"] for r in live})
    lo, hi = min(r["bar_ms"] for r in live), max(r["bar_ms"] for r in live)
    L = [f"# failed_breakout_short forward-record check — {datetime.now(timezone.utc):%Y-%m-%d}",
         "", "Pre-registration: `prereg_fbs_check_20261102.md`. Engine: unified_backtest "
         f"(entry {ub.ENTRY_MODEL}). Live span {datetime.fromtimestamp(lo/1000, tz=timezone.utc):%Y-%m-%d %H:%M} → "
         f"{datetime.fromtimestamp(hi/1000, tz=timezone.utc):%Y-%m-%d %H:%M} UTC, {len(syms)} symbols.", ""]

    # Q1 — live record, independent bets, weeks
    nets = [r["net"] for r in live]
    b = bets(live)
    bv = list(b.values())
    ci = boot_ci(bv)
    wk = defaultdict(float)
    for r in live:
        wk[week_of(r["bar_ms"])] += r["net"]
    green = sum(1 for v in wk.values() if v > 0) / len(wk)
    cluster_sizes = defaultdict(int)
    for r in live:
        cluster_sizes[r["bar_ms"]] += 1
    big = sorted(cluster_sizes.items(), key=lambda kv: -kv[1])[:5]
    q1 = statistics.mean(bv) > 0 and ci[0] > 0 and green >= GREEN_WEEKS_MIN
    L += ["## Q1 — live record as independent bets", "",
          f"- Trades: {summary(nets)}",
          f"- Independent bets (same 4h bar = one): {len(bv)} · mean {statistics.mean(bv):+.3f}R per bet · "
          f"95% CI [{ci[0]:+.3f}, {ci[1]:+.3f}] · {100*sum(1 for x in bv if x>0)/len(bv):.0f}% of bets green",
          f"- Weeks: {sum(1 for v in wk.values() if v > 0)}/{len(wk)} green ({100*green:.0f}%) · "
          + ", ".join(f"{k} {v:+.1f}R" for k, v in sorted(wk.items())),
          "- Largest same-bar clusters: " + ", ".join(
              f"{datetime.fromtimestamp(k/1000, tz=timezone.utc):%m-%d %H:%M} ×{v}" for k, v in big),
          f"- **Q1: {'HOLDS' if q1 else 'DOES NOT HOLD'}** (bar: mean > 0, CI lower > 0, ≥ 55% weeks green)", ""]

    # Engine data for the live symbols
    data, missing = load_data(syms, args.skip_fetch)
    ub.DEDUP_DAYS = 0  # keep every fire for matching; the 2-day dedup is re-applied below
    fired = {}
    for sym, d in data.items():
        for t in ub.build_trades(sym, d, None, {SIGNAL}, {"4h"}):
            fired[(sym, t["signal_ms"])] = t
    if missing:
        L += [f"_No engine data (too little history or fetch failed): {', '.join(missing)}_", ""]

    # Q3 — parity
    pairs, unmatched = [], []
    for r in live:
        t = fired.get((r["symbol"], r["bar_ms"]))
        if r["symbol"] not in data:
            unmatched.append((r, "no data"))
            continue
        if not t:
            unmatched.append((r, "engine did not fire on this bar"))
            continue
        bt = sim(t)
        if bt is None:
            unmatched.append((r, "engine: limit not filled"))
            continue
        pairs.append((r, bt, t))
    close_share = (sum(1 for r, bt, _ in pairs if abs(r["net"] - bt) <= PARITY_TOL_R) / len(pairs)
                   if pairs else 0)
    q3 = bool(pairs) and close_share >= PARITY_MIN_SHARE
    L += ["## Q3 — parity (live row vs engine, same symbol + signal bar)", "",
          f"- Matched {len(pairs)}/{len(live)} · within {PARITY_TOL_R}R: {100*close_share:.0f}% · "
          f"live {statistics.mean([p[0]['net'] for p in pairs]) if pairs else 0:+.3f}R vs engine "
          f"{statistics.mean([p[1] for p in pairs]) if pairs else 0:+.3f}R on the matched set",
          f"- **Q3: {'PARITY' if q3 else 'PARITY FAILS'}** (bar: ≥ 90% within 0.05R)"]
    reasons = defaultdict(int)
    for _, why in unmatched:
        reasons[why] += 1
    if unmatched:
        L.append("- Unmatched: " + ", ".join(f"{k} ×{v}" for k, v in reasons.items()))
    worst = sorted(pairs, key=lambda p: -abs(p[0]["net"] - p[1]))[:8]
    if worst and abs(worst[0][0]["net"] - worst[0][1]) > PARITY_TOL_R:
        L.append("- Largest gaps: " + "; ".join(
            f"{r['symbol']} {datetime.fromtimestamp(r['bar_ms']/1000, tz=timezone.utc):%m-%d %H:%M} "
            f"live {r['net']:+.2f} / engine {bt:+.2f}" for r, bt, _ in worst
            if abs(r["net"] - bt) > PARITY_TOL_R))
    L.append("")

    # Q3 diagnosis (pre-registration: unmatched/mismatched trades are listed with the reason).
    # Step from the live row to the engine one difference at a time.
    dec = []
    for r, bt, _ in pairs:
        a = replay_levels(r["symbol"], r["run_ms"], r["stop"], r["t1"], r["t2"]) if r["stop"] else None
        b = replay_levels(r["symbol"], r["bar_ms"], r["stop"], r["t1"], r["t2"]) if r["stop"] else None
        if a is not None and b is not None:
            dec.append((r["net"], a, b, bt, (r["run_ms"] - r["bar_ms"]) / 60000))
    if dec:
        same = sum(1 for x in dec if abs(x[0] - x[1]) <= PARITY_TOL_R) / len(dec)
        lags = sorted(x[4] for x in dec)
        L += ["### Q3 diagnosis — where the live/engine gap comes from", "",
              f"Trades with every step computable: {len(dec)}. Scan lag after the 4h close: median "
              f"{statistics.median(lags):.0f} min, max {lags[-1]:.0f} min.", "",
              "| step | what changes | mean net R |", "|---|---|---|",
              f"| live row | as scored by weekly_eval | {statistics.mean(x[0] for x in dec):+.3f} |",
              f"| A. replay | same levels + same start, recomputed here ({100*same:.0f}% within 0.05R of the row) | "
              f"{statistics.mean(x[1] for x in dec):+.3f} |",
              f"| B. enter at the 4h close | same fixed stop/T1/T2 prices, window starts at the close | "
              f"{statistics.mean(x[2] for x in dec):+.3f} |",
              f"| C. engine | engine stop, T1/T2 set from the fill (0.75R / 2R) | {statistics.mean(x[3] for x in dec):+.3f} |",
              ""]

    # Q2 — random entries on the same coin, same week, same stop distance in ATR
    rng_rows = []   # (bet bar, actual engine net, random mean)
    for r in live:
        if r["symbol"] not in data or r["stop"] is None:
            continue
        act = trade_at(r["symbol"], r["bar_ms"], stop_price=r["stop"])
        if not act:
            continue
        a = sim(act)
        if a is None:
            continue
        k = act["_k"]
        rs = []
        bar = r["bar_ms"] - RANDOM_HALF_WINDOW_MS
        bar -= bar % H4_MS
        while bar <= r["bar_ms"] + RANDOM_HALF_WINDOW_MS:
            if bar != r["bar_ms"]:
                rt = trade_at(r["symbol"], bar, stop_k=k)
                if rt:
                    x = sim(rt)
                    if x is not None:
                        rs.append(x)
            bar += H4_MS
        if len(rs) >= 10:
            rng_rows.append({"bar_ms": r["bar_ms"], "act": a, "rnd": statistics.mean(rs),
                             "diff": a - statistics.mean(rs)})
    q2 = False
    if rng_rows:
        diffs_by_bet = list(bets(rng_rows, "diff").values())
        dci = boot_ci(diffs_by_bet)
        act_m = statistics.mean(x["act"] for x in rng_rows)
        rnd_m = statistics.mean(x["rnd"] for x in rng_rows)
        q2 = (act_m - rnd_m) >= BEAT_RANDOM_R and dci[0] > 0
        L += ["## Q2 — the signal vs random shorts on the same coin, same week", "",
              f"- Trades with a full random set: {len(rng_rows)} ({len(diffs_by_bet)} bets) · "
              f"signal entries {act_m:+.3f}R · random entries {rnd_m:+.3f}R (same coin, ±3.5 days, "
              f"same stop in ATR, same management) · difference {act_m - rnd_m:+.3f}R per trade",
              f"- Difference per independent bet: mean {statistics.mean(diffs_by_bet):+.3f}R · "
              f"95% CI [{dci[0]:+.3f}, {dci[1]:+.3f}]",
              f"- Random shorts were profitable on their own: "
              f"{100*sum(1 for x in rng_rows if x['rnd'] > 0)/len(rng_rows):.0f}% of trades had a positive random mean",
              f"- **Q2: {'HOLDS' if q2 else 'DOES NOT HOLD'}** (bar: difference ≥ +0.05R and CI lower > 0)", ""]

    # Q2 sensitivity (NOT pre-registered; added after Q3 showed the engine enters at the close
    # while the live scan cannot): the same comparison with both the signal and the random
    # entries delayed by the live trade's actual scan lag.
    lag_rows = []
    for r in live:
        if r["symbol"] not in data or r["stop"] is None:
            continue
        delay = r["run_ms"] - r["bar_ms"]
        act = trade_at(r["symbol"], r["bar_ms"], stop_price=r["stop"], delay_ms=delay)
        if not act:
            continue
        a = sim(act)
        if a is None:
            continue
        rs = []
        bar = r["bar_ms"] - RANDOM_HALF_WINDOW_MS
        bar -= bar % H4_MS
        while bar <= r["bar_ms"] + RANDOM_HALF_WINDOW_MS:
            if bar != r["bar_ms"]:
                rt = trade_at(r["symbol"], bar, stop_k=act["_k"], delay_ms=delay)
                x = sim(rt) if rt else None
                if x is not None:
                    rs.append(x)
            bar += H4_MS
        if len(rs) >= 10:
            lag_rows.append({"bar_ms": r["bar_ms"], "act": a, "rnd": statistics.mean(rs),
                             "diff": a - statistics.mean(rs)})
    if lag_rows:
        dl = list(bets(lag_rows, "diff").values())
        lci = boot_ci(dl)
        am = statistics.mean(x["act"] for x in lag_rows)
        rm = statistics.mean(x["rnd"] for x in lag_rows)
        L += ["### Q2 at the live entry time (sensitivity, not pre-registered)", "",
              f"- {len(lag_rows)} trades ({len(dl)} bets), both entries delayed by the live scan lag: "
              f"signal {am:+.3f}R · random {rm:+.3f}R · difference {am - rm:+.3f}R per trade · "
              f"per bet {statistics.mean(dl):+.3f}R, 95% CI [{lci[0]:+.3f}, {lci[1]:+.3f}]"]
        byw = defaultdict(list)
        for x in lag_rows:
            byw[week_of(x["bar_ms"])].append(x)
        L.append("- By week (signal vs random, live timing): " + "; ".join(
            f"{w} n={len(v)} {statistics.mean(x['act'] for x in v):+.2f} vs "
            f"{statistics.mean(x['rnd'] for x in v):+.2f}" for w, v in sorted(byw.items())))
        L.append("")

    # Q4 — selection: engine population (2-day dedup) on live symbols in the live span
    taken = {(r["symbol"], r["bar_ms"]) for r in live}
    pop = sorted((t for (s, ms), t in fired.items() if lo <= ms <= hi), key=lambda t: t["signal_ms"])
    last, took, not_took = {}, [], []
    for t in pop:
        p = last.get(t["symbol"])
        if p is not None and t["signal_ms"] < p + 2 * DAY_MS:
            continue
        last[t["symbol"]] = t["signal_ms"]
        x = sim(t)
        if x is None:
            continue
        (took if (t["symbol"], t["signal_ms"]) in taken else not_took).append(x)
    L += ["## Q4 — selection (descriptive)", "",
          f"- Engine fires on the live symbols inside the live span, 2-day dedup: {summary(took + not_took)}",
          f"- …that live also took: {summary(took)}",
          f"- …that live did not take (coin not in that scan's top 30, dedup, or a fresh-signal miss): {summary(not_took)}",
          ""]

    # Q5 — history
    if HIST_FILE.exists():
        hist = [t for t in json.loads(HIST_FILE.read_text())
                if t.get("signal") == SIGNAL and t.get("tf") == "4h" and t.get("result")]
        bym = defaultdict(list)
        for t in hist:
            bym[t["signal_time"][:7]].append(t["result"]["net_blended_rr"])
        L += ["## Q5 — history (365-day unified backtest of 2026-10-21, 30 symbols)", "",
              f"- All: {summary([x for v in bym.values() for x in v])}",
              f"- Months net > 0: {sum(1 for v in bym.values() if statistics.mean(v) > 0)}/{len(bym)}", "",
              "| month | n | profitable | net R/trade |", "|---|---|---|---|"]
        for m in sorted(bym):
            v = bym[m]
            L.append(f"| {m} | {len(v)} | {100*sum(1 for x in v if x > 0)/len(v):.0f}% | {statistics.mean(v):+.3f} |")
        L.append("")

    verdict = "WORTH A FORWARD CLOCK" if (q1 and q2 and q3) else "NOT AN EDGE"
    L += ["## Verdict (pre-registered rule)", "",
          f"Q1 {'HOLDS' if q1 else 'fails'} · Q2 {'HOLDS' if q2 else 'fails'} · Q3 {'parity' if q3 else 'parity fails'} "
          f"→ **{verdict}**", ""]

    out = REPORTS / f"fbs_check_{datetime.now(timezone.utc):%Y%m%d}.md"
    out.write_text("\n".join(L))
    print("\n".join(L))
    print(f"\n→ {out}")


if __name__ == "__main__":
    main()
