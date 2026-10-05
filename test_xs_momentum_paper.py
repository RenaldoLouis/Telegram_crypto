"""Offline unit tests for xs_momentum_paper.py — synthetic data, no network. Run: python -m unittest test_xs_momentum_paper -v"""
import json
import math
import os
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

import numpy as np

import xs_momentum_paper as P

DAY = 86400 * 1000
ASOF = datetime(2026, 10, 5, tzinfo=timezone.utc)          # a Monday
P.MIN_UNIVERSE = 10


class FakeSource:
    """Synthetic daily panel + 8h funding. 40 symbols, 160 days ending AFTER asof so score() has a next week."""

    def __init__(self, seed=7):
        rng = np.random.default_rng(seed)
        self.syms = [f"S{i:02d}USDT" for i in range(39)] + ["BTCUSDT", "NVDAUSDT", "SOXSUSDT", "XAUTUSDT"]
        self.types = {"NVDAUSDT": "stock", "SOXSUSDT": "ETF"}            # XAUTUSDT: blank type → caught by supplement
        self.t0 = int(ASOF.timestamp() * 1000) - 150 * DAY
        self.days = 160
        self.close, self.turn, self.fund = {}, {}, {}
        for i, s in enumerate(self.syms):
            drift = (i - 20) * 0.002                                  # spread of trends → clear deciles
            if s in ("NVDAUSDT", "XAUTUSDT"):
                drift = 0.05                                          # would top every momentum decile if allowed
            if s == "SOXSUSDT":
                drift = -0.05                                         # would bottom every decile if allowed
            r = rng.normal(drift, 0.03, self.days)
            self.close[s] = 100 * np.cumprod(1 + r)
            self.turn[s] = np.full(self.days, 5e7 if i not in (3, 4) else 1e6)   # S03/S04 illiquid
            rate = -0.01 if i in (30, 31, 32) else 0.0001                 # 3 names heavily negative funding → carry basket
            self.fund[s] = rate
        self.launch = {s: self.t0 - 400 * DAY for s in self.syms}
        self.launch["S05USDT"] = int(ASOF.timestamp() * 1000) - 10 * DAY   # too young
        self.calls = 0

    def instruments(self):
        self.calls += 1
        return [{"symbol": s, "launchTime": self.launch[s], "symbolType": self.types.get(s, "")} for s in self.syms]

    def klines(self, symbol, start_ms, end_ms, limit=200):
        self.calls += 1
        rows = []
        for d in range(self.days):
            ts = self.t0 + d * DAY
            if start_ms <= ts <= end_ms:
                c = self.close[symbol][d]
                rows.append([str(ts), str(c), str(c), str(c), str(c), "1", str(self.turn[symbol][d])])
        return rows[::-1][:limit]

    def funding(self, symbol, start_ms, end_ms):
        self.calls += 1
        out, ts = [], (start_ms // (8 * 3600 * 1000) + 1) * 8 * 3600 * 1000
        while ts <= end_ms:
            out.append([ts, self.fund[symbol]])
            ts += 8 * 3600 * 1000
        return out


class TestRebalance(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.src = FakeSource()

    def tearDown(self):
        shutil.rmtree(self.dir)

    def test_weights_properties_and_schema(self):
        path = P.rebalance(self.src, ASOF, out_dir=self.dir, threads=1)
        self.assertTrue(path and os.path.exists(path))
        wf = json.load(open(path))
        self.assertEqual(wf["rules_hash"], P.rules_hash())
        self.assertEqual(wf["asof_close"], ASOF.isoformat())
        self.assertEqual(wf["asof_bar_open"], "2026-10-04")
        self.assertTrue(set(["S30USDT", "S31USDT", "S32USDT"]) <= set(wf["carry_excluded"]))
        for book in ("k56", "k91"):
            b = wf["books"][book]
            w = b["weights"]
            self.assertGreater(len(w), 0)
            self.assertAlmostEqual(sum(w.values()), 0.0, places=9)                       # dollar neutral
            self.assertLessEqual(sum(abs(x) for x in w.values()), 1.0 + 1e-9)             # gross <= 1
            self.assertEqual(b["n_long"], b["n_short"])
            for s, x in w.items():
                self.assertLessEqual(abs(x), 0.05 + 1e-12)                                # 10% of a 50% leg
                self.assertNotIn(s, wf["carry_excluded"])
                self.assertNotIn(s, ("S03USDT", "S04USDT", "S05USDT"))                    # illiquid / too young
            longs = sum(x for x in w.values() if x > 0)
            self.assertAlmostEqual(longs, 0.5 * b["leg_invested"], places=9)
            # legs of < 10 names → cap binds → leg under-invested
            if b["n_long"] < 10:
                self.assertLess(b["leg_invested"], 1.0)
        self.assertTrue(os.path.exists(os.path.join(self.dir, "latest_weights.md")))
        self.assertTrue(all(isinstance(x, float) for x in wf["books"]["k56"]["weights"].values()))

    def test_idempotent(self):
        P.rebalance(self.src, ASOF, out_dir=self.dir, threads=1)
        calls = self.src.calls
        self.assertIsNone(P.rebalance(self.src, ASOF, out_dir=self.dir, threads=1))
        self.assertEqual(self.src.calls, calls)                                           # no network on the repeat

    def test_tradfi_and_pegged_excluded(self):
        path = P.rebalance(self.src, ASOF, out_dir=self.dir, threads=1)
        wf = json.load(open(path))
        self.assertEqual(sorted(wf["tradfi_excluded"]), ["NVDAUSDT", "SOXSUSDT", "XAUTUSDT"])
        for book in ("k56", "k91"):
            for s in ("NVDAUSDT", "SOXSUSDT", "XAUTUSDT"):
                self.assertNotIn(s, wf["books"][book]["weights"])
        self.assertFalse(set(wf["carry_excluded"]) & {"NVDAUSDT", "SOXSUSDT", "XAUTUSDT"})
        self.assertIn("crypto_only", wf["rules"])
        self.assertTrue(P.is_crypto({"symbol": "ETHUSDT", "symbolType": ""}))
        self.assertTrue(P.is_crypto({"symbol": "AKEUSDT", "symbolType": "innovation"}))
        self.assertFalse(P.is_crypto({"symbol": "CLUSDT", "symbolType": "commodity"}))
        self.assertFalse(P.is_crypto({"symbol": "EURUSDUSDT", "symbolType": "forex"}))
        self.assertFalse(P.is_crypto({"symbol": "PAXGUSDT", "symbolType": ""}))

    def test_rejects_non_monday(self):
        with self.assertRaises(ValueError):
            P.monday_asof(asof="2026-10-06")
        self.assertEqual(P.monday_asof(now=datetime(2026, 10, 8, 15, tzinfo=timezone.utc)), ASOF)


class TestScoreArithmetic(unittest.TestCase):
    def test_first_week_full_open_and_funding_sign(self):
        w = {"A": 0.05, "B": -0.05}
        rets = {"A": 0.10, "B": -0.10}
        fund = {"A": -0.01, "B": 0.01}          # long receives negative funding, short receives positive
        sc = P.score_book(w, None, rets, fund)
        self.assertAlmostEqual(sc["gross"], 0.01)
        self.assertAlmostEqual(sc["turnover"], 0.10)
        self.assertAlmostEqual(sc["cost"], 0.10 * (0.00055 + 0.0003))
        self.assertAlmostEqual(sc["funding"], +0.001)
        self.assertAlmostEqual(sc["net"], 0.01 - 0.10 * 0.00085 + 0.001)

    def test_funding_paid(self):
        sc = P.score_book({"A": 0.05, "B": -0.05}, None, {"A": 0, "B": 0}, {"A": 0.01, "B": -0.01})
        self.assertAlmostEqual(sc["funding"], -0.001)                                     # long pays +, short pays −

    def test_turnover_vs_drifted_previous(self):
        w = {"A": 0.05, "B": -0.05}
        sc0 = P.score_book(w, None, {"A": 0.0, "B": 0.0}, {})
        self.assertEqual(sc0["end_weights"], {"A": 0.05, "B": -0.05})
        sc1 = P.score_book(w, sc0["end_weights"], {"A": 0.0, "B": 0.0}, {})
        self.assertAlmostEqual(sc1["turnover"], 0.0)
        self.assertAlmostEqual(sc1["cost"], 0.0)
        sc2 = P.score_book({"A": 0.05, "C": -0.05}, sc0["end_weights"], {}, {})
        self.assertAlmostEqual(sc2["turnover"], 0.10)                                     # close B, open C
        self.assertFalse(any(isinstance(v, float) and math.isnan(v) for v in sc2.values() if not isinstance(v, dict)))


class TestScoreEndToEnd(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.src = FakeSource()

    def tearDown(self):
        shutil.rmtree(self.dir)

    def test_score_waits_then_scores_once(self):
        P.rebalance(self.src, ASOF, out_dir=self.dir, threads=1)
        new, _ = P.score(self.src, out_dir=self.dir, now=ASOF + timedelta(days=3))
        self.assertEqual(new, [])                                                          # next Monday not reached
        new, summary = P.score(self.src, out_dir=self.dir, now=ASOF + timedelta(days=7, minutes=10), threads=1)
        self.assertEqual(sorted(r["book"] for r in new), ["k56", "k91"])
        for r in new:
            self.assertTrue(r["first_week"])
            self.assertAlmostEqual(r["turnover"], sum(abs(x) for x in json.load(open(os.path.join(self.dir, "weights_2026-10-05.json")))["books"][r["book"]]["weights"].values()))
            self.assertTrue(math.isfinite(r["net"]))
        self.assertTrue(summary["k56"][0].startswith("BUILDING (1/26)"))
        again, _ = P.score(self.src, out_dir=self.dir, now=ASOF + timedelta(days=7, minutes=10), threads=1)
        self.assertEqual(again, [])                                                        # idempotent
        self.assertEqual(len(P.load_scores(self.dir)), 2)
        self.assertIn("Pre-registered bar", open(os.path.join(self.dir, "scorecard.md")).read())
        txt = P.telegram_text(new, summary)
        self.assertLessEqual(len(txt.splitlines()), 15)


class TestBar(unittest.TestCase):
    def test_statuses(self):
        self.assertTrue(P.apply_bar([0.01] * 10)[0].startswith("BUILDING (10/26)"))
        good = [0.02, -0.005] * 13                                                          # Sharpe high, MDD tiny, 50% +? → 50% < 55%
        st, _ = P.apply_bar(good)
        self.assertTrue(st.startswith("EXTENDED"))                                        # fails %pos, Sharpe >= 0.5
        good2 = [0.02, 0.01, -0.005] * 9 - np.array([0.0] * 27)
        self.assertEqual(P.apply_bar(list(good2[:26]))[0], "PASS")
        rng = np.random.default_rng(1)
        bad = list(rng.normal(-0.01, 0.02, 26))
        self.assertIn(P.apply_bar(bad)[0], ("FAIL", "KILLED"))
        self.assertEqual(P.apply_bar([0.01] * 5 + [-0.30])[0], "KILLED")                 # kill at any n
        self.assertEqual(P.apply_bar([0.006, -0.004] * 26)[0], "FAIL (bar not met by n=52)")

    def test_rules_hash_detects_change(self):
        h0 = P.rules_hash()
        rules = json.loads(json.dumps(P.RULES))
        rules["per_name_cap_of_leg"] = 0.2
        self.assertNotEqual(h0, P.rules_hash(rules))
        self.assertEqual(h0, P.rules_hash(json.loads(json.dumps(P.RULES))))


if __name__ == "__main__":
    unittest.main()
