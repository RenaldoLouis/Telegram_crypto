#!/usr/bin/env python
"""options_collector.py — forward collector for BTC / ETH options skew and put/call flow (Deribit).

Why: options skew (puts priced above calls = traders paying for crash protection) and put/call flow are the
last options-market inputs on the new-input ledger, and their HISTORY is not on Deribit's free API (DVOL is,
and was closed 2026-11-17). So we record them forward, like the liquidation feed, and test them once weeks
of data exist. DATA COLLECTOR ONLY — no trade decision, no order API, no hosted model.

One public call per currency (`get_book_summary_by_currency`, kind=option) gives every listed option's
mark IV, underlying (the expiry's futures price), 24h volume and open interest. Deltas are computed here
(Black-76, r = 0, expiry 08:00 UTC) because the summary carries none.

Per snapshot and currency, one row:
  t_ms, currency, index (mean underlying of the nearest expiry),
  expiries: [[expiry_ms, days, fwd, atm_iv, put25_iv, call25_iv], ...]  (expiries 1.5 → 200 days)
  iv30_atm, rr25_30 (call25 − put25, 30-day, total-variance interpolation between the bracketing expiries),
  bf25_30 ((call25 + put25)/2 − atm), pc_vol (put / call 24h volume, all expiries), pc_oi (put / call OI)

    python options_collector.py snapshot --out /tmp/options_raw.jsonl     # one snapshot (BTC, ETH)
    python options_collector.py loop --out /tmp/options_raw.jsonl --every 900 --until <epoch s>
    python options_collector.py fold --raw /tmp/options_raw.jsonl          # → logs/market/options/<CUR>_<YYYY-MM>.jsonl
    python options_collector.py status

The scan keeper runs `loop` in the background and `fold` before every commit, so snapshots are committed
with logs/market and nothing is written to the repo while git is rebasing.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE = Path(__file__).resolve().parent
OUT_DIR = BASE / "logs/market/options"
URL = "https://www.deribit.com/api/v2/public/get_book_summary_by_currency"
CURRENCIES = ("BTC", "ETH")
DAY_MS = 86_400_000
YEAR_DAYS = 365.0
MIN_DAYS, MAX_DAYS, TARGET_DAYS = 1.5, 200.0, 30.0
MONTHS = {m: i + 1 for i, m in enumerate(("JAN", "FEB", "MAR", "APR", "MAY", "JUN",
                                         "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"))}


# ----------------------------------------------------------------------------- maths
def _ncdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def delta(fwd: float, strike: float, iv_pct: float, years: float, is_call: bool) -> float | None:
    """Black-76 forward delta (r = 0). None when undefined."""
    sig = iv_pct / 100.0
    if fwd <= 0 or strike <= 0 or sig <= 0 or years <= 0:
        return None
    d1 = (math.log(fwd / strike) + 0.5 * sig * sig * years) / (sig * math.sqrt(years))
    return _ncdf(d1) if is_call else _ncdf(d1) - 1.0


def expiry_ms(code: str) -> int:
    """'27NOV26' → 08:00 UTC that day (Deribit's expiry time)."""
    day, mon, yr = int(code[:-5]), MONTHS[code[-5:-2]], 2000 + int(code[-2:])
    return int(datetime(yr, mon, day, 8, tzinfo=timezone.utc).timestamp() * 1000)


def _interp(points, x):
    """Linear interpolation of y at x over sorted (x, y) points; None outside their range."""
    pts = sorted(points)
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            return y0 if x1 == x0 else y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return None


def smile_point(options, fwd, years, target_delta, is_call):
    """IV at |delta| = target among OTM options of one side, by linear interpolation in delta."""
    pts = []
    for o in options:
        if o["is_call"] != is_call or o["iv"] <= 0:
            continue
        if (is_call and o["strike"] < fwd) or ((not is_call) and o["strike"] > fwd):
            continue                                            # OTM only
        d = delta(fwd, o["strike"], o["iv"], years, is_call)
        if d is not None:
            pts.append((abs(d), o["iv"]))
    return _interp(pts, target_delta)


def atm_iv(options, fwd):
    """IV at the forward: interpolate across strikes using OTM calls above and OTM puts below."""
    pts = [(o["strike"], o["iv"]) for o in options if o["iv"] > 0 and
           ((o["is_call"] and o["strike"] >= fwd) or ((not o["is_call"]) and o["strike"] <= fwd))]
    return _interp(pts, fwd)


def summarise(summary: list[dict], currency: str, now_ms: int) -> dict | None:
    """One snapshot row from Deribit's option book summary."""
    by_exp, pv, cv, po, co = {}, 0.0, 0.0, 0.0, 0.0
    for s in summary:
        try:
            _, code, strike, cp = s["instrument_name"].split("-")
            o = {"strike": float(strike), "iv": float(s.get("mark_iv") or 0), "is_call": cp == "C",
                 "fwd": float(s.get("underlying_price") or 0)}
        except (ValueError, KeyError):
            continue
        vol, oi = float(s.get("volume") or 0), float(s.get("open_interest") or 0)
        if o["is_call"]:
            cv, co = cv + vol, co + oi
        else:
            pv, po = pv + vol, po + oi
        by_exp.setdefault(code, []).append(o)
    expiries = []
    for code, opts in by_exp.items():
        e_ms = expiry_ms(code)
        days = (e_ms - now_ms) / DAY_MS
        if not (MIN_DAYS <= days <= MAX_DAYS):
            continue
        fwds = [o["fwd"] for o in opts if o["fwd"] > 0]
        if not fwds:
            continue
        fwd, years = sum(fwds) / len(fwds), days / YEAR_DAYS
        a = atm_iv(opts, fwd)
        p25 = smile_point(opts, fwd, years, 0.25, False)
        c25 = smile_point(opts, fwd, years, 0.25, True)
        expiries.append([e_ms, round(days, 3), round(fwd, 2), _r(a), _r(p25), _r(c25)])
    if not expiries:
        return None
    expiries.sort()

    def at30(col):
        """Total-variance interpolation (iv² × t) at 30 days between the bracketing expiries."""
        pts = [(e[1], (e[col] / 100) ** 2 * e[1]) for e in expiries if e[col] is not None]
        v = _interp(pts, TARGET_DAYS)
        return None if v is None or v <= 0 else round(100 * math.sqrt(v / TARGET_DAYS), 3)

    a30, p30, c30 = at30(3), at30(4), at30(5)
    return {"t_ms": now_ms, "currency": currency, "index": expiries[0][2], "expiries": expiries,
            "iv30_atm": a30,
            "rr25_30": None if (p30 is None or c30 is None) else round(c30 - p30, 3),
            "bf25_30": None if (p30 is None or c30 is None or a30 is None) else round((c30 + p30) / 2 - a30, 3),
            "pc_vol": round(pv / cv, 4) if cv > 0 else None,
            "pc_oi": round(po / co, 4) if co > 0 else None}


def _r(x):
    return None if x is None else round(x, 3)


# ----------------------------------------------------------------------------- io
def snapshot(out: Path, get=requests.get, now_ms=None, log=print) -> int:
    """Append one row per currency to `out`. Returns rows written; a failed currency is logged, not raised."""
    now_ms = now_ms or int(time.time() * 1000)
    n = 0
    for cur in CURRENCIES:
        try:
            resp = get(URL, params={"currency": cur, "kind": "option"}, timeout=20).json()
            row = summarise(resp["result"], cur, now_ms)
        except Exception as exc:  # network / API change: keep collecting the other currency
            log(f"options {cur}: snapshot failed: {exc}")
            continue
        if row:
            out.parent.mkdir(parents=True, exist_ok=True)
            with out.open("a") as f:
                f.write(json.dumps(row, separators=(",", ":")) + "\n")
            n += 1
    return n


def fold(raw: Path, out_dir: Path = OUT_DIR) -> int:
    """Merge raw rows into logs/market/options/<CUR>_<YYYY-MM>.jsonl, deduplicated on (currency, t_ms)."""
    if not raw.exists():
        return 0
    new = {}
    for line in raw.read_text().splitlines():
        try:
            r = json.loads(line)
            new[(r["currency"], r["t_ms"])] = r
        except (json.JSONDecodeError, KeyError):
            continue                                          # a half-written last line → next fold
    by_file = {}
    for (cur, t), r in new.items():
        ym = datetime.fromtimestamp(t / 1000, tz=timezone.utc).strftime("%Y-%m")
        by_file.setdefault(out_dir / f"{cur}_{ym}.jsonl", []).append(r)
    added = 0
    for p, rows in by_file.items():
        have = set()
        if p.exists():
            have = {json.loads(l)["t_ms"] for l in p.read_text().splitlines() if l.strip()}
        rows = sorted((r for r in rows if r["t_ms"] not in have), key=lambda r: r["t_ms"])
        if rows:
            p.parent.mkdir(parents=True, exist_ok=True)
            with p.open("a") as f:
                for r in rows:
                    f.write(json.dumps(r, separators=(",", ":")) + "\n")
            added += len(rows)
    return added


def status(out_dir: Path = OUT_DIR):
    files = sorted(out_dir.glob("*.jsonl")) if out_dir.exists() else []
    if not files:
        print("no options snapshots yet")
    for p in files:
        rows = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
        last = rows[-1]
        print(f"{p.name}: {len(rows)} snapshots, last {datetime.fromtimestamp(last['t_ms'] / 1000, timezone.utc):%m-%d %H:%M} "
              f"iv30 {last['iv30_atm']} rr25 {last['rr25_30']} pc_vol {last['pc_vol']}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("snapshot", "loop", "fold", "status"))
    ap.add_argument("--out", default="/tmp/options_raw.jsonl")
    ap.add_argument("--raw", default="/tmp/options_raw.jsonl")
    ap.add_argument("--every", type=int, default=900)
    ap.add_argument("--until", type=int, default=0, help="epoch seconds; 0 = forever")
    a = ap.parse_args(argv)
    if a.cmd == "snapshot":
        print(f"wrote {snapshot(Path(a.out))} row(s)")
    elif a.cmd == "loop":
        while not a.until or time.time() < a.until:
            snapshot(Path(a.out), log=lambda m: print(m, file=sys.stderr, flush=True))
            time.sleep(a.every)
    elif a.cmd == "fold":
        print(f"options fold: {fold(Path(a.raw))} new row(s)")
    else:
        status()


if __name__ == "__main__":
    main()
