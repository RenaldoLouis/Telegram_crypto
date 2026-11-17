#!/usr/bin/env python
"""dvol_data.py — Deribit DVOL (30-day implied volatility index) history + look-ahead-safe features.

Pre-registration: logs/backtest_reports/prereg_dvol_20261117.md. Deribit's public
`get_volatility_index_data` (no key, no VPN) returns hourly OHLC of the index; each bar is stored by its
CLOSE time (open + 1 h), so a feature at T reads only bars closed at or before T.

    python dvol_data.py fetch [--currency BTC --start 2025-10-01 --end 2026-10-21]
    python dvol_data.py status

Store: logs/backtest_cache/dvol/<CUR>_1h_<start>_<end>.json (gitignored), rows [close_ms, o, h, l, c].
Research only: no trade decision, no order API, no hosted model.
"""
from __future__ import annotations

import argparse
import json
import math
import time
from bisect import bisect_right
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE = Path(__file__).resolve().parent
STORE = BASE / "logs/backtest_cache/dvol"
HARNESS_CACHE = BASE / "logs/backtest_cache/unified"
URL = "https://www.deribit.com/api/v2/public/get_volatility_index_data"
HOUR_MS = 3_600_000
CHUNK_MS = 900 * HOUR_MS                 # stay under the endpoint's per-call point limit
DEFAULT_START, DEFAULT_END = "2025-10-01", "2026-10-21"
Z_HOURS, Z_MIN = 720, 500                # trailing 30 days of hourly values
CHG_HOURS = 24
RV_HOURS = 168                           # realised vol over the last 7 days of hourly returns
ANNUALISE = math.sqrt(24 * 365) * 100
FEATURES = ("dvol_z", "dvol_chg", "vrp_z")


def _ms(day: str) -> int:
    return int(datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)


def store_path(currency: str, start: str, end: str) -> Path:
    return STORE / f"{currency}_1h_{start.replace('-', '')}_{end.replace('-', '')}.json"


# ----------------------------------------------------------------------------- fetch
def fetch(currency="BTC", start=DEFAULT_START, end=DEFAULT_END, get=requests.get, log=print):
    """Download hourly DVOL for [start, end) in chunks; write the store only when every chunk succeeded."""
    s_ms, e_ms = _ms(start), _ms(end)
    rows = {}
    t = s_ms
    while t < e_ms:
        t2 = min(t + CHUNK_MS, e_ms)
        for attempt in range(4):
            try:
                resp = get(URL, params={"currency": currency, "start_timestamp": t, "end_timestamp": t2,
                                        "resolution": "3600"}, timeout=20).json()
                data = resp["result"]["data"]
                break
            except Exception as exc:          # network blip → retry, then give up without writing
                if attempt == 3:
                    raise RuntimeError(f"DVOL fetch failed at {t}: {exc}") from exc
                time.sleep(2 * (attempt + 1))
        for o_ms, o, h, l, c in data:
            if s_ms <= int(o_ms) < e_ms:
                rows[int(o_ms) + HOUR_MS] = [int(o_ms) + HOUR_MS, float(o), float(h), float(l), float(c)]
        t = t2
        time.sleep(0.1)
    out = [rows[k] for k in sorted(rows)]
    STORE.mkdir(parents=True, exist_ok=True)
    p = store_path(currency, start, end)
    p.write_text(json.dumps(out))
    log(f"{currency}: {len(out)} hourly bars → {p}")
    return p


# ----------------------------------------------------------------------------- features
def _zscores(vals, window=Z_HOURS, min_n=Z_MIN):
    """z of vals[i] against the trailing `window` values ending at i (inclusive); None where too thin."""
    out = [None] * len(vals)
    for i in range(len(vals)):
        if vals[i] is None:
            continue
        win = [v for v in vals[max(0, i - window + 1):i + 1] if v is not None]
        if len(win) < min_n:
            continue
        m = sum(win) / len(win)
        sd = math.sqrt(sum((v - m) ** 2 for v in win) / (len(win) - 1))
        if sd > 0:
            out[i] = (vals[i] - m) / sd
    return out


class DvolIndex:
    """Hourly grid of the three features, indexed by bar close time; `at(kind, T)` reads the last
    hourly close ≤ T (None if that hour is missing or the feature is undefined)."""

    def __init__(self, dvol_rows, btc_rows):
        dv = {int(r[0]): float(r[4]) for r in dvol_rows}
        px = {int(r[0]) + HOUR_MS: float(r[4]) for r in btc_rows}       # Bybit kline row: open time first
        start, end = min(dv), max(dv)
        self.hours = list(range(start, end + HOUR_MS, HOUR_MS))
        d = [dv.get(h) for h in self.hours]
        p = [px.get(h) for h in self.hours]
        chg = [None if (i < CHG_HOURS or d[i] is None or d[i - CHG_HOURS] is None) else d[i] - d[i - CHG_HOURS]
               for i in range(len(d))]
        sd_chg = [None] * len(d)
        for i in range(len(d)):
            win = [v for v in chg[max(0, i - Z_HOURS + 1):i + 1] if v is not None]
            if chg[i] is not None and len(win) >= Z_MIN:
                m = sum(win) / len(win)
                sd = math.sqrt(sum((v - m) ** 2 for v in win) / (len(win) - 1))
                sd_chg[i] = chg[i] / sd if sd > 0 else None
        rets = [None if (i == 0 or p[i] is None or p[i - 1] is None) else math.log(p[i] / p[i - 1])
                for i in range(len(p))]
        vrp = [None] * len(d)
        for i in range(len(d)):
            win = [r for r in rets[max(0, i - RV_HOURS + 1):i + 1] if r is not None]
            if d[i] is None or len(win) < RV_HOURS * 0.9:
                continue
            m = sum(win) / len(win)
            rv = math.sqrt(sum((r - m) ** 2 for r in win) / (len(win) - 1)) * ANNUALISE
            vrp[i] = d[i] - rv
        self.series = {"dvol_z": _zscores(d), "dvol_chg": sd_chg, "vrp_z": _zscores(vrp)}

    def at(self, kind: str, t_ms: int):
        i = bisect_right(self.hours, t_ms) - 1
        return None if i < 0 else self.series[kind][i]

    @classmethod
    def load(cls, currency="BTC", start=DEFAULT_START, end=DEFAULT_END,
             btc_cache=HARNESS_CACHE / "BTCUSDT_60_20251021_20261021.json"):
        return cls(json.loads(store_path(currency, start, end).read_text()), json.loads(Path(btc_cache).read_text()))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("fetch", "status"))
    ap.add_argument("--currency", default="BTC")
    ap.add_argument("--start", default=DEFAULT_START)
    ap.add_argument("--end", default=DEFAULT_END)
    a = ap.parse_args(argv)
    if a.cmd == "fetch":
        fetch(a.currency, a.start, a.end)
    else:
        p = store_path(a.currency, a.start, a.end)
        if not p.exists():
            print(f"{p.name}: missing")
            return
        rows = json.loads(p.read_text())
        exp = (_ms(a.end) - _ms(a.start)) // HOUR_MS
        print(f"{p.name}: {len(rows)} / {exp} hours ({100 * len(rows) / exp:.1f}%)")


if __name__ == "__main__":
    main()
