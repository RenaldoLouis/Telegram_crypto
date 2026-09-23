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

import config
import signal_levels as sl

# Ranking score per (signal, timeframe): the out-of-sample (TEST) profitable% from the
# 2026-09-23 unified backtest (`unified_backtest.py`, exact live trade model, net of cost),
# expressed as a fraction. Replaces the pre-v13 GROSS expectancy table, which came from a
# backtester that simulated a different trade (8-day hold, no costs, static target).
# Kept under the key name `signal_expectancy` for schema compatibility — it is a HIT RATE.
# Re-derive from logs/backtest_reports/unified_*.md after each harness run.
EXPECTANCY = {
    ("range_reversion_short", "4h"): 0.66,   # vol_spike>=1.5 gate baked in: test n=41 65.9% / -0.04R (all-period 75% / +0.19R)
    ("range_reversion_long", "4h"): 0.73,    # n=11 test — thin
    ("failed_breakout_short", "4h"): 0.545,  # n=112 test
    ("trend_pullback_short", "4h"): 0.526,   # n=152 test
    ("liquidity_sweep_long", "1h"): 0.51,    # n=341 test
    ("rsi_bounce_long", "4h"): 0.51,         # n=96 test
}

# Map a signal name to the canonical setup_type (must be in main.VALID_SETUP_TYPES).
SETUP_TYPE = {
    "rsi_rejection_short": "range_mean_reversion",  # fading an RSI exhaustion extreme
    "trend_pullback_short": "trend_pullback",
    "failed_breakout_short": "failed_breakout",
    "liquidity_sweep_long": "liquidity_sweep",
    "rsi_bounce_long": "range_mean_reversion",   # oversold-bounce mean reversion
    "range_reversion_short": "range_mean_reversion",
    "range_reversion_long": "range_mean_reversion",
}

# Canonical reasoning rule per signal (must be in config.CANONICAL_RULES).
SETUP_RULE = {
    "rsi_rejection_short": "setup8_exhaustion",
    "trend_pullback_short": "trend_pullback",
    "failed_breakout_short": "liquidity_sweep",  # a failed breakout is a swept level
    "liquidity_sweep_long": "liquidity_sweep",
    "rsi_bounce_long": "range_reversion",
    "range_reversion_short": "range_reversion",
    "range_reversion_long": "range_reversion",
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


def _confidence(hit_rate, confluence):
    """Confidence from the signal's TEST hit rate (fraction) + confluence.
    high = at/above the 70% user bar with 3/4 confluence; medium = >=60%; else low."""
    if hit_rate >= 0.70 and confluence >= 3:
        return "high"
    if hit_rate >= 0.60:
        return "medium"
    return "low"


def _build_one(tech, direction, group, regime, interest_scores):
    """Build one setup dict from all same-direction fired signals for a symbol.

    The highest-expectancy fired signal is the anchor; its timeframe supplies the
    price/ATR used for level math. Returns None if the anchor TF lacks usable
    price/ATR (can't place a stop).
    """
    symbol = tech.get("symbol")
    # Anchor = highest validated expectancy — but EXECUTE signals always outrank
    # WATCH signals for anchoring: a watch co-fire with higher gross expectancy
    # must never demote an execute-worthy setup into the watch lane (e.g.
    # range_reversion_long can co-fire with liquidity_sweep_long at a swept range
    # bottom; the setup inherits the anchor's tier). Watch anchors only when the
    # whole group is watch-tier. Guard added 2026-09-10.
    exec_sigs = [s for s in group if s.get("tier", "execute") != "watch"]
    anchor_pool = exec_sigs or group
    anchor = max(anchor_pool, key=lambda s: _expectancy(s.get("signal"), s.get("tf")))
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
    max_age = getattr(config, "SIGNAL_MAX_AGE_MIN", {}) or {}
    stale = []
    for tech in market.get("technicals", []) or []:
        sigs = tech.get("validated_signals") or []
        # v13.0 freshness gate: a closed-bar signal is the validated trade only if we
        # enter at (about) the next bar's open. A scan that runs 2h after a 4h close is
        # not that trade — skip it; the scan that ran right after the close took it.
        fresh = []
        for s in sigs:
            limit = max_age.get(s.get("tf"))
            age = s.get("age_min")
            if limit is not None and age is not None and age > limit:
                stale.append(f"{tech.get('symbol')}:{s.get('signal')}@{age:.0f}m")
            else:
                fresh.append(s)
        sigs = fresh
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

    if stale:
        print(f"  [mechanical] skipped {len(stale)} stale signal(s) past SIGNAL_MAX_AGE_MIN: "
              f"{', '.join(stale[:6])}{' …' if len(stale) > 6 else ''}")

    # Deterministic rank: highest validated expectancy first, then confluence.
    setups.sort(key=lambda s: (s.get("signal_expectancy", 0.0), s.get("tf_confluence", 0)),
                reverse=True)
    for i, s in enumerate(setups, 1):
        s["rank"] = i

    return setups
