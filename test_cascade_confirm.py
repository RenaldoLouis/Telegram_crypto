"""Offline tests for cascade_confirm.py (no network, no cache)."""
import unittest

import cascade_confirm as cc

WEEK = cc.WEEK_MS


def _rows(n, net_h1, net_h2, start=cc.WIN_START, direction="short"):
    """n rows per half, one per week, alternating +/- around the given mean (wins 2:1 when mean > 0)."""
    rows = []
    for half, base, net in (("H1", start, net_h1), ("H2", cc.HALF_SPLIT, net_h2)):
        for i in range(n):
            x = net + (0.5 if i % 2 else -0.5)
            rows.append({"t": base + i * WEEK // 3, "sym": "X", "dir": direction, "half": half,
                         "net": x, "profitable": x > 0})
    return rows


class TestHalves(unittest.TestCase):
    def test_boundaries(self):
        self.assertEqual(cc.half_of(cc.WIN_START), "H1")
        self.assertEqual(cc.half_of(cc.HALF_SPLIT - 1), "H1")
        self.assertEqual(cc.half_of(cc.HALF_SPLIT), "H2")
        self.assertIsNone(cc.half_of(cc.WIN_START - 1))
        self.assertIsNone(cc.half_of(cc.WIN_END))


class TestGrade(unittest.TestCase):
    def test_pass(self):
        v, checks = cc.grade(_rows(80, 0.4, 0.4), _rows(80, -0.1, -0.1))
        self.assertEqual(v, "PASS", checks)

    def test_weak_when_pf_low(self):
        # mean +0.06 with ±0.5 swings → PF ≈ 1.27 < 1.3, still beats random by > 0.05R in both halves
        v, checks = cc.grade(_rows(80, 0.06, 0.06), _rows(80, -0.1, -0.1))
        self.assertFalse(checks["pf"])
        self.assertEqual(v, "WEAK", checks)

    def test_no_when_one_half_negative(self):
        v, _ = cc.grade(_rows(80, 0.6, -0.05), _rows(80, -0.1, -0.1))
        self.assertEqual(v, "NO")

    def test_no_when_not_beating_random(self):
        v, checks = cc.grade(_rows(80, 0.4, 0.4), _rows(80, 0.38, 0.38))
        self.assertFalse(checks["beats_random"])
        self.assertEqual(v, "NO")

    def test_no_when_thin(self):
        v, checks = cc.grade(_rows(20, 0.4, 0.4), _rows(80, -0.1, -0.1))
        self.assertFalse(checks["n"])
        self.assertEqual(v, "NO")


class TestStop(unittest.TestCase):
    def _fwd(self, n=20, price=100.0):
        return [{"ts": i * 900_000, "open": price, "high": price + 0.2, "low": price - 0.2, "close": price}
                for i in range(n)]

    def test_scale_doubles_risk(self):
        captured = {}
        orig = cc.ub.sim_trade_limit

        def spy(t, off, wait, **kw):
            captured.update(kw, stop=t["stop"], entry=t["entry"])
            return None
        cc.ub.sim_trade_limit = spy
        try:
            cc.simulate(self._fwd(), "long", stop0=98.0, atr=1.0)
        finally:
            cc.ub.sim_trade_limit = orig
        self.assertEqual(captured["stop_scale"], 2.0)
        self.assertEqual((captured["t1_r"], captured["t2_r"]), (0.75, 2.0))
        stop, t1, t2 = cc.ub.trade_levels({"entry": 100.0, "ref_price": 100.0, "stop": captured["stop"],
                                           "direction": "long", "target_r": 2.0}, 0.75, 2.0, 2.0)
        self.assertAlmostEqual(stop, 96.0)           # 2 × the 2.0 distance
        self.assertAlmostEqual(t2, 108.0)            # 2R of the new 4.0 risk

    def test_floor_applied_before_scaling(self):
        captured = {}
        orig = cc.ub.sim_trade_limit
        cc.ub.sim_trade_limit = lambda t, off, wait, **kw: captured.update(stop=t["stop"])
        try:
            cc.simulate(self._fwd(), "short", stop0=100.1, atr=1.0)   # 0.1 < floor 0.5 × ATR
        finally:
            cc.ub.sim_trade_limit = orig
        self.assertAlmostEqual(captured["stop"], 100.5)


if __name__ == "__main__":
    unittest.main()
