"""
Weekly evaluation script — scores past setups against actual price data.

Run manually or schedule for every Sunday:
    source venv/bin/activate
    python weekly_eval.py

What it does:
1. Reads all unscored setup JSONs from logs/setups/
2. For each setup, fetches actual klines from Bybit after the brief timestamp
3. Checks: did entry trigger? did stop hit first or target?
4. Records results in logs/evaluations/
5. Aggregates all evaluations into logs/performance/summary.md
"""

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pybit.unified_trading import HTTP
import config


# How many days to look forward for each timeframe
EVAL_WINDOWS = {
    "scalp": 1,
    "intraday": 2,
    "swing": 7,
}

SETUPS_DIR = Path("logs/setups")
EVALS_DIR = Path("logs/evaluations")
PERFORMANCE_DIR = Path("logs/performance")
TRADES_FILE = Path("logs/trades/my_trades.json")

# Only evaluate setups from the last N weeks
EVAL_LOOKBACK_WEEKS = 7


def get_bybit_client():
    return HTTP(
        testnet=False,
        api_key=config.BYBIT_API_KEY,
        api_secret=config.BYBIT_API_SECRET,
    )


def fetch_klines_after(client, symbol, start_time_utc, days):
    """Fetch 15m klines for `days` after start_time_utc. Returns list of (timestamp, high, low, close)."""
    start_ms = int(start_time_utc.timestamp() * 1000)
    end_ms = int((start_time_utc + timedelta(days=days)).timestamp() * 1000)

    all_candles = []
    cursor_start = start_ms

    while cursor_start < end_ms:
        try:
            res = client.get_kline(
                category="linear",
                symbol=symbol,
                interval="15",
                start=cursor_start,
                end=end_ms,
                limit=200,
            )
            candles = res["result"]["list"]
            if not candles:
                break

            # Bybit returns newest first
            candles.reverse()
            for c in candles:
                ts = int(c[0])
                if ts >= cursor_start:
                    all_candles.append({
                        "timestamp": ts,
                        "high": float(c[2]),
                        "low": float(c[3]),
                        "close": float(c[4]),
                    })

            # Move cursor past last candle
            last_ts = int(candles[-1][0])
            if last_ts <= cursor_start:
                break
            cursor_start = last_ts + 1

            time.sleep(0.1)  # rate limit
        except Exception as e:
            print(f"  Error fetching klines for {symbol}: {e}")
            break

    return all_candles


def evaluate_setup(client, setup, run_timestamp_utc):
    """Evaluate a single setup against actual price data."""
    symbol = setup["symbol"]
    direction = setup["direction"]
    timeframe = setup.get("timeframe", "intraday")
    entry_low = setup["entry_low"]
    entry_high = setup["entry_high"]
    stop_loss = setup["stop_loss"]
    target_1 = setup["target_1"]
    target_2 = setup.get("target_2")

    days = EVAL_WINDOWS.get(timeframe, 2)
    run_dt = datetime.fromisoformat(run_timestamp_utc)

    # Check if enough time has passed
    now = datetime.now(timezone.utc)
    if now < run_dt + timedelta(days=days):
        return None  # too early to evaluate

    candles = fetch_klines_after(client, symbol, run_dt, days)
    if not candles:
        return {"status": "no_data", "reason": "Could not fetch klines"}

    # Phase 1: Did price enter the entry zone?
    entry_triggered = False
    entry_candle_idx = None
    entry_price = (entry_low + entry_high) / 2  # assume mid-zone fill

    for i, c in enumerate(candles):
        if direction == "long":
            # Price dipped into or through the entry zone
            if c["low"] <= entry_high:
                entry_triggered = True
                entry_candle_idx = i
                entry_price = min(max(c["close"], entry_low), entry_high)
                break
        else:  # short
            if c["high"] >= entry_low:
                entry_triggered = True
                entry_candle_idx = i
                entry_price = max(min(c["close"], entry_high), entry_low)
                break

    if not entry_triggered:
        return {"status": "not_triggered", "reason": "Price never reached entry zone"}

    # Phase 2: After entry, did stop or target hit first?
    stop_hit = False
    t1_hit = False
    t2_hit = False
    exit_price = None
    exit_reason = None

    for c in candles[entry_candle_idx:]:
        if direction == "long":
            if c["low"] <= stop_loss:
                stop_hit = True
                exit_price = stop_loss
                exit_reason = "stop_loss"
                break
            if c["high"] >= target_1 and not t1_hit:
                t1_hit = True
            if target_2 and c["high"] >= target_2:
                t2_hit = True
                exit_price = target_2
                exit_reason = "target_2"
                break
        else:  # short
            if c["high"] >= stop_loss:
                stop_hit = True
                exit_price = stop_loss
                exit_reason = "stop_loss"
                break
            if c["low"] <= target_1 and not t1_hit:
                t1_hit = True
            if target_2 and c["low"] <= target_2:
                t2_hit = True
                exit_price = target_2
                exit_reason = "target_2"
                break

    # If neither stop nor target_2 hit, check if target_1 was hit
    if not stop_hit and not t2_hit:
        if t1_hit:
            exit_price = target_1
            exit_reason = "target_1"
        else:
            # Use last candle close as "still open" or expired
            exit_price = candles[-1]["close"]
            exit_reason = "expired"

    # Calculate actual R:R
    risk = abs(entry_price - stop_loss)
    if risk == 0:
        actual_rr = 0
    else:
        if direction == "long":
            actual_rr = round((exit_price - entry_price) / risk, 2)
        else:
            actual_rr = round((entry_price - exit_price) / risk, 2)

    won = actual_rr > 0

    return {
        "status": "evaluated",
        "entry_triggered": True,
        "entry_price": round(entry_price, 6),
        "exit_price": round(exit_price, 6),
        "exit_reason": exit_reason,
        "target_1_hit": t1_hit,
        "target_2_hit": t2_hit,
        "stop_hit": stop_hit,
        "actual_rr": actual_rr,
        "won": won,
    }


def run_evaluation():
    """Main evaluation loop — process all unscored setup files."""
    EVALS_DIR.mkdir(parents=True, exist_ok=True)
    PERFORMANCE_DIR.mkdir(parents=True, exist_ok=True)

    if not SETUPS_DIR.exists():
        print("No setups directory found. Run the screener first.")
        return

    # --- Phase 1: Load ALL past evaluations (full history for learning) ---
    all_evals = []
    for ef in sorted(EVALS_DIR.glob("eval_*.json")):
        try:
            all_evals.append(json.loads(ef.read_text(encoding="utf-8")))
        except Exception:
            pass
    evaluated_tags = {e["run_tag"] for e in all_evals}
    print(f"Loaded {len(all_evals)} past evaluation(s) from history.")

    # --- Phase 2: Evaluate NEW setups from last {EVAL_LOOKBACK_WEEKS} weeks only ---
    cutoff = datetime.now(timezone.utc) - timedelta(weeks=EVAL_LOOKBACK_WEEKS)
    all_setup_files = sorted(SETUPS_DIR.glob("setups_*.json"))
    setup_files = []
    for sf in all_setup_files:
        try:
            record = json.loads(sf.read_text(encoding="utf-8"))
            run_dt = datetime.fromisoformat(record["run_timestamp_utc"])
            if run_dt >= cutoff:
                setup_files.append(sf)
        except Exception:
            setup_files.append(sf)  # include if we can't parse date

    # Count how many actually need evaluation (new or partially evaluated)
    pending = []
    for sf in setup_files:
        record = json.loads(sf.read_text(encoding="utf-8"))
        run_tag = record["run_tag"]
        if run_tag not in evaluated_tags:
            pending.append(sf)
        else:
            # Re-evaluate if previous run was partial (some setups were "too early")
            existing = next((e for e in all_evals if e["run_tag"] == run_tag), None)
            if existing and len(existing["results"]) < len(record["setups"]):
                pending.append(sf)
    print(f"Found {len(setup_files)} setup file(s) within last {EVAL_LOOKBACK_WEEKS} weeks, "
          f"{len(pending)} need evaluation.")

    new_count = 0
    if pending:
        client = get_bybit_client()

        for sf in pending:
            record = json.loads(sf.read_text(encoding="utf-8"))
            run_tag = record["run_tag"]
            run_ts = record["run_timestamp_utc"]
            model = record.get("model", "unknown")
            setups = record["setups"]
            print(f"\nEvaluating {run_tag} [{model}] ({len(setups)} setups)...")

            # Find already-evaluated symbols for this run (from partial eval)
            existing_eval = next((e for e in all_evals if e["run_tag"] == run_tag), None)
            already_evaluated = set()
            if existing_eval:
                already_evaluated = {r["symbol"] for r in existing_eval["results"]}

            eval_results = []

            for setup in setups:
                symbol = setup["symbol"]

                # Skip if already evaluated in a previous partial run
                if symbol in already_evaluated:
                    continue

                print(f"  → {symbol} ({setup['direction']} {setup['timeframe']})...", end=" ")

                result = evaluate_setup(client, setup, run_ts)
                if result is None:
                    print("too early to evaluate")
                    continue  # skip this setup, evaluate others

                result["symbol"] = symbol
                result["direction"] = setup["direction"]
                result["timeframe"] = setup.get("timeframe", "intraday")
                result["setup_type"] = setup.get("setup_type", "other")
                result["confidence"] = setup.get("confidence", "medium")
                result["predicted_rr"] = setup.get("predicted_rr", 0)
                result["tf_confluence"] = setup.get("tf_confluence", 0)
                result["rank"] = setup.get("rank", 0)
                eval_results.append(result)

                status = result["status"]
                if status == "evaluated":
                    icon = "✓" if result["won"] else "✗"
                    print(f"{icon} R:R {result['actual_rr']} ({result['exit_reason']})")
                else:
                    print(f"— {result['reason']}")

                time.sleep(0.1)

            if not eval_results:
                continue  # all setups either already done or too early

            # Merge with existing partial eval or create new
            if existing_eval:
                existing_eval["results"].extend(eval_results)
                existing_eval["evaluated_at_utc"] = datetime.now(timezone.utc).isoformat()
                eval_record = existing_eval
            else:
                eval_record = {
                    "run_tag": run_tag,
                    "run_timestamp_utc": run_ts,
                    "model": model,
                    "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
                    "results": eval_results,
                }
                all_evals.append(eval_record)

            eval_file = EVALS_DIR / f"eval_{run_tag}.json"
            eval_file.write_text(json.dumps(eval_record, indent=2), encoding="utf-8")
            new_count += 1
            print(f"  Saved to {eval_file}")

    print(f"\n{'='*40}")
    print(f"Evaluated {new_count} new run(s). Total evaluations in history: {len(all_evals)}.")

    # --- Phase 3: Generate summary from ALL evaluations (full history) ---
    # This ensures the model learns from all past results, not just recent ones.
    generate_summary(all_evals)


def load_manual_trades():
    """Load the user's manual trade history from logs/trades/my_trades.json."""
    if not TRADES_FILE.exists():
        return []
    try:
        trades = json.loads(TRADES_FILE.read_text(encoding="utf-8"))
        return trades if isinstance(trades, list) else []
    except Exception as e:
        print(f"  Warning: Could not load manual trades: {e}")
        return []


def generate_summary(all_evals):
    """Aggregate all evaluations into a performance summary."""
    if not all_evals:
        print("No evaluations to summarize.")
        return

    # Load manual trade history
    manual_trades = load_manual_trades()

    # Flatten all results, carrying model info from the eval record
    all_results = []
    for ev in all_evals:
        for r in ev["results"]:
            r["run_tag"] = ev["run_tag"]
            r["model"] = ev.get("model", "unknown")
            all_results.append(r)

    evaluated = [r for r in all_results if r["status"] == "evaluated"]
    not_triggered = [r for r in all_results if r["status"] == "not_triggered"]
    total = len(all_results)

    if not evaluated:
        summary = "# Performance Summary\n\nNo evaluated setups yet. Need more data.\n"
        PERFORMANCE_DIR.mkdir(parents=True, exist_ok=True)
        (PERFORMANCE_DIR / "summary.md").write_text(summary, encoding="utf-8")
        print(f"Summary written (no data yet).")
        return

    wins = [r for r in evaluated if r["won"]]
    losses = [r for r in evaluated if not r["won"]]
    win_rate = len(wins) / len(evaluated) * 100 if evaluated else 0
    avg_rr = sum(r["actual_rr"] for r in evaluated) / len(evaluated) if evaluated else 0
    avg_win_rr = sum(r["actual_rr"] for r in wins) / len(wins) if wins else 0
    avg_loss_rr = sum(r["actual_rr"] for r in losses) / len(losses) if losses else 0

    # Stats by setup type
    setup_types = {}
    for r in evaluated:
        st = r.get("setup_type", "other")
        if st not in setup_types:
            setup_types[st] = {"wins": 0, "losses": 0, "rr_sum": 0, "count": 0}
        setup_types[st]["count"] += 1
        setup_types[st]["rr_sum"] += r["actual_rr"]
        if r["won"]:
            setup_types[st]["wins"] += 1
        else:
            setup_types[st]["losses"] += 1

    # Stats by confidence
    confidence_stats = {}
    for r in evaluated:
        conf = r.get("confidence", "medium")
        if conf not in confidence_stats:
            confidence_stats[conf] = {"wins": 0, "losses": 0, "count": 0}
        confidence_stats[conf]["count"] += 1
        if r["won"]:
            confidence_stats[conf]["wins"] += 1
        else:
            confidence_stats[conf]["losses"] += 1

    # Stats by rank
    rank_stats = {}
    for r in evaluated:
        rank = r.get("rank", 0)
        if rank not in rank_stats:
            rank_stats[rank] = {"wins": 0, "losses": 0, "count": 0}
        rank_stats[rank]["count"] += 1
        if r["won"]:
            rank_stats[rank]["wins"] += 1
        else:
            rank_stats[rank]["losses"] += 1

    # Stats by model
    model_stats = {}
    for r in evaluated:
        model = r.get("model", "unknown")
        if model not in model_stats:
            model_stats[model] = {"wins": 0, "losses": 0, "rr_sum": 0, "count": 0}
        model_stats[model]["count"] += 1
        model_stats[model]["rr_sum"] += r["actual_rr"]
        if r["won"]:
            model_stats[model]["wins"] += 1
        else:
            model_stats[model]["losses"] += 1

    # Build summary
    lines = [
        "# Performance Summary",
        f"_Last updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_",
        f"_Total runs evaluated: {len(all_evals)}_",
        "",
        "## Overall Stats",
        f"- Total setups: {total}",
        f"- Triggered: {len(evaluated)} ({len(evaluated)/total*100:.0f}%)" if total else "",
        f"- Not triggered: {len(not_triggered)}",
        f"- **Win rate: {win_rate:.1f}%** ({len(wins)}W / {len(losses)}L)",
        f"- Avg actual R:R: {avg_rr:.2f}",
        f"- Avg winning R:R: {avg_win_rr:.2f}",
        f"- Avg losing R:R: {avg_loss_rr:.2f}",
        "",
        "## By Setup Type",
        "| Setup Type | Trades | Wins | Losses | Win Rate | Avg R:R |",
        "|---|---|---|---|---|---|",
    ]

    for st, s in sorted(setup_types.items(), key=lambda x: x[1]["count"], reverse=True):
        wr = s["wins"] / s["count"] * 100 if s["count"] else 0
        ar = s["rr_sum"] / s["count"] if s["count"] else 0
        lines.append(f"| {st} | {s['count']} | {s['wins']} | {s['losses']} | {wr:.0f}% | {ar:.2f} |")

    lines += [
        "",
        "## By Confidence Level",
        "| Confidence | Trades | Wins | Losses | Win Rate |",
        "|---|---|---|---|---|",
    ]

    for conf in ["high", "medium", "low"]:
        if conf in confidence_stats:
            s = confidence_stats[conf]
            wr = s["wins"] / s["count"] * 100 if s["count"] else 0
            lines.append(f"| {conf} | {s['count']} | {s['wins']} | {s['losses']} | {wr:.0f}% |")

    lines += [
        "",
        "## By Rank Position",
        "| Rank | Trades | Win Rate |",
        "|---|---|---|",
    ]

    for rank in sorted(rank_stats.keys()):
        s = rank_stats[rank]
        wr = s["wins"] / s["count"] * 100 if s["count"] else 0
        lines.append(f"| #{rank} | {s['count']} | {wr:.0f}% |")

    # Stats by model
    if len(model_stats) > 0:
        lines += [
            "",
            "## By Model",
            "| Model | Trades | Wins | Losses | Win Rate | Avg R:R |",
            "|---|---|---|---|---|---|",
        ]
        for model, s in sorted(model_stats.items()):
            wr = s["wins"] / s["count"] * 100 if s["count"] else 0
            ar = s["rr_sum"] / s["count"] if s["count"] else 0
            lines.append(f"| {model} | {s['count']} | {s['wins']} | {s['losses']} | {wr:.0f}% | {ar:.2f} |")

    # Manual trade history section
    if manual_trades:
        closed = [t for t in manual_trades if t.get("result") in ("win", "loss")]
        my_wins = [t for t in closed if t.get("result") == "win"]
        my_losses = [t for t in closed if t.get("result") == "loss"]
        my_open = [t for t in manual_trades if t.get("result") == "open"]
        my_total = len(closed)
        my_wr = len(my_wins) / my_total * 100 if my_total else 0

        lines += [
            "",
            "## Trader's Actual Trades (Manual Log)",
            f"- Closed trades: {my_total} ({len(my_wins)}W / {len(my_losses)}L)",
            f"- Open trades: {len(my_open)}",
            f"- Win rate (closed): {my_wr:.0f}%",
        ]

        # Failure pattern analysis
        failure_reasons = {}
        for t in manual_trades:
            fr = t.get("failure_reason")
            if fr:
                failure_reasons[fr] = failure_reasons.get(fr, 0) + 1
        if failure_reasons:
            lines += ["", "### Recurring Failure Patterns"]
            for reason, count in sorted(failure_reasons.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"- **{reason}**: {count} occurrence(s)")

        # Detailed trade-by-trade with Claude recommendation context (last 10 only to control token cost)
        recent_trades = manual_trades[-10:]
        if len(manual_trades) > 10:
            lines += [
                "",
                f"### Trade-by-Trade Analysis (last 10 of {len(manual_trades)} — USE THESE TO IMPROVE FUTURE SETUPS)",
            ]
        else:
            lines += [
                "",
                "### Trade-by-Trade Analysis (USE THESE TO IMPROVE FUTURE SETUPS)",
            ]
        for t in recent_trades:
            rec = t.get("claude_recommendation", {})
            symbol = t.get("symbol", "?")
            lines.append(f"")
            lines.append(f"**{symbol}** ({t.get('date', '?')}) — {t.get('result', '?').upper()}")
            lines.append(f"- Trader: entry {t.get('entry_price', '?')}, SL {t.get('stop_loss', '?')}, "
                         f"exit {t.get('actual_exit', 'open')}, reason: {t.get('exit_reason', 'n/a')}")
            if rec:
                lines.append(f"- Claude recommended: {rec.get('setup_type', '?')} ({rec.get('timeframe', '?')}), "
                             f"rank #{rec.get('rank', '?')}, confidence {rec.get('confidence', '?')}, "
                             f"model {rec.get('model', '?')}")
                lines.append(f"  Entry zone {rec.get('entry_low', '?')}–{rec.get('entry_high', '?')}, "
                             f"SL {rec.get('stop_loss', '?')}, T1 {rec.get('target_1', '?')}, "
                             f"T2 {rec.get('target_2', '?')}, predicted R:R {rec.get('predicted_rr', '?')}")
            note = t.get("note", "").strip()
            fr = t.get("failure_reason", "")
            if note:
                lines.append(f"- **Lesson**: {note}")
            if fr:
                lines.append(f"- **Failure category**: {fr}")

    # Actionable insights
    lines += [
        "",
        "## Key Insights for Future Briefs",
    ]

    if win_rate < 40:
        lines.append("- WARNING: Overall win rate below 40%. Consider stricter entry criteria.")
    if win_rate >= 50:
        lines.append("- Win rate is healthy. Maintain current setup selection approach.")

    # Find best/worst setup types
    if setup_types:
        best = max(setup_types.items(), key=lambda x: (x[1]["wins"]/x[1]["count"]) if x[1]["count"] >= 3 else 0)
        worst = min(setup_types.items(), key=lambda x: (x[1]["wins"]/x[1]["count"]) if x[1]["count"] >= 3 else 1)
        if best[1]["count"] >= 3:
            lines.append(f"- Best setup type: **{best[0]}** ({best[1]['wins']}/{best[1]['count']} wins)")
        if worst[1]["count"] >= 3 and worst[0] != best[0]:
            lines.append(f"- Worst setup type: **{worst[0]}** ({worst[1]['wins']}/{worst[1]['count']} wins) — consider deprioritizing")

    # Confidence calibration check
    high_stats = confidence_stats.get("high", {"wins": 0, "count": 0})
    med_stats = confidence_stats.get("medium", {"wins": 0, "count": 0})
    if high_stats["count"] >= 3 and med_stats["count"] >= 3:
        high_wr = high_stats["wins"] / high_stats["count"]
        med_wr = med_stats["wins"] / med_stats["count"]
        if high_wr <= med_wr:
            lines.append("- CALIBRATION ISSUE: 'High' confidence setups don't outperform 'Medium'. Recalibrate confidence scoring.")
        else:
            lines.append("- Confidence calibration looks good: High > Medium win rates.")

    # Model comparison
    if len(model_stats) >= 2:
        model_ranked = sorted(model_stats.items(), key=lambda x: (x[1]["wins"]/x[1]["count"]) if x[1]["count"] >= 3 else 0, reverse=True)
        best_model = model_ranked[0]
        if best_model[1]["count"] >= 3:
            best_wr = best_model[1]["wins"] / best_model[1]["count"] * 100
            best_ar = best_model[1]["rr_sum"] / best_model[1]["count"]
            lines.append(f"- Best performing model: **{best_model[0]}** ({best_wr:.0f}% win rate, {best_ar:.2f} avg R:R)")
        # Compare all models with enough data
        for model, s in model_ranked:
            if s["count"] >= 5:
                wr = s["wins"] / s["count"] * 100
                ar = s["rr_sum"] / s["count"]
                lines.append(f"- {model}: {wr:.0f}% win rate, {ar:.2f} avg R:R over {s['count']} trades")

    summary_text = "\n".join(lines) + "\n"
    PERFORMANCE_DIR.mkdir(parents=True, exist_ok=True)
    summary_file = PERFORMANCE_DIR / "summary.md"
    summary_file.write_text(summary_text, encoding="utf-8")
    print(f"Performance summary written to {summary_file}")


if __name__ == "__main__":
    print("=" * 50)
    print("Crypto Screener — Weekly Evaluation")
    print("=" * 50)
    run_evaluation()
