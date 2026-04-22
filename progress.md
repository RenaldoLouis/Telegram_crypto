# Crypto Screener — Progress Tracker

_Last updated: 2026-04-22_

---

## What This Project Does

A personal, automated crypto analyst that runs once a night and delivers the **5 best trading opportunities** on Bybit USDT perpetuals to your Telegram — with full trade plans (entry, stop, targets, R:R). It self-evaluates past recommendations against actual price data and feeds results back to Claude.

```
Bybit API (50 tickers, single call)
    ↓
Python pre-filter (knowledge-based scoring, free)
    → Disqualify: <$10M turnover or <$50M OI
    → Score by: price action, funding extremes, liquidity, OI+move combos
    → Keep top 25 + watchlist (BTC, ETH, SOL)
    ↓
Fetch 4 timeframes per coin (15m, 1h, 4h, 1D)
    → RSI(14), EMA 20/50, volume spike ratio, breakout flags per TF
    ↓
Claude (Sonnet 4.6) analyzes against full knowledge base (9 files)
    → Multi-TF confluence scoring (4/4=High, 3/4=Medium, 2/4=Low)
    → Outputs 5 ranked setups (readable brief) + structured JSON
    ↓
main.py parses JSON → saves to logs/setups/
    ↓
Brief archived to logs/briefs/ (clean, no JSON)
    ↓
Telegram delivery (HTML formatted, retry on failure, plain text fallback)
    ↓
Weekly eval (weekly_eval.py, run Sundays)
    → Fetches actual prices from Bybit for each past setup
    → Scores: triggered? stop or target hit first? actual R:R?
    → Aggregates by: setup type, confidence, rank, MODEL
    → Writes logs/performance/summary.md
    → Claude reads summary on next run → feedback loop
```

---

## Current Architecture

| File | Lines | Purpose |
|---|---|---|
| `main.py` | 88 | Orchestrator — fetch → analyze → parse JSON → archive → deliver |
| `config.py` | 41 | Settings: API keys, model, limits, timeframes, watchlist |
| `fetchers/bybit_data.py` | 288 | Bybit API: 50 tickers → knowledge-based scoring → top 25 → multi-TF klines |
| `fetchers/telegram_reader.py` | — | Telethon: reads signal groups (currently disabled) |
| `analyzer/prompts.py` | 161 | System prompt + knowledge loader + performance feedback injection |
| `analyzer/claude_client.py` | 70 | Anthropic API wrapper with prompt caching + compact JSON |
| `delivery/telegram_bot.py` | 160 | MD→HTML converter, smart section-based chunking, retry with backoff |
| `weekly_eval.py` | 495 | Evaluation engine: scores setups, tracks by model, generates summary |
| `knowledge/` (9 files) | — | Full trading knowledge base (01–08 + trading_rules) |
| `progress.md` | — | This file — project progress tracker |

### Directory Structure

```
logs/
  briefs/         → Archived markdown briefs (one per run)
  setups/         → Structured JSON per run (symbol, entry, stop, target, model)
  evaluations/    → Scored results per run (win/loss, actual R:R, exit reason)
  performance/
    summary.md    → Rolling stats — Claude reads this on every future run
```

---

## Current Settings

| Setting | Value |
|---|---|
| Model | `claude-sonnet-4-6` |
| Max output tokens | 8000 |
| Broad scan pool | 50 tickers (by turnover) |
| Pre-filter to | 25 coins (by knowledge-based interest score + watchlist) |
| Timeframes | 15m, 1h, 4h, 1D |
| Indicators per TF | RSI(14), EMA 20, EMA 50, volume spike ratio, 20-candle breakout |
| Watchlist (always included) | BTCUSDT, ETHUSDT, SOLUSDT |
| Schedule | Once nightly (launchd, 9pm local) |
| Delivery | Telegram bot (HTML formatted) |

---

## Cost Estimation (Monthly)

### Per Run (once/night)
| Component | Tokens | Cost (Sonnet 4.6) | Cost (Haiku 4.5) |
|---|---|---|---|
| System prompt + knowledge | ~16,700 input | $0.050 | $0.013 |
| Market data (25 coins × 4 TFs) | ~3,000 input | $0.009 | $0.002 |
| Output (5 setups + JSON) | ~6,000-8,000 output | $0.090-0.120 | $0.024-0.032 |
| **Total per run** | **~28,000** | **~$0.15-0.18** | **~$0.04-0.05** |

### Monthly (30 runs)
| Model | Est. Cost |
|---|---|
| **Sonnet 4.6 (current)** | **$4.50-5.40/month** |
| Haiku 4.5 | $1.20-1.50/month |

_Prompt caching saves ~90% on system prompt for runs within 5 min, but once-nightly runs always have cold cache._

---

## Performance & Win Rate

**Status: Tracking started 2026-04-22. No evaluated setups yet.**

The weekly eval needs price data after each brief before scoring:
- Scalp setups: scored after 1 day
- Intraday setups: scored after 2 days
- Swing setups: scored after 7 days

**First evaluation possible: ~2026-04-29** (run `python weekly_eval.py`)

### What the eval tracks
- Overall win rate (W/L, avg R:R)
- Win rate by setup type (trend pullback, range breakout, spring, etc.)
- Win rate by confidence level (high/medium/low)
- Win rate by rank position (#1 through #5)
- **Win rate by model** (Sonnet vs Haiku comparison)
- Avg predicted R:R vs actual R:R
- Confidence calibration (do "high" calls actually win more?)
- Actionable insights auto-generated for Claude's future runs

Results live in `logs/performance/summary.md` and are injected into Claude's system prompt.

---

## Pre-Filter Scoring Logic

The Python pre-filter uses rules extracted from the knowledge base to score 50 tickers before any kline fetching:

### Hard Disqualifiers
| Rule | Threshold | Source |
|---|---|---|
| Low turnover | < $10M 24h turnover | `02_risk_management` |
| Low open interest | < $50M OI | `02_risk_management` |

### Scoring Factors
| Factor | Thresholds | Max Points | Source |
|---|---|---|---|
| Liquidity | $50M→1pt, $100M→2, $500M→3, $1B+→4 | 4 | `04_volume_analysis` |
| Price action | 1.5%→1, 3%→2, 5%→3, 10%→4, 15%+→5 | 5 | `05_crypto_specifics` |
| Funding extremes | ±0.01%→1, ±0.03%→3, ±0.05%+→5 | 5 | `04_volume_analysis`, `06_setup_playbook` |
| High OI + big move | $200M+ OI and >5% change | 2 | `04_volume_analysis` |
| Funding squeeze buildup | Extreme funding but price flat (<3%) | 3 | `06_setup_playbook` Setup 5 |
| Post-liquidation candidate | >10% move + >$200M turnover | 2 | `06_setup_playbook` Setup 6 |

---

## Changelog

### 2026-04-22 — Major Upgrade Session

**Multi-Timeframe Analysis**
- Added 4-timeframe scanning: 15m, 1h, 4h, 1D (was 1h only)
- Added EMA 20/50 trend detection per timeframe
- Claude checks multi-TF confluence for every recommendation (4/4=High, 3/4=Med, 2/4=Low)

**Knowledge-Based Python Pre-Filter**
- Broadened initial scan from 20 → 50 tickers (single API call)
- Hard disqualifiers: <$10M turnover or <$50M OI (from `02_risk_management`)
- Multi-factor scoring: liquidity, price action magnitude, funding extremes, OI+move combos, squeeze buildup, post-liquidation signals
- All thresholds derived from knowledge files, not arbitrary
- Pre-filter cuts 50 → 25 before any kline fetching (halves Bybit API calls)

**Always 5 Recommendations**
- Changed from 0-3 conservative setups to always 5 ranked opportunities
- Each with: multi-TF analysis, trade plan (entry/stop/target1/target2/R:R), confidence level
- Ranked by: R:R ratio, multi-TF confluence, volume confirmation, setup clarity

**Self-Evaluation Feedback Loop**
- Claude outputs structured JSON (`setups_json`) alongside readable brief
- `main.py` parses and archives to `logs/setups/` with model name
- `weekly_eval.py`: fetches actual 15m klines from Bybit, scores each setup
- Checks: entry triggered? → stop hit first or target? → actual R:R
- Aggregates stats by: setup type, confidence, rank, **model**
- Generates `logs/performance/summary.md` with actionable insights
- Claude reads performance summary on future runs → self-calibration

**Model Tracking**
- Every setup JSON records which Claude model generated it
- Weekly eval tracks win rate and avg R:R per model
- Enables future Sonnet vs Haiku comparison to find cost-effective option

**Telegram Delivery Improvements**
- Switched from Markdown to HTML parse mode (eliminates parse errors)
- Markdown→HTML converter handles `**bold**`, `*italic*`, `##` headers, `---` dividers
- Smart chunking: splits on section boundaries (`━━━` lines), not mid-sentence
- Retry with backoff on network errors (3 attempts: 2s, 4s, 6s delays)
- Fallback to plain text if HTML also fails
- 30s timeout per request

**Token Optimization**
- Removed 4 duplicate/unnecessary knowledge files (technical_analysis.md, watchlist.md, README.md, 00_recommended_reading.md)
- Compact JSON format (`separators=(',',':')`) — ~40% smaller market data
- Pre-filtering: Claude sees 25 pre-scored coins, not raw 50
- System prompt: ~16.7k tokens (down from ~20k+)
- Max output: 8000 tokens (5 setups + JSON block)

### 2026-04-21 — Initial Build

- Basic pipeline: Bybit → Claude (Haiku) → Telegram
- Single timeframe (1h), top 20 movers
- RSI(14), volume spike detection, 20-candle breakout
- 0-3 conservative setups, "no trade" valid output
- 8 knowledge files written (trading philosophy through glossary)
- Brief archiving to `logs/briefs/`

---

## What's Next (Backlog)

### Short Term (next 1-2 weeks)
- [ ] Run first weekly evaluation (~2026-04-29)
- [ ] Review first eval results, adjust prompt if needed
- [ ] Try a few runs on Haiku to start model comparison data

### Medium Term (next 1-2 months)
- [ ] Enable Telegram signal group reading (add groups to config)
- [ ] Add CoinGlass data (funding history, liquidation heatmap, OI changes)
- [ ] Add on-chain data source (exchange flows via CryptoQuant/Glassnode)
- [ ] Compress multi-TF analysis in prompt to save output tokens
- [ ] Build a simple dashboard/viewer for past briefs + eval results

### Long Term (Phase B prerequisites)
- [ ] 60+ days of Phase A briefs with evaluation data
- [ ] Documented win rate proving edge (from weekly_eval)
- [ ] Separate hard-coded risk engine (not Claude) for position sizing
- [ ] Explicit user approval to begin Phase B

---

## Phase Status

**Currently: Phase A — Analyst mode (signal-only)**

The human makes every trading decision. Claude surfaces setups. No auto-execution.

Phase B (auto-execution) will only be considered after:
1. 60+ days of evaluated Phase A data
2. Proven edge from weekly_eval (win rate + R:R)
3. Hard-coded risk engine built (position sizing, stop enforcement — NOT Claude)
4. Model comparison data (Sonnet vs Haiku accuracy)
5. Explicit user approval
