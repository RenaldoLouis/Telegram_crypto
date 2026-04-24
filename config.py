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
# CLAUDE_MODEL = "claude-sonnet-4-6"   # use sonnet when tuning
CLAUDE_MODEL = "claude-haiku-4-5"      # Cheap for daily use;
MAX_TOKENS_OUTPUT = 8000             # 5 detailed setups + JSON block needs ~6-7k tokens

# === Bybit Settings ===
BYBIT_CATEGORY = "linear"            # USDT perpetuals
TOP_MOVERS_LIMIT = 25                # Screen top 25 by volume
KLINE_INTERVALS = {                  # Multi-timeframe candle config
    "15": 100,                       # 15m — scalp (last ~25h)
    "60": 100,                       # 1h  — intraday (last ~4 days)
    "240": 100,                      # 4h  — swing (last ~16 days)
    "D": 60,                         # 1D  — trend context (last ~2 months)
}
# Legacy single-TF settings (kept for backward compat)
KLINE_INTERVAL = "60"
KLINE_LIMIT = 100

# === Telegram Groups to Monitor ===
# Add group usernames or IDs you want to screen
TELEGRAM_GROUPS = [
    # "@some_crypto_group",
    # "@another_signals_group",
]
TELEGRAM_LOOKBACK_HOURS = 12         # Read messages from last N hours

# === Watchlist (your personal focus) ===
WATCHLIST = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]  # Always include these