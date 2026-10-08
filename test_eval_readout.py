"""Behavior tests for the 2026-10-08 eval readout fixes in weekly_eval.py:
cross-run duplicate marking (trade identity = signal bar) and the gated VERDICT line.

Run: venv/bin/python test_eval_readout.py
"""

import json
import tempfile
from pathlib import Path

import weekly_eval as we


def _setup(symbol, source="shadow", sig="failed_breakout_short", tf="4h", direction="short"):
    return {"symbol": symbol, "direction": direction, "source": source,
            "signal_name": sig, "signal_tf": tf}


def _rec(tag, ts, setups):
    return {"run_tag": tag, "run_timestamp_utc": ts, "setups": setups}


def test_same_bar_is_same_trade():
    s = _setup("MUBARAKUSDT")
    a = we._signal_bar_key(s, "2026-10-04T20:03:10+00:00")
    b = we._signal_bar_key(s, "2026-10-04T20:15:31+00:00")
    c = we._signal_bar_key(s, "2026-10-05T00:05:00+00:00")   # next 4h close = new bar
    assert a == b and a != c, (a, b, c)
    assert we._signal_bar_key({"symbol": "X", "direction": "long"}, "2026-10-04T20:03:00+00:00") is None
    print("  ✓ test_same_bar_is_same_trade")


def test_later_copy_marked_duplicate_and_idempotent():
    recs = {r["run_tag"]: r for r in [
        _rec("20261004_2015", "2026-10-04T20:15:31+00:00", [_setup("MUBARAKUSDT"), _setup("NEWUSDT")]),
        _rec("20261004_2003", "2026-10-04T20:03:10+00:00", [_setup("MUBARAKUSDT")]),
    ]}
    first = we._first_issuers(recs.values())
    evals = [{"run_tag": tag, "run_timestamp_utc": r["run_timestamp_utc"],
              "results": [{"status": "evaluated", "symbol": s["symbol"], "source": s["source"]}
                          for s in r["setups"]]} for tag, r in recs.items()]
    prev = we.EVALS_DIR
    with tempfile.TemporaryDirectory() as d:
        we.EVALS_DIR = Path(d)
        try:
            assert we._mark_duplicate_evals(evals, recs, first) == 1
            late = next(e for e in evals if e["run_tag"] == "20261004_2015")
            st = {r["symbol"]: r["status"] for r in late["results"]}
            assert st == {"MUBARAKUSDT": "duplicate", "NEWUSDT": "evaluated"}, st
            assert late["results"][0]["duplicate_of"] == "20261004_2003"
            saved = json.loads((Path(d) / "eval_20261004_2015.json").read_text())
            assert saved["results"][0]["status"] == "duplicate"
            assert we._mark_duplicate_evals(evals, recs, first) == 0   # idempotent
        finally:
            we.EVALS_DIR = prev
    print("  ✓ test_later_copy_marked_duplicate_and_idempotent")


def test_same_block_same_direction_is_one_bet():
    rs = [{"_run_ts": "2026-10-05T17:20:00+00:00", "direction": "long", "net_rr": x}
          for x in (1.0, 1.0, 1.0, 1.0, -1.0)]
    rs.append({"_run_ts": "2026-10-05T17:20:00+00:00", "direction": "short", "net_rr": -1.0})
    bets = sorted(we._independent_bets(rs))
    assert bets == [-1.0, 0.6], bets
    print("  ✓ test_same_block_same_direction_is_one_bet")


def _v2(source, net, ts, direction="long", sig="liquidity_sweep_long"):
    return {"status": "evaluated", "eval_engine": we.EVAL_ENGINE, "source": source,
            "signal_name": sig, "direction": direction, "symbol": "X", "actual_rr": net,
            "net_rr": net, "net_blended_rr": net, "profitable": net > 0, "won": net > 0}


def _verdict(evals):
    prev = we.PERFORMANCE_DIR
    with tempfile.TemporaryDirectory() as d:
        we.PERFORMANCE_DIR = Path(d)
        try:
            we.generate_head_to_head(evals)
            txt = (Path(d) / "head_to_head.md").read_text()
        finally:
            we.PERFORMANCE_DIR = prev
    return next(l for l in txt.splitlines() if "VERDICT" in l)


def test_verdict_ignores_shadow_and_small_n():
    # 32 profitable shadow trades + 2 surfaced: the old line said "SURVIVES … tradeable-grade".
    evals = [{"run_tag": f"t{i}", "run_timestamp_utc": f"2026-10-{1 + i // 6:02d}T{(i % 6) * 4:02d}:05:00+00:00",
              "results": [_v2("shadow", 0.5, None)]} for i in range(32)]
    evals.append({"run_tag": "w", "run_timestamp_utc": "2026-10-05T08:05:00+00:00",
                  "results": [_v2("watch", 0.8, None, "short", "range_reversion_short")] * 2})
    line = _verdict(evals)
    assert "NOT DECIDABLE YET (2/30" in line and "SURVIVES" not in line, line
    print("  ✓ test_verdict_ignores_shadow_and_small_n")


def test_verdict_needs_ci_above_zero():
    def book(vals):
        return [{"run_tag": f"t{i}", "run_timestamp_utc": f"2026-10-{1 + i // 6:02d}T{(i % 6) * 4:02d}:05:00+00:00",
                 "results": [_v2("watch", v, None, "short", "range_reversion_short")]}
                for i, v in enumerate(vals)]
    assert "SURVIVES" in _verdict(book([0.6] * 24 + [-1.0] * 6))         # +0.28R, tight CI
    assert "CI spans zero" in _verdict(book([1.0] * 16 + [-1.0] * 14))  # +0.07R, wide CI
    assert "net-negative with 95%" in _verdict(book([0.3] * 10 + [-1.0] * 20))
    print("  ✓ test_verdict_needs_ci_above_zero")


if __name__ == "__main__":
    test_same_bar_is_same_trade()
    test_later_copy_marked_duplicate_and_idempotent()
    test_same_block_same_direction_is_one_bet()
    test_verdict_ignores_shadow_and_small_n()
    test_verdict_needs_ci_above_zero()
    print("All 5 eval-readout tests passed.")
