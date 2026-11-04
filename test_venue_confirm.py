"""Offline tests for venue_confirm.py (no network, no store)."""
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import venue_confirm as vc
import venue_data as vd

H = vd.HOUR_MS


def MS(y, m, d, h=0):
    return int(datetime(y, m, d, h, tzinfo=timezone.utc).timestamp() * 1000)


def _rows(n_per_half=200, aligned_net=0.5, against_net=-0.4, other_net=-0.1, flip_h2=False, flip_shorts=False):
    """Alternating aligned / against / neutral rows, both directions, 6h apart in each half."""
    rows = []
    for base, half in ((MS(2024, 11, 1), "H1"), (MS(2025, 5, 1), "H2")):
        for i in range(n_per_half):
            b = ("aligned", "against", "neutral")[i % 3]
            d = "long" if i % 2 else "short"
            net = {"aligned": aligned_net, "against": against_net, "neutral": other_net}[b]
            if b == "aligned" and ((flip_h2 and half == "H2") or (flip_shorts and d == "short")):
                net = against_net
            rows.append({"t": base + i * 6 * H, "sym": "X", "rule": "r 4h", "dir": d, "half": half,
                         "net": net, "profitable": net > 0, "hold": 60, "x": 2.0, "b": b})
    return rows


class Grade(unittest.TestCase):
    def test_pass(self):
        table, checks, v = vc.grade(_rows())
        self.assertEqual(v, "PASS", checks)
        self.assertGreater(table["gap"], 0.05)

    def test_replicated_below_bar_on_pf(self):
        # aligned wins +0.3 / loses −0.25 alternating within the aligned bucket → net > 0, PF < 1.3
        rows = _rows()
        k = 0
        for r in rows:
            if r["b"] == "aligned":
                r["net"] = 0.3 if k % 2 == 0 else -0.25
                r["profitable"] = r["net"] > 0
                k += 1
        table, checks, v = vc.grade(rows)
        self.assertFalse(checks["aligned_pf_ge_1.3"])
        self.assertTrue(checks["aligned_net_gt_0"] and checks["gap_ge_0.05"])
        self.assertEqual(v, "REPLICATED, BELOW BAR", checks)

    def test_half_sign_flip_is_no(self):
        _, checks, v = vc.grade(_rows(flip_h2=True))
        self.assertFalse(checks["gap_ge_0_in_both_halves"])
        self.assertEqual(v, "NO")

    def test_direction_composition_is_no(self):
        _, checks, v = vc.grade(_rows(flip_shorts=True))
        self.assertFalse(checks["gap_ge_0_in_both_directions"])
        self.assertEqual(v, "NO")

    def test_thin_is_no_and_no_data_excluded(self):
        rows = _rows(n_per_half=60)
        rows.append({**rows[0], "b": "no_data", "net": -5.0, "t": rows[0]["t"] + 1})
        table, checks, v = vc.grade(rows)
        self.assertFalse(checks["aligned_n_ge_100"])
        self.assertEqual(v, "NO")
        self.assertEqual(table["no_data"], 1)
        self.assertEqual(table["year"]["all"]["n"], 120)


class Halves(unittest.TestCase):
    def test_boundaries(self):
        self.assertEqual(vc.half_of(vc.WIN_MID - 1), "H1")
        self.assertEqual(vc.half_of(vc.WIN_MID), "H2")


class TaggedStore(unittest.TestCase):
    def test_tagged_window_is_separate_from_the_default(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(vd, "STORE_DIR", Path(d)):
            t = MS(2024, 11, 1)
            vd.save_series("X", "bybit_prem", [[t, 0.001]], tag="OLD")
            vd.save_series("X", "binance_prem", [[t, 0.0]], tag="OLD")
            self.assertEqual(vd.load_series("X", "bybit_prem"), [])
            self.assertEqual(vd.VenueIndex().symbols(), [])
            idx = vd.VenueIndex(tag="OLD")
            self.assertEqual(idx.symbols(), ["X"])
            self.assertAlmostEqual(idx.basis_disp_at("X", t), 0.001)


if __name__ == "__main__":
    unittest.main()
