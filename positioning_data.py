"""Binance USDT-M positioning metrics history (the free archive) → a look-ahead-safe index.

`data.binance.vision/data/futures/um/daily/metrics/<SYM>/<SYM>-metrics-<day>.zip`: one CSV per
day, one row per 5 minutes since 2023: sum_open_interest, sum_open_interest_value,
count_toptrader_long_short_ratio (top traders by ACCOUNTS), sum_toptrader_long_short_ratio
(top traders by POSITION size), count_long_short_ratio (all accounts), and
sum_taker_long_short_vol_ratio (taker buy / sell volume). Only the rows on 15-minute
boundaries are stored (`logs/backtest_cache/positioning/<SYM>.jsonl`, gitignored, ~11 KB raw
per symbol-day). Binance is the SOURCE of this input, not a proxy: the same numbers are served
live by Binance's public `futures/data/*LongShort*Ratio` endpoints (no key).

    python positioning_data.py fetch --symbols BTCUSDT,ETHUSDT --start 2025-10-20 --end 2026-11-02
    python positioning_data.py status

Research data only: no trade decision, no order API, no hosted model.
"""
from __future__ import annotations

import argparse
import io
import json
import math
import sys
import time
import zipfile
from bisect import bisect_right
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from pathlib import Path

import requests

from orderbook_data import REQUEST_TIMEOUT, WORKERS, binance_symbol, days_between

BASE_DIR = Path(__file__).resolve().parent
STORE_DIR = BASE_DIR / "logs" / "backtest_cache" / "positioning"
ARCHIVE = "https://data.binance.vision/data/futures/um/daily/metrics/{sym}/{sym}-metrics-{day}.zip"
BAR_MS = 15 * 60_000
MAX_ROW_AGE_MS = 10 * 60_000                    # a boundary whose own 5-min row is missing = no data
# stored row layout: [ms, oi, oi_value, top_acc, top_pos, glob_acc, taker]
COLS = ("oi", "oi_value", "top_acc", "top_pos", "glob_acc", "taker")


def reduce_day(csv_text: str) -> dict[int, list]:
    """One day's CSV → {B_ms: [B_ms, oi, oi_value, top_acc, top_pos, glob_acc, taker]} for the
    rows that fall on a 15-minute boundary."""
    out = {}
    for line in csv_text.splitlines()[1:]:
        parts = line.split(",")
        if len(parts) < 8:
            continue
        t = datetime.strptime(parts[0][:16], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
        m = int(t.timestamp() * 1000)
        if m % BAR_MS:
            continue
        try:
            vals = [float(x) for x in parts[2:8]]
        except ValueError:
            continue
        out[m] = [m] + vals
    return out


def fetch_day(sym: str, day: date) -> dict[int, list] | None:
    """Download + reduce one day. None = archive has no file for that day (404)."""
    url = ARCHIVE.format(sym=binance_symbol(sym), day=day.isoformat())
    for attempt in range(3):
        try:
            r = requests.get(url, timeout=REQUEST_TIMEOUT)
        except requests.RequestException:
            time.sleep(2 * (attempt + 1))
            continue
        if r.status_code == 404:
            return None
        if r.status_code != 200:
            time.sleep(2 * (attempt + 1))
            continue
        z = zipfile.ZipFile(io.BytesIO(r.content))
        return reduce_day(z.read(z.namelist()[0]).decode())
    raise RuntimeError(f"{sym} {day}: download failed after 3 attempts")


def store_path(sym: str) -> Path:
    return STORE_DIR / f"{sym}.jsonl"


def load_rows(sym: str) -> dict[int, list]:
    p = store_path(sym)
    if not p.exists():
        return {}
    rows = {}
    for line in p.read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            rows[int(r[0])] = r
    return rows


def save_rows(sym: str, rows: dict[int, list]) -> None:
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    with open(store_path(sym), "w") as f:
        for m in sorted(rows):
            f.write(json.dumps(rows[m], separators=(",", ":")) + "\n")


def fetch_symbol(sym: str, start: date, end: date, log=print) -> tuple[int, int]:
    """Fill the store for one symbol; days already stored are skipped. Returns (fetched, missing)."""
    rows = load_rows(sym)
    have_days = {datetime.fromtimestamp(m / 1000, timezone.utc).date() for m in rows}
    todo = [d for d in days_between(start, end) if d not in have_days]
    fetched = missing = 0
    with ThreadPoolExecutor(WORKERS) as ex:
        futs = {ex.submit(fetch_day, sym, d): d for d in todo}
        for fut in as_completed(futs):
            got = fut.result()
            if got is None:
                missing += 1
            else:
                rows.update(got)
                fetched += 1
    save_rows(sym, rows)
    log(f"  {sym}: +{fetched} days, {missing} missing on archive, {len(rows)} boundaries stored")
    return fetched, missing


class PositioningIndex:
    """Look-ahead-safe access. `at(sym, t_ms)` → the row at the last 15m boundary ≤ t_ms (None if
    none within MAX_ROW_AGE_MS); `series(sym, t_ms, bars, col)` → the values of the `bars`
    boundaries ending there, oldest first, None where a boundary is missing."""

    def __init__(self, symbols=None):
        self._ts: dict[str, list[int]] = {}
        self._rows: dict[str, dict[int, list]] = {}
        for sym in (symbols or [p.stem for p in STORE_DIR.glob("*.jsonl")]):
            rows = load_rows(sym)
            if rows:
                self._rows[sym] = rows
                self._ts[sym] = sorted(rows)

    def symbols(self):
        return sorted(self._rows)

    def at(self, sym: str, t_ms: int):
        ts = self._ts.get(sym)
        if not ts:
            return None
        i = bisect_right(ts, t_ms) - 1
        if i < 0 or t_ms - ts[i] > MAX_ROW_AGE_MS:
            return None
        return self._rows[sym][ts[i]]

    def series(self, sym: str, t_ms: int, bars: int, col: str):
        last = self.at(sym, t_ms)
        if last is None:
            return []
        k = 1 + COLS.index(col)
        rows = self._rows[sym]
        return [rows[m][k] if m in rows else None
                for m in range(last[0] - (bars - 1) * BAR_MS, last[0] + 1, BAR_MS)]


def log_ratio(x) -> float | None:
    """ln of a long/short ratio (symmetric around 0; None for a non-positive value)."""
    return math.log(x) if x and x > 0 else None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch", help="download + reduce days into the store (idempotent)")
    f.add_argument("--symbols", required=True, help="comma list of Bybit symbols")
    f.add_argument("--start", required=True, help="YYYY-MM-DD (UTC)")
    f.add_argument("--end", required=True, help="YYYY-MM-DD (UTC, inclusive)")
    sub.add_parser("status", help="what the store holds")
    a = ap.parse_args(argv)
    if a.cmd == "fetch":
        start, end = date.fromisoformat(a.start), date.fromisoformat(a.end)
        t0 = time.time()
        for sym in [s.strip() for s in a.symbols.split(",") if s.strip()]:
            fetch_symbol(sym, start, end)
            sys.stdout.flush()
        print(f"done in {time.time() - t0:.0f}s")
    else:
        idx = PositioningIndex()
        for sym in idx.symbols():
            ts = idx._ts[sym]
            print(f"{sym}: {len(ts)} boundaries "
                  f"{datetime.fromtimestamp(ts[0] / 1000, timezone.utc).date()} → "
                  f"{datetime.fromtimestamp(ts[-1] / 1000, timezone.utc).date()}")


if __name__ == "__main__":
    main()
