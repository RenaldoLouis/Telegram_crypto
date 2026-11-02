"""Does the live pre-filter pick the coins where failed_breakout_short works? (2026-11-02)

Pre-registration: logs/backtest_reports/prereg_fbs_selection_20261102.md (written before any data was fetched).
Rebuilds the live coin selection (top 30 by `_ticker_interest_score` + watchlist + momentum hot list) at
every 4h close of 2025-10-01 → 2026-09-20, fires `failed_breakout_short` with the live detector on every
liquid coin, and compares fires on selected vs not-selected coins and vs random shorts, on the live trade
model (entry after the scan lag, `trade_sim` management, costs).

Research only: changes no rule, gate or pick. No order API, no hosted model.

Usage:  python fbs_selection.py [--skip-fetch]   → logs/backtest_reports/fbs_selection_<date>.md
"""

import argparse
import bisect
import json
import random
import statistics
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from pybit.unified_trading import HTTP

import config
import signal_rules as sr
import unified_backtest as ub
from fbs_check import load_live
from fetchers.bybit_data import BybitFetcher

BASE = Path(__file__).parent
EDGE = BASE / "logs" / "backtest_cache" / "edge"
CACHE = BASE / "logs" / "backtest_cache" / "selection"
REPORTS = BASE / "logs" / "backtest_reports"

SIGNAL = "failed_breakout_short"
H4_MS = 14_400_000
M15_MS = 900_000
DAY_MS = 86_400_000


def _ms(y, m, d):
    return int(datetime(y, m, d, tzinfo=timezone.utc).timestamp() * 1000)


TEST_LO, TEST_HI = _ms(2025, 10, 1), _ms(2026, 9, 21)          # signal bars [lo, hi)
VALID_LO, VALID_HI = _ms(2026, 9, 21), _ms(2026, 10, 23)        # reconstruction check
FETCH_LO, FETCH_HI = _ms(2025, 9, 10), _ms(2026, 10, 24)        # 4h bars (warm-up + 48h hot window)
POOL_SIZE = 100
HOT_POOL_SIZE = 50
HOT_WINDOW_MS = 48 * 3_600_000
MIN_TURNOVER = 10_000_000
SCAN_LAG_MS = 2 * 60_000
RANDOM_HALF_WINDOW_MS = int(3.5 * DAY_MS)
WINDOW = ub.WINDOW_CANDLES["4h"]                                # 2 days of 15m bars
DEDUP_MS = 2 * DAY_MS
# Bar (pre-registered)
PF_MIN, GREEN_WEEKS_MIN = 1.3, 0.55
BEAT_RANDOM_R, BEAT_UNSELECTED_R = 0.05, 0.10
VALID_RECALL_MIN = 0.80
BOOT_N, SEED = 5000, 20261102


# ─── Fetch (cached) ──────────────────────────────────────────────────────────

def _get_kline(client, sym, interval, start, end):
    for attempt in range(3):
        try:
            return client.get_kline(category="linear", symbol=sym, interval=interval,
                                    start=start, end=end, limit=1000)
        except Exception as e:  # network / API error: retry, then give up for this page
            if attempt == 2:
                print(f"    ! {sym} {interval} {e}")
                return None
            time.sleep(1.5)


def fetch_range(client, sym, interval, lo, hi, step_ms):
    """Closed bars with open time in [lo, hi), oldest first. None on a failed page (never cached)."""
    out, end = {}, hi - 1
    while end >= lo:
        res = _get_kline(client, sym, interval, lo, end)
        if res is None:
            return None
        rows = res.get("result", {}).get("list", []) or []
        if not rows:
            break
        for r in rows:
            t = int(r[0])
            if lo <= t < hi:
                out[t] = [t] + [float(x) for x in r[1:7]]
        first = min(int(r[0]) for r in rows)
        if first <= lo or len(rows) < 1000:
            break
        end = first - 1
        time.sleep(0.05)
    return [out[k] for k in sorted(out)]


def load_4h(client, sym, skip_fetch):
    p = CACHE / f"{sym}_240.json"
    if p.exists():
        return json.loads(p.read_text())
    if skip_fetch:
        return []
    rows = fetch_range(client, sym, "240", FETCH_LO, FETCH_HI, H4_MS)
    if rows is None:
        return []
    p.write_text(json.dumps(rows))
    return rows


def load_15m(client, sym, intervals, skip_fetch):
    """15m bars covering the merged [lo, hi) intervals; cached per symbol, fetched only where missing."""
    p = CACHE / f"{sym}_15.json"
    have = json.loads(p.read_text()) if p.exists() else {"spans": [], "rows": []}
    rows = {r[0]: r for r in have["rows"]}
    spans = have["spans"]
    changed = False
    for lo, hi in intervals:
        if any(a <= lo and hi <= b for a, b in spans) or skip_fetch:
            continue
        got = fetch_range(client, sym, "15", lo, hi, M15_MS)
        if got is None:
            continue
        for r in got:
            rows[r[0]] = r
        spans.append([lo, hi])
        changed = True
    out = [rows[k] for k in sorted(rows)]
    if changed:
        p.write_text(json.dumps({"spans": spans, "rows": out}))
    return out


def merge(intervals):
    out = []
    for lo, hi in sorted(intervals):
        if out and lo <= out[-1][1]:
            out[-1][1] = max(out[-1][1], hi)
        else:
            out.append([lo, hi])
    return out


# ─── Universe + per-coin series ──────────────────────────────────────────────

def universe():
    by_day = defaultdict(list)
    for f in EDGE.glob("*_D.json"):
        s = f.name[:-7]
        for r in json.loads(f.read_text()):
            if TEST_LO - 3 * DAY_MS <= r[0] < VALID_HI:
                by_day[r[0]].append((r[6], s))
    syms = set(config.WATCHLIST)
    for v in by_day.values():
        v.sort(reverse=True)
        syms |= {s for t, s in v[:POOL_SIZE] if t >= MIN_TURNOVER}
    return sorted(syms)


def _series(path):
    try:
        rows = json.loads(path.read_text())
    except Exception:
        return [], []
    return [int(r[0]) for r in rows], [float(r[1]) for r in rows]


class Coin:
    """4h bars → per-close 24h turnover/change; edge-cache funding + daily OI as of t."""

    def __init__(self, sym, rows4h):
        self.sym = sym
        self.rows = rows4h
        self.close_ts = [int(r[0]) + H4_MS for r in rows4h]
        self.pos = {t: i for i, t in enumerate(self.close_ts)}
        self.f_ts, self.f_v = _series(EDGE / f"{sym}_funding.json")
        self.o_ts, self.o_v = _series(EDGE / f"{sym}_oi.json")

    def ticker_at(self, t):
        i = self.pos.get(t)
        if i is None or i < 6 or self.close_ts[i - 6] != t - DAY_MS:
            return None  # needs six contiguous bars and the close 24h earlier
        turnover = sum(self.rows[k][6] for k in range(i - 5, i + 1))
        base = self.rows[i - 6][4]
        pct = (self.rows[i][4] / base - 1) * 100 if base else 0.0
        j = bisect.bisect_right(self.f_ts, t) - 1
        k = bisect.bisect_right(self.o_ts, t) - 1
        return {"symbol": self.sym, "price_change_24h_pct": pct, "turnover_24h_usd": turnover,
                "volume_24h": sum(self.rows[x][5] for x in range(i - 5, i + 1)),
                "funding_rate_pct": self.f_v[j] * 100 if j >= 0 else 0.0,
                "open_interest": self.o_v[k] if k >= 0 else 0.0,
                # The study replays the scan AS IT RAN in 2025-26: the pre-filter compared the coin
                # count to its dollar thresholds (fixed 2026-11-02, it now reads the USD value). Feed
                # the coin count into the field the scorer reads so the replay stays the old scan.
                "open_interest_value": self.o_v[k] if k >= 0 else 0.0}


# ─── Selection replay ────────────────────────────────────────────────────────

def replay_selection(coins, closes):
    """{t: (selected set, {sym: 24h turnover})} using the live scoring + hot list + top-30 procedure."""
    flags = defaultdict(list)          # sym -> [(t, vol_accel)]
    prev_turn = {}
    sel = {}
    for t in closes:
        tick = {}
        for c in coins.values():
            x = c.ticker_at(t)
            if x:
                tick[c.sym] = x
        ranked = sorted(tick.values(), key=lambda x: -x["turnover_24h_usd"])
        # momentum pulse on the top 50 (2h pulse approximated on the 4h grid)
        for x in ranked[:HOT_POOL_SIZE]:
            s, pct, turn = x["symbol"], abs(x["price_change_24h_pct"]), x["turnover_24h_usd"]
            accel = turn / prev_turn[s] if prev_turn.get(s) else None
            big = pct > config.MOMENTUM_BIG_MOVE_PCT and turn > config.MOMENTUM_BIG_MOVE_TURNOVER
            squeeze = (abs(x["funding_rate_pct"]) > config.MOMENTUM_FUNDING_EXTREME_PCT
                       and pct > config.MOMENTUM_FUNDING_MOVE_PCT)
            vacc = accel is not None and accel > config.MOMENTUM_VOLUME_ACCEL_THRESHOLD
            if big or squeeze or vacc:
                flags[s].append((t, accel))
        prev_turn = {x["symbol"]: x["turnover_24h_usd"] for x in ranked}
        hot_map = {}
        for s, fl in flags.items():
            live_fl = [f for f in fl if t - HOT_WINDOW_MS < f[0] <= t]
            if live_fl:
                hot_map[s] = {"volume_acceleration": live_fl[-1][1]}
        watch = set(config.WATCHLIST) | set(hot_map)
        scored = []
        for x in ranked[:POOL_SIZE]:
            score, disq = BybitFetcher._ticker_interest_score(x, hot_map=hot_map)
            if disq and x["symbol"] not in watch:
                continue
            scored.append((x["symbol"], score))
        scored.sort(key=lambda kv: kv[1], reverse=True)   # stable: ties keep turnover order, as live
        chosen = [s for s, _ in scored if s in watch]
        picked = set(chosen)
        for s, _ in scored:
            if len(picked) >= config.TOP_MOVERS_LIMIT:
                break
            picked.add(s)
        picked |= watch
        sel[t] = (picked, {s: x["turnover_24h_usd"] for s, x in tick.items()})
    return sel


# ─── Trades ──────────────────────────────────────────────────────────────────

def fires_for(coin):
    if len(coin.rows) < 80:
        return []
    df = sr.compute_indicators([[str(int(r[0]))] + [str(x) for x in r[1:7]] for r in coin.rows])
    out = []
    for i in range(60, len(df)):
        for s in sr.detect_at(df, i, "4h", enabled={SIGNAL}):
            out.append({"sym": coin.sym, "t": int(df["timestamp"].iat[i]) + H4_MS,
                        "stop": float(s["stop_price"]), "atr": float(df["atr"].iat[i])})
    return out


class Sim:
    def __init__(self, m15):
        self.ts = [r[0] for r in m15]
        self.c = [{"open": r[1], "high": r[2], "low": r[3], "close": r[4]} for r in m15]

    def short(self, bar_t, stop=None, k=None, atr=None):
        """Net blended R of a short after the bar closing at bar_t, entered at the live time."""
        j = bisect.bisect_left(self.ts, bar_t + SCAN_LAG_MS)
        fwd = self.c[j:j + WINDOW]
        if len(fwd) < WINDOW or self.ts[j] - (bar_t + SCAN_LAG_MS) > M15_MS:
            return None, None  # missing data or a gap at the entry
        entry = fwd[0]["open"]
        stop = stop if stop is not None else entry + k * atr
        if stop <= entry or not atr:
            return None, None
        r = ub.sim_trade({"entry": entry, "stop": stop, "direction": "short", "target_r": 2.0,
                          "atr": atr, "_fwd": fwd})
        return (r["net_blended_rr"] if r else None), (stop - entry) / atr


def dedup(trades):
    last, out = {}, []
    for x in sorted(trades, key=lambda x: x["t"]):
        p = last.get(x["sym"])
        if p is not None and x["t"] < p + DEDUP_MS:
            continue
        last[x["sym"]] = x["t"]
        out.append(x)
    return out


# ─── Stats ───────────────────────────────────────────────────────────────────

def bets(rows, key):
    g = defaultdict(list)
    for r in rows:
        g[r["t"]].append(r[key])
    return [statistics.mean(v) for v in g.values()]


def boot(values, n=BOOT_N, seed=SEED):
    rng = random.Random(seed)
    m = sorted(statistics.mean(rng.choices(values, k=len(values))) for _ in range(n))
    return m[int(0.025 * n)], m[int(0.975 * n) - 1]


def boot_diff(a, b, n=BOOT_N, seed=SEED):
    rng = random.Random(seed)
    m = sorted(statistics.mean(rng.choices(a, k=len(a))) - statistics.mean(rng.choices(b, k=len(b)))
               for _ in range(n))
    return m[int(0.025 * n)], m[int(0.975 * n) - 1]


def quality(nets, ts_list):
    gp = sum(x for x in nets if x > 0)
    gl = -sum(x for x in nets if x < 0)
    wk = defaultdict(float)
    for x, t in zip(nets, ts_list):
        d = datetime.fromtimestamp(t / 1000, tz=timezone.utc).isocalendar()
        wk[(d[0], d[1])] += x
    return {"n": len(nets), "net": statistics.mean(nets) if nets else 0.0,
            "pf": gp / gl if gl else float("inf"),
            "prof": 100 * sum(1 for x in nets if x > 0) / len(nets) if nets else 0.0,
            "green": sum(1 for v in wk.values() if v > 0) / len(wk) if wk else 0.0, "weeks": len(wk)}


def fmt(q):
    return (f"n={q['n']} · {q['prof']:.1f}% profitable · net {q['net']:+.3f}R · PF {q['pf']:.2f} · "
            f"{100*q['green']:.0f}% of {q['weeks']} weeks green")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-fetch", action="store_true")
    args = ap.parse_args()
    CACHE.mkdir(parents=True, exist_ok=True)
    client = HTTP(testnet=False, timeout=20)
    t0 = time.time()

    syms = universe()
    print(f"Universe: {len(syms)} coins")
    coins = {}
    for n, s in enumerate(syms, 1):
        rows = load_4h(client, s, args.skip_fetch)
        if rows:
            coins[s] = Coin(s, rows)
        if n % 50 == 0:
            print(f"  4h {n}/{len(syms)} ({time.time() - t0:.0f}s)")
    print(f"4h data for {len(coins)}/{len(syms)} coins ({time.time() - t0:.0f}s)")

    closes = list(range(TEST_LO - 3 * DAY_MS, VALID_HI, H4_MS))
    sel = replay_selection(coins, closes)
    sizes = [len(sel[t][0]) for t in closes if TEST_LO <= t < TEST_HI]
    print(f"Selection replayed: median {statistics.median(sizes)} coins per scan ({time.time() - t0:.0f}s)")

    # fires on liquid coins (24h turnover ≥ $10M at the fire)
    fires = []
    for c in coins.values():
        for f in fires_for(c):
            if not (TEST_LO <= f["t"] < VALID_HI) or f["t"] not in sel:
                continue
            picked, turn = sel[f["t"]]
            if turn.get(f["sym"], 0) < MIN_TURNOVER:
                continue
            f["selected"] = f["sym"] in picked
            fires.append(f)
    print(f"Fires on liquid coins: {len(fires)} ({sum(f['selected'] for f in fires)} selected)")

    # validity gate: live record in the validation span
    live = [r for r in load_live() if VALID_LO <= r["bar_ms"] < VALID_HI]
    hit = [r for r in live if r["bar_ms"] in sel and r["symbol"] in sel[r["bar_ms"]][0]]
    recall = len(hit) / len(live) if live else 0
    print(f"Reconstruction recall on the live record: {len(hit)}/{len(live)} = {100*recall:.0f}%")

    # 15m windows around every fire (signal + random draws)
    need = defaultdict(list)
    for f in fires:
        need[f["sym"]].append((f["t"] - RANDOM_HALF_WINDOW_MS - DAY_MS,
                               f["t"] + RANDOM_HALF_WINDOW_MS + 3 * DAY_MS))
    sims = {}
    for n, (s, iv) in enumerate(sorted(need.items()), 1):
        sims[s] = Sim(load_15m(client, s, merge(iv), args.skip_fetch))
        if n % 25 == 0:
            print(f"  15m {n}/{len(need)} ({time.time() - t0:.0f}s)")

    def score_group(group):
        rows = []
        for f in dedup(group):
            sim_ = sims[f["sym"]]
            net, k = sim_.short(f["t"], stop=f["stop"], atr=f["atr"])
            if net is None:
                continue
            c = coins[f["sym"]]
            rnd = []
            t = f["t"] - RANDOM_HALF_WINDOW_MS
            t -= t % H4_MS
            while t <= f["t"] + RANDOM_HALF_WINDOW_MS:
                i = c.pos.get(t)
                if t != f["t"] and i is not None:
                    df_atr = _atr_at(c, i)
                    x, _ = sim_.short(t, k=k, atr=df_atr) if df_atr else (None, None)
                    if x is not None:
                        rnd.append(x)
                t += H4_MS
            rows.append({"sym": f["sym"], "t": f["t"], "net": net,
                         "rnd": statistics.mean(rnd) if len(rnd) >= 10 else None})
        return rows

    atr_cache = {}

    def _atr_at(c, i):
        if c.sym not in atr_cache:
            df = sr.compute_indicators([[str(int(r[0]))] + [str(x) for x in r[1:7]] for r in c.rows])
            atr_cache[c.sym] = [float(x) for x in df["atr"].tolist()]
        v = atr_cache[c.sym][i]
        return v if v == v and v > 0 else None

    test = [f for f in fires if TEST_LO <= f["t"] < TEST_HI]
    S = score_group([f for f in test if f["selected"]])
    U = score_group([f for f in test if not f["selected"]])
    V = score_group([f for f in fires if VALID_LO <= f["t"] < VALID_HI and f["selected"]])
    VU = score_group([f for f in fires if VALID_LO <= f["t"] < VALID_HI and not f["selected"]])
    print(f"Scored: selected {len(S)}, not selected {len(U)} ({time.time() - t0:.0f}s)")

    # ── bar
    qs, qu = quality([r["net"] for r in S], [r["t"] for r in S]), quality([r["net"] for r in U], [r["t"] for r in U])
    b1 = qs["net"] > 0 and qs["pf"] >= PF_MIN and qs["green"] >= GREEN_WEEKS_MIN
    Sr = [dict(r, diff=r["net"] - r["rnd"]) for r in S if r["rnd"] is not None]
    d_bets = bets(Sr, "diff")
    d_mean = statistics.mean(r["diff"] for r in Sr) if Sr else 0
    d_ci = boot(d_bets) if d_bets else (0, 0)
    b2 = d_mean >= BEAT_RANDOM_R and d_ci[0] > 0
    su_diff = qs["net"] - qu["net"]
    su_ci = boot_diff(bets(S, "net"), bets(U, "net")) if S and U else (0, 0)
    b3 = su_diff >= BEAT_UNSELECTED_R and su_ci[0] > 0
    half = sorted(S, key=lambda r: r["t"])
    h1, h2 = half[: len(half) // 2], half[len(half) // 2:]
    m1 = statistics.mean(r["net"] for r in h1) if h1 else 0
    m2 = statistics.mean(r["net"] for r in h2) if h2 else 0
    b4 = m1 > 0 and m2 > 0
    valid = recall >= VALID_RECALL_MIN
    verdict = ("VOID (reconstruction below the validity gate)" if not valid else
               "PASS" if (b1 and b2 and b3 and b4) else "FAIL")

    Ur = [r for r in U if r["rnd"] is not None]
    bym = defaultdict(lambda: [[], []])
    for r in S:
        bym[datetime.fromtimestamp(r["t"] / 1000, tz=timezone.utc).strftime("%Y-%m")][0].append(r["net"])
    for r in U:
        bym[datetime.fromtimestamp(r["t"] / 1000, tz=timezone.utc).strftime("%Y-%m")][1].append(r["net"])

    L = [f"# Does the live pre-filter pick the coins where failed_breakout_short works? — {datetime.now(timezone.utc):%Y-%m-%d}",
         "", "Pre-registration: `prereg_fbs_selection_20261102.md`. TEST = signal bars 2025-10-01 → 2026-09-20. "
         f"Universe {len(coins)} coins with 4h data (of {len(syms)}); selection replayed at every 4h close "
         f"(median {statistics.median(sizes)} coins per scan). Entry at the live time (close + 2 min → next 15m open), "
         f"limit_open, trade_sim management, costs. 2-day dedup per coin within each group.", "",
         "## Validity gate", "",
         f"- Live record 2026-09-21 → 10-22 marked selected by the reconstruction: {len(hit)}/{len(live)} "
         f"= **{100*recall:.0f}%** (gate ≥ 80%) → **{'VALID' if valid else 'VOID'}**",
         f"- Same span, reconstructed: selected {fmt(quality([r['net'] for r in V], [r['t'] for r in V])) if V else 'n=0'} · "
         f"not selected {fmt(quality([r['net'] for r in VU], [r['t'] for r in VU])) if VU else 'n=0'}", "",
         "## TEST results", "",
         f"- **Selected:** {fmt(qs)}",
         f"- **Not selected** (liquid, not in the scan): {fmt(qu)}",
         f"- Fires on liquid coins in TEST: {len(test)} ({sum(f['selected'] for f in test)} selected) before dedup", "",
         "| # | bar | result | |", "|---|---|---|---|",
         f"| 1 | quality on the selected book: net > 0, PF ≥ 1.3, ≥ 55% weeks green | net {qs['net']:+.3f}R, PF {qs['pf']:.2f}, "
         f"{100*qs['green']:.0f}% weeks | {'✓' if b1 else '✗'} |",
         f"| 2 | beats random shorts (same coin ±3.5 d) by ≥ +0.05R, CI lower > 0 | {d_mean:+.3f}R "
         f"(signal {statistics.mean(r['net'] for r in Sr) if Sr else 0:+.3f} vs random {statistics.mean(r['rnd'] for r in Sr) if Sr else 0:+.3f}), "
         f"per bet CI [{d_ci[0]:+.3f}, {d_ci[1]:+.3f}] | {'✓' if b2 else '✗'} |",
         f"| 3 | selected − not selected ≥ +0.10R, CI lower > 0 | {su_diff:+.3f}R, CI [{su_ci[0]:+.3f}, {su_ci[1]:+.3f}] | "
         f"{'✓' if b3 else '✗'} |",
         f"| 4 | selected net > 0 in both halves | {m1:+.3f}R / {m2:+.3f}R | {'✓' if b4 else '✗'} |", "",
         f"**Verdict: {verdict}**", "",
         "## Descriptive", "",
         f"- Not selected vs its own random baseline: {statistics.mean(r['net'] for r in Ur) if Ur else 0:+.3f} vs "
         f"{statistics.mean(r['rnd'] for r in Ur) if Ur else 0:+.3f}R (n {len(Ur)})", "",
         "| month | selected n | selected net R | not selected n | not selected net R |", "|---|---|---|---|---|"]
    for m in sorted(bym):
        a, b = bym[m]
        L.append(f"| {m} | {len(a)} | {statistics.mean(a) if a else 0:+.3f} | {len(b)} | {statistics.mean(b) if b else 0:+.3f} |")
    L += ["", "_Approximations (stated in the pre-registration): non-crypto perps ignored in the top-100 ranking; "
          "daily open interest; settled funding instead of the predicted rate; the 2h momentum pulse replayed on the "
          "4h grid; coins delisted before today may lack 4h data._"]
    out = REPORTS / f"fbs_selection_{datetime.now(timezone.utc):%Y%m%d}.md"
    out.write_text("\n".join(L))
    print("\n".join(L))
    print(f"\n→ {out} ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
