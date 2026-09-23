"""Unified backtester — validates signals under EXACTLY the trade the live pipeline takes.

Why this exists (audit 2026-09-23): the old `historical_backtester.py` entered at the
signal bar's close, held 8 days on 4h, charged no costs, had no T1/BE/trail, and
detected on bars the live scan never saw (the live detector read the OPEN bar). Every
"validated" expectancy therefore described a trade that was never traded. This harness
shares two modules with the live path so drift is impossible by construction:

  * `signal_rules.detect_at(df, i, tf)`  — the SAME detector the scan runs on the
                                             last CLOSED bar
  * `trade_sim.simulate(...)`            — the SAME simulator `weekly_eval.py` scores with
                                             (market-at-next-open, wick stops, T1 partial,
                                             BE + 0.3R trail, 2-day window, costs)

Forward simulation runs on 15m candles (like the evaluator), signals on 4h/1h closed
bars. Objective (user, 2026-09-23): maximise the % of suggestions that close PROFITABLE
net of cost (blended R > 0) subject to net expectancy > 0, target >= 70%.

Research-only: zero trading decisions, no order API, no Claude calls.

Usage:
    venv/bin/python unified_backtest.py                      # auto universe, 30 symbols, 180d
    venv/bin/python unified_backtest.py --quick              # 10 symbols
    venv/bin/python unified_backtest.py --skip-fetch         # cache only
    venv/bin/python unified_backtest.py --signals trend_pullback_short,failed_breakout_short
"""

import argparse
import bisect
import json
import math
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from itertools import product
from pathlib import Path

import pandas as pd
from pybit.unified_trading import HTTP

import config
import signal_rules as sr
import derivs_data as dd
import trade_sim as ts

BASE_DIR = Path(__file__).parent
CACHE_DIR = BASE_DIR / "logs" / "backtest_cache" / "unified"
REPORT_DIR = BASE_DIR / "logs" / "backtest_reports"
SETUPS_DIR = BASE_DIR / "logs" / "setups"

INTERVAL_MS = {"15": 900_000, "60": 3_600_000, "240": 14_400_000, "D": 86_400_000}
TF_LABEL = {"60": "1h", "240": "4h"}
# Mirror weekly_eval.EVAL_WINDOWS: 4h signal -> intraday (2d), 1h signal -> scalp (1d).
WINDOW_CANDLES = {"4h": 192, "1h": 96}
DEDUP_DAYS = getattr(config, "UB_DEDUP_DAYS", 2)                 # live cross-run dedup window
MIN_HISTORY_DAYS = getattr(config, "UB_MIN_HISTORY_DAYS", 60)    # skip newer listings
DEFAULT_T1_R = getattr(config, "UB_DEFAULT_T1_R", 0.75)
SHIP_PROFITABLE_PCT = getattr(config, "UB_SHIP_PROFITABLE_PCT", 70.0)
CANDIDATE_PROFITABLE_PCT = getattr(config, "UB_CANDIDATE_PROFITABLE_PCT", 60.0)
MIN_TEST_N = getattr(config, "UB_MIN_TEST_N", 20)
SHIP_MIN_N = getattr(config, "UB_SHIP_MIN_N", 30)

try:
    from historical_backtester import EXPANDED_SYMBOLS as MAJORS
except Exception:  # pragma: no cover
    MAJORS = ["ADAUSDT", "XRPUSDT", "SOLUSDT", "BTCUSDT", "ETHUSDT", "DOGEUSDT",
              "SUIUSDT", "XLMUSDT", "ENAUSDT", "HBARUSDT", "TRXUSDT", "NEARUSDT",
              "OPUSDT", "ARBUSDT", "INJUSDT"]
MAJORS_SET = set(MAJORS)


# ─── Data ────────────────────────────────────────────────────────────────────

def _now_ms():
    return int(time.time() * 1000)


def fetch_closed_klines(client, symbol, interval, days, skip_fetch=False):
    """Paginated closed-bar klines (oldest first) with a per-day cache file."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    now = _now_ms()
    end_day = datetime.now(timezone.utc).strftime("%Y%m%d")
    start_ms = now - days * 86_400_000
    start_day = datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc).strftime("%Y%m%d")
    cp = CACHE_DIR / f"{symbol}_{interval}_{start_day}_{end_day}.json"
    if cp.exists():
        return json.loads(cp.read_text())
    if skip_fetch:
        return []
    step = INTERVAL_MS[interval]
    out = []
    # Bybit answers a start/end window with the NEWEST `limit` bars, so page backwards.
    cursor_end = now
    pages = 0
    while cursor_end > start_ms and pages < 80:
        try:
            res = client.get_kline(category="linear", symbol=symbol, interval=interval,
                                   start=start_ms, end=cursor_end, limit=1000)
        except Exception as e:
            print(f"    ! {symbol} {interval} fetch error: {e}")
            break
        rows = res.get("result", {}).get("list", []) or []
        if not rows:
            break
        rows.reverse()  # oldest first
        for r in rows:
            t = int(r[0])
            if t < start_ms or t + step > now:
                continue  # outside window / still open
            out.append([str(t)] + [str(x) for x in r[1:7]])
        first_t = int(rows[0][0])
        if first_t <= start_ms or len(rows) < 1000:
            break
        cursor_end = first_t - 1
        pages += 1
        time.sleep(0.1)
    # sort + de-dup by timestamp (page overlap safety)
    by_ts = {}
    for r in out:
        by_ts[int(r[0])] = r
    dedup = [by_ts[k] for k in sorted(by_ts)]
    cp.write_text(json.dumps(dedup))
    return dedup


def auto_universe(max_symbols):
    """Live universe (symbols the pre-filter actually selected, by frequency) blended
    with the majors set. Half the slots go to majors (needed for the majors-vs-others
    cut), half to the most frequent non-major live symbols. BTCUSDT always included."""
    freq = Counter()
    for f in SETUPS_DIR.glob("setups_*.json"):
        try:
            rec = json.loads(f.read_text())
            for s in rec.get("setups", []):
                if s.get("symbol"):
                    freq[s["symbol"]] += 1
        except Exception:
            continue
    live_non_major = [s for s, _ in freq.most_common() if s not in MAJORS_SET]
    n_major = min(len(MAJORS), max(1, max_symbols // 2))
    picked = ["BTCUSDT"] + [m for m in MAJORS if m != "BTCUSDT"][: n_major - 1]
    for s in live_non_major:
        if len(picked) >= max_symbols:
            break
        picked.append(s)
    for m in MAJORS:  # fill any leftover slots with more majors
        if len(picked) >= max_symbols:
            break
        if m not in picked:
            picked.append(m)
    return picked


# ─── Feature helpers ─────────────────────────────────────────────────────────

class TrendIndex:
    """Trend (ema20 vs ema50) lookup by time using only bars CLOSED before t."""

    def __init__(self, df, interval):
        self.close_ts = [] if df is None or df.empty else \
            [int(x) + INTERVAL_MS[interval] for x in df["timestamp"].tolist()]
        self.bull = [] if df is None or df.empty else \
            (df["ema20"] > df["ema50"]).tolist()
        self.close = [] if df is None or df.empty else df["close"].tolist()

    def idx_at(self, t_ms):
        # last bar whose close time <= t_ms
        j = bisect.bisect_right(self.close_ts, t_ms) - 1
        return j if j >= 0 else None

    def trend_at(self, t_ms):
        j = self.idx_at(t_ms)
        if j is None:
            return None
        return "bullish" if self.bull[j] else "bearish"

    def change_pct(self, t_ms, bars_back):
        j = self.idx_at(t_ms)
        if j is None or j - bars_back < 0:
            return None
        base = self.close[j - bars_back]
        return round((self.close[j] / base - 1) * 100, 3) if base else None


def _safe(x, nd=4):
    try:
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return None
        return round(float(x), nd)
    except Exception:
        return None


# ─── Signal + simulation loop ────────────────────────────────────────────────

_PREP_CACHE = {}


def _prepare(symbol, data, deriv):
    """Indicator dfs (+ positioning columns) and 15m arrays for one symbol, cached."""
    if symbol in _PREP_CACHE:
        return _PREP_CACHE[symbol]
    m15 = data["15"]
    m15_ts = [int(r[0]) for r in m15]
    m15_c = [{"open": float(r[1]), "high": float(r[2]), "low": float(r[3]),
              "close": float(r[4])} for r in m15]
    dfs = {}
    for iv in ("240", "60", "D"):
        rows = data.get(iv) or []
        dfs[iv] = sr.compute_indicators(rows) if len(rows) >= 60 else None
        if dfs[iv] is not None and iv in ("240", "60"):
            # positioning columns as of each bar's close (funding, OI, 24h price change)
            dd.attach_to_df(dfs[iv], deriv, INTERVAL_MS[iv], 6 if iv == "240" else 24)
    _PREP_CACHE[symbol] = (m15_ts, m15_c, dfs)
    return _PREP_CACHE[symbol]


def build_trades(symbol, data, btc_h4, enabled, tfs, deriv=None, fs_params=None):
    """Walk every closed 4h/1h bar, fire signals, simulate on 15m. Returns trades."""
    if not data["15"]:
        return []
    m15_ts, m15_c, dfs = _prepare(symbol, data, deriv)
    trend_d = TrendIndex(dfs["D"], "D")
    trend_h1 = TrendIndex(dfs["60"], "60")
    trend_h4 = TrendIndex(dfs["240"], "240")

    fired = []  # (close_time_ms, tf_label, i, sig, df)
    for iv in ("240", "60"):
        lbl = TF_LABEL[iv]
        if lbl not in tfs or dfs[iv] is None:
            continue
        df = dfs[iv]
        # pull arrays for fast feature extraction
        for i in range(60, len(df)):
            sigs = sr.detect_at(df, i, lbl, enabled=enabled, params=fs_params)
            if not sigs:
                continue
            close_t = int(df["timestamp"].iat[i]) + INTERVAL_MS[iv]
            for s in sigs:
                fired.append((close_t, lbl, i, s, df))
    fired.sort(key=lambda x: x[0])

    trades = []
    last_by_key = {}  # (symbol, direction) -> close_t of last taken trade
    for close_t, lbl, i, sig, df in fired:
        key = (symbol, sig["direction"])
        prev = last_by_key.get(key)
        if prev is not None and close_t < prev + DEDUP_DAYS * 86_400_000:
            continue
        j = bisect.bisect_left(m15_ts, close_t)
        if j >= len(m15_c):
            continue
        fwd = m15_c[j:j + WINDOW_CANDLES[lbl]]
        if len(fwd) < 4:
            continue
        row = df.iloc[i]
        atr = float(row["atr"])
        entry = fwd[0]["open"]
        stop = sr.levels_for(sig, entry, atr)
        risk = abs(entry - stop)
        if risk <= 0 or (sig["direction"] == "long" and stop >= entry) or \
                (sig["direction"] == "short" and stop <= entry):
            continue
        last_by_key[key] = close_t
        dt = datetime.fromtimestamp(close_t / 1000, tz=timezone.utc)
        direction = sig["direction"]
        want = "bullish" if direction == "long" else "bearish"
        t_d, t_1, t_4 = trend_d.trend_at(close_t), trend_h1.trend_at(close_t), trend_h4.trend_at(close_t)
        conf = sum(1 for t in (t_d, t_1, t_4) if t == want)
        btc_t = btc_h4.trend_at(close_t) if btc_h4 else None
        close = float(row["close"])
        fr = _safe(row.get("funding_rate"), 6)
        oi24 = _safe(row.get("oi_chg_24h_pct"), 2)
        px24 = _safe(row.get("price_chg_24h_pct"), 2)
        oi4 = _safe(deriv.oi_change_pct(close_t, 4), 2) if deriv else None
        # "fading" = trading AGAINST the side that pays funding (shorting when longs pay)
        if fr is None or abs(fr) < 0.00005:
            f_side = "neutral"
        elif (fr > 0 and direction == "short") or (fr < 0 and direction == "long"):
            f_side = "fading_crowd"
        else:
            f_side = "with_crowd"
        h = dt.hour
        session = "21-23" if 21 <= h <= 23 else ("03-04" if 3 <= h <= 4 else
                  ("08-16" if 8 <= h < 16 else "other"))
        trades.append({
            "funding_rate": fr, "funding_mean24h": _safe(row.get("funding_mean24h"), 6),
            "funding_z": _safe(row.get("funding_z"), 2), "funding_side": f_side,
            "oi_chg_24h_pct": oi24, "oi_chg_4h_pct": oi4, "price_chg_24h_pct": px24,
            "oi_divergence": dd.oi_divergence(px24, oi24),
            "settlement_close": bool(row.get("settlement_close", False)),
            "hours_to_settlement": dd.hours_to_settlement(close_t), "session": session,
            "symbol": symbol, "signal": sig["signal"], "tf": lbl, "direction": direction,
            "tier": sig.get("tier", "execute"),
            "signal_time": dt.isoformat(), "signal_ms": close_t,
            "hour_utc": dt.hour, "weekday": dt.weekday(), "is_weekend": dt.weekday() >= 5,
            "entry": entry, "stop": stop, "target_r": float(sig.get("target_r", 2.0)),
            "atr_pct": _safe(atr / close * 100 if close else None, 3),
            "adx": _safe(row["adx"], 2), "rsi": _safe(row["rsi"], 2),
            "vol_spike": _safe(row["vol_spike"], 2),
            "ema20_dist_atr": _safe((close - float(row["ema20"])) / atr, 3),
            "ema50_dist_atr": _safe((close - float(row["ema50"])) / atr, 3),
            "range_pct": _safe((float(row["high_20"]) - float(row["low_20"])) / close * 100
                               if close else None, 3),
            "daily_trend": t_d, "h1_trend": t_1, "h4_trend": t_4, "confluence3": conf,
            "btc_h4_trend": btc_t,
            "btc_24h_change_pct": btc_h4.change_pct(close_t, 6) if btc_h4 else None,
            "btc_aligned": (btc_t == want) if btc_t else None,
            "is_major": symbol in MAJORS_SET,
            "_fwd": fwd,  # dropped before saving
        })
    return trades


def sim_trade(t, t1_r=DEFAULT_T1_R, stop_scale=1.0, t2_r=None, trail=True):
    entry, direction = t["entry"], t["direction"]
    d = abs(entry - t["stop"]) * stop_scale
    stop = entry - d if direction == "long" else entry + d
    t2r = t["target_r"] if t2_r is None else t2_r
    t1 = entry + t1_r * d if direction == "long" else entry - t1_r * d
    t2 = entry + t2r * d if direction == "long" else entry - t2r * d
    return ts.simulate(t["_fwd"], direction, stop, t1, t2, entry_price=entry,
                       candle_minutes=15, trail=trail)


# ─── Stats ───────────────────────────────────────────────────────────────────

def wilson(k, n, z=1.96):
    if n == 0:
        return (None, None)
    p = k / n
    den = 1 + z * z / n
    centre = p + z * z / (2 * n)
    adj = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (round(100 * (centre - adj) / den, 1), round(100 * (centre + adj) / den, 1))


def stats(results):
    s = ts.summarize(results)
    if s["n"]:
        k = sum(1 for r in results if r and r["profitable"])
        s["ci"] = wilson(k, s["n"])
    else:
        s["ci"] = (None, None)
    return s


def fmt(s):
    if not s or not s["n"]:
        return "n=0"
    ci = s.get("ci", (None, None))
    ci_s = f" [{ci[0]}–{ci[1]}]" if ci[0] is not None else ""
    pf = s["net_pf"]
    pf_s = "inf" if pf == float("inf") else f"{pf:.2f}"
    return (f"n={s['n']} prof={s['profitable_pct']}%{ci_s} net={s['net_exp']:+.3f} "
            f"gross={s['gross_exp']:+.3f} PF={pf_s} stop={s['stop_pct']}% mfe={s['avg_mfe']:.2f}")


def split_train_test(trades, frac=0.6):
    tr = sorted(trades, key=lambda t: t["signal_ms"])
    k = int(len(tr) * frac)
    return tr[:k], tr[k:]


# ─── Filter study ────────────────────────────────────────────────────────────

def _band(x, edges, labels):
    if x is None:
        return "na"
    for e, l in zip(edges, labels):
        if x < e:
            return l
    return labels[-1]


FILTERS = {
    "btc_aligned": lambda t: {True: "yes", False: "no", None: "na"}[t["btc_aligned"]],
    "confluence3": lambda t: "0-1" if t["confluence3"] <= 1 else "2-3",
    "risk_pct": lambda t: _band(t["risk_pct"] * 100 if t.get("risk_pct") else None,
                                [2, 4, 8], ["<2%", "2-4%", "4-8%", ">8%"]),
    "hour": lambda t: _band(t["hour_utc"], [8, 16], ["00-08", "08-16", "16-24"]),
    "weekend": lambda t: "weekend" if t["is_weekend"] else "weekday",
    "adx": lambda t: _band(t["adx"], [20, 30], ["<20", "20-30", ">30"]),
    "vol_spike": lambda t: "na" if t["vol_spike"] is None else (">=1.5" if t["vol_spike"] >= 1.5 else "<1.5"),
    "ema50_dist_atr": lambda t: _band(t["ema50_dist_atr"], [-2, -0.5, 0.5, 2],
                                      ["<-2", "-2..-0.5", "-0.5..0.5", "0.5..2", ">2"]),
    "symbol_group": lambda t: "major" if t["is_major"] else "other",
    # positioning / calendar (added 2026-09-23)
    "funding": lambda t: _band(t["funding_rate"] * 100 if t.get("funding_rate") is not None else None,
                               [-0.01, 0.005, 0.02, 0.05], ["<-0.01%", "-0.01..0.005%", "0.005..0.02%", "0.02..0.05%", ">0.05%"]),
    "funding_side": lambda t: t.get("funding_side", "na"),
    "funding_z": lambda t: _band(t.get("funding_z"), [-1, 1, 2], ["<-1", "-1..1", "1..2", ">2"]),
    "oi_divergence": lambda t: t.get("oi_divergence", "na"),
    "oi_chg_24h": lambda t: _band(t.get("oi_chg_24h_pct"), [-5, 0, 5], ["<-5%", "-5..0%", "0..5%", ">5%"]),
    "settlement_bar": lambda t: "settlement" if t.get("settlement_close") else "other",
    "session": lambda t: t.get("session", "na"),
}


def filter_study(train, test):
    """Per filter bucket: train and test stats. Returns (rows, n_cuts)."""
    rows = []
    n_cuts = 0
    for fname, fn in FILTERS.items():
        buckets = defaultdict(lambda: {"train": [], "test": []})
        for t in train:
            buckets[fn(t)]["train"].append(t)
        for t in test:
            buckets[fn(t)]["test"].append(t)
        for b, d in sorted(buckets.items()):
            n_cuts += 1
            s_tr = stats([t["_res"] for t in d["train"]])
            s_te = stats([t["_res"] for t in d["test"]])
            cand = (s_te["n"] >= MIN_TEST_N and (s_te["profitable_pct"] or 0) >= CANDIDATE_PROFITABLE_PCT
                    and (s_te["net_exp"] or 0) > 0 and s_tr["n"] > 0 and (s_tr["net_exp"] or 0) > 0)
            rows.append({"filter": fname, "bucket": b, "train": s_tr, "test": s_te, "candidate": cand,
                         "train_trades": d["train"], "test_trades": d["test"]})
    return rows, n_cuts


# ─── Management sweep ────────────────────────────────────────────────────────

MGMT_GRID = list(product([0.5, 0.75, 1.0], [0.75, 1.0, 1.5], [1.5, 2.0], [True, False]))


def mgmt_sweep(train, test):
    """Choose (t1, stop_scale, t2, trail) on TRAIN: max profitable% s.t. net>0.
    Returns (best_combo, train_stats, test_stats, default_test_stats)."""
    best = None
    for t1, sc, t2, trail in MGMT_GRID:
        res = [sim_trade(t, t1, sc, t2, trail) for t in train]
        s = stats(res)
        if not s["n"] or (s["net_exp"] or 0) <= 0:
            continue
        key = (s["profitable_pct"], s["net_exp"])
        if best is None or key > best[0]:
            best = (key, (t1, sc, t2, trail), s)
    if best is None:
        return None, None, None
    combo = best[1]
    te = stats([sim_trade(t, *combo) for t in test])
    return combo, best[2], te


# ─── Report ──────────────────────────────────────────────────────────────────

def month_table(trades):
    by = defaultdict(list)
    for t in trades:
        by[t["signal_time"][:7]].append(t["_res"])
    lines = ["| month | n | profitable% | net exp |", "|---|---|---|---|"]
    for m in sorted(by):
        s = stats(by[m])
        lines.append(f"| {m} | {s['n']} | {s['profitable_pct']} | {s['net_exp']:+.3f} |")
    return "\n".join(lines)


FS_GRID = list(product([0.0001, 0.0002, 0.0003, 0.0005], [0.0, 3.0], [3.0, 5.0], [True, False]))


def funding_sweep(data, derivs, btc_h4, sig):
    """Rebuild funding-squeeze trades for each parameter combo. Returns rows sorted by
    (train qualifies, train profitable%, train net); each row has train/test/all stats."""
    rows = []
    for fmin, oimin, flat, settle in FS_GRID:
        prm = {"fs_funding_min": fmin, "fs_oi_min_pct": oimin, "fs_price_flat_pct": flat,
               "fs_settlement_only": settle}
        trades = []
        for sym, d in data.items():
            trades.extend(build_trades(sym, d, btc_h4, {sig}, {"4h"}, deriv=derivs.get(sym), fs_params=prm))
        for t in trades:
            t["_res"] = sim_trade(t)
        trades = [t for t in trades if t["_res"]]
        if not trades:
            continue
        train, test = split_train_test(trades)
        s_tr, s_te, s_all = stats([t["_res"] for t in train]), stats([t["_res"] for t in test]), stats([t["_res"] for t in trades])
        ok = s_tr["n"] >= 30 and (s_tr["net_exp"] or 0) > 0
        rows.append({"params": prm, "train": s_tr, "test": s_te, "all": s_all, "qualifies": ok})
    rows.sort(key=lambda r: (r["qualifies"], r["train"]["profitable_pct"] or 0, r["train"]["net_exp"] or 0), reverse=True)
    return rows


def run(args):
    t0 = time.time()
    enabled = set(args.signals.split(",")) if args.signals else None
    tfs = set(args.tfs.split(","))
    if args.symbols and args.symbols != "auto":
        symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    else:
        symbols = auto_universe(10 if args.quick else args.max_symbols)
    if "BTCUSDT" not in symbols:
        symbols.insert(0, "BTCUSDT")
    print(f"Universe ({len(symbols)}): {', '.join(symbols)}")

    client = HTTP(testnet=False, timeout=20)
    data = {}
    derivs = {}
    skipped = []
    for n, sym in enumerate(symbols, 1):
        d = {}
        for iv in ("240", "60", "D", "15"):
            d[iv] = fetch_closed_klines(client, sym, iv, args.days, skip_fetch=args.skip_fetch)
        h4 = d["240"]
        span_days = (int(h4[-1][0]) - int(h4[0][0])) / 86_400_000 if len(h4) > 1 else 0
        if span_days < MIN_HISTORY_DAYS or len(d["15"]) < 500:
            skipped.append(f"{sym} ({span_days:.0f}d 4h, {len(d['15'])} 15m bars)")
            continue
        data[sym] = d
        if not args.no_derivs:
            fnd = dd.fetch_funding(client, sym, args.days, skip_fetch=args.skip_fetch)
            oi = dd.fetch_open_interest(client, sym, args.days, "1h", skip_fetch=args.skip_fetch)
            derivs[sym] = dd.DerivIndex(fnd, oi, "1h")
        dv = derivs.get(sym)
        print(f"  [{n}/{len(symbols)}] {sym}: 4h={len(d['240'])} 1h={len(d['60'])} "
              f"D={len(d['D'])} 15m={len(d['15'])} ({span_days:.0f}d)"
              + (f" funding={len(dv.f_ts)} oi={len(dv.o_ts)}" if dv else ""))
    if skipped:
        print(f"  Skipped (insufficient history): {', '.join(skipped)}")
    fetch_s = time.time() - t0

    btc_h4 = None
    if "BTCUSDT" in data and len(data["BTCUSDT"]["240"]) >= 60:
        btc_h4 = TrendIndex(sr.compute_indicators(data["BTCUSDT"]["240"]), "240")

    trades = []
    for sym, d in data.items():
        tr = build_trades(sym, d, btc_h4, enabled, tfs, deriv=derivs.get(sym))
        trades.extend(tr)
        print(f"  signals {sym}: {len(tr)}")
    print(f"Total trades: {len(trades)}  (fetch {fetch_s:.0f}s, total {time.time() - t0:.0f}s)")

    # default simulation
    for t in trades:
        t["_res"] = sim_trade(t)
        if t["_res"]:
            t["risk_pct"] = t["_res"]["risk_pct"]
    trades = [t for t in trades if t["_res"]]

    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    L = []
    L.append(f"# Unified backtest — {today}")
    L.append(f"\nUniverse: {len(data)} symbols ({', '.join(data)}); days={args.days}; "
             f"trades={len(trades)}; window 4h→192×15m, 1h→96×15m; entry=market at next 15m open; "
             f"T1={DEFAULT_T1_R}R partial 50%, BE after T1, +0.3R trail after 1R MFE; costs per "
             f"config (taker {config.TAKER_FEE_PCT*100:.3f}% + slip {config.SLIPPAGE_PCT*100:.2f}% per side).")
    L.append(f"\nMetric: **profitable%** = net-of-cost blended R > 0. Bar: SHIP ≥{SHIP_PROFITABLE_PCT}% & net>0 & "
             f"n≥{SHIP_MIN_N} on TEST; CANDIDATE ≥{CANDIDATE_PROFITABLE_PCT}%.")
    if skipped:
        L.append(f"\nSkipped: {', '.join(skipped)}")

    groups = defaultdict(list)
    for t in trades:
        groups[(t["signal"], t["tf"])].append(t)

    L.append("\n## (a) Per signal × tf — default config\n")
    L.append("| signal | tf | tier | ALL | TRAIN (60%) | TEST (40%) |")
    L.append("|---|---|---|---|---|---|")
    ship_rows = []
    per_sig_detail = []
    total_cuts = 0
    for (sig, tf), tr in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        train, test = split_train_test(tr)
        s_all = stats([t["_res"] for t in tr])
        s_tr = stats([t["_res"] for t in train])
        s_te = stats([t["_res"] for t in test])
        tier = sr.SIGNAL_TIER.get(sig, "?")
        L.append(f"| {sig} | {tf} | {tier} | {fmt(s_all)} | {fmt(s_tr)} | {fmt(s_te)} |")

        det = [f"\n### {sig} ({tf})\n", "**Walk-forward by month (default config):**\n", month_table(tr)]

        # (b) filters
        rows, n_cuts = filter_study(train, test)
        total_cuts += n_cuts
        det.append(f"\n**Filter study** ({n_cuts} cuts tested — expect ~{n_cuts*0.05:.1f} false positives at 5%):\n")
        det.append("| filter | bucket | TRAIN | TEST | flag |")
        det.append("|---|---|---|---|---|")
        for r in rows:
            det.append(f"| {r['filter']} | {r['bucket']} | {fmt(r['train'])} | {fmt(r['test'])} | "
                       f"{'CANDIDATE' if r['candidate'] else ''} |")

        # (c) management sweep
        combo, s_mtr, s_mte = mgmt_sweep(train, test)
        det.append("\n**Management sweep** (chosen on TRAIN: max profitable% s.t. net>0; T2 floor 1.5R):\n")
        if combo:
            det.append(f"- chosen: T1={combo[0]}R, stop×{combo[1]}, T2={combo[2]}R, trail={'on' if combo[3] else 'off'}")
            det.append(f"- TRAIN chosen: {fmt(s_mtr)}")
            det.append(f"- TEST chosen: {fmt(s_mte)}")
            det.append(f"- TEST default: {fmt(s_te)}")
        else:
            det.append("- no combo reaches net>0 on train")

        # (d) best filter (selected on TRAIN) + chosen mgmt, reported on TEST
        best_f = None
        for r in rows:
            if r["train"]["n"] >= MIN_TEST_N and (r["train"]["net_exp"] or 0) > 0:
                k = (r["train"]["profitable_pct"], r["train"]["net_exp"])
                if best_f is None or k > best_f[0]:
                    best_f = (k, r)
        best_te = None
        best_desc = "none"
        if best_f:
            r = best_f[1]
            c = combo or (DEFAULT_T1_R, 1.0, None, True)
            best_te = stats([sim_trade(t, *c) for t in r["test_trades"]])
            best_desc = f"{r['filter']}={r['bucket']} + T1={c[0]} stop×{c[1]} T2={c[2] or 'default'} trail={'on' if c[3] else 'off'}"
        verdict_src = best_te if (best_te and best_te["n"]) else s_te
        if verdict_src["n"] >= SHIP_MIN_N and (verdict_src["profitable_pct"] or 0) >= SHIP_PROFITABLE_PCT and (verdict_src["net_exp"] or 0) > 0:
            verdict = "SHIP"
        elif verdict_src["n"] >= MIN_TEST_N and (verdict_src["profitable_pct"] or 0) >= CANDIDATE_PROFITABLE_PCT and (verdict_src["net_exp"] or 0) > 0:
            verdict = "CANDIDATE"
        else:
            verdict = "NO"
        ship_rows.append((sig, tf, s_te, s_mte, best_desc, best_te, verdict))
        per_sig_detail.extend(det)

    L.append(f"\nTotal filter cuts tested across signals: {total_cuts}.")
    L.extend(per_sig_detail)

    # (e) funding-squeeze parameter sweep (positioning candidates)
    fs_names = {"funding_squeeze_short", "funding_squeeze_long"}
    if derivs and (enabled is None or (enabled & fs_names)) and "4h" in tfs:
        L.append("\n## (e) Funding-squeeze parameter sweep (chosen on TRAIN, reported on TEST)\n")
        L.append("Grid: funding_min × oi_min × price_flat × settlement_only. Selection = max profitable% "
                 "s.t. net>0 and n≥30 on TRAIN; every combo's TEST is listed so the landscape is visible "
                 "(the top row is a selected result — treat it as optimistic).\n")
        for sig in sorted(fs_names):
            rows = funding_sweep(data, derivs, btc_h4, sig)
            L.append(f"\n### {sig}\n")
            L.append("| funding_min | oi_min% | flat% | settle | TRAIN | TEST | ALL |")
            L.append("|---|---|---|---|---|---|---|")
            for r in rows[:12]:
                p = r["params"]
                L.append(f"| {p['fs_funding_min']*100:.2f}% | {p['fs_oi_min_pct']} | {p['fs_price_flat_pct']} | "
                         f"{'y' if p['fs_settlement_only'] else 'n'} | {fmt(r['train'])} | {fmt(r['test'])} | {fmt(r['all'])} |")
            if not rows:
                L.append("| (no combo produced ≥30 train trades) | | | | | | |")

    L.append("\n## (d) What would ship (TEST numbers; filter + management selected on TRAIN)\n")
    L.append("| signal | tf | default TEST | mgmt-only TEST | best filter+mgmt | best TEST | verdict |")
    L.append("|---|---|---|---|---|---|---|")
    for sig, tf, s_te, s_mte, desc, best_te, verdict in ship_rows:
        L.append(f"| {sig} | {tf} | {fmt(s_te)} | {fmt(s_mte) if s_mte else 'n/a'} | {desc} | "
                 f"{fmt(best_te) if best_te else 'n/a'} | **{verdict}** |")

    L.append(f"\nRuntime: {time.time() - t0:.0f}s. Config knobs (getattr defaults): UB_DEDUP_DAYS, "
             f"UB_MIN_HISTORY_DAYS, UB_DEFAULT_T1_R, UB_SHIP_PROFITABLE_PCT, UB_CANDIDATE_PROFITABLE_PCT, "
             f"UB_MIN_TEST_N, UB_SHIP_MIN_N.")
    report = "\n".join(L)
    rp = REPORT_DIR / f"unified_{today}.md"
    rp.write_text(report, encoding="utf-8")
    tp = REPORT_DIR / f"unified_{today}_trades.json"
    slim = []
    for t in trades:
        s = {k: v for k, v in t.items() if not k.startswith("_")}
        s["result"] = t["_res"]
        slim.append(s)
    tp.write_text(json.dumps(slim), encoding="utf-8")
    print(report)
    print(f"\nSaved {rp} and {tp}")
    return rp


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--symbols", default="auto")
    ap.add_argument("--max-symbols", type=int, default=30)
    ap.add_argument("--days", type=int, default=180)
    ap.add_argument("--signals", default="")
    ap.add_argument("--tfs", default="4h,1h")
    ap.add_argument("--skip-fetch", action="store_true")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--no-derivs", action="store_true", help="skip funding/OI fetch + positioning features")
    args = ap.parse_args()
    run(args)


if __name__ == "__main__":
    main()
