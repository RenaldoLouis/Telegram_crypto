"""Behavior tests for trade_sim.simulate — the ONE trade simulator shared by the live
evaluator (weekly_eval) and the unified backtester.

Run: venv/bin/python test_trade_sim.py
"""

import config
import trade_sim as ts


def c(o, h, l, cl):
    return {"open": o, "high": h, "low": l, "close": cl}


def _no_cost():
    """Disable the cost model for pure-geometry assertions; restore afterwards."""
    prev = config.COST_MODEL_ENABLED
    config.COST_MODEL_ENABLED = False
    return prev


def test_market_at_open_long_and_short():
    prev = _no_cost()
    try:
        # Long: entry at first open (100), stop 95 (risk 5), T1 104 (0.8R), T2 110 (2R).
        r = ts.simulate([c(100, 101, 99, 100.5), c(100.5, 111, 100, 110)],
                        "long", 95, 104, 110)
        assert r["entry_price"] == 100.0
        assert r["exit_reason"] == "target_2" and r["actual_rr"] == 2.0
        assert r["target_1_hit"] and r["blended_rr"] == round(0.5 * 0.8 + 0.5 * 2.0, 3)
        # Short mirror: entry 100, stop 105, T1 96, T2 90.
        r = ts.simulate([c(100, 101, 99, 99.5), c(99.5, 100, 89, 90)],
                        "short", 105, 96, 90)
        assert r["entry_price"] == 100.0 and r["exit_reason"] == "target_2"
        assert r["actual_rr"] == 2.0
    finally:
        config.COST_MODEL_ENABLED = prev


def test_stop_before_target_same_candle():
    prev = _no_cost()
    try:
        # One candle touches both the stop (95) and T2 (110): conservative → stop.
        r = ts.simulate([c(100, 112, 94, 101)], "long", 95, 104, 110)
        assert r["exit_reason"] == "stop_loss" and r["actual_rr"] == -1.0
        assert r["profitable"] is False
    finally:
        config.COST_MODEL_ENABLED = prev


def test_t1_partial_then_be_stop():
    prev = _no_cost()
    try:
        # Candle 1 reaches T1 (104, 0.8R) but not 1R; candle 2 comes back to entry → BE.
        r = ts.simulate([c(100, 104.5, 99.5, 104), c(104, 104.2, 99, 99.5)],
                        "long", 95, 104, 110)
        assert r["target_1_hit"] and r["exit_reason"] == "be_stop"
        assert r["actual_rr"] == 0.0
        assert r["blended_rr"] == 0.4 and r["profitable"] is True
    finally:
        config.COST_MODEL_ENABLED = prev


def test_trail_lock_after_1r_prior_candle_mfe():
    prev = _no_cost()
    try:
        # Candle 1: MFE 1.2R (106) — trail is NOT armed yet within this candle.
        # Candle 2: pulls back to entry → stop is now +0.3R (101.5) → trail_stop exit.
        r = ts.simulate([c(100, 106, 99.5, 105.5), c(105.5, 105.8, 100, 100.2)],
                        "long", 95, 104, 110)
        assert r["exit_reason"] == "trail_stop"
        assert abs(r["actual_rr"] - 0.3) < 1e-9
        # Same path with trail disabled → BE stop instead.
        r2 = ts.simulate([c(100, 106, 99.5, 105.5), c(105.5, 105.8, 100, 100.2)],
                         "long", 95, 104, 110, trail=False)
        assert r2["exit_reason"] == "be_stop" and r2["actual_rr"] == 0.0
    finally:
        config.COST_MODEL_ENABLED = prev


def test_expiry_marks_to_close():
    prev = _no_cost()
    try:
        r = ts.simulate([c(100, 101, 99, 100.5), c(100.5, 102, 100, 101)],
                        "long", 95, 104, 110)
        assert r["exit_reason"] == "expired"
        assert abs(r["actual_rr"] - 0.2) < 1e-9
        assert r["candles_to_exit"] == 2
    finally:
        config.COST_MODEL_ENABLED = prev


def test_inverted_levels_return_none():
    assert ts.simulate([c(100, 101, 99, 100)], "long", 105, 104, 110) is None   # stop above entry
    assert ts.simulate([c(100, 101, 99, 100)], "short", 95, 96, 90) is None     # stop below entry
    assert ts.simulate([c(100, 101, 99, 100)], "long", 100, 104, 110) is None   # zero risk
    assert ts.simulate([], "long", 95, 104, 110) is None


def test_cost_flips_tiny_gross_win():
    prev = config.COST_MODEL_ENABLED
    config.COST_MODEL_ENABLED = True
    try:
        # Expire at +0.02R gross with a 1% stop: round-trip 0.17% / 1% = 0.17R cost.
        r = ts.simulate([c(100, 100.05, 99.9, 100.02)], "long", 99, 100.75, 101.5)
        assert r["actual_rr"] > 0 and r["won"] is True
        assert r["net_rr"] < 0 and r["profitable"] is False
        assert r["cost_rr"] > 0.1
    finally:
        config.COST_MODEL_ENABLED = prev


def test_max_candles_cap():
    prev = _no_cost()
    try:
        candles = [c(100, 101, 99, 100.5), c(100.5, 101, 100, 100.8), c(100.8, 111, 100.5, 110)]
        r = ts.simulate(candles, "long", 95, 104, 110, max_candles=2)
        assert r["exit_reason"] == "expired" and r["candles_to_exit"] == 2
        r = ts.simulate(candles, "long", 95, 104, 110)
        assert r["exit_reason"] == "target_2"
    finally:
        config.COST_MODEL_ENABLED = prev


def test_summarize():
    prev = _no_cost()
    try:
        rs = [ts.simulate([c(100, 112, 94, 101)], "long", 95, 104, 110),
              ts.simulate([c(100, 101, 99, 100.5), c(100.5, 111, 100, 110)], "long", 95, 104, 110)]
        s = ts.summarize(rs)
        assert s["n"] == 2 and s["profitable_pct"] == 50.0 and s["stop_pct"] == 50.0
    finally:
        config.COST_MODEL_ENABLED = prev


def test_limit_entry_fill_and_fees():
    import trade_sim as ts, config
    # long: limit at open 100 - 0.5*ATR(2) = 99; first bar low 99.5 -> no fill; second bar low 98.5 -> fill
    c = [{"open": 100, "high": 101, "low": 99.5, "close": 100.5},
         {"open": 100.5, "high": 101, "low": 98.5, "close": 100},
         {"open": 100, "high": 104, "low": 99.8, "close": 103.5},
         {"open": 103.5, "high": 105, "low": 103, "close": 104}]
    r = ts.simulate_limit(c, "long", stop=97, target_1=100.5, target_2=102, atr=2.0,
                          limit_offset_atr=0.5, limit_wait_bars=4)
    assert r["filled"] and r["fill_bar"] == 1 and abs(r["entry_price"] - 99) < 1e-9
    assert r["exit_reason"] == "target_2" and r["fee_model"] == "maker_entry"
    # same trade costed as taker must be MORE expensive than maker_entry
    m = ts.simulate(c[1:], "long", 97, 100.5, 102, entry_price=99)
    assert m["cost_rr"] > r["cost_rr"] > 0
    # touch is not a fill: low == limit exactly -> unfilled
    c2 = [{"open": 100, "high": 101, "low": 99.0, "close": 100.5}] * 4
    assert ts.simulate_limit(c2, "long", 97, 100.5, 102, atr=2.0, limit_offset_atr=0.5)["filled"] is False
    # limit beyond stop is rejected
    assert ts.simulate_limit(c, "long", 99.5, 100.5, 102, atr=2.0, limit_offset_atr=1.0)["filled"] is False
    # stop exit under maker_entry still pays taker on the exit leg (cost above pure-maker)
    c3 = [{"open": 100, "high": 100.2, "low": 98.9, "close": 99}, {"open": 99, "high": 99.2, "low": 96.5, "close": 97}]
    r3 = ts.simulate_limit(c3, "long", 97, 100.5, 102, atr=2.0, limit_offset_atr=0.5, limit_wait_bars=2)
    assert r3["filled"] and r3["exit_reason"] == "stop_loss"
    rp = r3["risk_pct"]; pure_maker = 2 * config.MAKER_FEE_PCT / rp
    assert r3["cost_rr"] > pure_maker
    # default market path unchanged: fee_model taker, cost == cost_rr
    d = ts.simulate(c, "long", 97, 100.5, 102)
    assert d["fee_model"] == "taker" and abs(d["cost_rr"] - ts.cost_rr(d["risk_pct"], d["hold_minutes"])) < 1e-9
    print("PASS test_limit_entry_fill_and_fees")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"  ✓ {t.__name__}")
    print(f"All {len(tests)} trade_sim tests passed.")
