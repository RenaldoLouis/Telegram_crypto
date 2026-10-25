"""Behavior tests for playbook_study — the booking engine and the fill rules the verdict
rests on (synthetic bars, no cache, no network).

Run: venv/bin/python test_playbook_study.py
"""

import playbook_study as pb

START = 1_700_006_400_000                  # 2023-11-15 00:00 UTC
COST = pb.SIDE_COST


def grid(n_bars):
    return [START + i * pb.H4_MS for i in range(n_bars)]


def series(g, ohlc, fund=()):
    """ohlc: one (o, h, l, c) per grid bar; fund: (bar, rate) settlements."""
    rows = [[str(t), o, h, l, c, "0", "0"] for t, (o, h, l, c) in zip(g, ohlc)]
    return pb.build_series(g, rows, [[g[b], r] for b, r in fund])


def flat(n, px=100.0):
    return [(px, px, px, px)] * n


def test_trade_books_to_its_net_return():
    g = grid(12)
    bars = flat(12)
    bars[1:5] = [(100, 101, 99, 102), (102, 104, 101, 103), (103, 106, 102, 105), (105, 111, 104, 108)]
    p = series(g, bars, fund=[(1, 0.002), (2, 0.001)])
    for side in (1, -1):
        t = {"side": side, "entry_bar": 1, "entry_px": 100.0, "exit_bar": 4, "exit_px": 110.0, "weight": 0.5}
        # The settlement at the entry bar's start is not paid; the one inside the hold is.
        expected = side * 0.10 - COST * (1 + 1.1) - side * 0.001
        assert abs(pb.trade_net(t, p) - expected) < 1e-12
        pnl = [0.0] * 12
        pb.book_trade(pnl, t, p)
        assert abs(sum(pnl) - 0.5 * expected) < 1e-12, (sum(pnl), expected)
        assert pnl[5:] == [0.0] * 7


def test_positions_pay_turnover_and_funding_held_across():
    g = grid(6)
    p = series(g, [(100, 100, 100, 100), (100, 110, 100, 110), (110, 121, 110, 121), (121, 121, 121, 121),
                   (121, 121, 121, 121), (121, 121, 121, 121)], fund=[(1, 0.005), (2, 0.001)])
    pnl = [0.0] * 6
    pb.book_positions(pnl, {"X": [0.0, 1.0, 1.0, 0.0, 0.0, 0.0]}, {"X": p})
    # Entry at bar 1 (cost, no funding: not held across its start), held across bar 2's
    # settlement (paid), exit at bar 3 (cost).
    assert abs(pnl[1] - (0.10 - COST)) < 1e-12
    assert abs(pnl[2] - (0.10 - 0.001)) < 1e-12
    assert abs(pnl[3] + COST) < 1e-12 and pnl[4] == pnl[5] == 0.0


def test_vol_breakout_fills_at_trigger_gap_and_skips_two_sided_bars():
    g = grid(12)
    day0 = [(100, 110, 90, 100)] * 6                       # yesterday's range 20 → triggers 110 / 90
    cases = {
        "A": [(100, 105, 95, 100), (100, 111, 99, 108)] + [(108, 109, 107, 108)] * 4,
        "B": [(100, 111, 89, 100)] + [(100, 101, 99, 100)] * 5,      # both triggers in one bar
        "C": [(100, 104, 96, 100), (112, 113, 111, 112)] + [(112, 113, 111, 115)] * 4,   # gap above
    }
    panel = {k: series(g, day0 + v) for k, v in cases.items()}
    trades = {t["sym"]: t for t in pb.s_vol_breakout(panel, g)}
    assert trades["A"]["side"] == 1 and trades["A"]["entry_px"] == 110 and trades["A"]["entry_bar"] == 7
    assert trades["A"]["exit_bar"] == 11 and trades["A"]["exit_px"] == 108 and trades["A"]["reason"] == "close"
    assert trades["C"]["entry_px"] == 112 and trades["C"]["exit_px"] == 115
    # B crossed both triggers in one bar: booked as the side that loses more (short 90 → close 100).
    assert trades["B"]["side"] == -1 and trades["B"]["entry_px"] == 90 and trades["B"]["exit_px"] == 100
    assert {t["sym"] for t in pb.s_vol_breakout(panel, g, two_sided="skip")} == {"A", "C"}


def test_orb_two_sided_bar_is_a_stopped_out_loss():
    g = grid(6)
    bars = [(100, 101, 99, 100), (100, 102, 98, 100)] + flat(4)
    (t,) = pb.s_orb({"X": series(g, bars)}, g)
    assert (t["side"], t["entry_px"], t["exit_px"], t["exit_bar"]) == (-1, 99, 101, 1)
    assert pb.trade_net(t, series(g, bars)) < -0.02
    assert pb.s_orb({"X": series(g, bars)}, g, two_sided="skip") == []


def test_orb_stop_watched_from_the_bar_after_the_trigger():
    g = grid(6)
    bars = [(100, 101, 99, 100), (100, 102, 100, 101.5), (101.5, 101.6, 98.5, 99), (99, 99, 99, 99),
            (99, 99, 99, 99), (99, 99, 99, 99)]
    (t,) = pb.s_orb({"X": series(g, bars)}, g)
    assert t["side"] == 1 and t["entry_px"] == 101 and t["entry_bar"] == 1
    assert t["reason"] == "stop" and t["exit_bar"] == 2 and abs(t["exit_px"] - 99) < 1e-9


def test_bracket_counts_a_two_sided_bar_as_the_stop():
    g = grid(6)
    ctx = {"target_dist": 0.05, "stop_dist": 0.05, "last": 4}
    bar, px, why = pb.exit_bracket(series(g, [(100, 101, 99, 100), (100, 106, 94, 100)] + flat(4)), 0, 100.0, 1, ctx)
    assert (bar, why) == (1, "stop") and abs(px - 95) < 1e-9
    bar, px, why = pb.exit_bracket(series(g, [(100, 101, 99, 100), (100, 106, 99, 104)] + flat(4)), 0, 100.0, 1, ctx)
    assert (bar, why) == (1, "target") and abs(px - 105) < 1e-9
    assert pb.exit_bracket(series(g, flat(6)), 0, 100.0, -1, ctx) == (4, 100.0, "time")


def test_tsmom_uses_only_closes_before_the_day():
    days = 40
    g = grid(days * pb.BPD)
    up = [(100 + i, 101 + i, 99 + i, 100 + i + 0.5 * (i % 3)) for i in range(len(g))]
    down = [(500 - i, 501 - i, 499 - i, 500 - i - 0.3 * (i % 4)) for i in range(len(g))]
    base = pb.w_tsmom({"U": series(g, up), "D": series(g, down)}, g)
    # Rewrite day 35 onwards of one coin: the weights of day 35 must not move.
    cut = 35 * pb.BPD
    shocked = up[:cut] + [(o * 0.5, h * 0.5, l * 0.5, c * 0.5) for o, h, l, c in up[cut:]]
    after = pb.w_tsmom({"U": series(g, shocked), "D": series(g, down)}, g)
    assert base["U"][cut:cut + pb.BPD] == after["U"][cut:cut + pb.BPD]
    assert base["U"][cut] > 0 > base["D"][cut]
    assert abs(abs(base["U"][cut]) + abs(base["D"][cut]) - 1) < 1e-12
    longs = pb.w_tsmom({"U": series(g, up), "D": series(g, down)}, g, long_only=True)
    assert longs["U"][cut] == base["U"][cut] and longs["D"][cut] == 0.0


def test_metrics_count_green_red_and_flat_months():
    days = 31 + 31 + 30                                    # 2023-11-15 → 2024-02-15
    g = grid(days * pb.BPD)
    daily = [0.0] * days
    daily[1] = 0.02                                        # November green
    daily[20] = -0.01                                      # December red
    m = pb.metrics(daily, range(days), g)
    assert (m["green"], m["red"], m["flat"]) == (1, 1, m["months"] - 2)
    assert abs(m["net"] - 0.01) < 1e-12 and abs(m["dd"] - 0.01) < 1e-12


def test_verdict_follows_the_preregistered_bar():
    good = {"net": 0.1, "sharpe": 1.5, "green_pct": 0.7, "dd": 0.1}
    assert pb.verdict("A1", {"net": 0.05}, good, True)[0] == "PASS"
    assert pb.verdict("A1", {"net": -0.05}, good, True)[0] == "NO"
    assert pb.verdict("C3", {"net": -0.05}, good, True)[0] == "PASS"     # C3's TRAIN is in-sample
    assert pb.verdict("A1", {"net": 0.05}, good, False)[0] == "CANDIDATE"
    assert pb.verdict("A1", {"net": 0.05}, dict(good, green_pct=0.5), True)[0] == "NO"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"  ✓ {t.__name__}")
    print(f"All {len(tests)} playbook_study tests passed.")
