import anthropic
import json
import config
from analyzer.prompts import build_system_prompt


class ClaudeAnalyzer:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    def analyze(self, market_snapshot, telegram_messages):
        system_prompt = build_system_prompt()

        user_content = f"""# Today's Market Data

## Timestamp (UTC)
{market_snapshot['timestamp_utc']}

## Top Movers (by 24h turnover)
```json
{json.dumps(market_snapshot['top_movers'], indent=2)}
```

## Technical Indicators
```json
{json.dumps(market_snapshot['technicals'], indent=2)}
```

## Recent Telegram Signals (last {config.TELEGRAM_LOOKBACK_HOURS}h)
```json
{json.dumps(telegram_messages[:30], indent=2) if telegram_messages else "No signals"}
```

---
Produce the structured market brief per your instructions."""

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