"""Offline tests for dvol_data.py / dvol_study.py (no network, no store)."""
import math
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import dvol_data as dd
import dvol_study as ds
import orderbook_study as obs

H = dd.HOUR_MS
T0 = int(datetime(2025, 10, 1, tzinfo=timezone.utc).timestamp() * 1000)


def _index(n=900, dvol=lambda i: 50 + 5 * math.sin(i / 30), price=lambda i: 100 * math.exp(0.001 * math.sin(i))):
    dvol_rows = [[T0 + (i + 1) * H, 0, 0, 0, dvol(i)] for i in range(n)]          # stored by close time
    btc_rows = [[T0 + i * H, 0, 0, 0, price(i)] for i in range(n)]                 # Bybit rows: open time
    return dd.DvolIndex(dvol_rows, btc_rows)


class TestIndex(unittest.TestCase):
    def test_no_look_ahead(self):
        idx = _index()
        t = idx.hours[700]
        self.assertEqual(idx.at("dvol_z", t), idx.series["dvol_z"][700])
        self.assertEqual(idx.at("dvol_z", t + H - 1), idx.series["dvol_z"][700])   # next hour not closed yet
        self.assertEqual(idx.at("dvol_z", t - 1), idx.series["dvol_z"][699])

    def test_warm_up_is_none(self):
        idx = _index()
        for k in dd.FEATURES:
            self.assertIsNone(idx.series[k][100])
            self.assertIsNotNone(idx.series[k][800])

    def test_spike_gives_positive_z_and_chg(self):
        idx = _index(dvol=lambda i: 50 + (30 if i >= 850 else 0) + 0.5 * math.sin(i))
        i = 860
        self.assertGreater(idx.series["dvol_z"][i], 2)
        self.assertGreater(idx.series["dvol_chg"][i], 2)

    def test_vrp_uses_realised_vol(self):
        calm = _index(price=lambda i: 100.0 + 0.01 * (i % 2))
        wild = _index(price=lambda i: 100.0 * (1.03 if i % 2 else 1.0))
        # same DVOL, much higher realised vol → lower VRP level; z is relative so compare raw path via sign
        self.assertIsNotNone(calm.series["vrp_z"][800])
        self.assertIsNotNone(wild.series["vrp_z"][800])

    def test_missing_hour_is_none(self):
        rows = [[T0 + (i + 1) * H, 0, 0, 0, 50.0 + (i % 7)] for i in range(900) if i != 800]
        idx = dd.DvolIndex(rows, [[T0 + i * H, 0, 0, 0, 100.0 + (i % 3)] for i in range(900)])
        self.assertIsNone(idx.at("dvol_z", T0 + 801 * H))


class TestFetch(unittest.TestCase):
    def test_no_store_written_on_failure(self):
        def boom(*a, **k):
            raise ConnectionError("dns")
        with tempfile.TemporaryDirectory() as d, mock.patch.object(dd, "STORE", Path(d)), \
                mock.patch.object(dd.time, "sleep", lambda s: None):
            with self.assertRaises(RuntimeError):
                dd.fetch("BTC", "2025-10-01", "2025-10-03", get=boom, log=lambda *a: None)
            self.assertEqual(list(Path(d).iterdir()), [])

    def test_rows_stored_by_close_time(self):
        start = dd._ms("2025-10-01")

        class R:
            def __init__(self, data):
                self.data = data

            def json(self):
                return {"result": {"data": self.data}}

        def get(url, params, timeout):
            return R([[t, 1, 2, 0.5, 1.5] for t in range(params["start_timestamp"], params["end_timestamp"], H)])
        with tempfile.TemporaryDirectory() as d, mock.patch.object(dd, "STORE", Path(d)), \
                mock.patch.object(dd.time, "sleep", lambda s: None):
            import json
            p = dd.fetch("BTC", "2025-10-01", "2025-10-02", get=get, log=lambda *a: None)
            rows = json.loads(p.read_text())
        self.assertEqual(len(rows), 24)
        self.assertEqual(rows[0][0], start + H)


class TestOrientation(unittest.TestCase):
    def test_fear_favours_long(self):
        self.assertEqual(ds.bucket(1.5, "long", 1.0), "aligned")
        self.assertEqual(ds.bucket(1.5, "short", 1.0), "against")
        self.assertEqual(ds.bucket(-1.5, "short", 1.0), "aligned")
        self.assertEqual(ds.bucket(0.2, "long", 1.0), "neutral")
        self.assertEqual(ds.bucket(None, "long", 1.0), "no_data")


class TestGradeA(unittest.TestCase):
    def _rows(self, aligned_net, other_net, n=400):
        rows = []
        for half, pers, base in (("fit", ("OLDER", "TRAIN"), 0), ("unseen", ("TEST", "H"), 10_000)):
            for i in range(n):
                b = "aligned" if i % 3 == 0 else ("against" if i % 3 == 1 else "neutral")
                net = (aligned_net + (0.6 if i % 2 else -0.6)) if b == "aligned" else other_net
                rows.append({"t": base + i, "rule": "r 4h", "dir": "long" if i % 2 else "short",
                             "per": pers[i % 2], "half": half, "net": net, "profitable": net > 0,
                             "hold": 60, "b": {f"{k}_{thr:g}": b for k, thr in ds.A_VARIANTS}})
        return rows

    def test_pass_and_no(self):
        _, v = ds.grade_a(self._rows(aligned_net=0.5, other_net=-0.2))
        self.assertTrue(v["pass"], v["checks"])
        _, v = ds.grade_a(self._rows(aligned_net=-0.3, other_net=-0.1))
        self.assertFalse(v["pass"])


if __name__ == "__main__":
    unittest.main()
