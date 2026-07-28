import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import config
from fetchers.bybit_data import BybitFetcher
from fetchers.telegram_reader import TelegramReader
from analyzer.claude_client import ClaudeAnalyzer
from delivery.telegram_bot import send_brief, format_mechanical_brief
from mechanical_setups import build_mechanical_setups


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


# Symbols with a deeply negative long history (237-trade backtest).
LONG_BLACKLIST = {"ENAUSDT", "ETHUSDT", "HBARUSDT", "WLDUSDT",
                  "HYPEUSDT", "ONDOUSDT", "LABUSDT"}
VALID_SETUP_TYPES = {
    "trend_pullback", "range_breakout", "wyckoff_spring",
    "liquidity_sweep", "funding_squeeze", "post_liquidation",
    "failed_breakout", "range_mean_reversion", "recovery_bounce", "other",
}
REGIME_COUNT_LIMITS = {"risk_off": 2, "cautious": 3, "neutral": 3, "risk_on": 5}


def _rank_key(s):
    """Sort key on the setup's rank; missing/garbage ranks sort last."""
    try:
        return int(s.get("rank", 999))
    except (TypeError, ValueError):
        return 999


def setup_violations(setup, regime_label):
    """Per-setup BLOCKING checks. A non-empty return means the setup is dropped
    by enforce_setups(). Cross-setup rules (count cap, dedupe, long cap, 4/4-rank-1)
    live in enforce_setups, not here.
    """
    violations = []
    sym = setup.get("symbol", "?")
    direction = setup.get("direction")

    # T1 must be a partial-profit level at 0.75-1.0R, NOT the 1.5R edge level.
    # (The 1.5:1 minimum edge now lives on target_2 — see below.)
    pr = setup.get("predicted_rr", 0)
    if pr > 1.1:  # small tolerance over the 1.0R cap
        violations.append(f"predicted_rr {pr} exceeds 1.0R T1 cap (T1 too far)")

    # target_2 carries the 1.5:1 edge floor. Compute R:R to T2 from mid-entry.
    try:
        entry_mid = (float(setup["entry_low"]) + float(setup["entry_high"])) / 2
        risk = abs(entry_mid - float(setup["stop_loss"]))
        t2 = float(setup["target_2"])
        if risk > 0:
            t2_rr = (t2 - entry_mid) / risk if direction == "long" else (entry_mid - t2) / risk
            if t2_rr < 1.4:  # small tolerance under the 1.5 floor
                violations.append(f"R:R to target_2 {t2_rr:.2f} below 1.5 edge floor")
        else:
            violations.append("zero risk (entry == stop)")
    except (KeyError, TypeError, ValueError):
        violations.append("missing/invalid price fields for R:R check")

    # Long volume gate: every long must have volume confirmation.
    if direction == "long" and not setup.get("volume_confirmed", False):
        violations.append("LONG without volume_confirmed (long volume gate)")
    if direction == "long" and sym in LONG_BLACKLIST:
        violations.append("LONG on blacklisted symbol (negative long history)")
    # Confluence floor (audit 2026-07-13): the 2/4 bucket loses in BOTH directions
    # (2/4 long -0.66R/18t, 2/4 short -0.80R/5t; conf=2 overall 9% WR over 23 trades).
    # 3/4 is the empirical sweet spot, so require >= 3/4 for ANY setup.
    if setup.get("tf_confluence", 0) < config.LONG_MIN_CONFLUENCE:
        violations.append(
            f"tf_confluence {setup.get('tf_confluence', 0)} "
            f"< {config.LONG_MIN_CONFLUENCE} (confluence floor — 2/4 loses in both directions)"
        )

    if setup.get("setup_type") not in VALID_SETUP_TYPES:
        violations.append(f"unknown setup_type '{setup.get('setup_type')}'")
    if direction not in ("long", "short"):
        violations.append(f"invalid direction '{setup.get('direction')}'")
    if setup.get("timeframe") not in ("scalp", "intraday"):
        violations.append(f"invalid timeframe '{setup.get('timeframe')}'")

    return violations


def _demote_4of4_from_top(setups):
    """Confluence de-trust (audit 2026-07-13): 4/4 confluence is the WORST bucket
    (57 trades, 18% WR, -0.36R exp). Never anchor a run on a fully-aligned (=late,
    extended) setup. If the #1 slot is a 4/4, swap in the first sub-4/4 setup.
    `setups` must already be sorted by rank ascending. Mutates order, returns list.
    """
    if setups and (setups[0].get("tf_confluence") or 0) >= 4:
        for i, s in enumerate(setups):
            if (s.get("tf_confluence") or 0) < 4:
                setups.insert(0, setups.pop(i))
                print(f"  ↕ DEMOTE {setups[1].get('symbol','?')}: 4/4 setup can't be rank #1 "
                      "(4/4 = late/extended move)")
                break
    return setups


def enforce_setups(setups, regime_label):
    """Drop rule-breaking setups and apply cross-setup trims, returning the kept
    list (re-ranked 1..N). This REPLACES the old log-only validate_setups: violators
    are now actually removed, so the deterministic risk layer is an enforcer, not a
    logger. Applied to whichever source is the delivered output.
    """
    # 1. Drop per-setup violators.
    kept = []
    for s in setups:
        v = setup_violations(s, regime_label)
        if v:
            print(f"  ✂ DROP {s.get('symbol','?')} ({s.get('direction','?')}): {'; '.join(v)}")
            continue
        kept.append(s)

    # 2. Dedupe by symbol — keep the best-ranked instance.
    seen = {}
    for s in sorted(kept, key=_rank_key):
        sym = s.get("symbol")
        if sym in seen:
            print(f"  ✂ DROP {sym}: duplicate symbol (kept better-ranked instance)")
            continue
        seen[sym] = s
    kept = list(seen.values())

    # 3. Regime-aware long cap (audit 2026-07-13): longs are the entire net loss
    # (-33R / 29% WR); outside a confirmed risk_on rally, cap longs per run.
    long_cap = config.LONG_CAP_BY_REGIME.get(regime_label, 2)
    longs_sorted = sorted((s for s in kept if s.get("direction") == "long"), key=_rank_key)
    if len(longs_sorted) > long_cap:
        keep_ids = {id(s) for s in longs_sorted[:long_cap]}
        for s in longs_sorted[long_cap:]:
            print(f"  ✂ DROP {s.get('symbol','?')}: long cap {long_cap} for {regime_label} "
                  "(longs run 29% WR / -33R; prefer shorts outside risk_on)")
        kept = [s for s in kept if s.get("direction") != "long" or id(s) in keep_ids]

    # 4. Regime count cap — keep the top-N by rank.
    max_setups = REGIME_COUNT_LIMITS.get(regime_label, 3)
    kept = sorted(kept, key=_rank_key)
    if len(kept) > max_setups:
        for s in kept[max_setups:]:
            print(f"  ✂ DROP {s.get('symbol','?')}: exceeds {regime_label} max {max_setups}")
        kept = kept[:max_setups]

    # 5. 4/4-at-rank-1 demotion (re-rank, do not drop), then renumber 1..N.
    kept = _demote_4of4_from_top(kept)
    for i, s in enumerate(kept, 1):
        s["rank"] = i

    # 6. Advisory only (cannot be auto-fixed): risk_off with no short. The mechanical
    # path cannot fabricate a short, so this is a warning, not a drop.
    if regime_label == "risk_off" and kept and not any(s.get("direction") == "short" for s in kept):
        print("  ⚠ risk_off: no short setup in output (advisory — none available to include)")

    return kept


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


def _stamp_setups(setups, regime_label, interest_scores, source):
    """Stamp source/regime/interest_score/model and normalize rules_applied to the
    canonical taxonomy. Idempotent — safe to call on either source's setups.
    """
    for s in setups:
        s["source"] = source
        s["regime"] = regime_label
        s["model"] = config.MECHANICAL_MODEL_TAG if source == "mechanical" else config.CLAUDE_MODEL
        if s.get("interest_score") is None:
            s["interest_score"] = interest_scores.get(s.get("symbol"))
        reasoning = s.get("reasoning") or {}
        applied = reasoning.get("rules_applied", []) or []
        canonical = [r for r in applied if r in config.CANONICAL_RULES]
        dropped = [r for r in applied if r not in config.CANONICAL_RULES]
        if dropped:
            print(f"    - {s.get('symbol','?')}: dropped non-canonical rule IDs {dropped}")
        reasoning["rules_applied"] = canonical
        s["reasoning"] = reasoning


def _prepare_source(setups, regime_label, interest_scores, technicals, source):
    """Shared pipeline for either source: enrich → enforce → stamp. Returns kept."""
    enrich_with_entry_indicators(setups, technicals)
    before = len(setups)
    kept = enforce_setups(setups, regime_label)
    if len(kept) != before:
        print(f"  [{source}] enforcement kept {len(kept)}/{before} setups")
    _stamp_setups(kept, regime_label, interest_scores, source)
    return kept


# Longest eval window is `intraday` = 2 days (weekly_eval.EVAL_WINDOWS). A setup from a
# scan within that window is still "open" for scoring, so re-emitting the same
# symbol+direction+source would create a correlated pseudo-replicate trade (matters now
# that CI scans every 4h = 6x/day). Kept local to avoid importing weekly_eval.
_DEDUP_LOOKBACK_DAYS = 2


def _active_setup_keys(now_utc, lookback_days=_DEDUP_LOOKBACK_DAYS):
    """Return the set of (symbol, direction, source) tuples that already have a setup
    from a recent run still inside its eval window. Reads prior logs/setups/*.json.

    Best-effort instrumentation: any read/parse failure is swallowed and treated as
    "no active keys" so a malformed log can never crash a scan.
    """
    keys = set()
    cutoff = now_utc.timestamp() - lookback_days * 86400
    try:
        for f in Path("logs/setups").glob("setups_*.json"):
            try:
                record = json.loads(f.read_text(encoding="utf-8"))
                ts = datetime.fromisoformat(record["run_timestamp_utc"])
                if ts.timestamp() < cutoff:
                    continue
                for s in record.get("setups", []):
                    keys.add((s.get("symbol"), s.get("direction"), s.get("source")))
            except Exception:
                continue  # skip one bad file, keep scanning the rest
    except Exception:
        return set()
    return keys


def _drop_active_duplicates(setups, active_keys, source):
    """Filter out setups whose (symbol, direction, source) is already active within the
    eval window. Per-source so the mechanical-vs-claude head-to-head stays fair.
    """
    kept, dropped = [], []
    for s in setups:
        key = (s.get("symbol"), s.get("direction"), source)
        if key in active_keys:
            dropped.append(s.get("symbol", "?"))
        else:
            kept.append(s)
    if dropped:
        print(f"  [{source}] cross-run dedup: suppressed {len(dropped)} still-active "
              f"({', '.join(dropped)})")
    return kept


async def run_screener():
    print(f"[{datetime.now()}] Starting screener run...")
    run_ts = datetime.now(timezone.utc)
    run_tag = run_ts.strftime("%Y%m%d_%H%M")

    # 1. Fetch market data (required for BOTH the mechanical and Claude paths).
    print("→ Fetching Bybit data...")
    bybit = BybitFetcher()
    market = bybit.get_full_market_snapshot()
    print(f"  Got {len(market['top_movers'])} movers (from 50), {len(market['technicals'])} with multi-TF data")
    regime_info = market.get("market_regime") or {}
    regime_label = regime_info.get("regime", "neutral")
    interest_scores = market.get("interest_scores", {}) or {}
    technicals = market.get("technicals", [])

    # 2. PRIMARY: mechanical setups — built FIRST, with ZERO dependency on Claude.
    # This guarantees a scan always produces output even if Claude is down.
    print("→ Building mechanical setups (primary)...")
    mechanical = _prepare_source(
        build_mechanical_setups(market), regime_label, interest_scores, technicals, "mechanical"
    )
    print(f"  Mechanical: {len(mechanical)} setups (regime: {regime_label})")

    # 3. SHADOW: Claude — wrapped so ANY failure (quota, $ cap, timeout, API/network
    # error) degrades to mechanical-only instead of crashing the scan.
    claude_setups, brief, usage = [], None, None
    try:
        print("→ Reading Telegram groups...")
        tg = TelegramReader()
        messages = await tg.read_groups()
        print(f"  Got {len(messages)} messages")

        print("→ Calling Claude (shadow)...")
        analyzer = ClaudeAnalyzer()
        brief, usage = analyzer.analyze(market, messages)
        print(f"  Used {usage['input_tokens']}+{usage['output_tokens']} tokens")

        parsed = parse_setups_json(brief) or []
        if parsed:
            claude_setups = _prepare_source(
                parsed, regime_label, interest_scores, technicals, "claude"
            )
    except Exception as e:
        print(f"  ⚠ Claude shadow failed ({type(e).__name__}: {e}) — continuing mechanical-only")

    # 3b. Cross-run dedup: with CI scanning every 4h, the same coin re-flagged in
    # consecutive windows would log correlated pseudo-replicate trades that pollute the
    # eval / flip-gate counter. Drop any (symbol, direction, source) still active from a
    # recent scan. Per-source so the head-to-head comparison stays fair.
    active = _active_setup_keys(run_ts)
    mechanical = _drop_active_duplicates(mechanical, active, "mechanical")
    claude_setups = _drop_active_duplicates(claude_setups, active, "claude")

    # 4. Persist BOTH sources to one file, each tagged `source` (head-to-head data).
    all_setups = mechanical + claude_setups
    if all_setups:
        setups_dir = Path("logs/setups")
        setups_dir.mkdir(parents=True, exist_ok=True)
        setup_record = {
            "run_timestamp_utc": run_ts.isoformat(),
            "run_tag": run_tag,
            "model": config.CLAUDE_MODEL,            # kept for backward-compat (Claude era)
            "mechanical_model": config.MECHANICAL_MODEL_TAG,
            "primary_source": config.PRIMARY_SOURCE,
            "regime": regime_label,
            "sources": {"mechanical": len(mechanical), "claude": len(claude_setups)},
            "setups": all_setups,
        }
        setup_file = setups_dir / f"setups_{run_tag}.json"
        setup_file.write_text(json.dumps(setup_record, indent=2), encoding="utf-8")
        print(f"  Saved {len(all_setups)} setups "
              f"(mechanical={len(mechanical)}, claude={len(claude_setups)}) to {setup_file}")
    else:
        print("  No setups from either source this run")

    # 5. Decide what to DELIVER. Mechanical when it's primary OR when Claude failed.
    deliver_mechanical = (config.PRIMARY_SOURCE == "mechanical") or (brief is None)
    if deliver_mechanical:
        reason = "PRIMARY_SOURCE=mechanical" if config.PRIMARY_SOURCE == "mechanical" else "Claude unavailable"
        print(f"→ Delivering MECHANICAL brief ({reason})...")
        clean_brief = format_mechanical_brief(mechanical, regime_label)
    else:
        print("→ Delivering CLAUDE brief (shadow mode)...")
        clean_brief = strip_pre_analysis(strip_json_block(brief))

    # 6. Archive + deliver.
    archive_path = Path("logs/briefs")
    archive_path.mkdir(parents=True, exist_ok=True)
    fname = archive_path / f"brief_{run_tag}.md"
    fname.write_text(clean_brief, encoding="utf-8")
    print(f"  Archived to {fname}")

    print("→ Sending to Telegram...")
    send_brief(clean_brief, usage)

    print(f"[{datetime.now()}] Done.\n")


if __name__ == "__main__":
    asyncio.run(run_screener())
