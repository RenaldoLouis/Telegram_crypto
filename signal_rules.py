"""Shared signal detection — ONE implementation for live scan and backtest.

`detect_at(df, i, tf_label)` evaluates every validated/watch signal rule on the bar at
index `i` of an indicator-enriched DataFrame. The live scan calls it with `i` = the
LAST CLOSED bar; the unified backtester walks every closed bar. Because the two share
this function, the live signal population is by construction the population that was
backtested (the 2026-09-23 audit found the old live detector evaluated the still-OPEN
4h bar, which the backtester never saw).

Rules and parameters are the ones that were live in `bybit_data._check_validated_signals`
as of 2026-09-10; nothing was re-tuned here. `signal_tiers` / `SIGNAL_TIER` decide
whether a rule ships as EXECUTE or WATCH and are meant to be updated from
`unified_backtest.py` results.
"""

import pandas as pd

import config

# tier per signal — "execute" = surfaced as a counted suggestion once it passes the
# structural gates; "watch" = surfaced only under the WATCH label, paper-tracked.
SIGNAL_TIER = {
    # 2026-09-23 unified backtest (30 symbols, 180 days, exact live trade model, TEST = last 40%):
    # NOTHING reached the SHIP bar (>=70% profitable net, net exp > 0, n>=30 on test). Every
    # former EXECUTE signal is net-negative out of sample under the real trade. So the whole
    # set runs as WATCH (gated, paper-tracked, forward-scored by eval engine v2) until a rule
    # clears the bar on FORWARD data (head_to_head "promotion" table). Test numbers:
    "range_reversion_short": "watch",   # vol_spike>=1.5 gate baked in: test n=41 65.9% / -0.04R; all-period n=101 75% / +0.19R
    "range_reversion_long": "watch",    # test n=11 73% / -0.04R (too thin)
    "failed_breakout_short": "watch",   # test n=112 54.5% / -0.12R
    "trend_pullback_short": "watch",    # test n=152 52.6% / -0.18R
    "liquidity_sweep_long": "watch",    # 1h test n=341 51% / -0.25R (4h 44% -> disabled)
    "rsi_bounce_long": "watch",         # test n=96 51% / -0.09R
    "rsi_rejection_short": "watch",     # test n=85 39% / -0.23R -> DISABLED (no TF)
    # Positioning candidates (added 2026-09-23, item 2 of the research plan): fade a crowded
    # side at funding settlement when open interest has been building and price has stalled.
    # Need funding/OI columns on the df (derivs_data.attach_to_df); silently inert without them.
    "funding_squeeze_short": "watch",
    "funding_squeeze_long": "watch",
}

# Timeframes each rule is allowed to fire on (empty tuple = disabled, kept for the harness).
SIGNAL_TFS = {
    "trend_pullback_short": ("4h",),
    "failed_breakout_short": ("4h",),
    "liquidity_sweep_long": ("1h",),    # 4h variant disabled 2026-09-23 (44% test, -0.38R)
    "rsi_bounce_long": ("4h",),
    "range_reversion_short": ("4h",),
    "range_reversion_long": ("4h",),
    "rsi_rejection_short": (),          # disabled 2026-09-23 (39% test)
    "funding_squeeze_short": ("4h",),   # settlement bars are 4h closes (00/08/16 UTC)
    "funding_squeeze_long": ("4h",),
}

# Defaults for the funding-squeeze rules (overridable per call via detect_at(params=...),
# which is how unified_backtest.py sweeps them; live uses config/getattr values).
FS_DEFAULTS = {
    "fs_funding_min": getattr(config, "FS_FUNDING_MIN", 0.0003),     # 0.03% per 8h = crowded
    "fs_oi_min_pct": getattr(config, "FS_OI_MIN_PCT", 3.0),          # OI up >= 3% over 24h
    "fs_price_flat_pct": getattr(config, "FS_PRICE_FLAT_PCT", 3.0),  # |24h price change| <= 3%
    "fs_settlement_only": getattr(config, "FS_SETTLEMENT_ONLY", True),
    "fs_stop_atr": getattr(config, "FS_STOP_ATR", 1.5),
    "fs_target_r": getattr(config, "FS_TARGET_R", 1.5),
}

ALL_SIGNALS = tuple(SIGNAL_TIER)


def compute_indicators(candles_or_df):
    """Indicator set the rules need. Accepts raw Bybit kline rows
    [ts, open, high, low, close, volume, turnover] (oldest first) or a DataFrame
    with those columns. Returns a new DataFrame with indicator columns added."""
    if isinstance(candles_or_df, pd.DataFrame):
        df = candles_or_df.copy()
    else:
        df = pd.DataFrame(
            candles_or_df,
            columns=["timestamp", "open", "high", "low", "close", "volume", "turnover"],
        )
    df[["open", "high", "low", "close", "volume"]] = df[
        ["open", "high", "low", "close", "volume"]
    ].astype(float)
    df["timestamp"] = df["timestamp"].astype("int64")

    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss
    df["rsi"] = 100 - (100 / (1 + rs))
    df["ema20"] = df["close"].ewm(span=20, adjust=False).mean()
    df["ema50"] = df["close"].ewm(span=50, adjust=False).mean()
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - df["close"].shift()).abs(),
        (df["low"] - df["close"].shift()).abs(),
    ], axis=1).max(axis=1)
    df["atr"] = tr.rolling(14).mean()
    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["macd_sig"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_sig"]
    plus_dm = df["high"].diff()
    minus_dm = -df["low"].diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
    atr_w = tr.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean() / atr_w
    minus_di = 100 * minus_dm.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean() / atr_w
    di_sum = (plus_di + minus_di).replace(0, float("nan"))
    dx = 100 * (plus_di - minus_di).abs() / di_sum
    df["adx"] = dx.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    # Rolling structure (INCLUDING the current bar, mirrors the historical backtester).
    df["high_20"] = df["high"].rolling(20).max()
    df["low_20"] = df["low"].rolling(20).min()
    df["vol_avg_20"] = df["volume"].rolling(20).mean()
    df["vol_spike"] = df["volume"] / df["vol_avg_20"]
    return df


def _ok(c):
    return all(pd.notna(c[col]) for col in ("rsi", "ema20", "ema50", "atr", "adx", "macd_hist")) \
        and c["atr"] > 0


def detect_at(df, i, tf_label, enabled=None, params=None):
    """Evaluate all rules on bar `i` (0-based, must be a CLOSED bar) of an
    indicator-enriched df. Returns a list of signal dicts:
      signal, tf, direction, target_r, stop_atr, [stop_price], tier, indicators.
    `enabled` optionally restricts which signal names may fire. `params` overrides
    FS_DEFAULTS for the funding-squeeze rules (harness sweeps).
    """
    prm = dict(FS_DEFAULTS)
    if params:
        prm.update(params)
    if i < 21 or i >= len(df):
        return []
    c = df.iloc[i]
    p = df.iloc[i - 1]
    p2 = df.iloc[i - 2]
    if not _ok(c):
        return []

    def allowed(name):
        return (enabled is None or name in enabled) and tf_label in SIGNAL_TFS.get(name, ())

    out = []
    close = float(c["close"])
    atr = float(c["atr"])

    # --- Liquidity Sweep Long (1h + 4h) ---
    if allowed("liquidity_sweep_long"):
        prior_low = float(df["low"].iloc[i - 20:i].min())
        rng = float(c["high"]) - float(c["low"])
        pierce = prior_low - float(c["low"])
        lower_wick = min(float(c["open"]), close) - float(c["low"])
        if (rng > 0 and pierce >= 0.15 * atr and close > prior_low
                and lower_wick >= 0.5 * rng and c["rsi"] < 50):
            stop_price = float(c["low"]) - 0.25 * atr
            risk = close - stop_price
            if risk > 0:
                out.append({
                    "signal": "liquidity_sweep_long", "tf": tf_label, "direction": "long",
                    "target_r": 2.0, "stop_atr": round(risk / atr, 2),
                    "stop_price": round(stop_price, 8),
                    "tier": SIGNAL_TIER["liquidity_sweep_long"],
                    "indicators": f"swept {prior_low:.4f} low, RSI {c['rsi']:.1f}, ADX {c['adx']:.1f}",
                })

    # --- Trend Pullback Short (4h) ---
    if (allowed("trend_pullback_short") and c["ema20"] < c["ema50"] and c["adx"] > 15
            and 50 <= c["rsi"] <= 70 and close < float(c["ema50"])
            and abs(close - float(c["ema20"])) < 0.7 * atr and c["macd"] < 0):
        out.append({
            "signal": "trend_pullback_short", "tf": tf_label, "direction": "short",
            "target_r": 2.0, "stop_atr": 1.5,
            "tier": SIGNAL_TIER["trend_pullback_short"],
            "indicators": f"EMA20<EMA50, RSI {c['rsi']:.1f}, ADX {c['adx']:.1f}, near EMA20",
        })

    # --- Failed Breakout Short (4h) ---
    if allowed("failed_breakout_short"):
        prior_high = float(df["high"].iloc[i - 20:i].max())
        if (float(c["high"]) > prior_high and close < prior_high
                and close < float(c["open"]) and c["rsi"] > 45):
            stop_price = float(c["high"]) + 0.25 * atr
            risk = stop_price - close
            if risk > 0:
                out.append({
                    "signal": "failed_breakout_short", "tf": tf_label, "direction": "short",
                    "target_r": 2.0, "stop_atr": round(risk / atr, 2),
                    "stop_price": round(stop_price, 8),
                    "tier": SIGNAL_TIER["failed_breakout_short"],
                    "indicators": f"failed breakout of {prior_high:.4f}, RSI {c['rsi']:.1f}",
                })

    # --- RSI Bounce Long (4h, watch) ---
    if (allowed("rsi_bounce_long") and pd.notna(p["rsi"]) and pd.notna(p2["rsi"])
            and p2["rsi"] < 30 and p["rsi"] < 35 and 30 < c["rsi"] < 45 and c["rsi"] > p["rsi"]):
        out.append({
            "signal": "rsi_bounce_long", "tf": tf_label, "direction": "long",
            "target_r": 2.0, "stop_atr": 2.0, "tier": SIGNAL_TIER["rsi_bounce_long"],
            "indicators": f"RSI {c['rsi']:.1f} bouncing (was {p2['rsi']:.1f}), ADX {c['adx']:.1f}",
        })

    # --- Range Reversion Short / Long (4h, watch) ---
    if allowed("range_reversion_short") or allowed("range_reversion_long"):
        high_20 = float(df["high"].iloc[i - 19:i + 1].max())
        low_20 = float(df["low"].iloc[i - 19:i + 1].min())
        range_pct = (high_20 - low_20) / close * 100 if close > 0 else 0.0
        # Volume gate (2026-09-23 unified backtest): the only filter of 188 tested with a large
        # effect AND train/test agreement (bucket view: test 81%/+0.23R with vs 50%/-0.35R
        # without). Re-run with the gate INSIDE the rule (what runs live): all-period n=101
        # 75% / +0.19R, train 82% / +0.34R, test n=41 65.9% / -0.04R. Candidate, not proven.
        # None = no gate (harness baseline).
        min_vs = getattr(config, "RANGE_REVERSION_SHORT_MIN_VOL_SPIKE", 1.5)
        vs_ok = (min_vs is None) or (pd.notna(c["vol_spike"]) and c["vol_spike"] >= min_vs)
        if (allowed("range_reversion_short") and vs_ok and c["adx"] < 25 and c["rsi"] > 70
                and range_pct >= 5.0 and close >= high_20 * 0.99):
            stop_price = high_20 + 0.7 * atr
            risk = stop_price - close
            if risk > 0:
                out.append({
                    "signal": "range_reversion_short", "tf": tf_label, "direction": "short",
                    "target_r": 1.5, "stop_atr": round(risk / atr, 2),
                    "stop_price": round(stop_price, 8),
                    "tier": SIGNAL_TIER["range_reversion_short"],
                    "indicators": f"range top {high_20:.4f} ({range_pct:.1f}% range), RSI {c['rsi']:.1f}, ADX {c['adx']:.1f}",
                })
        if (allowed("range_reversion_long") and c["adx"] < 18 and c["rsi"] < 30
                and range_pct >= 4.0 and close <= low_20 * 1.015):
            stop_price = low_20 - 0.3 * atr
            risk = close - stop_price
            if risk > 0:
                out.append({
                    "signal": "range_reversion_long", "tf": tf_label, "direction": "long",
                    "target_r": 1.5, "stop_atr": round(risk / atr, 2),
                    "stop_price": round(stop_price, 8),
                    "tier": SIGNAL_TIER["range_reversion_long"],
                    "indicators": f"range bottom {low_20:.4f} ({range_pct:.1f}% range), RSI {c['rsi']:.1f}, ADX {c['adx']:.1f}",
                })

    # --- RSI Rejection Short (4h, watch) ---
    # RSI was overbought (>70) two bars ago, still >65 last bar, now 55-70 and falling —
    # fade the exhaustion. Same rule as historical_backtester.signal_rsi_rejection_short.
    if (allowed("rsi_rejection_short") and pd.notna(p["rsi"]) and pd.notna(p2["rsi"])
            and p2["rsi"] > 70 and p["rsi"] > 65 and 55 < c["rsi"] < 70 and c["rsi"] < p["rsi"]):
        out.append({
            "signal": "rsi_rejection_short", "tf": tf_label, "direction": "short",
            "target_r": 2.0, "stop_atr": 2.0, "tier": SIGNAL_TIER["rsi_rejection_short"],
            "indicators": f"RSI {c['rsi']:.1f} rolling over (was {p2['rsi']:.1f}), ADX {c['adx']:.1f}",
        })

    # --- Funding Squeeze Short / Long (4h, watch; positioning fade) ---
    # Crowded side pays extreme funding + OI has been building + price stalled → the
    # crowd is trapped; fade it at settlement. Columns come from derivs_data.attach_to_df.
    if (allowed("funding_squeeze_short") or allowed("funding_squeeze_long")) and "funding_rate" in df.columns:
        fr = c["funding_rate"]
        oi_chg = c["oi_chg_24h_pct"]
        p_chg = c["price_chg_24h_pct"]
        settle_ok = (not prm["fs_settlement_only"]) or bool(c.get("settlement_close", False))
        if (pd.notna(fr) and pd.notna(oi_chg) and pd.notna(p_chg) and settle_ok
                and oi_chg >= prm["fs_oi_min_pct"] and abs(p_chg) <= prm["fs_price_flat_pct"]):
            base = {"tf": tf_label, "target_r": prm["fs_target_r"], "stop_atr": prm["fs_stop_atr"],
                    "indicators": f"funding {fr*100:+.3f}%/8h, OI {oi_chg:+.1f}%/24h, px {p_chg:+.1f}%/24h"}
            if allowed("funding_squeeze_short") and fr >= prm["fs_funding_min"]:
                out.append(dict(base, signal="funding_squeeze_short", direction="short",
                                tier=SIGNAL_TIER["funding_squeeze_short"]))
            if allowed("funding_squeeze_long") and fr <= -prm["fs_funding_min"]:
                out.append(dict(base, signal="funding_squeeze_long", direction="long",
                                tier=SIGNAL_TIER["funding_squeeze_long"]))

    return out


def levels_for(sig, price, atr):
    """Stop price for a signal fired at `price` (the closed bar's close, or the live
    fill). Structural signals carry an explicit stop_price; the rest use stop_atr."""
    if sig.get("stop_price") is not None:
        return float(sig["stop_price"])
    mult = float(sig.get("stop_atr", 1.5))
    return price - mult * atr if sig["direction"] == "long" else price + mult * atr
