#!/usr/bin/env python
"""
backtester.py — What-if backtester for crypto-screener.
Reads eval + setup logs, runs parameter sweep analyses. Zero Claude tokens.

Usage:
  python backtester.py                  # Full report (all analyses)
  python backtester.py --baseline       # Just baseline stats
  python backtester.py --t1-sweep       # T1 distance analysis
  python backtester.py --symbols        # Per-symbol report
  python backtester.py --rank-sweep     # Rank cutoff analysis
  python backtester.py --regime-sweep   # Regime limit variations
  python backtester.py --combo          # Auto-discover best filter combos
  python backtester.py --filter direction=short         # Custom filter
  python backtester.py --filter tf_confluence=4         # Repeatable
  python backtester.py --exclude ETHUSDT,BTCUSDT        # Blacklist symbols
  python backtester.py --min-confluence 3               # Minimum TF confluence
"""

import json
import os
import sys
import argparse
from collections import defaultdict
from pathlib import Path

import config  # for LONG_MIN_CONFLUENCE (v11.3 gate-compliance audit)

BASE_DIR = Path(__file__).parent
EVAL_DIR = BASE_DIR / "logs" / "evaluations"
SETUP_DIR = BASE_DIR / "logs" / "setups"
VERSION_MARKERS = BASE_DIR / "logs" / "performance" / "version_markers.json"


# ─── Data Loading ────────────────────────────────────────────────────────────

def load_all_evals():
    """Load all eval files, flatten to list of evaluated trade records."""
    trades = []
    for fp in sorted(EVAL_DIR.glob("eval_*.json")):
        with open(fp) as f:
            data = json.load(f)
        run_tag = data.get("run_tag", "")
        model = data.get("model", "unknown")
        regime = data.get("regime", "")
        for r in data.get("results", []):
            if r.get("status") != "evaluated" or not r.get("entry_triggered"):
                continue
            r["run_tag"] = run_tag
            r["_model"] = model
            r["_file_regime"] = regime
            trades.append(r)
    return trades


def load_setup_lookup():
    """Build lookup: (run_tag, symbol) → extra setup fields."""
    lookup = {}
    for fp in sorted(SETUP_DIR.glob("setups_*.json")):
        with open(fp) as f:
            data = json.load(f)
        run_tag = data.get("run_tag", "")
        regime = data.get("regime", "")
        for s in data.get("setups", []):
            key = (run_tag, s.get("symbol", ""))
            lookup[key] = {
                "volume_confirmed": s.get("volume_confirmed", False),
                "setup_regime": regime,
                "target_1": s.get("target_1"),
                "target_2": s.get("target_2"),
                "stop_loss": s.get("stop_loss"),
                "entry_low": s.get("entry_low"),
                "entry_high": s.get("entry_high"),
            }
    return lookup


def merge_trades(trades, setup_lookup):
    """Enrich eval trades with setup data."""
    for t in trades:
        key = (t.get("run_tag", ""), t.get("symbol", ""))
        setup = setup_lookup.get(key, {})
        t["volume_confirmed"] = setup.get("volume_confirmed", False)
        t["regime"] = setup.get("setup_regime") or t.get("_file_regime") or "unknown"
        t["orig_target_1"] = setup.get("target_1")
        t["orig_target_2"] = setup.get("target_2")
        t["orig_stop_loss"] = setup.get("stop_loss")
    return trades


# ─── Stats Computation ───────────────────────────────────────────────────────

def compute_stats(trades):
    """Compute aggregate stats for a list of trades."""
    if not trades:
        return {
            "n": 0, "wins": 0, "losses": 0, "wr": 0.0,
            "avg_rr": 0.0, "rr_sum": 0.0,
            "avg_blended": 0.0, "blended_sum": 0.0,
            "t1_hits": 0, "t1_rate": 0.0,
            "avg_mfe": 0.0, "expectancy": 0.0, "profit_factor": 0.0,
        }

    n = len(trades)
    wins = sum(1 for t in trades if t.get("won"))
    rr_sum = sum(t.get("actual_rr", 0) for t in trades)
    blended_sum = sum(t.get("blended_rr", 0) for t in trades)
    t1_hits = sum(1 for t in trades if t.get("target_1_hit"))
    mfe_sum = sum(t.get("max_favorable_rr", 0) for t in trades)

    # Expectancy = avg_win * WR - avg_loss * (1-WR)
    winning = [t.get("actual_rr", 0) for t in trades if t.get("won")]
    losing = [abs(t.get("actual_rr", 0)) for t in trades if not t.get("won")]
    avg_win = sum(winning) / len(winning) if winning else 0
    avg_loss = sum(losing) / len(losing) if losing else 0
    wr = wins / n if n else 0
    expectancy = avg_win * wr - avg_loss * (1 - wr)

    gross_profit = sum(winning)
    gross_loss = sum(losing)
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

    return {
        "n": n,
        "wins": wins,
        "losses": n - wins,
        "wr": round(wr * 100, 1),
        "avg_rr": round(rr_sum / n, 3),
        "rr_sum": round(rr_sum, 2),
        "avg_blended": round(blended_sum / n, 3),
        "blended_sum": round(blended_sum, 2),
        "t1_hits": t1_hits,
        "t1_rate": round(t1_hits / n * 100, 1),
        "avg_mfe": round(mfe_sum / n, 3),
        "expectancy": round(expectancy, 3),
        "profit_factor": round(profit_factor, 2),
    }


# ─── Display Helpers ─────────────────────────────────────────────────────────

HEADER_FMT = "  {:<22s} {:>6s} {:>7s} {:>8s} {:>9s} {:>7s} {:>8s} {:>7s}"
ROW_FMT    = "  {:<22s} {:>6d} {:>6.1f}% {:>8.3f} {:>9.3f} {:>6.1f}% {:>8.3f} {:>7.2f}"

def print_header():
    print(HEADER_FMT.format("", "Trades", "WR", "Avg R:R", "Avg Blend", "T1 Hit", "Expect", "PF"))
    print("  " + "─" * 80)

def print_row(label, s):
    if s["n"] == 0:
        print(f"  {label:<22s} {'(no data)':>6s}")
        return
    print(ROW_FMT.format(
        label, s["n"], s["wr"], s["avg_rr"], s["avg_blended"],
        s["t1_rate"], s["expectancy"], s["profit_factor"]
    ))

def section(title):
    print(f"\n{'=' * 84}")
    print(f"  {title}")
    print(f"{'=' * 84}")


# ─── Analysis: Baseline ─────────────────────────────────────────────────────

def report_baseline(trades):
    section("BASELINE")
    s = compute_stats(trades)
    print(f"  Evaluated trades:  {s['n']}")
    print(f"  Win rate:          {s['wr']}% ({s['wins']}W / {s['losses']}L)")
    print(f"  Avg actual R:R:    {s['avg_rr']}")
    print(f"  Avg blended R:R:   {s['avg_blended']}")
    print(f"  T1 hit rate:       {s['t1_rate']}% ({s['t1_hits']}/{s['n']})")
    print(f"  Avg MFE:           {s['avg_mfe']}R")
    print(f"  Expectancy:        {s['expectancy']}R per trade")
    print(f"  Profit factor:     {s['profit_factor']}")
    print(f"  Sum actual R:R:    {s['rr_sum']}R")
    print(f"  Sum blended R:R:   {s['blended_sum']}R")

    # MFE direction accuracy
    right_dir = sum(1 for t in trades if t.get("max_favorable_rr", 0) >= 0.5)
    print(f"\n  Direction accuracy (MFE >= 0.5R):  {right_dir}/{s['n']} "
          f"({round(right_dir/s['n']*100, 1)}%)")
    right_1r = sum(1 for t in trades if t.get("max_favorable_rr", 0) >= 1.0)
    print(f"  Reached 1.0R+ before exit:         {right_1r}/{s['n']} "
          f"({round(right_1r/s['n']*100, 1)}%)")


# ─── Analysis: By Dimension ─────────────────────────────────────────────────

def report_by_dimension(trades, dim, label=None):
    label = label or dim
    section(f"BY {label.upper()}")
    print_header()
    groups = defaultdict(list)
    for t in trades:
        val = t.get(dim, "unknown")
        if isinstance(val, bool):
            val = "yes" if val else "no"
        groups[str(val)].append(t)

    baseline_wr = compute_stats(trades)["wr"]
    rows = []
    for val in sorted(groups.keys(), key=lambda v: -len(groups[v])):
        s = compute_stats(groups[val])
        delta = s["wr"] - baseline_wr
        tag = ""
        if s["n"] >= 5:
            if delta > 5:
                tag = " ▲"
            elif delta < -5:
                tag = " ▼"
        rows.append((val, s, delta, tag))

    for val, s, delta, tag in rows:
        lbl = f"{val}{tag}"
        print_row(lbl, s)


# ─── Analysis: T1 Sweep ─────────────────────────────────────────────────────

def sim_blended_for_t1(trades, t1_r):
    """Simulate blended R:R if T1 was at t1_r instead of original."""
    field = f"sim_t1_{'075' if t1_r == 0.75 else '100'}r_hit"
    results = []
    saves = 0
    for t in trades:
        sim_hit = t.get(field, False)
        original_stop = t.get("stop_hit", False)
        original_blended = t.get("blended_rr", 0)

        if sim_hit and original_stop:
            # THE SAVE: tighter T1 captures partial profit before stop
            # 50% closes at t1_r, stop moves to BE, trailing 50% exits at BE = 0R
            sim_br = 0.5 * t1_r
            saves += 1
        elif sim_hit and not t.get("target_1_hit", False):
            # Tighter T1 hit but original T1 wasn't — partial capture
            # 50% at t1_r, trailing 50% conservatively BEs
            sim_br = 0.5 * t1_r
            saves += 1
        else:
            # Either sim T1 not hit (same outcome) or original T1 was also hit
            sim_br = original_blended

        results.append(sim_br)
    return results, saves


def report_t1_sweep(trades):
    section("T1 DISTANCE SWEEP")
    print("  Simulates: 'What if T1 was at X R instead of current targets?'")
    print("  Model: losses where sim_t1 hit → 50% closes at T1, trailing 50% BEs.\n")

    baseline = compute_stats(trades)
    print(f"  {'Scenario':<20s} {'Blended Sum':>12s} {'Avg Blend':>10s} {'Saves':>8s} {'Δ vs Now':>10s}")
    print("  " + "─" * 64)

    current_blend_sum = baseline["blended_sum"]
    print(f"  {'Current T1':<20s} {current_blend_sum:>12.2f}R {baseline['avg_blended']:>10.3f} {'—':>8s} {'—':>10s}")

    for t1_r, label in [(0.75, "T1 @ 0.75R"), (1.0, "T1 @ 1.0R")]:
        sim_blends, saves = sim_blended_for_t1(trades, t1_r)
        sim_sum = round(sum(sim_blends), 2)
        sim_avg = round(sim_sum / len(sim_blends), 3) if sim_blends else 0
        delta = round(sim_sum - current_blend_sum, 2)
        arrow = "▲" if delta > 0 else "▼" if delta < 0 else "="
        print(f"  {label:<20s} {sim_sum:>12.2f}R {sim_avg:>10.3f} {saves:>8d} {arrow} {delta:>+8.2f}R")

    # Show the saves breakdown
    print(f"\n  'Saves' = trades that were losses but sim T1 would have captured partial profit.")

    # Also show: how many trades reached 0.5R, 0.75R, 1.0R MFE
    mfe_05 = sum(1 for t in trades if t.get("max_favorable_rr", 0) >= 0.5)
    mfe_075 = sum(1 for t in trades if t.get("max_favorable_rr", 0) >= 0.75)
    mfe_10 = sum(1 for t in trades if t.get("max_favorable_rr", 0) >= 1.0)
    mfe_15 = sum(1 for t in trades if t.get("max_favorable_rr", 0) >= 1.5)
    n = len(trades)
    print(f"\n  MFE Distribution (how far price moved in your favor):")
    print(f"    >= 0.50R:  {mfe_05}/{n} ({round(mfe_05/n*100,1)}%)")
    print(f"    >= 0.75R:  {mfe_075}/{n} ({round(mfe_075/n*100,1)}%)")
    print(f"    >= 1.00R:  {mfe_10}/{n} ({round(mfe_10/n*100,1)}%)")
    print(f"    >= 1.50R:  {mfe_15}/{n} ({round(mfe_15/n*100,1)}%)")


# ─── Analysis: Rank Sweep ────────────────────────────────────────────────────

def report_rank_sweep(trades):
    section("RANK CUTOFF SWEEP")
    print("  'What if we only took the top N setups per run?'\n")

    baseline = compute_stats(trades)
    print(f"  {'Cutoff':<18s} {'Trades':>7s} {'WR':>7s} {'Avg R:R':>8s} {'Avg Blend':>10s} {'Expect':>8s} {'Δ Expect':>10s}")
    print("  " + "─" * 72)

    # Group by run_tag, sort by rank, take top N
    runs = defaultdict(list)
    for t in trades:
        runs[t.get("run_tag", "")].append(t)

    for max_rank in [1, 2, 3, 4, 5]:
        filtered = []
        for run_trades in runs.values():
            for t in sorted(run_trades, key=lambda x: x.get("rank", 99)):
                if t.get("rank", 99) <= max_rank:
                    filtered.append(t)
        s = compute_stats(filtered)
        delta_exp = round(s["expectancy"] - baseline["expectancy"], 3)
        arrow = "▲" if delta_exp > 0 else "▼" if delta_exp < 0 else "="
        label = f"Top {max_rank} only" if max_rank < 5 else "All (top 5)"
        print(f"  {label:<18s} {s['n']:>7d} {s['wr']:>6.1f}% {s['avg_rr']:>8.3f} {s['avg_blended']:>10.3f} {s['expectancy']:>8.3f} {arrow} {delta_exp:>+8.3f}")


# ─── Analysis: Regime Limit Sweep ────────────────────────────────────────────

def report_regime_sweep(trades):
    section("REGIME LIMIT SWEEP")
    print("  'What if we changed max setups per regime?'\n")

    runs = defaultdict(list)
    for t in trades:
        runs[t.get("run_tag", "")].append(t)

    # Current limits
    scenarios = [
        ("Current",    {"risk_off": 2, "cautious": 3, "neutral": 3, "risk_on": 5, "unknown": 3}),
        ("Tighter",    {"risk_off": 1, "cautious": 2, "neutral": 2, "risk_on": 4, "unknown": 2}),
        ("Very tight", {"risk_off": 1, "cautious": 1, "neutral": 2, "risk_on": 3, "unknown": 2}),
        ("Loose",      {"risk_off": 2, "cautious": 3, "neutral": 4, "risk_on": 5, "unknown": 4}),
        ("No risk_off", {"risk_off": 0, "cautious": 3, "neutral": 3, "risk_on": 5, "unknown": 3}),
    ]

    print(f"  {'Scenario':<16s} {'Limits':>30s} {'Trades':>7s} {'WR':>7s} {'Avg R:R':>8s} {'Expect':>8s}")
    print("  " + "─" * 80)

    for name, limits in scenarios:
        filtered = []
        for run_tag, run_trades in runs.items():
            # Determine regime for this run (from first trade's regime)
            regime = run_trades[0].get("regime", "unknown") if run_trades else "unknown"
            max_n = limits.get(regime, 3)
            for t in sorted(run_trades, key=lambda x: x.get("rank", 99))[:max_n]:
                filtered.append(t)
        s = compute_stats(filtered)
        limits_str = f"ro={limits['risk_off']} ca={limits['cautious']} ne={limits['neutral']} ri={limits['risk_on']}"
        print(f"  {name:<16s} {limits_str:>30s} {s['n']:>7d} {s['wr']:>6.1f}% {s['avg_rr']:>8.3f} {s['expectancy']:>8.3f}")


# ─── Analysis: Symbol Report ────────────────────────────────────────────────

def report_symbols(trades, min_trades=3):
    section(f"SYMBOL REPORT (min {min_trades} trades)")
    groups = defaultdict(list)
    for t in trades:
        groups[t.get("symbol", "?")].append(t)

    rows = []
    for sym, sym_trades in groups.items():
        s = compute_stats(sym_trades)
        if s["n"] >= min_trades:
            rows.append((sym, s))

    # Sort by expectancy
    rows.sort(key=lambda x: x[1]["expectancy"], reverse=True)

    print_header()
    for sym, s in rows:
        tag = " ★" if s["expectancy"] > 0 else " ✗" if s["n"] >= 5 and s["wr"] < 20 else ""
        print_row(f"{sym}{tag}", s)

    # Summary
    positive = [r for r in rows if r[1]["expectancy"] > 0]
    negative = [r for r in rows if r[1]["expectancy"] <= 0 and r[1]["n"] >= 5]
    if positive:
        print(f"\n  ★ Positive expectancy: {', '.join(r[0] for r in positive)}")
    if negative:
        print(f"  ✗ Negative expectancy (5+ trades): {', '.join(r[0] for r in negative)}")

    # What-if: blacklist worst symbols
    if negative:
        blacklist = {r[0] for r in negative if r[1]["wr"] < 25}
        if blacklist:
            filtered = [t for t in trades if t.get("symbol") not in blacklist]
            s_filtered = compute_stats(filtered)
            s_baseline = compute_stats(trades)
            print(f"\n  What-if: blacklist {blacklist}")
            print(f"    Trades: {s_baseline['n']} → {s_filtered['n']}")
            print(f"    WR:     {s_baseline['wr']}% → {s_filtered['wr']}%")
            print(f"    Expect: {s_baseline['expectancy']} → {s_filtered['expectancy']}")


# ─── Analysis: Combined Filters ─────────────────────────────────────────────

def report_combo(trades):
    section("COMBINED FILTER DISCOVERY")
    print("  Testing stacked filter combos for best expectancy.\n")

    baseline = compute_stats(trades)
    combos = []

    # Define filter functions
    filters = {
        "confluence>=3": lambda t: t.get("tf_confluence", 0) >= 3,
        "confluence>=4": lambda t: t.get("tf_confluence", 0) >= 4,
        "rank<=2": lambda t: t.get("rank", 99) <= 2,
        "rank<=3": lambda t: t.get("rank", 99) <= 3,
        "vol_confirmed": lambda t: t.get("volume_confirmed", False),
        "not_risk_off": lambda t: t.get("regime") != "risk_off",
        "not_cautious": lambda t: t.get("regime") not in ("risk_off", "cautious"),
        "direction=long": lambda t: t.get("direction") == "long",
        "direction=short": lambda t: t.get("direction") == "short",
        "conf=medium": lambda t: t.get("confidence") == "medium",
        "conf!=low": lambda t: t.get("confidence") != "low",
    }

    # Test individual filters
    for name, fn in filters.items():
        filtered = [t for t in trades if fn(t)]
        if len(filtered) >= 10:
            s = compute_stats(filtered)
            combos.append((name, s, filtered))

    # Test pairs
    filter_items = list(filters.items())
    for i in range(len(filter_items)):
        for j in range(i + 1, len(filter_items)):
            name1, fn1 = filter_items[i]
            name2, fn2 = filter_items[j]
            filtered = [t for t in trades if fn1(t) and fn2(t)]
            if len(filtered) >= 8:
                s = compute_stats(filtered)
                combos.append((f"{name1} + {name2}", s, filtered))

    # Test triples (top pairs only)
    top_pairs = sorted(combos, key=lambda x: x[1]["expectancy"], reverse=True)[:5]
    for pair_name, pair_s, pair_trades in top_pairs:
        if " + " not in pair_name:
            continue
        parts = pair_name.split(" + ")
        for name3, fn3 in filter_items:
            if name3 in parts:
                continue
            filtered = [t for t in pair_trades if fn3(t)]
            if len(filtered) >= 5:
                s = compute_stats(filtered)
                combos.append((f"{pair_name} + {name3}", s, filtered))

    # Sort by expectancy, show top 15
    combos.sort(key=lambda x: x[1]["expectancy"], reverse=True)

    print(f"  {'Filter combo':<50s} {'N':>5s} {'WR':>7s} {'Expect':>8s} {'Avg Blend':>10s} {'PF':>6s}")
    print("  " + "─" * 90)
    print(f"  {'BASELINE':<50s} {baseline['n']:>5d} {baseline['wr']:>6.1f}% {baseline['expectancy']:>8.3f} {baseline['avg_blended']:>10.3f} {baseline['profit_factor']:>6.2f}")
    print("  " + "─" * 90)

    seen = set()
    shown = 0
    for name, s, _ in combos:
        if shown >= 15:
            break
        if name in seen:
            continue
        seen.add(name)
        delta = s["expectancy"] - baseline["expectancy"]
        arrow = " ▲" if delta > 0.05 else " ▼" if delta < -0.05 else ""
        print(f"  {name:<50s} {s['n']:>5d} {s['wr']:>6.1f}% {s['expectancy']:>8.3f} {s['avg_blended']:>10.3f} {s['profit_factor']:>6.2f}{arrow}")
        shown += 1


# ─── Analysis: Custom Filter ────────────────────────────────────────────────

def apply_custom_filters(trades, filter_strs, exclude_str, min_confluence):
    """Apply user-specified filters."""
    filtered = list(trades)

    for f in filter_strs:
        key, val = f.split("=", 1)
        # Try numeric
        try:
            val_num = float(val)
            filtered = [t for t in filtered if t.get(key) == val_num or t.get(key) == int(val_num)]
        except ValueError:
            # Boolean
            if val.lower() in ("true", "yes"):
                filtered = [t for t in filtered if t.get(key)]
            elif val.lower() in ("false", "no"):
                filtered = [t for t in filtered if not t.get(key)]
            else:
                filtered = [t for t in filtered if str(t.get(key, "")) == val]

    if exclude_str:
        blacklist = set(s.strip() for s in exclude_str.split(","))
        filtered = [t for t in filtered if t.get("symbol") not in blacklist]

    if min_confluence:
        filtered = [t for t in filtered if t.get("tf_confluence", 0) >= min_confluence]

    return filtered


def report_filtered(trades, all_trades, filter_desc):
    section(f"FILTERED: {filter_desc}")
    s = compute_stats(trades)
    b = compute_stats(all_trades)
    print(f"  Trades:      {b['n']} → {s['n']}")
    print(f"  Win rate:    {b['wr']}% → {s['wr']}%")
    print(f"  Avg R:R:     {b['avg_rr']} → {s['avg_rr']}")
    print(f"  Avg Blended: {b['avg_blended']} → {s['avg_blended']}")
    print(f"  Expectancy:  {b['expectancy']} → {s['expectancy']}")
    print(f"  PF:          {b['profit_factor']} → {s['profit_factor']}")


# ─── Analysis: Actionable Findings ──────────────────────────────────────────

def report_findings(trades):
    section("ACTIONABLE FINDINGS")
    findings = []
    baseline = compute_stats(trades)

    # 1. Check rank performance
    rank_stats = {}
    for rank in [1, 2, 3, 4, 5]:
        rt = [t for t in trades if t.get("rank") == rank]
        if len(rt) >= 5:
            rank_stats[rank] = compute_stats(rt)

    best_rank = max(rank_stats.items(), key=lambda x: x[1]["expectancy"]) if rank_stats else None
    worst_rank = min(rank_stats.items(), key=lambda x: x[1]["expectancy"]) if rank_stats else None
    if best_rank and worst_rank and best_rank[0] != worst_rank[0]:
        findings.append(
            f"Rank {best_rank[0]} is best ({best_rank[1]['wr']}% WR, {best_rank[1]['expectancy']} expect), "
            f"Rank {worst_rank[0]} is worst ({worst_rank[1]['wr']}% WR, {worst_rank[1]['expectancy']} expect)"
        )

    # 2. Confluence impact
    c4 = [t for t in trades if t.get("tf_confluence", 0) >= 4]
    c_low = [t for t in trades if t.get("tf_confluence", 0) <= 2]
    if len(c4) >= 5 and len(c_low) >= 5:
        s4, sl = compute_stats(c4), compute_stats(c_low)
        if s4["wr"] - sl["wr"] > 5:
            findings.append(
                f"4/4 confluence ({s4['wr']}% WR) outperforms 2/4 ({sl['wr']}% WR) "
                f"by {round(s4['wr'] - sl['wr'], 1)}pp"
            )

    # 3. T1 savings potential
    for t1_r, label in [(0.75, "0.75R"), (1.0, "1.0R")]:
        sim_blends, saves = sim_blended_for_t1(trades, t1_r)
        sim_sum = sum(sim_blends)
        delta = sim_sum - baseline["blended_sum"]
        if delta > 2:
            findings.append(
                f"T1 at {label} would save {saves} losing trades → "
                f"+{round(delta, 1)}R blended sum improvement"
            )

    # 4. Direction imbalance
    longs = [t for t in trades if t.get("direction") == "long"]
    shorts = [t for t in trades if t.get("direction") == "short"]
    if len(longs) >= 10 and len(shorts) >= 5:
        sl, ss = compute_stats(longs), compute_stats(shorts)
        if abs(sl["expectancy"] - ss["expectancy"]) > 0.1:
            better = "shorts" if ss["expectancy"] > sl["expectancy"] else "longs"
            findings.append(
                f"Direction edge: {better} have better expectancy "
                f"(L: {sl['expectancy']}, S: {ss['expectancy']})"
            )

    # 5. Volume confirmation
    vol_yes = [t for t in trades if t.get("volume_confirmed")]
    vol_no = [t for t in trades if not t.get("volume_confirmed")]
    if len(vol_yes) >= 5 and len(vol_no) >= 5:
        sy, sn = compute_stats(vol_yes), compute_stats(vol_no)
        if sy["wr"] - sn["wr"] > 5:
            findings.append(
                f"Volume-confirmed setups ({sy['wr']}% WR) outperform "
                f"non-confirmed ({sn['wr']}% WR) by {round(sy['wr'] - sn['wr'], 1)}pp"
            )

    # 6. Fast stops (dead-on-arrival setups)
    fast_stop = [t for t in trades if t.get("stop_hit") and t.get("candles_to_exit", 99) <= 4]
    if len(fast_stop) >= 3:
        pct = round(len(fast_stop) / len(trades) * 100, 1)
        findings.append(
            f"{len(fast_stop)} trades ({pct}%) stopped out within 4 candles (dead-on-arrival)"
        )

    # 7. MFE wasted — direction was right but still lost
    direction_right_lost = [
        t for t in trades
        if t.get("max_favorable_rr", 0) >= 1.0 and not t.get("won")
    ]
    if direction_right_lost:
        findings.append(
            f"{len(direction_right_lost)} trades reached 1.0R+ MFE but still lost — "
            f"target placement or exit timing issue"
        )

    # Print
    if findings:
        for i, f in enumerate(findings, 1):
            print(f"  {i}. {f}")
    else:
        print("  No significant findings with current data size.")


# ─── Analysis: Stop Timing ──────────────────────────────────────────────────

def report_stop_timing(trades):
    section("STOP TIMING ANALYSIS")
    stopped = [t for t in trades if t.get("stop_hit")]
    if not stopped:
        print("  No stopped trades.")
        return

    n = len(stopped)
    candles = [t.get("candles_to_exit", 0) for t in stopped]
    avg_candles = round(sum(candles) / n, 1)

    buckets = {
        "≤4 candles (instant)": [t for t in stopped if t.get("candles_to_exit", 0) <= 4],
        "5-12 candles (fast)": [t for t in stopped if 5 <= t.get("candles_to_exit", 0) <= 12],
        "13-30 candles (normal)": [t for t in stopped if 13 <= t.get("candles_to_exit", 0) <= 30],
        "31-60 candles (slow)": [t for t in stopped if 31 <= t.get("candles_to_exit", 0) <= 60],
        "60+ candles (very slow)": [t for t in stopped if t.get("candles_to_exit", 0) > 60],
    }

    print(f"  Total stopped: {n} | Avg candles to stop: {avg_candles}\n")
    print(f"  {'Bucket':<28s} {'Count':>6s} {'%':>7s} {'Avg MFE':>8s}")
    print("  " + "─" * 52)
    for label, bucket in buckets.items():
        if bucket:
            avg_mfe = round(sum(t.get("max_favorable_rr", 0) for t in bucket) / len(bucket), 3)
            print(f"  {label:<28s} {len(bucket):>6d} {round(len(bucket)/n*100,1):>6.1f}% {avg_mfe:>8.3f}")


# ─── Analysis: Monthly Trend ────────────────────────────────────────────────

def report_monthly(trades):
    section("MONTHLY TREND")
    groups = defaultdict(list)
    for t in trades:
        tag = t.get("run_tag", "")
        if len(tag) >= 6:
            month = f"{tag[:4]}-{tag[4:6]}"
            groups[month].append(t)

    print_header()
    for month in sorted(groups.keys()):
        s = compute_stats(groups[month])
        print_row(month, s)


# ─── v11.3 Version Segments (before/after cutover) ───────────────────────────

def report_version_segments(trades):
    """Compare PRE-cutover vs POST-cutover (v11.3-era) trade performance.

    v11.3 changed forward SELECTION (confluence floor, no-4/4-rank1, long cap,
    canonical rules) — invisible to signal-formula/eval backtests, which read the
    old logs. This report isolates trades selected AFTER the v11.3 cutover so the
    `backtest` command can show whether the change actually helped.

    A trade is v11.3-era iff it carries `interest_score` (only v11.3 wrote it) —
    unambiguous and robust to same-day edge cases. Verdict thresholds are read from
    version_markers.json::validation_target so this stays consistent with
    weekly_eval::_version_validation_line (intentional duplication — different data
    source / entry point; not worth a shared helper).
    """
    section("v11.3 VERSION SEGMENTS (before vs after cutover)")

    if not VERSION_MARKERS.exists():
        print("  No version_markers.json — nothing to segment.")
        return
    try:
        markers = json.loads(VERSION_MARKERS.read_text(encoding="utf-8")).get("markers", [])
    except Exception as e:
        print(f"  Could not read version_markers.json: {e}")
        return
    if not markers:
        print("  version_markers.json has no markers.")
        return

    m = markers[-1]
    ver = m.get("version", "latest")
    cutover = m.get("cutover_trade_count", 0)
    tgt = m.get("validation_target", {})
    min_trades = tgt.get("min_trades", 20)
    wr_target = tgt.get("wr_target", 34.0)
    exp_target = tgt.get("expectancy_target", 0.0)

    # Split on the v11.3 structural marker.
    post = [t for t in trades if t.get("interest_score") is not None]
    pre = [t for t in trades if t.get("interest_score") is None]
    pre_s = compute_stats(pre)
    post_s = compute_stats(post)

    print(f"  Cutover: {ver} at {cutover} trades ({m.get('date', '?')}). "
          f"Targets: WR >= {wr_target:.0f}%, expectancy >= {exp_target:+.2f}R over {min_trades} trades.\n")
    print_header()
    print_row(f"PRE ({ver} baseline)", pre_s)
    print_row(f"POST ({ver}-era)", post_s)
    print("  " + "─" * 80)

    if pre_s["n"] != cutover:
        print(f"  ⚠ PRE segment n={pre_s['n']} != recorded cutover {cutover} "
              f"(eval logs changed since the marker was written).")

    n_post = post_s["n"]
    if n_post == 0:
        print(f"\n  VERDICT: {ver} UNPROVEN — no forward trades evaluated yet.")
        print("  Keep scanning; after the first v11.3 setups resolve, eval-scan populates POST.")
        return

    print(f"\n  Delta (POST - PRE): WR {post_s['wr'] - pre_s['wr']:+.1f}pp, "
          f"expectancy {post_s['expectancy'] - pre_s['expectancy']:+.3f}R, "
          f"avg R:R {post_s['avg_rr'] - pre_s['avg_rr']:+.3f}")

    # Gate-compliance audit — these should be impossible under v11.3's validate_setups.
    viol_conf = sum(1 for t in post if (t.get("tf_confluence") or 0) < config.LONG_MIN_CONFLUENCE)
    viol_44_rank1 = sum(1 for t in post
                        if str(t.get("rank")) == "1" and (t.get("tf_confluence") or 0) >= 4)
    print(f"  Gate compliance (expect 0): confluence<{config.LONG_MIN_CONFLUENCE} = {viol_conf}, "
          f"4/4-at-rank1 = {viol_44_rank1}")
    if viol_conf or viol_44_rank1:
        print("  ⚠ A v11.3 gate is NOT being enforced — investigate main.py::validate_setups.")

    if n_post < min_trades:
        print(f"\n  VERDICT: {ver} VALIDATING ({n_post}/{min_trades} forward trades) — too early to conclude.")
    elif post_s["wr"] >= wr_target and post_s["expectancy"] >= exp_target:
        print(f"\n  VERDICT: {ver} VALIDATED — {n_post} forward trades at {post_s['wr']:.0f}% WR / "
              f"{post_s['expectancy']:+.2f}R (targets {wr_target:.0f}% / {exp_target:+.2f}R). It's working.")
    else:
        print(f"\n  VERDICT: {ver} NOT VALIDATING — REVIEW NEEDED. {n_post} forward trades at "
              f"{post_s['wr']:.0f}% WR / {post_s['expectancy']:+.2f}R vs targets "
              f"{wr_target:.0f}% / {exp_target:+.2f}R. Re-audit before adding more rules.")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="What-if backtester for crypto-screener")
    parser.add_argument("--baseline", action="store_true", help="Baseline stats only")
    parser.add_argument("--t1-sweep", action="store_true", help="T1 distance analysis")
    parser.add_argument("--symbols", action="store_true", help="Per-symbol report")
    parser.add_argument("--rank-sweep", action="store_true", help="Rank cutoff analysis")
    parser.add_argument("--regime-sweep", action="store_true", help="Regime limit variations")
    parser.add_argument("--combo", action="store_true", help="Auto-discover best filter combos")
    parser.add_argument("--monthly", action="store_true", help="Monthly trend")
    parser.add_argument("--stops", action="store_true", help="Stop timing analysis")
    parser.add_argument("--version", action="store_true", help="v11.3 before/after cutover segment report")
    parser.add_argument("--filter", action="append", default=[], help="Filter: key=value (repeatable)")
    parser.add_argument("--exclude", type=str, default="", help="Blacklist symbols: SYM1,SYM2")
    parser.add_argument("--min-confluence", type=int, default=0, help="Minimum TF confluence")
    parser.add_argument("--min-symbol-trades", type=int, default=3, help="Min trades for symbol report")
    args = parser.parse_args()

    # Load data
    print("\n  Loading data...")
    trades = load_all_evals()
    setup_lookup = load_setup_lookup()
    trades = merge_trades(trades, setup_lookup)

    if not trades:
        print("  No evaluated trades found!")
        sys.exit(1)

    print(f"  Loaded {len(trades)} evaluated trades from {len(set(t['run_tag'] for t in trades))} runs.")

    # Apply custom filters if specified
    if args.filter or args.exclude or args.min_confluence:
        all_trades = list(trades)
        trades = apply_custom_filters(trades, args.filter, args.exclude, args.min_confluence)
        desc_parts = args.filter + ([f"exclude={args.exclude}"] if args.exclude else []) + \
                     ([f"confluence>={args.min_confluence}"] if args.min_confluence else [])
        report_filtered(trades, all_trades, " + ".join(desc_parts))
        if not trades:
            print("  No trades match filter!")
            sys.exit(0)

    # Determine which reports to run
    specific = any([
        args.baseline, args.t1_sweep, args.symbols, args.rank_sweep,
        args.regime_sweep, args.combo, args.monthly, args.stops, args.version,
    ])
    run_all = not specific

    if run_all or args.baseline:
        report_baseline(trades)

    if run_all or args.monthly:
        report_monthly(trades)

    if run_all:
        for dim, label in [
            ("direction", "direction"),
            ("confidence", "confidence"),
            ("setup_type", "setup type"),
            ("tf_confluence", "TF confluence"),
            ("regime", "regime"),
            ("volume_confirmed", "volume confirmed"),
        ]:
            report_by_dimension(trades, dim, label)

    if run_all or args.t1_sweep:
        report_t1_sweep(trades)

    if run_all or args.rank_sweep:
        report_rank_sweep(trades)

    if run_all or args.regime_sweep:
        report_regime_sweep(trades)

    if run_all or args.symbols:
        report_symbols(trades, args.min_symbol_trades)

    if run_all or args.stops:
        report_stop_timing(trades)

    if run_all or args.combo:
        report_combo(trades)

    if run_all or args.version:
        report_version_segments(trades)

    if run_all:
        report_findings(trades)

    print()


if __name__ == "__main__":
    main()
