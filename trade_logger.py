#!/usr/bin/env python
"""
Trade Logger — CLI tool for managing my_trades.json.

Usage:
  python trade_logger.py open     # Open a new trade (pick from recent setups)
  python trade_logger.py close    # Close an open trade (input exit price)
  python trade_logger.py list     # List all trades
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

TRADES_FILE = Path(__file__).parent / "logs" / "trades" / "my_trades.json"
SETUPS_DIR = Path(__file__).parent / "logs" / "setups"


def load_trades():
    if TRADES_FILE.exists():
        with open(TRADES_FILE) as f:
            return json.load(f)
    return []


def save_trades(trades):
    TRADES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TRADES_FILE, "w") as f:
        json.dump(trades, f, indent=2)
    print(f"\nSaved to {TRADES_FILE}")


def get_recent_setups(n=5):
    """Load the N most recent setup files."""
    files = sorted(SETUPS_DIR.glob("setups_*.json"))[-n:]
    all_setups = []
    for f in files:
        with open(f) as fh:
            data = json.load(fh)
        run_tag = data.get("run_tag", f.stem.replace("setups_", ""))
        model = data.get("model", "unknown")
        for setup in data.get("setups", []):
            setup["_run_tag"] = run_tag
            setup["_model"] = model
            setup["_file"] = f.name
            all_setups.append(setup)
    return all_setups


def pick_number(prompt, min_val, max_val):
    while True:
        raw = input(prompt).strip()
        if not raw:
            return None
        try:
            val = int(raw)
            if min_val <= val <= max_val:
                return val
        except ValueError:
            pass
        print(f"  Enter a number between {min_val} and {max_val} (or Enter to skip)")


def pick_float(prompt, required=True):
    while True:
        raw = input(prompt).strip()
        if not raw:
            if required:
                print("  This field is required.")
                continue
            return None
        try:
            return float(raw)
        except ValueError:
            print("  Enter a valid number.")


def cmd_open():
    """Open a new trade by picking a setup and entering your real entry."""
    setups = get_recent_setups()
    if not setups:
        print("No setup files found.")
        return

    print("\n=== Recent Setups ===\n")
    for i, s in enumerate(setups, 1):
        print(
            f"  [{i}] {s['symbol']:12s} {s['direction']:5s} "
            f"rank={s['rank']}  {s['setup_type']:20s} "
            f"entry={s['entry_low']}-{s['entry_high']}  "
            f"SL={s['stop_loss']}  T1={s['target_1']}  T2={s['target_2']}  "
            f"RR={s['predicted_rr']}  conf={s['confidence']}  "
            f"({s['_file']})"
        )

    idx = pick_number("\nPick setup number: ", 1, len(setups))
    if idx is None:
        print("Cancelled.")
        return

    setup = setups[idx - 1]
    print(f"\nSelected: {setup['symbol']} {setup['direction']} from {setup['_file']}")
    print(f"  Recommended entry: {setup['entry_low']} - {setup['entry_high']}")
    print(f"  Recommended SL:    {setup['stop_loss']}")
    print(f"  Recommended T1:    {setup['target_1']}")
    print(f"  Recommended T2:    {setup['target_2']}")

    entry_price = pick_float("\nYour actual entry price: ")

    # SL default to recommendation
    sl_input = input(
        f"Your stop loss [{setup['stop_loss']}]: "
    ).strip()
    stop_loss = float(sl_input) if sl_input else setup["stop_loss"]

    # TP is optional (might not be set yet)
    tp_input = input(
        f"Your take profit target (Enter to skip): "
    ).strip()
    tp = float(tp_input) if tp_input else None

    note = input("Note (optional): ").strip() or None

    trade = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "run_tag": setup["_run_tag"],
        "symbol": setup["symbol"],
        "direction": setup["direction"],
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "target_hit": None,
        "actual_exit": None,
        "exit_reason": None,
        "result": "open",
        "pnl_percent": None,
        "claude_recommendation": {
            "rank": setup["rank"],
            "model": setup["_model"],
            "setup_type": setup["setup_type"],
            "timeframe": setup["timeframe"],
            "confidence": setup["confidence"],
            "tf_confluence": setup["tf_confluence"],
            "entry_low": setup["entry_low"],
            "entry_high": setup["entry_high"],
            "stop_loss": setup["stop_loss"],
            "target_1": setup["target_1"],
            "target_2": setup["target_2"],
            "predicted_rr": setup["predicted_rr"],
        },
        "note": note,
        "failure_reason": None,
    }

    if tp:
        trade["note"] = (
            f"TP set at {tp}. " + (trade["note"] or "")
        ).strip()

    trades = load_trades()
    trades.append(trade)
    save_trades(trades)

    print(f"\nOpened: {setup['symbol']} {setup['direction']} @ {entry_price}")


def cmd_close():
    """Close an open trade by entering exit price and reason."""
    trades = load_trades()
    open_trades = [(i, t) for i, t in enumerate(trades) if t["result"] == "open"]

    if not open_trades:
        print("No open trades.")
        return

    print("\n=== Open Trades ===\n")
    for display_idx, (_, t) in enumerate(open_trades, 1):
        print(
            f"  [{display_idx}] {t['symbol']:12s} {t['direction']:5s} "
            f"entry={t['entry_price']}  SL={t['stop_loss']}  "
            f"date={t['date']}"
        )

    idx = pick_number("\nPick trade to close: ", 1, len(open_trades))
    if idx is None:
        print("Cancelled.")
        return

    real_idx, trade = open_trades[idx - 1]

    exit_price = pick_float("Exit price: ")

    print("\nExit reason:")
    print("  [1] target_hit")
    print("  [2] stop_loss")
    print("  [3] manual_close")
    print("  [4] breakeven")
    reason_map = {1: "target_hit", 2: "stop_loss", 3: "manual_close", 4: "breakeven"}
    reason_idx = pick_number("Pick reason: ", 1, 4)
    exit_reason = reason_map.get(reason_idx, "manual_close")

    # Calculate PnL %
    if trade["direction"] == "long":
        pnl_pct = round((exit_price - trade["entry_price"]) / trade["entry_price"] * 100, 2)
    else:
        pnl_pct = round((trade["entry_price"] - exit_price) / trade["entry_price"] * 100, 2)

    result = "win" if pnl_pct > 0 else ("breakeven" if pnl_pct == 0 else "loss")

    # Update target_hit if reason is target_hit
    target_hit = exit_price if exit_reason == "target_hit" else None

    note = input("Note (optional, Enter to keep existing): ").strip()
    failure_reason = None
    if result == "loss":
        print("\nFailure reason (optional):")
        print("  [1] target_too_far")
        print("  [2] sl_too_tight")
        print("  [3] wrong_direction")
        print("  [4] bad_timing")
        print("  [5] other")
        print("  [Enter] skip")
        fr_map = {
            1: "target_too_far",
            2: "sl_too_tight",
            3: "wrong_direction",
            4: "bad_timing",
            5: "other",
        }
        fr_idx = pick_number("Pick: ", 1, 5)
        failure_reason = fr_map.get(fr_idx)

    trade["actual_exit"] = exit_price
    trade["exit_reason"] = exit_reason
    trade["result"] = result
    trade["pnl_percent"] = pnl_pct
    trade["target_hit"] = target_hit
    if note:
        trade["note"] = note
    if failure_reason:
        trade["failure_reason"] = failure_reason

    trades[real_idx] = trade
    save_trades(trades)

    emoji = "+" if pnl_pct >= 0 else ""
    print(f"\nClosed: {trade['symbol']} → {result} ({emoji}{pnl_pct}%)")


def cmd_list():
    """Show all trades."""
    trades = load_trades()
    if not trades:
        print("No trades yet.")
        return

    print(f"\n=== All Trades ({len(trades)}) ===\n")
    for t in trades:
        status = t["result"].upper()
        pnl = f"{t['pnl_percent']:+.2f}%" if t["pnl_percent"] is not None else "---"
        print(
            f"  {t['date']}  {t['symbol']:12s} {t['direction']:5s} "
            f"entry={t['entry_price']}  exit={t.get('actual_exit') or '---':>10}  "
            f"pnl={pnl:>8}  [{status}]"
        )

    # Summary
    closed = [t for t in trades if t["result"] in ("win", "loss", "breakeven")]
    if closed:
        wins = sum(1 for t in closed if t["result"] == "win")
        total_pnl = sum(t["pnl_percent"] for t in closed if t["pnl_percent"] is not None)
        print(f"\n  Closed: {len(closed)}  |  Wins: {wins}/{len(closed)} ({wins/len(closed)*100:.0f}%)  |  Total PnL: {total_pnl:+.2f}%")

    open_count = sum(1 for t in trades if t["result"] == "open")
    if open_count:
        print(f"  Open:   {open_count}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1].lower()
    if cmd == "open":
        cmd_open()
    elif cmd == "close":
        cmd_close()
    elif cmd == "list":
        cmd_list()
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
