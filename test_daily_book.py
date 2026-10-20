"""Behavior tests for the daily trader book (2026-10-19): pick selection, the liquidation
summary, the weekly review and the daily brief layout.

Run: venv/bin/python test_daily_book.py
"""

import json
import os
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

import carry_monitor
import config
import liq_summary
import main
import weekly_review
from delivery.telegram_bot import format_mechanical_brief

H = 3_600_000


def _cand(symbol, sig, direction="short", rank=1, source="shadow"):
    return {"symbol": symbol, "signal_name": sig, "signal_tf": "4h", "direction": direction,
            "rank": rank, "source": source, "signal_expectancy": 0.55, "signal_test_n": 112,
            "entry_low": 1.0, "entry_high": 1.0, "stop_loss": 1.1, "target_1": 0.925,
            "target_2": 0.85, "predicted_rr": 0.75, "reasoning": {"key_factor": f"{sig} on 4h"}}


def test_select_daily_picks_cap_priority_and_filters():
    prev = (config.DAILY_BOOK_ENABLED, config.DAILY_PICKS_MAX, config.DAILY_DIRECTIONS,
            config.DAILY_DISABLED_SIGNALS)
    config.DAILY_BOOK_ENABLED, config.DAILY_PICKS_MAX = True, 3
    config.DAILY_DIRECTIONS, config.DAILY_DISABLED_SIGNALS = ("long", "short"), ()
    try:
        pri = main._daily_priority()
        assert pri and min(pri, key=pri.get) == "range_reversion_short", pri
        cands = [_cand("AAA", "liquidity_sweep_long", "long"),
                 _cand("BBB", "failed_breakout_short"),
                 _cand("CCC", "range_reversion_short", source="watch"),
                 _cand("DDD", "trend_pullback_short"),
                 _cand("EEE", "rsi_bounce_long", "long")]
        # 1. Priority order within a scan, cap 3: the three best rules win.
        picks = main.select_daily_picks([dict(c) for c in cands], [])
        assert [p["symbol"] for p in picks] == ["CCC", "BBB", "DDD"], picks
        assert [p["daily_pick_seq"] for p in picks] == [1, 2, 3]
        assert picks[0]["source"] == "watch" and picks[1]["source"] == "shadow"   # source unchanged
        # 2. Picks already made today use up the room and their coins.
        already = [{"symbol": "CCC"}, {"symbol": "BBB"}]
        picks = main.select_daily_picks([dict(c) for c in cands], already)
        assert [p["symbol"] for p in picks] == ["DDD"] and picks[0]["daily_pick_seq"] == 3
        assert main.select_daily_picks([dict(c) for c in cands], already + [{"symbol": "ZZZ"}]) == []
        # 3. Direction and signal switches (what a weekly-review cut changes).
        config.DAILY_DIRECTIONS = ("long",)
        assert [p["symbol"] for p in main.select_daily_picks([dict(c) for c in cands], [])] == ["AAA", "EEE"]
        config.DAILY_DIRECTIONS, config.DAILY_DISABLED_SIGNALS = ("long", "short"), ("range_reversion_short",)
        assert main.select_daily_picks([dict(c) for c in cands], [])[0]["symbol"] == "BBB"
        # 4. Off switch.
        config.DAILY_BOOK_ENABLED = False
        assert main.select_daily_picks([dict(c) for c in cands], []) == []
    finally:
        (config.DAILY_BOOK_ENABLED, config.DAILY_PICKS_MAX, config.DAILY_DIRECTIONS,
         config.DAILY_DISABLED_SIGNALS) = prev
    print("  ✓ test_select_daily_picks_cap_priority_and_filters")


def test_daily_picks_today_reads_only_todays_flagged_rows():
    cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as d:
        os.chdir(d)
        try:
            Path("logs/setups").mkdir(parents=True)
            def save(tag, ts, setups):
                Path(f"logs/setups/setups_{tag}.json").write_text(json.dumps(
                    {"run_timestamp_utc": ts, "run_tag": tag, "setups": setups}))
            save("a", "2026-10-19T00:02:00+00:00", [dict(_cand("AAA", "x"), daily_pick=True), _cand("BBB", "x")])
            save("b", "2026-10-19T04:02:00+00:00", [dict(_cand("CCC", "x"), daily_pick=True)])
            save("c", "2026-10-18T20:02:00+00:00", [dict(_cand("OLD", "x"), daily_pick=True)])
            save("d", "2026-10-19T12:02:00+00:00", [dict(_cand("FUT", "x"), daily_pick=True)])  # after run_ts
            out = main._daily_picks_today(datetime(2026, 10, 19, 8, 2, tzinfo=timezone.utc))
            assert [p["symbol"] for p in out] == ["AAA", "CCC"], out
            assert out[0]["_issued_at"] == "00:02 UTC"
        finally:
            os.chdir(cwd)
    print("  ✓ test_daily_picks_today_reads_only_todays_flagged_rows")


def test_liq_summary_side_merge_prune_and_window():
    now = 1_000 * H
    lines = [json.dumps({"t": now - 2 * H + 5, "sym": "BTCUSDT", "side": "Buy", "notional": 100.0}),
             json.dumps({"t": now - 2 * H + 9, "sym": "BTCUSDT", "side": "Sell", "notional": 40.0}),
             json.dumps({"t": now - 30 * H, "sym": "ETHUSDT", "side": "Buy", "notional": 7.0}),
             json.dumps({"t": now - 99 * H, "sym": "ETHUSDT", "side": "Buy", "notional": 1.0}),   # before since
             "not json"]
    hours = liq_summary.aggregate(lines, since_ms=now - 50 * H)
    assert hours[str(now - 2 * H)]["BTCUSDT"] == [100.0, 40.0], hours     # Buy = long liquidated
    assert len(hours) == 2
    s = liq_summary.merge({"sources": {"old": {"since": now - 60 * H, "until": now - 40 * H,
                                               "hours": {str(now - 50 * H): {"BTCUSDT": [9.0, 9.0]}}}}},
                          "run1", now - 30 * H, now, hours, keep_hours=48)
    assert set(s["sources"]) == {"old", "run1"}
    assert s["sources"]["old"]["hours"] == {}                             # pruned hour (> 48h)
    w = liq_summary.window(s, now, 24)
    assert w["by_symbol"]["BTCUSDT"] == [100.0, 40.0] and w["total"] == [100.0, 40.0], w
    assert w["covered_hours"] == 24
    w4 = liq_summary.window(s, now, 4)
    assert w4["total"] == [100.0, 40.0] and w4["covered_hours"] == 4
    # re-summarising the same source replaces it (idempotent), never double counts
    s2 = liq_summary.merge(s, "run1", now - 30 * H, now, hours, keep_hours=48)
    assert liq_summary.window(s2, now, 24)["total"] == [100.0, 40.0]
    # sources that ended before the window → no coverage
    assert liq_summary.window({"sources": {"x": {"since": 0, "until": now - 30 * H, "hours": {}}}},
                              now, 24)["covered_hours"] == 0
    print("  ✓ test_liq_summary_side_merge_prune_and_window")


def _eval_row(symbol, direction, sig, net, profitable):
    return {"status": "evaluated", "symbol": symbol, "direction": direction, "signal_name": sig,
            "source": "shadow", "daily_pick": True, "blended_rr": net + 0.05,
            "net_blended_rr": net, "profitable": profitable, "eval_engine": "v2_market_open"}


def test_weekly_review_statuses_stats_and_cut_rule():
    with tempfile.TemporaryDirectory() as d:
        sd = Path(d)
        picks = [("t1", "2026-10-20T00:02:00+00:00", "AAA", "short", "failed_breakout_short"),
                 ("t2", "2026-10-21T04:02:00+00:00", "BBB", "long", "liquidity_sweep_long"),
                 ("t3", "2026-10-22T08:02:00+00:00", "CCC", "short", "trend_pullback_short"),
                 ("t4", "2026-10-25T20:02:00+00:00", "DDD", "short", "trend_pullback_short")]
        for tag, ts, sym, dr, sig in picks:
            (sd / f"setups_{tag}.json").write_text(json.dumps(
                {"run_timestamp_utc": ts, "run_tag": tag,
                 "setups": [dict(_cand(sym, sig, dr), daily_pick=True), _cand("NOPE", sig)]}))
        evals = [{"run_tag": "t1", "run_timestamp_utc": picks[0][1], "results": [_eval_row("AAA", "short", picks[0][4], 0.40, True)]},
                 {"run_tag": "t2", "run_timestamp_utc": picks[1][1], "results": [_eval_row("BBB", "long", picks[1][4], -1.05, False)]},
                 {"run_tag": "t3", "run_timestamp_utc": picks[2][1], "results": [{"status": "not_filled", "symbol": "CCC", "source": "shadow"}]}]
        got = weekly_review.load_picks(evals, setups_dir=sd)
        assert [(p["symbol"], p["status"]) for p in got] == [("AAA", "scored"), ("BBB", "scored"),
                                                             ("CCC", "not_filled"), ("DDD", "waiting")], got
        prev = (config.DAILY_TRIAL_START, config.DAILY_TRIAL_DAYS)
        config.DAILY_TRIAL_START, config.DAILY_TRIAL_DAYS = "2026-10-19", 14
        try:
            md, actions = weekly_review.build(date(2026, 10, 19), got, today=date(2026, 10, 26))
        finally:
            config.DAILY_TRIAL_START, config.DAILY_TRIAL_DAYS = prev
        assert "Picks made: 4 (scored 2, not filled 1, still inside their 2-day window 1)" in md, md
        assert "**50% profitable**" in md and "decision after the 2026-11-02 review" in md
        assert actions == [] and "No cut this week." in md
        assert "This week" in weekly_review.telegram_text(md) and "Picks this week" not in weekly_review.telegram_text(md)
    # the cut rule itself: >= min_n scored with net < 0 → CUT, else KEEP / building
    rows = [_eval_row(f"L{i}", "long", "liquidity_sweep_long", -0.3, False) for i in range(20)] + \
           [_eval_row(f"S{i}", "short", "failed_breakout_short", 0.2, True) for i in range(5)]
    flags = weekly_review.cut_flags(rows, min_n=20)
    assert flags[("direction", "long")][0] == "CUT" and flags[("setup", "liquidity_sweep_long")][0] == "CUT"
    assert flags[("direction", "short")][0] == "building 5/20"
    print("  ✓ test_weekly_review_statuses_stats_and_cut_rule")


def test_carry_line():
    day = carry_monitor.DAY_MS
    now = int(datetime(2026, 10, 20, tzinfo=timezone.utc).timestamp() * 1000)
    rows = [(now - i * day // 3, 0.0001) for i in range(90)]               # 0.01% every 8h for 30 days
    assert carry_monitor.funding_apr(rows, now, 30) == 10.95
    assert carry_monitor.funding_apr(rows, now, 7) == 10.95
    assert carry_monitor.funding_apr([], now, 7) is None
    ms = lambda y, m, d: int(datetime(y, m, d, 8, tzinfo=timezone.utc).timestamp() * 1000)
    inst = [{"symbol": "BTCUSDT-23OCT26", "contractType": "LinearFutures", "baseCoin": "BTC", "quoteCoin": "USDT", "deliveryTime": ms(2026, 10, 23)},
            {"symbol": "BTCUSDT-27NOV26", "contractType": "LinearFutures", "baseCoin": "BTC", "quoteCoin": "USDT", "deliveryTime": ms(2026, 11, 27)},
            {"symbol": "BTCUSDT-26MAR27", "contractType": "LinearFutures", "baseCoin": "BTC", "quoteCoin": "USDT", "deliveryTime": ms(2027, 3, 26)},
            {"symbol": "BTCUSDT-25DEC26", "contractType": "LinearFutures", "baseCoin": "BTC", "quoteCoin": "USDT", "deliveryTime": ms(2026, 12, 25)},
            {"symbol": "BTCUSD", "contractType": "InversePerpetual", "baseCoin": "BTC", "quoteCoin": "USD", "deliveryTime": 0}]
    assert carry_monitor.next_quarterly(inst, "BTC", now)[0] == "BTCUSDT-25DEC26"   # monthly + < 30 days skipped
    assert carry_monitor.basis_apr(101.0, 100.0, now + 73 * day, now) == 5.0
    data = {"funding": {"BTCUSDT": {"apr_7d": 2.1, "apr_30d": 2.6}, "ETHUSDT": None},
            "quarterly": {"BTC": {"symbol": "BTCUSDT-25DEC26", "days": 66, "apr": 5.6, "turnover_24h": 8e5}, "ETH": None}}
    md, _ = weekly_review.build(date(2026, 10, 19), [], today=date(2026, 10, 26), carry=data)
    assert "BTC perp funding paid to shorts, a year: last 7 days 2.1% · last 30 days 2.6%" in md, md
    assert "ETH perp funding: n/a" in md and "ETH quarterly: n/a" in md
    assert "`BTCUSDT-25DEC26` (66 days to expiry): basis 5.6% a year" in md and "thin, use limit orders" in md
    assert "≈ 6 weeks of BTC's 30-day funding" in md                       # 0.31% / (2.6%/52)
    assert md.index("Keep or cut") < md.index("## Carry") < md.index("Picks this week")
    assert "## Carry" in weekly_review.telegram_text(md)
    md0, _ = weekly_review.build(date(2026, 10, 19), [], today=date(2026, 10, 26), carry=None)
    assert "Data unavailable this week" in md0
    neg = dict(data, funding={"BTCUSDT": {"apr_7d": -1.0, "apr_30d": -0.5}})
    assert "BTC funding is negative" in "\n".join(carry_monitor.format_lines(neg))
    print("  ✓ test_carry_line")


def test_daily_brief_layout():
    ctx = {"price": 67234.5, "chg_24h": 1.23, "turnover_24h": 5.2e9, "funding_pct": 0.01, "oi_chg_24h": 2.1,
           "trend_1d": "bullish", "trend_4h": "bearish", "rsi_1d": 54.2, "adx_1d": 21.0, "vol_ratio_1d": 1.3,
           "prev_high": 68100.0, "prev_low": 66000.0, "high_20d": 70500.0, "low_20d": 61000.0,
           "regime": "neutral", "pct_declining": 60.0, "median_chg": -0.4, "liq_hours_covered": 22,
           "liq_long_24h": 12.3e6, "liq_short_24h": 4.5e6, "liq_long_4h": 1.2e6, "liq_short_4h": 0.3e6,
           "liq_btc_long_24h": 3.1e6, "liq_btc_short_24h": 1.0e6, "liq_coins": 20}
    pick = dict(_cand("SOLUSDT", "failed_breakout_short"), daily_pick=True, daily_pick_seq=2,
                _lane_live={"n": 30, "prof_pct": 70.0, "net": 0.238})
    earlier = [dict(_cand("ETHUSDT", "trend_pullback_short"), daily_pick=True, _issued_at="00:02 UTC")]
    watch_pick = dict(_cand("SANDUSDT", "range_reversion_short", source="watch"), daily_pick=True)
    text = format_mechanical_brief([], "neutral", watch=[watch_pick], daily=[pick], earlier=earlier, context=ctx)
    assert text.index("Market — BTC first") < text.index("Today's Trades") < text.index("Position Management")
    assert "**BTC 67,234.50** (+1.2% 24h) · trend: daily bullish, 4h bearish · daily RSI 54, ADX 21" in text, text
    assert "(20 coins with prints, feed up 22/24 h): longs $12.3M · shorts $4.5M → mostly longs wiped out" in text
    thin = format_mechanical_brief([], "neutral", daily=[], context=dict(ctx, liq_hours_covered=2, liq_coins=1))
    assert "(1 coin with prints, feed up 2/24 h)" in thin and "partial data, no verdict yet" in thin
    assert "### SOLUSDT | Short | `failed_breakout_short` (4h) — pick 2 of 3 today" in text
    assert "backtest 55% profitable (n=112) · live last 30: 70% / +0.24R" in text
    assert "**Earlier today:** ETHUSDT short via `trend_pullback_short` (00:02 UTC)" in text
    assert "2 of 3 picks used today" in text
    assert "Watch Candidate" not in text           # a watch row that is a daily pick is shown once
    quiet = format_mechanical_brief([], "neutral", watch=[], daily=[], earlier=[], context=None)
    assert "no forced trade" in quiet and "Position Management" not in quiet
    # no liquidation coverage → says so instead of printing zeros
    ctx0 = dict(ctx, liq_hours_covered=0)
    assert "no feed data in the last 24h yet" in format_mechanical_brief([], "neutral", daily=[], context=ctx0)
    print("  ✓ test_daily_brief_layout")


if __name__ == "__main__":
    test_select_daily_picks_cap_priority_and_filters()
    test_daily_picks_today_reads_only_todays_flagged_rows()
    test_liq_summary_side_merge_prune_and_window()
    test_weekly_review_statuses_stats_and_cut_rule()
    test_carry_line()
    test_daily_brief_layout()
    print("All 6 daily-book tests passed.")
