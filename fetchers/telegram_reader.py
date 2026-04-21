from telethon import TelegramClient
from datetime import datetime, timedelta, timezone
import config


class TelegramReader:
    def __init__(self):
        self.client = TelegramClient(
            "screener_session",
            config.TELEGRAM_API_ID,
            config.TELEGRAM_API_HASH,
        )

    async def read_groups(self):
        if not config.TELEGRAM_GROUPS:
            return []

        await self.client.start()
        cutoff = datetime.now(timezone.utc) - timedelta(hours=config.TELEGRAM_LOOKBACK_HOURS)

        all_messages = []
        for group in config.TELEGRAM_GROUPS:
            try:
                async for msg in self.client.iter_messages(group, limit=200):
                    if msg.date < cutoff:
                        break
                    if msg.text:
                        all_messages.append({
                            "group": group,
                            "time": msg.date.isoformat(),
                            "text": msg.text[:500],  # Cap length
                        })
            except Exception as e:
                print(f"Error reading {group}: {e}")

        await self.client.disconnect()
        return all_messages