"""Win rate is set by the target/stop geometry: hit rate of a plain bracket (whole position,
stop 1R, target kR, 2-day max hold) for our 4h/1h signal entries vs random-entry twins
(same symbol, same stop distance, random 4h close, random direction). Costs = trade_sim's
maker_entry legs (maker in + maker target; taker + slippage on stop/expiry; funding)."""
import json
import random
import sys
from bisect import bisect_left
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

BASE = Path(__file__).resolve().parent
CACHE = BASE / "logs/backtest_cache/unified"
TRADES = BASE / "logs/backtest_reports/unified_20260923_trades.json"
KS = (0.25, 0.5, 0.75, 1.0, 1.5, 2.0)
MAX_BARS = 192  # 2 days of 15m
TAKER = config.TAKER_FEE_PCT + config.SLIPPAGE_PCT
MAKER = config.MAKER_FEE_PCT
random.seed(7)

bars = {}


def load(sym):
    if sym not in bars:
        f = CACHE / f"{sym}_15_20260327_20260923.json"
        rows = json.loads(f.read_text()) if f.exists() else []
        rows = sorted((int(r[0]), float(r[1]), float(r[2]), float(r[3]), float(r[4])) for r in rows)
        bars[sym] = ([r[0] for r in rows], rows)
    return bars[sym]


def bracket(sym, start_ms, direction, risk_pct, k):
    ts, rows = load(sym)
    i = bisect_left(ts, start_ms)
    if i >= len(rows) - 2:
        return None
    entry = rows[i][1]
    r = entry * risk_pct
    sgn = 1 if direction == "long" else -1
    stop, tgt = entry - sgn * r, entry + sgn * k * r
    end = min(i + MAX_BARS, len(rows))
    for j in range(i, end):
        _, o, h, lo, c = rows[j]
        hit_stop = lo <= stop if sgn > 0 else h >= stop
        hit_tgt = h >= tgt if sgn > 0 else lo <= tgt
        if hit_stop:  # same-bar ambiguity resolved against us (as trade_sim's wick stops)
            gross, leg, bars_held = -1.0, TAKER, j - i + 1
            break
        if hit_tgt:
            gross, leg, bars_held = k, MAKER, j - i + 1
            break
    else:
        c = rows[end - 1][4]
        gross, leg, bars_held = sgn * (c - entry) / r, TAKER, end - i
    funding = config.FUNDING_PCT_PER_8H * (bars_held * 15 / 60 / 8)
    net = gross - (MAKER + leg + funding) / risk_pct
    return gross, net


live = {("range_reversion_short", "4h"), ("range_reversion_long", "4h"), ("failed_breakout_short", "4h"),
        ("trend_pullback_short", "4h"), ("liquidity_sweep_long", "1h"), ("rsi_bounce_long", "4h")}
trades = [t for t in json.loads(TRADES.read_text()) if (t["signal"], t["tf"]) in live]
span = {}
for t in trades:
    ts, _ = load(t["symbol"])
    if ts:
        span[t["symbol"]] = (ts[0], ts[-1] - MAX_BARS * 900_000)


def summarize(rows):
    rows = [x for x in rows if x]
    n = len(rows)
    win = sum(1 for g, _ in rows if g > 0)
    return n, 100 * win / n, sum(g for g, _ in rows) / n, sum(x for _, x in rows) / n


cost_r = sorted((MAKER + TAKER) / t["risk_pct"] for t in trades)
print(f"{len(trades)} signal trades, 29 symbols, 2026-03-29 -> 09-23; median stop distance "
      f"{100 * sorted(t['risk_pct'] for t in trades)[len(trades) // 2]:.2f}% of price; "
      f"median round-trip cost on a stop-out = {cost_r[len(cost_r) // 2]:.3f}R")
print(f"{'target':>7} | {'theory':>6} | {'SIGNALS hit%':>12} {'gross':>7} {'net':>7} | "
      f"{'RANDOM hit%':>11} {'gross':>7} {'net':>7}")
for k in KS:
    sig = [bracket(t["symbol"], t["signal_ms"], t["direction"], t["risk_pct"], k) for t in trades]
    rnd = []
    for t in trades:
        a, b = span[t["symbol"]]
        for _ in range(5):
            ms = random.randrange(a, b) // 14_400_000 * 14_400_000
            rnd.append(bracket(t["symbol"], ms, random.choice(("long", "short")), t["risk_pct"], k))
    n, h, g, x = summarize(sig)
    _, hr, gr, xr = summarize(rnd)
    print(f"{k:>5.2f}R | {100 / (1 + k):5.1f}% | {h:11.1f}% {g:+7.3f} {x:+7.3f} | {hr:10.1f}% {gr:+7.3f} {xr:+7.3f}")
print("theory = no-edge hit rate of a 1R stop vs kR target, 1/(1+k), ignoring costs and the 2-day expiry")
