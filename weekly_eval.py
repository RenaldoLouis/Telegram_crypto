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

import anthropic
from pybit.unified_trading import HTTP
import config


# How many days to look forward for each timeframe
# Swing removed — system now only recommends scalp/intraday.
# Legacy swing setups fall through to the default (2 days) in the eval logic.
EVAL_WINDOWS = {
    "scalp": 1,
    "intraday": 2,
}

SETUPS_DIR = Path("logs/setups")
EVALS_DIR = Path("logs/evaluations")
PERFORMANCE_DIR = Path("logs/performance")
TRADES_FILE = Path("logs/trades/my_trades.json")
WIN_RATE_HISTORY_FILE = Path("logs/performance/win_rate_history.json")
LIFETIME_STATS_FILE = Path("logs/performance/lifetime_stats.json")
STRATEGIC_RULES_FILE = Path("logs/performance/strategic_rules.md")
RECENT_PERFORMANCE_FILE = Path("logs/performance/recent_performance.md")
DELTA_REGISTRY_FILE = Path("logs/performance/rule_registry.json")

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
    # Models realistic position management (v10 — +0.3R trail):
    #   - Before T1 and before 1R MFE: original stop applies.
    #   - Once price runs 1.0R in favor: stop tightens to +0.3R (lock a partial
    #     gain) so structural winners aren't given back to zero. This replaces
    #     the old "return all the way to breakeven" behavior — backtest showed
    #     many trades reached 1.0-2.2R MFE then reversed to a 0R exit.
    #   - Once T1 is hit but MFE < 1R: stop moves to breakeven.
    #   - Partial profit: 50% closed at T1, remaining 50% trails with this stop.
    # The trail decision uses MFE as of PRIOR candles only (no intracandle
    # look-ahead — a candle cannot both reach 1R and honor the +0.3R stop).
    LOCK_TRIGGER_RR = 1.0   # once MFE reaches this...
    LOCK_STOP_RR = 0.3      # ...move the stop to +this many R
    stop_hit = False
    t1_hit = False
    t2_hit = False
    be_stop_hit = False     # breakeven stop hit after T1 (MFE stayed < 1R)
    trail_stop_hit = False  # +0.3R trail stop hit after 1R MFE
    exit_price = None
    exit_reason = None
    risk = abs(entry_price - stop_loss)
    max_favorable_rr = 0.0  # best R:R reached before exit
    candles_to_exit = 0

    for c in candles[entry_candle_idx:]:
        candles_to_exit += 1
        mfe_prior = max_favorable_rr  # MFE known entering this candle

        # Track MFE with this candle
        if risk > 0:
            if direction == "long":
                favorable = (c["high"] - entry_price) / risk
            else:
                favorable = (entry_price - c["low"]) / risk
            max_favorable_rr = max(max_favorable_rr, favorable)

        # Effective protective stop for this candle, most-protective first.
        if mfe_prior >= LOCK_TRIGGER_RR:
            protect_reason = "trail_stop"
            protect = (entry_price + LOCK_STOP_RR * risk) if direction == "long" \
                else (entry_price - LOCK_STOP_RR * risk)
        elif t1_hit:
            protect_reason = "be_stop"
            protect = entry_price
        else:
            protect_reason = "stop_loss"
            protect = stop_loss

        if direction == "long":
            if c["low"] <= protect:
                exit_price = protect
                exit_reason = protect_reason
                stop_hit = protect_reason == "stop_loss"
                be_stop_hit = protect_reason == "be_stop"
                trail_stop_hit = protect_reason == "trail_stop"
                break
            if not t1_hit and c["high"] >= target_1:
                t1_hit = True
            if target_2 and c["high"] >= target_2:
                t2_hit = True
                exit_price = target_2
                exit_reason = "target_2"
                break
        else:  # short
            if c["high"] >= protect:
                exit_price = protect
                exit_reason = protect_reason
                stop_hit = protect_reason == "stop_loss"
                be_stop_hit = protect_reason == "be_stop"
                trail_stop_hit = protect_reason == "trail_stop"
                break
            if not t1_hit and c["low"] <= target_1:
                t1_hit = True
            if target_2 and c["low"] <= target_2:
                t2_hit = True
                exit_price = target_2
                exit_reason = "target_2"
                break

    # If no definitive exit, determine outcome
    if not stop_hit and not be_stop_hit and not trail_stop_hit and not t2_hit:
        if t1_hit:
            exit_price = target_1
            exit_reason = "target_1"
        else:
            # Use last candle close as "still open" or expired
            exit_price = candles[-1]["close"]
            exit_reason = "expired"

    # Calculate actual R:R (raw, without partial profit model)
    if risk == 0:
        actual_rr = 0
    else:
        if direction == "long":
            actual_rr = round((exit_price - entry_price) / risk, 2)
        else:
            actual_rr = round((entry_price - exit_price) / risk, 2)

    won = actual_rr > 0

    # Partial profit model (blended R:R):
    # 50% of position closed at T1 if hit, remaining 50% trails with BE stop.
    # This models realistic trading where you take partial at T1 and let rest run.
    if risk > 0:
        t1_rr = 0.0
        if direction == "long":
            t1_rr = (target_1 - entry_price) / risk
        else:
            t1_rr = (entry_price - target_1) / risk

        if t1_hit:
            # 50% closed at T1 + 50% at final exit
            blended_rr = round(0.5 * t1_rr + 0.5 * actual_rr, 2)
        else:
            # T1 never hit — full position exits at actual price
            blended_rr = actual_rr
    else:
        blended_rr = 0

    # Simulated closer-T1 backtest: would tighter targets have won?
    # Check if T1 at 0.75R and 1.0R from entry would have been hit before stop.
    sim_t1_075r = False
    sim_t1_100r = False
    if risk > 0 and entry_candle_idx is not None:
        t1_at_075r = entry_price + (0.75 * risk) if direction == "long" else entry_price - (0.75 * risk)
        t1_at_100r = entry_price + (1.0 * risk) if direction == "long" else entry_price - (1.0 * risk)
        for c in candles[entry_candle_idx:]:
            if direction == "long":
                if c["low"] <= stop_loss:
                    break  # stop hit first
                if c["high"] >= t1_at_075r:
                    sim_t1_075r = True
                if c["high"] >= t1_at_100r:
                    sim_t1_100r = True
                    break  # both checked
            else:
                if c["high"] >= stop_loss:
                    break
                if c["low"] <= t1_at_075r:
                    sim_t1_075r = True
                if c["low"] <= t1_at_100r:
                    sim_t1_100r = True
                    break

    return {
        "status": "evaluated",
        "entry_triggered": True,
        "entry_price": round(entry_price, 6),
        "exit_price": round(exit_price, 6),
        "exit_reason": exit_reason,
        "target_1_hit": t1_hit,
        "target_2_hit": t2_hit,
        "stop_hit": stop_hit,
        "be_stop_hit": be_stop_hit,
        "trail_stop_hit": trail_stop_hit,
        "actual_rr": actual_rr,
        "blended_rr": blended_rr,
        "won": won,
        "max_favorable_rr": round(max_favorable_rr, 2),
        "candles_to_exit": candles_to_exit,
        "sim_t1_075r_hit": sim_t1_075r,
        "sim_t1_100r_hit": sim_t1_100r,
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

            # Find already-evaluated (symbol, source) pairs for this run (from partial
            # eval). Keyed on BOTH because one run can now carry the same symbol from
            # mechanical AND claude — keying on symbol alone would drop one source's
            # copy and corrupt the head-to-head. audit 2026-07-21
            existing_eval = next((e for e in all_evals if e["run_tag"] == run_tag), None)
            already_evaluated = set()
            if existing_eval:
                already_evaluated = {(r["symbol"], r.get("source", "claude"))
                                     for r in existing_eval["results"]}

            eval_results = []

            for setup in setups:
                symbol = setup["symbol"]

                # Skip if already evaluated in a previous partial run
                if (symbol, setup.get("source", "claude")) in already_evaluated:
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
                # Self-learning: capture reasoning for rule-level attribution
                result["rules_applied"] = setup.get("reasoning", {}).get("rules_applied", [])
                # Stamp regime per-result (was only on the wrapper → per-trade regime analysis
                # was unreliable). Prefer per-setup regime, fall back to file-level. audit 2026-07-13
                result["regime"] = setup.get("regime") or record.get("regime", "neutral")
                # Capture pre-filter interest score for selection-quality correlation.
                result["interest_score"] = setup.get("interest_score")
                # Head-to-head: which engine produced this setup (mechanical vs claude),
                # and whether a backtest-validated signal actually backed it. Old
                # Claude-only records have no source → default "claude". audit 2026-07-21
                result["source"] = setup.get("source", "claude")
                result["backtested_signal"] = setup.get("entry_indicators", {}).get("backtested_signal")
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
                    "regime": record.get("regime", "neutral"),
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
    # Head-to-head: mechanical vs Claude (human-only report)
    generate_head_to_head(all_evals)

    # --- Phase 4: Self-learning delta analysis ---
    # Auto-triggers every N new evaluated trades. Finds patterns,
    # checks if previous insights helped, generates ACTION rules.
    maybe_run_delta_analysis(all_evals)


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
        "by_symbol": {},
        "by_regime": {},
        "by_confluence": {},
        "by_rule_applied": {},
        "by_source": {},          # mechanical vs claude (head-to-head)
        "by_signal_backed": {},   # signal_backed vs discretionary
        "simulated_t1": {"sim_075r_hits": 0, "sim_100r_hits": 0, "sim_total": 0},
        "partial_profit": {
            "blended_rr_sum": 0.0,
            "blended_wins": 0,
            "blended_losses": 0,
            "be_stops": 0,
            "trail_stops": 0,
            "t1_then_t2": 0,
            "t1_then_be": 0,
            "t1_then_expire": 0,
        },
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


def _group_stats(results):
    """WR / expectancy / profit-factor for a list of evaluated result dicts."""
    n = len(results)
    if not n:
        return {"n": 0, "wr": 0.0, "exp": 0.0, "pf": 0.0, "wins": 0}
    rr = [r.get("actual_rr", 0) for r in results]
    wins = sum(1 for r in results if r.get("won"))
    gross_win = sum(x for x in rr if x > 0)
    gross_loss = abs(sum(x for x in rr if x < 0))
    pf = gross_win / gross_loss if gross_loss > 0 else (float("inf") if gross_win > 0 else 0.0)
    return {"n": n, "wr": wins / n * 100, "exp": sum(rr) / n, "pf": pf, "wins": wins}


def generate_head_to_head(all_evals):
    """Mechanical-vs-Claude head-to-head on WR / expectancy / profit factor (plus a
    signal-backed vs discretionary split). Writes logs/performance/head_to_head.md
    (human-only — NOT sent to Claude) and prints a one-line summary. This is the
    payoff of the shadow architecture: it answers 'does our mechanical logic beat
    Claude?' with our own evaluated trade data.
    """
    evaluated = [r for ev in all_evals for r in ev.get("results", [])
                 if r.get("status") == "evaluated"]
    if not evaluated:
        print("Head-to-head: no evaluated trades yet.")
        return

    def fmt_pf(pf):
        return "∞" if pf == float("inf") else f"{pf:.2f}"

    by_source, by_backed = {}, {}
    for r in evaluated:
        by_source.setdefault(r.get("source", "claude"), []).append(r)
        key = "signal_backed" if r.get("backtested_signal") else "discretionary"
        by_backed.setdefault(key, []).append(r)

    lines = ["# Head-to-Head: Mechanical vs Claude", "",
             f"Total evaluated trades: {len(evaluated)}", "",
             "## By source", "",
             "| source | n | win% | expectancy (R) | profit factor |",
             "|---|---|---|---|---|"]
    for src in sorted(by_source):
        s = _group_stats(by_source[src])
        lines.append(f"| {src} | {s['n']} | {s['wr']:.1f}% | {s['exp']:+.3f} | {fmt_pf(s['pf'])} |")

    lines += ["", "## By signal backing", "",
              "| backing | n | win% | expectancy (R) | profit factor |",
              "|---|---|---|---|---|"]
    for key in sorted(by_backed):
        s = _group_stats(by_backed[key])
        lines.append(f"| {key} | {s['n']} | {s['wr']:.1f}% | {s['exp']:+.3f} | {fmt_pf(s['pf'])} |")

    m, c = _group_stats(by_source.get("mechanical", [])), _group_stats(by_source.get("claude", []))
    lines += ["", "## Verdict"]
    if m["n"] >= 20 and c["n"] >= 20:
        lead = "Mechanical" if m["exp"] > c["exp"] else "Claude"
        lines.append(f"**{lead} LEADS on expectancy** "
                     f"(mechanical {m['exp']:+.3f}R vs claude {c['exp']:+.3f}R; "
                     f"n={m['n']}/{c['n']}).")
    else:
        lines.append(f"**INSUFFICIENT DATA** — need >=20 evaluated trades per source "
                     f"(mechanical={m['n']}, claude={c['n']}). Keep running the shadow.")

    PERFORMANCE_DIR.mkdir(parents=True, exist_ok=True)
    out = PERFORMANCE_DIR / "head_to_head.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Head-to-head → mechanical {m['n']}t {m['exp']:+.3f}R vs "
          f"claude {c['n']}t {c['exp']:+.3f}R  ({out})")


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

    # Ensure newer stat keys exist for backward compatibility
    if "by_symbol" not in stats:
        stats["by_symbol"] = {}
    if "by_regime" not in stats:
        stats["by_regime"] = {}
    if "by_confluence" not in stats:
        stats["by_confluence"] = {}
    if "by_rule_applied" not in stats:
        stats["by_rule_applied"] = {}
    if "by_source" not in stats:
        stats["by_source"] = {}
    if "by_signal_backed" not in stats:
        stats["by_signal_backed"] = {}
    if "simulated_t1" not in stats:
        stats["simulated_t1"] = {"sim_075r_hits": 0, "sim_100r_hits": 0, "sim_total": 0}
    if "partial_profit" not in stats:
        stats["partial_profit"] = {
            "blended_rr_sum": 0.0, "blended_wins": 0, "blended_losses": 0,
            "be_stops": 0, "trail_stops": 0, "t1_then_t2": 0, "t1_then_be": 0, "t1_then_expire": 0,
        }

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
            _increment_bucket(stats["by_symbol"], r.get("symbol", "unknown"), r)

            # Regime tracking (self-learning). Prefer per-result regime (audit 2026-07-13);
            # fall back to the eval wrapper for older records.
            regime = r.get("regime") or ev.get("regime", "neutral")
            _increment_bucket(stats["by_regime"], regime, r)

            # TF-confluence tracking. Data shows 3/4 is the edge and 4/4 is the WORST bucket
            # (exhaustion) — the opposite of the old "more confluence = more confidence" premise.
            conf_key = str(r.get("tf_confluence", 0))
            _increment_bucket(stats["by_confluence"], conf_key, r)

            # Rule-applied tracking (self-learning). Only count canonical rule IDs so
            # attribution is statistically meaningful (drops free-text one-off IDs).
            for rule_id in r.get("rules_applied", []):
                if rule_id in config.CANONICAL_RULES:
                    _increment_bucket(stats["by_rule_applied"], rule_id, r)

            # Head-to-head: mechanical vs claude, and signal-backed vs discretionary.
            _increment_bucket(stats["by_source"], r.get("source", "claude"), r)
            backed = "signal_backed" if r.get("backtested_signal") else "discretionary"
            _increment_bucket(stats["by_signal_backed"], backed, r)

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

            # Simulated closer-T1 stats
            if "simulated_t1" not in stats:
                stats["simulated_t1"] = {"sim_075r_hits": 0, "sim_100r_hits": 0, "sim_total": 0}
            if r.get("sim_t1_075r_hit") is not None:
                stats["simulated_t1"]["sim_total"] += 1
                if r.get("sim_t1_075r_hit"):
                    stats["simulated_t1"]["sim_075r_hits"] += 1
                if r.get("sim_t1_100r_hit"):
                    stats["simulated_t1"]["sim_100r_hits"] += 1

            # Partial profit tracking
            pp = stats["partial_profit"]
            blended = r.get("blended_rr")
            if blended is not None:
                pp["blended_rr_sum"] += blended
                if blended > 0:
                    pp["blended_wins"] += 1
                else:
                    pp["blended_losses"] += 1
            if r.get("be_stop_hit"):
                pp["be_stops"] += 1
            if r.get("trail_stop_hit"):
                pp["trail_stops"] = pp.get("trail_stops", 0) + 1
            if r.get("target_1_hit"):
                exit_r = r.get("exit_reason", "")
                if exit_r == "target_2":
                    pp["t1_then_t2"] += 1
                elif exit_r in ("be_stop", "trail_stop"):
                    pp["t1_then_be"] += 1
                elif exit_r in ("target_1", "expired"):
                    pp["t1_then_expire"] += 1

        processed.add(run_tag)
        new_count += 1

    stats["processed_run_tags"] = sorted(processed)
    stats["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    LIFETIME_STATS_FILE.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(f"Lifetime stats updated: {new_count} new run(s) processed, "
          f"{stats['total_evaluated']} total evaluated trades.")


def _version_validation_line(total, overall):
    """Report whether the latest deployed version is actually improving results.

    Reads logs/performance/version_markers.json. Compares cumulative performance
    SINCE the cutover trade count against the pre-cutover baseline. This closes the
    forward-validation loop automatically — the system flags itself if a change that
    looked good on backtest is NOT working on live trades (i.e. the bad-logic loop
    would be recurring). audit 2026-07-13
    """
    marker_file = PERFORMANCE_DIR / "version_markers.json"
    if not marker_file.exists():
        return None
    try:
        markers = json.loads(marker_file.read_text(encoding="utf-8")).get("markers", [])
    except Exception:
        return None
    if not markers:
        return None
    m = markers[-1]
    cutover = m.get("cutover_trade_count", 0)
    fwd_n = total - cutover
    ver = m.get("version", "latest")
    tgt = m.get("validation_target", {})
    min_trades = tgt.get("min_trades", 20)

    if fwd_n <= 0:
        return (f"0. **{ver} UNPROVEN (MONITOR)**: {ver} just deployed at {cutover} trades; "
                f"0 forward trades evaluated yet. Baseline was {m.get('baseline_wr')}% WR / "
                f"{m.get('baseline_expectancy')}R exp. ACTION: keep selecting per the rules below; "
                f"win rate is validated forward over the next {min_trades} trades, not asserted.")

    # Cumulative-since-cutover performance
    fwd_wins = overall["wins"] - m.get("baseline_wins", round(m.get("baseline_wr", 0) / 100 * cutover))
    fwd_wr = fwd_wins / fwd_n * 100 if fwd_n else 0
    fwd_exp = (overall["rr_sum"] - m.get("baseline_rr_sum", m.get("baseline_expectancy", 0) * cutover)) / fwd_n

    if fwd_n < min_trades:
        return (f"0. **{ver} VALIDATING ({fwd_n}/{min_trades} forward trades)**: so far "
                f"{fwd_wr:.0f}% WR / {fwd_exp:+.2f}R exp vs baseline {m.get('baseline_wr')}% / "
                f"{m.get('baseline_expectancy')}R. ACTION: too early to conclude — keep monitoring.")

    wr_tgt = tgt.get("wr_target", 34.0)
    exp_tgt = tgt.get("expectancy_target", 0.0)
    if fwd_wr >= wr_tgt and fwd_exp >= exp_tgt:
        return (f"0. **{ver} VALIDATED**: {fwd_n} forward trades at {fwd_wr:.0f}% WR / {fwd_exp:+.2f}R "
                f"exp (targets {wr_tgt:.0f}% / {exp_tgt:+.2f}R). The change is working — maintain it.")
    return (f"0. **{ver} NOT VALIDATING — REVIEW NEEDED**: {fwd_n} forward trades only reached "
            f"{fwd_wr:.0f}% WR / {fwd_exp:+.2f}R exp vs targets {wr_tgt:.0f}% / {exp_tgt:+.2f}R. "
            f"ACTION: the last change did NOT deliver — re-audit before adding more rules (do not "
            f"pile on new delta insights, that is how the bad-logic loop returns).")


def generate_strategic_rules():
    """Derive compact, prescriptive rules from lifetime_stats.json.

    These rules are what Claude reads every run — the distilled wisdom from
    all historical evaluations. ~600-800 tokens regardless of how long you've run.

    Rules are PRESCRIPTIVE (tell Claude exactly what to do), not just
    DESCRIPTIVE (tell Claude what's wrong). Each rule includes a specific
    actionable instruction.

    Sample size calibration:
    - <30 trades per category: ADVISORY only (note the small sample)
    - 30-50 trades: STRONG guidance
    - 50+ trades: HARD rules
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

    # Determine confidence tier based on total sample size
    if total >= 50:
        sample_label = "solid sample"
    elif total >= 30:
        sample_label = "moderate sample"
    else:
        sample_label = "small sample — treat all rules as advisory"

    lines = [
        f"# Strategic Rules (derived from {total} evaluated trades — {sample_label})",
        f"_Last updated: {stats['last_updated']}_",
        "",
    ]

    # --- Version self-validation: is the latest change actually working? ---
    val_line = _version_validation_line(total, overall)
    if val_line:
        lines.append(val_line)
        lines.append("")

    # --- Overall selectivity ---
    if win_rate < 20:
        lines.append(
            f"1. **SELECTIVITY NEEDED**: Win rate is {win_rate:.0f}% over {total} trades. "
            "ACTION: Output max 2-3 setups per run. Only include setups with 3/4+ TF confluence AND R:R >= 2.5:1."
        )
    elif win_rate < 40:
        lines.append(
            f"1. **MODERATE SELECTIVITY**: Win rate is {win_rate:.0f}%. "
            "ACTION: Output 2-4 setups per run. Prefer fewer, higher-conviction setups over padding to 5."
        )
    else:
        lines.append(
            f"1. **MAINTAIN APPROACH**: Win rate is {win_rate:.0f}%. Current selectivity is working."
        )

    rule_num = 2

    # --- Confidence calibration (check ALL levels including high) ---
    conf_stats = {}
    for conf in ["high", "medium", "low"]:
        cs = stats["by_confidence"].get(conf)
        if cs and cs["total"] >= 3:
            conf_stats[conf] = {
                "wr": cs["wins"] / cs["total"] * 100,
                "total": cs["total"],
                "wins": cs["wins"],
            }

    # Check if high confidence underperforms medium (calibration issue)
    if "high" in conf_stats and "medium" in conf_stats:
        high_wr = conf_stats["high"]["wr"]
        med_wr = conf_stats["medium"]["wr"]
        if high_wr < med_wr and conf_stats["high"]["total"] >= 5:
            lines.append(
                f"{rule_num}. **CONFIDENCE MISCALIBRATED**: 'High' confidence is {conf_stats['high']['wins']}/{conf_stats['high']['total']} "
                f"({high_wr:.0f}% WR) but 'Medium' is {conf_stats['medium']['wins']}/{conf_stats['medium']['total']} ({med_wr:.0f}% WR). "
                "ACTION: Reserve 'high confidence' for setups with 3/4 TF confluence + volume confirmed + clean "
                "structure. Do NOT equate 4/4 confluence with high confidence (see confluence rule below). "
                "If unsure, label 'medium' — it actually performs better."
            )
            rule_num += 1

    # --- TF-confluence performance (audit 2026-07-13): the core-premise inversion ---
    by_conf = stats.get("by_confluence", {})
    c3 = by_conf.get("3", {})
    c4 = by_conf.get("4", {})
    if c3.get("total", 0) >= config.RULE_MIN_SAMPLE and c4.get("total", 0) >= 10:
        c3_wr = c3["wins"] / c3["total"] * 100
        c3_rr = c3["rr_sum"] / c3["total"]
        c4_wr = c4["wins"] / c4["total"] * 100
        c4_rr = c4["rr_sum"] / c4["total"]
        if c4_rr < c3_rr - 0.1:
            lines.append(
                f"{rule_num}. **3/4 CONFLUENCE BEATS 4/4**: 3/4 TF is {c3['wins']}/{c3['total']} "
                f"({c3_wr:.0f}% WR, {c3_rr:+.2f} avg R:R) but 4/4 TF is {c4['wins']}/{c4['total']} "
                f"({c4_wr:.0f}% WR, {c4_rr:+.2f} avg R:R). 4/4 alignment = exhausted/late move, not higher "
                "probability. ACTION: Treat 3/4 confluence as the sweet spot. When all 4 TFs already agree, the "
                "move is likely mature — demand a fresh pullback/retest entry or SKIP; never rank a 4/4 setup #1 "
                "just because it is 4/4."
            )
            rule_num += 1

    for conf in ["medium", "low"]:
        cs = stats["by_confidence"].get(conf)
        if cs and cs["total"] >= 5:
            wr = cs["wins"] / cs["total"] * 100
            if cs["total"] >= 30 and wr < 15:
                lines.append(
                    f"{rule_num}. **{conf.upper()} CONFIDENCE WEAK**: {cs['wins']}/{cs['total']} wins ({wr:.0f}%). "
                    f"ACTION: Require R:R >= 3:1 for '{conf}' confidence setups."
                )
                rule_num += 1
            elif wr < 20:
                lines.append(
                    f"{rule_num}. **{conf.upper()} CONFIDENCE UNDERPERFORMING** ({cs['total']} trades): "
                    f"{cs['wins']}/{cs['total']} wins ({wr:.0f}%). "
                    f"ACTION: Be extra selective — require R:R >= 2.5:1 and 3/4+ TF confluence for '{conf}' setups."
                )
                rule_num += 1

    # --- Timeframe performance (NEW) ---
    for tf, ts in stats.get("by_timeframe", {}).items():
        if ts["total"] >= 3:
            wr = ts["wins"] / ts["total"] * 100
            if wr < 20 and ts["total"] >= 5:
                lines.append(
                    f"{rule_num}. **AVOID {tf.upper()} TIMEFRAME**: {ts['wins']}/{ts['total']} wins ({wr:.0f}% WR). "
                    f"ACTION: Do not recommend '{tf}' setups until data improves. Stick to better-performing timeframes."
                )
                rule_num += 1

    # --- Direction performance ---
    for direction, ds in stats.get("by_direction", {}).items():
        if ds["total"] >= config.DIRECTION_RULE_MIN_TRADES:
            # Enough data for hard rules
            wr = ds["wins"] / ds["total"] * 100
            if wr == 0:
                lines.append(
                    f"{rule_num}. **NO {direction.upper()} WINS**: 0/{ds['total']} {direction} trades won. "
                    f"ACTION: Avoid {direction} setups until market conditions change. Only include with 3/4 TF confluence + volume + fresh entry."
                )
                rule_num += 1
            elif wr < 15:
                lines.append(
                    f"{rule_num}. **{direction.upper()} UNDERPERFORMING**: {ds['wins']}/{ds['total']} ({wr:.0f}% WR). "
                    f"ACTION: Be extra selective with {direction} setups — require 3/4+ TF confluence + volume confirmation."
                )
                rule_num += 1
        elif ds["total"] >= 3:
            # Small sample — informational only, do NOT block the direction
            wr = ds["wins"] / ds["total"] * 100
            if wr == 0:
                lines.append(
                    f"{rule_num}. **{direction.upper()} NEEDS DATA**: 0/{ds['total']} {direction} trades won, "
                    f"but sample is too small ({ds['total']} trades, need {config.DIRECTION_RULE_MIN_TRADES}+). "
                    f"ACTION: Include {direction} setups when the market regime supports it and structure is clear. "
                    f"Do NOT avoid {direction} based on this small sample."
                )
                rule_num += 1

    # Directional blind spot: flag if one direction is massively underrepresented
    short_stats = stats.get("by_direction", {}).get("short", {})
    long_stats = stats.get("by_direction", {}).get("long", {})
    if short_stats.get("total", 0) < 10 and long_stats.get("total", 0) > 30:
        lines.append(
            f"{rule_num}. **DIRECTIONAL BLIND SPOT**: Only {short_stats.get('total', 0)} short trades "
            f"vs {long_stats.get('total', 0)} long trades in history. "
            f"ACTION: When the market regime is RISK_OFF, actively consider short setups to build data. "
            f"Do not default to longs in a declining market."
        )
        rule_num += 1

    # --- Setup type rules ---
    best_type = None
    best_type_wr = 0
    for st, s in stats["by_setup_type"].items():
        if s["total"] >= 5:
            wr = s["wins"] / s["total"] * 100
            avg = s["rr_sum"] / s["total"]
            if wr > best_type_wr:
                best_type = st
                best_type_wr = wr
            if wr < 15 and avg < -0.5:
                if s["total"] >= 30:
                    lines.append(
                        f"{rule_num}. **DEPRIORITIZE '{st}'**: {wr:.0f}% WR, {avg:.2f} avg R:R over "
                        f"{s['total']} trades. ACTION: Require 3/4+ TF confluence + volume confirmed."
                    )
                else:
                    lines.append(
                        f"{rule_num}. **'{st}' STRUGGLING** ({s['total']} trades): "
                        f"{wr:.0f}% WR, {avg:.2f} avg R:R. ACTION: Apply extra scrutiny — check entries and stops."
                    )
                rule_num += 1
    # BEST TYPE requires POSITIVE EXPECTANCY, not just win rate. A high-WR type can still
    # bleed net R (e.g. trend_pullback was 32% WR but -20.7R). audit 2026-07-13
    if best_type and best_type_wr >= 25 and stats["by_setup_type"][best_type]["total"] >= config.RULE_MIN_SAMPLE:
        bt = stats["by_setup_type"][best_type]
        bt_avg = bt["rr_sum"] / bt["total"]
        if bt_avg > 0.05:
            lines.append(
                f"{rule_num}. **BEST TYPE: '{best_type}'**: {best_type_wr:.0f}% WR, {bt_avg:+.2f} avg R:R over "
                f"{bt['total']} trades. ACTION: Prioritize this setup type when structure is clean."
            )
            rule_num += 1
        elif bt_avg < -0.15:
            lines.append(
                f"{rule_num}. **NO PROFITABLE SETUP TYPE YET**: highest-WR type '{best_type}' still nets "
                f"{bt_avg:+.2f} avg R:R over {bt['total']} trades. ACTION: Do NOT anchor on any setup type. "
                "Select purely on structural quality + expectancy, not type familiarity."
            )
            rule_num += 1

    # --- Rank anomaly detection (NEW) ---
    rank_stats = stats.get("by_rank", {})
    r1 = rank_stats.get("1", {})
    r2 = rank_stats.get("2", {})
    if r1.get("total", 0) >= 5 and r2.get("total", 0) >= 5:
        r1_wr = r1["wins"] / r1["total"] * 100
        r2_wr = r2["wins"] / r2["total"] * 100
        if r2_wr > r1_wr + 10:
            lines.append(
                f"{rule_num}. **RANK #1 UNDERPERFORMS #2**: Rank #1 is {r1['wins']}/{r1['total']} ({r1_wr:.0f}% WR) "
                f"but Rank #2 is {r2['wins']}/{r2['total']} ({r2_wr:.0f}% WR). "
                "ACTION: Your top-ranked setup may be the most 'obvious' one, not the best one. "
                "Re-evaluate ranking — prioritize setup quality and structural clarity over headline appeal."
            )
            rule_num += 1

    # --- Rank padding rule ---
    low_rank_total = sum(
        s["total"] for rk, s in rank_stats.items() if int(rk) >= 4
    )
    low_rank_wins = sum(
        s["wins"] for rk, s in rank_stats.items() if int(rk) >= 4
    )
    if low_rank_total >= 8:
        lr_wr = low_rank_wins / low_rank_total * 100
        if lr_wr < 20:
            lines.append(
                f"{rule_num}. **STOP PADDING TO 5**: Rank #4-5 have {low_rank_wins}/{low_rank_total} wins ({lr_wr:.0f}%). "
                "ACTION: Only include #4/#5 if they have R:R >= 2.5:1 and 3/4+ TF confluence. "
                "2-3 good setups beats 5 mediocre ones."
            )
            rule_num += 1

    # --- Prediction accuracy + MFE-based optimal T1 (ENHANCED) ---
    pg = stats["prediction_gap"]
    mfe = stats["mfe_stats"]
    sim_t1 = stats.get("simulated_t1", {})
    if pg["count"] >= 10:
        avg_pred = pg["sum_predicted"] / pg["count"]
        avg_act = pg["sum_actual"] / pg["count"]
        gap = avg_pred - avg_act
        if gap > 1.5:
            # Build a prescriptive T1 rule using MFE data
            t1_guidance = ""
            if mfe["total_with_mfe"] >= 10:
                avg_mfe = mfe["mfe_sum"] / mfe["total_with_mfe"]
                t1_guidance = f" Average MFE is {avg_mfe:.1f}R, so set T1 at max {avg_mfe * 0.75:.1f}R from entry."
            # Add simulated T1 evidence if available
            sim_evidence = ""
            if sim_t1.get("sim_total", 0) >= 5:
                hit_075 = sim_t1["sim_075r_hits"] / sim_t1["sim_total"] * 100
                hit_100 = sim_t1["sim_100r_hits"] / sim_t1["sim_total"] * 100
                sim_evidence = (
                    f" Backtest: T1 at 0.75R would hit {hit_075:.0f}% of trades, "
                    f"T1 at 1.0R would hit {hit_100:.0f}% (vs current T1 hit rate of "
                    f"{stats['target_stats']['t1_hits']}/{total} = "
                    f"{stats['target_stats']['t1_hits'] / total * 100:.0f}%)."
                )
            lines.append(
                f"{rule_num}. **TARGETS TOO FAR**: Predicted avg {avg_pred:.1f}R but actual is {avg_act:.2f}R "
                f"(gap: {gap:.1f}R).{t1_guidance}{sim_evidence} "
                "ACTION: Place T1 at the nearest REAL structural level. Use ATR: T1 should be 1.5-2× ATR from entry, NOT 3×+."
            )
            rule_num += 1

    # --- Direction accuracy (MFE) ---
    if mfe["total_with_mfe"] >= 10:
        dir_acc = mfe["reached_05r"] / mfe["total_with_mfe"] * 100
        avg_mfe = mfe["mfe_sum"] / mfe["total_with_mfe"]
        if dir_acc >= 50 and win_rate < 30:
            lines.append(
                f"{rule_num}. **DIRECTION RIGHT, EXECUTION WRONG**: {dir_acc:.0f}% reach 0.5R+ favorable "
                f"(avg MFE: {avg_mfe:.2f}R) but win rate is {win_rate:.0f}%. "
                "ACTION: Widen stops by 0.5× ATR and bring T1 closer. The direction is correct — fix the execution."
            )
            rule_num += 1
        elif dir_acc < 40:
            lines.append(
                f"{rule_num}. **DIRECTION OFTEN WRONG**: Only {dir_acc:.0f}% reach 0.5R favorable. "
                "ACTION: Only trade with 3/4+ TF confluence + volume confirmation. Skip unclear setups."
            )
            rule_num += 1

    # --- Stop loss analysis ---
    st = stats["stop_timing"]
    if st["total_stops"] >= 5 and st["fast_stops"] > st["total_stops"] * 0.4:
        avg_candles = st["candles_sum"] / st["total_stops"]
        lines.append(
            f"{rule_num}. **STOPS HIT TOO FAST**: {st['fast_stops']}/{st['total_stops']} stops hit within "
            f"2 hours (avg {avg_candles:.0f} candles). "
            "ACTION: Use wider ATR-based stops (2.5-3× ATR for intraday). Wait for 15m candle close confirmation."
        )
        rule_num += 1

    # --- Target hit rate ---
    ts = stats["target_stats"]
    if total >= 10 and ts["t1_hits"] < total * 0.3:
        t1_pct = ts["t1_hits"] / total * 100
        lines.append(
            f"{rule_num}. **T1 HIT RATE LOW**: Only {ts['t1_hits']}/{total} ({t1_pct:.0f}%) setups hit T1. "
            "ACTION: T1 must be at the nearest real structural level (prior S/R, EMA cluster, order block). "
            "Not a projected move. If nearest structure gives R:R < 1.5:1, skip the setup."
        )
        rule_num += 1

    # --- Per-symbol performance (NEW) ---
    by_symbol = stats.get("by_symbol", {})
    # Find consistently winning and losing symbols
    winning_symbols = []
    losing_symbols = []
    for sym, ss in by_symbol.items():
        if ss["total"] >= 3:
            wr = ss["wins"] / ss["total"] * 100
            if wr >= 60:
                winning_symbols.append((sym, ss["wins"], ss["total"], wr))
            elif wr == 0:
                losing_symbols.append((sym, ss["total"]))

    if winning_symbols:
        winners_str = ", ".join(f"{s[0]} ({s[1]}/{s[2]})" for s in sorted(winning_symbols, key=lambda x: -x[3])[:5])
        lines.append(
            f"{rule_num}. **WINNING SYMBOLS**: {winners_str}. "
            "ACTION: Give these symbols slight priority when they appear in the scan."
        )
        rule_num += 1

    if losing_symbols and len(losing_symbols) >= 2:
        losers_str = ", ".join(f"{s[0]} (0/{s[1]})" for s in sorted(losing_symbols, key=lambda x: -x[1])[:5])
        lines.append(
            f"{rule_num}. **LOSING SYMBOLS**: {losers_str}. "
            "ACTION: Require 3/4+ TF confluence + volume confirmed for these symbols. Do not include as filler."
        )
        rule_num += 1

    # --- Monthly trend ---
    months = sorted(stats["monthly_trend"].keys())
    if len(months) >= 2:
        last_month = stats["monthly_trend"][months[-1]]
        prev_month = stats["monthly_trend"][months[-2]]
        if last_month["total"] >= 5 and prev_month["total"] >= 5:
            last_wr = last_month["wins"] / last_month["total"] * 100
            prev_wr = prev_month["wins"] / prev_month["total"] * 100
            if last_wr > prev_wr + 10:
                lines.append(
                    f"{rule_num}. **IMPROVING**: {months[-2]} was {prev_wr:.0f}% → {months[-1]} is {last_wr:.0f}%. "
                    "Current approach is working — maintain it."
                )
                rule_num += 1
            elif last_wr < prev_wr - 10 and last_wr < 30:
                lines.append(
                    f"{rule_num}. **DECLINING**: {months[-2]} was {prev_wr:.0f}% → {months[-1]} is {last_wr:.0f}%. "
                    "ACTION: Tighten entries and widen stops. Review if market regime changed."
                )
                rule_num += 1

    # --- Partial profit model insight ---
    pp = stats.get("partial_profit", {})
    pp_total = pp.get("blended_wins", 0) + pp.get("blended_losses", 0)
    if pp_total >= 10:
        blended_wr = pp["blended_wins"] / pp_total * 100
        blended_avg = pp["blended_rr_sum"] / pp_total
        if blended_wr > win_rate + 5:
            lines.append(
                f"{rule_num}. **PARTIAL PROFIT HELPS**: With 50% close at T1 + BE stop, "
                f"blended WR is {blended_wr:.0f}% (vs raw {win_rate:.0f}%), avg blended R:R {blended_avg:.2f}. "
                "ACTION: Always recommend taking 50% profit at T1 and moving stop to breakeven."
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

    # --- Per-regime performance (self-learning) ---
    # Hard regime rules need REGIME_RULE_MIN_TRADES (20) — a 10-16 trade bucket generating a
    # "no-trade zone" / "maintain approach" directive is how the old system whipsawed. Below
    # threshold we emit a NEEDS-DATA note instead of a hard rule. audit 2026-07-13
    by_regime = stats.get("by_regime", {})
    for regime_label, rs in by_regime.items():
        if rs["total"] < 8:
            continue
        r_wr = rs["wins"] / rs["total"] * 100
        r_rr = rs["rr_sum"] / rs["total"]
        if rs["total"] < config.REGIME_RULE_MIN_TRADES:
            if r_rr < -0.2:
                lines.append(
                    f"{rule_num}. **{regime_label.upper()} REGIME WEAK (NEEDS DATA)**: {rs['wins']}/{rs['total']} "
                    f"({r_wr:.0f}% WR, {r_rr:+.2f} avg R:R, only {rs['total']} trades). "
                    f"ACTION: In {regime_label}, stay selective (max 2 setups) but do NOT hard-block — "
                    "sample too small to be sure."
                )
                rule_num += 1
            continue
        # >= 20 trades: hard rules, gated on expectancy not just WR
        if r_rr < -0.15:
            lines.append(
                f"{rule_num}. **{regime_label.upper()} REGIME LOSING**: {rs['wins']}/{rs['total']} "
                f"({r_wr:.0f}% WR, {r_rr:+.2f} avg R:R over {rs['total']} trades). "
                f"ACTION: During {regime_label}, reduce to max 1-2 setups and require 3/4 TF + volume + fresh entry."
            )
            rule_num += 1
        elif r_rr > 0.1 and r_wr >= 40:
            lines.append(
                f"{rule_num}. **{regime_label.upper()} REGIME STRONG**: {rs['wins']}/{rs['total']} "
                f"({r_wr:.0f}% WR, {r_rr:+.2f} avg R:R over {rs['total']} trades). "
                f"ACTION: During {regime_label}, maintain current approach — it's working."
            )
            rule_num += 1

    # --- Rule-applied effectiveness (self-learning) ---
    # Gated on RULE_MIN_SAMPLE + expectancy sign (not WR alone), over canonical rule IDs only.
    # audit 2026-07-13
    by_rule = stats.get("by_rule_applied", {})
    effective_rules = []
    ineffective_rules = []
    for rule_id, rs in by_rule.items():
        if rs["total"] >= config.RULE_MIN_SAMPLE:
            r_wr = rs["wins"] / rs["total"] * 100
            r_rr = rs["rr_sum"] / rs["total"]
            if r_wr >= 40 and r_rr > 0:
                effective_rules.append((rule_id, rs["wins"], rs["total"], r_wr, r_rr))
            elif r_rr < -0.15:
                ineffective_rules.append((rule_id, rs["wins"], rs["total"], r_wr, r_rr))

    if effective_rules:
        eff_str = ", ".join(f"{r[0]} ({r[1]}/{r[2]}={r[3]:.0f}%, {r[4]:+.2f}R)" for r in
                           sorted(effective_rules, key=lambda x: -x[4])[:3])
        lines.append(
            f"{rule_num}. **EFFECTIVE RULES**: {eff_str}. "
            "ACTION: Continue applying these rules — they correlate with positive expectancy."
        )
        rule_num += 1

    if ineffective_rules:
        ineff_str = ", ".join(f"{r[0]} ({r[1]}/{r[2]}={r[3]:.0f}%, {r[4]:+.2f}R)" for r in
                             sorted(ineffective_rules, key=lambda x: x[4])[:3])
        lines.append(
            f"{rule_num}. **INEFFECTIVE RULES**: {ineff_str}. "
            "ACTION: Stop leaning on these rules — they correlate with net losses."
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

    # Blended stats (partial profit model)
    blended_rrs = [r.get("blended_rr") for r in recent_results if r.get("blended_rr") is not None]
    blended_wins = sum(1 for b in blended_rrs if b > 0)
    blended_avg = sum(blended_rrs) / len(blended_rrs) if blended_rrs else avg_rr
    blended_wr = blended_wins / len(blended_rrs) * 100 if blended_rrs else win_rate

    lines = [
        f"# Recent Performance (last {RECENT_WINDOW_WEEKS} weeks)",
        f"_{len(recent_results)} trades: {len(wins)}W / {len(losses)}L "
        f"({win_rate:.0f}% WR, {avg_rr:.2f} avg R:R)_",
    ]
    if blended_rrs:
        lines.append(
            f"_Partial profit model (50% at T1 + BE stop): "
            f"{blended_wr:.0f}% WR, {blended_avg:.2f} avg blended R:R_"
        )
    lines += [
        "",
        "## Trade-by-Trade (LEARN FROM EACH ONE)",
        "| Date | Symbol | Dir | TF | Type | Conf | TF-Conf | Pred R:R | Actual R:R | Blended | Exit | MFE |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
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
        blended = r.get("blended_rr")
        blended_str = f"{blended}" if blended is not None else "n/a"
        exit_r = r.get("exit_reason", "?")
        mfe = r.get("max_favorable_rr")
        mfe_str = f"{mfe}R" if mfe is not None else "n/a"
        icon = "W" if r.get("won") else "L"
        lines.append(
            f"| {date_str} | {sym} | {d} | {tf} | {st} | {conf} | {tfc}/4 "
            f"| {pred} | {actual} ({icon}) | {blended_str} | {exit_r} | {mfe_str} |"
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

    # Blended (partial profit) stats
    blended_rrs = [r.get("blended_rr") for r in evaluated if r.get("blended_rr") is not None]
    blended_wins_count = sum(1 for b in blended_rrs if b > 0)
    blended_avg = sum(blended_rrs) / len(blended_rrs) if blended_rrs else 0
    blended_wr = blended_wins_count / len(blended_rrs) * 100 if blended_rrs else 0
    be_stops = sum(1 for r in evaluated if r.get("be_stop_hit"))

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
    ]
    if blended_rrs:
        lines += [
            "",
            "### Partial Profit Model (50% at T1 + BE stop)",
            f"- **Blended win rate: {blended_wr:.1f}%** ({blended_wins_count}W / {len(blended_rrs) - blended_wins_count}L)",
            f"- Avg blended R:R: {blended_avg:.2f}",
            f"- BE stops (T1 hit then reversed to entry): {be_stops}",
        ]
    lines.append("")
    lines += [
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


# ============================================================
# Delta Analysis — Self-Learning System
# ============================================================
# Triggered automatically after every eval when enough new trades
# have accumulated. Replaces the slow quarterly cadence with a
# faster feedback loop (every ~15 new trades).
#
# Flow: eval runs → enough new trades? → call Claude for patterns
#       → grade previous insights → generate new ACTION rules
#       → append to strategic_rules.md → next scan reads them
# ============================================================

DELTA_ANALYSIS_PROMPT = """You are analyzing RECENT performance changes in a crypto screener that recommends Bybit perpetual futures setups.

## Context
- {new_trades} new evaluated trades since last analysis (total: {total_trades})
- Win rate at last analysis: {wr_at_last}
- Current win rate: {current_wr}

## Lifetime Stats (compact)
```json
{lifetime_stats}
```

## Recent 20 Trade Outcomes
```json
{recent_trades}
```

## Current Rules Being Followed
{current_rules}

## Previous Delta Insights to Evaluate
{previous_insights}

## Task
1. **Grade each previous insight** (if any): EFFECTIVE / INEFFECTIVE / INCONCLUSIVE — with one-line reason.
   Base this on whether the pattern described in the insight improved, worsened, or stayed the same.
2. **Identify 2-5 NEW actionable patterns** not already in the current rules.
   Focus on: regime-specific patterns, rule_applied effectiveness, symbol/direction combos,
   temporal patterns, and anything the algorithmic rules can't detect.

## Output Format (STRICT — parseable)
### Previous Insight Grades
- [insight_id]: EFFECTIVE|INEFFECTIVE|INCONCLUSIVE — [reason]

### New Insights
1. **[SHORT_ID]**: [observation]. ACTION: [specific instruction for Claude].
2. ...

Rules:
- Each insight under 50 words. Be concrete — "Avoid ENAUSDT longs in cautious regime" not "Be more careful."
- SHORT_ID must be lowercase_with_underscores, max 30 chars (e.g., "ada_short_edge", "range_in_cautious")
- Only include insights NOT already covered by the algorithmic rules above.
- If win rate DECLINED since last analysis, focus on what went WRONG and what to stop doing.
- If win rate IMPROVED, identify what's working and reinforce it.
"""


def _load_delta_registry():
    """Load the delta analysis registry (tracks when analysis ran and insight history)."""
    if DELTA_REGISTRY_FILE.exists():
        try:
            return json.loads(DELTA_REGISTRY_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "last_delta_trade_count": 0,
        "last_delta_date": None,
        "wr_at_last_delta": None,
        "insights": [],
    }


def _save_delta_registry(registry):
    """Save the delta analysis registry."""
    DELTA_REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    DELTA_REGISTRY_FILE.write_text(json.dumps(registry, indent=2), encoding="utf-8")


def _load_recent_eval_details(all_evals, limit=20):
    """Load recent evaluated trade details for the delta analysis prompt."""
    recent = []
    for ev in sorted(all_evals, key=lambda e: e.get("run_tag", ""), reverse=True):
        for r in reversed(ev.get("results", [])):
            if r.get("status") == "evaluated":
                recent.append({
                    "symbol": r.get("symbol"),
                    "direction": r.get("direction"),
                    "timeframe": r.get("timeframe"),
                    "setup_type": r.get("setup_type"),
                    "confidence": r.get("confidence"),
                    "rank": r.get("rank"),
                    "won": r.get("won"),
                    "actual_rr": r.get("actual_rr"),
                    "blended_rr": r.get("blended_rr"),
                    "exit_reason": r.get("exit_reason"),
                    "mfe": r.get("max_favorable_rr"),
                    "rules_applied": r.get("rules_applied", []),
                    "regime": ev.get("regime", "neutral"),
                    "run_tag": ev.get("run_tag"),
                })
            if len(recent) >= limit:
                break
        if len(recent) >= limit:
            break
    return recent


def _parse_delta_insights(analysis_text, total_trades):
    """Parse new insights from delta analysis output."""
    insights = []
    # Look for numbered insights after "### New Insights"
    in_new = False
    for line in analysis_text.split("\n"):
        line = line.strip()
        if "### New Insights" in line or "### new insights" in line.lower():
            in_new = True
            continue
        if in_new and line and line[0].isdigit() and "**" in line:
            # Extract insight ID and text
            import re
            match = re.match(r'\d+\.\s*\*\*(\w+)\*\*:\s*(.+)', line)
            if match:
                insight_id = match.group(1).lower()
                text = match.group(2).strip()
                insights.append({
                    "id": insight_id,
                    "text": text,
                    "added_at_trade_count": total_trades,
                    "added_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    "status": "experimental",
                    "trades_since": 0,
                })
    return insights


def _parse_insight_grades(analysis_text):
    """Parse grades for previous insights from delta analysis output."""
    grades = {}
    in_grades = False
    for line in analysis_text.split("\n"):
        line = line.strip()
        if "### Previous Insight Grades" in line or "previous insight grades" in line.lower():
            in_grades = True
            continue
        if in_grades and line.startswith("### "):
            break  # Next section
        if in_grades and line.startswith("- "):
            # Format: - insight_id: EFFECTIVE|INEFFECTIVE|INCONCLUSIVE — reason
            parts = line[2:].split(":", 1)
            if len(parts) == 2:
                insight_id = parts[0].strip().lower()
                grade_text = parts[1].strip().upper()
                if "EFFECTIVE" in grade_text and "INEFFECTIVE" not in grade_text:
                    grades[insight_id] = "confirmed"
                elif "INEFFECTIVE" in grade_text:
                    grades[insight_id] = "expired"
                else:
                    grades[insight_id] = "experimental"  # inconclusive, keep trying
    return grades


def maybe_run_delta_analysis(all_evals):
    """Run delta analysis if enough new trades have accumulated.

    This replaces the quarterly cadence with a faster feedback loop.
    Triggered automatically after every eval — checks if threshold is met.
    """
    if not LIFETIME_STATS_FILE.exists():
        return

    stats = json.loads(LIFETIME_STATS_FILE.read_text(encoding="utf-8"))
    total = stats["total_evaluated"]

    if total < config.DELTA_ANALYSIS_MIN_TRADES:
        return  # Not enough total data

    registry = _load_delta_registry()
    last_count = registry.get("last_delta_trade_count", 0)
    new_trades = total - last_count

    if new_trades < config.DELTA_ANALYSIS_TRADE_THRESHOLD:
        print(f"\nDelta analysis: {new_trades} new trades since last analysis "
              f"(need {config.DELTA_ANALYSIS_TRADE_THRESHOLD}). Skipping.")
        return

    print(f"\n{'='*50}")
    print(f"Self-Learning: Delta Analysis")
    print(f"  {new_trades} new trades since last analysis (total: {total})")
    print(f"{'='*50}")

    # Compute current win rate
    overall = stats["overall"]
    current_wr = f"{overall['wins'] / total * 100:.1f}%" if total > 0 else "N/A"
    wr_at_last = registry.get("wr_at_last_delta", "N/A")

    # Load recent trade details
    recent_trades = _load_recent_eval_details(all_evals, limit=20)

    # Load current rules
    current_rules = ""
    if STRATEGIC_RULES_FILE.exists():
        current_rules = STRATEGIC_RULES_FILE.read_text(encoding="utf-8").strip()

    # Format previous insights for evaluation
    active_insights = [i for i in registry.get("insights", []) if i["status"] != "expired"]
    if active_insights:
        prev_text = "\n".join(
            f"- **{i['id']}** (added {i['added_date']}, {i.get('trades_since', 0)} trades since): {i['text']}"
            for i in active_insights
        )
    else:
        prev_text = "No previous insights yet — this is the first delta analysis."

    # Build prompt
    prompt = DELTA_ANALYSIS_PROMPT.format(
        total_trades=total,
        new_trades=new_trades,
        lifetime_stats=json.dumps(stats, indent=2),
        recent_trades=json.dumps(recent_trades, indent=2),
        current_rules=current_rules,
        previous_insights=prev_text,
        wr_at_last=wr_at_last,
        current_wr=current_wr,
    )

    # Call Claude
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    print("Calling Claude for delta analysis...")

    try:
        response = client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=1500,
            temperature=0,  # deterministic: same stats → same insights (kills run-to-run variance)
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:
        print(f"  Delta analysis failed: {e}")
        return

    analysis = response.content[0].text
    usage = response.usage
    print(f"  Used {usage.input_tokens}+{usage.output_tokens} tokens.")
    print(f"\n{analysis}\n")

    # Parse grades for previous insights
    grades = _parse_insight_grades(analysis)
    for insight in registry.get("insights", []):
        if insight["id"] in grades:
            old_status = insight["status"]
            insight["status"] = grades[insight["id"]]
            if old_status != insight["status"]:
                print(f"  Insight '{insight['id']}': {old_status} → {insight['status']}")

    # Update trades_since; STALE-expire experimental insights not re-affirmed within ~2 batches.
    # (Old behaviour auto-graduated to 'confirmed', locking in unvalidated noise — removed.)
    # audit 2026-07-13
    stale_after = config.DELTA_ANALYSIS_TRADE_THRESHOLD * 2
    for insight in registry.get("insights", []):
        if insight["status"] != "expired":
            insight["trades_since"] = total - insight["added_at_trade_count"]
            if insight["status"] == "experimental" and insight["trades_since"] >= stale_after:
                insight["status"] = "expired"
                print(f"  Insight '{insight['id']}': expired (stale after {insight['trades_since']} trades)")

    # Parse new insights
    new_insights = _parse_delta_insights(analysis, total)
    if new_insights:
        print(f"  {len(new_insights)} new insight(s) registered:")
        for ni in new_insights:
            print(f"    - {ni['id']}: {ni['text'][:80]}...")

    # Merge: keep non-expired old insights + add new ones
    surviving = [i for i in registry.get("insights", []) if i["status"] != "expired"]
    # Avoid duplicate IDs
    existing_ids = {i["id"] for i in surviving}
    for ni in new_insights:
        if ni["id"] not in existing_ids:
            surviving.append(ni)

    # Cap active insights so Claude never receives a wall of (often contradictory) rules.
    # Keep confirmed first, then most-recent experimental. audit 2026-07-13
    cap = config.MAX_ACTIVE_DELTA_INSIGHTS
    if len(surviving) > cap:
        surviving.sort(key=lambda i: (i["status"] != "confirmed", -i.get("added_at_trade_count", 0)))
        for dropped in surviving[cap:]:
            dropped["status"] = "expired"
            print(f"  Insight '{dropped['id']}': expired (over active cap of {cap})")
        surviving = surviving[:cap]

    # Update registry
    registry["last_delta_trade_count"] = total
    registry["last_delta_date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    registry["wr_at_last_delta"] = current_wr
    registry["insights"] = surviving
    _save_delta_registry(registry)
    print(f"  Registry updated: {len(surviving)} active insight(s).")

    # Apply active insights to strategic_rules.md
    _apply_delta_insights_to_rules(surviving, total)

    # Save full analysis log
    log_dir = Path("logs/performance/quarterly")
    log_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    log_file = log_dir / f"delta_{now.strftime('%Y%m%d')}.md"
    log_content = (
        f"# Delta Analysis — {now.strftime('%Y-%m-%d %H:%M UTC')}\n"
        f"_Based on {total} evaluated trades ({new_trades} new). Model: {config.CLAUDE_MODEL}_\n"
        f"_WR at last analysis: {wr_at_last} → current: {current_wr}_\n"
        f"_Tokens: {usage.input_tokens} input + {usage.output_tokens} output_\n\n"
        f"{analysis}\n"
    )
    log_file.write_text(log_content, encoding="utf-8")
    print(f"  Full analysis saved to {log_file}")


def _apply_delta_insights_to_rules(insights, total_trades):
    """Append active delta insights to strategic_rules.md.

    Only experimental and confirmed insights are included.
    Expired insights are automatically excluded.
    """
    active = [i for i in insights if i["status"] in ("experimental", "confirmed")]
    if not active:
        # Remove delta section if no active insights
        if STRATEGIC_RULES_FILE.exists():
            content = STRATEGIC_RULES_FILE.read_text(encoding="utf-8")
            marker = "\n## Delta Insights"
            if marker in content:
                content = content[:content.index(marker)].rstrip() + "\n"
                STRATEGIC_RULES_FILE.write_text(content, encoding="utf-8")
        return

    # Build the delta insights section
    now = datetime.now(timezone.utc)
    lines = [
        f"\n## Delta Insights (Self-Learning)",
        f"_Updated {now.strftime('%Y-%m-%d')} from {total_trades} trades. "
        f"Status: experimental=use as guidance, confirmed=follow strictly._\n",
    ]
    for i, insight in enumerate(active, 1):
        status_marker = "✓" if insight["status"] == "confirmed" else "?"
        lines.append(
            f"{i}. [{status_marker}] **{insight['id']}**: {insight['text']}"
        )
    lines.append("")

    # Replace previous delta section in strategic_rules.md
    if STRATEGIC_RULES_FILE.exists():
        content = STRATEGIC_RULES_FILE.read_text(encoding="utf-8")
    else:
        content = "# Strategic Rules\n_No algorithmic rules yet._\n"

    # Remove old delta section AND old quarterly section
    for marker in ("\n## Delta Insights", "\n## Quarterly Deep Insights"):
        if marker in content:
            content = content[:content.index(marker)]

    content = content.rstrip() + "\n" + "\n".join(lines)
    STRATEGIC_RULES_FILE.write_text(content, encoding="utf-8")
    print(f"  Strategic rules updated with {len(active)} delta insight(s).")


if __name__ == "__main__":
    print("=" * 50)
    print("Crypto Screener — Weekly Evaluation")
    print("=" * 50)
    run_evaluation()
