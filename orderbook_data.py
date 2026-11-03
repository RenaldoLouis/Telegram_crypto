"""Order-book depth history from Binance's public archive (the free proxy for Bybit).

Binance publishes, for every USDT-M perp, one depth snapshot per minute since 2023
(`data/futures/um/daily/bookDepth/<SYM>/<SYM>-bookDepth-YYYY-MM-DD.zip`, CSV columns
timestamp, percentage, depth, notional): cumulative resting depth within ±0.2 / 1 / 2 /
3 / 4 / 5 % of the mid. Negative percentage = bids (below mid), positive = asks.

This module downloads those files and keeps only what the study needs, per 15-minute
boundary B (UTC): the snapshot taken AT minute B (the standing book at the bar close,
no later minute is read) and the mean over the 15 minutes (B-15, B]. Output:
`logs/backtest_cache/orderbook/<SYM>.jsonl` (gitignored), one JSON row per boundary:
    [B_ms, bid_at[6], ask_at[6], bid_mean[6], ask_mean[6]]   (USD notional, BANDS order)

Bybit does not publish historical depth, so this is a PROXY: anything that passes the
study must be confirmed on Bybit's own feed before it touches a pick (same rule as the
CVD study, 2026-10-16). Research only: zero trading decisions, no order API.
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import time
import zipfile
from bisect import bisect_right
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent
STORE_DIR = BASE_DIR / "logs" / "backtest_cache" / "orderbook"
ARCHIVE = "https://data.binance.vision/data/futures/um/daily/bookDepth/{sym}/{sym}-bookDepth-{day}.zip"
BANDS = (0.2, 1.0, 2.0, 3.0, 4.0, 5.0)          # % from mid; index into the stored vectors
MINUTE_MS = 60_000
BAR_MS = 15 * MINUTE_MS
MAX_SNAPSHOT_AGE_MS = 5 * MINUTE_MS             # a boundary with no snapshot within 5 min = missing
# Bybit symbols whose Binance name differs (Binance-missing symbols are simply skipped).
SYMBOL_MAP = {"PUMPFUNUSDT": "PUMPUSDT"}
REQUEST_TIMEOUT = 60
WORKERS = 8


def binance_symbol(sym: str) -> str:
    return SYMBOL_MAP.get(sym, sym)


def reduce_day(csv_text: str) -> dict[int, list]:
    """One day's CSV → {B_ms: [B_ms, bid_at, ask_at, bid_mean, ask_mean]} for every 15m
    boundary B whose own minute carries a snapshot. Rows are per minute × band."""
    per_min: dict[int, tuple[list, list]] = {}
    for line in csv_text.splitlines()[1:]:
        ts_s, pct_s, _depth, notional_s = line.split(",")
        t = datetime.strptime(ts_s[:16], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
        m = int(t.timestamp() * 1000)
        pct = float(pct_s)
        try:
            k = BANDS.index(abs(pct))
        except ValueError:
            continue
        bid, ask = per_min.setdefault(m, ([0.0] * 6, [0.0] * 6))
        (bid if pct < 0 else ask)[k] = float(notional_s)
    out = {}
    for m, (bid, ask) in per_min.items():
        if m % BAR_MS:
            continue
        window = [per_min[x] for x in range(m - 14 * MINUTE_MS, m + MINUTE_MS, MINUTE_MS) if x in per_min]
        n = len(window)
        bid_mean = [sum(w[0][k] for w in window) / n for k in range(6)]
        ask_mean = [sum(w[1][k] for w in window) / n for k in range(6)]
        out[m] = [m, bid, ask, bid_mean, ask_mean]
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


def days_between(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def fetch_symbol(sym: str, start: date, end: date, log=print) -> tuple[int, int]:
    """Fill the store for one symbol; days already stored (any boundary present) are skipped.
    Returns (days fetched, days missing on the archive)."""
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


class OrderBookIndex:
    """Look-ahead-safe access: `at(sym, t_ms)` returns the row at the last 15m boundary ≤ t_ms
    (None if none within MAX_SNAPSHOT_AGE_MS); `window(sym, t_ms, bars)` the rows of the
    `bars` boundaries ending at that boundary (oldest first; shorter if gaps)."""

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
        if i < 0 or t_ms - ts[i] > MAX_SNAPSHOT_AGE_MS:
            return None
        return self._rows[sym][ts[i]]

    def window(self, sym: str, t_ms: int, bars: int):
        last = self.at(sym, t_ms)
        if last is None:
            return []
        rows = self._rows[sym]
        return [rows[m] for m in range(last[0] - (bars - 1) * BAR_MS, last[0] + 1, BAR_MS) if m in rows]


def imbalance(row, band: float, which: str = "at") -> float | None:
    """(bid - ask) / (bid + ask) of the cumulative notional within ±band %, in (-1, +1).
    Positive = more resting bids than asks (bid-heavy book). `which` = "at" (the boundary
    snapshot) or "mean" (the 15-minute mean)."""
    k = BANDS.index(band)
    bid, ask = (row[1][k], row[2][k]) if which == "at" else (row[3][k], row[4][k])
    tot = bid + ask
    return (bid - ask) / tot if tot > 0 else None


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
        idx = OrderBookIndex()
        for sym in idx.symbols():
            ts = idx._ts[sym]
            print(f"{sym}: {len(ts)} boundaries "
                  f"{datetime.fromtimestamp(ts[0] / 1000, timezone.utc).date()} → "
                  f"{datetime.fromtimestamp(ts[-1] / 1000, timezone.utc).date()}")


if __name__ == "__main__":
    main()
