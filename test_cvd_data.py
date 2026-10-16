"""Offline tests for cvd_data.py (2026-10-16): bar aggregation + coverage gating, the valid-bar
cvd_slope definition, the confirm/contra bucketer, and the harness's pre-registered cvd_study
verdict logic on synthetic trades.

Run: venv/bin/python test_cvd_data.py
"""

import math

import cvd_data as cd

H = 3_600_000
M = 60_000


def _idx(rows):
    """rows: list of (minute_ms, buy_q, sell_q) for one symbol 'X'."""
    return cd.CvdIndex({"X": rows})


def test_bar_aggregation_and_coverage():
    t0 = 10 * H
    rows = [(t0 + i * M, 2.0, 1.0) for i in range(60)]            # full hour: delta +60, cov 1.0
    rows += [(t0 + H + i * M, 1.0, 3.0) for i in range(30)]       # half hour: cov 0.5
    idx = _idx(rows)
    d, q, c = idx.bar("X", t0, H)
    assert d == 60.0 and q == 180.0 and c == 1.0, (d, q, c)
    d, q, c = idx.bar("X", t0 + H, H)
    assert d == -60.0 and c == 0.5, (d, c)
    assert idx.bar("X", t0 + 2 * H, H) == (0.0, 0.0, 0.0)          # no buckets → zero coverage
    assert idx.bar("Y", t0, H) is None                              # unknown symbol
    assert idx.symbols == ["X"]
    print("  ✓ test_bar_aggregation_and_coverage")


def test_slope_series_matches_definition_and_skips_gaps():
    # 30 valid bars, delta = +10 each → after warm-up slope = (6*10)/(10*6) = 1.0
    delta = [10.0] * 30
    s = cd.slope_series(delta)
    assert all(math.isnan(x) for x in s[:9]) and abs(s[29] - 1.0) < 1e-9, s[25:]
    # sign follows net flow: last 6 bars strongly negative → slope < 0
    delta2 = [10.0] * 24 + [-50.0] * 6
    assert cd.slope_series(delta2)[-1] < 0
    # a collector outage (NaN run) longer than MAX_SPAN breaks recency: the first bars after
    # the gap have no slope until 6 valid bars fit inside 12 calendar bars again
    delta3 = [10.0] * 20 + [float("nan")] * 10 + [10.0] * 3
    s3 = cd.slope_series(delta3)
    assert math.isnan(s3[30]) and math.isnan(s3[32]), s3[28:]
    delta4 = [10.0] * 20 + [float("nan")] * 4 + [10.0] * 6
    assert not math.isnan(cd.slope_series(delta4)[-1])            # short gap: 6 valid within 12 → ok
    print("  ✓ test_slope_series_matches_definition_and_skips_gaps")


def test_attach_to_df_gates_on_coverage():
    import pandas as pd
    t0 = 100 * H
    rows = []
    for b in range(40):                                            # 40 hourly bars
        minutes = 60 if b not in (35, 37) else (20 if b == 35 else 36)   # bar 35: 33% (NA); bar 37: 60% (scaled)
        rows += [(t0 + b * H + i * M, 3.0, 1.0) for i in range(minutes)]
    df = pd.DataFrame({"timestamp": [t0 + b * H for b in range(40)], "close": [1.0] * 40})
    cd.attach_to_df(df, _idx(rows), "X", H)
    assert abs(df["cvd_cov"].iloc[35] - 1 / 3) < 1e-9 and math.isnan(df["cvd_delta"].iloc[35])
    assert math.isnan(df["cvd_slope"].iloc[35]) and not math.isnan(df["cvd_slope"].iloc[39])
    assert abs(df["cvd_slope"].iloc[34] - 1.0) < 1e-9
    # 60%-covered bar: delta scaled to a full bar (36 min × +2 = 72 → 72/0.6 = 120 = the full-bar value)
    assert df["cvd_cov"].iloc[37] == 0.6 and abs(df["cvd_delta"].iloc[37] - 120.0) < 1e-9
    assert abs(df["cvd_slope"].iloc[39] - 1.0) < 1e-9                                  # scaling keeps the slope flat
    cd.attach_to_df(df, None, "X", H)                              # no index → all NaN, no crash
    assert df["cvd_slope"].isna().all()
    print("  ✓ test_attach_to_df_gates_on_coverage")


def test_confirm_bucket():
    assert cd.confirm_bucket(0.3, "long", 0.2) == "confirm"
    assert cd.confirm_bucket(-0.3, "short", 0.2) == "confirm"
    assert cd.confirm_bucket(0.3, "short", 0.2) == "contra"
    assert cd.confirm_bucket(0.1, "long", 0.2) == "neutral"
    assert cd.confirm_bucket(float("nan"), "long", 0.2) == "na" and cd.confirm_bucket(None, "long", 0.2) == "na"
    print("  ✓ test_confirm_bucket")


def _trade(sig, direction, slope, profitable, net, t):
    return {"signal": sig, "tf": "4h", "direction": direction, "cvd_slope": slope, "signal_ms": t,
            "_res": {"profitable": profitable, "net_blended_rr": net, "blended_rr": net + 0.1,
                     "max_favorable_rr": 1.0 if profitable else 0.2, "stop_hit": not profitable, "filled": True}}


def test_cvd_study_verdicts():
    import unified_backtest as ub
    # Rule A: confirm bucket clearly better on both halves with n>=30 on TEST, monotonic → PASS
    tr = []
    t = 0
    for i in range(200):
        t += 1
        conf = i % 2 == 0
        slope = -0.5 if conf else 0.0                       # shorts: negative slope = confirm
        tr.append(_trade("A", "short", slope, (i % 10) < 8 if conf else (i % 10) < 4,
                         0.4 if ((i % 10) < 8 if conf else (i % 10) < 4) else -0.6, t))
    lines, verdict, per_rule = ub.cvd_study({("A", "4h"): tr})
    assert per_rule[("A", "4h")] == "PASS", per_rule
    assert verdict == "PASS", verdict
    # Rule B: confirm no better → FAIL
    # outcome independent of the confirm flag (parity): confirm == baseline → no lift
    tr_b = [_trade("B", "short", -0.5 if i % 2 == 0 else 0.0, (i // 2) % 10 < 5, 0.1 if (i // 2) % 10 < 5 else -0.6, i)
            for i in range(200)]
    _, verdict_b, per_b = ub.cvd_study({("B", "4h"): tr_b})
    assert per_b[("B", "4h")] == "FAIL" and verdict_b == "FAIL", (per_b, verdict_b)
    # Rule C: same effect as A but only ~20 TEST confirm trades → INCONCLUSIVE
    tr_c = tr[:100]
    _, verdict_c, per_c = ub.cvd_study({("C", "4h"): [dict(x, signal="C") for x in tr_c]})
    assert per_c[("C", "4h")] == "INCONCLUSIVE" and verdict_c == "INCONCLUSIVE", (per_c, verdict_c)
    # Mixed: one FAIL + one INCONCLUSIVE → INCONCLUSIVE; one PASS anywhere → PASS
    _, v_mix, _ = ub.cvd_study({("B", "4h"): tr_b, ("C", "4h"): [dict(x, signal="C") for x in tr_c]})
    assert v_mix == "INCONCLUSIVE"
    _, v_mix2, _ = ub.cvd_study({("B", "4h"): tr_b, ("A", "4h"): tr})
    assert v_mix2 == "PASS"
    # too few CVD-tagged trades everywhere → NOT_RUN (a data problem, never a FAIL)
    _, v_skip, per_skip = ub.cvd_study({("D", "4h"): tr[:5]})
    assert per_skip[("D", "4h")] == "SKIPPED" and v_skip == "NOT_RUN"
    assert any("PRE-REGISTERED" in l for l in lines)
    print("  ✓ test_cvd_study_verdicts")


if __name__ == "__main__":
    test_bar_aggregation_and_coverage()
    test_slope_series_matches_definition_and_skips_gaps()
    test_attach_to_df_gates_on_coverage()
    test_confirm_bucket()
    test_cvd_study_verdicts()
    print("All 5 cvd_data tests passed.")
