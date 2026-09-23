"""Research item #1 (2026-09-23): fade forced liquidation flow.

Hypothesis: a burst of liquidations on one side (forced, price-insensitive flow) overshoots
price; entering AGAINST the cascade once the bar closes captures the snap-back with a high
hit rate. Bybit's stream gives the CLOSE direction of each liquidation: side="Sell" = a
long was liquidated (forced selling) → fade = LONG; side="Buy" = a short was squeezed →
fade = SHORT. The opposite ("continuation") direction is simulated too, so the data — not
the story — says which side pays.

Data: the collector's own prints (logs/liquidations/*.jsonl + ci/*.jsonl, deduped). The
store has ~45% hourly coverage, so a bar is only eligible when the collector was
demonstrably alive around it (any print, any symbol, within ±1h); baselines use covered
bars only. Signals fire on CLOSED 15m bars; entry at the next 15m open; simulation via
trade_sim (identical to the evaluator). Zero trading decisions, zero API writes, no Claude.

Run: venv/bin/python liq_fade_backtest.py [--days 50] [--skip-fetch]
"""

import argparse
import bisect
import glob
import json
import math
import statistics as st
import time
from collections import defaultdict
from datetime import datetime, timezone
from itertools import product
from pathlib import Path

from pybit.unified_trading import HTTP

import config
import signal_rules as sr
import trade_sim as ts
from unified_backtest import fetch_closed_klines, wilson, stats, fmt

BAR = 900_000
REPORT_DIR = Path("logs/backtest_reports")


def load_prints():
    seen, rows = set(), []
    for f in glob.glob("logs/liquidations/*.jsonl") + glob.glob("logs/liquidations/ci/*.jsonl"):
        with open(f) as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                k = (int(r["t"]), r["sym"], r["side"], float(r["price"]), float(r["qty"]))
                if k in seen:
                    continue
                seen.add(k)
                rows.append((int(r["t"]), r["sym"], r["side"], float(r["notional"])))
    rows.sort()
    return rows


def bucket(rows):
    """{sym: {bar_start_ms: [sell_notional, buy_notional]}} and the set of covered hours."""
    per = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0]))
    hours = set()
    for t, sym, side, notional in rows:
        b = (t // BAR) * BAR
        per[sym][b][0 if side == "Sell" else 1] += notional
        hours.add(t // 3_600_000)
    return per, hours


def covered(hours, bar_start):
    h = bar_start // 3_600_000
    return (h in hours) or (h - 1 in hours) or (h + 1 in hours)


def build_series(sym, klines, liq_by_bar, hours):
    """Per closed 15m bar: OHLC, atr, sell/buy liq notional, covered flag, baseline."""
    df = sr.compute_indicators(klines)
    ts_list = df["timestamp"].astype("int64").tolist()
    o = df["open"].tolist(); h = df["high"].tolist(); l = df["low"].tolist(); c = df["close"].tolist()
    atr = df["atr"].tolist()
    sell = [liq_by_bar.get(t, [0, 0])[0] for t in ts_list]
    buy = [liq_by_bar.get(t, [0, 0])[1] for t in ts_list]
    cov = [covered(hours, t) for t in ts_list]
    # trailing baseline: mean total liq notional per COVERED bar over the prior 7 days
    base = []
    win = 7 * 96
    run_sum, run_n = 0.0, 0
    q = []  # (idx, total) of covered bars in window
    for i in range(len(ts_list)):
        while q and q[0][0] < i - win:
            _, v = q.pop(0)
            run_sum -= v; run_n -= 1
        base.append(run_sum / run_n if run_n >= 96 else None)  # need >= 1 day of covered bars
        if cov[i]:
            tot = sell[i] + buy[i]
            q.append((i, tot)); run_sum += tot; run_n += 1
    return {"ts": ts_list, "o": o, "h": h, "l": l, "c": c, "atr": atr,
            "sell": sell, "buy": buy, "cov": cov, "base": base,
            "fwd": [{"open": o[i], "high": h[i], "low": l[i], "close": c[i]} for i in range(len(ts_list))]}


def fire(series, i, W, k_rel, floor_abs, dom, M, confirm):
    """Return ('Sell'|'Buy', extreme_price) if a cascade ended at bar i, else None."""
    if i < max(W, 20) + 1 or not series["cov"][i]:
        return None
    a = series["atr"][i]
    if a is None or (isinstance(a, float) and math.isnan(a)) or a <= 0:
        return None
    j0 = i - W + 1
    if confirm:
        j0 -= 1  # the cascade window is the W bars BEFORE the confirmation bar i
        if j0 < 1:
            return None
        win_bars = range(j0, i)
    else:
        win_bars = range(j0, i + 1)
    s = sum(series["sell"][j] for j in win_bars)
    b = sum(series["buy"][j] for j in win_bars)
    tot = s + b
    base = series["base"][i]
    if tot <= 0 or base is None:
        return None
    if tot < floor_abs or tot < k_rel * base * len(win_bars):
        return None
    if s / tot >= dom:
        side, ext = "Sell", min(series["l"][j] for j in win_bars)
        move = (series["c"][j0 - 1] - min(series["c"][j] for j in win_bars)) / a
        if confirm and not (series["c"][i] > series["c"][i - 1]):  # reclaim bar
            return None
    elif b / tot >= dom:
        side, ext = "Buy", max(series["h"][j] for j in win_bars)
        move = (max(series["c"][j] for j in win_bars) - series["c"][j0 - 1]) / a
        if confirm and not (series["c"][i] < series["c"][i - 1]):
            return None
    else:
        return None
    if move < M:
        return None
    return side, ext, tot


def run_combo(series_by_sym, prm, mode, fwd_bars, stop_pad_atr, t2_r, t1_r=0.75, dedup_h=12):
    trades = []
    for sym, S in series_by_sym.items():
        last = {}
        n = len(S["ts"])
        for i in range(21, n - 2):
            f = fire(S, i, prm["W"], prm["k"], prm["floor"], prm["dom"], prm["M"], prm["confirm"])
            if not f:
                continue
            side, ext, tot = f
            fade_dir = "long" if side == "Sell" else "short"
            direction = fade_dir if mode == "fade" else ("short" if fade_dir == "long" else "long")
            key = direction
            if key in last and S["ts"][i] < last[key] + dedup_h * 3_600_000:
                continue
            entry = S["o"][i + 1]
            a = S["atr"][i]
            if mode == "fade":
                stop = ext - stop_pad_atr * a if direction == "long" else ext + stop_pad_atr * a
            else:
                stop = entry - 1.5 * a if direction == "long" else entry + 1.5 * a
            risk = abs(entry - stop)
            if risk <= 0 or (direction == "long" and stop >= entry) or (direction == "short" and stop <= entry):
                continue
            t1 = entry + t1_r * risk if direction == "long" else entry - t1_r * risk
            t2 = entry + t2_r * risk if direction == "long" else entry - t2_r * risk
            fwd = S["fwd"][i + 1:i + 1 + fwd_bars]
            if len(fwd) < 4:
                continue
            res = ts.simulate(fwd, direction, stop, t1, t2, entry_price=entry, candle_minutes=15)
            if not res:
                continue
            last[key] = S["ts"][i]
            trades.append({"symbol": sym, "t": S["ts"][i] + BAR, "direction": direction, "side": side,
                           "liq_notional": tot, "risk_pct": res["risk_pct"], "res": res,
                           "major": sym in ("BTCUSDT", "ETHUSDT")})
    trades.sort(key=lambda t: t["t"])
    return trades


def split(trades, frac=0.6):
    k = int(len(trades) * frac)
    return trades[:k], trades[k:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=50)
    ap.add_argument("--skip-fetch", action="store_true")
    args = ap.parse_args()
    t0 = time.time()

    rows = load_prints()
    per, hours = bucket(rows)
    syms = sorted(per, key=lambda s: -sum(v[0] + v[1] for v in per[s].values()))
    span_h = (rows[-1][0] - rows[0][0]) // 3_600_000 + 1
    print(f"prints={len(rows)} symbols={len(syms)} span={span_h/24:.0f}d hourly coverage={100*len(hours)/span_h:.0f}%")

    client = HTTP(testnet=False, timeout=20)
    series = {}
    for s in syms:
        kl = fetch_closed_klines(client, s, "15", args.days, skip_fetch=args.skip_fetch)
        if len(kl) < 500:
            print(f"  skip {s}: {len(kl)} bars"); continue
        series[s] = build_series(s, kl, per[s], hours)
    print(f"series built for {len(series)} symbols ({time.time()-t0:.0f}s)")

    GRID = [dict(W=W, k=k, floor=fl, dom=d, M=M, confirm=cf)
            for W, k, fl, d, M, cf in product([1, 2, 4], [10, 30], [50_000, 250_000], [0.7], [0.5, 1.0, 1.5], [0, 1])]
    L = [f"# Liquidation forced-flow fade — {datetime.now(timezone.utc):%Y-%m-%d}",
         f"\nprints={len(rows)}, symbols={len(series)}, span≈{span_h/24:.0f}d, hourly coverage {100*len(hours)/span_h:.0f}% "
         f"(bars eligible only when the collector was alive ±1h). Signal bar = closed 15m; entry next 15m open; "
         f"fwd window 96×15m (1 day); T1 0.75R (50%), BE, +0.3R trail; costs per config. Grid = {len(GRID)} combos × "
         f"{{fade, continuation}} × stop pad {{0.25, 0.5}} ATR × T2 {{1.5, 2.0}}. Every combo is listed; nothing here "
         f"is out-of-sample-selected — with this little data, treat the best rows as optimistic.\n",
         "| mode | W | k×base | floor | M(ATR) | confirm | pad | T2 | ALL | TRAIN | TEST | majors | alts | long | short |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    results = []
    for mode in ("fade", "continuation"):
        for prm in GRID:
            for pad, t2 in product([0.25, 0.5], [1.5, 2.0]):
                if mode == "continuation" and (pad != 0.25):
                    continue
                tr = run_combo(series, prm, mode, 96, pad, t2)
                if len(tr) < 15:
                    continue
                a, b = split(tr)
                row = {"mode": mode, "prm": prm, "pad": pad, "t2": t2, "n": len(tr),
                       "all": stats([t["res"] for t in tr]), "train": stats([t["res"] for t in a]),
                       "test": stats([t["res"] for t in b]),
                       "majors": stats([t["res"] for t in tr if t["major"]]),
                       "alts": stats([t["res"] for t in tr if not t["major"]]),
                       "long": stats([t["res"] for t in tr if t["direction"] == "long"]),
                       "short": stats([t["res"] for t in tr if t["direction"] == "short"]),
                       "trades": tr}
                results.append(row)
    results.sort(key=lambda r: ((r["all"]["profitable_pct"] or 0), r["all"]["net_exp"] or 0), reverse=True)
    for r in results:
        p = r["prm"]
        L.append(f"| {r['mode']} | {p['W']} | {p['k']} | {p['floor']//1000}k | {p['M']} | {p['confirm']} | {r['pad']} | {r['t2']} | "
                 f"{fmt(r['all'])} | {fmt(r['train'])} | {fmt(r['test'])} | {fmt(r['majors'])} | {fmt(r['alts'])} | "
                 f"{fmt(r['long'])} | {fmt(r['short'])} |")
    # summary: how many combos net>0 on ALL, and on both halves
    n_all_pos = sum(1 for r in results if (r["all"]["net_exp"] or 0) > 0)
    n_both = sum(1 for r in results if (r["train"]["net_exp"] or 0) > 0 and (r["test"]["net_exp"] or 0) > 0)
    fade = [r for r in results if r["mode"] == "fade"]; cont = [r for r in results if r["mode"] == "continuation"]
    def med(rs, key):
        v = [r["all"][key] for r in rs if r["all"][key] is not None]
        return st.median(v) if v else None
    L.insert(3, f"Combos with ≥15 trades: {len(results)} (fade {len(fade)}, continuation {len(cont)}). Net>0 over ALL: {n_all_pos}. "
                f"Net>0 on BOTH train and test: {n_both}. Median profitable% — fade {med(fade,'profitable_pct')}, "
                f"continuation {med(cont,'profitable_pct')}; median net — fade {med(fade,'net_exp')}, continuation {med(cont,'net_exp')}.\n")
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    rp = REPORT_DIR / f"liq_fade_{datetime.now(timezone.utc):%Y%m%d}.md"
    rp.write_text("\n".join(L), encoding="utf-8")
    slim = [{k: v for k, v in r.items() if k != "trades"} | {"n_trades": len(r["trades"])} for r in results]
    (REPORT_DIR / f"liq_fade_{datetime.now(timezone.utc):%Y%m%d}_grid.json").write_text(json.dumps(slim, default=str))
    print("\n".join(L[:4]))
    print("\nTop 15 rows:")
    print("\n".join(L[5:20]))
    print(f"\nSaved {rp}  ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
