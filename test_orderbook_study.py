"""Offline tests for orderbook_data.py + orderbook_study.py (no network, no caches)."""
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import orderbook_data as od
import orderbook_study as os_

MS = lambda y, m, d, hh=0, mm=0: int(datetime(y, m, d, hh, mm, tzinfo=timezone.utc).timestamp() * 1000)


def csv_day(minutes, bid_fn, ask_fn):
    """Synthetic bookDepth CSV: one row per minute × band, notional = fn(minute, band)."""
    lines = ["timestamp,percentage,depth,notional"]
    for mm in minutes:
        stamp = f"2026-10-01 {mm // 60:02d}:{mm % 60:02d}:01"
        for b in od.BANDS:
            lines.append(f"{stamp},-{b:.2f},1,{bid_fn(mm, b)}")
            lines.append(f"{stamp},{b:.2f},1,{ask_fn(mm, b)}")
    return "\n".join(lines)


class FakeIndex:
    """Duck-typed OrderBookIndex: rows keyed by (sym, boundary ms)."""

    def __init__(self, rows):
        self.rows = rows

    def at(self, sym, t):
        cands = [m for (s, m) in self.rows if s == sym and m <= t and t - m <= od.MAX_SNAPSHOT_AGE_MS]
        return self.rows[(sym, max(cands))] if cands else None

    def window(self, sym, t, bars):
        last = self.at(sym, t)
        if last is None:
            return []
        return [self.rows[(sym, m)] for m in range(last[0] - (bars - 1) * od.BAR_MS, last[0] + 1, od.BAR_MS)
                if (sym, m) in self.rows]


def row(m, imb, band_k=None):
    """A store row whose imbalance at every band is `imb` (bid = 1+imb, ask = 1−imb)."""
    bid, ask = [1 + imb] * 6, [1 - imb] * 6
    return [m, bid, ask, bid, ask]


class ReduceDayTest(unittest.TestCase):
    def test_boundaries_and_means(self):
        # minutes 0..30: bid notional = 100 + minute, ask = 100 (so imbalance rises through the day)
        text = csv_day(range(0, 31), lambda mm, b: 100 + mm, lambda mm, b: 100)
        got = od.reduce_day(text)
        b0, b15, b30 = MS(2026, 10, 1), MS(2026, 10, 1, 0, 15), MS(2026, 10, 1, 0, 30)
        self.assertEqual(sorted(got), [b0, b15, b30])         # only 15m boundaries kept
        self.assertEqual(got[b15][1][0], 115.0)                # the snapshot AT minute 15
        self.assertEqual(got[b15][2][0], 100.0)
        # mean over (B-15, B] = minutes 1..15 → bid mean 108
        self.assertAlmostEqual(got[b15][3][0], 108.0)
        # boundary 0 has only its own minute in the window
        self.assertAlmostEqual(got[b0][3][0], 100.0)

    def test_missing_boundary_minute_is_dropped(self):
        text = csv_day([m for m in range(0, 31) if m != 15], lambda mm, b: 1, lambda mm, b: 1)
        got = od.reduce_day(text)
        self.assertNotIn(MS(2026, 10, 1, 0, 15), got)


class IndexTest(unittest.TestCase):
    def test_lookup_never_reads_the_future(self):
        with tempfile.TemporaryDirectory() as d:
            orig = od.STORE_DIR
            od.STORE_DIR = Path(d)
            try:
                b = MS(2026, 10, 1, 4, 0)
                od.save_rows("XUSDT", {b: row(b, 0.2), b + od.BAR_MS: row(b + od.BAR_MS, -0.5)})
                idx = od.OrderBookIndex(["XUSDT"])
                self.assertIsNone(idx.at("XUSDT", b - 1))                      # before the first snapshot
                self.assertEqual(idx.at("XUSDT", b)[0], b)                      # at the boundary
                self.assertEqual(idx.at("XUSDT", b + 4 * od.MINUTE_MS)[0], b)   # within 5 min → same row
                self.assertIsNone(idx.at("XUSDT", b + 6 * od.MINUTE_MS))        # gap > 5 min → no data
                self.assertEqual(idx.at("XUSDT", b + od.BAR_MS + 1000)[0], b + od.BAR_MS)
                self.assertEqual([r[0] for r in idx.window("XUSDT", b + od.BAR_MS, 2)], [b, b + od.BAR_MS])
                self.assertEqual(len(idx.window("XUSDT", b + od.BAR_MS, 3)), 2)  # gap tolerated (shorter)
            finally:
                od.STORE_DIR = orig

    def test_imbalance(self):
        r = row(0, 0.25)
        self.assertAlmostEqual(od.imbalance(r, 2.0), 0.25)
        self.assertAlmostEqual(od.imbalance(r, 1.0, "mean"), 0.25)
        self.assertIsNone(od.imbalance([0, [0] * 6, [0] * 6, [0] * 6, [0] * 6], 2.0))


class FeatureTest(unittest.TestCase):
    def test_tilt_needs_eight_boundaries_and_is_last_hour_minus_prior(self):
        b = MS(2026, 10, 1, 4, 0)
        rows = {("X", b - k * od.BAR_MS): row(b - k * od.BAR_MS, 0.1 if k >= 4 else 0.3) for k in range(8)}
        idx = FakeIndex(rows)
        self.assertAlmostEqual(os_.feature(idx, "X", b, "tilt", 2.0), 0.2)
        self.assertAlmostEqual(os_.feature(idx, "X", b, "imb", 2.0), 0.3)
        del rows[("X", b - 7 * od.BAR_MS)]
        self.assertIsNone(os_.feature(FakeIndex(rows), "X", b, "tilt", 2.0))
        self.assertIsNone(os_.feature(FakeIndex(rows), "Y", b, "imb", 2.0))

    def test_bucket_sign_convention(self):
        self.assertEqual(os_.bucket(0.3, "long", 0.2), "aligned")     # bid-heavy favours a long
        self.assertEqual(os_.bucket(0.3, "short", 0.2), "against")
        self.assertEqual(os_.bucket(-0.3, "short", 0.2), "aligned")   # ask-heavy favours a short
        self.assertEqual(os_.bucket(0.1, "long", 0.2), "neutral")
        self.assertEqual(os_.bucket(None, "long", 0.2), "no_data")


class TestAVerdictTest(unittest.TestCase):
    def _trades(self, aligned_wins_unseen):
        """60 trades per half per bucket: aligned long trades (book +0.5) and against (book −0.5)."""
        fit0, uns0 = MS(2026, 4, 1), MS(2026, 8, 1)      # TRAIN and TEST periods
        rows, trades = {}, []
        k = 0
        for base, half in ((fit0, "fit"), (uns0, "unseen")):
            for i in range(120):
                T = base + i * 12 * 3600 * 1000      # 60 days: the unseen half spans TEST and H
                aligned = i % 2 == 0
                rows[("X", T)] = row(T, 0.5 if aligned else -0.5)
                win = aligned if (half == "fit" or aligned_wins_unseen) else (not aligned)
                net = 0.8 if win else -0.6
                trades.append({"signal_ms": T, "symbol": "X", "signal": "r", "tf": "4h", "direction": "long",
                               "result": {"net_blended_rr": net, "profitable": net > 0, "hold_minutes": 60}})
                k += 1
        return FakeIndex(rows), trades

    def test_pass_when_aligned_wins_on_the_unseen_half(self):
        idx, trades = self._trades(aligned_wins_unseen=True)
        _, table, v = os_.run_test_a(idx, trades)
        self.assertTrue(v["pass"], v)
        self.assertGreater(v["unseen_gap"], 0.05)
        self.assertEqual(table[v["selected"]]["unseen"]["aligned"]["n"], 60)

    def test_no_when_the_sign_flips_out_of_sample(self):
        idx, trades = self._trades(aligned_wins_unseen=False)
        _, _, v = os_.run_test_a(idx, trades)
        self.assertIsNotNone(v["selected"])               # still selected on the fit half
        self.assertFalse(v["pass"])
        self.assertFalse(v["checks"]["against_not_better"])


class SimBookTradeTest(unittest.TestCase):
    def test_fill_and_target(self):
        # open 100; first bar dips to 99.5 (fills the long limit at 100, stop at 99 untouched), then runs to 103 → T2 (2R at ATR 1)
        fwd = [{"ts": 0, "open": 100, "high": 100.5, "low": 99.5, "close": 100.2}]
        fwd += [{"ts": i, "open": 100.2, "high": 103.0, "low": 100.0, "close": 102.9} for i in range(1, 10)]
        r = os_.sim_book_trade(fwd, "long", 1.0)
        self.assertIsNotNone(r)
        self.assertTrue(r["profitable"])
        self.assertIsNone(os_.sim_book_trade(fwd[:3], "long", 1.0))      # too short
        self.assertIsNone(os_.sim_book_trade(fwd, "long", 0.0))          # no ATR

    def test_not_filled_when_price_never_trades_through(self):
        fwd = [{"ts": i, "open": 100 + i, "high": 101 + i, "low": 100 + i, "close": 101 + i} for i in range(10)]
        self.assertIsNone(os_.sim_book_trade(fwd, "long", 1.0))


class PeriodTest(unittest.TestCase):
    def test_halves(self):
        self.assertEqual(os_.half_of(MS(2026, 1, 15)), "fit")
        self.assertEqual(os_.half_of(MS(2026, 5, 1)), "fit")
        self.assertEqual(os_.half_of(MS(2026, 8, 1)), "unseen")
        self.assertEqual(os_.half_of(MS(2026, 10, 1)), "unseen")
        self.assertIsNone(os_.half_of(MS(2025, 10, 1)))


if __name__ == "__main__":
    unittest.main()
