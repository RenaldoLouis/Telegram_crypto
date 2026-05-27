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
CLAUDE_MODEL = "claude-sonnet-4-6"   # use sonnet when tuning
# CLAUDE_MODEL = "claude-haiku-4-5"      # Cheap for daily use;
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

# === Momentum Pulse Settings ===
MOMENTUM_PULSE_EXPIRY_HOURS = 48          # Hot list entries expire after this
MOMENTUM_BIG_MOVE_PCT = 8.0              # Flag if price moved > this %
MOMENTUM_BIG_MOVE_TURNOVER = 200_000_000 # ... AND turnover above this ($200M)
MOMENTUM_VOLUME_ACCEL_THRESHOLD = 3.0    # Flag if turnover is Nx the previous pulse
MOMENTUM_FUNDING_EXTREME_PCT = 0.05      # Flag if |funding| > this %
MOMENTUM_FUNDING_MOVE_PCT = 3.0          # ... AND price moving > this %
MOMENTUM_HOT_LIST_PATH = "logs/momentum/hot_list.json"
MOMENTUM_SNAPSHOT_PATH = "logs/momentum/last_snapshot.json"

# === Market Regime Detection ===
# risk_off (bearish) — broad sell-off, favor shorts, max 2 setups
REGIME_BEARISH_DECLINE_PCT = 70        # % of tickers declining to trigger risk_off
REGIME_BEARISH_MEDIAN_CHANGE = -2.0    # median change threshold for risk_off
REGIME_BEARISH_BTC_CHANGE = -4.0       # BTC change alone triggers risk_off
REGIME_BEARISH_COMBO_DECLINE = 60      # softer decline % when combined with BTC drop
REGIME_BEARISH_COMBO_BTC = -3.0        # softer BTC threshold when combined with decline %
# cautious — soft bearish, not a full sell-off but market leaning down, max 3 setups
REGIME_CAUTIOUS_DECLINE_PCT = 55       # >55% of coins declining
REGIME_CAUTIOUS_MEDIAN_CHANGE = -0.5   # median change slightly negative
REGIME_CAUTIOUS_BTC_CHANGE = -2.0      # BTC down 2%+ alone triggers cautious
REGIME_CAUTIOUS_COMBO_DECLINE = 50     # 50%+ declining when combined with BTC drop
REGIME_CAUTIOUS_COMBO_BTC = -1.5       # BTC -1.5%+ when 50%+ declining
# risk_on (bullish) — broad rally, favor longs
REGIME_BULLISH_DECLINE_PCT = 30        # % declining ceiling for risk_on
REGIME_BULLISH_MEDIAN_CHANGE = 2.0     # median change threshold for risk_on
REGIME_BULLISH_BTC_CHANGE = 4.0        # BTC change alone triggers risk_on
REGIME_BULLISH_COMBO_DECLINE = 40
REGIME_BULLISH_COMBO_BTC = 3.0

# Minimum trades before "avoid direction" rule becomes hard
DIRECTION_RULE_MIN_TRADES = 15