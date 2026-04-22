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
        setups_dir = Path("logs/setups")
        setups_dir.mkdir(parents=True, exist_ok=True)
        setup_record = {
            "run_timestamp_utc": run_ts.isoformat(),
            "run_tag": run_tag,
            "model": config.CLAUDE_MODEL,
            "setups": setups,
        }
        setup_file = setups_dir / f"setups_{run_tag}.json"
        setup_file.write_text(json.dumps(setup_record, indent=2), encoding="utf-8")
        print(f"  Saved {len(setups)} setups to {setup_file}")
    else:
        print("  No structured setups saved (parse failed or missing)")

    # 5. Archive the brief (without the JSON block — keep it clean)
    archive_path = Path("logs/briefs")
    archive_path.mkdir(parents=True, exist_ok=True)
    clean_brief = strip_json_block(brief)
    fname = archive_path / f"brief_{run_tag}.md"
    fname.write_text(clean_brief, encoding="utf-8")
    print(f"  Archived to {fname}")

    # 6. Deliver via Telegram (clean brief without JSON block)
    print("→ Sending to Telegram...")
    send_brief(clean_brief, usage)

    print(f"[{datetime.now()}] Done.\n")


if __name__ == "__main__":
    asyncio.run(run_screener())
