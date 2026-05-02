# Crypto Screener — Progress Tracker

_Last updated: 2026-05-03_

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
Claude (Haiku 4.5 daily / Sonnet for tuning) analyzes as professional trader
    → Professional trader mindset (don't chase, trap awareness, realistic targets)
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
    → Evaluates NEW setups from last 7 weeks only (not all-time)
    → Loads ALL past evaluations for cumulative learning
    → Fetches actual prices from Bybit for each past setup
    → Scores: triggered? stop or target hit first? actual R:R? MFE?
    → Per-trade prediction vs reality table (Claude sees each failure)
    → Win rate trend: per-run + cumulative + previous vs current comparison
    → Prediction accuracy gap + direction accuracy (via MFE)
    → Aggregates by: setup type, confidence, rank, MODEL
    → Merges manual trade log (logs/trades/my_trades.json) + trader notes
    → Writes logs/performance/summary.md + win_rate_history.json
    → Derives mandatory rules from data (auto-escalates if not improving)
    → Claude reads summary + rules + validation checklist on next run → feedback loop
```

---

## Current Architecture

| File | Lines | Purpose |
|---|---|---|
| `main.py` | 88 | Orchestrator — fetch → analyze → parse JSON → archive → deliver |
| `config.py` | 41 | Settings: API keys, model, limits, timeframes, watchlist |
| `fetchers/bybit_data.py` | 288 | Bybit API: 50 tickers → knowledge-based scoring → top 25 → multi-TF klines |
| `fetchers/telegram_reader.py` | — | Telethon: reads signal groups (currently disabled) |
| `analyzer/prompts.py` | 195 | Professional trader prompt + knowledge + performance feedback + validation checklist + derived rules |
| `analyzer/claude_client.py` | 70 | Anthropic API wrapper with prompt caching + compact JSON |
| `delivery/telegram_bot.py` | 160 | MD→HTML converter, smart section-based chunking, retry with backoff |
| `weekly_eval.py` | 700 | Evaluation engine: MFE tracking, per-trade results table, win rate trend, enriched summary |
| `knowledge/` (9 files) | — | Full trading knowledge base (01–08 + trading_rules) |
| `progress.md` | — | This file — project progress tracker |

### Directory Structure

```
logs/
  briefs/         → Archived markdown briefs (one per run)
  setups/         → Structured JSON per run (symbol, entry, stop, target, model)
  evaluations/    → Scored results per run (win/loss, actual R:R, exit reason)
  trades/
    my_trades.json → Manual trade log with notes/lessons (user-edited)
  performance/
    summary.md            → Rolling stats, per-trade results, win rate trend — Claude reads this
    win_rate_history.json  → Persistent win rate snapshots across eval runs (tracks improvement)
```

---

## Current Settings

| Setting | Value |
|---|---|
| Model | `claude-sonnet-4-6` (current) — model name tracked per setup for comparison |
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

**Status: 8 runs evaluated (32 setups, 28 triggered). Active since 2026-04-22.**

### Current Stats (as of 2026-05-03)
| Metric | Value |
|---|---|
| Overall win rate | **10.7%** (3W / 25L) |
| Avg actual R:R | -0.62 |
| Avg predicted R:R | 2.0 |
| **Prediction gap** | **2.7R** (targets systematically too optimistic) |
| T1 hit rate | 2/28 (7%) — targets are too far |
| Stop loss hit rate | 21/28 (75%) — stops too tight or direction wrong |

### By Confidence Level
| Confidence | Win Rate | Note |
|---|---|---|
| High | 22% (2/9) | Only confidence level with wins |
| Medium | **0% (0/14)** | Zero wins — mandatory rule: R:R >= 3:1 or drop |
| Low | 20% (1/5) | Small sample |

### By Model
| Model | Win Rate | Avg R:R | Trades |
|---|---|---|---|
| claude-haiku-4-5 | 12% | -0.25 | 8 |
| claude-sonnet-4-6 | 6% | -0.81 | 16 |

### Win Rate Trend (per eval run)
| Run Date | Run Win Rate | Cumulative |
|---|---|---|
| 2026-04-22 | 25% | 25.0% |
| 2026-04-22 | 0% | 11.1% |
| 2026-04-23 | 33% | 16.7% |
| 2026-04-25 | 0% | 11.8% |
| 2026-04-25 | 0% | 9.1% |
| 2026-04-26 | 50% | 12.5% |
| 2026-04-28 | 0% | 11.5% |
| 2026-04-29 | 0% | 10.7% |

**⚠️ Win rate is NOT improving. Last 3 runs have 0% win rate.**

### Key Diagnosis
1. **Targets too far**: Only 2/28 setups hit T1. Avg predicted R:R is 2.0 but actual is -0.62.
2. **Stops too tight**: 21/28 hit stop loss. Need MFE data (now tracking) to determine if direction was right but stops too narrow.
3. **Medium confidence = 0% win rate**: 14 trades, 0 wins. Claude now has mandatory rule to drop these unless R:R >= 3:1.
4. **Rank #4-5 are filler**: 1/11 wins (9%). Claude now limited to 1-2 high-conviction setups.

### Manual Trades Logged
| Date | Symbol | Direction | Result | Failure Reason |
|---|---|---|---|---|
| 2026-04-23 | SPKUSDT | long | loss | target_too_far |
| 2026-04-25 | ENJUSDT | long | open | sl_too_tight |

### What the eval tracks
- Overall win rate (W/L, avg R:R)
- Win rate by setup type, confidence level, rank position, **model**
- **Per-trade prediction vs reality table** (predicted R:R vs actual, exit reason, MFE)
- **Win rate trend** per eval run with cumulative tracking
- **Prediction accuracy gap** (avg predicted vs avg actual R:R)
- **Direction accuracy via MFE** (% of trades reaching 0.5R favorable — tracks if direction is right but execution wrong)
- **Entry timing analysis** (flags if stops hit within 2 hours)
- Confidence calibration, recurring failure patterns, trader notes/lessons
- Mandatory performance-based rules auto-derived and injected into Claude's prompt

Results live in `logs/performance/summary.md` + `win_rate_history.json` and are injected into Claude's system prompt.

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

### 2026-05-03 — Feedback Loop Overhaul: Per-Trade Learning, MFE Tracking & Win Rate Trend

**Problem identified**: Claude received aggregate stats ("10.7% win rate") but never saw its specific trade failures. Token-saving changes had compressed all 28 evaluations into summaries, stripping the case-by-case data Claude needs to learn specific patterns. Claude also acknowledged mandatory rules in text but still violated them (e.g., including medium-confidence setups with R:R < 3:1).

**Per-Trade Prediction vs Reality Table** (`weekly_eval.py`)
- New "Your Predictions vs Reality" section in summary.md showing every individual evaluated trade
- Each row: date, symbol, direction, timeframe, confidence, TF confluence, predicted R:R, actual R:R, exit reason, MFE
- Claude now sees exactly which trades failed and by how much — not just aggregate stats
- Shows last 20 evaluated trades (compact table format, ~500 tokens)

**Max Favorable Excursion (MFE) Tracking** (`weekly_eval.py`)
- `evaluate_setup()` now tracks `max_favorable_rr` — how far price moved in Claude's predicted direction before the outcome
- Also tracks `candles_to_exit` — how quickly the stop was hit
- This is the critical diagnostic: if MFE is high but trades still lose → direction is right, stops too tight. If MFE is low → direction calls are wrong.
- Old evaluations show "n/a" (backward compatible). New evals will populate going forward.

**Prediction Accuracy Gap Metric**
- Computed and displayed: avg predicted R:R (2.0) vs avg actual R:R (-0.62) = **2.7R gap**
- Auto-generates mandatory rule when gap > 1.5R: "Your targets are SYSTEMATICALLY too optimistic"
- Direction accuracy diagnosis auto-generated once MFE data accumulates

**Entry Timing Analysis**
- Flags when >40% of stop-outs happen within 2 hours (8 candles on 15m) — indicates entries are too early

**Win Rate Trend Tracking**
- New `logs/performance/win_rate_history.json` — persistent snapshots of win rate after each eval run
- New "Win Rate Trend" table in summary.md — per-run win rate + cumulative win rate, chronologically
- Previous vs current comparison in overall stats: `**Win rate: 10.7%** (↓ -2.0% from previous eval) ⚠️ REGRESSION`
- Auto-alerts: flags "last 3 runs 0% win rate" or "win rate NOT improving"
- Mandatory rule derived from trend: if win rate not improving → "make BIGGER changes, not incremental tweaks"
- If win rate IS improving → "maintain current approach, don't loosen criteria"

**Pre-Inclusion Validation Checklist** (`prompts.py`)
- Added 6-point mandatory checklist Claude must run for EVERY setup before including it:
  1. Confidence + R:R pass performance rules
  2. TF confluence >= 3/4
  3. T1 within distance limits (scalp <1.5%, intraday <3%, swing <5%)
  4. Stop loss wide enough (scalp >=1%, intraday >=2%, swing >=3%)
  5. Not a chase (>5% move without pullback)
  6. Setup type has proven track record
- Failing any check → setup must be dropped to Risk Flags, not included

**Stronger Rule Enforcement** (`prompts.py`)
- Added explicit override clause: "MANDATORY Performance-Based Rules are NON-NEGOTIABLE. You must NOT include a setup that violates any mandatory rule, even if you think the setup looks good."
- Changed "Output 1 to 5 setups" → "Output 0 to 5 setups" with emphasis that 0 is valid

**Duplicate Elimination**
- Removed standalone trader notes section from `build_system_prompt()` — same data was already in summary.md's trade-by-trade section
- Saves ~300 tokens per run with no information loss

**Token Impact**: +700 tokens net (from ~19.3k to ~20k). Minimal cost increase for dramatically better learning signal.

### 2026-04-25 — Eval Bug Fix, Enriched Trade Journal & Token Cost Control

**Weekly Eval Bug Fix — Partial Evaluation Support**
- Fixed bug where a single "too early" setup would skip the entire run (swing setups blocked intraday setups from being evaluated)
- Changed from `break` (abort run) to `continue` (skip individual setup, evaluate the rest)
- Added partial eval tracking: runs with some setups still "too early" are re-queued on next eval run
- Merges new results into existing eval files — no duplicates, no missed setups
- Example: April 22 run has 3 intraday setups (2-day window) that were blocked by 2 swing setups (7-day window). Now the intraday ones get evaluated immediately, swing ones merge in later.

**Enriched Trade Journal Format**
- Each manual trade in `my_trades.json` now includes a `claude_recommendation` object linking back to Claude's original suggestion:
  - rank, model, setup_type, timeframe, confidence, tf_confluence
  - Full entry zone, SL, T1, T2, predicted R:R
- Added `failure_reason` tag per trade (e.g. `sl_too_tight`, `target_too_far`) for pattern aggregation
- Added `"open"` as a valid trade result (not counted in win/loss stats)
- Summary now shows:
  - **Recurring Failure Patterns** — aggregated failure categories so Claude sees what keeps going wrong
  - **Trade-by-Trade Analysis** — trader's actual execution side-by-side with Claude's recommendation, showing exactly where and why setups failed
  - Each trade entry: trader's execution, Claude's recommendation, lesson learned, failure category

**Token Cost Control for Feedback Loop**
- Capped trade-by-trade analysis in `summary.md` to last 10 trades (was unbounded)
- Capped trader notes injection in `prompts.py` to last 10 notes (was unbounded)
- Aggregate stats (win rate tables, failure patterns) remain uncapped — they summarize all history in fixed-size tables
- Without cap: 100 trades would add ~3,000–5,000 tokens per run. With cap: stays ~1,000–1,500 tokens regardless of history size
- Older trades still contribute to aggregate stats, just not shown individually to Claude

**New Trade Logged: ENJUSDT**
- Entry 0.06060, SL 0.0595 (from run 20260425_0751, Claude rank #3, haiku-4.5)
- Note: SL too tight — only 1.8% from entry, high risk of noise stop-out
- Tagged as `failure_reason: sl_too_tight`

### 2026-04-24 — Professional Trader Prompt & Trade Journal

**System Prompt Overhaul — Professional Trader Mindset**
- Rewrote Claude's identity from "disciplined analyst" to "professional crypto derivatives trader"
- Added 6 professional trading rules enforced in every analysis:
  - **Don't Chase**: rejects entries after >5% moves without pullback, respects overbought RSI
  - **BTC Correlation**: flags all alt longs as suspect when BTC drops >3%
  - **Liquidity & Trap Awareness**: warns about stop hunts at obvious levels, liquidity sweeps
  - **Realistic Targets**: Target 1 must be next actual S/R, not a dream level (learned from SPK trade)
  - **Position Management**: breakeven levels, partial TP guidance for every setup
  - **When to Skip**: extended moves, low-volume breakouts, crowded funding, news spikes
- Added "trap check" field to every setup output (what could go wrong)
- Added conflict resolution rules for disagreeing timeframes
- Market structure phase identification now mandatory (Accumulation/Markup/Distribution/Markdown)
- Token impact: ~800 tokens extra (~2300 vs ~1500), still within budget

**Manual Trade Journal**
- Created `logs/trades/my_trades.json` — user logs actual trades with entry, exit, result, and free-text notes
- Notes/lessons are injected directly into Claude's system prompt on every run
- First entry: SPKUSDT loss — "targets were too far, should have TP'd at 0.05255"

**Weekly Eval Improvements**
- Eval now only fetches klines for setups from last 7 weeks (prevents bloat after months of running)
- But always loads ALL past evaluation results for cumulative learning (summary uses full history)
- Three-phase design: (1) load all past evals, (2) evaluate new setups within 7-week window, (3) generate summary from everything
- Summary now includes "Trader's Actual Trades" section with manual log table
- Summary includes "Trader Notes & Lessons" section — fed back to Claude for self-improvement

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
- [ ] Wait for pending evals to mature (swing setups from Apr 26, 28, May 2 need 7 days)
- [ ] Run eval after May 5 to get first MFE data and see if validation checklist improves results
- [ ] Update ENJ trade result once closed (win/loss, actual exit)
- [ ] Review MFE data once available: is direction right but stops too tight, or are direction calls wrong?
- [ ] If win rate still not improving after 2 more evals, consider: switching to higher-TF-only setups, reducing to max 1-2 setups, or adding volume spike as hard requirement
- [x] Fix feedback loop: add per-trade results table so Claude sees specific failures
- [x] Add MFE tracking to diagnose direction vs execution problems
- [x] Add win rate trend tracking with previous vs current comparison
- [x] Add validation checklist to enforce rules Claude was violating
- [x] Fix duplicate trader notes wasting tokens
- [x] Add prediction accuracy gap metric
- [x] Fix eval bug: partial evaluation support (swing no longer blocks intraday)
- [x] Enrich trade journal: link each trade to Claude's recommendation + failure categories
- [x] Cap feedback loop token cost: last 10 trades/notes in prompt, aggregates uncapped
- [x] Try a few runs on Haiku to start model comparison data (switched daily to Haiku 4.5)
- [x] Upgrade system prompt to professional trader mindset
- [x] Add manual trade journal with notes/lessons fed back to Claude
- [x] Weekly eval: 7-week window for new evals + cumulative learning from all history

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
