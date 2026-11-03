"""Offline tests for orderbook_fade_confirm.py (no network, no depth store)."""
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import orderbook_fade_confirm as fc
import unified_backtest as ub

MS15 = 900_000


def _ms(y, m, d, h=0):
    return int(datetime(y, m, d, h, tzinfo=timezone.utc).timestamp() * 1000)


class FakeClient:
    """Answers get_kline like Bybit: the NEWEST `limit` bars of [start, end], newest first."""

    def __init__(self, first_ms, last_ms, step, fail_after_pages=None):
        self.ts = list(range(first_ms, last_ms + 1, step))
        self.fail_after = fail_after_pages
        self.pages = 0

    def get_kline(self, category, symbol, interval, start, end, limit):
        if self.fail_after is not None and self.pages >= self.fail_after:
            raise RuntimeError("network down")
        self.pages += 1
        rows = [[str(t), "1", "2", "0.5", "1.5", "10", "10"] for t in self.ts if start <= t <= end]
        rows = rows[-limit:]
        rows.reverse()
        return {"result": {"list": rows}}


class FetchWindow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = mock.patch.object(ub, "CACHE_DIR", Path(self.tmp.name))
        self.p.start()

    def tearDown(self):
        self.p.stop()
        self.tmp.cleanup()

    def test_window_bounds_and_cache(self):
        start, end = _ms(2024, 10, 1), _ms(2024, 10, 2)
        client = FakeClient(start - 10 * MS15, end + 10 * MS15, MS15)
        with mock.patch("time.sleep"):
            rows = fc.fetch_window(client, "XUSDT", "15", start, end, tag="t", log=lambda *_: None)
        ts = [int(r[0]) for r in rows]
        self.assertEqual(ts[0], start)
        self.assertEqual(ts[-1], end - MS15)          # the bar closing exactly at `end` is the last one kept
        self.assertEqual(len(ts), 96)
        self.assertEqual(ts, sorted(set(ts)))
        self.assertTrue((Path(self.tmp.name) / "XUSDT_15_t.json").exists())
        # second call is served from the cache without touching the client
        client.pages = 0
        again = fc.fetch_window(client, "XUSDT", "15", start, end, tag="t")
        self.assertEqual(again, rows)
        self.assertEqual(client.pages, 0)

    def test_pages_backwards_over_1000_bars(self):
        start = _ms(2024, 10, 1)
        end = start + 2500 * MS15
        client = FakeClient(start, end, MS15)
        with mock.patch("time.sleep"):
            rows = fc.fetch_window(client, "YUSDT", "15", start, end, tag="t", log=lambda *_: None)
        self.assertEqual(len(rows), 2500)
        self.assertGreater(client.pages, 2)

    def test_failed_page_not_cached(self):
        start = _ms(2024, 10, 1)
        end = start + 2500 * MS15
        client = FakeClient(start, end, MS15, fail_after_pages=1)
        with mock.patch("time.sleep"):
            rows = fc.fetch_window(client, "ZUSDT", "15", start, end, tag="t", log=lambda *_: None)
        self.assertLess(len(rows), 2500)
        self.assertFalse((Path(self.tmp.name) / "ZUSDT_15_t.json").exists())


class Halves(unittest.TestCase):
    def test_boundaries(self):
        self.assertEqual(fc.half_of(fc.WIN_START), "H1")
        self.assertEqual(fc.half_of(fc.WIN_MID - 1), "H1")
        self.assertEqual(fc.half_of(fc.WIN_MID), "H2")
        self.assertEqual(fc.WIN_START, _ms(2024, 10, 20))
        self.assertEqual(fc.WIN_END, _ms(2025, 10, 19))


def _rows(n_against, against_net, base_net, flip_h2=False, spread=0.0):
    """n_against `against` rows (alternating against_net ± spread → a finite PF) and 3× as many
    `neutral` rows at base_net, spread over the window."""
    rows, t = [], fc.WIN_START
    step = (fc.WIN_END - fc.WIN_START) // (4 * n_against)
    for i in range(4 * n_against):
        t += step
        against = i % 4 == 0
        net = against_net if against else base_net
        if against and flip_h2 and t >= fc.WIN_MID:
            net = base_net - 0.5
        if against and not flip_h2:
            net = against_net + (spread if i % 8 == 0 else -spread)
        rows.append({"t": t, "sym": "X", "rule": "r 4h", "dir": "long", "half": fc.half_of(t), "net": net,
                     "profitable": net > 0, "hold": 600, "b": "against" if against else "neutral",
                     "b_tilt": "no_data"})
    return rows


class Grade(unittest.TestCase):
    def test_pass(self):
        table, checks, verdict = fc.grade(_rows(120, 0.30, -0.10))
        self.assertEqual(verdict, "PASS", (checks, table["cells"]["against"]))
        self.assertTrue(all(checks.values()))

    def test_replicated_below_bar(self):
        # a small positive lift with a weak PF: core checks hold, PF fails
        # +0.3 / -0.25 alternating: mean +0.025, PF 1.2
        table, checks, verdict = fc.grade(_rows(120, 0.025, -0.10, spread=0.275))
        self.assertTrue(checks["gap_ge_0.05"] and checks["against_net_gt_0"])
        self.assertFalse(checks["against_pf_ge_1.3"])
        self.assertEqual(verdict, "REPLICATED, BELOW BAR")

    def test_no_when_thin(self):
        _, checks, verdict = fc.grade(_rows(40, 0.30, -0.10))
        self.assertFalse(checks["against_n_ge_100"])
        self.assertEqual(verdict, "NO")

    def test_no_on_half_sign_flip(self):
        _, checks, verdict = fc.grade(_rows(120, 0.30, -0.10, flip_h2=True))
        self.assertFalse(checks["gap_ge_0_in_both_halves"])
        self.assertEqual(verdict, "NO")

    def test_no_data_rows_excluded(self):
        rows = _rows(120, 0.30, -0.10)
        for r in rows[:50]:
            r["b"] = "no_data"
            r["net"] = -5.0
        table, _, _ = fc.grade(rows)
        self.assertEqual(table["desc"]["no_data"], 50)
        self.assertEqual(table["cells"]["all"]["n"], len(rows) - 50)


class WindowTrades(unittest.TestCase):
    def test_filters_rules_window_and_fills(self):
        inside, before = fc.WIN_START + 5 * 86_400_000, fc.WIN_START - 86_400_000
        fake = [{"signal": "trend_pullback_short", "tf": "4h", "signal_ms": inside, "symbol": "BTCUSDT", "direction": "short"},
                {"signal": "trend_pullback_short", "tf": "4h", "signal_ms": before, "symbol": "BTCUSDT", "direction": "short"},
                {"signal": "rsi_rejection_short", "tf": "4h", "signal_ms": inside, "symbol": "BTCUSDT", "direction": "short"},
                {"signal": "liquidity_sweep_long", "tf": "1h", "signal_ms": inside + 1, "symbol": "BTCUSDT", "direction": "long"}]
        results = iter([{"filled": True, "net_blended_rr": 0.1, "profitable": True, "hold_minutes": 60},
                        {"filled": False}])
        data = {"BTCUSDT": {"240": [[str(i * 14_400_000), "1", "1", "1", "1", "1", "1"] for i in range(10)]}}
        with mock.patch.object(ub, "build_trades", return_value=fake), \
             mock.patch.object(ub, "sim_trade", side_effect=lambda t: next(results)), \
             mock.patch.object(ub, "TrendIndex"), mock.patch.object(fc.sr, "compute_indicators"):
            out = fc.build_window_trades(data)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["signal_ms"], inside)
        self.assertNotIn("_res", out[0])
        self.assertIn("result", out[0])


if __name__ == "__main__":
    unittest.main()
