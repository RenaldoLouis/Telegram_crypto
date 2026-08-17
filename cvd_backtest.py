"""cvd_backtest.py — Order-flow (CVD) hypothesis backtest. Roadmap item #4.

Tests whether taker ORDER FLOW (CVD — cumulative volume delta) carries a
NET-OF-COST predictive edge, using FREE deep history from Binance USD-M futures
kline dumps (data.binance.vision). Those monthly CSVs carry a
`taker_buy_base_volume` column = per-bar taker aggressor delta = exactly the raw
material for CVD, for years back, for free.

WHY BINANCE DATA (not Bybit):
  Bybit has NO free historical trade/CVD feed — its recent-trade REST endpoint
  caps at ~1000 most-recent trades (a few minutes), no time range, no pagination.
  So a real Bybit CVD backtest is impossible today; true Bybit CVD is a weeks-long
  FORWARD-collection job. Before committing those weeks, prove-or-kill the
  hypothesis on Binance's deep history: taker flow across major perp venues is
  highly correlated, so a genuine flow edge would show here too. `fapi.binance.com`
  (REST) is ISP-blocked, but `data.binance.vision` (the static dump host) is NOT —
  we only need the dumps.

DISCIPLINE (CLAUDE.md north star):
  - Optimize NET-of-cost expectancy (config cost model), never win rate / gross R.
  - Prove out-of-sample: chronological TRAIN/TEST split; a feature that flips sign
    on the held-out half is overfit and REJECTED (same bar as the OI-delta and
    S/R experiments).
  - RESEARCH / DATA ONLY — zero trading decisions, no order API. If (and only if)
    a flow signal survives OOS here, Phase 2 = forward-collect real Bybit CVD to
    confirm ON-VENUE, THEN promote into mechanical_setups.py (CORE PRINCIPLE:
    Claude/hosted feeds never decide; the edge lives in owned Python).

Usage:
  source venv/bin/activate
  python cvd_backtest.py --interval 4h --months 8            # H1 flow-filter test
  python cvd_backtest.py --interval 4h --months 8 --divergence  # + H2 standalone
  python cvd_backtest.py --interval 1h --months 4 --symbols BTCUSDT,ETHUSDT,SOLUSDT
  python cvd_backtest.py --no-cache                          # force re-download
"""
import argparse
import io
import json
import sys
import zipfile
from datetime import date
from pathlib import Path

import pandas as pd
import requests

import config
from historical_backtester import (
    compute_indicators_df,
    evaluate_forward,
    compute_stats,
    signal_trend_pullback_long,
    signal_trend_pullback_short,
    signal_rsi_rejection_short,
    make_liquidity_sweep,
    EXPANDED_SYMBOLS,
)

BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR / "logs" / "cvd_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

BINANCE_DUMP = ("https://data.binance.vision/data/futures/um/monthly/klines"
                "/{sym}/{itv}/{sym}-{itv}-{yr:04d}-{mo:02d}.zip")

INTERVAL_MIN = {"1h": 60, "2h": 120, "4h": 240, "1d": 1440}

# Binance USD-M futures kline CSV columns (12). Index 9 = taker buy base volume.
COLS = ["open_time", "open", "high", "low", "close", "volume", "close_time",
        "quote_volume", "count", "taker_buy_base", "taker_buy_quote", "ignore"]


# ─── Data layer: Binance monthly kline dumps (free, deep history) ─────────────

def _months_back(n, end=None):
    """Yield (year, month) for the n complete months ending BEFORE the current
    month (avoid a partial in-progress month). Deterministic, no wall-clock in
    the result — the current month is excluded so reruns are stable mid-month."""
    end = end or date.today()
    y, m = end.year, end.month
    # step back to last COMPLETE month
    m -= 1
    if m == 0:
        y, m = y - 1, 12
    out = []
    for _ in range(n):
        out.append((y, m))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return list(reversed(out))


def _fetch_month(sym, itv, yr, mo, use_cache=True):
    """Download + parse ONE monthly dump. Returns list of row-lists or [] if the
    file doesn't exist (early months for a young symbol 404 — that's fine)."""
    cache = CACHE_DIR / f"{sym}_{itv}_{yr:04d}-{mo:02d}.json"
    if use_cache and cache.exists():
        return json.loads(cache.read_text())

    url = BINANCE_DUMP.format(sym=sym, itv=itv, yr=yr, mo=mo)
    try:
        r = requests.get(url, timeout=30)
    except Exception as e:
        print(f"    ! {sym} {yr}-{mo:02d} fetch error: {type(e).__name__}: {e}")
        return []
    if r.status_code == 404:
        cache.write_text("[]")  # remember the gap so we don't re-hit it
        return []
    if r.status_code != 200:
        print(f"    ! {sym} {yr}-{mo:02d} HTTP {r.status_code}")
        return []

    try:
        zf = zipfile.ZipFile(io.BytesIO(r.content))
        raw = zf.read(zf.namelist()[0]).decode("utf-8", "replace")
    except Exception as e:
        print(f"    ! {sym} {yr}-{mo:02d} unzip error: {type(e).__name__}: {e}")
        return []

    rows = []
    for line in raw.splitlines():
        parts = line.split(",")
        if len(parts) < 11:
            continue
        # Some newer dumps carry a header row — skip anything non-numeric.
        try:
            ot = int(float(parts[0]))
        except ValueError:
            continue
        rows.append(parts)
    cache.write_text(json.dumps(rows))
    return rows


def load_symbol(sym, itv, months, use_cache=True):
    """Assemble a full indicator DataFrame for one symbol, with CVD columns
    attached. Returns None if too little data."""
    allrows = []
    for (yr, mo) in _months_back(months):
        allrows.extend(_fetch_month(sym, itv, yr, mo, use_cache))
    if len(allrows) < 120:
        return None

    # dedupe + sort by open_time (dumps are already ordered, but be safe)
    seen, rows = set(), []
    for p in sorted(allrows, key=lambda x: int(float(x[0]))):
        ot = int(float(p[0]))
        if ot in seen:
            continue
        seen.add(ot)
        rows.append(p)

    # candles for compute_indicators_df: [ts, o, h, l, c, volume, turnover]
    candles = [[int(float(p[0])), float(p[1]), float(p[2]), float(p[3]),
                float(p[4]), float(p[5]), float(p[7])] for p in rows]
    df = compute_indicators_df(candles)

    # attach CVD raw columns (same order as candles)
    df["volume_base"] = [float(p[5]) for p in rows]
    df["quote_volume"] = [float(p[7]) for p in rows]
    df["taker_buy_base"] = [float(p[9]) for p in rows]
    df["taker_buy_quote"] = [float(p[10]) for p in rows]

    # per-bar net taker flow in QUOTE terms (scale-comparable across symbols)
    df["delta_quote"] = 2.0 * df["taker_buy_quote"] - df["quote_volume"]
    # per-bar taker-buy share (0..1, 0.5 = balanced)
    df["taker_ratio"] = (df["taker_buy_base"] / df["volume_base"]).clip(0, 1)
    # running CVD (for divergence)
    df["cvd"] = df["delta_quote"].cumsum()
    return df


# ─── Flow features (no lookahead: all reference bars <= i) ────────────────────

def add_flow_window(df, k):
    """K-bar taker-buy share ending at each bar. >0.5 = net buying pressure over
    the window. Uses only past+current bars (rolling, right-aligned)."""
    tb = df["taker_buy_quote"].rolling(k).sum()
    qv = df["quote_volume"].rolling(k).sum()
    df[f"flow_ratio_{k}"] = (tb / qv).clip(0, 1)
    return f"flow_ratio_{k}"


def add_deep_flow(df, k=6):
    """Richer, no-lookahead flow constructs (all rolling right-aligned):
      flow_z    — current bar's net taker delta in std units (extremity)
      cvd_slope — normalized net flow momentum over k bars (signed)
      body_atr  — bar's close-open move in ATR units (price response)
    Absorption = large |flow_z| whose SIGN disagrees with body_atr (heavy taker
    pressure one way, price refuses to follow -> the other side is absorbing)."""
    dq = df["delta_quote"]
    std = dq.rolling(50).std()
    df["flow_z"] = dq / std.replace(0, float("nan"))
    denom = dq.abs().rolling(20).mean() * k
    df["cvd_slope"] = (df["cvd"] - df["cvd"].shift(k)) / denom.replace(0, float("nan"))
    df["body_atr"] = (df["close"] - df["open"]) / df["atr_14"].replace(0, float("nan"))
    return df


def absorption_trades(df, symbol, z_thr, target_r, eval_window, cooldown,
                      body_max=0.25):
    """Standalone absorption-reversal signal.
      Bullish: heavy taker SELLING (flow_z <= -z_thr) but price did NOT drop
               (body_atr >= -body_max)  -> bids absorbed the sell -> LONG.
      Bearish: heavy taker BUYING (flow_z >= +z_thr) but price did NOT rise
               (body_atr <= +body_max)  -> offers absorbed the buy -> SHORT.
    Stop beyond the absorbing bar's extreme + 0.5 ATR; entry at its close."""
    trades, last = [], -cooldown - 1
    z = df["flow_z"].values
    body = df["body_atr"].values
    close = df["close"].values
    hi, lo = df["high"].values, df["low"].values
    atr = df["atr_14"].values
    for i in range(50, len(df) - eval_window):
        if i - last < cooldown:
            continue
        if pd.isna(z[i]) or pd.isna(body[i]) or pd.isna(atr[i]) or atr[i] <= 0:
            continue
        sig = None
        if z[i] <= -z_thr and body[i] >= -body_max:      # bullish absorption
            entry = close[i]
            stop = lo[i] - 0.5 * atr[i]
            risk = entry - stop
            if risk > 0:
                sig = {"direction": "long", "entry": entry, "stop": stop, "risk": risk}
        elif z[i] >= z_thr and body[i] <= body_max:      # bearish absorption
            entry = close[i]
            stop = hi[i] + 0.5 * atr[i]
            risk = stop - entry
            if risk > 0:
                sig = {"direction": "short", "entry": entry, "stop": stop, "risk": risk}
        if sig is None:
            continue
        res = evaluate_forward(df, i, sig, target_r, eval_window)
        if res is None:
            continue
        last = i
        trades.append({
            **res, "signal": "absorption", "symbol": symbol,
            "direction": sig["direction"], "entry_price": sig["entry"],
            "risk": sig["risk"], "flow_z": float(z[i]),
            "ts": int(df.iloc[i]["timestamp"]),
        })
    return trades


# ─── Net-of-cost (replicates weekly_eval.trade_cost_rr / config cost model) ───

def cost_rr(entry, risk, candles_to_exit, interval_min):
    if not config.COST_MODEL_ENABLED:
        return 0.0
    rp = (risk / entry) if entry else 0.0
    if rp <= 0:
        return 0.0
    roundtrip = 2 * (config.TAKER_FEE_PCT + config.SLIPPAGE_PCT)
    hold_h = max(candles_to_exit, 1) * interval_min / 60.0
    funding = config.FUNDING_PCT_PER_8H * (hold_h / 8.0)
    return (roundtrip + funding) / rp


def net_stats(trades, interval_min):
    """compute_stats on NET-of-cost R (actual_rr - cost_rr per trade)."""
    net = []
    for t in trades:
        c = cost_rr(t["entry_price"], t["risk"], t.get("candles", 1), interval_min)
        net.append({**t, "actual_rr": round(t["actual_rr"] - c, 3)})
    return compute_stats(net)


# ─── H1: does taker flow FILTER existing signals into a better net subset? ────

BASE_SIGNALS = {
    "trend_pullback_long": signal_trend_pullback_long,
    "trend_pullback_short": signal_trend_pullback_short,
    "rsi_rejection_short": signal_rsi_rejection_short,
    "liquidity_sweep_long": make_liquidity_sweep("long"),
}


def collect_signal_trades(df, symbol, sig_name, sig_fn, flow_col, target_r,
                          eval_window, cooldown):
    """Run a base signal across df, tag each trade with the flow_ratio at entry."""
    trades = []
    last = -cooldown - 1
    n = len(df)
    for i in range(50, n - eval_window):
        if i - last < cooldown:
            continue
        sig = sig_fn(df, i)
        if sig is None:
            continue
        last = i
        res = evaluate_forward(df, i, sig, target_r, eval_window)
        if res is None:
            continue
        fr = df.iloc[i][flow_col]
        if pd.isna(fr):
            continue
        trades.append({
            **res, "signal": sig_name, "symbol": symbol,
            "direction": sig["direction"], "entry_price": sig["entry"],
            "risk": sig["risk"], "flow_ratio": float(fr),
            "ts": int(df.iloc[i]["timestamp"]),
        })
    return trades


def bucket_by_flow(trades, thr):
    """Split trades into flow-CONFIRM / flow-CONTRA / neutral relative to their
    direction. Long confirm = buyers dominant (ratio>=0.5+thr); short confirm =
    sellers dominant (ratio<=0.5-thr)."""
    conf, contra, neu = [], [], []
    for t in trades:
        fr, d = t["flow_ratio"], t["direction"]
        buy_dom = fr >= 0.5 + thr
        sell_dom = fr <= 0.5 - thr
        if (d == "long" and buy_dom) or (d == "short" and sell_dom):
            conf.append(t)
        elif (d == "long" and sell_dom) or (d == "short" and buy_dom):
            contra.append(t)
        else:
            neu.append(t)
    return conf, contra, neu


# ─── H2: CVD divergence as a STANDALONE reversal signal ───────────────────────

def _pivots(df, order=3):
    """Confirmed pivot-high / pivot-low indices (needs `order` bars each side, so
    a pivot at j is only knowable at bar j+order — callers must gate on that)."""
    highs, lows = [], []
    h, l = df["high"].values, df["low"].values
    n = len(df)
    for j in range(order, n - order):
        seg_h = h[j - order:j + order + 1]
        seg_l = l[j - order:j + order + 1]
        if h[j] == seg_h.max() and (seg_h == h[j]).sum() == 1:
            highs.append(j)
        if l[j] == seg_l.min() and (seg_l == l[j]).sum() == 1:
            lows.append(j)
    return highs, lows


def divergence_trades(df, symbol, target_r, eval_window, cooldown, order=3):
    """Regular divergence between price and CVD, entered on the confirmation bar.
    Bearish: price higher-high but CVD lower-high -> short. Bullish: price
    lower-low but CVD higher-low -> long. No lookahead: pivot p is used only at
    bar i = p + order (its first knowable bar)."""
    highs, lows = _pivots(df, order)
    cvd = df["cvd"].values
    hi, lo = df["high"].values, df["low"].values
    atr = df["atr_14"].values
    close = df["close"].values
    trades, last = [], -cooldown - 1

    # index pivots by confirmation bar for quick lookup
    conf_high = {p + order: p for p in highs}
    conf_low = {p + order: p for p in lows}
    prev_high = [p for p in highs]
    prev_low = [p for p in lows]

    def last_two(lst, i):
        got = [p for p in lst if p + order <= i]
        return got[-2:] if len(got) >= 2 else None

    for i in range(50, len(df) - eval_window):
        if i - last < cooldown:
            continue
        r = df.iloc[i]
        if pd.isna(r["atr_14"]) or r["atr_14"] <= 0:
            continue
        sig = None
        # Bearish divergence -> short, only fire on a fresh high confirmation
        if i in conf_high:
            pair = last_two(prev_high, i)
            if pair:
                p1, p2 = pair
                if hi[p2] > hi[p1] and cvd[p2] < cvd[p1]:
                    entry = close[i]
                    stop = max(hi[p2], hi[i]) + 0.5 * atr[i]
                    risk = stop - entry
                    if risk > 0:
                        sig = {"direction": "short", "entry": entry,
                               "stop": stop, "risk": risk}
        # Bullish divergence -> long
        if sig is None and i in conf_low:
            pair = last_two(prev_low, i)
            if pair:
                p1, p2 = pair
                if lo[p2] < lo[p1] and cvd[p2] > cvd[p1]:
                    entry = close[i]
                    stop = min(lo[p2], lo[i]) - 0.5 * atr[i]
                    risk = entry - stop
                    if risk > 0:
                        sig = {"direction": "long", "entry": entry,
                               "stop": stop, "risk": risk}
        if sig is None:
            continue
        res = evaluate_forward(df, i, sig, target_r, eval_window)
        if res is None:
            continue
        last = i
        trades.append({
            **res, "signal": "cvd_divergence", "symbol": symbol,
            "direction": sig["direction"], "entry_price": sig["entry"],
            "risk": sig["risk"], "ts": int(df.iloc[i]["timestamp"]),
        })
    return trades


# ─── Reporting ────────────────────────────────────────────────────────────────

def _split(trades, ratio=0.6):
    """Chronological train/test split by entry timestamp."""
    s = sorted(trades, key=lambda t: t["ts"])
    cut = int(len(s) * ratio)
    return s[:cut], s[cut:]


ROW = "    {:<26s} {:>4d} | net {:>7.3f} | wr {:>5.1f}% | gross {:>7.3f}"


def _line(label, trades, itv_min):
    if not trades:
        print(f"    {label:<26s}   (0 trades)")
        return
    n = net_stats(trades, itv_min)
    g = compute_stats(trades)
    print(ROW.format(label, n["n"], n["expectancy"], n["wr"], g["expectancy"]))


def report_filter(all_trades, itv_min, thr):
    print("\n" + "=" * 78)
    print(f"  H1 — TAKER-FLOW FILTER on existing signals  (thr=±{thr:.0%}, "
          f"net-of-cost)")
    print("=" * 78)
    by_sig = {}
    for t in all_trades:
        by_sig.setdefault(t["signal"], []).append(t)
    for sig, trades in sorted(by_sig.items()):
        conf, contra, neu = bucket_by_flow(trades, thr)
        print(f"\n  {sig}   (n={len(trades)})")
        _line("ALL (baseline)", trades, itv_min)
        _line("flow-CONFIRM", conf, itv_min)
        _line("flow-CONTRA", contra, itv_min)
        # OOS check on the confirm bucket vs baseline
        tr_b, te_b = _split(trades)
        tr_c, te_c = _split(conf)
        if te_b and te_c:
            nb = net_stats(te_b, itv_min)["expectancy"]
            nc = net_stats(te_c, itv_min)["expectancy"]
            verdict = "HOLDS OOS" if nc > nb and nc >= 0 else (
                "improves but still net-neg" if nc > nb else "NO — worse OOS")
            print(f"    -> TEST net: baseline {nb:+.3f} vs confirm {nc:+.3f}  "
                  f"[{verdict}]")


def report_divergence(all_trades, itv_min):
    print("\n" + "=" * 78)
    print("  H2 — CVD DIVERGENCE standalone signal  (net-of-cost, TRAIN/TEST)")
    print("=" * 78)
    if not all_trades:
        print("    (no divergence signals fired)")
        return
    for d in ("long", "short", None):
        sub = [t for t in all_trades if d is None or t["direction"] == d]
        label = d or "both"
        tr, te = _split(sub)
        print(f"\n  direction={label}  (n={len(sub)})")
        _line("ALL", sub, itv_min)
        _line("TRAIN (60%)", tr, itv_min)
        _line("TEST  (40%)", te, itv_min)


def bucket_by_slope(trades, thr):
    """0-centered bucketer for cvd_slope-tagged trades (stored under 'flow_ratio').
    Confirm = flow momentum aligned with trade direction."""
    conf, contra = [], []
    for t in trades:
        s, d = t["flow_ratio"], t["direction"]
        if (d == "long" and s >= thr) or (d == "short" and s <= -thr):
            conf.append(t)
        elif (d == "long" and s <= -thr) or (d == "short" and s >= thr):
            contra.append(t)
    return conf, contra


def report_absorption(trades, itv_min):
    print("\n" + "=" * 78)
    print("  DEEP-A — ABSORPTION reversal, z-threshold SWEEP  (net-of-cost)")
    print("  Robust edge => positive AND OOS-stable AND stronger at higher z.")
    print("=" * 78)
    if not trades:
        print("    (no absorption signals — check thresholds)")
        return
    # trades were collected at the lowest z; re-bucket by |flow_z| stored per trade
    for z in (1.0, 1.5, 2.0, 2.5, 3.0):
        sub = [t for t in trades if abs(t["flow_z"]) >= z]
        tr, te = _split(sub)
        n = net_stats(sub, itv_min) if sub else None
        if not sub:
            print(f"\n  z>={z}: (0 trades)")
            continue
        ntr = net_stats(tr, itv_min)["expectancy"] if tr else float("nan")
        nte = net_stats(te, itv_min)["expectancy"] if te else float("nan")
        print(f"\n  z>={z}  n={n['n']}  net={n['expectancy']:+.3f}  wr={n['wr']:.1f}%"
              f"  | TRAIN {ntr:+.3f}  TEST {nte:+.3f}")


def report_slope_filter(all_trades, itv_min, thr):
    print("\n" + "=" * 78)
    print(f"  DEEP-B — CVD-SLOPE (flow momentum) FILTER on shorts  (thr=±{thr}, "
          f"net-of-cost)")
    print("=" * 78)
    by_sig = {}
    for t in all_trades:
        by_sig.setdefault(t["signal"], []).append(t)
    for sig, trades in sorted(by_sig.items()):
        conf, contra = bucket_by_slope(trades, thr)
        print(f"\n  {sig}   (n={len(trades)})")
        _line("ALL (baseline)", trades, itv_min)
        _line("slope-CONFIRM", conf, itv_min)
        _line("slope-CONTRA", contra, itv_min)
        tr_b, te_b = _split(trades)
        tr_c, te_c = _split(conf)
        if te_b and te_c:
            nb = net_stats(te_b, itv_min)["expectancy"]
            nc = net_stats(te_c, itv_min)["expectancy"]
            v = "HOLDS OOS" if nc > nb and nc >= 0 else (
                "improves, still net-neg" if nc > nb else "NO — worse OOS")
            print(f"    -> TEST net: baseline {nb:+.3f} vs confirm {nc:+.3f}  [{v}]")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", default="4h", choices=list(INTERVAL_MIN))
    ap.add_argument("--months", type=int, default=8)
    ap.add_argument("--symbols", default=None,
                    help="comma list; default = the 15-symbol validation universe")
    ap.add_argument("--target-r", type=float, default=1.5)
    ap.add_argument("--eval-window", type=int, default=48)
    ap.add_argument("--cooldown", type=int, default=6)
    ap.add_argument("--flow-k", type=int, default=6, help="flow window (bars)")
    ap.add_argument("--flow-thr", type=float, default=0.02,
                    help="taker-share threshold above/below 0.5 for confirm/contra")
    ap.add_argument("--divergence", action="store_true", help="also run H2")
    ap.add_argument("--deep", action="store_true",
                    help="run deeper flow constructs (absorption + CVD-slope)")
    ap.add_argument("--slope-thr", type=float, default=0.15,
                    help="cvd_slope threshold for the momentum filter")
    ap.add_argument("--no-cache", action="store_true")
    args = ap.parse_args()

    itv = args.interval
    itv_min = INTERVAL_MIN[itv]
    symbols = (args.symbols.split(",") if args.symbols else EXPANDED_SYMBOLS)
    use_cache = not args.no_cache

    print(f"\nCVD backtest — {itv}, {args.months} months, {len(symbols)} symbols, "
          f"target {args.target_r}R  (source: data.binance.vision)")
    print("Loading data (Binance USD-M dumps; cached under logs/cvd_cache)...")

    filt_trades, div_trades, abs_trades, slope_trades = [], [], [], []
    loaded = 0
    for sym in symbols:
        df = load_symbol(sym, itv, args.months, use_cache)
        if df is None or len(df) < 120:
            print(f"  - {sym}: insufficient data, skipped")
            continue
        loaded += 1
        flow_col = add_flow_window(df, args.flow_k)
        for sname, sfn in BASE_SIGNALS.items():
            filt_trades += collect_signal_trades(
                df, sym, sname, sfn, flow_col, args.target_r,
                args.eval_window, args.cooldown)
        if args.divergence:
            div_trades += divergence_trades(
                df, sym, args.target_r, args.eval_window, args.cooldown)
        if args.deep:
            add_deep_flow(df, args.flow_k)
            abs_trades += absorption_trades(
                df, sym, 1.0, args.target_r, args.eval_window, args.cooldown)
            for sname in ("trend_pullback_short", "rsi_rejection_short"):
                slope_trades += collect_signal_trades(
                    df, sym, sname, BASE_SIGNALS[sname], "cvd_slope",
                    args.target_r, args.eval_window, args.cooldown)
        print(f"  + {sym}: {len(df)} bars")

    if not loaded:
        print("\nNo data loaded — is data.binance.vision reachable? "
              "(REST fapi is ISP-blocked; the dump host should NOT be)")
        sys.exit(1)

    print(f"\nLoaded {loaded}/{len(symbols)} symbols. "
          f"Filter trades: {len(filt_trades)}  Divergence trades: {len(div_trades)}")
    report_filter(filt_trades, itv_min, args.flow_thr)
    if args.divergence:
        report_divergence(div_trades, itv_min)
    if args.deep:
        report_absorption(abs_trades, itv_min)
        report_slope_filter(slope_trades, itv_min, args.slope_thr)

    print("\nReminder: NET-of-cost is the verdict metric. A bucket that beats "
          "baseline only on TRAIN (flips on TEST) is overfit — reject it.\n")


if __name__ == "__main__":
    main()
