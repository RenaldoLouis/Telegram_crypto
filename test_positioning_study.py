"""Offline tests for positioning_data.py + positioning_study.py (no network, no store)."""
import math
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import positioning_data as pdx
import positioning_study as ps

B = pdx.BAR_MS


def MS(y, m, d, h=0):
    return int(datetime(y, m, d, h, tzinfo=timezone.utc).timestamp() * 1000)


CSV = ("create_time,symbol,sum_open_interest,sum_open_interest_value,count_toptrader_long_short_ratio,"
       "sum_toptrader_long_short_ratio,count_long_short_ratio,sum_taker_long_short_vol_ratio\n"
       "2025-10-20 00:00:00,BTCUSDT,80795.18,8751464006.01,2.20787007,1.01256300,2.04458547,0.38669900\n"
       "2025-10-20 00:05:00,BTCUSDT,80817.17,8751758923.23,2.20071209,1.01439100,2.03753530,0.76979600\n"
       "2025-10-20 00:10:00,BTCUSDT,80904.19,8740087844.14,2.20791587,1.01840900,2.02762195,0.37658500\n"
       "2025-10-20 00:15:00,BTCUSDT,80950.00,8740000000.00,2.21,1.02,2.03,0.40\n")


class ReduceDay(unittest.TestCase):
    def test_boundaries_only_and_columns(self):
        out = pdx.reduce_day(CSV)
        self.assertEqual(sorted(out), [MS(2025, 10, 20), MS(2025, 10, 20) + B])
        r = out[MS(2025, 10, 20)]
        self.assertEqual(r[1 + pdx.COLS.index("top_pos")], 1.012563)
        self.assertEqual(r[1 + pdx.COLS.index("glob_acc")], 2.04458547)
        self.assertEqual(len(r), 7)


class Index(unittest.TestCase):
    def test_no_look_ahead_and_series_gaps(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(pdx, "STORE_DIR", Path(d)):
            t0 = MS(2025, 11, 1)
            rows = {t0 + i * B: [t0 + i * B, 1, 1, 1, 1.0 + i, 2.0, 1] for i in range(6) if i != 3}
            pdx.save_rows("X", rows)
            idx = pdx.PositioningIndex(["X"])
            self.assertIsNone(idx.at("X", t0 - 1))
            self.assertEqual(idx.at("X", t0 + 2 * B + 60_000)[0], t0 + 2 * B)   # last boundary ≤ t
            self.assertIsNone(idx.at("X", t0 + 3 * B + 60_000))                  # boundary 3 missing → stale
            self.assertEqual(idx.series("X", t0 + 5 * B, 4, "top_pos"), [3.0, None, 5.0, 6.0])
            self.assertEqual(idx.series("X", t0 + 5 * B, 4, "glob_acc"), [2.0, None, 2.0, 2.0])

    def test_log_ratio(self):
        self.assertAlmostEqual(pdx.log_ratio(1.0), 0.0)
        self.assertIsNone(pdx.log_ratio(0))
        self.assertIsNone(pdx.log_ratio(None))


class FakeIndex:
    """series() = an alternating 1.0/1.2 pattern ending at the level stored for (sym, boundary ≤ t);
    both columns answer alike."""

    def __init__(self, levels):
        self.levels = levels          # {(sym, T): last value}

    def _key(self, sym, t):
        c = [T for (s, T) in self.levels if s == sym and T <= t and t - T <= pdx.MAX_ROW_AGE_MS]
        return (sym, max(c)) if c else None

    def at(self, sym, t):
        k = self._key(sym, t)
        return [k[1]] if k else None

    def series(self, sym, t, bars, col):
        k = self._key(sym, t)
        if k is None:
            return []
        return [1.0 if i % 2 else 1.2 for i in range(bars - 1)] + [self.levels[k]]


class Features(unittest.TestCase):
    def test_z_sign_and_magnitude(self):
        T = MS(2026, 1, 1)
        idx = FakeIndex({("X", T): 3.0, ("Y", T): 0.3})
        self.assertGreater(ps.feature(idx, "X", T, "top_z"), 3)
        self.assertLess(ps.feature(idx, "Y", T, "glob_z"), -3)
        self.assertIsNone(ps.feature(idx, "X", T - 1, "top_z"))     # no boundary ≤ t within the age limit

    def test_z_needs_enough_history(self):
        class Thin(FakeIndex):
            def series(self, sym, t, bars, col):
                return [1.0, 1.2, 1.0, 3.0]
        self.assertIsNone(ps.feature(Thin({("X", 0): 3.0}), "X", 0, "top_z"))

    def test_tilt_sign_and_missing_reference(self):
        T = MS(2026, 1, 1)
        idx = FakeIndex({("X", T): 3.0, ("Y", T): 0.3})
        self.assertGreater(ps.feature(idx, "X", T, "top_tilt"), 1)
        self.assertLess(ps.feature(idx, "Y", T, "top_tilt"), -1)

        class Hole(FakeIndex):
            def series(self, sym, t, bars, col):
                s = super().series(sym, t, bars, col)
                s[-1 - ps.TILT_BARS] = None
                return s
        self.assertIsNone(ps.feature(Hole({("X", T): 3.0}), "X", T, "top_tilt"))

    def test_orientation(self):
        # crowd long (+) → aligned for a SHORT (faded); top traders long (+) → aligned for a LONG (followed)
        self.assertEqual(ps.bucket(2.0, "glob_z", "short", 1.0), "aligned")
        self.assertEqual(ps.bucket(2.0, "glob_z", "long", 1.0), "against")
        self.assertEqual(ps.bucket(2.0, "top_z", "long", 1.0), "aligned")
        self.assertEqual(ps.bucket(0.5, "top_z", "long", 1.0), "neutral")
        self.assertEqual(ps.bucket(None, "top_tilt", "long", 1.0), "no_data")


class TestA(unittest.TestCase):
    def _trades(self, aligned_wins_unseen):
        """120 long trades per half at 12h spacing: top traders long (level 3 → aligned) or short
        (level 0.3 → against); aligned wins on the fit half, and on the unseen half iff asked."""
        levels, trades = {}, []
        for base, half in ((MS(2026, 4, 1), "fit"), (MS(2026, 8, 1), "unseen")):
            for i in range(120):
                T = base + i * 12 * 3600 * 1000
                aligned = i % 2 == 0
                levels[("X", T)] = 3.0 if aligned else 0.3
                win = aligned if (half == "fit" or aligned_wins_unseen) else (not aligned)
                net = 0.8 if win else -0.6
                trades.append({"signal_ms": T, "symbol": "X", "signal": "r", "tf": "4h", "direction": "long",
                               "result": {"net_blended_rr": net, "profitable": net > 0, "hold_minutes": 60}})
        return FakeIndex(levels), trades

    def test_pass_selects_a_followed_top_variant(self):
        idx, trades = self._trades(True)
        _, table, v = ps.run_test_a(idx, trades)
        self.assertTrue(v["selected"].startswith("top_"), v)
        self.assertTrue(v["pass"], v)

    def test_sign_flip_out_of_sample_is_no(self):
        idx, trades = self._trades(False)
        _, _, v = ps.run_test_a(idx, trades)
        self.assertTrue(v["selected"].startswith("top_"))
        self.assertFalse(v["pass"])
        self.assertFalse(v["checks"]["aligned_net_gt_0"])


if __name__ == "__main__":
    unittest.main()
