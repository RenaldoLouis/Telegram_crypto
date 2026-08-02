import os
from dotenv import load_dotenv

load_dotenv()

# === API Keys ===
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
# NOTE: Bybit API key removed — the screener reads only PUBLIC market data
# (get_tickers / get_kline), which needs no auth. Keyless avoids the 90-day
# key expiry and IP-whitelist requirement. Do NOT re-add unless a private
# (account/order) endpoint is ever introduced (Phase B only).
TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", 0))
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# === Setup Source (mechanical-primary / Claude-shadow) ===
# "claude"     — deliver Claude's brief; mechanical setups generated + logged in shadow.
# "mechanical" — deliver mechanical setups; Claude logged in shadow (and skipped if it fails).
# A Claude failure ALWAYS falls back to mechanical delivery regardless of this flag.
PRIMARY_SOURCE = "claude"
MECHANICAL_MODEL_TAG = "mechanical_v1"   # recorded as `model` on mechanical setups for eval

# === Claude Settings ===
CLAUDE_MODEL = "claude-sonnet-4-6"   # use sonnet when tuning
# CLAUDE_MODEL = "claude-haiku-4-5"      # Cheap for daily use;
MAX_TOKENS_OUTPUT = 8000             # 5 detailed setups + JSON block needs ~6-7k tokens
THINKING_BUDGET = 10000              # Extended thinking budget — reasoning tokens (not sent to Telegram)

# === Bybit Settings ===
BYBIT_CATEGORY = "linear"            # USDT perpetuals
TOP_MOVERS_LIMIT = 30                # Screen top 30 by volume (liquidity filter caps real set ~24)
KLINE_INTERVALS = {                  # Multi-timeframe candle config
    "15": 100,                       # 15m — scalp (last ~25h)
    "60": 100,                       # 1h  — intraday (last ~4 days)
    "240": 100,                      # 4h  — higher TF structure (last ~16 days)
    "D": 210,                        # 1D  — trend context (last ~7 months, enough for SMA200)
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

# === Self-Learning (Delta Analysis) Settings ===
DELTA_ANALYSIS_TRADE_THRESHOLD = 25  # Trigger delta analysis after N new evaluated trades (raised 15→25 to cut overfit)
DELTA_ANALYSIS_MIN_TRADES = 20       # Minimum total trades before first delta analysis

# --- Anti-overfit gates for strategic rules & delta insights (audit 2026-07-13) ---
RULE_MIN_SAMPLE = 20          # a prioritize/avoid rule needs >= this many trades
REGIME_RULE_MIN_TRADES = 20   # a regime-specific hard rule needs >= this many trades (was effectively 5)
MAX_ACTIVE_DELTA_INSIGHTS = 6 # cap active delta insights sent to Claude (was unbounded → 20 contradictory rules)
LONG_MIN_CONFLUENCE = 3       # longs require >= 3/4 TF confluence (hard structural gate; longs run -33R)
# Regime-aware long cap: longs are the entire net loss (29% WR / -33R over 181 trades) while shorts
# are ~breakeven (36% / 56). Outside a confirmed risk_on rally, cap the number of longs per run so a
# bearish/neutral tape can't be filled with the losing direction. audit 2026-07-13
LONG_CAP_BY_REGIME = {"risk_off": 1, "cautious": 1, "neutral": 2, "risk_on": 5}
# Symmetric short cap (audit 2026-08-02): mirror of the long cap for the opposite side.
# Shorting a rising tape is the mechanical engine's version of the long-in-a-selloff leak
# — the 07-30 17:38 batch fired 3 shorts in risk_on (all stopped, MFE ~0.10R). Cap shorts
# hard in bullish regimes; leave them uncapped where shorts are the edge (risk_off/cautious).
SHORT_CAP_BY_REGIME = {"risk_off": 5, "cautious": 5, "neutral": 3, "risk_on": 1}
# Per-run same-direction concentration cap (audit 2026-08-02): N identical-direction setups
# in one run from one signal is one bet sized N×, so a single bad read becomes a correlated
# multi-loss streak (both 07-30 batches were 3× trend_pullback_short → 3 simultaneous stops).
# Cap same-direction setups per run so correlated drawdown can't compound. None = no cap.
MAX_SAME_DIRECTION_PER_RUN = 2

# --- Transaction cost model (audit 2026-08-02) -----------------------------------------
# A +0.04R GROSS expectancy is meaningless until it survives real perp costs. Costs are
# a % of notional per side; the eval converts them to R per-trade via each trade's own
# risk_pct (|entry-stop|/entry). That conversion is the whole point: median risk here is
# ~3.1% of price, so a 0.17% round-trip already costs ~0.055R — LARGER than the gross edge.
# Tight-stop setups (small risk_pct) correctly pay MORE R per unit of fee.
COST_MODEL_ENABLED = True
TAKER_FEE_PCT = 0.00055        # Bybit USDT-perp taker fee, each side (~0.055%)
SLIPPAGE_PCT = 0.0003          # assumed slippage each side (entry + exit fill), tunable
FUNDING_PCT_PER_8H = 0.0001    # avg |funding| per 8h, applied as a cost over the hold
FALLBACK_RISK_PCT = 0.031      # median recovered risk_pct — used when a trade's own is unrecoverable

# Canonical rule taxonomy. Claude may ONLY cite these IDs in reasoning.rules_applied.
# Free-text IDs are dropped on save so attribution stays statistically meaningful
# (history had ~120 one-off IDs across 60 setups → every rule was n=1-3 noise).
CANONICAL_RULES = {
    # regime
    "regime_risk_off", "regime_cautious", "regime_neutral", "regime_risk_on",
    # direction / structure
    "short_bias", "long_structural_confirmed", "btc_bearish_guard", "decoupled_alt",
    # setup mechanics
    "validated_signal", "trend_pullback", "range_reversion", "funding_squeeze",
    "setup8_exhaustion", "liquidity_sweep", "post_liquidation",
    # execution
    "tight_t1", "partial_profit", "wait_for_retest", "rank_reeval",
    # confluence / confidence
    "confluence_3of4", "volume_confirmed", "medium_over_high_conf",
    # divergence
    "rsi_divergence", "macd_divergence",
    # risk controls
    "losing_streak_caution", "dead_cat_bounce_risk", "symbol_priority", "symbol_avoid",
}