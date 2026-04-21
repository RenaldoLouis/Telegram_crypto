import asyncio
from datetime import datetime
from pathlib import Path

from fetchers.bybit_data import BybitFetcher
from fetchers.telegram_reader import TelegramReader
from analyzer.claude_client import ClaudeAnalyzer
from delivery.telegram_bot import send_brief


async def run_screener():
    print(f"[{datetime.now()}] Starting screener run...")

    # 1. Fetch market data
    print("→ Fetching Bybit data...")
    bybit = BybitFetcher()
    market = bybit.get_full_market_snapshot()
    print(f"  Got {len(market['top_movers'])} movers, {len(market['technicals'])} technicals")

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

    # 4. Archive the brief
    archive_path = Path("logs/briefs")
    archive_path.mkdir(parents=True, exist_ok=True)
    fname = archive_path / f"brief_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
    fname.write_text(brief, encoding="utf-8")
    print(f"  Archived to {fname}")

    # 5. Deliver via Telegram
    print("→ Sending to Telegram...")
    send_brief(brief, usage)

    print(f"[{datetime.now()}] Done.\n")


if __name__ == "__main__":
    asyncio.run(run_screener())