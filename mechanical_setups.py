"""Pure-Python mechanical setup constructor.

Turns fired, backtest-validated signals (from
`bybit_data.py::_check_validated_signals`) into COMPLETE trade setups
(entry/stop/T1/T2 + rank/confidence/confluence) with zero dependency on Claude.
This is the PRIMARY source of setups in the mechanical-primary architecture;
Claude runs in shadow for comparison.

Output dicts match the schema in `analyzer/prompts.py` so `main.py::enforce_setups`,
`delivery`, and `weekly_eval` consume them unchanged. Extra keys added:
`source="mechanical"`, `signal_name`, `signal_tf`, `signal_expectancy`.

Ranking/confidence are deterministic — driven by each signal's validated
out-of-sample expectancy (not a model's opinion).
"""

import signal_levels as sl

# Validated out-of-sample expectancy (R) per (signal, timeframe), from the Jul 2026
# re-validation baked into bybit_data.py::_check_validated_signals docstrings/labels.
# Keep in sync when signals are re-validated monthly via `backtest`.
EXPECTANCY = {
    ("rsi_rejection_short", "1h"): 0.17,    # Jul 29 re-run: 1h-only (4h dropped)
    ("trend_pullback_short", "4h"): 0.28,
    ("failed_breakout_short", "4h"): 0.12,   # Phase 3, validated 4h-only (N=75)
    ("liquidity_sweep_long", "1h"): 0.08,    # Jul 29: confirmed both TFs, 100% robust
    ("liquidity_sweep_long", "4h"): 0.04,
    ("rsi_bounce_long", "4h"): 0.11,         # 2026-08-20: WATCH tier — gross +0.108R/N20, net-marginal
}

# Map a signal name to the canonical setup_type (must be in main.VALID_SETUP_TYPES).
SETUP_TYPE = {
    "rsi_rejection_short": "range_mean_reversion",  # fading an RSI exhaustion extreme
    "trend_pullback_short": "trend_pullback",
    "failed_breakout_short": "failed_breakout",
    "liquidity_sweep_long": "liquidity_sweep",
    "rsi_bounce_long": "range_mean_reversion",   # oversold-bounce mean reversion
}

# Canonical reasoning rule per signal (must be in config.CANONICAL_RULES).
SETUP_RULE = {
    "rsi_rejection_short": "setup8_exhaustion",
    "trend_pullback_short": "trend_pullback",
    "failed_breakout_short": "liquidity_sweep",  # a failed breakout is a swept level
    "liquidity_sweep_long": "liquidity_sweep",
    "rsi_bounce_long": "range_reversion",
}

VOLUME_CONFIRM_RATIO = 1.5


def _expectancy(signal_name, tf):
    return EXPECTANCY.get((signal_name, tf), 0.0)


def _tf_confluence(tech, direction):
    """Canonical multi-TF confluence: how many of the 4 timeframes (15m/1h/4h/1D)
    have a trend that AGREES with the trade direction. This is the same semantic
    Claude self-reports, so mechanical and Claude confluence are comparable, and
    the 4/4-is-worst gate applies identically. NOT manufactured from signal count
    (that would inflate to 4/4 — the historically worst bucket).
    """
    tfs = tech.get("timeframes", {}) or {}
    want = "bullish" if direction == "long" else "bearish"
    count = sum(1 for label in ("15m", "1h", "4h", "1D")
                if (tfs.get(label) or {}).get("trend") == want)
    return max(1, min(4, count))


def _confidence(expectancy, confluence):
    if expectancy >= 0.5 and confluence >= 3:
        return "high"
    if expectancy >= 0.25:
        return "medium"
    return "low"


def _build_one(tech, direction, group, regime, interest_scores):
    """Build one setup dict from all same-direction fired signals for a symbol.

    The highest-expectancy fired signal is the anchor; its timeframe supplies the
    price/ATR used for level math. Returns None if the anchor TF lacks usable
    price/ATR (can't place a stop).
    """
    symbol = tech.get("symbol")
    # Anchor = highest validated expectancy.
    anchor = max(group, key=lambda s: _expectancy(s.get("signal"), s.get("tf")))
    signal_name = anchor.get("signal")
    signal_tf = anchor.get("tf")
    expectancy = _expectancy(signal_name, signal_tf)

    tfs = tech.get("timeframes", {}) or {}
    tf_data = tfs.get(signal_tf) or {}
    price = tf_data.get("current_price")
    atr = tf_data.get("atr_14")
    if price is None or not atr or atr <= 0:
        return None

    entry_low, entry_high = sl.entry_zone(price, atr)
    # Prefer an explicit structural stop_price when the signal carries one
    # (e.g. failed_breakout's stop at the fired candle's high); else ATR-multiple.
    if anchor.get("stop_price") is not None:
        stop = float(anchor["stop_price"])
    else:
        stop = sl.stop_from_atr(price, atr, anchor.get("stop_atr", 1.5), direction)
    risk = abs(price - stop)
    if risk <= 0:
        return None

    target_2 = sl.target_from_r(price, risk, anchor.get("target_r", 1.5), direction)

    # Structural candidate levels for T1 (in the anchor TF).
    levels = [
        tf_data.get("swing_high"), tf_data.get("swing_low"),
        tf_data.get("ema_20"), tf_data.get("ema_50"),
        tf_data.get("high_20"), tf_data.get("low_20"),
    ]
    target_1, predicted_rr = sl.nearest_structural_target(price, risk, direction, levels)

    confluence = _tf_confluence(tech, direction)
    vol_ratio = tf_data.get("volume_spike_ratio")
    volume_confirmed = bool(vol_ratio is not None and vol_ratio > VOLUME_CONFIRM_RATIO)

    return {
        "symbol": symbol,
        "direction": direction,
        "timeframe": "scalp" if signal_tf == "1h" else "intraday",
        "setup_type": SETUP_TYPE.get(signal_name, "other"),
        "entry_low": entry_low,
        "entry_high": entry_high,
        "stop_loss": stop,
        "target_1": target_1,
        "target_2": target_2,
        "predicted_rr": predicted_rr,
        "confidence": _confidence(expectancy, confluence),
        "tf_confluence": confluence,
        "volume_confirmed": volume_confirmed,
        "reasoning": {
            "rules_applied": ["validated_signal", SETUP_RULE.get(signal_name, "trend_pullback")],
            "key_factor": f"{signal_name} on {signal_tf}: {anchor.get('indicators', '')}",
        },
        # Mechanical-path instrumentation.
        # tier: "execute" (default) → real edge, gated + delivered + counted.
        #       "watch"             → gross-positive/net-marginal (or gate-rejected) signal;
        #                             surfaced + paper-tracked only, never in the edge book.
        "tier": anchor.get("tier", "execute"),
        "source": "mechanical",
        "signal_name": signal_name,
        "signal_tf": signal_tf,
        "signal_expectancy": expectancy,
        "regime": regime,
        "interest_score": (interest_scores or {}).get(symbol),
    }


def build_mechanical_setups(market):
    """Construct all mechanical setups for a scan. Ranked 1..N by validated
    expectancy then confluence. Does NOT apply the hard gates — call
    main.enforce_setups() on the result for that (same as the Claude path).
    """
    regime_info = market.get("market_regime") or {}
    regime = regime_info.get("regime", "neutral")
    interest_scores = market.get("interest_scores") or {}

    setups = []
    for tech in market.get("technicals", []) or []:
        sigs = tech.get("validated_signals") or []
        if not sigs:
            continue
        by_dir = {}
        for s in sigs:
            by_dir.setdefault(s.get("direction"), []).append(s)
        for direction, group in by_dir.items():
            if direction not in ("long", "short"):
                continue
            setup = _build_one(tech, direction, group, regime, interest_scores)
            if setup:
                setups.append(setup)

    # Deterministic rank: highest validated expectancy first, then confluence.
    setups.sort(key=lambda s: (s.get("signal_expectancy", 0.0), s.get("tf_confluence", 0)),
                reverse=True)
    for i, s in enumerate(setups, 1):
        s["rank"] = i

    return setups
