"""Behavior tests for the trader's checklist (2026-10-21): the supply/demand zone and trendline
detectors, live/backtest parity (the live stamp on a scan-sized window == the study's points on the
full cache), the scan never breaking on a checklist failure, and the weekly review's forward line.

Run: venv/bin/python test_checklist.py
"""

import json
import random
from pathlib import Path

import checklist
import derivs_data as dd
import main
import weekly_review

BASE = Path(__file__).resolve().parent
CACHE = BASE / "logs/backtest_cache/unified"
H4 = 14_400_000


def _flat(n, price=100.0):
    return {"o": [price] * n, "h": [price + 0.5] * n, "l": [price - 0.5] * n, "c": [price] * n, "atr": [1.0] * n}


def _set(f, i, o, h, l, c):
    f["o"][i], f["h"][i], f["l"][i], f["c"][i] = o, h, l, c


def _demand_frame(n=60, k=30, prior_touch=False, broken=False):
    """Base bar k-1 = [99.5, 100.5], impulse bar k closes 103, price holds ~104, returns at the last bar."""
    f = _flat(n)
    _set(f, k, 100.3, 103.2, 100.2, 103.0)
    for m in range(k + 1, n - 1):
        _set(f, m, 104.0, 104.5, 103.5, 104.0)
    if prior_touch:
        _set(f, k + 5, 104.0, 104.5, 100.4, 104.0)          # dipped into the zone before
    if broken:
        _set(f, k + 8, 104.0, 104.5, 98.0, 99.0)            # closed below the zone low
    _set(f, n - 1, 103.5, 103.6, 100.6, 100.8)               # the return
    return f


def test_supply_demand_zone():
    f = _demand_frame()
    zs = checklist.zones(f, long=True)
    assert any(z[0] == 30 and (z[1], z[2]) == (99.5, 100.5) for z in zs), zs
    j = len(f["c"]) - 1
    assert checklist.at_zone(f, zs, j, 100.8, long=True)
    assert not checklist.at_zone(f, zs, j, 102.5, long=True), "too far above the zone"
    assert not checklist.at_zone(f, zs, j, 100.8, long=False), "a demand zone is not a short point"
    f2 = _demand_frame(prior_touch=True)
    assert not checklist.at_zone(f2, checklist.zones(f2, True), j, 100.8, True), "not fresh"
    f3 = _demand_frame(broken=True)
    assert not checklist.at_zone(f3, checklist.zones(f3, True), j, 100.8, True), "broken"
    f4 = _flat(40)
    _set(f4, 30, 100.3, 103.2, 100.2, 103.0)
    _set(f4, 31, 101.0, 101.2, 100.6, 100.8)                 # never left: no "return"
    assert not checklist.at_zone(f4, checklist.zones(f4, True), 31, 100.8, True)
    print("  ✓ test_supply_demand_zone")


def test_trendline():
    n = 60
    f = _flat(n, 110.0)
    for m in range(n):                                       # strictly rising lows: no swing lows ...
        f["l"][m] = 109.0 + 0.01 * m
        f["c"][m], f["h"][m] = f["l"][m] + 1.0, f["l"][m] + 1.5
    f["l"][20], f["l"][35] = 100.0, 103.0                    # ... except two rising dips: +0.2 per bar
    for m in (20, 35):
        f["c"][m] = f["l"][m] + 1.0
    j = n - 1
    line_j = 100.0 + 0.2 * (j - 20)                          # 107.8
    sw = checklist.swings(f, long=True)
    assert 20 in sw and 35 in sw, sw
    assert checklist.at_trendline(f, sw, j, line_j + 0.3, long=True)
    assert not checklist.at_trendline(f, sw, j, line_j + 2.0, long=True), "too far above"
    f["c"][45] = 100.0                                       # a close well below the line → broken
    assert not checklist.at_trendline(f, sw, j, line_j + 0.3, long=True)
    print("  ✓ test_trendline")


def _rows(path, upto_ms, interval_ms, keep):
    rows = sorted({int(r[0]): r for r in json.loads(path.read_text())}.values(), key=lambda r: int(r[0]))
    return [r for r in rows if int(r[0]) + interval_ms <= upto_ms][-keep:]


def test_live_stamp_matches_study():
    """The scan sees 300 4h / 300 1h / 210 daily bars; the study sees the whole cache. Same points."""
    trades_p = BASE / "logs/backtest_reports/unified_20260923_trades.json"
    if not trades_p.exists() or not (CACHE / "BTCUSDT_240_20260327_20260923.json").exists():
        print("  - test_live_stamp_matches_study skipped (backtest caches not present)")
        return
    tag = "20260327_20260923"
    trades = [t for t in json.loads(trades_p.read_text()) if t["signal_ms"] > 1_780_000_000_000]
    random.Random(5).shuffle(trades)
    btc_path = CACHE / f"BTCUSDT_240_{tag}.json"
    btc_full = checklist.frame(json.loads(btc_path.read_text()), "240")
    checked = 0
    for t in trades[:40]:
        s, T = t["symbol"], t["signal_ms"]
        p4, p1 = CACHE / f"{s}_240_{tag}.json", CACHE / f"{s}_60_{tag}.json"
        pd_ = BASE / f"logs/backtest_cache/xs_{s}_D.json"
        fp, op = CACHE / f"{s}_funding_{tag}.json", CACHE / f"{s}_oi_1h_{tag}.json"
        if not all(p.exists() for p in (p4, p1, pd_, fp, op)):
            continue
        deriv = dd.DerivIndex([tuple(x) for x in json.loads(fp.read_text())],
                              [tuple(x) for x in json.loads(op.read_text())], "1h")
        daily_rows = sorted(json.loads(pd_.read_text()), key=lambda r: int(r[0]))
        f4, f1 = checklist.frame(json.loads(p4.read_text()), "240"), checklist.frame(json.loads(p1.read_text()), "60")
        study = checklist.points(f4, f1, checklist.daily_sma200(daily_rows), btc_full, deriv, T, t["direction"], t["tf"])
        live = checklist.stamp(_rows(p4, T, H4, 300), _rows(p1, T, 3_600_000, 300),
                               _rows(pd_, T, 86_400_000, 210), _rows(btc_path, T, H4, 300),
                               deriv, t["direction"], t["tf"])
        assert study and live and live["t_ms"] == T, (s, T, live)
        assert live["points"] == study[0], (s, T, t["signal"], live["points"], study[0])
        checked += 1
    assert checked >= 20, checked
    print(f"  ✓ test_live_stamp_matches_study ({checked} trades)")


class _FakeFetcher:
    def __init__(self, closed, derivs_fail=False):
        self.closed, self.derivs_fail = closed, derivs_fail

    def get_recent_derivs(self, symbol):
        if self.derivs_fail:
            raise TimeoutError("boom")
        return dd.DerivIndex([], [], "1h")


def _walk(n, interval_ms, start=1_780_000_000_000, seed=1):
    rng, p, out = random.Random(seed), 100.0, []
    for i in range(n):
        o = p
        p = max(1.0, p * (1 + rng.gauss(0, 0.01)))
        out.append([str(start + i * interval_ms), f"{o:.4f}", f"{max(o, p) * 1.003:.4f}",
                    f"{min(o, p) * 0.997:.4f}", f"{p:.4f}", f"{rng.uniform(1e5, 2e5):.1f}", "0"])
    return out


def test_stamp_checklist_never_breaks_scan():
    end = 1_780_000_000_000 + 300 * H4
    rows4, rows1 = _walk(300, H4), _walk(300, 3_600_000, start=end - 300 * 3_600_000, seed=2)
    rows_d = _walk(210, 86_400_000, start=end - 210 * 86_400_000, seed=3)
    good = {("AAA", "240"): rows4, ("AAA", "60"): rows1, ("AAA", "D"): rows_d, ("BTCUSDT", "240"): rows4}
    a, b = {"symbol": "AAA", "signal_tf": "4h", "direction": "long"}, {"symbol": "ZZZ", "signal_tf": "4h", "direction": "short"}
    main._stamp_checklist([a, b], _FakeFetcher(good))
    assert "checklist" in a and 0 <= a["checklist"]["score"] <= 9 and a["checklist"]["derivs_ok"] is True, a
    assert set(a["checklist"]["points"]) == set(checklist.ITEMS)
    assert "checklist" not in b, "no bars for ZZZ → unstamped, no exception"
    c = {"symbol": "AAA", "signal_tf": "1h", "direction": "short"}
    main._stamp_checklist([c], _FakeFetcher(good, derivs_fail=True))
    assert c["checklist"]["derivs_ok"] is False and not c["checklist"]["points"]["funding"], c
    d = {"symbol": "AAA", "signal_tf": "4h", "direction": "long"}
    main._stamp_checklist([d], _FakeFetcher({("AAA", "240"): [["x"]], ("AAA", "60"): rows1, ("AAA", "D"): rows_d}))
    assert "checklist" not in d, "garbage bars → unstamped, no exception"
    print("  ✓ test_stamp_checklist_never_breaks_scan")


def _row(score, net, profitable, derivs_ok=True):
    return {"status": "evaluated", "symbol": "AAA", "direction": "long", "source": "shadow",
            "net_blended_rr": net, "blended_rr": net + 0.05, "profitable": profitable,
            "eval_engine": "v2_market_open",
            "checklist": {"score": score, "derivs_ok": derivs_ok, "points": {}}}


def test_weekly_review_checklist_lines():
    rows = [_row(6, 0.3, True)] * 4 + [_row(2, -0.4, False)] * 6 + [_row(7, 5.0, True, derivs_ok=False)]
    text = "\n".join(weekly_review.checklist_lines(rows))
    assert "score ≥ 5: 4 scored · 100% profitable · net +0.30R/trade" in text, text
    assert "all candidates: 10 scored" in text and "building 4/30" in text, text
    ready = [_row(5, 0.2, True)] * 30 + [_row(1, -0.5, False)] * 30
    assert "READY" in "\n".join(weekly_review.checklist_lines(ready))
    worse = [_row(5, -0.1, False)] * 30 + [_row(1, 0.4, True)] * 30
    assert "NOT CONFIRMED" in "\n".join(weekly_review.checklist_lines(worse))
    assert "Checklist" in weekly_review.telegram_text("# Weekly review x\n\n## Checklist forward test (…)\n- a")
    print("  ✓ test_weekly_review_checklist_lines")


if __name__ == "__main__":
    test_supply_demand_zone()
    test_trendline()
    test_live_stamp_matches_study()
    test_stamp_checklist_never_breaks_scan()
    test_weekly_review_checklist_lines()
    print("All 5 checklist tests passed.")
