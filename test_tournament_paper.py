"""Behavior tests for tournament_paper — the forward paper tournament (synthetic market, no network).

Run: venv/bin/python test_tournament_paper.py
"""

import json
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

import edge_search as es
import tournament_paper as tp
from test_blend_paper import FakeSource

START = pd.Timestamp("2026-10-25", tz="UTC")


def _run(src, tmp, now, others=None):
    return tp.run(now=pd.Timestamp(now, tz="UTC"), source=src, out=tmp / "out", cache=tmp / "cache",
                  telegram=False, start=START, min_universe=10, others={} if others is None else others)


def _btc_up(src, seed=3):
    """Give the fake BTC an uptrend so the BTC-trend lane is on (FakeSource's BTC drifts down)."""
    rng = np.random.default_rng(seed)
    rows = src.rows["BTCUSDT"]
    c = 100 * np.exp(np.cumsum(rng.normal(0.004, 0.01, len(rows))))
    o = np.concatenate([[100.0], c[:-1]])
    src.rows["BTCUSDT"] = [[r[0], oi, max(oi, ci) * 1.01, min(oi, ci) * 0.99, ci, 1.0, 1e9] for r, oi, ci in zip(rows, o, c)]
    return src


def _rows(daily):
    """Score rows from {lane: pd.Series of daily net}."""
    return [{"day": str(d.date()), "lane": lane, "net": float(v)} for lane, s in daily.items() for d, v in s.items()]


def _flat(start, end, mean, sd=0.002, seed=0):
    idx = pd.date_range(start, end, freq="D", tz="UTC")
    rng = np.random.default_rng(seed)
    return pd.Series(mean + rng.normal(0, sd, len(idx)), index=idx)


def _alt(start, end, t, d=0.01):
    """Alternating mean ± d with a daily-mean t-statistic of exactly `t` (no drawdown to speak of)."""
    idx = pd.date_range(start, end, freq="D", tz="UTC")
    n = len(idx)
    base = d * np.where(np.arange(n) % 2 == 0, 1.0, -1.0)
    base = base - base.mean()
    return pd.Series(base + t * base.std(ddof=1) / np.sqrt(n), index=idx)


def test_frozen_code_and_entrants_are_the_blend_sleeves():
    assert tp.code_fingerprint() == tp.FROZEN_CODE, "the tournament's code changed — new pre-registration needed"
    assert set(tp.ENTRANTS.values()) == set(tp.BLEND_SLEEVES)
    assert tp.BLEND_SLEEVES["xs_mom_28d_skip0_10pct"] == 0.5152 and tp.VOL_FACTOR == 0.5


def test_run_records_every_lane_scores_and_is_idempotent():
    src = FakeSource()
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        new = _run(src, tmp, "2026-10-28 00:30")
        assert {r["lane"] for r in new} == set(tp.LANES)
        assert sorted({r["day"] for r in new}) == ["2026-10-25", "2026-10-26", "2026-10-27"]
        first = [r for r in new if r["day"] == "2026-10-25" and tp.LANES.index(r["lane"]) < 4]
        assert all(r["gross"] == 0.0 and r["net"] == r["cost"] for r in first)           # opening cost only
        doc = json.loads((tmp / "out" / "weights_2026-10-27.json").read_text())
        assert doc["rules_hash"] == tp.rules_hash() and doc["late_hours"] == 0.5
        assert doc["lanes"]["listing_short"]["weights"]["NEWUSDT"] < 0                     # the new listing is shorted
        assert set(doc["lanes"]["btc_trend"]["weights"]) <= {"BTCUSDT"}
        for c in tp.CONTROLS:                                                              # dollar-neutral L/S books
            w = pd.Series(doc["lanes"][c]["weights"])
            assert len(w) >= 4 and abs(w.sum()) < 1e-9 and (w > 0).any() and (w < 0).any()
        calls = src.calls
        assert _run(src, tmp, "2026-10-28 03:00") == [] and src.calls == calls            # idempotent, no fetch
        nxt = _run(src, tmp, "2026-10-29 00:40")
        assert sorted({r["day"] for r in nxt}) == ["2026-10-28"] and len(nxt) == len(tp.LANES)
        assert (tmp / "out" / "table.md").exists()


def test_reuses_a_complete_current_download_and_refetches_a_partial_one():
    src = FakeSource()
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        now = pd.Timestamp("2026-10-28 00:30", tz="UTC")
        end_ms = int(now.normalize().timestamp() * 1000)
        tp.bp.fetch_live(src, tmp / "cache", end_ms, [], min_universe=10)                  # what paper #3 left behind
        calls = src.calls
        assert tp.ensure_data(now, src, tmp / "cache", [], 10)[0] == "reused" and src.calls == calls
        (tmp / "cache" / "C03USDT_D.json").unlink()                                       # a symbol that failed
        assert tp.ensure_data(now, src, tmp / "cache", [], 10)[0] == "fetched"
        later = now + pd.Timedelta(days=1)                                               # yesterday's download
        assert tp.ensure_data(later, src, tmp / "cache", [], 10)[0] == "fetched"


def test_window_weights_equal_full_history_for_every_lane():
    src = _btc_up(FakeSource())
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        _run(src, tmp, "2026-10-28 00:30")
        day = pd.Timestamp("2026-10-27", tz="UTC")
        src.write_full(tmp / "full", int((day + pd.Timedelta(days=1)).timestamp() * 1000))
        P = es.Panel(end=day, cache=tmp / "full")
        doc = json.loads((tmp / "out" / "weights_2026-10-27.json").read_text())
        for lane in tp.LANES:
            full = tp.lane_weights(P, lane).loc[day]
            full = full[full.abs() > 1e-12]
            rec = pd.Series(doc["lanes"][lane]["weights"], dtype=float)
            assert len(rec) > 0 and set(full.index) == set(rec.index), lane          # every lane holds something
            assert (full - rec.reindex(full.index)).abs().max() < 1e-9, lane


def test_random_controls_are_reproducible_and_know_nothing():
    src = FakeSource()
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        src.write_full(tmp / "full", int(pd.Timestamp("2026-10-28", tz="UTC").timestamp() * 1000))
        P = es.Panel(end=pd.Timestamp("2026-10-27", tz="UTC"), cache=tmp / "full")
        a, b = tp.random_score(P, 1), tp.random_score(P, 1)
        assert a.equals(b) and not a.equals(tp.random_score(P, 2))
        assert a[a.index.dayofweek != 6].isna().all().all()                              # Sundays only
        W1, W2 = tp.lane_weights(P, "random_1"), tp.lane_weights(P, "random_2")
        assert not W1.iloc[-1].equals(W2.iloc[-1])
        mom = tp.lane_weights(P, "mom28").iloc[-1]                                      # same book shape
        assert abs(W1.iloc[-1].abs().sum() - mom.abs().sum()) < 1e-9


def test_stage_one_kill_and_selection():
    s1 = (tp.STAGE1_START, tp.STAGE1_END)
    daily = {"mom28": _flat(*s1, 0.0010, seed=1), "listing_short": _flat(*s1, 0.0006, seed=2),
             "btc_trend": _flat(*s1, 0.0015, seed=3), "carry7": _flat(*s1, -0.0005, seed=4)}
    daily["btc_trend"].iloc[10] = -0.20                                                  # one crash: killed
    for i, c in enumerate(tp.CONTROLS):
        daily[c] = _flat(*s1, 0.0, seed=10 + i)
    rows = _rows(daily)
    assert tp.killed(rows) == {"btc_trend"}
    sel = tp.select(rows)
    assert sel["picks"] == ["mom28", "listing_short"]                                   # killed + negative out
    daily["random_1"] = _flat(*s1, 0.0020, seed=20)                                      # a lucky control
    assert tp.select(_rows(daily))["picks"] == []
    with tempfile.TemporaryDirectory() as t:
        out = Path(t)
        partial = [r for r in rows if not (r["day"] == str(tp.STAGE1_END.date()) and r["lane"] == "random_3")]
        assert tp.maybe_select(partial, out, tp.STAGE1_END) == (None, False)            # waits for every lane
        sel, now = tp.maybe_select(rows, out, tp.STAGE1_END)
        assert now and sel["picks"] == ["mom28", "listing_short"]
        again, now = tp.maybe_select(_rows(daily), out, tp.STAGE1_END)                   # written once, never redone
        assert not now and again["picks"] == ["mom28", "listing_short"]


def test_stage_two_holm():
    s2 = (tp.STAGE2_START, tp.STAGE2_END)
    strong = _alt(*s2, 10.0)
    weak = _alt(*s2, 1.0)
    running = _rows({"mom28": strong[:50], "carry7": weak[:50]})
    assert {v[0] for v in tp.stage2(running, ["mom28", "carry7"]).values()} == {"RUNNING"}
    out = tp.stage2(_rows({"mom28": strong, "carry7": weak}), ["mom28", "carry7"])
    assert out["mom28"][0] == "PASS" and out["carry7"][0] == "FAIL"
    crash = weak.copy()
    crash.iloc[20] = -0.30
    assert tp.stage2(_rows({"mom28": strong[:40], "carry7": crash[:40]}), ["mom28", "carry7"])["carry7"][0] == "FAIL"
    # Holm with t = 1.8 (p ≈ 0.036): enough alone (≤ α), not as the best of two (> α/2), enough as the second.
    mid = _alt(*s2, 1.8)
    assert 0.025 < tp.window_stats(mid)["p"] < 0.05
    assert tp.stage2(_rows({"mom28": mid}), ["mom28"])["mom28"][0] == "PASS"
    two = tp.stage2(_rows({"mom28": mid, "carry7": _alt(*s2, 1.8)}), ["mom28", "carry7"])
    assert {v[0] for v in two.values()} == {"FAIL"}
    both = tp.stage2(_rows({"mom28": strong, "carry7": mid}), ["mom28", "carry7"])
    assert both["mom28"][0] == "PASS" and both["carry7"][0] == "PASS"


def test_lane_status_through_the_stages():
    rows = _rows({x: _flat(tp.START_DAY, tp.STAGE1_START - pd.Timedelta(days=1), 0.0) for x in tp.LANES})
    assert tp.lane_status("mom28", rows, None, tp.STAGE1_START - pd.Timedelta(days=1)) == "shakedown"
    wk3 = tp.STAGE1_START + pd.Timedelta(days=15)
    assert tp.lane_status("mom28", rows, None, wk3) == "stage 1 · week 3/13"
    assert tp.lane_status("random_1", rows, None, wk3) == "control"
    sel = {"picks": ["mom28"]}
    assert tp.lane_status("carry7", rows, sel, tp.STAGE2_START + pd.Timedelta(days=3)) == "not selected"
    assert tp.lane_status("mom28", rows, sel, tp.STAGE2_START + pd.Timedelta(days=8)) == "stage 2 · week 2/26"


def test_table_and_telegram_only_when_a_week_completes():
    days = pd.date_range("2026-11-02", "2026-11-08", tz="UTC")
    daily = {x: pd.Series(0.001, index=days) for x in tp.LANES}
    rows = _rows(daily)
    others = {"k56": ("paper #2 momentum k56", "W", pd.Series({pd.Timestamp("2026-11-02", tz="UTC"): 0.02}),
                      "own clock · 1/26 weeks")}
    mid = [r for r in rows if r["day"] == "2026-11-05"]
    assert tp.telegram_text(mid, rows, others, None, [], False) is None
    end = [r for r in rows if r["day"] == "2026-11-08"]
    text = tp.telegram_text(end, rows, others, None, [], False)
    assert "Week 11-02 → 11-08 (stage 1 · week 1/13)" in text and "28-day momentum: +0.70% / +0.70%" in text
    assert "paper #2 momentum k56: +2.00% / +2.00%" in text and "paper only" in text
    assert "KILLED: funding carry 7d" in tp.telegram_text(mid, rows, others, None, ["carry7"], False)
    L, week_end, start = tp.table(rows, others, None)
    assert week_end == days[-1] and start == tp.STAGE1_START and len(L) == 2 + len(tp.LANES) + 1


def test_trade_lanes_convert_r_to_account_percent():
    ts = "2026-11-03T04:02:00+00:00"
    ev = {"run_timestamp_utc": ts, "run_tag": "t1", "results": [
        {"symbol": "AUSDT", "source": "watch", "status": "evaluated", "daily_pick": True, "blended_rr": 1.0,
         "net_blended_rr": 1.0, "checklist": {"score": 6, "derivs_ok": True}},
        {"symbol": "BUSDT", "source": "shadow", "status": "evaluated", "blended_rr": -1.0,
         "net_blended_rr": -1.0, "checklist": {"score": 3, "derivs_ok": True}}]}
    with tempfile.TemporaryDirectory() as t:
        setups = Path(t)
        (setups / "setups_x.json").write_text(json.dumps({"run_timestamp_utc": ts, "run_tag": "t1", "setups": [
            {"symbol": "AUSDT", "source": "watch", "direction": "long", "daily_pick": True}]}))
        lanes = tp.trade_lanes([ev], setups)
    import weekly_review as wr
    mon = pd.Timestamp("2026-11-02", tz="UTC")
    r_net = __import__("weekly_eval")._managed_rr(ev["results"][0])[1]
    assert abs(lanes["daily_book"][2][mon] - r_net * wr.RISK_PCT / 100) < 1e-12
    assert abs(lanes["checklist"][2][mon] - r_net * wr.RISK_PCT / 100) < 1e-12        # score 3 excluded


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"  ✓ {t.__name__}")
    print(f"All {len(tests)} tournament_paper tests passed.")
