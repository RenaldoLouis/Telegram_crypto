import anthropic
import json
import config
from analyzer.prompts import build_system_prompt


class ClaudeAnalyzer:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    def analyze(self, market_snapshot, telegram_messages):
        system_prompt = build_system_prompt()

        # Compact technicals to save tokens — only include symbols with data
        compact_technicals = []
        for t in market_snapshot['technicals']:
            entry = {"symbol": t["symbol"]}
            for tf_label, indicators in t.get("timeframes", {}).items():
                entry[tf_label] = indicators
            compact_technicals.append(entry)

        user_content = f"""# Today's Market Data

## Timestamp (UTC)
{market_snapshot['timestamp_utc']}

## Top Movers (by 24h turnover) — Top {len(market_snapshot['top_movers'])} coins
```json
{json.dumps(market_snapshot['top_movers'], indent=2)}
```

## Multi-Timeframe Technical Indicators (15m / 1h / 4h / 1D)
Each symbol has indicators per timeframe: RSI(14), volume_spike_ratio, EMA 20/50, trend, breakout flags.
```json
{json.dumps(compact_technicals, indent=2)}
```

## Recent Telegram Signals (last {config.TELEGRAM_LOOKBACK_HOURS}h)
```json
{json.dumps(telegram_messages[:30], indent=2) if telegram_messages else "No signals"}
```

---
Analyze the data across ALL timeframes. Pick the 5 best opportunities ranked by R:R and multi-TF confluence. Produce the structured brief per your instructions."""

        response = self.client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=config.MAX_TOKENS_OUTPUT,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )

        brief_text = response.content[0].text
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
        return brief_text, usage