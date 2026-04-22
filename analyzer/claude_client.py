import anthropic
import json
import config
from analyzer.prompts import build_system_prompt


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

        user_content = f"""# Market Data ({market_snapshot['timestamp_utc']})

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
Analyze all data across timeframes. Pick the 5 best opportunities. Include the setups_json block."""

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