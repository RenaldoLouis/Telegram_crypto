import anthropic
import json
from pathlib import Path
import config
from analyzer.prompts import build_system_prompt


def _detect_losing_streak():
    """Read recent eval files and count consecutive stop losses from the most recent trade backward."""
    eval_dir = Path("logs/evaluations")
    if not eval_dir.exists():
        return 0, 0  # streak, total_recent_losses

    eval_files = sorted(eval_dir.glob("eval_*.json"), reverse=True)
    consecutive_stops = 0
    recent_losses = 0  # losses in last 20 trades
    trades_checked = 0
    streak_broken = False

    for ef in eval_files[:6]:  # Check last 6 eval files (~30 trades max)
        try:
            data = json.loads(ef.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        # Results are in chronological order within the file; iterate in reverse
        for r in reversed(data.get("results", [])):
            trades_checked += 1
            if trades_checked <= 20 and not r.get("won", False):
                recent_losses += 1
            if not streak_broken:
                if r.get("exit_reason") == "stop_loss":
                    consecutive_stops += 1
                else:
                    streak_broken = True
            if trades_checked >= 20:
                break
        if trades_checked >= 20:
            break

    return consecutive_stops, recent_losses


class ClaudeAnalyzer:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    def analyze(self, market_snapshot, telegram_messages):
        system_prompt = build_system_prompt()

        # Build compact technicals — all symbols have full multi-TF data
        compact_technicals = []
        all_validated_signals = []
        for t in market_snapshot.get("technicals", []):
            entry = {"s": t["symbol"]}
            for tf_label, indicators in t.get("timeframes", {}).items():
                entry[tf_label] = indicators
            compact_technicals.append(entry)
            # Collect validated signals
            for sig in t.get("validated_signals", []):
                all_validated_signals.append(sig)

        # Always inject regime context so Claude can see market breadth even in neutral
        regime_section = ""
        regime_max_setups = 3  # default for neutral/missing
        regime = market_snapshot.get("market_regime")
        if regime:
            m = regime.get("metrics", {})
            regime_label = regime.get("regime", "neutral")
            regime_section = (
                f"\n## Market Regime: {regime_label.upper()}\n"
                f"- {m.get('pct_declining', '?')}% of top 50 coins declining\n"
                f"- BTC 24h: {m.get('btc_change_pct', '?')}%\n"
                f"- Median 24h: {m.get('median_change_pct', '?')}%\n"
                f"- Avg funding: {m.get('avg_funding_pct', '?')}%\n"
                f"- Coins >5% decline: {m.get('large_decline_count', '?')}\n"
            )
            # Explicit regime limits — these are LAW, not guidance
            if regime_label == "risk_off":
                regime_max_setups = 2
                regime_section += (
                    "\n**⚠️ MANDATORY REGIME LIMITS (non-negotiable):**\n"
                    "- Output MAXIMUM 2 setups this run. No exceptions.\n"
                    "- At least 1 setup MUST be a SHORT if any coin shows bearish structure "
                    "(distribution, breakdown, failed breakout, funding squeeze with overleveraged longs).\n"
                    "- Longs ONLY if they have 4/4 TF confluence + volume confirmed + clear structural support holding. "
                    "If a long doesn't meet ALL three, DROP it.\n"
                    "- If no high-conviction setup exists, output 0 setups.\n"
                )
            elif regime_label == "cautious":
                regime_max_setups = 3
                regime_section += (
                    "\n**⚠️ MANDATORY REGIME LIMITS (non-negotiable):**\n"
                    "- Output MAXIMUM 3 setups this run.\n"
                    "- Every long MUST have volume confirmed OR 4/4 TF confluence. No exceptions.\n"
                    "- Include at least 1 SHORT setup if any coin shows clear bearish structure.\n"
                    "- Do NOT label bounces from oversold as 'trend_pullback' — use 'recovery_bounce'.\n"
                )
            elif regime_label == "risk_on":
                regime_max_setups = 5
                regime_section += (
                    "\n**REGIME LIMITS:**\n"
                    "- Maximum 5 setups this run.\n"
                    "- Favor trend-following longs.\n"
                    "- Shorts only with clear multi-TF distribution.\n"
                )
            else:  # neutral
                regime_max_setups = 3
                regime_section += (
                    "\n**REGIME LIMITS:**\n"
                    "- Maximum 3 setups this run.\n"
                    "- No directional bias — analyze both long and short opportunities.\n"
                )
        else:
            regime_section = (
                "\n## Market Regime: NEUTRAL (regime data unavailable)\n"
                "**REGIME LIMITS:**\n"
                "- Maximum 3 setups this run.\n"
            )

        # Detect losing streak from recent evaluations
        streak_section = ""
        consecutive_stops, recent_losses = _detect_losing_streak()
        if consecutive_stops >= 5:
            streak_section = (
                f"\n## ⚠️ LOSING STREAK ALERT: {consecutive_stops} consecutive stop losses\n"
                f"Recent performance is poor. MANDATORY adjustments:\n"
                f"- Output MAXIMUM 2 setups this run (quality over quantity)\n"
                f"- Every setup MUST have volume_confirmed=true OR 4/4 TF confluence\n"
                f"- Prefer setups in the OPPOSITE direction of the losing streak if structure supports it\n"
                f"- If nothing meets this bar, output 0 setups\n"
            )
        elif consecutive_stops >= 3:
            streak_section = (
                f"\n## ⚠️ CAUTION: {consecutive_stops} consecutive stop losses\n"
                f"Be more selective. Output MAXIMUM 3 setups. Increase quality bar.\n"
            )

        # Inject recent loss rate (activates the previously-unused recent_losses counter)
        recent_losses_section = ""
        if recent_losses >= 15:
            recent_losses_section = (
                f"\n## ⚠️ SEVERE DROUGHT: {recent_losses}/20 recent trades lost\n"
                f"The current approach is clearly not working. MANDATORY:\n"
                f"- Output MAXIMUM 1-2 setups. Do NOT pad.\n"
                f"- Every setup MUST have volume confirmed AND structural clarity.\n"
                f"- Strongly prefer range setups (mean reversion, springs, sweeps) over trend-following.\n"
                f"- Consider outputting 0 setups if conditions are choppy.\n"
            )
        elif recent_losses >= 12:
            recent_losses_section = (
                f"\n## ⚠️ HIGH LOSS RATE: {recent_losses}/20 recent trades lost\n"
                f"Recent performance is poor. Be extra selective — max 2-3 setups, higher quality bar.\n"
            )

        # Compute effective max setups across all constraints
        streak_max = None
        if consecutive_stops >= 5:
            streak_max = 2
        elif consecutive_stops >= 3:
            streak_max = 3
        loss_rate_max = None
        if recent_losses >= 15:
            loss_rate_max = 2
        elif recent_losses >= 12:
            loss_rate_max = 3
        # Effective max = strictest of all constraints
        all_limits = [regime_max_setups]
        if streak_max is not None:
            all_limits.append(streak_max)
        if loss_rate_max is not None:
            all_limits.append(loss_rate_max)
        effective_max = min(all_limits)

        # Build a single resolved directive so Claude sees ONE number
        effective_section = (
            f"\n## ⚠️ EFFECTIVE LIMIT THIS RUN: MAXIMUM {effective_max} SETUPS\n"
            f"This is the resolved limit from regime ({regime_max_setups})"
        )
        if streak_max is not None:
            effective_section += f" + losing streak ({streak_max})"
        if loss_rate_max is not None:
            effective_section += f" + recent loss rate ({loss_rate_max})"
        effective_section += (
            f". The strictest applies: **{effective_max}**.\n"
            f"Output more than {effective_max} setups and the entire output is invalid.\n"
        )

        # Extract BTC daily trend for prominent injection
        btc_section = ""
        for t in market_snapshot.get("technicals", []):
            if t.get("symbol") == "BTCUSDT":
                btc_1d = t.get("timeframes", {}).get("1D", {})
                if btc_1d:
                    btc_trend = btc_1d.get("trend", "unknown")
                    btc_rsi = btc_1d.get("rsi_14", "?")
                    btc_adx = btc_1d.get("adx_14", "?")
                    btc_section = (
                        f"\n## BTC Daily Trend: {btc_trend.upper()}\n"
                        f"- BTC 1D RSI: {btc_rsi}\n"
                        f"- BTC 1D ADX: {btc_adx}\n"
                    )
                    if btc_trend == "bearish" and isinstance(btc_rsi, (int, float)) and btc_rsi < 40:
                        btc_section += (
                            "- ⚠️ BTC daily downtrend with weak RSI. "
                            "Correlated alt longs are HIGH RISK. "
                            "Only recommend alt longs with independent momentum (decoupled from BTC) "
                            "or 4/4 TF + volume confirmed.\n"
                        )
                break

        # Build validated signals section (backtested, cross-TF confirmed)
        validated_section = ""
        if all_validated_signals:
            validated_section = (
                "\n## BACKTESTED SIGNALS (cross-TF validated, out-of-sample confirmed)\n"
                "These signals passed train/test validation on 15 symbols across 1h+4h.\n"
                "They have empirical edge. PRIORITIZE over unvalidated setups.\n"
                "At least 1 of your setups SHOULD be a validated signal if any fired.\n"
                "Do NOT override the direction of a validated signal.\n\n"
            )
            for sig in all_validated_signals:
                validated_section += (
                    f"**{sig['symbol']}** — `{sig['signal']}` on {sig['tf']}: "
                    f"{sig['indicators']}\n"
                    f"  → {sig['direction'].upper()} @ {sig['target_r']}R target, "
                    f"{sig['stop_atr']} ATR stop | {sig['historical']}\n\n"
                )
            print(f"  Validated signals: {len(all_validated_signals)} fired")

        user_content = f"""# Market Data ({market_snapshot['timestamp_utc']})
{regime_section}{btc_section}{streak_section}{recent_losses_section}{effective_section}{validated_section}
## Top Movers ({len(market_snapshot['top_movers'])} pre-filtered by turnover + interest score)
```json
{json.dumps(market_snapshot['top_movers'], separators=(',', ':'))}
```

## Multi-TF Technicals (15m / 1h / 4h / 1D per symbol)
```json
{json.dumps(compact_technicals, separators=(',', ':'))}
```

## Telegram Signals (last {config.TELEGRAM_LOOKBACK_HOURS}h)
{json.dumps(telegram_messages[:30], separators=(',', ':')) if telegram_messages else "None"}

---
Analyze all data across timeframes. Pick the BEST opportunities (quality over quantity). Include the setups_json block."""

        # Send the system prompt as a cacheable block.
        # The knowledge library (~35-45k tokens) doesn't change between runs,
        # so we cache it. Subsequent calls within ~5 min reuse the cache
        # and pay ~90% less for those input tokens.
        #
        # Extended thinking enabled: Claude's reasoning goes into a separate
        # thinking block (not included in output), so all output tokens are
        # used for the actual brief. max_tokens must cover thinking + text.
        response = self.client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=config.MAX_TOKENS_OUTPUT + config.THINKING_BUDGET,
            thinking={
                "type": "enabled",
                "budget_tokens": config.THINKING_BUDGET,
            },
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_content}],
        )

        # Extract only text blocks — thinking blocks stay internal
        brief_text = "".join(
            block.text for block in response.content if block.type == "text"
        )

        # Capture cache hit/miss metrics for cost tracking.
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "cache_creation_input_tokens": getattr(
                response.usage, "cache_creation_input_tokens", 0
            ) or 0,
            "cache_read_input_tokens": getattr(
                response.usage, "cache_read_input_tokens", 0
            ) or 0,
        }

        return brief_text, usage