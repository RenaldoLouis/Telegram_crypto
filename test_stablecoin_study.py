"""Offline tests for stablecoin_data.py / stablecoin_study.py (no network)."""
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import stablecoin_data as sd
import stablecoin_study as ss

DAY = sd.DAY_MS
D0 = int(datetime(2025, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)


def _rows(n=400, growth=lambda i: 0.001 * (1 + (i % 5) / 10)):
    v, out = 1e11, []
    for i in range(n):
        v *= 1 + growth(i)
        out.append([D0 + i * DAY, v])
    return out


class TestIndex(unittest.TestCase):
    def test_uses_yesterdays_row_only(self):
        idx = sd.StableIndex({"total": _rows(), "usdt": _rows()})
        day = D0 + 300 * DAY
        self.assertEqual(idx.at("stable_7d", day + 5 * 3_600_000), idx.f["stable_7d"][day - DAY])
        self.assertEqual(idx.at("stable_7d", day), idx.f["stable_7d"][day - DAY])           # 00:00 of D → D−1

    def test_mint_wave_gives_positive_z(self):
        rows = _rows(growth=lambda i: 0.004 if 350 <= i < 360 else 0.001 * (1 + (i % 5) / 10))
        idx = sd.StableIndex({"total": rows, "usdt": rows})
        self.assertGreater(idx.f["stable_7d"][D0 + 357 * DAY], 2)
        self.assertGreater(idx.at("usdt_7d", D0 + 358 * DAY), 2)

    def test_warm_up_and_gaps_are_none(self):
        rows = [r for i, r in enumerate(_rows()) if i != 250]
        idx = sd.StableIndex({"total": rows, "usdt": rows})
        self.assertIsNone(idx.at("stable_30d", D0 + 50 * DAY))
        self.assertIsNone(idx.f["stable_7d"].get(D0 + 257 * DAY))                            # 7 days after the gap


class TestFetch(unittest.TestCase):
    def test_writes_both_series(self):
        class R:
            def __init__(self, sid):
                self.sid = sid

            def json(self):
                return [{"date": str(1735689600 + i * 86400), "totalCirculatingUSD": {"peggedUSD": 1e11 + i}}
                        for i in range(3)]
        with tempfile.TemporaryDirectory() as d, mock.patch.object(sd, "STORE", Path(d)):
            sd.fetch(get=lambda url, params, timeout: R(params.get("stablecoin")), log=lambda *a: None)
            self.assertEqual(len(json.loads((Path(d) / "usdt.json").read_text())), 3)
            self.assertEqual(json.loads((Path(d) / "total.json").read_text())[0][0], 1735689600000)

    def test_empty_response_raises_without_writing(self):
        class R:
            def json(self):
                return []
        with tempfile.TemporaryDirectory() as d, mock.patch.object(sd, "STORE", Path(d)):
            with self.assertRaises(RuntimeError):
                sd.fetch(get=lambda url, params, timeout: R(), log=lambda *a: None)
            self.assertFalse((Path(d) / "total.json").exists())


class TestStudy(unittest.TestCase):
    def test_nine_trials_and_follow_the_money(self):
        self.assertEqual(len(ss.A_VARIANTS) + len(ss.B_VARIANTS), 9)
        self.assertEqual(ss.ds.bucket(1.2, "long", 1.0), "aligned")


if __name__ == "__main__":
    unittest.main()
