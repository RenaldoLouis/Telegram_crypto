#!/usr/bin/env python
"""
historical_backtester.py — Rule-based strategy backtester.
Tests mechanical signal rules against historical Bybit kline data.
Zero Claude tokens, pure Python.

Usage:
  python historical_backtester.py                              # PoC: top coins, 1h, 1000 candles
  python historical_backtester.py --symbols ADAUSDT,XRPUSDT    # Specific symbols
  python historical_backtester.py --interval 240               # 4h timeframe
  python historical_backtester.py --limit 1000                 # Candles to fetch
  python historical_backtester.py --signals trend_pullback     # Specific signal only
  python historical_backtester.py --target-sweep               # Test R:R targets 0.5-2.0
  python historical_backtester.py --no-cache                   # Force refetch from Bybit
  python historical_backtester.py --cooldown 6                 # Candles between signals
"""

import json
import os
import sys
import time
import argparse
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict
from itertools import product

import pandas as pd

# Reuse existing Bybit client
import config
from pybit.unified_trading import HTTP

BASE_DIR = Path(__file__).parent
CACHE_DIR = BASE_DIR / "logs" / "backtest_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Default coins — mix of winners and losers from eval data
DEFAULT_SYMBOLS = ["ADAUSDT", "XRPUSDT", "SOLUSDT", "BTCUSDT", "ETHUSDT", "DOGEUSDT"]

# Expanded set for thorough validation
EXPANDED_SYMBOLS = [
    "ADAUSDT", "XRPUSDT", "SOLUSDT", "BTCUSDT", "ETHUSDT", "DOGEUSDT",
    "SUIUSDT", "XLMUSDT", "ENAUSDT", "HBARUSDT", "TRXUSDT", "NEARUSDT",
    "OPUSDT", "ARBUSDT", "INJUSDT",
]

INTERVAL_LABELS = {"15": "15m", "60": "1h", "240": "4h", "D": "1D"}


# ─── Kline Cache ─────────────────────────────────────────────────────────────

def cache_path(symbol, interval, limit):
    return CACHE_DIR / f"{symbol}_{interval}_{limit}.json"


def fetch_klines(symbol, interval, limit=1000, use_cache=True):
    """Fetch klines from Bybit with local caching."""
    cp = cache_path(symbol, interval, limit)

    if use_cache and cp.exists():
        data = json.loads(cp.read_text())
        print(f"    Cache hit: {symbol} {INTERVAL_LABELS.get(interval, interval)} ({len(data['candles'])} candles)")
        return data["candles"]

    print(f"    Fetching: {symbol} {INTERVAL_LABELS.get(interval, interval)} ({limit} candles)...")
    client = HTTP(
        testnet=False,
        api_key=config.BYBIT_API_KEY,
        api_secret=config.BYBIT_API_SECRET,
    )

    try:
        res = client.get_kline(
            category="linear",
            symbol=symbol,
            interval=interval,
            limit=min(limit, 1000),
        )
        candles = res["result"]["list"]
        candles.reverse()  # oldest first

        # Cache locally
        cache_data = {
            "symbol": symbol,
            "interval": interval,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "candles": candles,
        }
        cp.write_text(json.dumps(cache_data))
        time.sleep(0.1)  # rate limit
        return candles

    except Exception as e:
        print(f"    Error fetching {symbol}: {e}")
        return []


# ─── Indicator Computation (full DataFrame) ─────────────────────────────────

def compute_indicators_df(candles):
    """Compute all indicators on full candle DataFrame. Returns enriched DataFrame."""
    df = pd.DataFrame(
        candles,
        columns=["timestamp", "open", "high", "low", "close", "volume", "turnover"]
    )
    df[["open", "high", "low", "close", "volume"]] = df[
        ["open", "high", "low", "close", "volume"]
    ].astype(float)

    # RSI (14)
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss
    df["rsi_14"] = 100 - (100 / (1 + rs))

    # Volume spike
    df["vol_avg_20"] = df["volume"].rolling(20).mean()
    df["vol_spike"] = df["volume"] / df["vol_avg_20"]

    # 20-candle high/low
    df["high_20"] = df["high"].rolling(20).max()
    df["low_20"] = df["low"].rolling(20).min()

    # EMA 20 & 50
    df["ema_20"] = df["close"].ewm(span=20, adjust=False).mean()
    df["ema_50"] = df["close"].ewm(span=50, adjust=False).mean()

    # ATR (14)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - df["close"].shift()).abs(),
        (df["low"] - df["close"].shift()).abs(),
    ], axis=1).max(axis=1)
    df["atr_14"] = tr.rolling(14).mean()

    # MACD (12, 26, 9)
    ema_12 = df["close"].ewm(span=12, adjust=False).mean()
    ema_26 = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"] = ema_12 - ema_26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]

    # ADX (14) — Wilder's smoothing
    plus_dm = df["high"].diff()
    minus_dm = -df["low"].diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
    atr_wilder = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1/14, min_periods=14, adjust=False).mean() / atr_wilder
    minus_di = 100 * minus_dm.ewm(alpha=1/14, min_periods=14, adjust=False).mean() / atr_wilder
    di_sum = plus_di + minus_di
    di_sum = di_sum.replace(0, float('nan'))
    dx = 100 * (plus_di - minus_di).abs() / di_sum
    df["adx_14"] = dx.ewm(alpha=1/14, min_periods=14, adjust=False).mean()

    # Range % (20-candle range as % of price)
    df["range_pct"] = ((df["high_20"] - df["low_20"]) / df["close"]) * 100

    # Candle body % (for candle analysis)
    df["body_pct"] = ((df["close"] - df["open"]) / df["open"]) * 100

    return df


# ─── Signal Rules ────────────────────────────────────────────────────────────
# Each signal function receives (df, i) where i is the candle index.
# Returns None (no signal) or dict with signal details.
# All signals use ONLY data at index <= i (no lookahead).

def _valid(df, i):
    """Check if candle i has valid indicators (past warmup)."""
    row = df.iloc[i]
    return (
        i >= 50 and
        pd.notna(row["rsi_14"]) and
        pd.notna(row["ema_20"]) and
        pd.notna(row["ema_50"]) and
        pd.notna(row["atr_14"]) and
        pd.notna(row["adx_14"]) and
        row["atr_14"] > 0
    )


def signal_trend_pullback_long(df, i):
    """Uptrend + pullback to EMA20 + momentum intact."""
    if not _valid(df, i):
        return None
    r = df.iloc[i]

    if (r["ema_20"] > r["ema_50"] and          # uptrend
        r["adx_14"] > 20 and                    # trending
        35 <= r["rsi_14"] <= 55 and             # pulled back
        r["close"] > r["ema_50"] and            # still above EMA50
        abs(r["close"] - r["ema_20"]) < 0.7 * r["atr_14"] and  # near EMA20
        r["macd"] > 0):                         # momentum positive

        entry = r["close"]
        stop = entry - 1.5 * r["atr_14"]
        risk = entry - stop
        return {"direction": "long", "entry": entry, "stop": stop, "risk": risk}
    return None


def signal_trend_pullback_short(df, i):
    """Downtrend + bounce to EMA20 + momentum negative."""
    if not _valid(df, i):
        return None
    r = df.iloc[i]

    if (r["ema_20"] < r["ema_50"] and
        r["adx_14"] > 20 and
        45 <= r["rsi_14"] <= 65 and
        r["close"] < r["ema_50"] and
        abs(r["close"] - r["ema_20"]) < 0.7 * r["atr_14"] and
        r["macd"] < 0):

        entry = r["close"]
        stop = entry + 1.5 * r["atr_14"]
        risk = stop - entry
        return {"direction": "short", "entry": entry, "stop": stop, "risk": risk}
    return None


def signal_range_reversion_long(df, i):
    """Ranging market + RSI oversold at range bottom."""
    if not _valid(df, i):
        return None
    r = df.iloc[i]

    if (r["adx_14"] < 20 and                    # ranging
        r["rsi_14"] < 35 and                     # oversold
        pd.notna(r["range_pct"]) and
        r["range_pct"] > 3 and                   # range wide enough
        pd.notna(r["low_20"]) and
        r["close"] <= r["low_20"] * 1.015):      # near range bottom (1.5%)

        entry = r["close"]
        stop = r["low_20"] - 0.5 * r["atr_14"]
        risk = entry - stop
        if risk <= 0:
            return None
        return {"direction": "long", "entry": entry, "stop": stop, "risk": risk}
    return None


def signal_range_reversion_short(df, i):
    """Ranging market + RSI overbought at range top."""
    if not _valid(df, i):
        return None
    r = df.iloc[i]

    if (r["adx_14"] < 20 and
        r["rsi_14"] > 65 and
        pd.notna(r["range_pct"]) and
        r["range_pct"] > 3 and
        pd.notna(r["high_20"]) and
        r["close"] >= r["high_20"] * 0.985):

        entry = r["close"]
        stop = r["high_20"] + 0.5 * r["atr_14"]
        risk = stop - entry
        if risk <= 0:
            return None
        return {"direction": "short", "entry": entry, "stop": stop, "risk": risk}
    return None


def signal_volume_breakout_long(df, i):
    """Price breaks above 20-candle high with volume confirmation."""
    if not _valid(df, i):
        return None
    r = df.iloc[i]

    # Need previous candle's high_20 to confirm breakout happened THIS candle
    if i < 1:
        return None
    prev = df.iloc[i - 1]

    if (pd.notna(prev["high_20"]) and
        prev["close"] < prev["high_20"] and     # wasn't breaking out before
        r["close"] > r["high_20"] and            # now breaking out
        pd.notna(r["vol_spike"]) and
        r["vol_spike"] > 2.0 and                 # volume confirms
        r["adx_14"] > 15):                       # some trend energy

        entry = r["close"]
        stop = r["high_20"] - 0.5 * r["atr_14"]  # below breakout level
        risk = entry - stop
        if risk <= 0:
            return None
        return {"direction": "long", "entry": entry, "stop": stop, "risk": risk}
    return None


def signal_volume_breakout_short(df, i):
    """Price breaks below 20-candle low with volume confirmation."""
    if not _valid(df, i):
        return None
    r = df.iloc[i]

    if i < 1:
        return None
    prev = df.iloc[i - 1]

    if (pd.notna(prev["low_20"]) and
        prev["close"] > prev["low_20"] and
        r["close"] < r["low_20"] and
        pd.notna(r["vol_spike"]) and
        r["vol_spike"] > 2.0 and
        r["adx_14"] > 15):

        entry = r["close"]
        stop = r["low_20"] + 0.5 * r["atr_14"]
        risk = stop - entry
        if risk <= 0:
            return None
        return {"direction": "short", "entry": entry, "stop": stop, "risk": risk}
    return None


def signal_ema_crossover_long(df, i):
    """EMA20 crosses above EMA50 with volume."""
    if not _valid(df, i) or i < 1:
        return None
    r = df.iloc[i]
    prev = df.iloc[i - 1]

    if (pd.notna(prev["ema_20"]) and pd.notna(prev["ema_50"]) and
        prev["ema_20"] <= prev["ema_50"] and     # was below
        r["ema_20"] > r["ema_50"] and            # now above (crossover)
        pd.notna(r["vol_spike"]) and
        r["vol_spike"] > 1.5 and                 # volume confirms
        r["adx_14"] > 15):

        entry = r["close"]
        stop = r["ema_50"] - 0.5 * r["atr_14"]
        risk = entry - stop
        if risk <= 0:
            return None
        return {"direction": "long", "entry": entry, "stop": stop, "risk": risk}
    return None


def signal_ema_crossover_short(df, i):
    """EMA20 crosses below EMA50 with volume."""
    if not _valid(df, i) or i < 1:
        return None
    r = df.iloc[i]
    prev = df.iloc[i - 1]

    if (pd.notna(prev["ema_20"]) and pd.notna(prev["ema_50"]) and
        prev["ema_20"] >= prev["ema_50"] and
        r["ema_20"] < r["ema_50"] and
        pd.notna(r["vol_spike"]) and
        r["vol_spike"] > 1.5 and
        r["adx_14"] > 15):

        entry = r["close"]
        stop = r["ema_50"] + 0.5 * r["atr_14"]
        risk = stop - entry
        if risk <= 0:
            return None
        return {"direction": "short", "entry": entry, "stop": stop, "risk": risk}
    return None


def signal_macd_momentum_long(df, i):
    """MACD histogram flips positive in uptrend."""
    if not _valid(df, i) or i < 1:
        return None
    r = df.iloc[i]
    prev = df.iloc[i - 1]

    if (pd.notna(prev["macd_hist"]) and
        prev["macd_hist"] <= 0 and               # was negative
        r["macd_hist"] > 0 and                   # now positive (flip)
        r["ema_20"] > r["ema_50"] and            # in uptrend
        r["rsi_14"] > 40 and r["rsi_14"] < 65):  # not extreme

        entry = r["close"]
        stop = entry - 1.5 * r["atr_14"]
        risk = entry - stop
        return {"direction": "long", "entry": entry, "stop": stop, "risk": risk}
    return None


def signal_macd_momentum_short(df, i):
    """MACD histogram flips negative in downtrend."""
    if not _valid(df, i) or i < 1:
        return None
    r = df.iloc[i]
    prev = df.iloc[i - 1]

    if (pd.notna(prev["macd_hist"]) and
        prev["macd_hist"] >= 0 and
        r["macd_hist"] < 0 and
        r["ema_20"] < r["ema_50"] and
        r["rsi_14"] > 35 and r["rsi_14"] < 60):

        entry = r["close"]
        stop = entry + 1.5 * r["atr_14"]
        risk = stop - entry
        return {"direction": "short", "entry": entry, "stop": stop, "risk": risk}
    return None


def signal_rsi_bounce_long(df, i):
    """RSI oversold bounce — RSI was <30, now crossing back above 30."""
    if not _valid(df, i) or i < 2:
        return None
    r = df.iloc[i]
    prev = df.iloc[i - 1]
    prev2 = df.iloc[i - 2]

    if (pd.notna(prev["rsi_14"]) and pd.notna(prev2["rsi_14"]) and
        prev2["rsi_14"] < 30 and                 # was deeply oversold
        prev["rsi_14"] < 35 and                  # still low
        r["rsi_14"] > 30 and r["rsi_14"] < 45 and  # crossing back up
        r["rsi_14"] > prev["rsi_14"]):           # RSI rising

        entry = r["close"]
        stop = entry - 2.0 * r["atr_14"]
        risk = entry - stop
        return {"direction": "long", "entry": entry, "stop": stop, "risk": risk}
    return None


def signal_rsi_rejection_short(df, i):
    """RSI overbought rejection — RSI was >70, now crossing back below 70."""
    if not _valid(df, i) or i < 2:
        return None
    r = df.iloc[i]
    prev = df.iloc[i - 1]
    prev2 = df.iloc[i - 2]

    if (pd.notna(prev["rsi_14"]) and pd.notna(prev2["rsi_14"]) and
        prev2["rsi_14"] > 70 and
        prev["rsi_14"] > 65 and
        r["rsi_14"] < 70 and r["rsi_14"] > 55 and
        r["rsi_14"] < prev["rsi_14"]):

        entry = r["close"]
        stop = entry + 2.0 * r["atr_14"]
        risk = stop - entry
        return {"direction": "short", "entry": entry, "stop": stop, "risk": risk}
    return None


# ─── Phase 3 candidate signals (candle-only, testable via the slow factory path) ──
# These trade breakout FAILURE (opposite of the continuation-style volume_breakout).
# funding_squeeze / post_liquidation archetypes are intentionally NOT here: the
# backtester has only OHLCV klines (no funding/OI columns), so they can't be
# mechanized or validated in this harness.

def make_failed_breakout(direction, buffer_atr=0.5, rsi_gate=50, body_confirm=True):
    """Failed breakout / trap: price pokes beyond the prior 20-candle extreme
    intrabar, then closes back inside — an upthrust (short) or spring (long).
    Uses only candles <= i (no lookahead)."""
    def signal(df, i):
        if not _valid(df, i) or i < 21:
            return None
        r = df.iloc[i]
        atr = r["atr_14"]
        if not pd.notna(atr) or atr <= 0:
            return None
        window = df.iloc[i - 20:i]  # 20 candles BEFORE i
        if direction == "short":
            prior_high = window["high"].max()
            body_ok = (not body_confirm) or (r["close"] < r["open"])
            if (r["high"] > prior_high and r["close"] < prior_high and
                    body_ok and r["rsi_14"] > rsi_gate):
                entry = r["close"]
                stop = r["high"] + buffer_atr * atr
                risk = stop - entry
                if risk <= 0:
                    return None
                return {"direction": "short", "entry": entry, "stop": stop, "risk": risk}
        else:
            prior_low = window["low"].min()
            body_ok = (not body_confirm) or (r["close"] > r["open"])
            if (r["low"] < prior_low and r["close"] > prior_low and
                    body_ok and r["rsi_14"] < (100 - rsi_gate)):
                entry = r["close"]
                stop = r["low"] - buffer_atr * atr
                risk = entry - stop
                if risk <= 0:
                    return None
                return {"direction": "long", "entry": entry, "stop": stop, "risk": risk}
        return None
    return signal


def make_liquidity_sweep(direction, pierce_atr=0.15, wick_frac=0.5, rsi_gate=50):
    """Liquidity sweep: a wick pierces the prior 20-candle extreme by >= pierce_atr
    ATRs (stop-hunt), the piercing wick is >= wick_frac of the candle range, and
    price closes back inside. Distinct from failed_breakout by requiring a dominant
    rejection wick, not just a close reclaim."""
    def signal(df, i):
        if not _valid(df, i) or i < 21:
            return None
        r = df.iloc[i]
        atr = r["atr_14"]
        rng = r["high"] - r["low"]
        if not pd.notna(atr) or atr <= 0 or rng <= 0:
            return None
        window = df.iloc[i - 20:i]
        if direction == "short":
            prior_high = window["high"].max()
            pierce = r["high"] - prior_high
            upper_wick = r["high"] - max(r["open"], r["close"])
            if (pierce >= pierce_atr * atr and r["close"] < prior_high and
                    upper_wick >= wick_frac * rng and r["rsi_14"] > rsi_gate):
                entry = r["close"]
                stop = r["high"] + 0.25 * atr
                risk = stop - entry
                if risk <= 0:
                    return None
                return {"direction": "short", "entry": entry, "stop": stop, "risk": risk}
        else:
            prior_low = window["low"].min()
            pierce = prior_low - r["low"]
            lower_wick = min(r["open"], r["close"]) - r["low"]
            if (pierce >= pierce_atr * atr and r["close"] > prior_low and
                    lower_wick >= wick_frac * rng and r["rsi_14"] < (100 - rsi_gate)):
                entry = r["close"]
                stop = r["low"] - 0.25 * atr
                risk = entry - stop
                if risk <= 0:
                    return None
                return {"direction": "long", "entry": entry, "stop": stop, "risk": risk}
        return None
    return signal


# ─── Confluence stacking ─────────────────────────────────────────────────────
# Wrap any base signal to additionally require N-of-M same-candle confirmations
# (trend, momentum, strength, volume). Tests the hypothesis that MORE confirmation
# raises expectancy — validate a *_stacked variant head-to-head against its base.
# (This is the single-TF proxy for the live multi-TF confluence gate.)

def make_confluence_stack(base_signal_fn, min_confirms=2):
    """Require >= min_confirms of {trend, macd, ADX>25, volume>1.5x} to agree with
    the base signal's direction. Returns the base signal only if the bar is met."""
    def signal(df, i):
        base = base_signal_fn(df, i)
        if base is None:
            return None
        r = df.iloc[i]
        d = base["direction"]
        confirms = 0
        if pd.notna(r["ema_20"]) and pd.notna(r["ema_50"]):
            if (d == "long" and r["ema_20"] > r["ema_50"]) or \
               (d == "short" and r["ema_20"] < r["ema_50"]):
                confirms += 1
        if pd.notna(r["macd"]):
            if (d == "long" and r["macd"] > 0) or (d == "short" and r["macd"] < 0):
                confirms += 1
        if pd.notna(r["adx_14"]) and r["adx_14"] > 25:
            confirms += 1
        if pd.notna(r["vol_spike"]) and r["vol_spike"] > 1.5:
            confirms += 1
        return base if confirms >= min_confirms else None
    return signal


def make_failed_breakout_stacked(direction, min_confirms=2, buffer_atr=0.5,
                                 rsi_gate=50, body_confirm=True):
    base = make_failed_breakout(direction, buffer_atr=buffer_atr, rsi_gate=rsi_gate,
                                body_confirm=body_confirm)
    return make_confluence_stack(base, min_confirms=min_confirms)


def make_liquidity_sweep_stacked(direction, min_confirms=2, pierce_atr=0.15,
                                 wick_frac=0.5, rsi_gate=50):
    base = make_liquidity_sweep(direction, pierce_atr=pierce_atr, wick_frac=wick_frac,
                                rsi_gate=rsi_gate)
    return make_confluence_stack(base, min_confirms=min_confirms)


# Default-param instances for normal-mode backtest (ALL_SIGNALS).
signal_failed_breakout_long = make_failed_breakout("long")
signal_failed_breakout_short = make_failed_breakout("short")
signal_liquidity_sweep_long = make_liquidity_sweep("long")
signal_liquidity_sweep_short = make_liquidity_sweep("short")
signal_failed_breakout_short_stacked = make_failed_breakout_stacked("short")
signal_liquidity_sweep_long_stacked = make_liquidity_sweep_stacked("long")


# Registry of all signal rules
ALL_SIGNALS = {
    "trend_pullback_long": signal_trend_pullback_long,
    "trend_pullback_short": signal_trend_pullback_short,
    "range_reversion_long": signal_range_reversion_long,
    "range_reversion_short": signal_range_reversion_short,
    "volume_breakout_long": signal_volume_breakout_long,
    "volume_breakout_short": signal_volume_breakout_short,
    "ema_crossover_long": signal_ema_crossover_long,
    "ema_crossover_short": signal_ema_crossover_short,
    "macd_momentum_long": signal_macd_momentum_long,
    "macd_momentum_short": signal_macd_momentum_short,
    "rsi_bounce_long": signal_rsi_bounce_long,
    "rsi_rejection_short": signal_rsi_rejection_short,
    "failed_breakout_long": signal_failed_breakout_long,
    "failed_breakout_short": signal_failed_breakout_short,
    "liquidity_sweep_long": signal_liquidity_sweep_long,
    "liquidity_sweep_short": signal_liquidity_sweep_short,
    "failed_breakout_short_stacked": signal_failed_breakout_short_stacked,
    "liquidity_sweep_long_stacked": signal_liquidity_sweep_long_stacked,
}


# ─── Forward Evaluation ─────────────────────────────────────────────────────

def evaluate_forward(df, signal_idx, signal, target_r, eval_window=48):
    """Check forward candles after signal. Returns outcome dict."""
    entry = signal["entry"]
    stop = signal["stop"]
    risk = signal["risk"]
    direction = signal["direction"]

    if direction == "long":
        target = entry + target_r * risk
    else:
        target = entry - target_r * risk

    max_idx = min(signal_idx + eval_window, len(df) - 1)
    if signal_idx + 1 > max_idx:
        return None  # not enough forward data

    mfe = 0.0  # max favorable excursion in R
    candles_to_exit = 0

    for j in range(signal_idx + 1, max_idx + 1):
        candle = df.iloc[j]
        candles_to_exit = j - signal_idx

        # Track MFE
        if direction == "long":
            favorable = (candle["high"] - entry) / risk if risk > 0 else 0
            # Check stop
            if candle["low"] <= stop:
                return {
                    "outcome": "stop_loss", "actual_rr": -1.0,
                    "mfe": round(mfe, 3), "candles": candles_to_exit,
                    "target_r": target_r,
                }
            # Check target
            if candle["high"] >= target:
                return {
                    "outcome": "target_hit", "actual_rr": round(target_r, 3),
                    "mfe": round(max(mfe, favorable), 3), "candles": candles_to_exit,
                    "target_r": target_r,
                }
        else:  # short
            favorable = (entry - candle["low"]) / risk if risk > 0 else 0
            if candle["high"] >= stop:
                return {
                    "outcome": "stop_loss", "actual_rr": -1.0,
                    "mfe": round(mfe, 3), "candles": candles_to_exit,
                    "target_r": target_r,
                }
            if candle["low"] <= target:
                return {
                    "outcome": "target_hit", "actual_rr": round(target_r, 3),
                    "mfe": round(max(mfe, favorable), 3), "candles": candles_to_exit,
                    "target_r": target_r,
                }

        mfe = max(mfe, favorable)

    # Expired — use last close
    last_close = df.iloc[max_idx]["close"]
    if direction == "long":
        exit_rr = (last_close - entry) / risk if risk > 0 else 0
    else:
        exit_rr = (entry - last_close) / risk if risk > 0 else 0

    return {
        "outcome": "expired", "actual_rr": round(exit_rr, 3),
        "mfe": round(mfe, 3), "candles": candles_to_exit,
        "target_r": target_r,
    }


# ─── Backtest Engine ─────────────────────────────────────────────────────────

def run_backtest(df, symbol, signals_to_test, target_rs, cooldown=12, eval_window=48):
    """Run all signal rules across the DataFrame. Returns list of trade records."""
    results = []
    n = len(df)

    for sig_name, sig_fn in signals_to_test.items():
        last_signal_idx = -cooldown - 1  # allow first signal immediately

        for i in range(50, n - eval_window):
            # Cooldown check
            if i - last_signal_idx < cooldown:
                continue

            signal = sig_fn(df, i)
            if signal is None:
                continue

            last_signal_idx = i

            for tr in target_rs:
                result = evaluate_forward(df, i, signal, tr, eval_window)
                if result is None:
                    continue
                result["signal"] = sig_name
                result["symbol"] = symbol
                result["direction"] = signal["direction"]
                result["candle_idx"] = i
                result["entry_price"] = round(signal["entry"], 8)
                result["stop_price"] = round(signal["stop"], 8)
                result["risk"] = round(signal["risk"], 8)
                result["timestamp"] = df.iloc[i]["timestamp"]
                results.append(result)

    return results


# ─── Reporting ───────────────────────────────────────────────────────────────

def compute_stats(trades):
    """Compute aggregate stats."""
    if not trades:
        return {"n": 0, "wr": 0, "avg_rr": 0, "expectancy": 0, "pf": 0, "avg_mfe": 0}

    n = len(trades)
    wins = sum(1 for t in trades if t["actual_rr"] > 0)
    rr_sum = sum(t["actual_rr"] for t in trades)
    mfe_sum = sum(t.get("mfe", 0) for t in trades)

    winning = [t["actual_rr"] for t in trades if t["actual_rr"] > 0]
    losing = [abs(t["actual_rr"]) for t in trades if t["actual_rr"] <= 0]
    avg_win = sum(winning) / len(winning) if winning else 0
    avg_loss = sum(losing) / len(losing) if losing else 0
    wr = wins / n
    expectancy = avg_win * wr - avg_loss * (1 - wr)

    gross_profit = sum(winning)
    gross_loss = sum(losing)
    pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')

    return {
        "n": n, "wins": wins, "losses": n - wins,
        "wr": round(wr * 100, 1),
        "avg_rr": round(rr_sum / n, 3),
        "expectancy": round(expectancy, 3),
        "pf": round(pf, 2),
        "avg_mfe": round(mfe_sum / n, 3),
        "rr_sum": round(rr_sum, 2),
    }


HDR = "  {:<30s} {:>5s} {:>7s} {:>8s} {:>8s} {:>6s} {:>8s}"
ROW = "  {:<30s} {:>5d} {:>6.1f}% {:>8.3f} {:>8.3f} {:>6.2f} {:>8.3f}"

def print_header():
    print(HDR.format("", "N", "WR", "Expect", "Avg R:R", "PF", "Avg MFE"))
    print("  " + "─" * 77)

def print_row(label, s):
    if s["n"] == 0:
        return
    print(ROW.format(label, s["n"], s["wr"], s["expectancy"], s["avg_rr"], s["pf"], s["avg_mfe"]))

def section(title):
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print(f"{'=' * 80}")


def report_by_signal(all_trades, target_r=None):
    """Report per-signal breakdown."""
    section(f"BY SIGNAL RULE{f' (target={target_r}R)' if target_r else ''}")
    print_header()

    # Filter to specific target if given
    trades = [t for t in all_trades if target_r is None or t["target_r"] == target_r]
    baseline = compute_stats(trades)
    print_row("ALL SIGNALS", baseline)
    print("  " + "─" * 77)

    groups = defaultdict(list)
    for t in trades:
        groups[t["signal"]].append(t)

    rows = []
    for sig, sig_trades in sorted(groups.items()):
        s = compute_stats(sig_trades)
        rows.append((sig, s))

    rows.sort(key=lambda x: x[1]["expectancy"], reverse=True)
    for sig, s in rows:
        tag = " ★" if s["expectancy"] > 0 and s["n"] >= 10 else ""
        print_row(f"{sig}{tag}", s)


def report_by_symbol(all_trades, target_r=None):
    """Report per-symbol breakdown."""
    section(f"BY SYMBOL{f' (target={target_r}R)' if target_r else ''}")
    print_header()

    trades = [t for t in all_trades if target_r is None or t["target_r"] == target_r]

    groups = defaultdict(list)
    for t in trades:
        groups[t["symbol"]].append(t)

    rows = []
    for sym, sym_trades in sorted(groups.items()):
        s = compute_stats(sym_trades)
        rows.append((sym, s))

    rows.sort(key=lambda x: x[1]["expectancy"], reverse=True)
    for sym, s in rows:
        tag = " ★" if s["expectancy"] > 0 and s["n"] >= 10 else ""
        print_row(f"{sym}{tag}", s)


def report_target_sweep(all_trades):
    """Report by target R:R level — find optimal target distance."""
    section("TARGET R:R SWEEP")
    print("  Which target distance produces the best expectancy?\n")
    print_header()

    target_rs = sorted(set(t["target_r"] for t in all_trades))
    for tr in target_rs:
        trades = [t for t in all_trades if t["target_r"] == tr]
        s = compute_stats(trades)
        tag = " ★ BEST" if s["expectancy"] > 0 else ""
        print_row(f"Target {tr}R{tag}", s)


def report_signal_x_target(all_trades):
    """Matrix: each signal × each target R:R."""
    section("SIGNAL × TARGET MATRIX (expectancy)")

    target_rs = sorted(set(t["target_r"] for t in all_trades))
    signals = sorted(set(t["signal"] for t in all_trades))

    # Header
    hdr = f"  {'Signal':<28s}" + "".join(f" {tr:>6.2f}R" for tr in target_rs)
    print(hdr)
    print("  " + "─" * (28 + 8 * len(target_rs)))

    best_combos = []
    for sig in signals:
        row = f"  {sig:<28s}"
        for tr in target_rs:
            trades = [t for t in all_trades if t["signal"] == sig and t["target_r"] == tr]
            if not trades:
                row += f" {'—':>7s}"
                continue
            s = compute_stats(trades)
            val = s["expectancy"]
            marker = "*" if val > 0 and s["n"] >= 10 else " "
            row += f" {val:>+6.3f}{marker}"
            if val > 0 and s["n"] >= 10:
                best_combos.append((sig, tr, s))
        print(row)

    if best_combos:
        best_combos.sort(key=lambda x: x[2]["expectancy"], reverse=True)
        print(f"\n  ★ Best combos (positive expectancy, 10+ trades):")
        for sig, tr, s in best_combos[:10]:
            print(f"    {sig} @ {tr}R → {s['expectancy']:+.3f} expect, "
                  f"{s['wr']}% WR, {s['n']} trades, PF {s['pf']}")


def report_signal_x_symbol(all_trades, target_r):
    """Matrix: each signal × each symbol at best target."""
    section(f"SIGNAL × SYMBOL (target={target_r}R, expectancy)")

    trades = [t for t in all_trades if t["target_r"] == target_r]
    signals = sorted(set(t["signal"] for t in trades))
    symbols = sorted(set(t["symbol"] for t in trades))

    hdr = f"  {'Signal':<28s}" + "".join(f" {s:>8s}" for s in symbols)
    print(hdr)
    print("  " + "─" * (28 + 9 * len(symbols)))

    for sig in signals:
        row = f"  {sig:<28s}"
        for sym in symbols:
            st = [t for t in trades if t["signal"] == sig and t["symbol"] == sym]
            if not st:
                row += f" {'—':>8s}"
                continue
            s = compute_stats(st)
            val = s["expectancy"]
            n = s["n"]
            row += f" {val:>+.2f}/{n:<3d}"
        print(row)


def report_mfe_analysis(all_trades, target_r=None):
    """MFE distribution — how far price moves in signal direction."""
    section(f"MFE DISTRIBUTION{f' (target={target_r}R)' if target_r else ''}")

    trades = [t for t in all_trades if target_r is None or t["target_r"] == target_r]
    n = len(trades)
    if n == 0:
        print("  No trades.")
        return

    thresholds = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
    print(f"  Total signals: {n}\n")
    print(f"  {'MFE Threshold':<18s} {'Count':>6s} {'%':>7s} {'Implication':>30s}")
    print("  " + "─" * 65)
    for thr in thresholds:
        count = sum(1 for t in trades if t.get("mfe", 0) >= thr)
        pct = round(count / n * 100, 1)
        impl = ""
        if thr == 0.5:
            impl = "direction usually right" if pct > 50 else "direction often wrong"
        elif thr == 1.0:
            impl = f"1.0R target viable" if pct > 40 else "1.0R target too far"
        print(f"  >= {thr:.2f}R{'':<12s} {count:>6d} {pct:>6.1f}% {impl:>30s}")


def report_findings(all_trades, target_rs):
    """Auto-generate actionable findings."""
    section("ACTIONABLE FINDINGS")
    findings = []

    # Find best target R:R
    best_tr, best_exp = None, -999
    for tr in target_rs:
        trades = [t for t in all_trades if t["target_r"] == tr]
        s = compute_stats(trades)
        if s["n"] >= 20 and s["expectancy"] > best_exp:
            best_exp = s["expectancy"]
            best_tr = tr
    if best_tr and best_exp > -0.5:
        findings.append(f"Best target distance: {best_tr}R (expectancy: {best_exp:+.3f})")

    # Find best signal rules
    best_signals = []
    for sig in set(t["signal"] for t in all_trades):
        for tr in target_rs:
            trades = [t for t in all_trades if t["signal"] == sig and t["target_r"] == tr]
            s = compute_stats(trades)
            if s["n"] >= 10 and s["expectancy"] > 0:
                best_signals.append((sig, tr, s))
    best_signals.sort(key=lambda x: x[2]["expectancy"], reverse=True)
    for sig, tr, s in best_signals[:5]:
        findings.append(
            f"Profitable signal: {sig} @ {tr}R → {s['wr']}% WR, "
            f"{s['expectancy']:+.3f} expect, {s['n']} trades"
        )

    # Direction edge
    longs = [t for t in all_trades if t["direction"] == "long" and t["target_r"] == (best_tr or 1.0)]
    shorts = [t for t in all_trades if t["direction"] == "short" and t["target_r"] == (best_tr or 1.0)]
    sl, ss = compute_stats(longs), compute_stats(shorts)
    if sl["n"] >= 10 and ss["n"] >= 10:
        better = "longs" if sl["expectancy"] > ss["expectancy"] else "shorts"
        findings.append(
            f"Direction edge: {better} ({sl['expectancy']:+.3f} L vs {ss['expectancy']:+.3f} S)"
        )

    # MFE waste
    if best_tr:
        trades = [t for t in all_trades if t["target_r"] == best_tr]
        wasted = sum(1 for t in trades if t.get("mfe", 0) >= best_tr and t["actual_rr"] <= 0)
        if wasted > 0:
            findings.append(f"{wasted} signals reached {best_tr}R MFE but still lost (stop timing issue)")

    if findings:
        for i, f in enumerate(findings, 1):
            print(f"  {i}. {f}")
    else:
        print("  Not enough data for significant findings. Try more symbols/candles.")


# ─── Parameterized Signal Factories ──────────────────────────────────────────
# Each factory returns a signal function with tunable parameters.
# Used by the --optimize sweep to find the best parameter combination.

def make_trend_pullback(direction, rsi_lo, rsi_hi, adx_min, atr_mult, ema_prox, require_macd):
    """Factory for trend pullback signals with tunable params."""
    def signal(df, i):
        if not _valid(df, i):
            return None
        r = df.iloc[i]
        if direction == "short":
            if (r["ema_20"] < r["ema_50"] and
                r["adx_14"] > adx_min and
                rsi_lo <= r["rsi_14"] <= rsi_hi and
                r["close"] < r["ema_50"] and
                abs(r["close"] - r["ema_20"]) < ema_prox * r["atr_14"] and
                (not require_macd or r["macd"] < 0)):
                entry = r["close"]
                stop = entry + atr_mult * r["atr_14"]
                risk = stop - entry
                return {"direction": "short", "entry": entry, "stop": stop, "risk": risk}
        else:
            if (r["ema_20"] > r["ema_50"] and
                r["adx_14"] > adx_min and
                rsi_lo <= r["rsi_14"] <= rsi_hi and
                r["close"] > r["ema_50"] and
                abs(r["close"] - r["ema_20"]) < ema_prox * r["atr_14"] and
                (not require_macd or r["macd"] > 0)):
                entry = r["close"]
                stop = entry - atr_mult * r["atr_14"]
                risk = entry - stop
                return {"direction": "long", "entry": entry, "stop": stop, "risk": risk}
        return None
    return signal


def make_range_reversion(direction, rsi_thresh, adx_max, range_min, price_prox, atr_mult):
    """Factory for range mean reversion signals."""
    def signal(df, i):
        if not _valid(df, i):
            return None
        r = df.iloc[i]
        if not pd.notna(r["range_pct"]) or r["range_pct"] < range_min:
            return None
        if r["adx_14"] >= adx_max:
            return None

        if direction == "long":
            if (r["rsi_14"] < rsi_thresh and
                pd.notna(r["low_20"]) and
                r["close"] <= r["low_20"] * (1 + price_prox / 100)):
                entry = r["close"]
                stop = r["low_20"] - atr_mult * r["atr_14"]
                risk = entry - stop
                if risk <= 0:
                    return None
                return {"direction": "long", "entry": entry, "stop": stop, "risk": risk}
        else:
            if (r["rsi_14"] > (100 - rsi_thresh) and
                pd.notna(r["high_20"]) and
                r["close"] >= r["high_20"] * (1 - price_prox / 100)):
                entry = r["close"]
                stop = r["high_20"] + atr_mult * r["atr_14"]
                risk = stop - entry
                if risk <= 0:
                    return None
                return {"direction": "short", "entry": entry, "stop": stop, "risk": risk}
        return None
    return signal


def make_macd_momentum(direction, adx_min, rsi_lo, rsi_hi, atr_mult, require_trend):
    """Factory for MACD histogram flip signals."""
    def signal(df, i):
        if not _valid(df, i) or i < 1:
            return None
        r = df.iloc[i]
        prev = df.iloc[i - 1]
        if not pd.notna(prev["macd_hist"]):
            return None

        if direction == "long":
            if (prev["macd_hist"] <= 0 and r["macd_hist"] > 0 and
                r["adx_14"] > adx_min and
                rsi_lo <= r["rsi_14"] <= rsi_hi and
                (not require_trend or r["ema_20"] > r["ema_50"])):
                entry = r["close"]
                stop = entry - atr_mult * r["atr_14"]
                risk = entry - stop
                return {"direction": "long", "entry": entry, "stop": stop, "risk": risk}
        else:
            if (prev["macd_hist"] >= 0 and r["macd_hist"] < 0 and
                r["adx_14"] > adx_min and
                rsi_lo <= r["rsi_14"] <= rsi_hi and
                (not require_trend or r["ema_20"] < r["ema_50"])):
                entry = r["close"]
                stop = entry + atr_mult * r["atr_14"]
                risk = stop - entry
                return {"direction": "short", "entry": entry, "stop": stop, "risk": risk}
        return None
    return signal


def make_rsi_extreme(direction, rsi_extreme, rsi_recover, atr_mult):
    """Factory for RSI oversold bounce / overbought rejection."""
    def signal(df, i):
        if not _valid(df, i) or i < 2:
            return None
        r = df.iloc[i]
        prev = df.iloc[i - 1]
        prev2 = df.iloc[i - 2]
        if not (pd.notna(prev["rsi_14"]) and pd.notna(prev2["rsi_14"])):
            return None

        if direction == "long":
            if (prev2["rsi_14"] < rsi_extreme and
                prev["rsi_14"] < rsi_extreme + 5 and
                r["rsi_14"] > rsi_recover and r["rsi_14"] < rsi_recover + 15 and
                r["rsi_14"] > prev["rsi_14"]):
                entry = r["close"]
                stop = entry - atr_mult * r["atr_14"]
                risk = entry - stop
                return {"direction": "long", "entry": entry, "stop": stop, "risk": risk}
        else:
            if (prev2["rsi_14"] > (100 - rsi_extreme) and
                prev["rsi_14"] > (100 - rsi_extreme - 5) and
                r["rsi_14"] < (100 - rsi_recover) and r["rsi_14"] > (100 - rsi_recover - 15) and
                r["rsi_14"] < prev["rsi_14"]):
                entry = r["close"]
                stop = entry + atr_mult * r["atr_14"]
                risk = stop - entry
                return {"direction": "short", "entry": entry, "stop": stop, "risk": risk}
        return None
    return signal


def make_volume_breakout(direction, vol_min, adx_min, atr_mult):
    """Factory for volume-confirmed breakout signals."""
    def signal(df, i):
        if not _valid(df, i) or i < 1:
            return None
        r = df.iloc[i]
        prev = df.iloc[i - 1]
        if not pd.notna(r["vol_spike"]) or r["vol_spike"] < vol_min:
            return None
        if r["adx_14"] < adx_min:
            return None

        if direction == "long":
            if (pd.notna(prev["high_20"]) and
                prev["close"] < prev["high_20"] and
                r["close"] > r["high_20"]):
                entry = r["close"]
                stop = r["high_20"] - atr_mult * r["atr_14"]
                risk = entry - stop
                if risk <= 0:
                    return None
                return {"direction": "long", "entry": entry, "stop": stop, "risk": risk}
        else:
            if (pd.notna(prev["low_20"]) and
                prev["close"] > prev["low_20"] and
                r["close"] < r["low_20"]):
                entry = r["close"]
                stop = r["low_20"] + atr_mult * r["atr_14"]
                risk = stop - entry
                if risk <= 0:
                    return None
                return {"direction": "short", "entry": entry, "stop": stop, "risk": risk}
        return None
    return signal


# ─── Parameter Grids ─────────────────────────────────────────────────────────

PARAM_GRIDS = {
    "trend_pullback_short": {
        "factory": lambda **kw: make_trend_pullback("short", **kw),
        "params": {
            "rsi_lo":       [35, 40, 45, 50],
            "rsi_hi":       [60, 65, 70, 75],
            "adx_min":      [15, 18, 20, 25],
            "atr_mult":     [1.0, 1.5, 2.0, 2.5],
            "ema_prox":     [0.5, 0.7, 1.0, 1.5],
            "require_macd": [True, False],
        },
        "targets": [0.5, 0.75, 1.0, 1.5, 2.0],
    },
    "trend_pullback_long": {
        "factory": lambda **kw: make_trend_pullback("long", **kw),
        "params": {
            "rsi_lo":       [30, 35, 40],
            "rsi_hi":       [50, 55, 60],
            "adx_min":      [15, 18, 20, 25],
            "atr_mult":     [1.0, 1.5, 2.0, 2.5],
            "ema_prox":     [0.5, 0.7, 1.0, 1.5],
            "require_macd": [True, False],
        },
        "targets": [0.5, 0.75, 1.0, 1.5],
    },
    "range_reversion_short": {
        "factory": lambda **kw: make_range_reversion("short", **kw),
        "params": {
            "rsi_thresh":  [30, 33, 35, 38],   # maps to >65, >67, etc. for short
            "adx_max":     [18, 20, 22, 25],
            "range_min":   [2.0, 3.0, 4.0, 5.0],
            "price_prox":  [1.0, 1.5, 2.0, 3.0],
            "atr_mult":    [0.3, 0.5, 0.7, 1.0],
        },
        "targets": [0.5, 0.75, 1.0, 1.5],
    },
    "range_reversion_long": {
        "factory": lambda **kw: make_range_reversion("long", **kw),
        "params": {
            "rsi_thresh":  [30, 33, 35, 38],
            "adx_max":     [18, 20, 22, 25],
            "range_min":   [2.0, 3.0, 4.0, 5.0],
            "price_prox":  [1.0, 1.5, 2.0, 3.0],
            "atr_mult":    [0.3, 0.5, 0.7, 1.0],
        },
        "targets": [0.5, 0.75, 1.0, 1.5],
    },
    "macd_momentum_short": {
        "factory": lambda **kw: make_macd_momentum("short", **kw),
        "params": {
            "adx_min":       [10, 15, 20],
            "rsi_lo":        [30, 35, 40],
            "rsi_hi":        [55, 60, 65, 70],
            "atr_mult":      [1.0, 1.5, 2.0],
            "require_trend": [True, False],
        },
        "targets": [0.5, 0.75, 1.0, 1.5],
    },
    "macd_momentum_long": {
        "factory": lambda **kw: make_macd_momentum("long", **kw),
        "params": {
            "adx_min":       [10, 15, 20],
            "rsi_lo":        [35, 40, 45],
            "rsi_hi":        [60, 65, 70],
            "atr_mult":      [1.0, 1.5, 2.0],
            "require_trend": [True, False],
        },
        "targets": [0.5, 0.75, 1.0, 1.5],
    },
    "rsi_rejection_short": {
        "factory": lambda **kw: make_rsi_extreme("short", **kw),
        "params": {
            "rsi_extreme":  [25, 28, 30, 33],   # maps to >70, >72, etc.
            "rsi_recover":  [25, 28, 30, 33],    # maps to <70, <72, etc.
            "atr_mult":     [1.5, 2.0, 2.5, 3.0],
        },
        "targets": [0.5, 0.75, 1.0, 1.5, 2.0],
    },
    "rsi_bounce_long": {
        "factory": lambda **kw: make_rsi_extreme("long", **kw),
        "params": {
            "rsi_extreme":  [25, 28, 30, 33],
            "rsi_recover":  [25, 28, 30, 33],
            "atr_mult":     [1.5, 2.0, 2.5, 3.0],
        },
        "targets": [0.5, 0.75, 1.0, 1.5, 2.0],
    },
    "volume_breakout_short": {
        "factory": lambda **kw: make_volume_breakout("short", **kw),
        "params": {
            "vol_min":  [1.5, 2.0, 2.5, 3.0],
            "adx_min":  [10, 15, 20],
            "atr_mult": [0.3, 0.5, 0.7, 1.0],
        },
        "targets": [0.5, 0.75, 1.0, 1.5],
    },
    "volume_breakout_long": {
        "factory": lambda **kw: make_volume_breakout("long", **kw),
        "params": {
            "vol_min":  [1.5, 2.0, 2.5, 3.0],
            "adx_min":  [10, 15, 20],
            "atr_mult": [0.3, 0.5, 0.7, 1.0],
        },
        "targets": [0.5, 0.75, 1.0, 1.5],
    },
    # Phase 3 candidates — NO fast sweep; optimized/validated via the generic slow
    # factory path. Grids are kept SMALL so the slow path stays practical.
    "failed_breakout_short": {
        "factory": lambda **kw: make_failed_breakout("short", **kw),
        "params": {
            "buffer_atr":  [0.25, 0.5],
            "rsi_gate":    [45, 50, 55],
            "body_confirm": [True, False],
        },
        "targets": [1.0, 1.5, 2.0],
    },
    "failed_breakout_long": {
        "factory": lambda **kw: make_failed_breakout("long", **kw),
        "params": {
            "buffer_atr":  [0.25, 0.5],
            "rsi_gate":    [45, 50, 55],
            "body_confirm": [True, False],
        },
        "targets": [1.0, 1.5, 2.0],
    },
    "liquidity_sweep_short": {
        "factory": lambda **kw: make_liquidity_sweep("short", **kw),
        "params": {
            "pierce_atr": [0.1, 0.2],
            "wick_frac":  [0.4, 0.5, 0.6],
            "rsi_gate":   [50, 55],
        },
        "targets": [1.0, 1.5, 2.0],
    },
    "liquidity_sweep_long": {
        "factory": lambda **kw: make_liquidity_sweep("long", **kw),
        "params": {
            "pierce_atr": [0.1, 0.2],
            "wick_frac":  [0.4, 0.5, 0.6],
            "rsi_gate":   [50, 55],
        },
        "targets": [1.0, 1.5, 2.0],
    },
    # Confluence-stacked variants — sweep min_confirms to test whether requiring
    # more same-candle confirmation raises expectancy vs the un-stacked base.
    "failed_breakout_short_stacked": {
        "factory": lambda **kw: make_failed_breakout_stacked("short", **kw),
        "params": {"min_confirms": [1, 2, 3], "buffer_atr": [0.5], "rsi_gate": [50]},
        "targets": [1.0, 1.5, 2.0],
    },
    "liquidity_sweep_long_stacked": {
        "factory": lambda **kw: make_liquidity_sweep_stacked("long", **kw),
        "params": {"min_confirms": [1, 2, 3], "wick_frac": [0.5], "rsi_gate": [50]},
        "targets": [1.0, 1.5, 2.0],
    },
}


# ─── Parameter Sweep Engine (vectorized) ─────────────────────────────────────

import numpy as np

def _precompute_arrays(df):
    """Extract DataFrame columns as numpy arrays for fast sweep."""
    n = len(df)
    return {
        "n": n,
        "close": df["close"].values.astype(float),
        "high": df["high"].values.astype(float),
        "low": df["low"].values.astype(float),
        "ema_20": df["ema_20"].values.astype(float),
        "ema_50": df["ema_50"].values.astype(float),
        "adx_14": df["adx_14"].values.astype(float),
        "rsi_14": df["rsi_14"].values.astype(float),
        "atr_14": df["atr_14"].values.astype(float),
        "macd": df["macd"].values.astype(float),
        "macd_hist": df["macd_hist"].values.astype(float),
        "vol_spike": df["vol_spike"].values.astype(float),
        "high_20": df["high_20"].values.astype(float),
        "low_20": df["low_20"].values.astype(float),
        "range_pct": df["range_pct"].values.astype(float),
        # Validity mask: past warmup + no NaN in critical fields
        "valid": np.array([
            i >= 50 and
            not np.isnan(df["rsi_14"].iat[i]) and
            not np.isnan(df["ema_20"].iat[i]) and
            not np.isnan(df["ema_50"].iat[i]) and
            not np.isnan(df["atr_14"].iat[i]) and
            not np.isnan(df["adx_14"].iat[i]) and
            df["atr_14"].iat[i] > 0
            for i in range(n)
        ]),
    }


def _fast_evaluate(arr, idx, direction, entry, stop, risk, target_r, eval_window):
    """Fast forward evaluation using numpy arrays."""
    n = arr["n"]
    if direction == "long":
        target = entry + target_r * risk
    else:
        target = entry - target_r * risk

    max_idx = min(idx + eval_window, n - 1)
    if idx + 1 > max_idx:
        return None

    mfe = 0.0
    for j in range(idx + 1, max_idx + 1):
        if direction == "long":
            favorable = (arr["high"][j] - entry) / risk if risk > 0 else 0
            if arr["low"][j] <= stop:
                return {"outcome": "stop_loss", "actual_rr": -1.0, "mfe": mfe, "target_r": target_r}
            if arr["high"][j] >= target:
                return {"outcome": "target_hit", "actual_rr": target_r, "mfe": max(mfe, favorable), "target_r": target_r}
        else:
            favorable = (entry - arr["low"][j]) / risk if risk > 0 else 0
            if arr["high"][j] >= stop:
                return {"outcome": "stop_loss", "actual_rr": -1.0, "mfe": mfe, "target_r": target_r}
            if arr["low"][j] <= target:
                return {"outcome": "target_hit", "actual_rr": target_r, "mfe": max(mfe, favorable), "target_r": target_r}
        mfe = max(mfe, favorable)

    # Expired
    last_close = arr["close"][max_idx]
    if direction == "long":
        exit_rr = (last_close - entry) / risk if risk > 0 else 0
    else:
        exit_rr = (entry - last_close) / risk if risk > 0 else 0
    return {"outcome": "expired", "actual_rr": round(exit_rr, 3), "mfe": mfe, "target_r": target_r}


def _sweep_trend_pullback(arrs, direction, params, targets, cooldown, eval_window):
    """Fast vectorized sweep for trend_pullback signal."""
    rsi_lo = params["rsi_lo"]
    rsi_hi = params["rsi_hi"]
    adx_min = params["adx_min"]
    atr_mult = params["atr_mult"]
    ema_prox = params["ema_prox"]
    require_macd = params["require_macd"]

    all_results = []
    for arr in arrs:
        n = arr["n"]
        last_sig = -cooldown - 1

        for i in range(50, n - eval_window):
            if i - last_sig < cooldown:
                continue
            if not arr["valid"][i]:
                continue

            rsi = arr["rsi_14"][i]
            adx = arr["adx_14"][i]
            close = arr["close"][i]
            ema20 = arr["ema_20"][i]
            ema50 = arr["ema_50"][i]
            atr = arr["atr_14"][i]
            macd_val = arr["macd"][i]

            if not (rsi_lo <= rsi <= rsi_hi and adx > adx_min):
                continue
            if abs(close - ema20) >= ema_prox * atr:
                continue

            if direction == "short":
                if ema20 >= ema50 or close >= ema50:
                    continue
                if require_macd and macd_val >= 0:
                    continue
                entry = close
                stop = entry + atr_mult * atr
                risk = stop - entry
            else:
                if ema20 <= ema50 or close <= ema50:
                    continue
                if require_macd and macd_val <= 0:
                    continue
                entry = close
                stop = entry - atr_mult * atr
                risk = entry - stop

            last_sig = i
            for tr in targets:
                result = _fast_evaluate(arr, i, direction, entry, stop, risk, tr, eval_window)
                if result:
                    all_results.append(result)

    return all_results


def _sweep_range_reversion(arrs, direction, params, targets, cooldown, eval_window):
    """Fast vectorized sweep for range_reversion signal."""
    rsi_thresh = params["rsi_thresh"]
    adx_max = params["adx_max"]
    range_min = params["range_min"]
    price_prox = params["price_prox"]
    atr_mult = params["atr_mult"]

    all_results = []
    for arr in arrs:
        n = arr["n"]
        last_sig = -cooldown - 1

        for i in range(50, n - eval_window):
            if i - last_sig < cooldown or not arr["valid"][i]:
                continue

            rsi = arr["rsi_14"][i]
            adx = arr["adx_14"][i]
            rng = arr["range_pct"][i]
            close = arr["close"][i]
            atr = arr["atr_14"][i]

            if np.isnan(rng) or rng < range_min or adx >= adx_max:
                continue

            if direction == "long":
                low20 = arr["low_20"][i]
                if np.isnan(low20) or rsi >= rsi_thresh:
                    continue
                if close > low20 * (1 + price_prox / 100):
                    continue
                entry = close
                stop = low20 - atr_mult * atr
                risk = entry - stop
                if risk <= 0:
                    continue
            else:
                high20 = arr["high_20"][i]
                if np.isnan(high20) or rsi <= (100 - rsi_thresh):
                    continue
                if close < high20 * (1 - price_prox / 100):
                    continue
                entry = close
                stop = high20 + atr_mult * atr
                risk = stop - entry
                if risk <= 0:
                    continue

            last_sig = i
            for tr in targets:
                result = _fast_evaluate(arr, i, direction, entry, stop, risk, tr, eval_window)
                if result:
                    all_results.append(result)

    return all_results


def _sweep_macd_momentum(arrs, direction, params, targets, cooldown, eval_window):
    """Fast vectorized sweep for MACD momentum signal."""
    adx_min = params["adx_min"]
    rsi_lo = params["rsi_lo"]
    rsi_hi = params["rsi_hi"]
    atr_mult = params["atr_mult"]
    require_trend = params["require_trend"]

    all_results = []
    for arr in arrs:
        n = arr["n"]
        last_sig = -cooldown - 1

        for i in range(51, n - eval_window):
            if i - last_sig < cooldown or not arr["valid"][i]:
                continue

            rsi = arr["rsi_14"][i]
            adx = arr["adx_14"][i]
            hist = arr["macd_hist"][i]
            prev_hist = arr["macd_hist"][i - 1]
            close = arr["close"][i]
            atr = arr["atr_14"][i]

            if np.isnan(prev_hist) or not (rsi_lo <= rsi <= rsi_hi) or adx < adx_min:
                continue

            if direction == "long":
                if prev_hist > 0 or hist <= 0:
                    continue
                if require_trend and arr["ema_20"][i] <= arr["ema_50"][i]:
                    continue
                entry = close
                stop = entry - atr_mult * atr
                risk = entry - stop
            else:
                if prev_hist < 0 or hist >= 0:
                    continue
                if require_trend and arr["ema_20"][i] >= arr["ema_50"][i]:
                    continue
                entry = close
                stop = entry + atr_mult * atr
                risk = stop - entry

            last_sig = i
            for tr in targets:
                result = _fast_evaluate(arr, i, direction, entry, stop, risk, tr, eval_window)
                if result:
                    all_results.append(result)

    return all_results


def _sweep_rsi_extreme(arrs, direction, params, targets, cooldown, eval_window):
    """Fast vectorized sweep for RSI extreme signal."""
    rsi_extreme = params["rsi_extreme"]
    rsi_recover = params["rsi_recover"]
    atr_mult = params["atr_mult"]

    all_results = []
    for arr in arrs:
        n = arr["n"]
        last_sig = -cooldown - 1

        for i in range(52, n - eval_window):
            if i - last_sig < cooldown or not arr["valid"][i]:
                continue

            rsi = arr["rsi_14"][i]
            rsi_prev = arr["rsi_14"][i - 1]
            rsi_prev2 = arr["rsi_14"][i - 2]
            close = arr["close"][i]
            atr = arr["atr_14"][i]

            if np.isnan(rsi_prev) or np.isnan(rsi_prev2):
                continue

            if direction == "long":
                if not (rsi_prev2 < rsi_extreme and rsi_prev < rsi_extreme + 5 and
                        rsi > rsi_recover and rsi < rsi_recover + 15 and rsi > rsi_prev):
                    continue
                entry = close
                stop = entry - atr_mult * atr
                risk = entry - stop
            else:
                if not (rsi_prev2 > (100 - rsi_extreme) and rsi_prev > (100 - rsi_extreme - 5) and
                        rsi < (100 - rsi_recover) and rsi > (100 - rsi_recover - 15) and rsi < rsi_prev):
                    continue
                entry = close
                stop = entry + atr_mult * atr
                risk = stop - entry

            last_sig = i
            for tr in targets:
                result = _fast_evaluate(arr, i, direction, entry, stop, risk, tr, eval_window)
                if result:
                    all_results.append(result)

    return all_results


# Map signal names to their fast sweep function + direction
FAST_SWEEP_MAP = {
    "trend_pullback_short":  (_sweep_trend_pullback,  "short"),
    "trend_pullback_long":   (_sweep_trend_pullback,  "long"),
    "range_reversion_short": (_sweep_range_reversion, "short"),
    "range_reversion_long":  (_sweep_range_reversion, "long"),
    "macd_momentum_short":   (_sweep_macd_momentum,   "short"),
    "macd_momentum_long":    (_sweep_macd_momentum,   "long"),
    "rsi_rejection_short":   (_sweep_rsi_extreme,     "short"),
    "rsi_bounce_long":       (_sweep_rsi_extreme,     "long"),
}


def _eval_combo(signal_name, grid, params, targets, cooldown, eval_window,
                fast_arrs=None, dfs=None):
    """Return trades for ONE parameter combo. Uses the fast vectorized sweep when
    the signal has one AND fast_arrs is supplied; otherwise builds the signal from
    its `factory` and runs the generic (slower) backtest over `dfs`. This is what
    lets NEW signals be optimized/validated without a hand-written numpy sweep.
    """
    if signal_name in FAST_SWEEP_MAP and fast_arrs is not None:
        sweep_fn, direction = FAST_SWEEP_MAP[signal_name]
        return sweep_fn(fast_arrs, direction, params, targets, cooldown, eval_window)
    factory = grid.get("factory")
    if factory is None or dfs is None:
        return []
    sig_fn = factory(**params)
    trades = []
    for symbol, df in dfs.items():
        trades.extend(run_backtest(df, symbol, {signal_name: sig_fn}, targets, cooldown, eval_window))
    return trades


def run_param_sweep(dfs, signal_name, grid, cooldown=12, eval_window=48, min_trades=15):
    """Sweep all parameter combinations. Fast numpy sweep when available, else the
    generic factory path (for signals without a vectorized sweep)."""
    param_names = list(grid["params"].keys())
    param_values = [grid["params"][k] for k in param_names]
    targets = grid["targets"]

    total_combos = 1
    for v in param_values:
        total_combos *= len(v)

    print(f"\n  Sweeping {signal_name}: {total_combos} param combos × {len(targets)} targets")

    has_fast = signal_name in FAST_SWEEP_MAP
    if not has_fast and grid.get("factory") is None:
        print(f"  No fast sweep or factory for '{signal_name}', skipping.")
        return []
    if not has_fast:
        print(f"  (slow factory path — no vectorized sweep for '{signal_name}')")

    # Fast path pre-computes numpy arrays; slow path works directly on DataFrames.
    arrs = [_precompute_arrays(df) for df in dfs.values()] if has_fast else None

    results = []
    tested = 0

    for values in product(*param_values):
        params = dict(zip(param_names, values))

        # Skip invalid RSI ranges
        if "rsi_lo" in params and "rsi_hi" in params and params["rsi_lo"] >= params["rsi_hi"]:
            continue

        all_trades = _eval_combo(signal_name, grid, params, targets,
                                 cooldown, eval_window, fast_arrs=arrs, dfs=dfs)

        # Group by target and record stats
        for tr in targets:
            tr_trades = [t for t in all_trades if t["target_r"] == tr]
            if len(tr_trades) < min_trades:
                continue
            s = compute_stats(tr_trades)
            results.append({
                "params": dict(params),
                "target_r": tr,
                "stats": s,
                "n": s["n"],
            })

        tested += 1
        if tested % 500 == 0:
            print(f"    ...{tested} combos tested, {len(results)} viable")

    results.sort(key=lambda x: x["stats"]["expectancy"], reverse=True)
    print(f"  Done: {tested} combos, {len(results)} viable (>={min_trades} trades)")
    return results


def report_optimization(signal_name, results, top_n=20):
    """Report the best parameter combinations from sweep."""
    section(f"OPTIMIZATION: {signal_name}")

    if not results:
        print("  No viable parameter combinations found (need more data).")
        return

    print(f"  Top {min(top_n, len(results))} parameter combinations:\n")
    print(f"  {'#':<4s} {'Target':>7s} {'N':>5s} {'WR':>7s} {'Expect':>8s} {'PF':>6s} {'Parameters'}")
    print("  " + "─" * 90)

    for i, r in enumerate(results[:top_n], 1):
        s = r["stats"]
        params_str = ", ".join(f"{k}={v}" for k, v in r["params"].items())
        print(f"  {i:<4d} {r['target_r']:>6.2f}R {s['n']:>5d} {s['wr']:>6.1f}% "
              f"{s['expectancy']:>+7.3f} {s['pf']:>6.2f}  {params_str}")

    # Highlight the best
    best = results[0]
    bs = best["stats"]
    print(f"\n  ★ BEST FORMULA for {signal_name}:")
    print(f"    Target: {best['target_r']}R")
    print(f"    Parameters:")
    for k, v in best["params"].items():
        print(f"      {k}: {v}")
    print(f"    Results: {bs['wr']}% WR, {bs['expectancy']:+.3f} expectancy, "
          f"PF {bs['pf']}, {bs['n']} trades, avg MFE {bs['avg_mfe']}R")

    # Show parameter sensitivity — which params matter most
    if len(results) >= 20:
        print(f"\n  Parameter sensitivity (avg expectancy by value):")
        param_names = list(results[0]["params"].keys())
        for pname in param_names:
            val_stats = defaultdict(list)
            for r in results:
                val_stats[r["params"][pname]].append(r["stats"]["expectancy"])
            print(f"    {pname}:")
            for val in sorted(val_stats.keys(), key=lambda v: str(v)):
                exps = val_stats[val]
                avg = sum(exps) / len(exps)
                best_e = max(exps)
                print(f"      {str(val):<8s} → avg {avg:+.3f}, best {best_e:+.3f} ({len(exps)} combos)")


def run_full_optimization(dfs, signal_names, cooldown, eval_window, min_trades, top_n):
    """Run optimization for specified signals and produce a final summary."""
    all_bests = []

    for sig_name in signal_names:
        if sig_name not in PARAM_GRIDS:
            print(f"  No parameter grid for '{sig_name}', skipping.")
            continue
        grid = PARAM_GRIDS[sig_name]
        results = run_param_sweep(dfs, sig_name, grid, cooldown, eval_window, min_trades)
        report_optimization(sig_name, results, top_n)
        if results:
            all_bests.append((sig_name, results[0]))

    # Final summary
    if all_bests:
        section("OPTIMIZATION SUMMARY — BEST FORMULA PER SIGNAL")
        print(f"\n  {'Signal':<28s} {'Target':>7s} {'N':>5s} {'WR':>7s} {'Expect':>8s} {'PF':>6s}")
        print("  " + "─" * 65)
        all_bests.sort(key=lambda x: x[1]["stats"]["expectancy"], reverse=True)
        for sig_name, best in all_bests:
            s = best["stats"]
            print(f"  {sig_name:<28s} {best['target_r']:>6.2f}R {s['n']:>5d} {s['wr']:>6.1f}% "
                  f"{s['expectancy']:>+7.3f} {s['pf']:>6.2f}")

        print(f"\n  ⚠ Run --validate to confirm these aren't overfit before integrating.")


# ─── Validation Engine (train/test split + robustness) ───────────────────────

def _split_arrays(arr, split_ratio=0.6):
    """Split precomputed arrays into train/test at split_ratio."""
    n = arr["n"]
    split_idx = int(n * split_ratio)
    train, test = {}, {}
    for key, val in arr.items():
        if key == "n":
            train["n"] = split_idx
            test["n"] = n - split_idx
        elif isinstance(val, np.ndarray):
            train[key] = val[:split_idx]
            test[key] = val[split_idx:]
        else:
            train[key] = val
            test[key] = val
    return train, test


def _compute_robustness(results, param_grid):
    """Score how robust the top result is — do neighboring params also work?"""
    if not results:
        return 0.0, {}

    best = results[0]
    best_params = best["params"]
    best_target = best["target_r"]

    param_names = list(param_grid["params"].keys())
    param_values = {k: param_grid["params"][k] for k in param_names}

    # For each param, check if ±1 step also has positive expectancy
    neighbor_results = {}
    total_neighbors = 0
    positive_neighbors = 0

    for pname in param_names:
        vals = param_values[pname]
        best_val = best_params[pname]
        if best_val not in vals:
            continue
        idx = vals.index(best_val)

        neighbors = []
        for offset in [-1, 1]:
            ni = idx + offset
            if 0 <= ni < len(vals):
                neighbor_val = vals[ni]
                # Find this combo in results
                for r in results:
                    if r["target_r"] != best_target:
                        continue
                    match = True
                    for pk, pv in best_params.items():
                        if pk == pname:
                            if r["params"][pk] != neighbor_val:
                                match = False
                                break
                        else:
                            if r["params"][pk] != pv:
                                match = False
                                break
                    if match:
                        neighbors.append((neighbor_val, r["stats"]["expectancy"]))
                        total_neighbors += 1
                        if r["stats"]["expectancy"] > 0:
                            positive_neighbors += 1
                        break

        neighbor_results[pname] = neighbors

    robustness = positive_neighbors / total_neighbors if total_neighbors > 0 else 0
    return robustness, neighbor_results


def run_validation(dfs_all, signal_names, cooldown, eval_window, min_trades, split_ratio=0.6):
    """Train/test split validation: optimize on train, evaluate on test."""
    section("VALIDATION — TRAIN/TEST SPLIT")
    print(f"  Split: {split_ratio*100:.0f}% train / {(1-split_ratio)*100:.0f}% test")
    print(f"  If test expectancy drops to 0 or negative → overfit, discard.\n")

    # Split all DataFrames — numpy arrays for the fast path, DataFrame slices for
    # the generic slow (factory) path. Slices keep the indicators already computed
    # on the full history.
    train_arrs, test_arrs = [], []
    train_dfs, test_dfs = {}, {}
    for sym, df in dfs_all.items():
        arr = _precompute_arrays(df)
        train, test = _split_arrays(arr, split_ratio)
        train_arrs.append(train)
        test_arrs.append(test)
        split_idx = int(len(df) * split_ratio)
        train_dfs[sym] = df.iloc[:split_idx].reset_index(drop=True)
        test_dfs[sym] = df.iloc[split_idx:].reset_index(drop=True)

    validated = []

    for sig_name in signal_names:
        if sig_name not in PARAM_GRIDS:
            continue
        grid = PARAM_GRIDS[sig_name]
        has_fast = sig_name in FAST_SWEEP_MAP
        if not has_fast and grid.get("factory") is None:
            continue

        param_names = list(grid["params"].keys())
        param_values = [grid["params"][k] for k in param_names]
        targets = grid["targets"]

        # === TRAIN: find best params ===
        train_results = []
        for values in product(*param_values):
            params = dict(zip(param_names, values))
            if "rsi_lo" in params and "rsi_hi" in params and params["rsi_lo"] >= params["rsi_hi"]:
                continue
            trades = _eval_combo(sig_name, grid, params, targets, cooldown, eval_window,
                                 fast_arrs=train_arrs if has_fast else None, dfs=train_dfs)
            for tr in targets:
                tr_trades = [t for t in trades if t["target_r"] == tr]
                if len(tr_trades) < max(8, min_trades // 2):  # lower bar for train half
                    continue
                s = compute_stats(tr_trades)
                train_results.append({"params": dict(params), "target_r": tr, "stats": s})

        if not train_results:
            print(f"  {sig_name}: no viable combos on train set, skipping.")
            continue

        train_results.sort(key=lambda x: x["stats"]["expectancy"], reverse=True)

        # Take top 5 from train, test each on test set
        print(f"  {sig_name}:")
        print(f"    {'#':<4s} {'Target':>7s} {'Train WR':>9s} {'Train Exp':>10s} "
              f"{'Test WR':>8s} {'Test Exp':>9s} {'Test N':>7s} {'Verdict':>10s}")
        print(f"    {'─' * 70}")

        for rank, train_r in enumerate(train_results[:5], 1):
            params = train_r["params"]
            tr = train_r["target_r"]
            ts = train_r["stats"]

            # === TEST: evaluate same params on unseen data ===
            test_trades = _eval_combo(sig_name, grid, params, [tr], cooldown, eval_window,
                                      fast_arrs=test_arrs if has_fast else None, dfs=test_dfs)
            test_s = compute_stats(test_trades)

            # Verdict
            if test_s["n"] < 5:
                verdict = "LOW DATA"
            elif test_s["expectancy"] > 0 and test_s["pf"] > 1.0:
                verdict = "✓ PASS"
            elif test_s["expectancy"] > -0.1:
                verdict = "~ MARGINAL"
            else:
                verdict = "✗ OVERFIT"

            print(f"    {rank:<4d} {tr:>6.2f}R {ts['wr']:>8.1f}% {ts['expectancy']:>+9.3f} "
                  f"{test_s['wr']:>7.1f}% {test_s['expectancy']:>+8.3f} {test_s['n']:>7d} {verdict:>10s}")

            if "PASS" in verdict:
                # Compute robustness
                robustness, neighbors = _compute_robustness(train_results, grid)
                validated.append({
                    "signal": sig_name,
                    "params": params,
                    "target_r": tr,
                    "train": ts,
                    "test": test_s,
                    "robustness": robustness,
                    "neighbors": neighbors,
                })

        print()

    # === Final validated summary ===
    section("VALIDATED FORMULAS (passed train/test + positive expectancy)")

    if not validated:
        print("  No formulas passed validation. All were overfit or insufficient data.")
        print("  Try: more symbols (--symbols), or longer history (--interval 240).")
        return validated

    # Deduplicate: keep best test expectancy per signal
    best_per_signal = {}
    for v in validated:
        key = v["signal"]
        if key not in best_per_signal or v["test"]["expectancy"] > best_per_signal[key]["test"]["expectancy"]:
            best_per_signal[key] = v

    print(f"\n  {'Signal':<28s} {'Target':>7s} {'Train':>10s} {'Test':>10s} {'Test N':>7s} {'Robust':>7s} {'Status'}")
    print("  " + "─" * 80)

    for sig_name, v in sorted(best_per_signal.items(), key=lambda x: x[1]["test"]["expectancy"], reverse=True):
        robust_pct = f"{v['robustness']*100:.0f}%"
        status = "★ STRONG" if v["test"]["expectancy"] > 0.1 and v["robustness"] > 0.5 else "✓ OK"
        print(f"  {sig_name:<28s} {v['target_r']:>6.2f}R "
              f"{v['train']['expectancy']:>+9.3f} {v['test']['expectancy']:>+9.3f} "
              f"{v['test']['n']:>7d} {robust_pct:>7s} {status}")

    # Show robustness details for top formulas
    for sig_name, v in sorted(best_per_signal.items(), key=lambda x: x[1]["test"]["expectancy"], reverse=True)[:3]:
        if v["neighbors"]:
            print(f"\n  Robustness detail — {sig_name}:")
            print(f"    Best params: {v['params']}")
            for pname, nbrs in v["neighbors"].items():
                if nbrs:
                    nbr_str = ", ".join(f"{val}→{exp:+.3f}" for val, exp in nbrs)
                    print(f"    {pname}: neighbors [{nbr_str}]")

    print(f"\n  Only ★ STRONG or ✓ OK formulas should be integrated into the screener.")
    return validated


def _slice_arrays(arr, start_frac, end_frac):
    """Slice precomputed arrays to the [start_frac, end_frac) index window."""
    n = arr["n"]
    a, b = int(n * start_frac), int(n * end_frac)
    out = {}
    for key, val in arr.items():
        if key == "n":
            out["n"] = max(0, b - a)
        elif isinstance(val, np.ndarray):
            out[key] = val[a:b]
        else:
            out[key] = val
    return out


def run_walkforward(dfs_all, signal_names, cooldown, eval_window, min_trades,
                    n_windows=4, train_frac=0.5):
    """Walk-forward validation: slide successive out-of-sample TEST windows across
    the tail of the data, each preceded by an expanding TRAIN window. A signal is
    ROBUST only if it holds up across MOST windows — a stronger bar than a single
    60/40 split, which can get lucky on one cut.

    For window w: train on [0, train_frac + w·step), test on the next step-slice.
    Best train params (by expectancy) are carried to that window's test slice.
    Uses the fast sweep when available, else the generic factory path.
    """
    section("WALK-FORWARD VALIDATION (rolling out-of-sample windows)")
    print(f"  {n_windows} windows, expanding train from {train_frac*100:.0f}%. "
          f"A signal must PASS a majority of windows to be considered robust.\n")

    precomp = {sym: _precompute_arrays(df) for sym, df in dfs_all.items()}
    step = (1.0 - train_frac) / n_windows
    summary = []

    for sig_name in signal_names:
        if sig_name not in PARAM_GRIDS:
            continue
        grid = PARAM_GRIDS[sig_name]
        has_fast = sig_name in FAST_SWEEP_MAP
        if not has_fast and grid.get("factory") is None:
            continue
        param_names = list(grid["params"].keys())
        param_values = [grid["params"][k] for k in param_names]
        targets = grid["targets"]

        window_rows = []
        for w in range(n_windows):
            tr_end = train_frac + step * w
            te_end = train_frac + step * (w + 1)

            # Build this window's train/test data (both representations).
            train_arrs = [_slice_arrays(precomp[s], 0.0, tr_end) for s in dfs_all]
            test_arrs = [_slice_arrays(precomp[s], tr_end, te_end) for s in dfs_all]
            train_dfs, test_dfs = {}, {}
            for sym, df in dfs_all.items():
                n = len(df)
                train_dfs[sym] = df.iloc[:int(n * tr_end)].reset_index(drop=True)
                test_dfs[sym] = df.iloc[int(n * tr_end):int(n * te_end)].reset_index(drop=True)

            # Optimize on train.
            best = None
            for values in product(*param_values):
                params = dict(zip(param_names, values))
                if "rsi_lo" in params and "rsi_hi" in params and params["rsi_lo"] >= params["rsi_hi"]:
                    continue
                trades = _eval_combo(sig_name, grid, params, targets, cooldown, eval_window,
                                     fast_arrs=train_arrs if has_fast else None, dfs=train_dfs)
                for tr in targets:
                    tt = [t for t in trades if t["target_r"] == tr]
                    if len(tt) < max(6, min_trades // 2):
                        continue
                    s = compute_stats(tt)
                    if best is None or s["expectancy"] > best["stats"]["expectancy"]:
                        best = {"params": dict(params), "target_r": tr, "stats": s}

            if best is None:
                window_rows.append(None)
                continue

            # Test the winning params on the unseen window.
            tt = _eval_combo(sig_name, grid, best["params"], [best["target_r"]],
                             cooldown, eval_window,
                             fast_arrs=test_arrs if has_fast else None, dfs=test_dfs)
            ts = compute_stats(tt)
            passed = ts["n"] >= 5 and ts["expectancy"] > 0 and ts["pf"] > 1.0
            window_rows.append({"train": best, "test": ts, "passed": passed})

        valid = [v for v in window_rows if v]
        n_pass = sum(1 for v in valid if v["passed"])
        avg_test_exp = (sum(v["test"]["expectancy"] for v in valid) / len(valid)) if valid else 0.0

        print(f"  {sig_name}:  passed {n_pass}/{len(valid)} windows, "
              f"avg test expectancy {avg_test_exp:+.3f}R")
        for w, v in enumerate(window_rows, 1):
            if v is None:
                print(f"    window {w}: (no viable train combos)")
            else:
                mark = "✓" if v["passed"] else "✗"
                print(f"    window {w}: {mark} test {v['test']['n']}t "
                      f"WR {v['test']['wr']:.0f}% exp {v['test']['expectancy']:+.3f} "
                      f"PF {v['test']['pf']}  (target {v['train']['target_r']}R)")
        summary.append((sig_name, n_pass, len(valid), avg_test_exp))

    section("WALK-FORWARD SUMMARY (robust across windows)")
    if not summary:
        print("  No signals evaluated.")
        return summary
    print(f"  {'Signal':<28s} {'Pass/Win':>9s} {'AvgTestExp':>11s}  {'Robust?'}")
    print("  " + "─" * 60)
    for sig_name, n_pass, n_win, avg in sorted(summary, key=lambda x: x[3], reverse=True):
        robust = n_win > 0 and n_pass >= (n_win + 1) // 2 and avg > 0
        print(f"  {sig_name:<28s} {f'{n_pass}/{n_win}':>9s} {avg:>+10.3f}  "
              f"{'★ ROBUST' if robust else '—'}")
    print(f"\n  Only signals ROBUST across a majority of windows should go live.")
    return summary


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Historical strategy backtester")
    parser.add_argument("--symbols", type=str, default=",".join(DEFAULT_SYMBOLS),
                        help="Comma-separated symbols (default: top 6)")
    parser.add_argument("--interval", type=str, default="60",
                        help="Kline interval: 15, 60, 240, D (default: 60)")
    parser.add_argument("--limit", type=int, default=1000,
                        help="Candles to fetch per symbol (default: 1000, max 1000)")
    parser.add_argument("--signals", type=str, default="",
                        help="Comma-separated signal names to test (default: all)")
    parser.add_argument("--target-sweep", action="store_true",
                        help="Test multiple target R:R levels")
    parser.add_argument("--targets", type=str, default="0.5,0.75,1.0,1.5",
                        help="Comma-separated target R:R values (default: 0.5,0.75,1.0,1.5)")
    parser.add_argument("--cooldown", type=int, default=12,
                        help="Min candles between signals (default: 12)")
    parser.add_argument("--eval-window", type=int, default=48,
                        help="Forward candles to evaluate (default: 48)")
    parser.add_argument("--no-cache", action="store_true",
                        help="Force refetch from Bybit (ignore cache)")
    parser.add_argument("--optimize", type=str, default="",
                        help="Run parameter sweep. Comma-separated signal names, or 'all' for all grids")
    parser.add_argument("--validate", type=str, default="",
                        help="Train/test validation. Comma-separated signal names, or 'all'")
    parser.add_argument("--split", type=float, default=0.6,
                        help="Train/test split ratio (default: 0.6 = 60%% train)")
    parser.add_argument("--min-trades", type=int, default=15,
                        help="Min trades for optimize results (default: 15)")
    parser.add_argument("--top-n", type=int, default=20,
                        help="Show top N results per signal in optimize (default: 20)")
    parser.add_argument("--full", action="store_true",
                        help="Full pipeline: validate on 4h + 1h (15 symbols, fresh data) + eval combo analysis")
    parser.add_argument("--walkforward", type=str, default="",
                        help="Walk-forward validation across rolling windows. Signal names or 'all'")
    parser.add_argument("--wf-windows", type=int, default=4,
                        help="Number of walk-forward windows (default: 4)")
    args = parser.parse_args()

    # ── Full pipeline mode: validate both TFs + eval combo ──
    if args.full:
        full_symbols = ",".join(EXPANDED_SYMBOLS)
        all_sigs = list(PARAM_GRIDS.keys())

        print("\n" + "=" * 80)
        print("  FULL BACKTEST PIPELINE")
        print("  Step 1/3: Validate on 4h (167 days, 15 symbols, fresh data)")
        print("  Step 2/3: Validate on 1h (42 days, 15 symbols, fresh data)")
        print("  Step 3/3: Analyze Claude's eval history (combo filters)")
        print("=" * 80)

        # Step 1: Validate on 4h
        section("STEP 1/3 — VALIDATE ON 4h (167 DAYS)")
        dfs_4h = {}
        for sym in EXPANDED_SYMBOLS:
            candles = fetch_klines(sym, "240", 1000, use_cache=False)
            if candles and len(candles) >= 100:
                dfs_4h[sym] = compute_indicators_df(candles)
        if dfs_4h:
            results_4h = run_validation(dfs_4h, all_sigs, args.cooldown, args.eval_window,
                                        args.min_trades, args.split)
        else:
            print("  No data for 4h validation.")
            results_4h = []

        # Step 2: Validate on 1h
        section("STEP 2/3 — VALIDATE ON 1h (42 DAYS)")
        dfs_1h = {}
        for sym in EXPANDED_SYMBOLS:
            candles = fetch_klines(sym, "60", 1000, use_cache=False)
            if candles and len(candles) >= 100:
                dfs_1h[sym] = compute_indicators_df(candles)
        if dfs_1h:
            results_1h = run_validation(dfs_1h, all_sigs, args.cooldown, args.eval_window,
                                        args.min_trades, args.split)
        else:
            print("  No data for 1h validation.")
            results_1h = []

        # Step 3: Run eval combo analysis
        section("STEP 3/3 — CLAUDE EVAL COMBO ANALYSIS")
        try:
            from backtester import (load_all_evals, load_setup_lookup, merge_trades,
                                    report_baseline, report_combo, report_findings,
                                    report_version_segments)
            trades = load_all_evals()
            setup_lookup = load_setup_lookup()
            trades = merge_trades(trades, setup_lookup)
            if trades:
                print(f"  Loaded {len(trades)} evaluated trades.")
                report_baseline(trades)
                report_combo(trades)
                report_version_segments(trades)  # v11.3 before/after segment + verdict
            else:
                print("  No evaluated trades found.")
        except Exception as e:
            print(f"  Could not run eval combo analysis: {e}")

        # Final cross-TF summary
        section("CROSS-TF SUMMARY")
        passed_4h = {v["signal"] for v in results_4h} if results_4h else set()
        passed_1h = {v["signal"] for v in results_1h} if results_1h else set()
        both = passed_4h & passed_1h
        only_4h = passed_4h - passed_1h
        only_1h = passed_1h - passed_4h

        if both:
            print(f"\n  ★ CONFIRMED on BOTH timeframes (safe to integrate):")
            for sig in sorted(both):
                print(f"    - {sig}")
        if only_4h:
            print(f"\n  ⚠ 4h only (use with caution):")
            for sig in sorted(only_4h):
                print(f"    - {sig}")
        if only_1h:
            print(f"\n  ⚠ 1h only (use with caution):")
            for sig in sorted(only_1h):
                print(f"    - {sig}")
        if not both and not only_4h and not only_1h:
            print("\n  No formulas passed validation on either timeframe.")

        print()
        sys.exit(0)

    symbols = [s.strip().upper() for s in args.symbols.split(",")]
    target_rs = [float(t) for t in args.targets.split(",")]
    interval = args.interval
    limit = min(args.limit, 1000)

    # Filter signals if specified
    if args.signals:
        sig_names = [s.strip() for s in args.signals.split(",")]
        signals_to_test = {}
        for name in sig_names:
            # Match partial names
            for full_name, fn in ALL_SIGNALS.items():
                if name in full_name:
                    signals_to_test[full_name] = fn
        if not signals_to_test:
            print(f"  No signals matched '{args.signals}'")
            print(f"  Available: {', '.join(ALL_SIGNALS.keys())}")
            sys.exit(1)
    else:
        signals_to_test = ALL_SIGNALS

    tf_label = INTERVAL_LABELS.get(interval, interval)
    print(f"\n  Historical Backtester")
    print(f"  Symbols:    {', '.join(symbols)}")
    print(f"  Timeframe:  {tf_label}")
    print(f"  Candles:    {limit} per symbol")
    print(f"  Signals:    {len(signals_to_test)} rules")
    print(f"  Targets:    {', '.join(f'{t}R' for t in target_rs)}")
    print(f"  Cooldown:   {args.cooldown} candles")
    print(f"  Eval window:{args.eval_window} candles")
    print()

    # ── Optimize mode: parameter sweep (fetch data + sweep, then exit) ──
    if args.optimize:
        if args.optimize.lower() == "all":
            opt_signals = list(PARAM_GRIDS.keys())
        else:
            opt_signals = []
            for name in args.optimize.split(","):
                name = name.strip()
                for grid_name in PARAM_GRIDS:
                    if name in grid_name:
                        opt_signals.append(grid_name)
            if not opt_signals:
                print(f"  No grids matched '{args.optimize}'")
                print(f"  Available: {', '.join(PARAM_GRIDS.keys())}")
                sys.exit(1)

        # Build {symbol: df} dict for sweep
        dfs = {}
        for sym in symbols:
            candles = fetch_klines(sym, interval, limit, use_cache=not args.no_cache)
            if candles and len(candles) >= 100:
                dfs[sym] = compute_indicators_df(candles)
        if not dfs:
            print("  No valid data for optimization.")
            sys.exit(1)

        run_full_optimization(dfs, opt_signals, args.cooldown, args.eval_window,
                              args.min_trades, args.top_n)
        print()
        sys.exit(0)

    # ── Validate mode: train/test split ──
    if args.validate:
        if args.validate.lower() == "all":
            val_signals = list(PARAM_GRIDS.keys())
        else:
            val_signals = []
            for name in args.validate.split(","):
                name = name.strip()
                for grid_name in PARAM_GRIDS:
                    if name in grid_name:
                        val_signals.append(grid_name)
            if not val_signals:
                print(f"  No grids matched '{args.validate}'")
                sys.exit(1)

        dfs = {}
        for sym in symbols:
            candles = fetch_klines(sym, interval, limit, use_cache=not args.no_cache)
            if candles and len(candles) >= 100:
                dfs[sym] = compute_indicators_df(candles)
        if not dfs:
            print("  No valid data for validation.")
            sys.exit(1)

        run_validation(dfs, val_signals, args.cooldown, args.eval_window,
                       args.min_trades, args.split)
        print()
        sys.exit(0)

    # ── Walk-forward mode: rolling out-of-sample windows ──
    if args.walkforward:
        if args.walkforward.lower() == "all":
            wf_signals = list(PARAM_GRIDS.keys())
        else:
            wf_signals = []
            for name in args.walkforward.split(","):
                name = name.strip()
                for grid_name in PARAM_GRIDS:
                    if name in grid_name:
                        wf_signals.append(grid_name)
            if not wf_signals:
                print(f"  No grids matched '{args.walkforward}'")
                sys.exit(1)

        dfs = {}
        for sym in symbols:
            candles = fetch_klines(sym, interval, limit, use_cache=not args.no_cache)
            if candles and len(candles) >= 100:
                dfs[sym] = compute_indicators_df(candles)
        if not dfs:
            print("  No valid data for walk-forward.")
            sys.exit(1)

        run_walkforward(dfs, wf_signals, args.cooldown, args.eval_window,
                        args.min_trades, n_windows=args.wf_windows, train_frac=args.split)
        print()
        sys.exit(0)

    # ── Normal mode: fetch + fixed signal testing ──
    all_trades = []
    for sym in symbols:
        candles = fetch_klines(sym, interval, limit, use_cache=not args.no_cache)
        if not candles or len(candles) < 100:
            print(f"    Skipping {sym}: insufficient data ({len(candles)} candles)")
            continue

        df = compute_indicators_df(candles)
        trades = run_backtest(df, sym, signals_to_test, target_rs,
                              cooldown=args.cooldown, eval_window=args.eval_window)
        all_trades.extend(trades)
        print(f"    {sym}: {len([t for t in trades if t['target_r'] == target_rs[0]])} signals fired")

    if not all_trades:
        print("\n  No signals fired! Try different symbols or loosen signal rules.")
        sys.exit(0)

    unique_signals = len(set((t["signal"], t["candle_idx"], t["symbol"]) for t in all_trades))
    print(f"\n  Total: {unique_signals} unique signals × {len(target_rs)} target levels "
          f"= {len(all_trades)} trade evaluations")

    # Reports
    # Use first target_r as the "primary" for single-target reports
    primary_tr = target_rs[0] if len(target_rs) == 1 else None

    report_by_signal(all_trades, primary_tr)
    report_by_symbol(all_trades, primary_tr)

    if len(target_rs) > 1:
        report_target_sweep(all_trades)
        report_signal_x_target(all_trades)

    # MFE at the most useful target
    best_tr = target_rs[0]
    report_mfe_analysis(all_trades, best_tr)

    if len(target_rs) > 1:
        report_findings(all_trades, target_rs)

    print()


if __name__ == "__main__":
    main()
