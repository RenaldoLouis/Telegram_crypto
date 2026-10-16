"""Behavior tests for monthly_review.py (2026-10-16): the pre-registered decision rules, the
hit-rate band, the forward daily-pick study, the fade check, the figure check, the
recommendation ledger and the facts cadence. Everything runs offline on synthetic evals.

Run: venv/bin/python test_monthly_review.py
"""

import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import monthly_review as mr

NOW = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)
START = NOW - timedelta(days=20)   # inside the v2 era (starts 2026-09-23)


def _res(symbol, sig="range_reversion_short", source="watch", direction="short", profitable=True, net=0.5, rank=1):
    return {"status": "evaluated", "symbol": symbol, "signal_name": sig, "source": source, "direction": direction,
            "profitable": profitable, "net_blended_rr": net, "blended_rr": net + 0.1, "rank": rank,
            "eval_engine": "v2_market_open"}


def _ev(ts, results, tag=None):
    return {"run_tag": tag or ts.strftime("%Y%m%d_%H%M"), "run_timestamp_utc": ts.isoformat(), "results": results}


def _book(n, wins, sig="range_reversion_short", source="watch", start=START, step_h=8):
    return [_ev(start + timedelta(hours=step_h * i),
                [_res(f"S{i}USDT", sig=sig, source=source, profitable=i < wins, net=0.5 if i < wins else -0.6)])
            for i in range(n)]


def _surf(evs):
    return mr.v2_rows(mr.collect(evs), mr.SURFACED)


def _patch_paths(tmp):
    t = Path(tmp)
    mr.OUT_DIR = t / "monthly"
    mr.XS_SCORES = t / "xs" / "scores.jsonl"
    mr.REPORT_DIR = t / "reports"
    mr.COVERAGE = t / "keeper" / "coverage.jsonl"
    mr.SETUPS_DIR = t / "setups"
    for p in (mr.OUT_DIR, mr.REPORT_DIR, mr.SETUPS_DIR):
        p.mkdir(parents=True, exist_ok=True)


def test_forward_test_1_follows_the_pre_registered_rule():
    d = lambda evs, now=NOW: mr.forward_test_1(_surf(evs), now)["decision"]
    assert d(_book(3, 2)).startswith("BUILDING (3/30)")
    assert d(_book(21, 12)).startswith("KILL")                      # 57% after n=20
    assert d(_book(21, 13)).startswith("BUILDING (21/30)")           # 61.9%: no kill
    assert d(_book(30, 22)).startswith("PROMOTE")                    # 73.3%, net>0
    assert d(_book(30, 20)).startswith("EXTEND")                     # 66.7%
    assert d(_book(30, 15)).startswith("RETIRE")                     # 50%
    assert d(_book(3, 2), now=datetime(2027, 1, 2, tzinfo=timezone.utc)).startswith("EXPIRED")
    # a shadow-lane copy of the rule never counts toward the frozen test
    assert mr.forward_test_1(_surf(_book(5, 5, source="shadow")), NOW)["n"] == 0
    ft = mr.forward_test_1(_surf(_book(3, 2)), NOW)
    assert ft["n"] == 3 and ft["wins"] == 2 and ft["prof_pct"] == 66.7 and ft["net"] == 0.133
    assert ft["pace_per_week"] > 0 and ft["days_to_expiry"] == 76
    print("  ✓ test_forward_test_1_follows_the_pre_registered_rule")


def test_band_statuses():
    b = lambda n, w, prev=None: mr.band(_surf(_book(n, w)), prev)["status"]
    assert b(10, 9) == "BUILDING"
    assert b(30, 22) == "GREEN"                    # 73% + net>0
    assert b(30, 19) == "OK"                       # 63%
    assert b(30, 17) == "YELLOW"                   # 56.7% once
    assert b(30, 17, prev="YELLOW") == "RED"       # twice in a row
    assert b(30, 17, prev="OK") == "YELLOW"
    assert b(30, 12) == "RED"                      # 40%: red even on the first look
    # the window is the LAST 30 trades: 30 losers followed by 30 winners reads GREEN
    evs = _book(30, 0, start=START) + _book(30, 30, start=START + timedelta(days=12))
    assert mr.band(_surf(evs), None)["status"] == "GREEN"
    print("  ✓ test_band_statuses")


def test_daily_pick_uses_the_fixed_backtest_priority():
    day = START + timedelta(days=1)
    evs = [_ev(day, [_res("AAA", sig="failed_breakout_short", source="shadow", rank=1, profitable=False, net=-0.6)]),
           _ev(day + timedelta(hours=4), [_res("BBB", sig="range_reversion_short", source="shadow", rank=2, profitable=True, net=0.4),
                                          _res("CCC", sig="rsi_bounce_long", source="shadow", direction="long", profitable=False, net=-0.3)])]
    dp = mr.daily_pick_study(mr.v2_rows(mr.collect(evs)), NOW)
    assert dp["priority"][0] == "range_reversion_short", dp["priority"]
    best = dp["policies"]["best_rule_each_day"]
    assert best["n"] == 1 and best["wins"] == 1 and best["days_with_pick"] == 1       # BBB wins the day
    assert dp["policies"]["longs_only"]["wins"] == 0
    assert dp["policies"]["only_failed_breakout_short"]["n"] == 1
    print("  ✓ test_daily_pick_uses_the_fixed_backtest_priority")


def test_backtest_fade_reads_the_latest_trade_log():
    with tempfile.TemporaryDirectory() as tmp:
        _patch_paths(tmp)
        assert "note" in mr.backtest_fade(NOW)
        def tr(month, i, prof, vol=2.0):
            return {"signal": "range_reversion_short", "tf": "4h", "vol_spike": vol, "signal_time": f"{month}-{10 + i:02d}T00:00",
                    "result": {"profitable": prof, "net_blended_rr": 0.4 if prof else -0.5}}
        trades = [tr("2026-08", i, i < 4) for i in range(5)] + [tr("2026-09", i, i < 2) for i in range(5)]
        trades.append(tr("2026-09", 9, True, vol=1.0))      # below the volume gate: ignored
        (mr.REPORT_DIR / "unified_20261001_trades.json").write_text(json.dumps(trades))
        bf = mr.backtest_fade(NOW)
        assert bf["freshness"] == "fresh" and bf["age_days"] == 15
        assert bf["all"]["n"] == 10 and bf["latest_month"] == "2026-09"
        assert bf["latest"]["prof_pct"] == 40.0 and bf["prior_months"]["prof_pct"] == 80.0
        assert bf["fading"] is True
    print("  ✓ test_backtest_fade_reads_the_latest_trade_log")


def test_paper_test_2_filters_on_the_frozen_rules_hash():
    import xs_momentum_paper as xp
    with tempfile.TemporaryDirectory() as tmp:
        _patch_paths(tmp)
        h = xp.rules_hash()
        mr.XS_SCORES.parent.mkdir(parents=True)
        rows = [{"week": "2026-10-05", "book": "k56", "rules_hash": h, "net": 0.03},
                {"week": "2026-10-12", "book": "k56", "rules_hash": h, "net": -0.01},
                {"week": "2026-10-12", "book": "k56", "rules_hash": "deadbeef00000000", "net": 0.5},
                {"week": "2026-10-05", "book": "k91", "rules_hash": h, "net": 0.007}]
        mr.XS_SCORES.write_text("".join(json.dumps(r) + "\n" for r in rows))
        pt = mr.paper_test_2()
        assert pt["books"]["k56"]["n_weeks"] == 2 and pt["books"]["k56"]["verdict"].startswith("BUILDING (2/26)")
        assert pt["books"]["k91"]["n_weeks"] == 1 and pt["books"]["k56"]["weeks"][0]["net_pct"] == 3.0
    print("  ✓ test_paper_test_2_filters_on_the_frozen_rules_hash")


def test_facts_cadence_and_render():
    with tempfile.TemporaryDirectory() as tmp:
        _patch_paths(tmp)
        evs = _book(3, 2) + _book(6, 3, sig="failed_breakout_short", source="shadow", start=START + timedelta(days=2))
        jp = mr.maybe_write_facts(evs, now=NOW)
        assert jp and jp.name == "facts_2026-10-16.json" and jp.with_suffix(".md").exists()
        assert mr.maybe_write_facts(evs, now=NOW + timedelta(days=10)) is None            # not due
        assert mr.maybe_write_facts(evs, now=NOW + timedelta(days=31)) is not None        # due
        assert mr.maybe_write_facts(evs, force=True, now=NOW) is not None                 # forced, same date
        hist = mr._read_jsonl(mr._band_history())
        assert [h["date"] for h in hist] == ["2026-10-16", "2026-11-16"], hist            # same-date rewrite, no dup
        facts = json.loads(jp.read_text())
        md = mr.render_md(facts)
        assert "## 1. Forward test #1" in md and "BUILDING (3/30)" in md and "## 5. Daily-pick study" in md
        assert facts["forward_test_1"]["n"] == 3 and facts["band"]["status"] == "BUILDING"
        assert facts["shadow_lane"]["by_signal"]["failed_breakout_short"]["all"]["n"] == 6
        assert facts["previous_review"] is None
        later = json.loads((mr.OUT_DIR / "facts_2026-11-16.json").read_text())
        assert later["previous_review"]["date"] == "2026-10-16"
    print("  ✓ test_facts_cadence_and_render")


def test_figure_check_flags_only_unsupported_numbers():
    with tempfile.TemporaryDirectory() as tmp:
        _patch_paths(tmp)
        facts = mr.build_facts(_book(3, 2), NOW)
        ft = facts["forward_test_1"]
        ok = (f"Forward test #1 stands at n={ft['n']} with {ft['prof_pct']}% profitable and {ft['net']:+.3f}R, "
              f"2 of 3 green; expiry 2026-12-31 (76 days). Decision at n=30; kill rule <60% after 20. "
              f"Grade R-2026-09-16-1: inconclusive. Fired at 04:02 on the 4h chart, v13.0.\n```json\n{{\"x\": 12345}}\n```")
        assert mr.check_figures(ok, facts) == [], mr.check_figures(ok, facts)
        bad = mr.check_figures("The rule is now 92.4% profitable with +0.777R over 123 trades.", facts)
        assert [t for t, _ in bad] == ["92.4", "+0.777", "123"], bad
    print("  ✓ test_figure_check_flags_only_unsupported_numbers")


def test_ledger_ingest_and_grading():
    with tempfile.TemporaryDirectory() as tmp:
        _patch_paths(tmp)
        review1 = ('text\n```json\n{"recommendations": [{"claim": "shorts beat longs", "test": "unified_backtest shorts-only",'
                   ' "would_be_wrong_if": "longs >= shorts on TEST", "lane": "research"}, {"claim": "second"}], "grades": []}\n```')
        assert mr.ingest(review1, "2026-10-16") == (2, 0)
        assert mr.ingest(review1, "2026-10-16") == (0, 0)                      # idempotent per tag
        opens = mr.open_recommendations()
        assert [r["id"] for r in opens] == ["R-2026-10-16-1", "R-2026-10-16-2"]
        review2 = ('```json\n{"recommendations": [], "grades": [{"id": "R-2026-10-16-1", "grade": "supported", "evidence": "n=40"},'
                   ' {"id": "R-2026-10-16-2", "grade": "inconclusive", "evidence": "n=3"}, {"id": "R-nope", "grade": "refuted"}]}\n```')
        assert mr.ingest(review2, "2026-11-16") == (0, 2)
        led = {r["id"]: r for r in mr._read_jsonl(mr._ledger())}
        assert led["R-2026-10-16-1"]["status"] == "supported" and led["R-2026-10-16-2"]["status"] == "open"
        assert len(mr.open_recommendations()) == 1
        assert mr.ingest("no block here", "2026-12-16") == (0, 0)
    print("  ✓ test_ledger_ingest_and_grading")


if __name__ == "__main__":
    cwd = os.getcwd()
    test_forward_test_1_follows_the_pre_registered_rule()
    test_band_statuses()
    test_daily_pick_uses_the_fixed_backtest_priority()
    test_backtest_fade_reads_the_latest_trade_log()
    test_paper_test_2_filters_on_the_frozen_rules_hash()
    test_facts_cadence_and_render()
    test_figure_check_flags_only_unsupported_numbers()
    test_ledger_ingest_and_grading()
    os.chdir(cwd)
    print("All 8 monthly-review tests passed.")
