"""Behavior tests for blend_paper — forward paper test #3 (synthetic market, no network).

Run: venv/bin/python test_blend_paper.py
"""

import json
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

import blend_paper as bp
import edge_search as es

DAY = 86_400_000
START = pd.Timestamp("2026-10-25", tz="UTC")


class FakeSource:
    """30 trending/mean coins + BTC from 2026-03-01, one perp listed 2026-10-11, funding 3×/day."""

    def __init__(self, fail=None, seed=7):
        rng = np.random.default_rng(seed)
        days = pd.date_range("2026-03-01", "2026-11-20", freq="D", tz="UTC")
        self.rows, self.fund, self.inst, self.calls, self.fail = {}, {}, [], 0, fail
        syms = ["BTCUSDT"] + [f"C{i:02d}USDT" for i in range(30)] + ["NEWUSDT"]
        for k, s in enumerate(syms):
            first = 224 if s == "NEWUSDT" else 0
            d = days[first:]
            c = 100 * np.exp(np.cumsum(rng.normal((k % 7 - 3) * 0.002, 0.03, len(d))))
            o = np.concatenate([[100.0], c[:-1]])
            t = [int(x.timestamp() * 1000) for x in d]
            self.rows[s] = [[ti, oi, max(oi, ci) * 1.01, min(oi, ci) * 0.99, ci, 1.0, 1e9] for ti, oi, ci in zip(t, o, c)]
            self.fund[s] = [[ti + h * 3_600_000, float(rng.normal(1e-4, 3e-4))] for ti in t for h in (0, 8, 16)]
            self.inst.append({"symbol": s, "status": "Trading", "launchTime": t[0]})

    def instruments(self):
        self.calls += 1
        return self.inst

    def daily(self, symbol, start_ms, end_ms):
        if symbol == self.fail:
            raise RuntimeError("boom")
        start = start_ms - start_ms % DAY
        return [r for r in self.rows[symbol] if start <= r[0] and r[0] + DAY <= end_ms]

    def funding(self, symbol, start_ms, end_ms):
        return [r for r in self.fund[symbol] if start_ms <= r[0] <= end_ms]

    def write_full(self, cache, end_ms):
        """The whole history up to end_ms, in the edge cache layout (the full-history reference)."""
        cache.mkdir(parents=True, exist_ok=True)
        (cache / "instruments.json").write_text(json.dumps({"instruments": self.inst}))
        for s in self.rows:
            (cache / f"{s}_D.json").write_text(json.dumps([r for r in self.rows[s] if r[0] + DAY <= end_ms]))
            (cache / f"{s}_funding.json").write_text(json.dumps([r for r in self.fund[s] if r[0] <= end_ms]))


def _run(src, tmp, now):
    return bp.run(now=pd.Timestamp(now, tz="UTC"), source=src, out=tmp / "out", cache=tmp / "cache",
                  telegram=False, start=START, min_universe=10)


def test_frozen_code_matches():
    assert bp.code_fingerprint() == bp.FROZEN_CODE, "the tested book's code changed — new paper test needed"
    assert abs(bp.SCALE - 1.039297 / 2) < 1e-12


def test_run_records_scores_and_is_idempotent():
    src = FakeSource()
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        new = _run(src, tmp, "2026-10-28 00:30")
        assert [r["day"] for r in new] == ["2026-10-25", "2026-10-26", "2026-10-27"]
        assert new[0]["gross"] == 0.0 and new[0]["cost"] < 0 and new[0]["net"] == new[0]["cost"]  # opening cost only
        w = json.loads((tmp / "out" / "weights_2026-10-27.json").read_text())
        assert w["n_positions"] > 10 and w["late_hours"] == 0.5 and w["rules_hash"] == bp.rules_hash()
        assert w["weights"]["NEWUSDT"] < 0                          # the new-listing short is on
        calls = src.calls
        assert _run(src, tmp, "2026-10-28 03:00") == [] and src.calls == calls   # idempotent, no fetch
        nxt = _run(src, tmp, "2026-10-29 00:40")
        assert [r["day"] for r in nxt] == ["2026-10-28"]
        assert len(bp.load_scores(tmp / "out")) == 4 and (tmp / "out" / "scorecard.md").exists()


def test_window_weights_equal_full_history():
    src = FakeSource()
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        _run(src, tmp, "2026-10-28 00:30")
        day = pd.Timestamp("2026-10-27", tz="UTC")
        src.write_full(tmp / "full", int((day + pd.Timedelta(days=1)).timestamp() * 1000))
        full = bp.target_weights(es.Panel(end=day, cache=tmp / "full")).loc[day]
        full = full[full.abs() > 1e-12]
        rec = pd.Series(json.loads((tmp / "out" / "weights_2026-10-27.json").read_text())["weights"])
        assert set(full.index) == set(rec.index)
        assert (full - rec.reindex(full.index)).abs().max() < 1e-9


def test_a_failed_symbol_aborts_without_writing_weights():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        try:
            _run(FakeSource(fail="C05USDT"), tmp, "2026-10-28 00:30")
            raise AssertionError("ran on a partial universe")
        except RuntimeError as e:
            assert "no partial book" in str(e)
        assert not list((tmp / "out").glob("weights_*.json"))
        try:
            bp.fetch_live(FakeSource(), tmp / "c2", 0, [], min_universe=100)
            raise AssertionError("ran on a tiny universe")
        except RuntimeError as e:
            assert "trading symbols" in str(e)


def test_backfill_is_capped_at_seven_days():
    rec = {pd.Timestamp("2026-10-26", tz="UTC"): {}}
    days = bp.days_to_record(pd.Timestamp("2026-11-20 01:00", tz="UTC"), rec, START)
    assert len(days) == 7 and days[-1] == pd.Timestamp("2026-11-19", tz="UTC")
    assert bp.days_to_record(pd.Timestamp("2026-10-25 23:00", tz="UTC"), {}, START) == []   # 10-25 not closed yet
    assert bp.days_to_record(pd.Timestamp("2026-10-26 00:05", tz="UTC"), {}, START) == [START]


def test_bar_status():
    def st(months, net=0.1, sharpe=1.2, dd=0.05):
        return {"months": months, "net": net, "sharpe": sharpe, "dd": dd}
    six = {f"2026-{m:02d}": 0.01 for m in (11, 12)} | {f"2027-{m:02d}": 0.01 for m in (1, 2, 3, 4)}
    assert bp.bar_status(st(six))[0] == "PASS"
    assert bp.bar_status(st(six, dd=0.16))[0] == "KILLED"
    assert bp.bar_status(st(six, net=-0.01))[0] == "FAIL"
    assert bp.bar_status(st(dict(six, **{"2026-11": -0.01, "2026-12": -0.01, "2027-01": -0.01})))[0] == "EXTEND"
    red = {"2026-11": -0.01, "2026-12": -0.01, "2027-01": -0.01, "2027-02": -0.01}
    assert bp.bar_status(st(red))[0] == "KILLED"
    assert bp.bar_status(st({"2026-10": -0.05, "2026-11": 0.01}))[0] == "RUNNING"   # October is a partial start


def test_telegram_only_when_a_week_or_month_completes():
    rows = [{"day": str(d.date()), "net": 0.001} for d in pd.date_range("2026-10-25", "2026-11-01", tz="UTC")]
    assert bp.telegram_text(rows[2:5], rows, "RUNNING", "") is None                     # 10-27 → 10-29
    text = bp.telegram_text(rows[-3:], rows, "RUNNING", "0/6 full months")            # 10-30 → 11-01
    assert "Week 10-26 → 11-01: +0.70%" in text and "October" in text and "paper only" in text
    first = bp.telegram_text(rows[:1], rows[:1], "RUNNING", "")                      # the start day is a Sunday
    assert "Week 10-19 → 10-25: +0.10% (1 day scored)" in first


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"  ✓ {t.__name__}")
    print(f"All {len(tests)} blend_paper tests passed.")
