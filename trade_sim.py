"""Single source of truth for simulating ONE trade against forward candles.

Used by BOTH the live evaluator (`weekly_eval.py`, 15m candles after a scan) and the
unified backtester (`unified_backtest.py`, 15m candles after a closed signal bar), so
the number that validates a signal and the number that scores it live are produced by
the SAME code path. The 2026-09-23 audit found the two had drifted apart on entry
semantics, hold horizon, costs, tie-breaks and exit management — every "validated"
expectancy described a trade the live pipeline never took.

Trade model (identical everywhere):
  * ENTRY  — market order at the OPEN of the first forward candle (`candles[0]`).
             No entry zone / limit fiction: the scan fires on a CLOSED signal bar and
             the trader enters at market. If `entry_price` is given it is used as-is
             (the caller has already decided the fill).
  * STOP   — wick-based (`low <= stop` for longs, `high >= stop` for shorts).
  * T1     — partial-profit level: `t1_partial` of the position is closed there and
             the stop moves to breakeven for the remainder.
  * TRAIL  — once MFE (as of PRIOR candles — no intracandle look-ahead) reaches
             `lock_trigger_r`, the stop tightens to `+lock_stop_r`.
  * T2     — full exit of the remainder.
  * TIE    — within one candle the protective stop is checked BEFORE targets
             (conservative: a candle that touched both is scored as a stop).
  * EXPIRY — mark-to-market at the last candle's close.
  * COSTS  — round-trip taker fee + slippage (+ funding over the hold), converted to
             R via the trade's own risk_pct. See `cost_rr`.

`profitable` (the hit-rate metric the user asked for on 2026-09-23) is TRUE when the
net-of-cost blended R (partial at T1 + managed remainder) is > 0.

Pure Python, no pandas. Candles are dicts with open/high/low/close (+ optional
timestamp). Native floats in and out.
"""

import config

LOCK_TRIGGER_R = 1.0   # once prior-candle MFE reaches this ...
LOCK_STOP_R = 0.3      # ... move the stop to +this many R
T1_PARTIAL = 0.5       # fraction of the position closed at T1

# Minutes per candle for the two candle granularities we simulate on.
MINUTES = {"15": 15, "60": 60, "240": 240}


def cost_rr(risk_pct, hold_minutes=0.0):
    """Round-trip TAKER cost of one trade in R, from % of notional (legacy default).

    `risk_pct` = |entry - stop| / entry. A fixed % fee costs MORE R on a tight-stop
    trade, which is exactly the asymmetry a gross-R backtest hides.
    """
    if not getattr(config, "COST_MODEL_ENABLED", True):
        return 0.0
    rp = float(risk_pct) if risk_pct and risk_pct > 0 else config.FALLBACK_RISK_PCT
    roundtrip = 2 * (config.TAKER_FEE_PCT + config.SLIPPAGE_PCT)
    funding = config.FUNDING_PCT_PER_8H * (float(hold_minutes) / 60.0 / 8.0)
    return round((roundtrip + funding) / rp, 4)


# Fee models (fractions of notional per leg). "taker" = the legacy default: market in,
# market out, slippage both sides, whatever the exit. "maker_entry" = passive limit fill on
# entry (maker fee, no slippage) + limit take-profits (maker) while stops / breakeven /
# trail / expiry are still market exits (taker + slippage).
def _leg_costs(fee_model):
    taker = config.TAKER_FEE_PCT + config.SLIPPAGE_PCT
    maker = getattr(config, "MAKER_FEE_PCT", 0.0002)
    if fee_model == "maker_entry":
        return {"entry": maker, "target": maker, "stop": taker, "expiry": taker}
    return {"entry": taker, "target": taker, "stop": taker, "expiry": taker}


def cost_rr_legs(risk_pct, hold_minutes, fee_model, exit_reason, t1_hit, t1_partial):
    """Cost in R for one trade given how each leg actually filled."""
    if not getattr(config, "COST_MODEL_ENABLED", True):
        return 0.0
    rp = float(risk_pct) if risk_pct and risk_pct > 0 else config.FALLBACK_RISK_PCT
    legs = _leg_costs(fee_model)
    if exit_reason == "target_2":
        final = legs["target"]
    elif exit_reason == "expired":
        final = legs["expiry"]
    elif exit_reason == "target_1":      # T1 filled, remainder marked at expiry
        final = legs["expiry"]
    else:                                # stop_loss / be_stop / trail_stop
        final = legs["stop"]
    if t1_hit:
        exit_cost = t1_partial * legs["target"] + (1 - t1_partial) * final
    else:
        exit_cost = final
    funding = config.FUNDING_PCT_PER_8H * (float(hold_minutes) / 60.0 / 8.0)
    return round((legs["entry"] + exit_cost + funding) / rp, 4)


def simulate(candles, direction, stop, target_1, target_2=None, entry_price=None,
             max_candles=None, candle_minutes=15,
             lock_trigger_r=LOCK_TRIGGER_R, lock_stop_r=LOCK_STOP_R,
             t1_partial=T1_PARTIAL, trail=True, fee_model="taker"):
    """Simulate one trade. Returns a result dict, or None if `candles` is empty.

    Args:
        candles: forward candles, oldest first. Each has open/high/low/close.
        direction: "long" | "short".
        stop, target_1, target_2: absolute prices. target_2 may be None.
        entry_price: fill price; default = candles[0]["open"] (market at next open).
        max_candles: cap on how many candles the trade may live; default all.
        candle_minutes: 15 for the evaluator / unified backtest, used for funding.
        lock_trigger_r / lock_stop_r / t1_partial / trail: management parameters.
        fee_model: "taker" (default, legacy: market both ways) or "maker_entry"
            (passive entry + limit take-profits at maker fee; stops still taker).
    """
    if not candles:
        return None
    if max_candles is not None:
        candles = candles[:max_candles]
        if not candles:
            return None

    entry = float(entry_price) if entry_price is not None else float(candles[0]["open"])
    stop = float(stop)
    t1 = float(target_1) if target_1 is not None else None
    t2 = float(target_2) if target_2 is not None else None
    is_long = direction == "long"

    risk = abs(entry - stop)
    if risk <= 0:
        return None
    # Sign sanity: stop must be on the losing side, targets on the winning side.
    if is_long and not (stop < entry):
        return None
    if (not is_long) and not (stop > entry):
        return None

    def r_of(price):
        return (price - entry) / risk if is_long else (entry - price) / risk

    t1_hit = t2_hit = False
    exit_price = None
    exit_reason = None
    mfe = 0.0
    mae = 0.0
    n = 0

    for c in candles:
        n += 1
        hi, lo = float(c["high"]), float(c["low"])
        mfe_prior = mfe
        fav = r_of(hi) if is_long else r_of(lo)
        adv = r_of(lo) if is_long else r_of(hi)
        mfe = max(mfe, fav)
        mae = min(mae, adv)

        # Protective stop for this candle — most protective first.
        if trail and mfe_prior >= lock_trigger_r:
            protect_reason = "trail_stop"
            protect = entry + lock_stop_r * risk if is_long else entry - lock_stop_r * risk
        elif t1_hit:
            protect_reason = "be_stop"
            protect = entry
        else:
            protect_reason = "stop_loss"
            protect = stop

        stopped = (lo <= protect) if is_long else (hi >= protect)
        if stopped:
            exit_price, exit_reason = protect, protect_reason
            break
        reached_t1 = (hi >= t1) if is_long else (lo <= t1)
        if t1 is not None and not t1_hit and reached_t1:
            t1_hit = True
        if t2 is not None:
            reached_t2 = (hi >= t2) if is_long else (lo <= t2)
            if reached_t2:
                t2_hit = True
                exit_price, exit_reason = t2, "target_2"
                break

    if exit_reason is None:
        # Ran out of candles: remainder marked to market at the last close.
        exit_price = float(candles[n - 1]["close"])
        exit_reason = "target_1" if t1_hit else "expired"

    actual_rr = round(r_of(exit_price), 3)
    if t1 is not None and t1_hit:
        blended_rr = round(t1_partial * r_of(t1) + (1 - t1_partial) * actual_rr, 3)
    else:
        blended_rr = actual_rr

    risk_pct = risk / entry if entry else None
    hold_minutes = n * candle_minutes
    if fee_model == "taker":
        cost = cost_rr(risk_pct, hold_minutes)          # legacy path, unchanged numbers
    else:
        cost = cost_rr_legs(risk_pct, hold_minutes, fee_model, exit_reason, t1_hit, t1_partial)

    return {
        "entry_price": round(entry, 8),
        "exit_price": round(exit_price, 8),
        "exit_reason": exit_reason,
        "target_1_hit": t1_hit,
        "target_2_hit": t2_hit,
        "stop_hit": exit_reason == "stop_loss",
        "be_stop_hit": exit_reason == "be_stop",
        "trail_stop_hit": exit_reason == "trail_stop",
        "actual_rr": actual_rr,
        "blended_rr": blended_rr,
        "max_favorable_rr": round(mfe, 3),
        "max_adverse_rr": round(mae, 3),
        "candles_to_exit": n,
        "hold_minutes": hold_minutes,
        "risk_pct": round(risk_pct, 6) if risk_pct else None,
        "fee_model": fee_model,
        "cost_rr": cost,
        "net_rr": round(actual_rr - cost, 3),
        "net_blended_rr": round(blended_rr - cost, 3),
        # The 2026-09-23 hit-rate metric: did the managed trade close green NET of cost?
        "profitable": (blended_rr - cost) > 0,
        "won": actual_rr > 0,            # legacy gross flag (kept for old aggregations)
        "won_net": (actual_rr - cost) > 0,
    }


def simulate_limit(candles, direction, stop, target_1, target_2=None, atr=None,
                   limit_offset_atr=0.0, limit_wait_bars=4, max_candles=None,
                   candle_minutes=15, fee_model="maker_entry", **kw):
    """Passive (maker) entry: rest a limit at the first bar's open, improved by
    `limit_offset_atr` × ATR in the trade's favour (long: below, short: above). The order
    fills only if price trades THROUGH the limit (strictly beyond it) within
    `limit_wait_bars`; a touch is not a fill. Unfilled → returns {"filled": False}.
    On a fill the trade is simulated from the fill bar with `simulate()` (stop checked in
    the fill bar too — we were filled on the way against us, so that is fair) and costed
    with the maker-entry fee model. Everything else is identical to the market path.
    """
    if not candles:
        return None
    is_long = direction == "long"
    base = float(candles[0]["open"])
    off = (float(limit_offset_atr) * float(atr)) if (atr and limit_offset_atr) else 0.0
    limit = base - off if is_long else base + off
    if (is_long and limit <= float(stop)) or ((not is_long) and limit >= float(stop)):
        return {"filled": False, "reason": "limit beyond stop"}
    fill_bar = None
    for j, c in enumerate(candles[:max(1, int(limit_wait_bars))]):
        traded_through = (float(c["low"]) < limit) if is_long else (float(c["high"]) > limit)
        if traded_through:
            fill_bar = j
            break
    if fill_bar is None:
        return {"filled": False, "reason": "not filled", "limit_price": round(limit, 8)}
    fwd = candles[fill_bar:]
    res = simulate(fwd, direction, stop, target_1, target_2, entry_price=limit,
                   max_candles=max_candles, candle_minutes=candle_minutes,
                   fee_model=fee_model, **kw)
    if res is None:
        return {"filled": False, "reason": "invalid levels at fill"}
    res["filled"] = True
    res["fill_bar"] = fill_bar
    res["limit_price"] = round(limit, 8)
    return res


def summarize(results):
    """Aggregate a list of simulate() results into the readout used everywhere:
    n, profitable % (net blended), gross/net expectancy, net profit factor."""
    rs = [r for r in results if r]
    n = len(rs)
    if n == 0:
        return {"n": 0, "profitable_pct": None, "net_exp": None, "gross_exp": None,
                "net_pf": None, "avg_mfe": None}
    net = [r["net_blended_rr"] for r in rs]
    gross = [r["blended_rr"] for r in rs]
    wins = sum(x for x in net if x > 0)
    losses = -sum(x for x in net if x < 0)
    return {
        "n": n,
        "profitable_pct": round(100.0 * sum(1 for r in rs if r["profitable"]) / n, 1),
        "net_exp": round(sum(net) / n, 4),
        "gross_exp": round(sum(gross) / n, 4),
        "net_pf": round(wins / losses, 2) if losses > 0 else (float("inf") if wins > 0 else 0.0),
        "avg_mfe": round(sum(r["max_favorable_rr"] for r in rs) / n, 3),
        "stop_pct": round(100.0 * sum(1 for r in rs if r["stop_hit"]) / n, 1),
    }
