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
        for t in market_snapshot.get("technicals", []):
            entry = {"s": t["symbol"]}
            for tf_label, indicators in t.get("timeframes", {}).items():
                entry[tf_label] = indicators
            compact_technicals.append(entry)

        # Always inject regime context so Claude can see market breadth even in neutral
        regime_section = ""
        regime = market_snapshot.get("market_regime")
        if regime:
            m = regime.get("metrics", {})
            regime_label = regime.get("regime", "neutral").upper()
            regime_section = (
                f"\n## Market Regime: {regime_label}\n"
                f"- {m.get('pct_declining', '?')}% of top 50 coins declining\n"
                f"- BTC 24h: {m.get('btc_change_pct', '?')}%\n"
                f"- Median 24h: {m.get('median_change_pct', '?')}%\n"
                f"- Avg funding: {m.get('avg_funding_pct', '?')}%\n"
                f"- Coins >5% decline: {m.get('large_decline_count', '?')}\n"
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

        user_content = f"""# Market Data ({market_snapshot['timestamp_utc']})
{regime_section}{streak_section}
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
        response = self.client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=config.MAX_TOKENS_OUTPUT,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_content}],
        )

        brief_text = response.content[0].text

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