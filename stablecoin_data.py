#!/usr/bin/env python
"""stablecoin_data.py — DefiLlama stablecoin supply history + look-ahead-safe daily features.

Pre-registration: logs/backtest_reports/prereg_stablecoin_20261117.md. Two public, keyless series:
total USD-pegged stablecoin supply and USDT supply, one row per day dated 00:00 UTC. The current day's
row is updated during the day, so the row dated D is used only from D + 1 day (a feature at T reads rows
dated ≤ floor_day(T) − 1 day).

    python stablecoin_data.py fetch      # → logs/backtest_cache/stablecoins/{total,usdt}.json
    python stablecoin_data.py status

Research only: no trade decision, no order API, no hosted model.
"""
from __future__ import annotations

import argparse
import json
import math
from bisect import bisect_right
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE = Path(__file__).resolve().parent
STORE = BASE / "logs/backtest_cache/stablecoins"
URL = "https://stablecoins.llama.fi/stablecoincharts/all"
SERIES = {"total": None, "usdt": 1}            # DefiLlama stablecoin id (None = all stablecoins)
DAY_MS = 86_400_000
USE_LAG_DAYS = 1
# feature → (series, change window in days, z window in days, minimum values for the z)
FEATURES = {"stable_7d": ("total", 7, 90, 60), "stable_30d": ("total", 30, 180, 120), "usdt_7d": ("usdt", 7, 90, 60)}


def fetch(get=requests.get, log=print):
    """Download both series; each file is written only after its download parsed."""
    STORE.mkdir(parents=True, exist_ok=True)
    for name, sid in SERIES.items():
        params = {} if sid is None else {"stablecoin": sid}
        data = get(URL, params=params, timeout=60).json()
        rows = [[int(r["date"]) * 1000, float(r["totalCirculatingUSD"]["peggedUSD"])]
                for r in data if r.get("totalCirculatingUSD", {}).get("peggedUSD") is not None]
        if not rows:
            raise RuntimeError(f"stablecoin {name}: empty response")
        (STORE / f"{name}.json").write_text(json.dumps(sorted(rows)))
        log(f"{name}: {len(rows)} days, {datetime.fromtimestamp(rows[0][0] / 1000, timezone.utc):%Y-%m-%d} → "
            f"{datetime.fromtimestamp(rows[-1][0] / 1000, timezone.utc):%Y-%m-%d}")


def _features(rows, change_days, z_days, z_min):
    """{day_ms: z} — z of the change_days % change against the trailing z_days changes (inclusive)."""
    supply = {d: v for d, v in rows}
    days = sorted(supply)
    chg = {}
    for d in days:
        prev = supply.get(d - change_days * DAY_MS)
        if prev:
            chg[d] = 100.0 * (supply[d] / prev - 1.0)
    out = {}
    for d in days:
        if d not in chg:
            continue
        win = [chg[x] for x in (d - k * DAY_MS for k in range(z_days)) if x in chg]
        if len(win) < z_min:
            continue
        m = sum(win) / len(win)
        sd = math.sqrt(sum((v - m) ** 2 for v in win) / (len(win) - 1))
        if sd > 0:
            out[d] = (chg[d] - m) / sd
    return out


class StableIndex:
    """`at(kind, T)` = the feature of the row dated floor_day(T) − USE_LAG_DAYS (None if missing)."""

    def __init__(self, series_rows: dict):
        self.f = {k: _features(series_rows[s], c, z, mn) for k, (s, c, z, mn) in FEATURES.items()}

    def at(self, kind: str, t_ms: int):
        day = t_ms // DAY_MS * DAY_MS - USE_LAG_DAYS * DAY_MS
        return self.f[kind].get(day)

    @classmethod
    def load(cls):
        return cls({s: json.loads((STORE / f"{s}.json").read_text()) for s in SERIES})


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("fetch", "status"))
    a = ap.parse_args(argv)
    if a.cmd == "fetch":
        fetch()
        return
    for s in SERIES:
        p = STORE / f"{s}.json"
        if not p.exists():
            print(f"{s}: missing")
            continue
        rows = json.loads(p.read_text())
        print(f"{s}: {len(rows)} days, last {datetime.fromtimestamp(rows[-1][0] / 1000, timezone.utc):%Y-%m-%d} "
              f"${rows[-1][1] / 1e9:.1f}B")


if __name__ == "__main__":
    main()
