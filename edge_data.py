"""Full-history Bybit data for the edge search (2026-10-25) — every USDT perpetual ever listed.

The playbook study ran on 15 coins that survived to today. This module downloads the daily bars
and the funding history of EVERY Bybit linear USDT perpetual — the ones trading today AND the
313 delisted ones (`instruments-info` with status=Closed; their klines and funding are served
when the request names a window inside their life) — so the search is not a survivors-only
test. Tokenized stocks / ETFs / commodities / forex (`symbolType`) and pegged tokens are dropped,
as in the live scan.

Cache: `logs/backtest_cache/edge/` (gitignored) — `instruments.json`, `<SYM>_D.json`
(rows [ts, o, h, l, c, volume, turnover], oldest first, closed days only) and
`<SYM>_funding.json` ([[ts, rate], ...]). A symbol whose download failed is not cached.

Usage:
    venv/bin/python edge_data.py fetch            # ~1,100 symbols, 6 threads, resumable
    venv/bin/python edge_data.py fetch-oi         # daily open interest for every cached symbol
    venv/bin/python edge_data.py status           # what is cached
"""

import argparse
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import requests

import config

BASE = "https://api.bybit.com"
CACHE = Path(__file__).resolve().parent / "logs" / "backtest_cache" / "edge"
DAY_MS = 86_400_000
EARLIEST_MS = int(datetime(2020, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
KLINE_PAGE_DAYS = 1000
FUNDING_PAGE, FUNDING_MAX_PAGES = 200, 150
THREADS = 6
MIN_INTERVAL_S = 0.05                       # shared pacing: ≤ 20 requests/s across threads

_lock = threading.Lock()
_last = [0.0]
_session = threading.local()


def _get(path, params, retries=5):
    """GET with shared pacing and retries; returns `result` or raises after the last retry."""
    for attempt in range(retries):
        with _lock:
            wait = _last[0] + MIN_INTERVAL_S - time.time()
            if wait > 0:
                time.sleep(wait)
            _last[0] = time.time()
        try:
            if not hasattr(_session, "s"):
                _session.s = requests.Session()
            r = _session.s.get(BASE + path, params=params, timeout=20).json()
            if r.get("retCode") == 0:
                return r.get("result", {})
            if r.get("retCode") == 10006:                     # rate limit
                time.sleep(2 + attempt * 2)
                continue
            raise RuntimeError(f"{path} {params.get('symbol')}: {r.get('retCode')} {r.get('retMsg')}")
        except (requests.RequestException, ValueError) as e:
            if attempt == retries - 1:
                raise RuntimeError(f"{path} {params.get('symbol')}: {e}") from e
            time.sleep(1 + attempt * 2)
    raise RuntimeError(f"{path} {params.get('symbol')}: retries exhausted")


def fetch_instruments():
    """Every linear USDT perpetual, trading and delisted, minus TradFi and pegged tokens."""
    out = []
    for status in ("Trading", "Closed"):
        cursor = None
        while True:
            p = {"category": "linear", "limit": 1000, "status": status}
            if cursor:
                p["cursor"] = cursor
            res = _get("/v5/market/instruments-info", p)
            for x in res.get("list", []) or []:
                if x.get("quoteCoin") != "USDT" or x.get("contractType") != "LinearPerpetual":
                    continue
                if x.get("symbolType") in config.SCAN_EXCLUDE_SYMBOL_TYPES or x["symbol"] in config.SCAN_EXCLUDE_SYMBOLS:
                    continue
                out.append({"symbol": x["symbol"], "status": status, "launchTime": int(x.get("launchTime") or 0)})
            cursor = res.get("nextPageCursor")
            if not cursor or not res.get("list"):
                break
    seen, uniq = set(), []
    for x in out:
        if x["symbol"] not in seen:
            seen.add(x["symbol"])
            uniq.append(x)
    return uniq


def fetch_daily(symbol, launch_ms, now_ms):
    """Closed daily bars from listing (or 2020-01-01) to yesterday, paged forward in windows
    — the only request shape Bybit answers for delisted symbols."""
    start = max(launch_ms - launch_ms % DAY_MS, EARLIEST_MS)
    by_ts = {}
    cursor = start
    while cursor < now_ms:
        end = min(cursor + KLINE_PAGE_DAYS * DAY_MS - 1, now_ms)
        res = _get("/v5/market/kline", {"category": "linear", "symbol": symbol, "interval": "D",
                                        "start": cursor, "end": end, "limit": 1000})
        for r in res.get("list", []) or []:
            t = int(r[0])
            if t + DAY_MS <= now_ms:                         # closed days only
                by_ts[t] = [t] + [float(x) for x in r[1:7]]
        cursor = end + 1
    return [by_ts[t] for t in sorted(by_ts)]


def fetch_funding(symbol, start_ms, end_ms):
    rows, cursor_end = {}, end_ms
    for _ in range(FUNDING_MAX_PAGES):
        res = _get("/v5/market/funding/history", {"category": "linear", "symbol": symbol,
                                                  "startTime": start_ms, "endTime": cursor_end, "limit": FUNDING_PAGE})
        lst = res.get("list", []) or []
        if not lst:
            break
        for it in lst:
            rows[int(it["fundingRateTimestamp"])] = float(it["fundingRate"])
        oldest = min(int(it["fundingRateTimestamp"]) for it in lst)
        if oldest <= start_ms or len(lst) < FUNDING_PAGE:
            break
        cursor_end = oldest - 1
    return [[t, rows[t]] for t in sorted(rows)]


def fetch_symbol(inst, now_ms):
    s = inst["symbol"]
    kp, fp = CACHE / f"{s}_D.json", CACHE / f"{s}_funding.json"
    if kp.exists() and fp.exists():
        return s, "cached"
    daily = fetch_daily(s, inst["launchTime"], now_ms)
    if not daily:
        kp.write_text("[]")
        fp.write_text("[]")
        return s, "no bars"
    funding = fetch_funding(s, daily[0][0], daily[-1][0] + 2 * DAY_MS)
    fp.write_text(json.dumps(funding, separators=(",", ":")))
    kp.write_text(json.dumps(daily, separators=(",", ":")))     # written last: its presence = complete
    return s, f"{len(daily)} days, {len(funding)} settlements"


def cmd_fetch(args):
    CACHE.mkdir(parents=True, exist_ok=True)
    now = int(time.time() * 1000)
    now_ms = now - now % DAY_MS                                  # today's open = end of the last closed day
    ip = CACHE / "instruments.json"
    if ip.exists() and not args.refresh_instruments:
        insts = json.loads(ip.read_text())["instruments"]
    else:
        insts = fetch_instruments()
        ip.write_text(json.dumps({"fetched_utc": datetime.now(timezone.utc).isoformat(), "end_ms": now_ms,
                                  "instruments": insts}, indent=1))
    end_ms = json.loads(ip.read_text()).get("end_ms", now_ms)
    print(f"{len(insts)} symbols ({sum(x['status'] == 'Closed' for x in insts)} delisted); end {end_ms}")
    t0, done, failed = time.time(), 0, []
    with ThreadPoolExecutor(THREADS) as ex:
        futs = {ex.submit(fetch_symbol, x, end_ms): x["symbol"] for x in insts}
        for f in as_completed(futs):
            done += 1
            try:
                s, msg = f.result()
            except Exception as e:                                # noqa: BLE001 — record and continue
                failed.append(futs[f])
                msg, s = f"FAILED {e}", futs[f]
            if done % 50 == 0 or msg.startswith("FAILED"):
                print(f"  [{done}/{len(insts)}] {s}: {msg} ({time.time() - t0:.0f}s)", flush=True)
    print(f"Done in {time.time() - t0:.0f}s; failed {len(failed)}: {failed[:20]}")


OI_PAGE_DAYS = 200


def fetch_oi(symbol, start_ms, end_ms):
    """Daily open interest (base units, both sides) over [start, end], paged forward in windows."""
    rows, cursor = {}, start_ms
    while cursor <= end_ms:
        end = min(cursor + OI_PAGE_DAYS * DAY_MS - 1, end_ms)
        res = _get("/v5/market/open-interest", {"category": "linear", "symbol": symbol, "intervalTime": "1d",
                                                "startTime": cursor, "endTime": end, "limit": OI_PAGE_DAYS})
        for it in res.get("list", []) or []:
            rows[int(it["timestamp"])] = float(it["openInterest"])
        cursor = end + 1
    return [[t, rows[t]] for t in sorted(rows)]


def cmd_fetch_oi(args):
    """Open-interest history for every cached symbol (`<SYM>_oi.json`), resumable."""
    insts = json.loads((CACHE / "instruments.json").read_text())["instruments"]
    t0, failed = time.time(), []

    def one(x):
        s = x["symbol"]
        op = CACHE / f"{s}_oi.json"
        if op.exists():
            return s, "cached"
        daily = json.loads((CACHE / f"{s}_D.json").read_text())
        rows = fetch_oi(s, daily[0][0], daily[-1][0] + DAY_MS) if daily else []
        op.write_text(json.dumps(rows, separators=(",", ":")))
        return s, f"{len(rows)} days"

    with ThreadPoolExecutor(THREADS) as ex:
        futs = {ex.submit(one, x): x["symbol"] for x in insts}
        for i, f in enumerate(as_completed(futs), 1):
            try:
                s, msg = f.result()
            except Exception as e:                                # noqa: BLE001 — record and continue
                failed.append(futs[f])
                s, msg = futs[f], f"FAILED {e}"
            if i % 100 == 0 or msg.startswith("FAILED"):
                print(f"  [{i}/{len(insts)}] {s}: {msg} ({time.time() - t0:.0f}s)", flush=True)
    print(f"Done in {time.time() - t0:.0f}s; failed {len(failed)}: {failed[:20]}")


def cmd_status(args):
    insts = json.loads((CACHE / "instruments.json").read_text())["instruments"]
    have = [x for x in insts if (CACHE / f"{x['symbol']}_D.json").exists()]
    print(f"{len(have)}/{len(insts)} cached")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("--refresh-instruments", action="store_true")
    f.set_defaults(fn=cmd_fetch)
    sub.add_parser("fetch-oi").set_defaults(fn=cmd_fetch_oi)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
