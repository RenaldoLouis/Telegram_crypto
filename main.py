import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import config
from fetchers.bybit_data import BybitFetcher
from fetchers.telegram_reader import TelegramReader
from analyzer.claude_client import ClaudeAnalyzer
from delivery.telegram_bot import send_brief


def parse_setups_json(brief_text):
    """Extract the structured JSON block from Claude's brief output."""
    match = re.search(r"```setups_json\s*\n(.+?)\n```", brief_text, re.DOTALL)
    if not match:
        print("  Warning: no setups_json block found in brief")
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as e:
        print(f"  Warning: failed to parse setups JSON: {e}")
        return None


def strip_json_block(brief_text):
    """Remove the setups_json block from the brief for Telegram delivery."""
    return re.sub(r"\n*```setups_json\s*\n.+?\n```\n*", "", brief_text, flags=re.DOTALL).strip()


def enrich_with_entry_indicators(setups, technicals):
    """Attach an `entry_indicators` snapshot to each setup for later analysis.

    Persists the 4h/1h indicator values that Claude saw at decision time —
    ADX, RSI, MACD, EMA20 distance in ATR units, and whether a backtested
    signal fired for this symbol+direction. This is instrumentation only: it
    changes no behavior, costs no tokens. It exists so a future eval can test
    whether stricter trend_pullback gates (ADX>25, price near EMA20, MACD
    confirm) actually win — data we currently cannot reconstruct from logs.
    """
    by_symbol = {t.get("symbol"): t for t in (technicals or [])}

    def tf_block(tfs, label):
        d = tfs.get(label) if tfs else None
        if not isinstance(d, dict):
            return None
        price, ema20, atr = d.get("current_price"), d.get("ema_20"), d.get("atr_14")
        ema20_dist_atr = None
        if price is not None and ema20 is not None and atr:
            ema20_dist_atr = round(abs(price - ema20) / atr, 2)
        return {
            "adx": d.get("adx_14"),
            "rsi": d.get("rsi_14"),
            "macd": d.get("macd"),
            "macd_hist": d.get("macd_hist"),
            "trend": d.get("trend"),
            "ema20_dist_atr": ema20_dist_atr,
            "range_pct": d.get("range_pct"),
        }

    for s in setups:
        tech = by_symbol.get(s.get("symbol"))
        if not tech:
            continue
        tfs = tech.get("timeframes", {})
        # Did a backtested signal fire for this symbol in the setup's direction?
        fired = [
            sig.get("signal")
            for sig in tech.get("validated_signals", [])
            if sig.get("direction") == s.get("direction")
        ]
        s["entry_indicators"] = {
            "tf_4h": tf_block(tfs, "4h"),
            "tf_1h": tf_block(tfs, "1h"),
            "backtested_signal": fired[0] if fired else None,
        }
    return setups


def validate_setups(setups, regime_label):
    """Pure Python validation of Claude's setup output against hard rules.

    Catches obvious violations that Claude's output should never have.
    Returns list of violation strings (empty = all good).
    """
    violations = []

    valid_types = {
        "trend_pullback", "range_breakout", "wyckoff_spring",
        "liquidity_sweep", "funding_squeeze", "post_liquidation",
        "failed_breakout", "range_mean_reversion", "recovery_bounce", "other",
    }
    regime_limits = {"risk_off": 2, "cautious": 3, "neutral": 3, "risk_on": 5}
    max_setups = regime_limits.get(regime_label, 3)

    if len(setups) > max_setups:
        violations.append(
            f"COUNT EXCEEDS REGIME LIMIT: {len(setups)} setups > {regime_label} max {max_setups}"
        )

    for s in setups:
        sym = s.get("symbol", "?")
        if s.get("predicted_rr", 0) > 1.6:  # small tolerance
            violations.append(f"{sym}: predicted_rr {s['predicted_rr']} exceeds 1.5 cap")
        if s.get("setup_type") not in valid_types:
            violations.append(f"{sym}: unknown setup_type '{s.get('setup_type')}'")
        if s.get("direction") not in ("long", "short"):
            violations.append(f"{sym}: invalid direction '{s.get('direction')}'")
        if s.get("timeframe") not in ("scalp", "intraday"):
            violations.append(f"{sym}: invalid timeframe '{s.get('timeframe')}'")

    symbols = [s.get("symbol") for s in setups]
    dupes = {sym for sym in symbols if symbols.count(sym) > 1}
    if dupes:
        violations.append(f"DUPLICATE SYMBOLS: {dupes}")

    if regime_label == "risk_off" and len(setups) > 0:
        shorts = [s for s in setups if s.get("direction") == "short"]
        if not shorts:
            violations.append("RISK_OFF: no short setup included (at least 1 required)")

    return violations


def strip_pre_analysis(brief_text):
    """Strip any pre-analysis/working notes before the formatted brief.

    Safety net: with extended thinking enabled, Claude shouldn't write working
    notes in the output. But if any leak through, strip everything before the
    first '## ' header that starts the actual brief.
    """
    match = re.search(r"^(## .+)", brief_text, re.MULTILINE)
    if match:
        return brief_text[match.start():]
    return brief_text


async def run_screener():
    print(f"[{datetime.now()}] Starting screener run...")
    run_ts = datetime.now(timezone.utc)
    run_tag = run_ts.strftime("%Y%m%d_%H%M")

    # 1. Fetch market data
    print("→ Fetching Bybit data...")
    bybit = BybitFetcher()
    market = bybit.get_full_market_snapshot()
    print(f"  Got {len(market['top_movers'])} movers (from 50), {len(market['technicals'])} with multi-TF data")

    # 2. Fetch Telegram signals
    print("→ Reading Telegram groups...")
    tg = TelegramReader()
    messages = await tg.read_groups()
    print(f"  Got {len(messages)} messages")

    # 3. Analyze with Claude
    print("→ Calling Claude...")
    analyzer = ClaudeAnalyzer()
    brief, usage = analyzer.analyze(market, messages)
    print(f"  Used {usage['input_tokens']}+{usage['output_tokens']} tokens")

    # 4. Parse structured setups from Claude's output
    setups = parse_setups_json(brief)
    if setups:
        # Extract regime for tracking (self-learning)
        regime_info = market.get("market_regime", {})
        regime_label = regime_info.get("regime", "neutral") if regime_info else "neutral"

        # Attach entry-time indicator snapshot for later analysis (instrumentation only)
        enrich_with_entry_indicators(setups, market.get("technicals", []))

        # Validate setups against hard rules
        violations = validate_setups(setups, regime_label)
        if violations:
            print("  ⚠️ Setup violations detected:")
            for v in violations:
                print(f"    - {v}")

        setups_dir = Path("logs/setups")
        setups_dir.mkdir(parents=True, exist_ok=True)
        setup_record = {
            "run_timestamp_utc": run_ts.isoformat(),
            "run_tag": run_tag,
            "model": config.CLAUDE_MODEL,
            "regime": regime_label,
            "setups": setups,
        }
        setup_file = setups_dir / f"setups_{run_tag}.json"
        setup_file.write_text(json.dumps(setup_record, indent=2), encoding="utf-8")
        print(f"  Saved {len(setups)} setups to {setup_file} (regime: {regime_label})")
    else:
        print("  No structured setups saved (parse failed or missing)")

    # 5. Archive the brief (without JSON block or pre-analysis notes)
    archive_path = Path("logs/briefs")
    archive_path.mkdir(parents=True, exist_ok=True)
    clean_brief = strip_pre_analysis(strip_json_block(brief))
    fname = archive_path / f"brief_{run_tag}.md"
    fname.write_text(clean_brief, encoding="utf-8")
    print(f"  Archived to {fname}")

    # 6. Deliver via Telegram (clean brief only)
    print("→ Sending to Telegram...")
    send_brief(clean_brief, usage)

    print(f"[{datetime.now()}] Done.\n")


if __name__ == "__main__":
    asyncio.run(run_screener())
