"""Offline tests for fbs_selection.py (the live-selection replay study, 2026-11-02)."""

import unittest
from unittest import mock

import config
import fbs_selection as fs

H4, DAY = fs.H4_MS, fs.DAY_MS


def _rows(n, start=0, price=1.0, turnover=5e6, step=0.0):
    """n contiguous 4h bars [t, o, h, l, c, vol, turnover]; close drifts by `step` per bar."""
    out = []
    for i in range(n):
        p = price + step * i
        out.append([start + i * H4, p, p * 1.01, p * 0.99, p, 1000.0, turnover])
    return out


class FakeCoin(fs.Coin):
    def __init__(self, sym, rows, funding=0.0001, oi=1e9):
        self.sym, self.rows = sym, rows
        self.close_ts = [int(r[0]) + H4 for r in rows]
        self.pos = {t: i for i, t in enumerate(self.close_ts)}
        self.f_ts, self.f_v = [0], [funding]
        self.o_ts, self.o_v = [0], [oi]


class TickerAt(unittest.TestCase):
    def test_24h_values_from_six_bars(self):
        c = FakeCoin("AUSDT", _rows(10, price=100.0, turnover=2e6, step=1.0))
        t = c.close_ts[8]
        x = c.ticker_at(t)
        self.assertAlmostEqual(x["turnover_24h_usd"], 12e6)            # six bars × $2M
        self.assertAlmostEqual(x["price_change_24h_pct"], (108 / 102 - 1) * 100)
        self.assertAlmostEqual(x["funding_rate_pct"], 0.01)              # rate × 100, as the ticker
        self.assertEqual(x["open_interest"], 1e9)                        # coins, not dollars

    def test_gap_returns_none(self):
        rows = _rows(10)
        del rows[5]                                                      # a missing bar inside 24h
        c = FakeCoin("AUSDT", rows)
        self.assertIsNone(c.ticker_at(c.close_ts[7]))


class Selection(unittest.TestCase):
    def test_watchlist_and_hot_first_then_cap(self):
        # 40 liquid coins + BTC with a coin-count OI below 50M (disqualified by the live rule,
        # kept because it is on the watchlist)
        coins = {f"C{i}USDT": FakeCoin(f"C{i}USDT", _rows(20, turnover=50e6 + i * 1e6)) for i in range(40)}
        coins["BTCUSDT"] = FakeCoin("BTCUSDT", _rows(20, turnover=900e6), oi=60_000)
        t = coins["BTCUSDT"].close_ts[12]
        with mock.patch.object(config, "WATCHLIST", ["BTCUSDT"]):
            sel = fs.replay_selection(coins, [t])
        picked, turn = sel[t]
        self.assertIn("BTCUSDT", picked)
        self.assertEqual(len(picked), config.TOP_MOVERS_LIMIT)
        # equal scores → the higher-turnover coins fill the slots (stable sort, as live)
        self.assertIn("C39USDT", picked)
        self.assertNotIn("C0USDT", picked)

    def test_hot_coin_bypasses_liquidity_and_expires(self):
        coins = {"BTCUSDT": FakeCoin("BTCUSDT", _rows(40, turnover=900e6))}
        # a coin with OI (coins) below 50M → disqualified unless hot; funding squeeze at one close
        rows = _rows(40, price=1.0, turnover=40e6, step=0.0)
        for i in range(14, 20):
            rows[i][4] = 1.1                                             # +10% move inside 24h
        coins["SQZUSDT"] = FakeCoin("SQZUSDT", rows, funding=0.001, oi=1e6)
        closes = coins["BTCUSDT"].close_ts[8:40]
        with mock.patch.object(config, "WATCHLIST", ["BTCUSDT"]):
            sel = fs.replay_selection(coins, closes)
        flagged = [t for t in closes if "SQZUSDT" in sel[t][0]]
        self.assertTrue(flagged)
        # |24h move| > 3% at bars 14..25 (up to 1.1, then back down to 1.0) → flagged at 12 closes;
        # each flag keeps the coin for 48h (window (t − 48h, t]) → hot from bar 14 to bar 25 + 44h.
        self.assertEqual(max(flagged) - min(flagged), 11 * H4 + fs.HOT_WINDOW_MS - H4)
        self.assertNotIn("SQZUSDT", sel[closes[-1]][0])                  # expired after 48h


class TradesAndStats(unittest.TestCase):
    def test_dedup_per_coin_two_days(self):
        xs = [{"sym": "A", "t": 0}, {"sym": "A", "t": DAY}, {"sym": "B", "t": DAY},
              {"sym": "A", "t": 2 * DAY + 1}]
        self.assertEqual([(x["sym"], x["t"]) for x in fs.dedup(xs)], [("A", 0), ("B", DAY), ("A", 2 * DAY + 1)])

    def test_entry_waits_for_scan_lag(self):
        m15 = [[i * fs.M15_MS, 100.0 - i * 0.01, 100.5 - i * 0.01, 99.5 - i * 0.01, 100.0 - i * 0.01, 1, 1]
               for i in range(400)]
        sim = fs.Sim(m15)
        bar_t = 10 * fs.M15_MS
        captured = {}
        with mock.patch.object(fs.ub, "sim_trade", side_effect=lambda t: captured.update(t) or
                               {"net_blended_rr": 0.1}):
            net, k = sim.short(bar_t, stop=101.0, atr=1.0)
        self.assertEqual(net, 0.1)
        self.assertAlmostEqual(captured["entry"], m15[11][1])            # the 15m bar AFTER close + 2 min
        self.assertEqual(len(captured["_fwd"]), fs.WINDOW)

    def test_quality(self):
        q = fs.quality([1.0, -0.5, 0.5], [0, 0, 8 * DAY])
        self.assertAlmostEqual(q["pf"], 3.0)
        self.assertEqual(q["weeks"], 2)


if __name__ == "__main__":
    unittest.main()
