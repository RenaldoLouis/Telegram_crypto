"""Offline tests for options_collector.py (no network)."""
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import options_collector as oc

NOW = int(datetime(2026, 11, 17, 8, tzinfo=timezone.utc).timestamp() * 1000)


def _chain(code, fwd, iv_fn):
    """Strikes 50 %–150 % of fwd, both sides, IV from iv_fn(moneyness)."""
    out = []
    for k in range(50, 151, 5):
        strike = fwd * k / 100
        for cp in ("C", "P"):
            out.append({"instrument_name": f"BTC-{code}-{int(strike)}-{cp}", "mark_iv": iv_fn(k / 100),
                        "underlying_price": fwd, "volume": 10.0 if cp == "P" else 5.0, "open_interest": 100.0})
    return out


class TestMaths(unittest.TestCase):
    def test_expiry_parse(self):
        self.assertEqual(oc.expiry_ms("27NOV26"), int(datetime(2026, 11, 27, 8, tzinfo=timezone.utc).timestamp() * 1000))
        self.assertEqual(oc.expiry_ms("4DEC26"), int(datetime(2026, 12, 4, 8, tzinfo=timezone.utc).timestamp() * 1000))

    def test_delta_bounds_and_put_call_parity(self):
        c = oc.delta(100, 100, 50, 0.1, True)
        p = oc.delta(100, 100, 50, 0.1, False)
        self.assertAlmostEqual(c - p, 1.0)
        self.assertGreater(c, 0.5)                         # ATM-forward call delta slightly above 0.5
        self.assertIsNone(oc.delta(100, 100, 0, 0.1, True))


class TestSummarise(unittest.TestCase):
    def test_flat_smile_has_zero_skew(self):
        chain = _chain("27NOV26", 65000, lambda m: 40.0) + _chain("25DEC26", 65200, lambda m: 40.0)
        r = oc.summarise(chain, "BTC", NOW)
        self.assertAlmostEqual(r["iv30_atm"], 40.0, places=2)
        self.assertAlmostEqual(r["rr25_30"], 0.0, places=2)
        self.assertAlmostEqual(r["pc_vol"], 2.0)
        self.assertAlmostEqual(r["pc_oi"], 1.0)

    def test_put_skew_is_negative_rr(self):
        skew = lambda m: 40.0 + 30.0 * max(0.0, 1.0 - m)          # downside strikes richer
        r = oc.summarise(_chain("27NOV26", 65000, skew) + _chain("25DEC26", 65200, skew), "BTC", NOW)
        self.assertLess(r["rr25_30"], -1.0)

    def test_expiry_window(self):
        r = oc.summarise(_chain("17NOV26", 65000, lambda m: 40.0), "BTC", NOW)   # expires now → excluded
        self.assertIsNone(r)

    def test_30d_needs_bracketing_expiries(self):
        r = oc.summarise(_chain("27NOV26", 65000, lambda m: 40.0), "BTC", NOW)   # only 10 days
        self.assertIsNone(r["iv30_atm"])
        self.assertIsNone(r["rr25_30"])


class TestIO(unittest.TestCase):
    def test_snapshot_survives_one_currency_failing(self):
        class R:
            def json(self):
                return {"result": _chain("27NOV26", 65000, lambda m: 40.0) + _chain("25DEC26", 65200, lambda m: 40.0)}

        def get(url, params, timeout):
            if params["currency"] == "ETH":
                raise ConnectionError("dns")
            return R()
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "raw.jsonl"
            self.assertEqual(oc.snapshot(out, get=get, now_ms=NOW, log=lambda m: None), 1)
            self.assertEqual(json.loads(out.read_text())["currency"], "BTC")

    def test_fold_dedupes_and_skips_half_line(self):
        with tempfile.TemporaryDirectory() as d:
            raw, out_dir = Path(d) / "raw.jsonl", Path(d) / "options"
            rows = [{"t_ms": NOW, "currency": "BTC"}, {"t_ms": NOW + 900_000, "currency": "BTC"},
                    {"t_ms": NOW, "currency": "ETH"}]
            raw.write_text("\n".join(json.dumps(r) for r in rows) + "\n{\"t_ms\": 1")
            self.assertEqual(oc.fold(raw, out_dir), 3)
            self.assertEqual(oc.fold(raw, out_dir), 0)          # idempotent
            self.assertEqual(len((out_dir / "BTC_2026-11.jsonl").read_text().splitlines()), 2)


if __name__ == "__main__":
    unittest.main()
