"""Engine parity check (2026-11-02): does unified_backtest score the trade the live evaluator scored?

For every v2-era evaluated live row (all rules, all lanes), find the engine's trade for the same
symbol, rule and signal bar, simulate it the engine's default way (`ub.sim_trade`), and compare
net R (managed trade, after costs) with the evaluator's number. Also compares the levels (stop,
T1, T2) in units of the live setup's risk, so a gap can be traced to levels or to timing.

Why: the 2026-11-02 failed_breakout_short check found the engine about +0.075R/trade more
optimistic than the evaluator on the same trades (entry at the 4h close instead of after the
scan; T1/T2 set from the fill instead of the setup's structural levels). This script is the
before/after measure for the fix and stays as a regression check.

Research only: changes no rule, gate or pick. No order API, no hosted model.

Usage:  python engine_parity.py [--skip-fetch]   → logs/backtest_reports/engine_parity_<date>.md
"""

import argparse
import json
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from pybit.unified_trading import HTTP

import unified_backtest as ub

BASE = Path(__file__).parent
EVALS = BASE / "logs" / "evaluations"
SETUPS = BASE / "logs" / "setups"
REPORTS = BASE / "logs" / "backtest_reports"

TF_MS = {"4h": 14_400_000, "1h": 3_600_000}
FETCH_DAYS = 125            # v2 era (from 2026-09-23) + indicator warm-up
PARITY_TOL_R = 0.05         # a pair "agrees" when |engine − live| ≤ this


def _floor(ms, step):
    return ms - ms % step


def load_live():
    """v2-era evaluated rows joined to their setup's levels."""
    setups = {}
    for f in SETUPS.glob("setups_*.json"):
        try:
            rec = json.loads(f.read_text())
        except Exception:
            continue
        setups[rec.get("run_tag")] = rec
    out = []
    for f in sorted(EVALS.glob("eval_*.json")):
        ev = json.loads(f.read_text())
        rec = setups.get(ev.get("run_tag")) or {}
        run_ms = int(datetime.fromisoformat(ev["run_timestamp_utc"]).timestamp() * 1000)
        for r in ev.get("results", []):
            if (r.get("eval_engine") != "v2_market_open" or r.get("status") != "evaluated"
                    or not r.get("signal_name")):
                continue
            s = next((x for x in rec.get("setups", []) if x.get("symbol") == r["symbol"]
                      and x.get("source", "claude") == r.get("source", "claude")), None)
            tf = (s or {}).get("signal_tf")           # eval rows do not carry the signal TF
            if not s or s.get("target_2") is None or tf not in TF_MS:
                continue
            out.append({
                "symbol": r["symbol"], "signal": r["signal_name"], "tf": tf,
                "direction": r["direction"], "bar_ms": _floor(run_ms, TF_MS[tf]), "run_ms": run_ms,
                "net": float(r["net_blended_rr"]),
                "stop": float(s["stop_loss"]), "t1": float(s["target_1"]), "t2": float(s["target_2"]),
                "ref": (float(s["entry_low"]) + float(s["entry_high"])) / 2,
            })
    return out


def engine_levels(t):
    """(stop, t1, t2) the engine simulates by default. Older engine trades carry no fixed T1/T2:
    they were set from the fill at 0.75R and target_r."""
    if t.get("t1") is not None:
        return t["stop"], t["t1"], t["t2"]
    e, s = t["entry"], t["stop"]
    d = abs(e - s)
    sign = 1 if t["direction"] == "long" else -1
    return s, e + sign * ub.DEFAULT_T1_R * d, e + sign * t["target_r"] * d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-fetch", action="store_true")
    ap.add_argument("--tag", default="", help="suffix for the report file (e.g. before / after)")
    args = ap.parse_args()

    live = load_live()
    syms = sorted({r["symbol"] for r in live})
    rules = {r["signal"] for r in live}
    tfs = {r["tf"] for r in live}
    client = HTTP(testnet=False, timeout=20)
    ub.DEDUP_DAYS = 0          # keep every fire; matching is by bar
    fired, missing = {}, []
    for sym in syms:
        d = {iv: ub.fetch_closed_klines(client, sym, iv, FETCH_DAYS, skip_fetch=args.skip_fetch)
             for iv in ("240", "60", "D", "15")}
        if len(d["240"]) < 70 or len(d["15"]) < 500:
            missing.append(sym)
            continue
        for t in ub.build_trades(sym, d, None, rules, tfs):
            fired[(sym, t["signal"], t["signal_ms"])] = t

    pairs, why = [], defaultdict(int)
    for r in live:
        if r["symbol"] in missing:
            why["no data"] += 1
            continue
        t = fired.get((r["symbol"], r["signal"], r["bar_ms"]))
        if not t:
            why["engine has no trade on this bar"] += 1
            continue
        res = ub.sim_trade(t)
        if not res:
            why["engine: limit not filled"] += 1
            continue
        pairs.append((r, res["net_blended_rr"], t))

    def lvl_gap(r, t):
        risk = abs(r["ref"] - r["stop"]) or 1e-12
        s, a, b = engine_levels(t)
        return abs(s - r["stop"]) / risk, abs(a - r["t1"]) / risk, abs(b - r["t2"]) / risk

    L = [f"# Engine parity — {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC {args.tag}".rstrip(), "",
         f"Live rows: {len(live)} v2 evaluated with levels · rules {', '.join(sorted(rules))} · "
         f"engine entry model {ub.ENTRY_MODEL}, scan lag {getattr(ub, 'SCAN_LAG_MS', 0) // 60000} min.", ""]
    if pairs:
        gaps = [bt - r["net"] for r, bt, _ in pairs]
        agree = sum(1 for g in gaps if abs(g) <= PARITY_TOL_R) / len(pairs)
        lg = [lvl_gap(r, t) for r, _, t in pairs]
        L += [f"- Matched {len(pairs)}/{len(live)} · agree within {PARITY_TOL_R}R: **{100 * agree:.0f}%**",
              f"- Mean net: live {statistics.mean(r['net'] for r, _, _ in pairs):+.3f}R · engine "
              f"{statistics.mean(bt for _, bt, _ in pairs):+.3f}R · **gap (engine − live) "
              f"{statistics.mean(gaps):+.3f}R/trade** (median {statistics.median(gaps):+.3f})",
              f"- Level gap, median in live-risk units: stop {statistics.median(x[0] for x in lg):.3f} · "
              f"T1 {statistics.median(x[1] for x in lg):.3f} · T2 {statistics.median(x[2] for x in lg):.3f}",
              "", "| rule | tf | n | live | engine | gap | agree |", "|---|---|---:|---:|---:|---:|---:|"]
        by = defaultdict(list)
        for r, bt, _ in pairs:
            by[(r["signal"], r["tf"])].append((r["net"], bt))
        for (sig, tf), v in sorted(by.items()):
            lv, ev = [a for a, _ in v], [b for _, b in v]
            ag = sum(1 for a, b in v if abs(b - a) <= PARITY_TOL_R) / len(v)
            L.append(f"| {sig} | {tf} | {len(v)} | {statistics.mean(lv):+.3f} | {statistics.mean(ev):+.3f} | "
                     f"{statistics.mean(ev) - statistics.mean(lv):+.3f} | {100 * ag:.0f}% |")
    L += ["", "Unmatched: " + (", ".join(f"{k} {v}" for k, v in sorted(why.items())) or "none")]
    out = REPORTS / f"engine_parity_{datetime.now(timezone.utc):%Y%m%d}{'_' + args.tag if args.tag else ''}.md"
    out.write_text("\n".join(L) + "\n")
    print("\n".join(L))
    print(f"\n→ {out}")


if __name__ == "__main__":
    main()
