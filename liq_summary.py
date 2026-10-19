"""Hourly liquidation summary for the brief's market-context section (2026-10-19).

`liquidation_collector.py` runs inside the scan keeper and appends raw Bybit liquidation prints
to logs/liquidations/liq_YYYY-MM.jsonl (gitignored, one runner's lifetime). Before each scan the
keeper calls `python liq_summary.py --source <run_id> --since <ms>`, which folds that runner's
prints into a small COMMITTED file (config.LIQ_SUMMARY_PATH) so every later scan — and the next
keeper job — can read the last 24h:

    {"updated": iso, "sources": {"<run_id>": {"since": ms, "until": ms,
                                              "hours": {"<hour_ms>": {"BTCUSDT": [long_usd, short_usd]}}}}}

Each source is rebuilt from its own raw prints on every call (idempotent) and other sources are
kept, so a 24h window spans keeper hand-overs. `since`/`until` mark when the collector was alive,
which is how the brief reports coverage honestly.

Side: Bybit's allLiquidation `S` is the POSITION side — "Buy" = a LONG was liquidated. Verified
on our own data 2026-10-19: in BTC hours that fell > 1%, 96% of liquidated notional was "Buy";
in hours that rose > 1%, 99% was "Sell". (liq_fade_backtest.py / liq_cluster_backtest.py assumed
the opposite — see progress.md.)

Zero trading decisions, no order API.
"""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import config

HOUR_MS = 3_600_000
RAW_DIR = Path(__file__).parent / "logs" / "liquidations"


def summary_path():
    return Path(__file__).parent / getattr(config, "LIQ_SUMMARY_PATH", "logs/market/liq_hourly.json")


def load_summary(path=None):
    try:
        return json.loads(Path(path or summary_path()).read_text(encoding="utf-8"))
    except Exception:
        return {"sources": {}}


def aggregate(lines, since_ms=0):
    """Raw print lines (JSON strings or dicts) → {hour_ms: {symbol: [long_usd, short_usd]}}."""
    hours = {}
    for line in lines:
        try:
            r = json.loads(line) if isinstance(line, str) else line
            t = int(r["t"])
            if t < since_ms:
                continue
            notional = float(r.get("notional") or 0.0)
            side = r.get("side")
            sym = r.get("sym")
        except Exception:
            continue
        if not sym or notional <= 0 or side not in ("Buy", "Sell"):
            continue
        cell = hours.setdefault(str(t // HOUR_MS * HOUR_MS), {}).setdefault(sym, [0.0, 0.0])
        cell[0 if side == "Buy" else 1] += notional        # Buy = long liquidated
    return {h: {s: [round(v[0], 2), round(v[1], 2)] for s, v in syms.items()} for h, syms in hours.items()}


def merge(summary, source, since_ms, until_ms, hours, keep_hours):
    """Replace `source`'s entry, prune everything older than keep_hours. Returns the summary."""
    sources = dict(summary.get("sources") or {})
    sources[str(source)] = {"since": int(since_ms), "until": int(until_ms), "hours": hours}
    cutoff = until_ms - keep_hours * HOUR_MS
    kept = {}
    for sid, s in sources.items():
        h = {k: v for k, v in (s.get("hours") or {}).items() if int(k) + HOUR_MS > cutoff}
        if int(s.get("until", 0)) > cutoff:
            kept[sid] = dict(s, since=max(int(s.get("since", 0)), cutoff), hours=h)
    return {"updated": datetime.fromtimestamp(until_ms / 1000, tz=timezone.utc).isoformat(), "sources": kept}


def window(summary, now_ms, hours=24):
    """Totals over the last `hours`: by symbol, all symbols, and how many of those hours a
    collector was alive (coverage). Long/short = liquidated LONG / SHORT notional (USD)."""
    lo = now_ms - hours * HOUR_MS
    by_sym, total = {}, [0.0, 0.0]
    alive = set()
    for s in (summary.get("sources") or {}).values():
        a, b = max(int(s.get("since", 0)), lo), min(int(s.get("until", 0)), now_ms)
        h = a // HOUR_MS * HOUR_MS
        while h < b:
            alive.add(h)
            h += HOUR_MS
        for k, syms in (s.get("hours") or {}).items():
            if not (lo - HOUR_MS < int(k) <= now_ms):
                continue
            for sym, (lg, sh) in syms.items():
                cell = by_sym.setdefault(sym, [0.0, 0.0])
                cell[0] += lg
                cell[1] += sh
                total[0] += lg
                total[1] += sh
    return {"hours": hours, "covered_hours": min(len(alive), hours), "by_symbol": by_sym, "total": total}


def _raw_lines(raw_dir):
    for f in sorted(Path(raw_dir).glob("liq_*.jsonl")):
        try:
            yield from f.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", required=True, help="collector identity, e.g. the keeper's GITHUB_RUN_ID")
    ap.add_argument("--since", type=int, required=True, help="collector start time, epoch ms")
    ap.add_argument("--raw-dir", default=str(RAW_DIR))
    args = ap.parse_args(argv)
    now_ms = int(time.time() * 1000)
    hours = aggregate(_raw_lines(args.raw_dir), since_ms=args.since)
    keep = int(getattr(config, "LIQ_SUMMARY_KEEP_HOURS", 48))
    out = merge(load_summary(), args.source, args.since, now_ms, hours, keep)
    p = summary_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    w = window(out, now_ms)
    print(f"liq summary: source {args.source}, {len(hours)} hours of prints; last 24h "
          f"longs ${w['total'][0] / 1e6:.1f}M / shorts ${w['total'][1] / 1e6:.1f}M, "
          f"{w['covered_hours']}/24 h covered")


if __name__ == "__main__":
    main()
