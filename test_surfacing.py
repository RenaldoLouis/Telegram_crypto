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


def _sand_like(symbol="SANDUSDT", conf=1, direction="short"):
    """The 2026-10-02 12:00 UTC case: range_reversion_short fired at a range top, so bearish
    confluence was 1/4. Prices mimic a short: entry 1.00, stop 1.10, T1 0.925 (0.75R), T2 0.85."""
    s = _cand(symbol, "range_reversion_short", 0.659, 41, direction=direction)
    s.update({"setup_type": "range_mean_reversion", "timeframe": "intraday",
              "tf_confluence": conf, "rank": 1, "volume_confirmed": False})
    return s


def test_watch_gate_parity_keeps_low_confluence_fire():
    """WATCH lane (harness parity) must NOT drop a fire for confluence; the EXECUTE path must."""
    prev = getattr(config, "WATCH_GATE_PARITY", "execute")
    try:
        # 1. The exact SAND case under harness parity: kept.
        kept = main.enforce_setups([_sand_like(conf=1)], "risk_on", harness_parity=True)
        assert [s["symbol"] for s in kept] == ["SANDUSDT"], kept
        # 2. Same setup through the EXECUTE path: still dropped (confluence floor intact).
        assert main.enforce_setups([_sand_like(conf=1)], "risk_on") == []
        # 3. 4/4 is refused on EXECUTE but allowed on the WATCH paper lane.
        assert main.enforce_setups([_sand_like(conf=4)], "neutral") == []
        assert len(main.enforce_setups([_sand_like(conf=4)], "neutral", harness_parity=True)) == 1
        # 4. Structural checks still apply under parity: a T2 below the 1.5R floor is dropped.
        bad = _sand_like(conf=1)
        bad["target_2"] = 0.95  # 0.5R
        assert main.enforce_setups([bad], "neutral", harness_parity=True) == []
        # 5. No regime / same-direction caps on the WATCH lane: 3 shorts in risk_on all survive
        #    (risk_on short cap is 1 and MAX_SAME_DIRECTION_PER_RUN is 2 on EXECUTE).
        three = [_sand_like(sym, conf=1) for sym in ("AAAUSDT", "BBBUSDT", "CCCUSDT")]
        for i, s in enumerate(three, 1):
            s["rank"] = i
        kept = main.enforce_setups(three, "risk_on", harness_parity=True)
        assert len(kept) == 3 and [s["rank"] for s in kept] == [1, 2, 3], kept
        # 6. One setup per symbol is still enforced (harness also has one trade per symbol).
        dup = [_sand_like(conf=1), _sand_like(conf=2)]
        dup[1]["rank"] = 2
        assert len(main.enforce_setups(dup, "neutral", harness_parity=True)) == 1
        # 7. build_watch_candidates honours the config switch.
        raw = [_sand_like(conf=1)]
        raw[0]["tier"] = "watch"
        config.WATCH_GATE_PARITY = "harness"
        out = main.build_watch_candidates([dict(raw[0])], [], {}, "risk_on")
        assert [c["symbol"] for c in out] == ["SANDUSDT"], out
        config.WATCH_GATE_PARITY = "execute"
        assert main.build_watch_candidates([dict(raw[0])], [], {}, "risk_on") == []
    finally:
        config.WATCH_GATE_PARITY = prev
    print("  ✓ test_watch_gate_parity_keeps_low_confluence_fire")


def test_engine_view_renders_below_bar_label_and_stays_uncounted():
    """Engine View (2026-10-16): shadow rows render under an explicit below-bar label with their
    measured numbers; the WATCH/EXECUTE text and the shadow rows' source are untouched."""
    prev = config.ENTRY_MODEL
    config.ENTRY_MODEL = "limit_open"
    try:
        _, shadow = main.split_surfaced_shadow([_cand("DDD", "trend_pullback_short", 0.526, 152)])
        item = dict(shadow[0]); item["signal_tf"] = "4h"; item["_issued_at"] = "04:02 UTC"
        item["_lane_live"] = {"n": 26, "prof_pct": 53.8, "net": 0.011}
        text = format_mechanical_brief([], "neutral", watch=[], engine_view=[item])
        assert "Engine View (below bar — NOT a recommendation, not counted)" in text, text
        assert "DDD | Short | `trend_pullback_short` (4h) · fired 04:02 UTC" in text
        assert "backtest TEST 53% (n=152) · live shadow last 26: 54% / +0.01R" in text
        assert "post-only LIMIT" in text and "Stand aside" in text
        assert shadow[0]["source"] == "shadow"          # the persisted row is unchanged
        # No engine view → the brief is byte-identical to before.
        assert "Engine View" not in format_mechanical_brief([], "neutral", watch=[], engine_view=[])
        # With a surfaced WATCH row the view is appended after the watch block, before the takeaway.
        both = format_mechanical_brief([], "neutral", watch=[_cand("BBB", "range_reversion_short", 0.66, 41)],
                                       engine_view=[item])
        assert both.index("Watch Candidate") < both.index("Engine View") < both.index("One-Line Takeaway")
    finally:
        config.ENTRY_MODEL = prev
    print("  ✓ test_engine_view_renders_below_bar_label_and_stays_uncounted")


def test_engine_view_picks_recent_shadow_rows_across_runs():
    """_engine_view merges this run's shadow rows with rows persisted by (quiet) runs inside the
    lookback, keeps the earliest copy, ranks by backtest hit rate, caps at ENGINE_VIEW_MAX."""
    import json, os, tempfile
    from datetime import datetime, timedelta, timezone
    now = datetime(2026, 10, 16, 6, 7, tzinfo=timezone.utc)
    cwd = os.getcwd()
    enabled = config.ENGINE_VIEW_ENABLED     # off by default since the daily book (2026-10-19)
    config.ENGINE_VIEW_ENABLED = True
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)
        try:
            os.makedirs("logs/setups")
            def rec(ts, setups, tag):
                json.dump({"run_timestamp_utc": ts.isoformat(), "run_tag": tag, "setups": setups},
                          open(f"logs/setups/setups_{tag}.json", "w"))
            keeper = now - timedelta(minutes=125)            # 04:02 UTC quiet keeper run
            old = now - timedelta(minutes=400)               # outside the lookback
            s_fb = dict(_cand("FBB", "failed_breakout_short", 0.545, 112)); s_fb["source"] = "shadow"
            s_ls = dict(_cand("LSS", "liquidity_sweep_long", 0.51, 341, "long")); s_ls["source"] = "shadow"
            s_old = dict(_cand("OLD", "range_reversion_long", 0.73, 11, "long")); s_old["source"] = "shadow"
            w = dict(_cand("WWW", "range_reversion_short", 0.66, 41))            # watch row: never in the view
            rec(keeper, [s_fb, s_ls, w], "20261016_0402")
            rec(old, [s_old], "20261015_2327")
            s_now = dict(_cand("FBB", "failed_breakout_short", 0.545, 112)); s_now["source"] = "shadow"
            s_tp = dict(_cand("TPP", "trend_pullback_short", 0.526, 152)); s_tp["source"] = "shadow"
            items = main._engine_view([s_now, s_tp], now, max_items=2, lookback_min=150)
            syms = [i["symbol"] for i in items]
            assert syms == ["FBB", "TPP"], syms                 # by hit rate: 0.545 > 0.526 > 0.51; OLD excluded
            assert items[0]["_issued_at"] == "04:02 UTC"        # earliest copy of FBB wins (the keeper's)
            assert "_lane_live" in items[0]
            prev = config.ENGINE_VIEW_ENABLED
            config.ENGINE_VIEW_ENABLED = False
            try:
                assert main._engine_view([s_now], now) == []
            finally:
                config.ENGINE_VIEW_ENABLED = prev
        finally:
            os.chdir(cwd)
            config.ENGINE_VIEW_ENABLED = enabled
    print("  ✓ test_engine_view_picks_recent_shadow_rows_across_runs")


if __name__ == "__main__":
    test_every_candidate_clearing_both_bars_is_surfaced()
    test_n_bar_disabled_when_zero()
    test_brief_renders_every_surfaced_watch_with_limit_entry()
    test_watch_gate_parity_keeps_low_confluence_fire()
    test_engine_view_renders_below_bar_label_and_stays_uncounted()
    test_engine_view_picks_recent_shadow_rows_across_runs()
    print("All 6 surfacing tests passed.")
