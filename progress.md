# Crypto Screener — Progress Tracker

_Last updated: 2026-04-22_

---

## What This Project Does

A personal, automated crypto analyst that runs once a night and delivers the **5 best trading opportunities** on Bybit USDT perpetuals to your Telegram — with full trade plans (entry, stop, targets, R:R). It also self-evaluates past recommendations against actual price data.

```
Bybit API (50 tickers)
    ↓
Python pre-filter (score by volume, funding, price action, OI)
    → Disqualify illiquid coins (<$10M volume, <$50M OI)
    → Rank by interest score
    → Keep top 25 + watchlist
    ↓
Fetch 4 timeframes per coin (15m, 1h, 4h, 1D)
    → RSI(14), EMA 20/50, volume spike ratio, breakout flags
    ↓
Claude (Sonnet 4.6) analyzes against full knowledge base
    → 9 knowledge files: philosophy, risk mgmt, market structure,
      volume analysis, crypto specifics, 7 playbook setups, watchlist, glossary
    → Outputs 5 ranked setups + structured JSON for tracking
    ↓
Telegram delivery (HTML formatted, retry on failure)
    ↓
Archive: brief (markdown) + setups (JSON)
    ↓
Weekly eval: fetches actual prices, scores each setup,
    writes performance summary → Claude reads on future runs (feedback loop)
```

---

## Current Architecture

| File | Lines | Purpose |
|---|---|---|
| `main.py` | 86 | Orchestrator — fetch → analyze → archive → deliver |
| `config.py` | 40 | All settings: API keys, model, limits, watchlist |
| `fetchers/bybit_data.py` | 288 | Bybit API: tickers, multi-TF klines, pre-filter scoring |
| `fetchers/telegram_reader.py` | — | Telethon: reads signal groups (currently disabled) |
| `analyzer/prompts.py` | 161 | System prompt + knowledge loader + performance feedback |
| `analyzer/claude_client.py` | 70 | Anthropic API wrapper with prompt caching |
| `delivery/telegram_bot.py` | 160 | Markdown→HTML conversion, smart chunking, retry logic |
| `weekly_eval.py` | 463 | Evaluation engine: scores past setups, generates summary |
| `knowledge/` (9 files) | — | Full trading knowledge base (01–08 + trading_rules) |

---

## Current Settings

| Setting | Value |
|---|---|
| Model | `claude-sonnet-4-6` |
| Max output tokens | 8000 |
| Broad scan pool | 50 tickers (by turnover) |
| Pre-filter to | 25 coins (by interest score + watchlist) |
| Timeframes | 15m, 1h, 4h, 1D |
| Watchlist (always included) | BTCUSDT, ETHUSDT, SOLUSDT |
| Schedule | Once nightly (launchd, 9pm local) |
| Delivery | Telegram bot (HTML formatted) |

---

## Cost Estimation (Monthly)

### Per Run (once/night)
| Component | Tokens | Cost (Sonnet 4.6) |
|---|---|---|
| System prompt + knowledge | ~16,700 input | ~$0.050 |
| Market data (25 coins × 4 TFs) | ~3,000 input | ~$0.009 |
| Output (5 setups + JSON) | ~6,000-8,000 output | ~$0.090-0.120 |
| **Total per run** | **~28,000** | **~$0.15-0.18** |

### Monthly (30 runs)
| Scenario | Est. Cost |
|---|---|
| Sonnet 4.6 (current) | **~$4.50-5.40/month** |
| Haiku 4.5 (if switched back) | **~$0.50-0.70/month** |

_Note: Prompt caching saves ~90% on system prompt for runs within 5 min of each other, but with once-nightly runs the cache is always cold._

---

## Performance & Win Rate

**Status: Tracking started 2026-04-22. No evaluated setups yet.**

The weekly eval (`weekly_eval.py`) needs 1-7 days of price data after each brief before it can score setups:
- Scalp setups: scored after 1 day
- Intraday setups: scored after 2 days
- Swing setups: scored after 7 days

**First evaluation possible: ~2026-04-29** (run `python weekly_eval.py`)

Once data accumulates, this section will show:
- Overall win rate
- Win rate by setup type (trend pullback, range breakout, etc.)
- Win rate by confidence level (high/medium/low)
- Avg predicted R:R vs actual R:R
- Confidence calibration (do "high" calls actually win more?)

Results are auto-generated in `logs/performance/summary.md` and fed back to Claude.

---

## Changelog

### 2026-04-22 — Major Upgrade Session

**Multi-Timeframe Analysis**
- Added 4-timeframe scanning: 15m, 1h, 4h, 1D (was 1h only)
- Added EMA 20/50 trend detection per timeframe
- Claude now checks multi-TF confluence for every recommendation

**Smarter Coin Selection**
- Broadened initial scan from 20 → 50 tickers
- Added knowledge-based Python pre-filter scoring:
  - Hard disqualifiers: <$10M turnover or <$50M OI (from `02_risk_management`)
  - Volume/liquidity tiers (from `04_volume_analysis`)
  - Funding rate extremes → squeeze potential (from `06_setup_playbook`)
  - Price action magnitude scoring (from `05_crypto_specifics`)
  - Combined signal bonuses: funding squeeze buildup, post-liquidation candidates
- Pre-filter cuts 50 → 25 most interesting coins before any kline fetching

**Always 5 Recommendations**
- Changed output from 0-3 conservative setups to always 5 ranked opportunities
- Each with full trade plan: entry zone, stop, target 1 + target 2, R:R, confidence
- Ranked by R:R, multi-TF confluence, volume confirmation

**Self-Evaluation Feedback Loop**
- Claude outputs structured JSON (`setups_json`) alongside readable brief
- `main.py` parses and archives to `logs/setups/`
- New `weekly_eval.py`: fetches actual prices from Bybit, scores each setup
- Generates `logs/performance/summary.md` with win rate stats
- Claude reads performance summary on future runs → calibrates behavior

**Telegram Delivery Improvements**
- Switched from Markdown to HTML parse mode (no more parse errors)
- Added markdown→HTML converter for Claude's output
- Smart chunking: splits on section boundaries, not mid-sentence
- Retry with backoff on network errors (3 attempts, 2s/4s/6s)
- Fallback to plain text if HTML also fails

**Token Optimization**
- Removed duplicate knowledge files (technical_analysis.md, watchlist.md, README.md, 00_recommended_reading.md)
- Compact JSON format (no indentation) — ~40% smaller market data
- Pre-filtering means Claude only sees 25 pre-scored coins, not raw 50
- System prompt: ~16.7k tokens (down from ~20k+)
- Max output: 4000 → 8000 tokens (needed for 5 setups + JSON block)

### 2026-04-21 — Initial Build

- Basic pipeline: Bybit → Claude (Haiku) → Telegram
- Single timeframe (1h), top 20 movers
- RSI, volume spike, breakout detection
- 0-3 conservative setups, "no trade" valid
- 8 knowledge files written (philosophy through glossary)
- Brief archiving to `logs/briefs/`

---

## What's Next (Backlog)

- [ ] Run first weekly evaluation (after ~7 days of briefs)
- [ ] Enable Telegram signal group reading (add groups to config)
- [ ] Add CoinGlass data (funding history, liquidation heatmap, OI changes)
- [ ] Add on-chain data source (exchange flows via CryptoQuant/Glassnode)
- [ ] Eval script: add time-to-resolution tracking
- [ ] Eval script: compare predicted R:R vs actual R:R
- [ ] Consider switching back to Haiku for cost savings once eval shows quality is sufficient
- [ ] Build a simple dashboard/viewer for past briefs + eval results
- [ ] Phase B prerequisites: 60+ days of journaled Phase A data, documented win rate, risk engine design

---

## Phase Status

**Currently: Phase A — Analyst mode (signal-only)**

Phase B (auto-execution) prerequisites:
1. ❌ 60+ days of Phase A briefs with evaluation data
2. ❌ Documented win rate proving edge (from weekly_eval)
3. ❌ Separate hard-coded risk engine (not Claude) for position sizing
4. ❌ Explicit user approval to begin Phase B
