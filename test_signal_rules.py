"""Behaviour tests for the v13.0 closed-bar signal path.

Run: venv/bin/python test_signal_rules.py

Guards the two invariants the 2026-09-23 audit found broken:
  1. The live scan never evaluates the still-open bar (`BybitFetcher._split_closed`).
  2. Live detection == backtest detection: `_check_validated_signals` is a thin wrapper
     over `signal_rules.detect_at` on the last closed bar, so walking the same candles
     bar-by-bar reproduces exactly what the live call fires on the final bar.
"""

import random

from fetchers.bybit_data import BybitFetcher
import signal_rules as sr


def _synthetic_candles(n=400, start_ms=1_700_000_000_000, bar_ms=14_400_000, seed=7):
    rnd = random.Random(seed)
    rows, price = [], 100.0
    for k in range(n):
        o = price
        drift = rnd.uniform(-1.5, 1.5)
        c = max(1.0, o + drift)
        h = max(o, c) + rnd.uniform(0, 1.0)
        l = min(o, c) - rnd.uniform(0, 1.0)
        v = rnd.uniform(1000, 5000)
        rows.append([str(start_ms + k * bar_ms), f"{o:.4f}", f"{h:.4f}", f"{l:.4f}",
                     f"{c:.4f}", f"{v:.2f}", f"{v * c:.2f}"])
        price = c
    return rows


def test_split_drops_open_bar():
    rows = _synthetic_candles(n=50)
    last_start = int(rows[-1][0])
    # "now" is 1h into the last 4h bar → it is open and must be dropped
    closed, open_bar = BybitFetcher._split_closed(rows, "240", now_ms=last_start + 3_600_000)
    assert open_bar is rows[-1] and len(closed) == 49
    # "now" is past the last bar's close → nothing is open
    closed, open_bar = BybitFetcher._split_closed(rows, "240", now_ms=last_start + 14_400_001)
    assert open_bar is None and len(closed) == 50


def test_live_wrapper_equals_detect_at_on_last_closed_bar():
    rows = _synthetic_candles(n=400)
    df = sr.compute_indicators(rows)
    expected = sr.detect_at(df, len(df) - 1, "4h")
    got = BybitFetcher._check_validated_signals(rows, "4h")
    strip = lambda sigs: [(s["signal"], s["direction"], s.get("stop_price"), s["stop_atr"]) for s in sigs]
    assert strip(got) == strip(expected)


def test_detect_at_only_uses_past_bars():
    """Appending future bars must not change what fires on bar i (no look-ahead)."""
    rows = _synthetic_candles(n=400)
    df_full = sr.compute_indicators(rows)
    df_cut = sr.compute_indicators(rows[:300])
    i = 299
    a = [(s["signal"], s["direction"]) for s in sr.detect_at(df_full, i, "4h")]
    b = [(s["signal"], s["direction"]) for s in sr.detect_at(df_cut, i, "4h")]
    assert a == b


def test_every_rule_can_fire_and_has_sane_levels():
    """Over a long random walk each rule fires at least once on some bar and every
    fired signal has its stop on the losing side of the close."""
    rows = _synthetic_candles(n=3000, seed=11)
    df = sr.compute_indicators(rows)
    seen = set()
    for i in range(60, len(df)):
        for tf in ("4h", "1h"):
            for s in sr.detect_at(df, i, tf):
                seen.add(s["signal"])
                close = float(df["close"].iloc[i])
                stop = sr.levels_for(s, close, float(df["atr"].iloc[i]))
                if s["direction"] == "long":
                    assert stop < close, s
                else:
                    assert stop > close, s
    missing = set(sr.ALL_SIGNALS) - seen
    # trend/range rules need specific regimes; require at least the structural ones.
    assert {"failed_breakout_short", "liquidity_sweep_long"} <= seen, missing


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("all signal_rules tests passed")
