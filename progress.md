# Crypto Screener — Progress Tracker

_Last updated: 2026-05-21 (v5)_

---

## What This Project Does

A personal, automated crypto analyst that runs once a night and delivers the **5 best trading opportunities** on Bybit USDT perpetuals to your Telegram — with full trade plans (entry, stop, targets, R:R). It self-evaluates past recommendations against actual price data and feeds results back to Claude.

```
Momentum Pulse (every 4h, GitHub Actions, free)
    → Bybit API: fetch 50 tickers (single call)
    → Compare vs previous snapshot → detect volume/price acceleration
    → Flag coins: big move (>8% + >$200M), vol accel (>3x), funding squeeze
    → Save to logs/momentum/hot_list.json (48h expiry)
    → Telegram alert for new flags
    ↓
Bybit API (50 tickers, single call)
    ↓
Python pre-filter (knowledge-based scoring, free)
    → Load hot list (dynamic watchlist from pulse)
    → Disqualify: <$10M turnover or <$50M OI
    → Score by: price action, funding extremes, liquidity, OI+move combos
    → Volume acceleration bonus: hot list coins get +2 (>2x) or +4 (>5x)
    → Keep top 25 + watchlist (BTC, ETH, SOL) + hot list
    ↓
Fetch 4 timeframes per coin (15m, 1h, 4h, 1D)
    → RSI(14), EMA 20/50, volume spike ratio, breakout flags per TF
    ↓
Claude (Sonnet 4.6 daily) analyzes as professional trader
    → Professional trader mindset (don't chase, trap awareness, realistic targets)
    → Multi-TF confluence scoring (4/4=High, 3/4=Medium, 2/4=Low)
    → R:R floor: 1.5:1 minimum (lowered from 2:1 based on 98-trade backtest)
    → Outputs 1-5 ranked setups (readable brief) + structured JSON
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
    → Breakeven stop model: after T1 hit, stop moves to entry (0R worst case, not -1R)
    → Partial profit model: blended_rr = 50% at T1 + 50% trails with BE stop
    → Tiered Knowledge Distillation:
      Layer 1: lifetime_stats.json — incremental running counters (O(1) update, no file re-reads)
      Layer 2: strategic_rules.md — compact algorithmic rules (~500 tokens, sent to Claude)
      Layer 3: recent_performance.md — rolling 4-week trade details (~800 tokens, sent to Claude)
      Human:  summary.md — full report with all tables (NOT sent to Claude)
    → Claude reads strategic_rules + recent_performance + validation checklist → feedback loop
    → Total performance tokens: ~1,300 (FIXED regardless of history length)
    ↓
Quarterly deep analysis (quarterly_analysis.py, run every ~3 months)
    → Feeds lifetime_stats.json + recent trades to Claude
    → Finds non-obvious patterns: temporal, symbol-specific, interaction effects
    → Appends qualitative insights to strategic_rules.md
```

---

## Current Architecture

| File | Lines | Purpose |
|---|---|---|
| `main.py` | 88 | Orchestrator — fetch → analyze → parse JSON → archive → deliver |
| `config.py` | 51 | Settings: API keys, model, limits, timeframes, watchlist, momentum thresholds |
| `fetchers/bybit_data.py` | 340 | Bybit API: 50 tickers → scoring + hot list → top 25 → multi-TF klines |
| `fetchers/telegram_reader.py` | — | Telethon: reads signal groups (currently disabled) |
| `analyzer/prompts.py` | 60 | Professional trader prompt + knowledge + tiered performance feedback |
| `analyzer/claude_client.py` | 70 | Anthropic API wrapper with prompt caching + compact JSON |
| `delivery/telegram_bot.py` | 160 | MD→HTML converter, smart section-based chunking, retry with backoff |
| `momentum_pulse.py` | 170 | Lightweight momentum detector — runs every 4h on GitHub Actions (zero Claude tokens) |
| `weekly_eval.py` | 1630 | Evaluation engine + BE stop/partial profit model + tiered knowledge distillation |
| `quarterly_analysis.py` | 130 | Claude-powered deep pattern analysis (run every ~3 months) |
| `knowledge/` (9 files) | — | Full trading knowledge base (01–08 + trading_rules) |
| `.github/workflows/` | — | GitHub Actions: momentum pulse every 4h (secrets via repo settings) |
| `progress.md` | — | This file — project progress tracker |

### Directory Structure

```
logs/
  briefs/         → Archived markdown briefs (one per run)
  setups/         → Structured JSON per run (symbol, entry, stop, target, model)
  evaluations/    → Scored results per run (win/loss, actual R:R, exit reason)
  trades/
    my_trades.json → Manual trade log with notes/lessons (user-edited)
  momentum/
    hot_list.json      → Active momentum-flagged coins (dynamic watchlist, 48h expiry)
    last_snapshot.json  → Previous pulse data (for delta detection between runs)
  performance/
    lifetime_stats.json    → Layer 1: Incremental running counters (backing data, not sent to Claude)
    strategic_rules.md     → Layer 2: Compact algorithmic rules (~500 tokens, sent to Claude)
    recent_performance.md  → Layer 3: Rolling 4-week trade details (~800 tokens, sent to Claude)
    summary.md             → Human-readable full report (NOT sent to Claude)
    win_rate_history.json  → Persistent win rate snapshots across eval runs
    quarterly/             → Deep analysis logs from quarterly_analysis.py
```

---

## Current Settings

| Setting | Value |
|---|---|
| Model | `claude-sonnet-4-6` (current) — model name tracked per setup for comparison |
| Max output tokens | 8000 |
| Broad scan pool | 50 tickers (by turnover) |
| Pre-filter to | 25 coins (by knowledge-based interest score + watchlist + hot list) |
| Timeframes | 15m, 1h, 4h, 1D |
| Indicators per TF | RSI(14), EMA 20, EMA 50, volume spike ratio, 20-candle breakout |
| Watchlist (always included) | BTCUSDT, ETHUSDT, SOLUSDT + momentum pulse hot list |
| Momentum pulse | Every 4h on GitHub Actions (zero Claude tokens) |
| Schedule | Nightly screener (launchd, 9pm local) + momentum pulse (GitHub Actions, every 4h) |
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

### Momentum Pulse Cost (separate from main scan)
| Resource | Per Run | Monthly (180 runs) | Cost |
|---|---|---|---|
| Bybit API | 1 call | 180 calls | $0 |
| Claude API | 0 calls | 0 | **$0** |
| Telegram | 0-1 msg | ~30-60 msgs | $0 |
| GitHub Actions | ~45 sec | ~135 min | **$0** (free tier: 2,000 min/month) |

_Prompt caching saves ~90% on system prompt for runs within 5 min, but once-nightly runs always have cold cache._

---

## Performance & Win Rate

**Status: 28 runs evaluated (101 trades triggered, 111 total setups). Active since 2026-04-22.**

### Current Stats (as of 2026-05-19)
| Metric | Value |
|---|---|
| Overall win rate | **37.6%** (38W / 63L) |
| Avg actual R:R | -0.06 |
| Avg predicted R:R | 2.1 |
| **Prediction gap** | **2.2R** (targets still optimistic — R:R floor lowered to 1.5:1 to address) |
| T1 hit rate | 33/101 (33%) |
| Direction accuracy (MFE ≥ 0.5R) | **65%** (56/70 with MFE data) — direction usually right |
| Avg MFE | 1.2R |
| Simulated T1 at 0.75R | **76% hit rate** (vs 33% current) |
| Simulated T1 at 1.0R | **62% hit rate** |

### By Confidence Level
| Confidence | Win Rate | Trades | Note |
|---|---|---|---|
| High | 22% (2/9) | 9 | Worse than medium — calibration issue |
| Medium | **41% (30/73)** | 73 | Best performing |
| Low | 32% (6/19) | 19 | Acceptable |

### By Model
| Model | Win Rate | Avg R:R | Trades |
|---|---|---|---|
| claude-sonnet-4-6 | **40%** | -0.02 | 89 |
| claude-haiku-4-5 | 12% | -0.25 | 8 |

### Win Rate Trajectory
| Date | Total Evaluated | Win Rate | Avg R:R |
|---|---|---|---|
| 2026-05-02 | 28 | 10.7% | -0.62 |
| 2026-05-04 | 29 | 10.3% | -0.64 |
| 2026-05-06 | 35 | 22.9% | -0.40 |
| 2026-05-07 | 37 | 27.0% | -0.34 |
| 2026-05-10 | 56 | 35.7% | -0.17 |
| 2026-05-14 | 80 | 38.8% | -0.06 |
| 2026-05-16 | 96 | 39.6% | -0.02 |
| 2026-05-19 | 101 | **37.6%** | **-0.06** |

**Win rate dramatically improved from 10.7% → peak 39.6%. Recent dip to 37.6% from 0/5 streak (May 16-17). Monthly: April 16% → May 47%. Feedback loop working.**

### Key Diagnosis
1. **Direction is right (65% reach 0.5R+ MFE)** but targets too far — execution problem, not analysis problem. R:R floor lowered from 2:1 to 1.5:1 to allow realistic T1 placement.
2. **High confidence is miscalibrated**: 22% WR vs medium at 41%. Flagged in strategic rules.
3. **Swing trades failing**: 11% WR (1/9). Short trades: 0% WR (0/3). Both flagged to avoid.
4. **Rank #2 outperforms #1**: 48% vs 32% WR. Ranking criteria flagged for review.
5. **T1 hit rate at 33%** but simulated backtest shows 76% at 0.75R, 62% at 1.0R — proving targets are the bottleneck.
6. **Partial profit model introduced**: 50% at T1 + BE stop should convert many "direction right, target missed" losses into breakeven or small wins. Data will accumulate from next eval run.

### What the eval tracks
- Overall win rate (W/L, avg R:R)
- **Blended R:R (partial profit model)**: 50% at T1 + 50% trails with BE stop → blended win rate and avg R:R
- **Breakeven stop model**: after T1 hit, stop moves to entry — trades scored as BE (0R) not full loss (-1R)
- Win rate by setup type, confidence level, rank position, **model**, timeframe, direction, **symbol**
- **Per-trade prediction vs reality table** (predicted R:R vs actual vs blended, exit reason, MFE)
- **Simulated closer-T1 backtest** — what would happen if T1 were at 0.75R and 1.0R
- **Win rate trend** per eval run with cumulative tracking + monthly trends
- **Prediction accuracy gap** (avg predicted vs avg actual R:R)
- **Direction accuracy via MFE** (% of trades reaching 0.5R favorable)
- **Per-symbol performance** — tracks which coins consistently win/lose
- **Entry timing analysis** (flags if stops hit within 2 hours)
- **Partial profit breakdown**: t1_then_t2, t1_then_be, t1_then_expire counts
- Confidence calibration, recurring failure patterns, trader notes/lessons
- Prescriptive rules auto-derived from `lifetime_stats.json` with specific ACTIONs

### How evaluation data reaches Claude (Tiered Knowledge Distillation)

| Layer | File | Tokens | Scales? | Purpose |
|---|---|---|---|---|
| 1. Lifetime Stats | `lifetime_stats.json` | N/A (backing data) | Grows slowly | Incremental counters — O(1) update per eval |
| 2. Strategic Rules | `strategic_rules.md` | ~500 | **Fixed** | Compact algorithmic rules from all history |
| 3. Recent Window | `recent_performance.md` | ~800 | **Fixed** (rolling) | Last 4 weeks of trade-by-trade outcomes |
| Human Report | `summary.md` | ~2K+ | Grows | Full tables for human review (NOT sent to Claude) |
| Quarterly Insights | Appended to `strategic_rules.md` | ~300 | **Fixed** | Claude-powered deep patterns every ~3 months |

**Total performance context in Claude's prompt: ~1,300 tokens** — regardless of running for 1 month or 3 years. Previous approach would grow to ~6K+ tokens after a year.

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
| Volume acceleration | Hot list coin with >2x→+2, >5x→+4 | 4 | `momentum_pulse.py` hot list |

---

## Changelog

### 2026-05-21 (v5) — Momentum Pulse: Intra-Day Momentum Detection via GitHub Actions

**Problem**: The system only scanned 1-2x daily. Fast-moving coins (like HYPE's +15.8% spike) were missed entirely because they started moving between scans. By the time the nightly scan ran, the move was already extended. The static watchlist (BTC/ETH/SOL) couldn't adapt to new momentum.

**3 Features (all zero Claude cost)**:

**1. Momentum Pulse Scanner** (`momentum_pulse.py`, new file)
- Standalone script that runs every 4 hours on GitHub Actions (free tier, ~135 min/month of 2,000 min quota)
- Single Bybit API call per run — fetches 50 tickers, compares against previous snapshot
- Three detection criteria (any one triggers a flag):
  - **Big move**: >8% price change AND >$200M turnover
  - **Volume acceleration**: turnover >3x the previous pulse (detects ramping volume before it's obvious)
  - **Funding squeeze**: |funding| >0.05% AND price moving >3%
- Saves flagged coins to `logs/momentum/hot_list.json` (48h auto-expiry)
- Saves snapshot to `logs/momentum/last_snapshot.json` for next comparison
- Sends Telegram alert immediately for newly flagged coins
- First run caught: HYPEUSDT (+15.8%), ZECUSDT (+15.6%), BSBUSDT (+23.2%)

**2. Dynamic Watchlist — Hot List Integration** (`fetchers/bybit_data.py`)
- `get_full_market_snapshot()` now loads `hot_list.json` at the start via `_load_hot_list()`
- Hot list symbols merged into watchlist alongside BTC/ETH/SOL
- Hot list coins bypass disqualification filters (same protection as static watchlist)
- Expired entries (>48h) automatically pruned on load

**3. Volume Acceleration Bonus in Pre-Filter** (`fetchers/bybit_data.py`)
- `_ticker_interest_score()` now accepts optional `hot_map` parameter
- Coins on the hot list with volume acceleration >2x get +2 bonus points
- Coins with >5x acceleration get +4 bonus points
- This prioritizes coins that are ramping up even if their absolute metrics are moderate

**GitHub Actions Deployment** (`.github/workflows/momentum_pulse.yml`)
- Runs on `cron: '0 */4 * * *'` (every 4h UTC) + manual trigger via `workflow_dispatch`
- Secrets stored as GitHub repository secrets (BYBIT_API_KEY, BYBIT_API_SECRET, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
- Auto-commits `hot_list.json` and `last_snapshot.json` back to the repo
- `scan` alias updated to `git pull` first, so local runs get the latest hot list

**Security Hardening**
- Scrubbed `screener_session.session`, `.DS_Store`, and all `__pycache__/*.pyc` files from entire git history using `git-filter-repo`
- Enhanced `.gitignore`: added `__pycache__/`, `*.pyc`, `venv/`, `.DS_Store`, `screener_session.session`
- Fixed error handlers in `telegram_bot.py` and `momentum_pulse.py` to print only status codes, not full `r.text` (prevents metadata leakage)
- All secrets verified: no hardcoded values in any `.py` file, GitHub Actions uses `${{ secrets.X }}` only

**New terminal shortcuts** (`~/.zshrc`):
- `scan` — now includes `git pull --quiet` to sync hot list before running
- `pulse` — run momentum pulse locally

**Config additions** (`config.py`):
- `MOMENTUM_PULSE_EXPIRY_HOURS = 48`
- `MOMENTUM_BIG_MOVE_PCT = 8.0`, `MOMENTUM_BIG_MOVE_TURNOVER = 200M`
- `MOMENTUM_VOLUME_ACCEL_THRESHOLD = 3.0`
- `MOMENTUM_FUNDING_EXTREME_PCT = 0.05`, `MOMENTUM_FUNDING_MOVE_PCT = 3.0`

**Cost impact**: Zero. Momentum pulse uses zero Claude tokens, 1 Bybit API call/run, GitHub Actions free tier. Main scan token usage unchanged (~28k/run) — hot list is only used for Python pre-filtering, not sent to Claude.

### 2026-05-19 (v4) — Execution Fix: Breakeven Stops, Partial Profits & Realistic R:R Floor

**Problem**: After 98 evaluated trades, the data showed a clear pattern: Claude picks direction correctly 65% of the time (avg MFE 1.15R), but targets at 2.0-2.5R are unreachable for most trades. T1 hit rate was only 33%. Worse, trades where T1 was hit but price later reversed to stop were scored as full -1.0R losses — even though in real trading you'd move stop to breakeven after T1. The hard R:R >= 2:1 rule in the prompt was forcing Claude to set unrealistic targets, contradicting the strategic rules that said "set T1 at max 1.0R."

**3 Changes**:

**1. Breakeven Stop After T1 Hit** (`weekly_eval.py::evaluate_setup()`)
- Once T1 is hit during evaluation, the simulated stop moves from original stop_loss to entry price (breakeven)
- If price reverses to entry after T1 → exit reason `be_stop` at 0R, not `stop_loss` at -1.0R
- Example: DOGEUSDT (May 17) had MFE of 1.6R and T1 was hit, but reversed to stop → was -1.0R loss, now would be 0R breakeven
- New field `be_stop_hit` in eval results

**2. Partial Profit Model** (`weekly_eval.py`)
- New `blended_rr` field per trade: `0.5 * T1_rr + 0.5 * actual_rr` when T1 is hit, otherwise `actual_rr`
- Models realistic position management: take 50% profit at T1, trail remainder with BE stop
- New lifetime stats tracking: `blended_rr_sum`, `blended_wins/losses`, `be_stops`, `t1_then_t2/be/expire`
- Recent performance table now includes "Blended" column alongside raw Actual R:R
- Summary includes "Partial Profit Model" section with blended WR and avg R:R
- Strategic rules auto-generate "PARTIAL PROFIT HELPS" rule when blended WR exceeds raw WR by 5%+

**3. R:R Floor Lowered from 2:1 to 1.5:1** (`analyzer/prompts.py`)
- Data justification: avg MFE is 1.15R. Simulated T1 at 1.0R hits 62%, T1 at 0.75R hits 76% — vs 33% for current ~2.0R targets
- Expected value: T1 at 1.0R → EV +0.24R/trade. T1 at 0.75R → EV +0.33R/trade. Current → EV -0.06R/trade
- All prompt references updated: target placement, hard rules, validation checklist, ranking criteria, risk framework
- Still prefers 2:1+ when structure supports it, but 1.5:1 at a real structural level is now valid
- Position management section rewritten to emphasize "50% at T1 + BE stop" as default strategy

**CLAUDE.md updated**: R:R floor guardrail, evaluation system docs, glossary (blended R:R, BE stop).

**Lifetime stats reset**: `processed_run_tags` cleared to rebuild all stats from existing eval files with new fields. Old eval files show `n/a` for blended_rr (they were scored with old logic). Partial profit data will accumulate from next eval run forward.

**Expected impact**: The combination of realistic targets (1.5:1 floor) + partial profit scoring should show a meaningful improvement in blended win rate once new eval data comes in. The direction accuracy (65%) suggests the system has real edge that was being masked by unreachable targets.

### 2026-05-14 (v3) — Accuracy Overhaul: Prescriptive Rules, MFE-Based T1, Per-Symbol Tracking

**Problem**: The learning loop was identifying problems (targets too far, confidence miscalibrated, swing losing) but not telling Claude **what to do about them**. Rules were descriptive ("targets are optimistic") not prescriptive ("set T1 at max 1.0R from entry"). Several critical patterns were not flagged at all (high confidence underperformance, losing timeframes, losing directions, rank anomalies, symbol patterns).

**7 Improvements to the Strategic Rules Generator** (`weekly_eval.py::generate_strategic_rules()`):

1. **High confidence calibration check**: Detects when 'high' confidence underperforms 'medium' (currently 22% vs 43% WR) and instructs Claude to recalibrate what deserves 'high' label.

2. **Timeframe performance rules**: Flags underperforming timeframes (e.g., swing at 11% WR → "avoid swing setups"). Previously only tracked in stats, never surfaced as a rule.

3. **Direction performance rules**: Flags losing directions (e.g., shorts at 0/3 WR → "avoid short setups until data improves"). Prevents Claude from recommending proven losing patterns.

4. **Rank anomaly detection**: Detects when Rank #2 outperforms Rank #1 (53% vs 37%) and instructs Claude to re-evaluate ranking criteria — prioritize structural clarity over headline appeal.

5. **Per-symbol tracking**: New `by_symbol` bucket in `lifetime_stats.json`. Surfaces consistently winning symbols (priority boost) and losing symbols (require extra confluence). Tracks win rate per coin.

6. **MFE-based optimal T1 calculation**: Uses average MFE (1.34R) to compute a specific maximum T1 distance (0.75 × avg MFE = 1.0R). Claude sees the exact number, not just "targets too far."

7. **Simulated closer-T1 backtest**: `evaluate_setup()` now backtests what would happen if T1 were at 0.75R and 1.0R. Results aggregated in `lifetime_stats.json::simulated_t1` and included in strategic rules: "T1 at 0.75R would hit X% of trades vs current Y%."

**All rules now prescriptive**: Every rule includes an "ACTION:" line telling Claude exactly what to do, not just what's wrong. Example: old rule said "TARGETS OPTIMISTIC: gap is 2.2R". New rule says "TARGETS TOO FAR: avg MFE is 1.3R, so set T1 at max 1.0R from entry. Backtest shows T1 at 0.75R would hit 65% vs current 28.6%. ACTION: Place T1 at nearest real structural level, use 1.5-2× ATR."

**Terminal shortcut**: Added `quarterly-scan` alias to `~/.zshrc` (alongside existing `scan` and `eval-scan`).

**New eval JSON fields**: `sim_t1_075r_hit`, `sim_t1_100r_hit` — boolean flags per evaluated trade.

**New lifetime_stats fields**: `by_symbol` (per-symbol win/loss/R:R), `simulated_t1` (aggregate sim results).

**Token impact**: Strategic rules grow from ~500 to ~600-800 tokens due to more prescriptive rules. Justified by dramatically better specificity.

### 2026-05-03 (v2) — Tiered Knowledge Distillation: Scalable Evaluation Feedback

**Problem**: The evaluation feedback system sent all historical data to Claude every run via `summary.md` + `_derive_performance_rules()`. At 28 trades this was ~2K tokens, but it would grow to ~6K+ after a year (52 runs × 5 setups). The `_derive_performance_rules()` function re-read ALL eval JSON files on every nightly run — O(n) in the number of runs.

**Solution**: Replaced the monolithic approach with a 3-layer tiered knowledge distillation system.

**Layer 1: Lifetime Stats** (`lifetime_stats.json`) — New incremental running counters:
- Tracks wins/losses/R:R by: setup type, confidence, rank, model, timeframe, direction, monthly trend
- Also tracks: prediction gap (sum of predicted vs actual R:R), MFE stats, stop timing, target hit rates
- Updated O(1) per new eval — adds to running totals, never re-reads old eval files
- Uses `processed_run_tags` to know which evals are already counted (supports bootstrap + incremental)

**Layer 2: Strategic Rules** (`strategic_rules.md`, ~500 tokens → sent to Claude):
- Compact, durable rules derived algorithmically from Layer 1
- 7-15 numbered rules like: "MEDIUM CONFIDENCE BANNED: 0/14 wins", "TARGETS TOO FAR: gap of 2.7R"
- Only changes when statistics shift meaningfully — not every week
- Replaces the old `_derive_performance_rules()` which read every eval file

**Layer 3: Recent Performance** (`recent_performance.md`, ~800 tokens → sent to Claude):
- Rolling 4-week window of trade-by-trade outcomes
- Old trades fall off automatically — fixed size regardless of history
- Includes manual trade notes/lessons from the rolling window
- Replaces the "last 20 trades" table that was in summary.md

**Quarterly Deep Analysis** (`quarterly_analysis.py`) — New script:
- Uses Claude to find non-obvious patterns in evaluation data every ~3 months
- Feeds `lifetime_stats.json` + last 20 trades to Claude for qualitative analysis
- Looks for: temporal patterns, setup interaction effects, symbol patterns, sequence effects, direction bias
- Appends findings to `strategic_rules.md` under "Quarterly Deep Insights" section
- Keeps logs in `logs/performance/quarterly/`

**Prompt Size Comparison** (performance section):
| Timeframe | Old approach | New approach |
|---|---|---|
| Now (28 trades) | ~2K tokens | ~1,300 tokens |
| 6 months (130 trades) | ~4K+ tokens | ~1,300 tokens |
| 1 year (260 trades) | ~6K+ tokens | **~1,300 tokens** |

**Simplification of `prompts.py`**:
- Deleted `_derive_performance_rules()` — 170 lines of code that re-read all eval files
- `build_system_prompt()` now just reads 2 small files: `strategic_rules.md` + `recent_performance.md`
- File went from 195 to 60 lines

**What's preserved**:
- `summary.md` still generated as human-readable report (unchanged format)
- `win_rate_history.json` still maintained
- All existing eval JSONs untouched
- Full backward compatibility — first `update_lifetime_stats()` call bootstraps from existing evals

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
- [ ] Add GitHub secrets (BYBIT_API_KEY, BYBIT_API_SECRET, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID) and push to enable pulse
- [ ] Monitor momentum pulse alerts for 1 week — verify thresholds catch real opportunities without spam
- [ ] Verify hot list integration: run `scan` and confirm "Hot list: N active coins" prints in output
- [ ] Run `quarterly-scan` — 101 trades is enough for deep pattern analysis
- [ ] Run 2-3 eval cycles to populate blended_rr data with new BE stop + partial profit model
- [ ] Compare blended WR vs raw WR after new data comes in — validate that partial profit model shows edge
- [ ] Monitor if 1.5:1 R:R floor lets Claude set more realistic T1 levels (T1 hit rate should increase from 33%)
- [ ] Review per-symbol stats — XRPUSDT (67% WR) and SOLUSDT (0/3) trends continue?
- [x] **Momentum pulse scanner** — intra-day momentum detection every 4h on GitHub Actions, zero Claude cost (v5)
- [x] **Dynamic watchlist (hot list)** — pulse-flagged coins auto-included in main scan (v5)
- [x] **Volume acceleration bonus** — hot list coins get +2/+4 pre-filter scoring bonus (v5)
- [x] **GitHub Actions deployment** — automated pulse with secrets, auto-commit back to repo (v5)
- [x] **Security hardening** — scrubbed session/pyc/.DS_Store from git history, enhanced .gitignore (v5)
- [x] **Breakeven stop model** — T1 hit → stop moves to entry, not full loss (v4)
- [x] **Partial profit model** — blended_rr: 50% at T1 + 50% trails with BE stop (v4)
- [x] **R:R floor lowered to 1.5:1** — based on 98-trade backtest showing avg MFE 1.15R (v4)
- [x] **Prescriptive strategic rules** — all rules now include ACTION lines (v3)
- [x] **MFE-based optimal T1** — uses avg MFE to compute specific T1 distance ceiling (v3)
- [x] **Simulated closer-T1 backtest** — backtests T1 at 0.75R and 1.0R per trade (v3)
- [x] **Per-symbol tracking** — by_symbol bucket in lifetime_stats (v3)
- [x] **High confidence calibration** — detects when high underperforms medium (v3)
- [x] **Timeframe/direction rules** — flags swing (11% WR) and shorts (0% WR) (v3)
- [x] **Rank anomaly detection** — flags when #2 beats #1 (v3)
- [x] **`quarterly-scan` terminal alias** — run quarterly_analysis.py with one command (v3)
- [x] Tiered knowledge distillation: lifetime_stats.json + strategic_rules.md + recent_performance.md
- [x] Quarterly deep analysis script (quarterly_analysis.py) for Claude-powered pattern detection
- [x] Decouple summary.md (human report) from Claude's prompt (now reads compact tiered files)
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
