"""Behavior tests for edge_search — the booking engine, the point-in-time panel, the holdout
lock and the rising Sharpe bar (synthetic data, no network).

Run: venv/bin/python test_edge_search.py
"""

import json
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

import edge_search as es

DAY = 86_400_000


def frames(closes, turnover=1e9, funding=None, start="2023-01-01"):
    """closes: {sym: [close per day, None = no bar]} → a Panel."""
    n = len(next(iter(closes.values())))
    idx = pd.date_range(start, periods=n, freq="D", tz="UTC")
    close = pd.DataFrame({s: pd.Series(v, index=idx, dtype=float) for s, v in closes.items()})
    turn = pd.DataFrame(turnover, index=idx, columns=close.columns).where(close.notna())
    fund = pd.DataFrame(0.0, index=idx, columns=close.columns)
    for (s, day), rate in (funding or {}).items():
        fund.iloc[day, fund.columns.get_loc(s)] = rate
    return es.from_frames(close, turn, fund)


def test_run_weights_books_return_funding_and_costs():
    P = frames({"A": [100, 110, 110, 110]}, funding={("A", 1): 0.001})
    W = pd.DataFrame({"A": [1.0, 1.0, 0.0, 0.0]}, index=P.close.index)
    r = es.run_weights(P, W)
    c = es.TAKER + es.SLIP_TIERS[0][1]                    # $1B turnover → the liquid tier
    assert abs(r.iloc[0] + c) < 1e-12                       # bought at day 0's close
    assert abs(r.iloc[1] - (0.10 - 0.001)) < 1e-12          # held over day 1: +10%, pays funding
    assert abs(r.iloc[2] - (0.0 - c)) < 1e-12               # sold at day 2's close (held over day 2: flat)
    assert r.iloc[3] == 0.0


def test_a_coin_that_stops_trading_is_closed_at_its_last_close():
    P = frames({"A": [100, 90, None, None], "B": [1, 1, 1, 1]})
    W = pd.DataFrame({"A": [-1.0] * 4, "B": [0.0] * 4}, index=P.close.index)
    r = es.run_weights(P, W)
    c = es.TAKER + es.SLIP_TIERS[0][1]
    assert abs(r.iloc[1] - (0.10)) < 1e-12                  # short gained 10%
    # Day 2 has no price: no return, the position is closed at the coin's own (still liquid) tier.
    assert abs(r.iloc[2] + c) < 1e-12 and r.iloc[3] == 0.0
    assert abs(r.iloc[0] + c) < 1e-12


def test_hold_weekly_keeps_the_sunday_weights():
    idx = pd.date_range("2024-01-01", periods=15, freq="D", tz="UTC")      # Monday
    W = pd.DataFrame({"A": np.arange(15, dtype=float)}, index=idx)
    H = es.hold_weekly(W)
    assert (H["A"].iloc[:6] == 0).all()                    # before the first Sunday close
    assert (H["A"].iloc[6:13] == 6).all() and (H["A"].iloc[13:] == 13).all()


def test_xs_book_longs_the_top_and_shorts_the_bottom():
    n_days = 40
    closes = {f"C{i:02d}": [100.0] * n_days for i in range(30)}
    P = frames(closes)
    score = pd.DataFrame({s: float(i) for i, s in enumerate(closes)}, index=P.close.index)
    W = es.xs_book(P, score, 0.1, weekly=False)
    last = W.iloc[-1]
    assert (last[["C27", "C28", "C29"]] == 0.5 / 3).all() and (last[["C00", "C01", "C02"]] == -0.5 / 3).all()
    assert abs(last.abs().sum() - 1.0) < 1e-12 and (last.iloc[3:27] == 0).all()
    assert (W.iloc[:es.MIN_AGE_DAYS - 1] == 0).all().all()  # nothing is eligible before 30 days of history


def test_new_listing_short_window_cap_and_hedge():
    closes = {"BTCUSDT": [100.0] * 60, "NEW": [None] * 10 + [5.0] * 50}
    P = frames(closes)
    W = es.f_new_listing_short(P, delay=1, hold=14, hedge=True)
    first = P.close.index[10]
    active = W["NEW"][W["NEW"] < 0]
    assert active.index[0] == first + pd.Timedelta(days=1) and len(active) == 14
    assert (active == -0.1).all() and (W.loc[active.index, "BTCUSDT"] == 0.1).all()


def test_sharpe_bar_rises_with_the_number_of_trials():
    assert es.sharpe_bar(1, 4) == 1.0
    assert es.sharpe_bar(76, 4) > es.sharpe_bar(20, 4) > 1.0
    assert abs(es.sharpe_bar(76, 4) - np.sqrt(2 * np.log(76)) / 2) < 1e-12


def test_panel_cut_never_reads_holdout_rows():
    with tempfile.TemporaryDirectory() as tmp:
        cache = Path(tmp)
        t0 = int(pd.Timestamp("2024-12-29", tz="UTC").timestamp() * 1000)
        rows = [[t0 + i * DAY, 1, 1, 1, 100 + i, 1, 1e9] for i in range(6)]           # 12-29 → 01-03
        (cache / "instruments.json").write_text(json.dumps({"instruments": [{"symbol": "X", "launchTime": t0}]}))
        (cache / "X_D.json").write_text(json.dumps(rows))
        # Settlement at 01-01 00:00 belongs to day 12-31 (held over it); 01-01 08:00 is holdout.
        jan1 = int(pd.Timestamp("2025-01-01", tz="UTC").timestamp() * 1000)
        (cache / "X_funding.json").write_text(json.dumps([[jan1, 0.0005], [jan1 + 8 * 3_600_000, 0.9]]))
        (cache / "X_oi.json").write_text(json.dumps([[t0 + 2 * DAY, 500.0], [jan1, 9e9]]))
        old = es.CACHE
        es.CACHE = cache
        try:
            P = es.Panel(end=es.DISCOVERY_END)
        finally:
            es.CACHE = old
        assert P.close.index.max() == es.DISCOVERY_END and P.close["X"].iloc[-1] == 102
        assert P.fund["X"].iloc[-1] == 0.0005 and P.fund["X"].sum() == 0.0005
        assert P.oi["X"].max() == 500.0 and P.oi["X"].iloc[-1] == 500.0      # 2025 open interest never loaded


def test_confirm_refuses_without_committed_finalists():
    old = es.FINALISTS
    with tempfile.TemporaryDirectory() as tmp:
        es.FINALISTS = Path(tmp) / "edge_finalists.json"
        es.FINALISTS.write_text("{}")
        try:
            es.cmd_confirm(None)
            raise AssertionError("confirm ran without committed finalists")
        except SystemExit as e:
            assert "Refusing" in str(e)
        finally:
            es.FINALISTS = old


def test_finalist_bar():
    good = {"sharpe": 2.0, "years": 4, "green_pct": 0.7, "dd_20v": 0.1, "alpha_t": 3.0,
            "years_20v": {"2021": 0.2, "2022": 0.1, "2023": 0.05, "2024": -0.02}}
    assert es.finalist_checks(good, 50) == (True, [])
    ok, miss = es.finalist_checks(dict(good, years_20v={"2021": 0.2, "2022": -0.2, "2023": 0.1, "2024": 0.1}), 50)
    assert not ok and any("worst year" in m for m in miss)
    assert not es.finalist_checks(dict(good, sharpe=1.4), 76)[0]


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"  ✓ {t.__name__}")
    print(f"All {len(tests)} edge_search tests passed.")
