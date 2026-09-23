"""Behavior tests for main.split_surfaced_shadow + the WATCH brief rendering.

Run: venv/bin/python test_surfacing.py
"""

import config
import main
from delivery.telegram_bot import format_mechanical_brief


def _cand(symbol, sig, hit, n, direction="short"):
    return {"symbol": symbol, "signal_name": sig, "signal_expectancy": hit, "signal_test_n": n,
            "direction": direction, "source": "watch", "tier": "watch", "entry_low": 1.0,
            "entry_high": 1.0, "stop_loss": 1.1, "target_1": 0.93, "target_2": 0.85,
            "predicted_rr": 0.75, "confidence": "low", "tf_confluence": 3,
            "reasoning": {"key_factor": f"{sig} on 4h"}}


def test_every_candidate_clearing_both_bars_is_surfaced():
    prev = (config.SURFACE_MIN_HIT_RATE, config.SURFACE_MIN_TEST_N)
    config.SURFACE_MIN_HIT_RATE, config.SURFACE_MIN_TEST_N = 0.60, 30
    try:
        cands = [_cand("AAA", "range_reversion_long", 0.73, 11, "long"),   # thin n → shadow
                 _cand("BBB", "range_reversion_short", 0.66, 41),          # surfaced
                 _cand("CCC", "range_reversion_short", 0.66, 41),          # ALSO surfaced (was shadow pre-fix)
                 _cand("DDD", "trend_pullback_short", 0.526, 152),         # below hit bar → shadow
                 _cand("EEE", "mystery_rule", 0.90, None)]                 # unknown n → shadow
        surfaced, shadow = main.split_surfaced_shadow(cands)
        assert [c["symbol"] for c in surfaced] == ["BBB", "CCC"], surfaced
        assert [c["symbol"] for c in shadow] == ["AAA", "DDD", "EEE"], shadow
        assert all(c["source"] == "shadow" and c["tier"] == "shadow" for c in shadow)
        assert all(c["source"] == "watch" for c in surfaced)
        assert [c["rank"] for c in surfaced] == [1, 2]
        assert [c["rank"] for c in shadow] == [1, 2, 3]
    finally:
        config.SURFACE_MIN_HIT_RATE, config.SURFACE_MIN_TEST_N = prev
    print("  ✓ test_every_candidate_clearing_both_bars_is_surfaced")


def test_n_bar_disabled_when_zero():
    prev = (config.SURFACE_MIN_HIT_RATE, config.SURFACE_MIN_TEST_N)
    config.SURFACE_MIN_HIT_RATE, config.SURFACE_MIN_TEST_N = 0.60, 0
    try:
        surfaced, shadow = main.split_surfaced_shadow([_cand("AAA", "range_reversion_long", 0.73, 11)])
        assert len(surfaced) == 1 and not shadow
    finally:
        config.SURFACE_MIN_HIT_RATE, config.SURFACE_MIN_TEST_N = prev
    print("  ✓ test_n_bar_disabled_when_zero")


def test_brief_renders_every_surfaced_watch_with_limit_entry():
    prev = config.ENTRY_MODEL
    config.ENTRY_MODEL = "limit_open"
    try:
        watch = [_cand("BBB", "range_reversion_short", 0.66, 41),
                 _cand("CCC", "range_reversion_short", 0.66, 41)]
        text = format_mechanical_brief([], "neutral", watch=watch)
        assert "Watch Candidates" in text, text
        assert "### BBB | Short | Watch" in text and "### CCC | Short | Watch" in text
        assert text.count("post-only LIMIT") == 2
        assert "2 candidates to WATCH" in text
        one = format_mechanical_brief([], "neutral", watch=watch[:1])
        assert "Watch Candidate (" in one and "1 candidate to WATCH" in one
        empty = format_mechanical_brief([], "neutral", watch=[])
        assert "0 setups" in empty and "Watch" not in empty
    finally:
        config.ENTRY_MODEL = prev
    print("  ✓ test_brief_renders_every_surfaced_watch_with_limit_entry")


if __name__ == "__main__":
    test_every_candidate_clearing_both_bars_is_surfaced()
    test_n_bar_disabled_when_zero()
    test_brief_renders_every_surfaced_watch_with_limit_entry()
    print("All 3 surfacing tests passed.")
