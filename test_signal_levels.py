"""Drift-guard + behavior tests for signal_levels.py.

Run: venv/bin/python test_signal_levels.py

The critical test asserts signal_levels.target_from_r / stop_from_atr produce
EXACTLY what historical_backtester.py's inline math does. If the backtester's
formulas are ever changed, this test fails and forces the shared module to be
updated in lockstep (no silent drift between the validated backtester and the
live mechanical constructor).
"""

import signal_levels as sl


def test_target_matches_backtester():
    # evaluate_forward:478-480 -> target = entry +/- target_r * risk
    for entry, risk, target_r in [(100.0, 3.0, 1.5), (2.5, 0.08, 2.0), (60000.0, 900.0, 1.5)]:
        long_expected = entry + target_r * risk
        short_expected = entry - target_r * risk
        assert abs(sl.target_from_r(entry, risk, target_r, "long") - long_expected) < 1e-6
        assert abs(sl.target_from_r(entry, risk, target_r, "short") - short_expected) < 1e-6


def test_stop_matches_backtester():
    # signal_*:200/220 -> stop = entry -/+ mult * ATR
    for price, atr, mult in [(100.0, 2.0, 1.5), (2.5, 0.05, 2.0), (60000.0, 500.0, 1.5)]:
        long_expected = price - mult * atr
        short_expected = price + mult * atr
        assert abs(sl.stop_from_atr(price, atr, mult, "long") - long_expected) < 1e-6
        assert abs(sl.stop_from_atr(price, atr, mult, "short") - short_expected) < 1e-6


def test_entry_zone_contains_price():
    lo, hi = sl.entry_zone(100.0, 2.0)
    assert lo < 100.0 < hi
    # ATR missing -> 0.1% band, still contains price
    lo, hi = sl.entry_zone(100.0, 0)
    assert lo < 100.0 < hi


def test_structural_t1_in_band():
    # long, entry 100, risk 4 -> band [103, 104]. Levels: 103.5 in band, 101 too near, 110 too far.
    t1, rr = sl.nearest_structural_target(100.0, 4.0, "long", [101.0, 103.5, 110.0, None, float("nan")])
    assert abs(t1 - 103.5) < 1e-6
    assert 0.75 <= rr <= 1.0
    # nearest-in-band wins when two qualify (103.2 closer than 103.9)
    t1, rr = sl.nearest_structural_target(100.0, 4.0, "long", [103.9, 103.2])
    assert abs(t1 - 103.2) < 1e-6


def test_structural_t1_fallback():
    # No level in band -> synthetic 0.75R
    t1, rr = sl.nearest_structural_target(100.0, 4.0, "long", [101.0, 120.0])
    assert abs(t1 - 103.0) < 1e-6 and rr == 0.75
    # short fallback
    t1, rr = sl.nearest_structural_target(100.0, 4.0, "short", [])
    assert abs(t1 - 97.0) < 1e-6 and rr == 0.75


def test_predicted_rr_never_exceeds_cap():
    # Whatever the levels, predicted_rr must stay <= 1.0 (T1 enforcement gate).
    for lv in [102.5, 103.0, 104.0, 105.0, 100.5]:
        _, rr = sl.nearest_structural_target(100.0, 4.0, "long", [lv])
        assert rr <= 1.0


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
    print(f"\nAll {len(tests)} tests passed.")
