"""Cross-venue funding and premium (basis) history: Bybit vs Binance vs OKX → a look-ahead-safe index.

Five series per Bybit symbol, stored in `logs/backtest_cache/venues/<SYM>_<series>.json` (gitignored):
    bybit_fund    [[settle_ms, rate, interval_hours], ...]   public /v5/market/funding/history; the interval
                                                              of a settlement = its spacing to the previous one
    binance_fund  [[settle_ms, rate, interval_hours], ...]   monthly `fundingRate` archive (data.binance.vision)
    bybit_prem    [[close_ms, premium], ...]                  public /v5/market/premium-index-price-kline, 15m close
    binance_prem  [[close_ms, premium], ...]                  monthly `premiumIndexKlines` 15m archive, close
    okx_basis     [[close_ms, basis], ...]                    15m swap last-price close / index close − 1
Every row is stamped with the time it became KNOWN (a settlement at its timestamp, floored to the minute;
a 15-minute bar at its close), and `VenueIndex` answers only from rows with timestamp ≤ the query time.
OKX funding is not stored (its public history keeps ~3 months). Each series is fetched once per symbol
for a FIXED window and skipped when its file exists (`--force` refetches); a failed download is never
written, so a rerun completes it.

    python venue_data.py fetch --symbols BTCUSDT,ETHUSDT --start 2025-11-01 --end 2026-10-15
    python venue_data.py status

Research data only (pre-registration `prereg_venue_dispersion_20261103.md`): no trade decision, no
order API, no hosted model. Bybit calls need the VPN; the Binance archive and OKX do not.
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import time
import zipfile
from bisect import bisect_right
from datetime import date, datetime, timezone
from pathlib import Path

import requests

from orderbook_data import REQUEST_TIMEOUT, binance_symbol

BASE_DIR = Path(__file__).resolve().parent
STORE_DIR = BASE_DIR / "logs" / "backtest_cache" / "venues"
SERIES = ("bybit_fund", "binance_fund", "bybit_prem", "binance_prem", "okx_basis")
FUND_SERIES = ("bybit_fund", "binance_fund")
PREM_SERIES = ("bybit_prem", "binance_prem", "okx_basis")
MINUTE_MS = 60_000
BAR_MS = 15 * MINUTE_MS
HOUR_MS = 60 * MINUTE_MS
MAX_SETTLEMENT_AGE_MS = 8 * HOUR_MS + 5 * MINUTE_MS   # a settlement older than this at T = no data
BPS = 10_000.0

BYBIT_HOSTS = ("https://api.bybit.com", "https://api.bytick.com")
BYBIT_FUND = "/v5/market/funding/history"
BYBIT_PREM = "/v5/market/premium-index-price-kline"
BYBIT_FUND_LIMIT, BYBIT_PREM_LIMIT = 200, 1000
BINANCE_FUND = "https://data.binance.vision/data/futures/um/monthly/fundingRate/{sym}/{sym}-fundingRate-{month}.zip"
BINANCE_PREM = "https://data.binance.vision/data/futures/um/monthly/premiumIndexKlines/{sym}/15m/{sym}-15m-{month}.zip"
OKX_CANDLES = "https://www.okx.com/api/v5/market/history-candles"
OKX_INDEX = "https://www.okx.com/api/v5/market/history-index-candles"
OKX_LIMIT = 300
OKX_PAUSE_S = 0.12                       # history endpoints allow 10–20 requests per 2 s
OKX_BASE_MAP = {"PUMPFUN": "PUMP"}       # Bybit base → OKX base where the ticker differs
RETRIES = 3


# ----------------------------------------------------------------------------- naming
def okx_base(sym: str) -> str:
    base = sym[:-4] if sym.endswith("USDT") else sym
    if base.startswith("1000"):          # 1000PEPE on Bybit = PEPE on OKX; a premium is unitless
        base = base[4:]
    return OKX_BASE_MAP.get(base, base)


def okx_swap(sym: str) -> str:
    return f"{okx_base(sym)}-USDT-SWAP"


def okx_index(sym: str) -> str:
    return f"{okx_base(sym)}-USDT"


def store_path(sym: str, series: str) -> Path:
    return STORE_DIR / f"{sym}_{series}.json"


def load_series(sym: str, series: str) -> list[list]:
    p = store_path(sym, series)
    return json.loads(p.read_text()) if p.exists() else []


def save_series(sym: str, series: str, rows: list[list]) -> None:
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    store_path(sym, series).write_text(json.dumps(rows, separators=(",", ":")))


def months_between(start: date, end: date):
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        yield f"{y:04d}-{m:02d}"
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


# ----------------------------------------------------------------------------- reducers (pure)
def funding_rows(points: list[tuple[int, float]]) -> list[list]:
    """[(settle_ms, rate), ...] in any order → [[settle_ms, rate, interval_hours], ...] oldest first,
    the interval of each settlement = the spacing to the previous one (the first takes the next spacing).
    Timestamps are floored to the minute (Binance stamps a few ms of latency on the settlement)."""
    pts = sorted({(t // MINUTE_MS) * MINUTE_MS: r for t, r in points}.items())
    if len(pts) < 2:
        return [[t, r, 8.0] for t, r in pts]
    out = []
    for i, (t, r) in enumerate(pts):
        prev_t = pts[i - 1][0] if i else None
        gap = (t - prev_t) if prev_t is not None else (pts[1][0] - t)
        out.append([t, r, round(gap / HOUR_MS, 4)])
    return out


def reduce_binance_funding(csv_text: str) -> list[list]:
    """`calc_time,funding_interval_hours,last_funding_rate` → [[settle_ms, rate, hours], ...]."""
    out = []
    for line in csv_text.splitlines()[1:]:
        parts = line.split(",")
        if len(parts) < 3:
            continue
        t = (int(parts[0]) // MINUTE_MS) * MINUTE_MS
        out.append([t, float(parts[2]), float(parts[1])])
    return out


def reduce_binance_premium(csv_text: str) -> list[list]:
    """premiumIndexKlines CSV (open_time, open, high, low, close, ...) → [[close_ms, close], ...]."""
    out = []
    for line in csv_text.splitlines():
        parts = line.split(",")
        if len(parts) < 5 or not parts[0].isdigit():
            continue
        out.append([int(parts[0]) + BAR_MS, float(parts[4])])
    return out


def okx_basis_rows(swap: dict[int, float], index: dict[int, float]) -> list[list]:
    """{open_ms: close} of the swap and of the index → [[close_ms, swap/index − 1], ...] for the
    bars both have (index close > 0)."""
    return [[t + BAR_MS, swap[t] / index[t] - 1.0] for t in sorted(swap) if t in index and index[t] > 0]


def merge_rows(rows: list[list]) -> list[list]:
    """Dedupe by timestamp (last wins), oldest first."""
    return [list(v) for _, v in sorted({r[0]: r for r in rows}.items())]


# ----------------------------------------------------------------------------- fetchers (network)
class FetchError(RuntimeError):
    pass


def _get_json(url: str, params: dict | None = None):
    last = None
    for attempt in range(RETRIES):
        try:
            r = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
            if r.status_code == 200:
                return r.json()
            last = f"HTTP {r.status_code}"
        except (requests.RequestException, ValueError) as e:
            last = repr(e)
        time.sleep(1.5 * (attempt + 1))
    raise FetchError(f"{url}: {last}")


def _get_zip_csv(url: str) -> str | None:
    """The CSV inside a Binance archive zip; None when the archive has no such file (404)."""
    last = None
    for attempt in range(RETRIES):
        try:
            r = requests.get(url, timeout=REQUEST_TIMEOUT)
        except requests.RequestException as e:
            last = repr(e)
            time.sleep(1.5 * (attempt + 1))
            continue
        if r.status_code == 404:
            return None
        if r.status_code == 200:
            z = zipfile.ZipFile(io.BytesIO(r.content))
            return z.read(z.namelist()[0]).decode()
        last = f"HTTP {r.status_code}"
        time.sleep(1.5 * (attempt + 1))
    raise FetchError(f"{url}: {last}")


def _bybit(path: str, params: dict) -> list:
    last = None
    for host in BYBIT_HOSTS:
        try:
            j = _get_json(host + path, params)
        except FetchError as e:
            last = e
            continue
        if j.get("retCode") != 0:
            raise FetchError(f"{path} {params.get('symbol')}: {j.get('retMsg')}")
        return j.get("result", {}).get("list", []) or []
    raise FetchError(str(last))


def fetch_bybit_funding(sym: str, start_ms: int, end_ms: int) -> list[list]:
    """Settlements in [start, end], paged backwards 200 at a time."""
    pts, end = {}, end_ms
    for _ in range(200):
        rows = _bybit(BYBIT_FUND, {"category": "linear", "symbol": sym, "startTime": start_ms,
                                   "endTime": end, "limit": BYBIT_FUND_LIMIT})
        if not rows:
            break
        for r in rows:
            pts[int(r["fundingRateTimestamp"])] = float(r["fundingRate"])
        oldest = min(int(r["fundingRateTimestamp"]) for r in rows)
        if oldest <= start_ms or len(rows) < BYBIT_FUND_LIMIT:
            break
        end = oldest - 1
        time.sleep(0.1)
    return funding_rows([(t, r) for t, r in pts.items() if start_ms <= t <= end_ms])


def fetch_bybit_premium(sym: str, start_ms: int, end_ms: int) -> list[list]:
    """15m premium-index bars whose OPEN is in [start, end), paged backwards 1000 at a time; stored by close."""
    out, end = {}, end_ms
    for _ in range(400):
        rows = _bybit(BYBIT_PREM, {"category": "linear", "symbol": sym, "interval": "15", "start": start_ms,
                                   "end": end, "limit": BYBIT_PREM_LIMIT})
        if not rows:
            break
        for r in rows:
            t = int(r[0])
            if start_ms <= t < end_ms:
                out[t + BAR_MS] = float(r[4])
        oldest = min(int(r[0]) for r in rows)
        if oldest <= start_ms or len(rows) < BYBIT_PREM_LIMIT:
            break
        end = oldest - 1
        time.sleep(0.05)
    return [[t, v] for t, v in sorted(out.items())]


def fetch_binance_funding(sym: str, start: date, end: date) -> list[list]:
    rows = []
    for month in months_between(start, end):
        csv = _get_zip_csv(BINANCE_FUND.format(sym=binance_symbol(sym), month=month))
        if csv:
            rows += reduce_binance_funding(csv)
    return merge_rows(rows)


def fetch_binance_premium(sym: str, start: date, end: date) -> list[list]:
    rows = []
    for month in months_between(start, end):
        csv = _get_zip_csv(BINANCE_PREM.format(sym=binance_symbol(sym), month=month))
        if csv:
            rows += reduce_binance_premium(csv)
    return merge_rows(rows)


def _okx_closes(url: str, inst: str, start_ms: int, end_ms: int) -> dict[int, float]:
    """{open_ms: close} of the 15m candles with open in [start, end), paged backwards with `after`."""
    out, after = {}, end_ms
    for _ in range(2000):
        j = _get_json(url, {"instId": inst, "bar": "15m", "limit": OKX_LIMIT, "after": after})
        if j.get("code") != "0":
            raise FetchError(f"OKX {inst}: {j.get('msg')}")
        rows = j.get("data") or []
        if not rows:
            break
        for r in rows:
            t = int(r[0])
            if start_ms <= t < end_ms:
                out[t] = float(r[4])
        oldest = min(int(r[0]) for r in rows)
        if oldest <= start_ms:
            break
        after = oldest
        time.sleep(OKX_PAUSE_S)
    return out


def fetch_okx_basis(sym: str, start_ms: int, end_ms: int) -> list[list]:
    """None-safe: a symbol OKX does not list yields [] (stored, so it is not retried)."""
    j = _get_json("https://www.okx.com/api/v5/public/instruments", {"instType": "SWAP", "instId": okx_swap(sym)})
    if not j.get("data"):
        return []
    swap = _okx_closes(OKX_CANDLES, okx_swap(sym), start_ms, end_ms)
    index = _okx_closes(OKX_INDEX, okx_index(sym), start_ms, end_ms)
    return okx_basis_rows(swap, index)


FETCHERS = {
    "bybit_fund": lambda sym, s_ms, e_ms, s, e: fetch_bybit_funding(sym, s_ms, e_ms),
    "binance_fund": lambda sym, s_ms, e_ms, s, e: fetch_binance_funding(sym, s, e),
    "bybit_prem": lambda sym, s_ms, e_ms, s, e: fetch_bybit_premium(sym, s_ms, e_ms),
    "binance_prem": lambda sym, s_ms, e_ms, s, e: fetch_binance_premium(sym, s, e),
    "okx_basis": lambda sym, s_ms, e_ms, s, e: fetch_okx_basis(sym, s_ms, e_ms),
}


def fetch_symbol(sym: str, start: date, end: date, series=SERIES, force=False, log=print) -> dict[str, int]:
    """Fill every requested series for one symbol; an existing file is kept unless `force`. A failed
    series is logged and left unwritten (rerun to complete). Returns {series: rows stored or -1}."""
    s_ms = int(datetime(start.year, start.month, start.day, tzinfo=timezone.utc).timestamp() * 1000)
    e_ms = int(datetime(end.year, end.month, end.day, tzinfo=timezone.utc).timestamp() * 1000)
    out = {}
    for name in series:
        if store_path(sym, name).exists() and not force:
            out[name] = len(load_series(sym, name))
            continue
        t0 = time.time()
        try:
            rows = FETCHERS[name](sym, s_ms, e_ms, start, end)
        except FetchError as e:
            log(f"  {sym} {name}: FAILED ({e}) — not stored")
            out[name] = -1
            continue
        save_series(sym, name, rows)
        out[name] = len(rows)
        log(f"  {sym} {name}: {len(rows)} rows in {time.time() - t0:.0f}s")
    return out


# ----------------------------------------------------------------------------- index
class VenueIndex:
    """Look-ahead-safe access to the five series of every symbol in the store (or `symbols`)."""

    def __init__(self, symbols=None):
        self._fund: dict[str, dict[str, tuple[list[int], list[list]]]] = {}
        self._prem: dict[str, dict[str, dict[int, float]]] = {}
        names = symbols or sorted({p.stem.rsplit("_", 2)[0] for p in STORE_DIR.glob("*_bybit_prem.json")})
        for sym in names:
            self._fund[sym] = {}
            for name in FUND_SERIES:
                rows = load_series(sym, name)
                self._fund[sym][name] = ([r[0] for r in rows], rows)
            self._prem[sym] = {name: {r[0]: r[1] for r in load_series(sym, name)} for name in PREM_SERIES}

    def symbols(self):
        return sorted(s for s in self._prem if self._prem[s]["bybit_prem"])

    def settled(self, sym: str, name: str, t_ms: int):
        """[settle_ms, rate, hours] of the last settlement ≤ t_ms within MAX_SETTLEMENT_AGE_MS, else None."""
        ts, rows = self._fund.get(sym, {}).get(name, ([], []))
        i = bisect_right(ts, t_ms) - 1
        if i < 0 or t_ms - ts[i] > MAX_SETTLEMENT_AGE_MS:
            return None
        return rows[i]

    def fund_disp(self, sym: str, t_ms: int):
        """Bybit minus Binance last settled rate, each as an 8-hour equivalent, in bps; None if either missing."""
        b, n = self.settled(sym, "bybit_fund", t_ms), self.settled(sym, "binance_fund", t_ms)
        if b is None or n is None or not b[2] or not n[2]:
            return None
        return (b[1] * 8.0 / b[2] - n[1] * 8.0 / n[2]) * BPS

    def basis_disp_at(self, sym: str, close_ms: int):
        """d(B) = Bybit premium at the bar closing at B minus the mean of the other venues' basis at B;
        None unless Bybit and at least one other venue have the bar."""
        p = self._prem.get(sym)
        if not p or close_ms not in p["bybit_prem"]:
            return None
        others = [p[name][close_ms] for name in ("binance_prem", "okx_basis") if close_ms in p[name]]
        if not others:
            return None
        return p["bybit_prem"][close_ms] - sum(others) / len(others)

    def basis_disp_series(self, sym: str, t_ms: int, bars: int) -> list:
        """d at the `bars` 15m boundaries ending at the last boundary ≤ t_ms, oldest first (None where missing)."""
        last = (t_ms // BAR_MS) * BAR_MS
        return [self.basis_disp_at(sym, b) for b in range(last - (bars - 1) * BAR_MS, last + 1, BAR_MS)]


# ----------------------------------------------------------------------------- CLI
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch", help="download the five series per symbol for a fixed window (idempotent)")
    f.add_argument("--symbols", required=True, help="comma list of Bybit symbols")
    f.add_argument("--start", required=True, help="YYYY-MM-DD (UTC)")
    f.add_argument("--end", required=True, help="YYYY-MM-DD (UTC, exclusive for bars, inclusive for months)")
    f.add_argument("--series", default=",".join(SERIES))
    f.add_argument("--force", action="store_true")
    sub.add_parser("status", help="what the store holds")
    a = ap.parse_args(argv)
    if a.cmd == "fetch":
        start, end = date.fromisoformat(a.start), date.fromisoformat(a.end)
        series = tuple(s.strip() for s in a.series.split(",") if s.strip())
        t0 = time.time()
        for sym in [s.strip() for s in a.symbols.split(",") if s.strip()]:
            fetch_symbol(sym, start, end, series, a.force)
            sys.stdout.flush()
        print(f"done in {time.time() - t0:.0f}s")
    else:
        idx = VenueIndex()
        for sym in idx.symbols():
            parts = []
            for name in SERIES:
                rows = load_series(sym, name)
                if rows:
                    d0 = datetime.fromtimestamp(rows[0][0] / 1000, timezone.utc).date()
                    d1 = datetime.fromtimestamp(rows[-1][0] / 1000, timezone.utc).date()
                    parts.append(f"{name} {len(rows)} ({d0}→{d1})")
                else:
                    parts.append(f"{name} 0")
            print(f"{sym}: " + ", ".join(parts))


if __name__ == "__main__":
    main()
