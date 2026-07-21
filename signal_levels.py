"""Shared, pure-function level math for trade construction.

Single source of truth for entry/stop/target arithmetic so the live mechanical
setup constructor (`mechanical_setups.py`) and the historical backtester
(`historical_backtester.py::evaluate_forward`) cannot drift apart. The backtester
keeps its own inline math for stability (it is validated on 237 trades); the
`test_signal_levels.py` drift-guard asserts this module matches it exactly.

All functions are pure: no I/O, no pandas, native floats in and out. Direction is
always the string "long" or "short".
"""

# T1 (partial-profit) must land at 0.75-1.0R. T2 (reward leg) carries the >=1.5R edge floor.
T1_MIN_R = 0.75
T1_MAX_R = 1.0
T1_FALLBACK_R = 0.75

# Half-width of the entry zone as a fraction of ATR. Tight on purpose: the zone must
# contain the signal price so the eval's entry-trigger fires and the mid ~= price.
ENTRY_ZONE_ATR = 0.15


def entry_zone(price, atr, half_atr=ENTRY_ZONE_ATR):
    """A tight (low, high) entry band centered on `price`.

    Symmetric so the band always contains `price` (both directions). Falls back to
    a 0.1% band if ATR is missing/zero so we never return a degenerate zone.
    """
    price = float(price)
    if atr and atr > 0:
        pad = half_atr * float(atr)
    else:
        pad = abs(price) * 0.001
    return round(price - pad, 8), round(price + pad, 8)


def stop_from_atr(price, atr, stop_atr, direction):
    """Stop placed `stop_atr` ATRs away from `price`, against the trade.

    Mirrors historical_backtester.py:200/220 (entry -/+ mult*ATR).
    """
    price, atr, stop_atr = float(price), float(atr), float(stop_atr)
    if direction == "long":
        return round(price - stop_atr * atr, 8)
    return round(price + stop_atr * atr, 8)


def target_from_r(entry, risk, target_r, direction):
    """Target at a fixed R-multiple of risk. Mirrors evaluate_forward:478-480."""
    entry, risk, target_r = float(entry), float(risk), float(target_r)
    if direction == "long":
        return round(entry + target_r * risk, 8)
    return round(entry - target_r * risk, 8)


def nearest_structural_target(entry, risk, direction, levels):
    """T1 = the nearest real structural level in the profit direction that sits
    within the 0.75-1.0R band. Falls back to a synthetic 0.75R level if none qualify.

    `levels` is any iterable of candidate prices (swing pivots, EMAs, range
    extremes); None/NaN entries are ignored. Returns (target_1, predicted_rr) where
    predicted_rr is always in [0.75, 1.0] so it passes the T1<=1.0R enforcement gate.
    """
    entry, risk = float(entry), float(risk)
    if risk <= 0:
        # Degenerate; return entry so the caller's own risk>0 guard rejects it.
        return round(entry, 8), T1_FALLBACK_R

    lo, hi = T1_MIN_R * risk, T1_MAX_R * risk
    best = None  # (distance_r, level)
    for lv in levels or []:
        if lv is None:
            continue
        try:
            lv = float(lv)
        except (TypeError, ValueError):
            continue
        if lv != lv:  # NaN
            continue
        dist = (lv - entry) if direction == "long" else (entry - lv)
        if lo <= dist <= hi:
            dist_r = dist / risk
            if best is None or dist_r < best[0]:
                best = (dist_r, lv)

    if best is not None:
        dist_r, lv = best
        return round(lv, 8), round(dist_r, 3)

    # Fallback: synthetic 0.75R level.
    if direction == "long":
        return round(entry + T1_FALLBACK_R * risk, 8), T1_FALLBACK_R
    return round(entry - T1_FALLBACK_R * risk, 8), T1_FALLBACK_R
