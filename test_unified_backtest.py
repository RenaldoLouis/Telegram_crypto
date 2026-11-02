"""Offline tests for unified_backtest's live-parity trade construction (2026-11-02).

The engine must build the trade weekly_eval scores for a live setup: levels from the price at
the scan (stop, T2 at target_r, structural T1 as mechanical_setups places it), candles from the
first 15m open at or after close + scan lag, the evaluator's gap-skip rule, fixed levels in the
simulation. engine_parity.py measures the same thing on the live record.
"""

import math
import random
import unittest
from unittest import mock

import mechanical_setups as ms
import signal_rules as sr
import unified_backtest as ub
from fetchers.bybit_data import BybitFetcher

H4, M15 = 14_400_000, 900_000
SIG = {"signal": "trend_pullback_short", "tf": "4h", "direction": "short", "target_r": 2.0,
       "stop_atr": 1.5, "tier": "watch", "indicators": ""}


def h4_rows(n=100, seed=1, start=0):
    """Wavy 4h candles so swing pivots, EMAs and 20-bar extremes all exist."""
    rng = random.Random(seed)
    out, p = [], 100.0
    for k in range(n):
        o = p
        p = 100 + 6 * math.sin(k / 5) + rng.uniform(-1, 1)
        hi, lo = max(o, p) + rng.uniform(0.1, 1.0), min(o, p) - rng.uniform(0.1, 1.0)
        out.append([start + k * H4, o, hi, lo, p, 1000.0, 1e6])
    return out


def m15_rows(start, n, price=100.0, step=0.0):
    return [[start + k * M15, price + step * k, price + step * k + 0.2, price + step * k - 0.2,
             price + step * k, 1.0, 1.0] for k in range(n)]


class LevelsMatchLiveConstructor(unittest.TestCase):
    """Drift guard: live_targets == mechanical_setups._build_one on the same closed bars."""

    def test_same_levels_as_live_setup(self):
        structural = 0
        for seed in range(6):
            rows = h4_rows(seed=seed)
            df = sr.compute_indicators(rows)
            i = len(df) - 1
            atr = float(df["atr"].iat[i])
            # price at the scan: just off the last close (usually the 0.75R fallback), and placed
            # so EMA20 sits at 0.85R below it (structural T1 path)
            for ref in (float(df["close"].iat[i]) + 0.3, float(df["ema20"].iat[i]) + 0.85 * 1.5 * atr):
                stop = sr.levels_for(SIG, ref, atr)
                risk = abs(ref - stop)
                t1, t2, _ = ub.live_targets(df, i, SIG, ref, risk)
                structural += abs((ref - t1) / risk - 0.75) > 1e-6

                tf = BybitFetcher._compute_indicators(None, rows)   # the live indicator set
                tf["current_price"] = ref
                setup = ms._build_one({"symbol": "XUSDT", "timeframes": {"4h": tf}}, "short", [SIG],
                                      "neutral", {})
                self.assertAlmostEqual(setup["stop_loss"], stop, places=4)
                self.assertAlmostEqual(setup["target_2"], t2, places=4)
                self.assertAlmostEqual(setup["target_1"], t1, places=4, msg=f"seed {seed} ref {ref}")
        self.assertGreaterEqual(structural, 6)                         # the structural path was compared


class BuildTrades(unittest.TestCase):
    def setUp(self):
        ub._PREP_CACHE.clear()
        self.h4 = h4_rows(n=100)
        self.i = 80
        self.close_t = self.h4[self.i][0] + H4

    def _build(self, m15, sym="TUSDT"):
        data = {"240": self.h4, "60": [], "D": [], "15": m15}
        fire = lambda df, i, tf, enabled=None, params=None: [dict(SIG)] if i == self.i else []
        with mock.patch.object(ub.sr, "detect_at", side_effect=fire):
            return ub.build_trades(sym, data, None, {SIG["signal"]}, {"4h"})

    def test_window_starts_after_scan_lag_and_levels_from_close_price(self):
        m15 = m15_rows(self.close_t - 4 * M15, 400, price=100.0, step=0.0001)
        (t,) = self._build(m15)
        self.assertEqual(t["ref_price"], m15[4][1])                   # the 15m bar opening at the close
        self.assertEqual(t["entry"], m15[5][1])                       # first open at/after close + 2 min
        self.assertEqual(t["_fwd"][0]["open"], m15[5][1])
        self.assertEqual(len(t["_fwd"]), ub.WINDOW_CANDLES["4h"])
        risk = t["stop"] - t["ref_price"]
        self.assertAlmostEqual(t["t2"], t["ref_price"] - 2.0 * risk, places=6)
        self.assertGreaterEqual((t["ref_price"] - t["t1"]) / risk, 0.75 - 1e-9)
        self.assertLessEqual((t["ref_price"] - t["t1"]) / risk, 1.0 + 1e-9)

    def test_gap_skip_drops_the_trade(self):
        m15 = m15_rows(self.close_t - 4 * M15, 400, price=100.0)
        m15[5][1] = 1_000.0                                           # first scored open above the stop
        self.assertEqual(self._build(m15), [])

    def test_gap_skip_still_blocks_a_repeat(self):
        h4 = self.h4
        second = self.i + 2                                           # 8h later, inside the 2-day dedup
        close2 = h4[second][0] + H4
        m15 = m15_rows(self.close_t - 4 * M15, 400, price=100.0)
        m15[5][1] = 1_000.0
        data = {"240": h4, "60": [], "D": [], "15": m15}
        fire = lambda df, i, tf, enabled=None, params=None: [dict(SIG)] if i in (self.i, second) else []
        with mock.patch.object(ub.sr, "detect_at", side_effect=fire):
            out = ub.build_trades("GUSDT", data, None, {SIG["signal"]}, {"4h"})
        self.assertNotIn(close2, [t["signal_ms"] for t in out])


class Simulation(unittest.TestCase):
    def _trade(self, **kw):
        t = {"direction": "short", "entry": 100.2, "ref_price": 100.0, "stop": 102.0, "t1": 98.4,
             "t2": 96.0, "t1_levels": [98.4], "target_r": 2.0, "atr": 1.0, "_fwd": [{"open": 1}]}
        t.update(kw)
        return t

    def test_default_uses_the_setups_fixed_levels(self):
        with mock.patch.object(ub.ts, "simulate_limit", return_value={"filled": True}) as sim:
            ub.sim_trade_limit(self._trade(), 0.0, 2)
        _, direction, stop, t1, t2 = sim.call_args.args
        self.assertEqual((direction, stop, t1, t2), ("short", 102.0, 98.4, 96.0))

    def test_overrides_rebuild_from_the_scan_price(self):
        stop, t1, t2 = ub.trade_levels(self._trade(), t1_r=1.0, stop_scale=1.5, t2_r=1.5)
        self.assertAlmostEqual(stop, 103.0)                           # 1.5 × 2.0 from 100
        self.assertAlmostEqual(t1, 97.0)
        self.assertAlmostEqual(t2, 95.5)

    def test_legacy_trade_dict_without_levels(self):
        t = {"direction": "short", "entry": 100.0, "stop": 102.0, "target_r": 2.0}
        stop, t1, t2 = ub.trade_levels(t)
        self.assertEqual((stop, t1, t2), (102.0, 98.5, 96.0))


if __name__ == "__main__":
    unittest.main()
