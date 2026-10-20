"""Replay the live daily-book policy (main.select_daily_picks) over the 2026-09-23 unified backtest.

Each backtest trade = one gated candidate at its signal close. Scans are processed in close-time
order; within a scan the live priority applies; one per coin per UTC day; max 3/day; cross-run
dedup = no new candidate for (symbol, direction, source) within 48h of the last persisted one.
"""
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402
import main  # noqa: E402
import mechanical_setups as ms  # noqa: E402

TRADES = Path(__file__).resolve().parent / "logs/backtest_reports/unified_20260923_trades.json"
raw = json.load(open(TRADES))
min_n = config.SURFACE_MIN_TEST_N
surfaced = {sig for (sig, tf), hit in ms.EXPECTANCY.items()
            if hit >= config.SURFACE_MIN_HIT_RATE and (ms.TEST_N.get((sig, tf)) or 0) >= min_n}
live_keys = set(ms.EXPECTANCY)

trades = sorted((t for t in raw if (t["signal"], t["tf"]) in live_keys), key=lambda t: t["signal_ms"])
test_start = trades[int(len(trades) * 0.6)]["signal_time"][:10]  # same 60/40 chrono split as the harness


def replay(pool, picks_max=3, dirs=("long", "short"), four_h_only_1h=False):
    config.DAILY_PICKS_MAX = picks_max
    config.DAILY_DIRECTIONS = dirs
    by_scan = defaultdict(list)
    for t in pool:
        ts = datetime.fromisoformat(t["signal_time"])
        if four_h_only_1h and t["tf"] == "1h" and ts.hour % 4:
            continue
        by_scan[ts].append(t)
    last = {}
    picked_by_day = defaultdict(list)
    out = []
    for ts in sorted(by_scan):
        cands = []
        for t in by_scan[ts]:
            src = "watch" if t["signal"] in surfaced else "shadow"
            k = (t["symbol"], t["direction"], src)
            if k in last and ts - last[k] < timedelta(hours=48):
                continue
            last[k] = ts
            cands.append({"symbol": t["symbol"], "direction": t["direction"],
                          "signal_name": t["signal"], "rank": None, "_t": t})
        seen = set()
        cands = [c for c in cands if not (c["symbol"] in seen or seen.add(c["symbol"]))]  # one per symbol per run
        day = ts.date()
        for p in main.select_daily_picks(cands, picked_by_day[day]):
            picked_by_day[day].append(p)
            out.append(p["_t"])
    return out


def stats(rows):
    if not rows:
        return "n=0"
    n = len(rows)
    prof = sum(1 for t in rows if t["result"]["profitable"])
    net = sum(t["result"]["net_blended_rr"] for t in rows)
    return f"n={n:4d}  profitable {100 * prof / n:5.1f}%  net {net / n:+.3f}R/trade  total {net:+6.1f}R"


def report(title, picks):
    days = len({t["signal_time"][:10] for t in picks})
    print(f"\n=== {title} — {days} days with a pick")
    print(f"  ALL          {stats(picks)}")
    print(f"  TRAIN <{test_start} {stats([t for t in picks if t['signal_time'][:10] < test_start])}")
    print(f"  TEST >={test_start} {stats([t for t in picks if t['signal_time'][:10] >= test_start])}")
    for d in ("short", "long"):
        print(f"  {d:6s}       {stats([t for t in picks if t['direction'] == d])}")
    by_m = defaultdict(list)
    for t in picks:
        by_m[t["signal_time"][:7]].append(t)
    for m in sorted(by_m):
        print(f"  {m}      {stats(by_m[m])}")
    by_s = defaultdict(list)
    for t in picks:
        by_s[t["signal"]].append(t)
    for s in sorted(by_s, key=lambda s: -len(by_s[s])):
        print(f"  {s:24s}{stats(by_s[s])}")


print(f"backtest {trades[0]['signal_time'][:10]} -> {trades[-1]['signal_time'][:10]}, "
      f"{len({t['symbol'] for t in trades})} symbols, {len(trades)} candidate trades; surfaced rules: {surfaced}")
report("LIVE POLICY: 3/day, both directions", replay(trades))
report("3/day, 1h signals only at 4h closes (conservative coverage)", replay(trades, four_h_only_1h=True))
report("3/day, shorts only", replay(trades, dirs=("short",)))
report("1/day, both directions", replay(trades, picks_max=1))
