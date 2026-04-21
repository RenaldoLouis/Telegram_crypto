import os
from dotenv import load_dotenv

load_dotenv()

# === API Keys ===
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")
TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", 0))
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# === Claude Settings ===
CLAUDE_MODEL = "claude-haiku-4-5"   # Cheap for daily use; switch to sonnet when tuning
MAX_TOKENS_OUTPUT = 2000

# === Bybit Settings ===
BYBIT_CATEGORY = "linear"            # USDT perpetuals
TOP_MOVERS_LIMIT = 20                # Screen top 20 by volume
KLINE_INTERVAL = "60"                # 1h candles for technicals
KLINE_LIMIT = 100                    # Last 100 candles for RSI etc.

# === Telegram Groups to Monitor ===
# Add group usernames or IDs you want to screen
TELEGRAM_GROUPS = [
    # "@some_crypto_group",
    # "@another_signals_group",
]
TELEGRAM_LOOKBACK_HOURS = 12         # Read messages from last N hours

# === Watchlist (your personal focus) ===
WATCHLIST = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]  # Always include these