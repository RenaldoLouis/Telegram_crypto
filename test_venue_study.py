"""Offline tests for venue_data.py + venue_study.py (no network, no store)."""
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import venue_data as vd
import venue_study as vs

B, H = vd.BAR_MS, vd.HOUR_MS


def MS(y, m, d, h=0, mi=0):
    return int(datetime(y, m, d, h, mi, tzinfo=timezone.utc).timestamp() * 1000)


class Reducers(unittest.TestCase):
    def test_binance_funding_floors_latency_and_keeps_interval(self):
        csv = ("calc_time,funding_interval_hours,last_funding_rate\n"
               f"{MS(2026, 9, 1) + 5},4,0.00003698\n{MS(2026, 9, 1, 4) + 7},4,0.00004981\n")
        rows = vd.reduce_binance_funding(csv)
        self.assertEqual(rows, [[MS(2026, 9, 1), 0.00003698, 4.0], [MS(2026, 9, 1, 4), 0.00004981, 4.0]])

    def test_binance_premium_is_stored_by_close(self):
        csv = ("open_time,open,high,low,close,volume,close_time,quote_volume,count,tb,tbq,ignore\n"
               f"{MS(2025, 10, 1)},-0.0005,-0.0001,-0.0007,-0.000538,0,{MS(2025, 10, 1) + B - 1},0,180,0,0,0\n")
        self.assertEqual(vd.reduce_binance_premium(csv), [[MS(2025, 10, 1) + B, -0.000538]])

    def test_okx_basis_joins_matching_bars_only(self):
        t = MS(2026, 1, 1)
        rows = vd.okx_basis_rows({t: 101.0, t + B: 100.0, t + 2 * B: 99.0}, {t: 100.0, t + 2 * B: 100.0})
        self.assertEqual([r[0] for r in rows], [t + B, t + 3 * B])
        self.assertAlmostEqual(rows[0][1], 0.01)
        self.assertAlmostEqual(rows[1][1], -0.01)

    def test_bybit_funding_interval_from_spacing(self):
        t = MS(2026, 2, 1)
        rows = vd.funding_rows([(t + 8 * H, 0.0002), (t, 0.0001), (t + 12 * H, 0.0003), (t + 16 * H + 5, 0.0004)])
        self.assertEqual([r[0] for r in rows], [t, t + 8 * H, t + 12 * H, t + 16 * H])
        self.assertEqual([r[2] for r in rows], [8.0, 8.0, 4.0, 4.0])      # first takes the next spacing


class Index(unittest.TestCase):
    def _store(self, d):
        t = MS(2026, 3, 1)
        vd.save_series("X", "bybit_fund", [[t, 0.0001, 8.0], [t + 8 * H, 0.0003, 8.0]])
        vd.save_series("X", "binance_fund", [[t, 0.0001, 4.0], [t + 4 * H, 0.0002, 4.0]])
        vd.save_series("X", "bybit_prem", [[t + i * B, 0.001 * i] for i in range(6)])
        vd.save_series("X", "binance_prem", [[t + i * B, 0.0005] for i in range(6) if i != 3])
        vd.save_series("X", "okx_basis", [[t + i * B, 0.0015] for i in range(2)])
        return t

    def test_funding_dispersion_is_8h_normalised_and_no_look_ahead(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(vd, "STORE_DIR", Path(d)):
            t = self._store(d)
            idx = vd.VenueIndex(["X"])
            self.assertIsNone(idx.fund_disp("X", t - 1))                      # nothing settled yet
            self.assertAlmostEqual(idx.fund_disp("X", t), (0.0001 - 0.0002) * 1e4)   # 4h rate counts double
            self.assertAlmostEqual(idx.fund_disp("X", t + 4 * H), (0.0001 - 0.0004) * 1e4)
            self.assertAlmostEqual(idx.fund_disp("X", t + 8 * H), (0.0003 - 0.0004) * 1e4)   # Bybit's later print
            self.assertIsNone(idx.fund_disp("X", t + 8 * H + vd.MAX_SETTLEMENT_AGE_MS + 1))   # stale

    def test_basis_dispersion_needs_bybit_plus_one_venue(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(vd, "STORE_DIR", Path(d)):
            t = self._store(d)
            idx = vd.VenueIndex(["X"])
            self.assertAlmostEqual(idx.basis_disp_at("X", t), 0.0 - (0.0005 + 0.0015) / 2)   # both venues
            self.assertAlmostEqual(idx.basis_disp_at("X", t + 2 * B), 0.002 - 0.0005)       # Binance only
            self.assertIsNone(idx.basis_disp_at("X", t + 3 * B))                             # no other venue
            self.assertIsNone(idx.basis_disp_at("X", t + 9 * B))                             # no Bybit bar
            s = idx.basis_disp_series("X", t + 4 * B + 60_000, 3)                             # last boundary ≤ t
            self.assertEqual(len(s), 3)
            self.assertAlmostEqual(s[-1], 0.004 - 0.0005)
            self.assertIsNone(s[-2])

    def test_okx_names(self):
        self.assertEqual(vd.okx_swap("1000PEPEUSDT"), "PEPE-USDT-SWAP")
        self.assertEqual(vd.okx_index("PUMPFUNUSDT"), "PUMP-USDT")
        self.assertEqual(vd.okx_swap("BTCUSDT"), "BTC-USDT-SWAP")


class FakeIndex:
    """basis_disp_series() = an alternating ±1 bps pattern ending at the level stored for (sym, T);
    fund_disp() = the same level in bps."""

    def __init__(self, levels):
        self.levels = levels

    def _key(self, sym, t):
        c = [T for (s, T) in self.levels if s == sym and T <= t and t - T <= B]
        return (sym, max(c)) if c else None

    def fund_disp(self, sym, t):
        k = self._key(sym, t)
        return self.levels[k] if k else None

    def basis_disp_series(self, sym, t, bars):
        k = self._key(sym, t)
        if k is None:
            return []
        return [1e-4 if i % 2 else -1e-4 for i in range(bars - 1)] + [self.levels[k] * 1e-4]


class Features(unittest.TestCase):
    def test_z_and_tilt_sign_and_magnitude(self):
        T = MS(2026, 1, 1)
        idx = FakeIndex({("X", T): 5.0, ("Y", T): -5.0})
        self.assertGreater(vs.feature(idx, "X", T, "basis_disp_z"), 3)
        self.assertLess(vs.feature(idx, "Y", T, "basis_disp_z"), -3)
        self.assertGreater(vs.feature(idx, "X", T, "basis_disp_tilt"), 1)
        self.assertLess(vs.feature(idx, "Y", T, "basis_disp_tilt"), -1)
        self.assertEqual(vs.feature(idx, "X", T, "fund_disp"), 5.0)
        self.assertIsNone(vs.feature(idx, "X", T - 1, "basis_disp_z"))

    def test_thin_history_is_no_data(self):
        class Thin(FakeIndex):
            def basis_disp_series(self, sym, t, bars):
                return [1e-4, -1e-4, 1e-4, 5e-4]
        self.assertIsNone(vs.feature(Thin({("X", 0): 5.0}), "X", 0, "basis_disp_z"))
        self.assertIsNone(vs.feature(Thin({("X", 0): 5.0}), "X", 0, "basis_disp_tilt"))

    def test_orientation_is_fade(self):
        # Bybit richer (+) → aligned for a SHORT, against for a LONG
        self.assertEqual(vs.bucket(2.0, "short", 1.0), "aligned")
        self.assertEqual(vs.bucket(2.0, "long", 1.0), "against")
        self.assertEqual(vs.bucket(-2.0, "long", 1.0), "aligned")
        self.assertEqual(vs.bucket(0.5, "long", 1.0), "neutral")
        self.assertEqual(vs.bucket(None, "long", 1.0), "no_data")


class TestA(unittest.TestCase):
    def _trades(self, aligned_wins_unseen):
        """120 short trades per half at 12h spacing: Bybit richer (level +5 → aligned for a short) or
        cheaper (−5 → against); aligned wins on the fit half, and on the unseen half iff asked."""
        levels, trades = {}, []
        for base, half in ((MS(2026, 4, 1), "fit"), (MS(2026, 8, 1), "unseen")):
            for i in range(120):
                T = base + i * 12 * H
                aligned = i % 2 == 0
                levels[("X", T)] = 5.0 if aligned else -5.0
                win = aligned if (half == "fit" or aligned_wins_unseen) else (not aligned)
                net = 0.8 if win else -0.6
                trades.append({"signal_ms": T, "symbol": "X", "signal": "r", "tf": "4h", "direction": "short",
                               "result": {"net_blended_rr": net, "profitable": net > 0, "hold_minutes": 60}})
        return FakeIndex(levels), trades

    def test_pass_when_the_fade_holds_out_of_sample(self):
        idx, trades = self._trades(True)
        _, table, v = vs.run_test_a(idx, trades)
        self.assertIsNotNone(v["selected"], v)
        self.assertTrue(v["pass"], v)
        self.assertEqual(table[v["selected"]]["unseen"]["against"]["n"], 60)

    def test_sign_flip_out_of_sample_is_no(self):
        idx, trades = self._trades(False)
        _, _, v = vs.run_test_a(idx, trades)
        self.assertIsNotNone(v["selected"])
        self.assertFalse(v["pass"])
        self.assertFalse(v["checks"]["aligned_net_gt_0"])


if __name__ == "__main__":
    unittest.main()
