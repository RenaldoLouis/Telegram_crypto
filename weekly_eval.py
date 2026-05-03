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
WIN_RATE_HISTORY_FILE = Path("logs/performance/win_rate_history.json")
LIFETIME_STATS_FILE = Path("logs/performance/lifetime_stats.json")
STRATEGIC_RULES_FILE = Path("logs/performance/strategic_rules.md")
RECENT_PERFORMANCE_FILE = Path("logs/performance/recent_performance.md")

# Only evaluate setups from the last N weeks
EVAL_LOOKBACK_WEEKS = 7

# Rolling window for recent performance (sent to Claude)
RECENT_WINDOW_WEEKS = 4


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
    # Also track MFE (max favorable excursion) — how far price moved in our
    # direction before the outcome. This tells us if direction was right but
    # stop was too tight.
    stop_hit = False
    t1_hit = False
    t2_hit = False
    exit_price = None
    exit_reason = None
    risk = abs(entry_price - stop_loss)
    max_favorable_rr = 0.0  # best R:R reached before exit
    candles_to_exit = 0

    for c in candles[entry_candle_idx:]:
        candles_to_exit += 1

        # Track MFE before checking exit conditions
        if risk > 0:
            if direction == "long":
                favorable = (c["high"] - entry_price) / risk
            else:
                favorable = (entry_price - c["low"]) / risk
            max_favorable_rr = max(max_favorable_rr, favorable)

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
        "max_favorable_rr": round(max_favorable_rr, 2),
        "candles_to_exit": candles_to_exit,
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

    # --- Phase 3: Update tiered knowledge system ---
    # Layer 1: Update lifetime stats incrementally
    update_lifetime_stats(all_evals)
    # Layer 2: Generate strategic rules from lifetime stats (for Claude)
    generate_strategic_rules()
    # Layer 3: Generate recent performance window (for Claude)
    generate_recent_performance(all_evals)
    # Human report: regenerate summary.md for human readability
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


def _empty_lifetime_stats():
    """Return a fresh lifetime stats structure."""
    return {
        "last_updated": "",
        "total_setups": 0,
        "total_evaluated": 0,
        "total_not_triggered": 0,
        "overall": {"wins": 0, "losses": 0, "rr_sum": 0.0},
        "by_setup_type": {},
        "by_confidence": {},
        "by_rank": {},
        "by_model": {},
        "by_timeframe": {},
        "by_direction": {},
        "monthly_trend": {},
        "prediction_gap": {"sum_predicted": 0.0, "sum_actual": 0.0, "count": 0},
        "mfe_stats": {"reached_05r": 0, "total_with_mfe": 0, "mfe_sum": 0.0},
        "stop_timing": {"total_stops": 0, "fast_stops": 0, "candles_sum": 0},
        "target_stats": {"t1_hits": 0, "t2_hits": 0},
        "processed_run_tags": [],
    }


def _increment_bucket(bucket, key, result):
    """Increment a stats bucket (by_setup_type, by_confidence, etc.) with one result."""
    if key not in bucket:
        bucket[key] = {"wins": 0, "losses": 0, "total": 0, "rr_sum": 0.0}
    bucket[key]["total"] += 1
    bucket[key]["rr_sum"] += result.get("actual_rr", 0)
    if result.get("won"):
        bucket[key]["wins"] += 1
    else:
        bucket[key]["losses"] += 1


def update_lifetime_stats(all_evals):
    """Incrementally update lifetime_stats.json with only new evaluation data.

    On first run, bootstraps from all existing evals. On subsequent runs,
    only processes run_tags not yet in processed_run_tags.
    """
    PERFORMANCE_DIR.mkdir(parents=True, exist_ok=True)

    # Load existing stats or start fresh
    if LIFETIME_STATS_FILE.exists():
        try:
            stats = json.loads(LIFETIME_STATS_FILE.read_text(encoding="utf-8"))
        except Exception:
            stats = _empty_lifetime_stats()
    else:
        stats = _empty_lifetime_stats()

    processed = set(stats.get("processed_run_tags", []))

    new_count = 0
    for ev in all_evals:
        run_tag = ev["run_tag"]
        if run_tag in processed:
            continue

        model = ev.get("model", "unknown")
        # Extract month from run_tag (format: YYYYMMDD_HHMM)
        month_key = f"{run_tag[:4]}-{run_tag[4:6]}" if len(run_tag) >= 6 else "unknown"

        if month_key not in stats["monthly_trend"]:
            stats["monthly_trend"][month_key] = {"wins": 0, "losses": 0, "total": 0}

        for r in ev["results"]:
            stats["total_setups"] += 1

            if r.get("status") == "not_triggered":
                stats["total_not_triggered"] += 1
                continue

            if r.get("status") != "evaluated":
                continue

            stats["total_evaluated"] += 1
            actual_rr = r.get("actual_rr", 0)
            won = r.get("won", False)

            # Overall
            stats["overall"]["rr_sum"] += actual_rr
            if won:
                stats["overall"]["wins"] += 1
            else:
                stats["overall"]["losses"] += 1

            # Bucketed stats
            _increment_bucket(stats["by_setup_type"], r.get("setup_type", "other"), r)
            _increment_bucket(stats["by_confidence"], r.get("confidence", "medium"), r)
            _increment_bucket(stats["by_rank"], str(r.get("rank", 0)), r)
            _increment_bucket(stats["by_model"], model, r)
            _increment_bucket(stats["by_timeframe"], r.get("timeframe", "intraday"), r)
            _increment_bucket(stats["by_direction"], r.get("direction", "long"), r)

            # Monthly trend
            stats["monthly_trend"][month_key]["total"] += 1
            if won:
                stats["monthly_trend"][month_key]["wins"] += 1
            else:
                stats["monthly_trend"][month_key]["losses"] += 1

            # Prediction gap
            pred_rr = r.get("predicted_rr", 0)
            if pred_rr:
                stats["prediction_gap"]["sum_predicted"] += pred_rr
                stats["prediction_gap"]["sum_actual"] += actual_rr
                stats["prediction_gap"]["count"] += 1

            # MFE stats
            mfe = r.get("max_favorable_rr")
            if mfe is not None:
                stats["mfe_stats"]["total_with_mfe"] += 1
                stats["mfe_stats"]["mfe_sum"] += mfe
                if mfe >= 0.5:
                    stats["mfe_stats"]["reached_05r"] += 1

            # Stop timing
            if r.get("stop_hit") and r.get("candles_to_exit") is not None:
                stats["stop_timing"]["total_stops"] += 1
                stats["stop_timing"]["candles_sum"] += r["candles_to_exit"]
                if r["candles_to_exit"] <= 8:
                    stats["stop_timing"]["fast_stops"] += 1

            # Target stats
            if r.get("target_1_hit"):
                stats["target_stats"]["t1_hits"] += 1
            if r.get("target_2_hit"):
                stats["target_stats"]["t2_hits"] += 1

        processed.add(run_tag)
        new_count += 1

    stats["processed_run_tags"] = sorted(processed)
    stats["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    LIFETIME_STATS_FILE.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(f"Lifetime stats updated: {new_count} new run(s) processed, "
          f"{stats['total_evaluated']} total evaluated trades.")


def generate_strategic_rules():
    """Derive compact, durable rules from lifetime_stats.json.

    These rules are what Claude reads every run — the distilled wisdom from
    all historical evaluations. ~500 tokens regardless of how long you've run.
    """
    if not LIFETIME_STATS_FILE.exists():
        return

    stats = json.loads(LIFETIME_STATS_FILE.read_text(encoding="utf-8"))
    total = stats["total_evaluated"]
    if total < 5:
        return  # not enough data

    overall = stats["overall"]
    win_rate = overall["wins"] / total * 100
    avg_rr = overall["rr_sum"] / total

    lines = [
        f"# Strategic Rules (derived from {total} evaluated trades)",
        f"_Last updated: {stats['last_updated']}_",
        "",
    ]

    # --- Overall selectivity ---
    if win_rate < 20:
        lines.append(
            f"1. **CRITICAL SELECTIVITY**: Win rate is {win_rate:.0f}% — nearly all setups lose. "
            "Output 1-2 high-quality setups MAX. Fewer is better. 0 setups is valid."
        )
    elif win_rate < 40:
        lines.append(
            f"1. **SELECTIVITY**: Win rate is {win_rate:.0f}%. Apply strict entry criteria — "
            "prefer fewer, higher-conviction setups. 1-3 setups per run."
        )
    else:
        lines.append(
            f"1. **MAINTAIN APPROACH**: Win rate is {win_rate:.0f}%. Current selectivity is working."
        )

    rule_num = 2

    # --- Confidence rules ---
    for conf in ["medium", "low"]:
        cs = stats["by_confidence"].get(conf)
        if cs and cs["total"] >= 3:
            wr = cs["wins"] / cs["total"] * 100
            if wr < 20:
                lines.append(
                    f"{rule_num}. **{conf.upper()} CONFIDENCE BANNED**: {cs['wins']}/{cs['total']} wins ({wr:.0f}%). "
                    f"DO NOT include '{conf}' confidence setups unless R:R >= 3:1."
                )
                rule_num += 1

    # --- Setup type rules ---
    best_type = None
    best_type_wr = 0
    for st, s in stats["by_setup_type"].items():
        if s["total"] >= 3:
            wr = s["wins"] / s["total"] * 100
            avg = s["rr_sum"] / s["total"]
            if wr > best_type_wr:
                best_type = st
                best_type_wr = wr
            if wr < 15 and avg < -0.5 and s["total"] >= 5:
                lines.append(
                    f"{rule_num}. **DEPRIORITIZE '{st}'**: {wr:.0f}% WR, {avg:.2f} avg R:R over "
                    f"{s['total']} trades. Only include if 4/4 TF confluence + high confidence."
                )
                rule_num += 1
    if best_type and best_type_wr >= 30:
        lines.append(
            f"{rule_num}. **BEST TYPE: '{best_type}'**: {best_type_wr:.0f}% WR — prioritize this setup type."
        )
        rule_num += 1

    # --- Rank padding rule ---
    low_rank_total = sum(
        s["total"] for rk, s in stats["by_rank"].items() if int(rk) >= 4
    )
    low_rank_wins = sum(
        s["wins"] for rk, s in stats["by_rank"].items() if int(rk) >= 4
    )
    if low_rank_total >= 4:
        lr_wr = low_rank_wins / low_rank_total * 100
        if lr_wr < 15:
            lines.append(
                f"{rule_num}. **STOP PADDING**: Rank #4-5 have {low_rank_wins}/{low_rank_total} wins ({lr_wr:.0f}%). "
                "Don't pad to 5 setups. Only include #4/#5 if they genuinely qualify."
            )
            rule_num += 1

    # --- Prediction accuracy ---
    pg = stats["prediction_gap"]
    if pg["count"] >= 5:
        avg_pred = pg["sum_predicted"] / pg["count"]
        avg_act = pg["sum_actual"] / pg["count"]
        gap = avg_pred - avg_act
        if gap > 1.5:
            lines.append(
                f"{rule_num}. **TARGETS TOO FAR**: Predicted avg {avg_pred:.1f}R but actual is {avg_act:.2f}R "
                f"(gap: {gap:.1f}R). Use T1 limits strictly: scalp <1.5%, intraday <3%, swing <5%."
            )
            rule_num += 1

    # --- Direction accuracy (MFE) ---
    mfe = stats["mfe_stats"]
    if mfe["total_with_mfe"] >= 5:
        dir_acc = mfe["reached_05r"] / mfe["total_with_mfe"] * 100
        avg_mfe = mfe["mfe_sum"] / mfe["total_with_mfe"]
        if dir_acc >= 50 and win_rate < 30:
            lines.append(
                f"{rule_num}. **DIRECTION RIGHT, EXECUTION WRONG**: {dir_acc:.0f}% reach 0.5R+ favorable "
                f"(avg MFE: {avg_mfe:.2f}R) but win rate is {win_rate:.0f}%. "
                "Widen stops, bring T1 closer."
            )
            rule_num += 1
        elif dir_acc < 40:
            lines.append(
                f"{rule_num}. **DIRECTION WRONG**: Only {dir_acc:.0f}% reach 0.5R favorable. "
                "Require 4/4 TF confluence + volume confirmation before recommending."
            )
            rule_num += 1

    # --- Stop loss analysis ---
    if total >= 5:
        stop_rate = sum(
            s["losses"] for s in stats["by_setup_type"].values()
        )  # losses ≈ stops in most cases
        st = stats["stop_timing"]
        if st["total_stops"] >= 3 and st["fast_stops"] > st["total_stops"] * 0.4:
            avg_candles = st["candles_sum"] / st["total_stops"]
            lines.append(
                f"{rule_num}. **ENTRY TIMING**: {st['fast_stops']}/{st['total_stops']} stops hit within "
                f"2 hours (avg {avg_candles:.0f} candles). Wait for 15m confirmation before entering."
            )
            rule_num += 1

    # --- Target hit rate ---
    ts = stats["target_stats"]
    if total >= 5 and ts["t1_hits"] < total * 0.3:
        lines.append(
            f"{rule_num}. **T1 RARELY HIT**: Only {ts['t1_hits']}/{total} setups hit T1. "
            "Targets are set too far. Use closer, more realistic T1 levels."
        )
        rule_num += 1

    # --- Monthly trend ---
    months = sorted(stats["monthly_trend"].keys())
    if len(months) >= 2:
        last_month = stats["monthly_trend"][months[-1]]
        prev_month = stats["monthly_trend"][months[-2]]
        if last_month["total"] >= 3 and prev_month["total"] >= 3:
            last_wr = last_month["wins"] / last_month["total"] * 100
            prev_wr = prev_month["wins"] / prev_month["total"] * 100
            if last_wr > prev_wr:
                lines.append(
                    f"{rule_num}. **IMPROVING**: {months[-2]} was {prev_wr:.0f}% → {months[-1]} is {last_wr:.0f}%. "
                    "Current approach is working — maintain selectivity."
                )
            elif last_wr <= prev_wr and last_wr < 30:
                lines.append(
                    f"{rule_num}. **NOT IMPROVING**: {months[-2]} was {prev_wr:.0f}% → {months[-1]} is {last_wr:.0f}%. "
                    "Make bigger changes: output fewer setups, require higher confluence."
                )
            rule_num += 1

    # --- Model comparison ---
    model_stats = stats["by_model"]
    models_with_data = {m: s for m, s in model_stats.items() if s["total"] >= 5}
    if len(models_with_data) >= 2:
        best_model = max(models_with_data.items(), key=lambda x: x[1]["wins"] / x[1]["total"])
        bm_wr = best_model[1]["wins"] / best_model[1]["total"] * 100
        bm_rr = best_model[1]["rr_sum"] / best_model[1]["total"]
        lines.append(
            f"{rule_num}. **BEST MODEL**: {best_model[0]} ({bm_wr:.0f}% WR, {bm_rr:.2f} avg R:R). "
            "Consider using this model for production runs."
        )
        rule_num += 1

    lines.append("")
    STRATEGIC_RULES_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"Strategic rules written ({rule_num - 1} rules) to {STRATEGIC_RULES_FILE}")


def generate_recent_performance(all_evals):
    """Generate a rolling-window recent performance summary for Claude.

    Shows trade-by-trade outcomes from the last RECENT_WINDOW_WEEKS weeks.
    Fixed size regardless of total history — ~800 tokens.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(weeks=RECENT_WINDOW_WEEKS)

    # Collect recent evaluated results
    recent_results = []
    for ev in all_evals:
        try:
            run_dt = datetime.fromisoformat(ev["run_timestamp_utc"])
        except Exception:
            continue
        if run_dt < cutoff:
            continue
        model = ev.get("model", "unknown")
        for r in ev["results"]:
            if r.get("status") == "evaluated":
                r["run_tag"] = ev["run_tag"]
                r["model"] = model
                recent_results.append(r)

    if not recent_results:
        RECENT_PERFORMANCE_FILE.write_text(
            "# Recent Performance\nNo evaluated trades in the last "
            f"{RECENT_WINDOW_WEEKS} weeks.\n",
            encoding="utf-8",
        )
        return

    wins = [r for r in recent_results if r.get("won")]
    losses = [r for r in recent_results if not r.get("won")]
    win_rate = len(wins) / len(recent_results) * 100
    avg_rr = sum(r.get("actual_rr", 0) for r in recent_results) / len(recent_results)

    lines = [
        f"# Recent Performance (last {RECENT_WINDOW_WEEKS} weeks)",
        f"_{len(recent_results)} trades: {len(wins)}W / {len(losses)}L "
        f"({win_rate:.0f}% WR, {avg_rr:.2f} avg R:R)_",
        "",
        "## Trade-by-Trade (LEARN FROM EACH ONE)",
        "| Date | Symbol | Dir | TF | Type | Conf | TF-Conf | Pred R:R | Actual R:R | Exit | MFE |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]

    # Show all recent trades (capped by the window, not by count)
    for r in sorted(recent_results, key=lambda x: x.get("run_tag", ""), reverse=True):
        tag = r.get("run_tag", "?")
        date_str = f"{tag[:4]}-{tag[4:6]}-{tag[6:8]}" if len(tag) >= 8 else tag
        sym = r.get("symbol", "?")[:10]
        d = "L" if r.get("direction") == "long" else "S"
        tf = r.get("timeframe", "?")[:5]
        st = r.get("setup_type", "?")[:12]
        conf = r.get("confidence", "?")[:3]
        tfc = r.get("tf_confluence", "?")
        pred = r.get("predicted_rr", "?")
        actual = r.get("actual_rr", "?")
        exit_r = r.get("exit_reason", "?")
        mfe = r.get("max_favorable_rr")
        mfe_str = f"{mfe}R" if mfe is not None else "n/a"
        icon = "W" if r.get("won") else "L"
        lines.append(
            f"| {date_str} | {sym} | {d} | {tf} | {st} | {conf} | {tfc}/4 "
            f"| {pred} | {actual} ({icon}) | {exit_r} | {mfe_str} |"
        )

    # Recent patterns
    lines.append("")

    # Best/worst recent setup type
    recent_types = {}
    for r in recent_results:
        st = r.get("setup_type", "other")
        if st not in recent_types:
            recent_types[st] = {"wins": 0, "total": 0}
        recent_types[st]["total"] += 1
        if r.get("won"):
            recent_types[st]["wins"] += 1

    for st, s in recent_types.items():
        if s["total"] >= 2:
            wr = s["wins"] / s["total"] * 100
            lines.append(f"- Recent '{st}': {s['wins']}/{s['total']} ({wr:.0f}% WR)")

    # Manual trades context
    manual_trades = load_manual_trades()
    if manual_trades:
        # Only include recent manual trades
        recent_manual = []
        for t in manual_trades:
            t_date = t.get("date", "")
            try:
                if datetime.fromisoformat(t_date) >= cutoff:
                    recent_manual.append(t)
            except Exception:
                recent_manual.append(t)  # include if can't parse date

        if recent_manual:
            closed = [t for t in recent_manual if t.get("result") in ("win", "loss")]
            lines += [
                "",
                "## Trader's Recent Actual Trades",
            ]
            for t in recent_manual[-5:]:  # last 5 manual trades
                symbol = t.get("symbol", "?")
                result = t.get("result", "?").upper()
                note = t.get("note", "").strip()
                fr = t.get("failure_reason", "")
                lines.append(f"- **{symbol}** ({t.get('date', '?')}) — {result}")
                if note:
                    lines.append(f"  Lesson: {note}")
                if fr:
                    lines.append(f"  Failure: {fr}")

    lines.append("")
    RECENT_PERFORMANCE_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"Recent performance written ({len(recent_results)} trades) to {RECENT_PERFORMANCE_FILE}")


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

    # --- Win rate history: load previous snapshots ---
    win_rate_history = []
    if WIN_RATE_HISTORY_FILE.exists():
        try:
            win_rate_history = json.loads(WIN_RATE_HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            win_rate_history = []

    # Compute per-run win rates for trend display
    per_run_stats = {}
    for r in evaluated:
        tag = r.get("run_tag", "unknown")
        if tag not in per_run_stats:
            per_run_stats[tag] = {"wins": 0, "losses": 0, "total": 0}
        per_run_stats[tag]["total"] += 1
        if r["won"]:
            per_run_stats[tag]["wins"] += 1
        else:
            per_run_stats[tag]["losses"] += 1

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
    # Determine previous win rate from history for comparison
    prev_wr_str = ""
    if win_rate_history:
        prev = win_rate_history[-1]
        prev_wr = prev["win_rate"]
        delta = win_rate - prev_wr
        if delta > 0:
            prev_wr_str = f"  (**↑ {delta:+.1f}%** from previous eval: {prev_wr:.1f}%)"
        elif delta < 0:
            prev_wr_str = f"  (**↓ {delta:+.1f}%** from previous eval: {prev_wr:.1f}%) ⚠️ REGRESSION"
        else:
            prev_wr_str = f"  (unchanged from previous eval: {prev_wr:.1f}%) ⚠️ NO IMPROVEMENT"

    lines = [
        "# Performance Summary",
        f"_Last updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_",
        f"_Total runs evaluated: {len(all_evals)}_",
        "",
        "## Overall Stats",
        f"- Total setups: {total}",
        f"- Triggered: {len(evaluated)} ({len(evaluated)/total*100:.0f}%)" if total else "",
        f"- Not triggered: {len(not_triggered)}",
        f"- **Win rate: {win_rate:.1f}%** ({len(wins)}W / {len(losses)}L){prev_wr_str}",
        f"- Avg actual R:R: {avg_rr:.2f}",
        f"- Avg winning R:R: {avg_win_rr:.2f}",
        f"- Avg losing R:R: {avg_loss_rr:.2f}",
        "",
        "## Win Rate Trend (per eval run)",
        "This tracks whether recommendations are IMPROVING over time. If not trending up, something needs to change.",
        "",
        "| Run Date | Setups | W | L | Run Win Rate | Cumulative Win Rate |",
        "|---|---|---|---|---|---|",
    ]

    # Add per-run rows chronologically with running cumulative win rate
    cum_wins = 0
    cum_total = 0
    for tag in sorted(per_run_stats.keys()):
        s = per_run_stats[tag]
        cum_wins += s["wins"]
        cum_total += s["total"]
        run_wr = s["wins"] / s["total"] * 100 if s["total"] else 0
        cum_wr = cum_wins / cum_total * 100 if cum_total else 0
        date_str = f"{tag[:4]}-{tag[4:6]}-{tag[6:8]}" if len(tag) >= 8 else tag
        lines.append(f"| {date_str} | {s['total']} | {s['wins']} | {s['losses']} | {run_wr:.0f}% | {cum_wr:.1f}% |")

    # Flag if no improvement trend
    sorted_tags = sorted(per_run_stats.keys())
    if len(sorted_tags) >= 3:
        # Check last 3 runs
        recent_runs = sorted_tags[-3:]
        recent_wrs = []
        for tag in recent_runs:
            s = per_run_stats[tag]
            recent_wrs.append(s["wins"] / s["total"] * 100 if s["total"] else 0)
        if all(wr == 0 for wr in recent_wrs):
            lines.append("")
            lines.append("**⚠️ ALERT: Last 3 runs have 0% win rate. The current approach is NOT working. "
                         "Major changes needed: tighter setup criteria, wider stops, closer targets, "
                         "or fewer setups per run.**")
        elif len(recent_wrs) >= 2 and recent_wrs[-1] <= recent_wrs[0]:
            lines.append("")
            lines.append("**⚠️ Win rate is NOT improving across recent runs. "
                         "Review what changed and whether the feedback loop is being followed.**")

    lines += [
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

    # --- Per-trade prediction vs reality table ---
    # This is the KEY learning signal: Claude sees each individual trade outcome.
    # Show last 20 evaluated trades so Claude can spot specific patterns.
    recent_evaluated = sorted(evaluated, key=lambda r: r.get("run_tag", ""), reverse=True)[:20]
    if recent_evaluated:
        lines += [
            "",
            "## Your Predictions vs Reality (LEARN FROM EACH ONE)",
            "Each row is a setup YOU recommended. Study the gap between predicted and actual R:R.",
            "",
            "| Date | Symbol | Dir | TF | Conf | TF-Conf | Pred R:R | Actual R:R | Exit | MFE |",
            "|---|---|---|---|---|---|---|---|---|---|",
        ]
        for r in recent_evaluated:
            tag = r.get("run_tag", "?")
            date_str = f"{tag[:4]}-{tag[4:6]}-{tag[6:8]}" if len(tag) >= 8 else tag
            sym = r.get("symbol", "?")[:8]  # truncate for table width
            d = "L" if r.get("direction") == "long" else "S"
            tf = r.get("timeframe", "?")[:5]
            conf = r.get("confidence", "?")[:3]
            tfc = r.get("tf_confluence", "?")
            pred = r.get("predicted_rr", "?")
            actual = r.get("actual_rr", "?")
            exit_r = r.get("exit_reason", "?")
            mfe = r.get("max_favorable_rr")
            mfe_str = f"{mfe}R" if mfe is not None else "n/a"
            lines.append(f"| {date_str} | {sym} | {d} | {tf} | {conf} | {tfc}/4 | {pred} | {actual} | {exit_r} | {mfe_str} |")

        # Prediction accuracy gap
        pred_rrs = [r.get("predicted_rr", 0) for r in evaluated if r.get("predicted_rr")]
        actual_rrs = [r.get("actual_rr", 0) for r in evaluated]
        if pred_rrs:
            avg_pred = sum(pred_rrs) / len(pred_rrs)
            avg_act = sum(actual_rrs) / len(actual_rrs)
            lines.append(f"")
            lines.append(f"**Prediction gap: avg predicted R:R = {avg_pred:.1f}, avg actual = {avg_act:.2f} (gap of {avg_pred - avg_act:.1f}R)**")

        # Direction accuracy using MFE
        mfe_results = [r for r in evaluated if r.get("max_favorable_rr") is not None]
        if mfe_results:
            direction_right = [r for r in mfe_results if r["max_favorable_rr"] >= 0.5]
            dir_acc = len(direction_right) / len(mfe_results) * 100
            avg_mfe = sum(r["max_favorable_rr"] for r in mfe_results) / len(mfe_results)
            lines.append(f"**Direction accuracy: {len(direction_right)}/{len(mfe_results)} ({dir_acc:.0f}%) reached 0.5R+ favorable. Avg MFE: {avg_mfe:.2f}R**")
            if dir_acc >= 50 and win_rate < 30:
                lines.append("**DIAGNOSIS: Direction is often right but stops are too tight or targets too far. Focus on WIDER STOPS and CLOSER TARGETS.**")
            elif dir_acc < 40:
                lines.append("**DIAGNOSIS: Direction calls are wrong most of the time. Be far more selective — only trade when multi-TF confluence is 4/4.**")

        # Quick stop analysis — how fast stops are hit
        quick_stops = [r for r in evaluated if r.get("stop_hit") and r.get("candles_to_exit") is not None]
        if quick_stops:
            avg_candles = sum(r["candles_to_exit"] for r in quick_stops) / len(quick_stops)
            fast_stops = [r for r in quick_stops if r["candles_to_exit"] <= 8]  # <= 2 hours on 15m
            if fast_stops and len(fast_stops) > len(quick_stops) * 0.4:
                lines.append(
                    f"**ENTRY TIMING: {len(fast_stops)}/{len(quick_stops)} stop-outs happened within 2 hours "
                    f"(avg {avg_candles:.0f} candles). Entries are too early — wait for confirmation on 15m before entering.**"
                )

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

    if win_rate < 20:
        lines.append(
            f"- CRITICAL: Win rate is {win_rate:.0f}% — nearly all setups lose. "
            "REDUCE quantity: only recommend setups with 4/4 TF confluence or high confidence. "
            "1-2 high-quality setups is better than 5 mediocre ones."
        )
    elif win_rate < 40:
        lines.append(
            f"- WARNING: Win rate is {win_rate:.0f}% (below 40%). "
            "Apply stricter entry criteria — prefer fewer, higher-conviction setups."
        )
    elif win_rate >= 50:
        lines.append("- Win rate is healthy. Maintain current setup selection approach.")

    # Target distance analysis — check if targets are systematically too far
    t1_hits = [r for r in evaluated if r.get("target_1_hit")]
    t1_miss_losses = [r for r in evaluated if not r.get("target_1_hit") and r.get("stop_hit")]
    if len(evaluated) >= 5 and len(t1_hits) < len(evaluated) * 0.3:
        lines.append(
            f"- TARGET ISSUE: Only {len(t1_hits)}/{len(evaluated)} setups hit T1. "
            "Targets are set too far. Use closer, more realistic T1 levels."
        )

    # SL analysis — check if stops are hit too quickly
    stop_hits = [r for r in evaluated if r.get("stop_hit")]
    if len(evaluated) >= 5 and len(stop_hits) > len(evaluated) * 0.7:
        lines.append(
            f"- STOP LOSS ISSUE: {len(stop_hits)}/{len(evaluated)} setups hit stop loss. "
            "Stops may be too tight or entries too imprecise. Widen SL or wait for better entries."
        )

    # Avg R:R analysis
    if avg_rr < -0.5:
        lines.append(
            f"- R:R ISSUE: Average actual R:R is {avg_rr:.2f}. "
            "Losses are large relative to wins. Tighten targets and/or widen stops."
        )

    # Find best/worst setup types
    if setup_types:
        best = max(setup_types.items(), key=lambda x: (x[1]["wins"]/x[1]["count"]) if x[1]["count"] >= 3 else 0)
        worst = min(setup_types.items(), key=lambda x: (x[1]["wins"]/x[1]["count"]) if x[1]["count"] >= 3 else 1)
        if best[1]["count"] >= 3:
            lines.append(f"- Best setup type: **{best[0]}** ({best[1]['wins']}/{best[1]['count']} wins)")
        if worst[1]["count"] >= 3 and worst[0] != best[0]:
            wr = worst[1]["wins"] / worst[1]["count"] * 100
            lines.append(
                f"- Worst setup type: **{worst[0]}** ({worst[1]['wins']}/{worst[1]['count']} wins, {wr:.0f}%) "
                "— deprioritize unless 4/4 TF confluence"
            )

    # Confidence calibration check
    high_stats = confidence_stats.get("high", {"wins": 0, "count": 0})
    med_stats = confidence_stats.get("medium", {"wins": 0, "count": 0})
    low_stats = confidence_stats.get("low", {"wins": 0, "count": 0})

    if med_stats["count"] >= 3:
        med_wr = med_stats["wins"] / med_stats["count"] * 100
        if med_wr < 20:
            lines.append(
                f"- MEDIUM CONFIDENCE FAILING: {med_stats['wins']}/{med_stats['count']} wins ({med_wr:.0f}%). "
                "Stop recommending medium-confidence setups unless R:R >= 3:1."
            )

    if low_stats["count"] >= 3:
        low_wr = low_stats["wins"] / low_stats["count"] * 100
        if low_wr < 20:
            lines.append(
                f"- LOW CONFIDENCE FAILING: {low_stats['wins']}/{low_stats['count']} wins ({low_wr:.0f}%). "
                "Do NOT include low-confidence setups."
            )

    if high_stats["count"] >= 3 and med_stats["count"] >= 3:
        high_wr = high_stats["wins"] / high_stats["count"]
        med_wr_ratio = med_stats["wins"] / med_stats["count"]
        if high_wr <= med_wr_ratio:
            lines.append("- CALIBRATION ISSUE: 'High' confidence setups don't outperform 'Medium'. Recalibrate confidence scoring.")
        elif high_wr > 0.4:
            lines.append("- Confidence calibration looks good: High > Medium win rates.")

    # Rank-based insight
    low_rank_count = sum(s["count"] for rk, s in rank_stats.items() if rk >= 4)
    low_rank_wins = sum(s["wins"] for rk, s in rank_stats.items() if rk >= 4)
    if low_rank_count >= 4:
        low_rank_wr = low_rank_wins / low_rank_count * 100
        if low_rank_wr < 15:
            lines.append(
                f"- RANK #4-5 FAILING: {low_rank_wins}/{low_rank_count} wins ({low_rank_wr:.0f}%). "
                "These are filler setups. Recommend fewer, better setups instead of padding to 5."
            )

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

    # --- Save win rate history snapshot ---
    # Each eval run appends a snapshot so we can track improvement over time.
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    snapshot = {
        "date": now_str,
        "total_evaluated": len(evaluated),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(win_rate, 1),
        "avg_rr": round(avg_rr, 2),
    }
    # Only append if different from last snapshot (avoid duplicates from re-runs
    # that didn't add new evaluations)
    if not win_rate_history or win_rate_history[-1]["total_evaluated"] != len(evaluated):
        win_rate_history.append(snapshot)
        WIN_RATE_HISTORY_FILE.write_text(json.dumps(win_rate_history, indent=2), encoding="utf-8")
        print(f"Win rate history updated: {len(win_rate_history)} snapshots")


if __name__ == "__main__":
    print("=" * 50)
    print("Crypto Screener — Weekly Evaluation")
    print("=" * 50)
    run_evaluation()
