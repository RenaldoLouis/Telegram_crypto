# Crypto Screener — Progress Tracker

_Last updated: 2026-06-02 (v9.1)_

---

## What This Project Does

A personal, automated crypto analyst that runs once a night and delivers the **best trading opportunities** (quality over quantity, typically 2-3 per run) on Bybit USDT perpetuals to your Telegram — with full trade plans (entry, stop, targets, R:R). It self-evaluates past recommendations against actual price data and feeds results back to Claude.

```
Momentum Pulse (every 4h, GitHub Actions, free)
    → Bybit API: fetch 50 tickers (single call)
    → Compare vs previous snapshot → detect volume/price acceleration
    → Flag coins: big move (>8% + >$200M), vol accel (>3x), funding squeeze
    → Market regime detection: risk_off / cautious / neutral / risk_on (from 50-ticker aggregate)
    → Save to logs/momentum/hot_list.json (48h expiry + regime)
    → Telegram alert: regime changes + new coin flags
    ↓
Bybit API (50 tickers, single call)
    ↓
Python pre-filter (knowledge-based scoring, free)
    → Load hot list (dynamic watchlist from pulse) + market regime
    → Disqualify: <$10M turnover or <$50M OI
    → Score by: price action, funding extremes, liquidity, OI+move combos
    → Volume acceleration bonus: hot list coins get +2 (>2x) or +4 (>5x)
    → Keep top 25 + watchlist (BTC, ETH, SOL) + hot list
    ↓
Fetch 4 timeframes per coin (15m, 1h, 4h, 1D)
    → RSI(14), EMA 20/50, volume spike ratio, breakout flags, ADX(14), range_pct per TF
    ↓
Claude (Sonnet 4.6 daily) analyzes as professional trader
    → BTC Daily Trend Guard: extracts BTC 1D trend/RSI/ADX, blocks correlated alt longs when bearish
    → ADX-based market type: ADX < 20 = ranging (use range setups), ADX > 25 = trending (trend_pullback OK)
    → Market regime awareness: risk_off/cautious → favor shorts, risk_on → favor longs
    → Drought alert: 15+/20 recent losses → SEVERE DROUGHT, max 1-2 setups
    → Losing streak circuit breaker: 5+ consecutive SLs → max 2 setups, strict quality gate
    → Dead cat bounce detection: daily RSI sub-35 bounce ≠ trend pullback
    → Professional trader mindset (don't chase, trap awareness, realistic targets)
    → Multi-TF confluence scoring (4/4=High, 3/4=Medium, 2/4=Low)
    → R:R target: 1.5:1 (floor AND ceiling — MFE data proves higher targets unreachable)
    → Volume hard gate: low volume environment → max 2 setups
    → Outputs 0-3 ranked setups (quality over quantity) + structured JSON
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
| `config.py` | 74 | Settings: API keys, model, limits, timeframes, watchlist, momentum + regime thresholds (4-tier) |
| `fetchers/bybit_data.py` | 362 | Bybit API: 50 tickers → scoring + hot list + regime → top 25 → multi-TF klines (incl. ADX + range_pct) |
| `fetchers/telegram_reader.py` | — | Telethon: reads signal groups (currently disabled) |
| `analyzer/prompts.py` | 351 | Professional trader prompt + knowledge + tiered performance feedback + regime/streak/volume/bounce/ADX/range rules |
| `analyzer/claude_client.py` | 179 | Anthropic API wrapper with prompt caching + compact JSON + losing streak + drought alert + BTC trend injection |
| `delivery/telegram_bot.py` | 160 | MD→HTML converter, smart section-based chunking, retry with backoff |
| `momentum_pulse.py` | 397 | Momentum detector + 4-tier market regime detection — runs every 4h on GitHub Actions (zero Claude tokens) |
| `weekly_eval.py` | 1630 | Evaluation engine + BE stop/partial profit model + tiered knowledge distillation |
| `quarterly_analysis.py` | 130 | Claude-powered deep pattern analysis (run every ~3 months) |
| `trade_logger.py` | 195 | CLI trade journal manager — open/close/list trades from recent setups |
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
    hot_list.json      → Active momentum-flagged coins + market regime (dynamic watchlist, 48h expiry)
    last_snapshot.json  → Previous pulse data + regime (for delta + regime transition detection)
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
| Indicators per TF | RSI(14), EMA 20, EMA 50, volume spike ratio, 20-candle breakout, **ADX(14)**, **range_pct** |
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

**Status: 45 runs evaluated (156 trades triggered, 167 total setups). Active since 2026-04-22.**

### Current Stats (as of 2026-06-01)
| Metric | Value |
|---|---|
| Overall win rate | **30.8%** (48W / 108L) ⚠️ declining |
| Avg actual R:R | -0.18 |
| Avg predicted R:R | 2.0 |
| **Prediction gap** | **2.2R** |
| T1 hit rate | 46/156 (29%) |
| Direction accuracy (MFE ≥ 0.5R) | **62%** (97/156) |
| Avg MFE | 1.04R |
| Simulated T1 at 0.75R | **54% hit rate** (41/76) |
| Simulated T1 at 1.0R | **42% hit rate** (32/76) |
| Blended WR (partial profit) | 31% (17W / 38L, with 7 BE stops) |
| Blended avg R:R | -0.37 |

### By Confidence Level
| Confidence | Win Rate | Trades | Note |
|---|---|---|---|
| High | 22% (2/9) | 9 | Worse than medium — calibration issue |
| Medium | **34% (38/111)** | 111 | Best performing |
| Low | 33% (7/21) | 21 | Acceptable |

### By Model
| Model | Win Rate | Avg R:R | Trades |
|---|---|---|---|
| claude-sonnet-4-6 | **35%** | -0.11 | 129 |
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
| 2026-05-19 | 101 | 37.6% | -0.06 |
| 2026-05-27 | 141 | 33.3% | -0.13 |
| 2026-05-29 | 148 | 31.8% | -0.17 |
| 2026-06-01 | 156 | **30.8%** | **-0.18** |

**Win rate peaked at 39.7% (May 22) then collapsed to 30.8% after extended losing streak May 21-Jun 1 (2W/39L = 5% win rate over last 39 trades). Monthly: April 16% → early May 40% → late May/Jun 31%. Root cause: trend-following in a ranging/choppy market with no ADX-based detection. v9 adds ADX, range detection, BTC daily trend guard, and range-specific setups.**

### May 22-25 Losing Streak Analysis (triggered v8 changes)

| Date | Trades | SL | BE Stop | Win | Win Rate |
|---|---|---|---|---|---|
| May 22 (2 scans) | 8 | 8 | 0 | 0 | 0% |
| May 23 | 2 | 2 | 0 | 0 | 0% |
| May 24 | 5 | 3 | 2 | 0 | 0% |
| May 25 | 5 | 3 | 1 | 1 | 20% |
| **Total** | **20** | **16** | **3** | **1** | **5%** |

**Root causes identified and fixed in v8:**
1. All 20 trades were longs in a declining market (58% declining, BTC -1.26%) — classified as "neutral" but should have been "cautious"
2. Bounces from oversold daily RSI (sub-35) labeled as "trend_pullback" instead of dead cat bounce
3. 5 setups per run despite "dangerously low volume" flagged in every brief
4. Targets at 1.6-2.0R when MFE data shows average of 1.08R — at least 4-5 trades would have won with T1 at 0.75R
5. No circuit breaker: 10+ consecutive SLs with no selectivity increase
6. Zero shorts despite >50% of coins declining — self-reinforcing anti-short loop

### Key Diagnosis
1. **Direction is right (64% reach 0.5R+ MFE)** but targets too far — execution problem, not analysis problem. v8 hard-caps predicted_rr at 1.5.
2. **High confidence is miscalibrated**: 22% WR vs medium at 34%. Flagged in strategic rules.
3. **Swing trades failing**: 25% WR (3/12), flagged to avoid. Short trades: 0% WR (0/3), but sample too small — v6 fixed the feedback loop, v8 forces shorts when >50% declining.
4. **Rank #2 outperforms #1**: 41% vs 25% WR. Ranking criteria flagged for review.
5. **T1 hit rate at 31%** but simulated backtest shows 59% at 0.75R, 46% at 1.0R — proving targets are the bottleneck. v8 hard-caps at 1.5R.
6. **Partial profit model active**: blended WR 38%, 6 BE stops instead of full losses. Data confirms the model helps but targets still need to come down.
7. **Low volume = low conviction**: when volume is absent, 5 setups means 5 losses. v8 caps at 2 setups in low-volume environments.
8. **Dead cat bounces kill longs**: post-sell-off recovery bounces (daily RSI sub-35 → 15m/1h flip bullish) are traps, not trend pullbacks. v8 adds explicit detection.

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

### 2026-06-02 (v9.1) — Trade Logger CLI + Trade Journal Updates

**Trade Logger Script** (`trade_logger.py`)
- New CLI tool for managing `logs/trades/my_trades.json` without manual JSON editing
- `trade open` — shows recent setups from scanner, pick one by number, enter actual entry/SL/TP. Auto-fills `claude_recommendation` from setup file.
- `trade close` — shows open trades, pick one, enter exit price + reason. Auto-calculates PnL%. Prompts for failure reason on losses.
- `trade list` — shows all trades with win rate and total PnL summary
- Terminal shortcut added: `trade` alias in `~/.zshrc`

**Trade Journal Updates**
- Closed ENJUSDT: SL hit at 0.05964, PnL -1.58% (failure: SL too tight)
- Closed HYPEUSDT: TP hit at 75.025, PnL +3.87% (first win — took profit below recommended T1 of 76.0)
- Current record: 1W / 2L (33% WR), total PnL: -4.80%

**Cost impact**: Zero. Trade logger is a local CLI tool with no API calls.

### 2026-06-01 (v9) — Choppy Market Fix: ADX Trend Detection + Range Setups + BTC Guard + Drought Alert

**Problem**: May 21-Jun 1 produced 2 wins in 39 trades (5% win rate), dragging cumulative WR from 40% to 31%. Deep data analysis revealed 3 root causes: (1) system called "trend_pullback" on ranging coins (e.g., XRP 4h ADX=16, clearly ranging — not trending), (2) kept longing BTC-correlated alts while BTC daily was declining, (3) `recent_losses` counter (15/20 losses) was computed but never injected — only consecutive stop losses triggered alerts.

**Data-driven diagnosis (39 trades, May 21-Jun 1):**
- **31% (12/39) directionally wrong** — MFE < 0.3R, price never moved in predicted direction. All were longs on BTC-correlated alts in a BTC downtrend.
- **33% (13/39) right direction, weak** — MFE 0.3-0.8R. Choppy market whipsawed these.
- **36% (14/39) right direction, wrong setup/target** — MFE > 0.8R but still lost. ALL 14 would have hit T1 at 0.75R. Winners during this period all had INDEPENDENT momentum (NEAR, XLM, INJ — decoupled from BTC).
- XRP recommended 7 times during clear downtrend, all 7 lost.
- 4/4 TF confluence had 0% win rate — all TFs reflected same BTC-driven decline.

**5 Fixes:**

**1. ADX (14) Trend Strength Indicator** (`fetchers/bybit_data.py`)
- New `adx_14` computed per timeframe using Wilder's smoothing method
- ADX < 20 = ranging/choppy (trend-following will fail), 20-25 = weak trend, > 25 = trending
- New `range_pct` — 20-candle high-low range as % of price. < 5% on 4h = tight consolidation, 5-10% = standard range.
- Validated on live data: XRP 4h ADX=16.47 (ranging), DOGE 4h ADX=25.47 (borderline trending), BTC 4h ADX=31.56 (trending)

**2. Choppy / Range Market Rules** (`analyzer/prompts.py`)
- New prompt section teaching Claude how to read ADX and range_pct
- When ADX < 20 on 4h: DO NOT use "trend_pullback" — use range-specific setups instead
- Only trade at range BOUNDARIES (near 20-candle high/low), not mid-range
- Valid range setups: range_mean_reversion, wyckoff_spring, liquidity_sweep, funding_squeeze, failed_breakout
- Quick 4-8h holds: fade at range extreme, target range midpoint
- Max 2 setups when most coins show ADX < 20
- New setup_type `range_mean_reversion` added to JSON enum

**3. BTC Daily Trend Guard** (`analyzer/claude_client.py`, `analyzer/prompts.py`)
- Extracts BTC 1D trend, RSI, and ADX from technicals and injects prominently into user content
- When BTC 1D trend is bearish with RSI < 40: explicit warning that correlated alt longs are HIGH RISK
- Correlated alt longs during BTC bearish daily: REQUIRE 4/4 TF + volume confirmed, otherwise DROP
- "Decoupled" alts (moving opposite to BTC) are still valid — these were the only winners during the streak
- Prompt updated: BTC Correlation Awareness section strengthened with Daily Trend Guard rules

**4. Recent Loss Rate Injection — Drought Alert** (`analyzer/claude_client.py`)
- Activated the previously-unused `recent_losses` counter from `_detect_losing_streak()`
- 15+/20 recent trades lost → SEVERE DROUGHT: max 1-2 setups, prefer range setups, consider 0 setups
- 12+/20 recent trades lost → HIGH LOSS RATE: max 2-3 setups, higher quality bar
- Current state: 15/20 = SEVERE DROUGHT will fire on next run
- This catches broad losing patterns that the consecutive-stop counter misses (one BE stop resets the streak counter, but 15/20 losses is still terrible)

**5. Validation Checklist Updated** (`analyzer/prompts.py`)
- New check #3: "ADX trend check — if 4h ADX < 20, this coin is RANGING. Do NOT label it trend_pullback."
- Failing ADX check → auto-DROP the setup (added to mandatory drop list alongside R:R and dead cat bounce)
- T1 check updated: "In ranging markets, T1 = range midpoint"

**Cost impact**: +1,600 tokens per run (~5.7% increase, from ~28k to ~29.6k). ~$0.10/month. Well below 2x threshold. Breakdown:
- System prompt (cached): +680 tokens (ADX/range rules, BTC guard, validation)
- Market data: +750 tokens (adx_14 + range_pct × 25 symbols × 4 TFs)
- User content: +170 tokens (BTC section + drought alert)

**Expected impact (backtested against May 21-Jun 1 data):**

| Protection Layer | Would Have Fired? | Effect |
|---|---|---|
| ADX < 20 block on trend_pullback | Yes (XRP ADX=16, most alts ranging) | ~20 trades blocked or relabeled to range setups |
| BTC Daily Trend Guard | Depends on EMA cross timing | Correlated alt longs flagged HIGH RISK |
| SEVERE DROUGHT (15/20) | Yes | Max 1-2 setups per run instead of 3-5 |
| Range-boundary-only rule | Yes | Mid-range entries blocked, only range extremes allowed |
| range_mean_reversion type | N/A (new) | Correct labeling for range plays, tracked separately in eval |

Combined: instead of 39 trades with 2 wins, the system would have produced ~8-12 high-quality range-boundary trades or skipped entirely. The 14 trades with MFE > 0.8R could be captured as partial wins with range-aware targets.

### 2026-05-27 (v8) — Losing Streak Root Cause Fix: Cautious Regime + Circuit Breaker + T1 Hard Cap

**Problem**: May 22-25 produced 16 stop losses in 20 trades (5% win rate). All 20 trades were longs in a declining market that was classified as "neutral." Root cause analysis revealed 6 systemic issues: (1) regime detection too lenient — 58% declining + BTC -1.26% should not be neutral, (2) dead cat bounces from oversold daily RSI mislabeled as "trend_pullback", (3) 5 setups per run in low-volume environments, (4) targets at 1.6-2.0R when MFE proves most trades don't reach 1.1R, (5) no circuit breaker for losing streaks, (6) zero shorts despite >50% of coins declining.

**6 Fixes**:

**1. Cautious Regime Tier** (`config.py`, `momentum_pulse.py`)
- New 4th regime tier between neutral and risk_off: `cautious` (soft bearish)
- Triggers: ≥55% declining AND median ≤ -0.5%, OR BTC ≤ -2%, OR ≥50% declining AND BTC ≤ -1.5%
- Claude limited to max 3 setups, longs require volume OR 4/4 TF, must consider shorts
- May 22-25 conditions (58% declining, -0.53% median) would now trigger `cautious` instead of `neutral`
- Config: `REGIME_CAUTIOUS_DECLINE_PCT=55`, `REGIME_CAUTIOUS_MEDIAN_CHANGE=-0.5`, `REGIME_CAUTIOUS_BTC_CHANGE=-2.0`, `REGIME_CAUTIOUS_COMBO_DECLINE=50`, `REGIME_CAUTIOUS_COMBO_BTC=-1.5`

**2. Losing Streak Circuit Breaker** (`analyzer/claude_client.py`)
- New `_detect_losing_streak()` reads recent eval files, counts consecutive stop losses from most recent backward
- 5+ consecutive SLs → LOSING STREAK ALERT injected into Claude's user content: max 2 setups, require volume OR 4/4 TF
- 3-4 consecutive SLs → CAUTION: max 3 setups, increase quality bar
- On May 25, the system would have detected 8 consecutive SLs and fired the alert

**3. Regime Always Injected** (`analyzer/claude_client.py`)
- Previously regime metrics only sent to Claude when non-neutral (to save tokens)
- Now always injected so Claude can see market breadth metrics even in neutral markets
- Enables Claude to make better judgment calls about setup count and direction (~100 extra tokens)

**4. Dead Cat Bounce Detection** (`analyzer/prompts.py`)
- New prompt section: "Dead Cat Bounce Detection (CRITICAL)"
- Teaches Claude the difference between a real trend pullback (daily uptrend → EMA pullback) and a dead cat bounce (daily oversold RSI sub-35 → brief 15m/1h recovery that gets sold into)
- When daily RSI was sub-35 within last 3 candles: any long must be LOW confidence, tighter targets, labeled "recovery_bounce" not "trend_pullback"

**5. T1 Hard Cap + Volume Gate + Short Requirement + Setup Count Limits** (`analyzer/prompts.py`)
- **T1 hard cap**: predicted_rr must be 1.5 (the floor IS the ceiling). No more 1.8, 2.0, 2.5 targets. MFE data (avg 1.08R over 141 trades) proves higher targets are unreachable for most trades.
- **Volume hard gate**: if all symbols show <0.5x volume spike, max 2 setups. Low volume → fewer setups, not 5 setups with caveats.
- **Short requirement**: when >50% coins declining, Claude MUST actively search for at least 1 short. Cannot use "historical short win rate is low" as excuse (sample is only 3 trades).
- **Default max 3 setups** (was effectively 5). Regime-specific: risk_off=2, cautious=3, neutral=3, risk_on=5.
- Updated pre-inclusion checklist with dead-cat-bounce check (#6) and volume gate (#7).

**6. Strategic Rules Updated** (`logs/performance/strategic_rules.md`)
- Rule 1: "STRICT SELECTIVITY" — 2-3 setups default, not 5
- Rule 6 (new): "DEAD CAT BOUNCE TRAP" — May 22-25 specific diagnosis
- Rule 8: "TARGETS TOO FAR — HARD CAP" — predicted_rr must be 1.5
- Rule 9 (new): "VOLUME IS A GATE, NOT A FLAG" — max 2 setups in low volume

**Cost impact**: ~+100 tokens per run (regime section now always sent, streak section ~50-80 tokens when active). Well below 2x threshold. No additional API calls — streak detection reads local eval files.

**Expected impact (backtested against May 22-25 data)**:

| Protection Layer | Would Have Fired? | Effect |
|---|---|---|
| Cautious regime | Yes (58% declining) | Max 3 setups, longs need volume/4TF, consider shorts |
| Losing streak | Yes by May 25 (8 SLs) | Max 2 setups, strict quality gate |
| Volume hard gate | Yes (most symbols <0.5x) | Max 2 setups |
| Dead cat bounce | Yes (daily RSI sub-35 bounces) | All longs flagged LOW confidence |
| T1 hard cap at 1.5R | Yes | ~4-5 trades saved (MFE reached 0.75-1.05R) |
| Short requirement | Yes (>50% declining) | At least 1 short per scan |

Combined effect: instead of 20 trades with 16 SLs, the system would have produced ~4-6 high-quality setups with several shorts mixed in. Even if the same % stopped out, the position count reduction alone would have cut losses by 60-70%.

### 2026-05-25 (v7) — ATH/ATL Exhaustion Setup + Fibonacci Framework + Short Unblock Fix

**Problem**: HYPEUSDT hit ATH at ~$63 with RSI overbought across all 4 timeframes (83/79/64/74). The system correctly detected it via momentum pulse (big_move flag, $711M turnover) and included it in the May 24 scan. Claude flagged it as "DO NOT CHASE" in Risk Flags — but only warned against longs. It did NOT recommend a short, despite textbook exhaustion signals at ATH. HYPE subsequently fell toward the golden pocket (~$35.30). Root cause: (1) `strategic_rules.md` had stale "Avoid short setups" rule from before the v6 safeguard was added — the eval was never re-run to regenerate it; (2) no setup in the playbook covered ATH exhaustion reversals; (3) no Fibonacci retracement framework existed for target placement.

**3 Fixes**:

**1. Strategic Rules Regenerated** (`strategic_rules.md` — user ran `eval-scan`)
- Rule 3 changed from "NO SHORT WINS: Avoid short setups" (hard block) to "SHORT NEEDS DATA: Do NOT avoid short based on this small sample" (permissive)
- New Rule 4: "DIRECTIONAL BLIND SPOT: Only 3 short trades vs 126 long trades. ACTION: When market regime is RISK_OFF, actively consider short setups to build data"
- The v6 safeguard code was correct (`DIRECTION_RULE_MIN_TRADES = 15`, 3 trades < 15 → "NEEDS DATA"), but the rules file was stale from before v6. Re-running eval-scan regenerated it properly.

**2. Setup 8: ATH/ATL Exhaustion Reversal** (`knowledge/06_setup_playbook.md`)
- Replaced the empty Setup 8 slot with a complete exhaustion reversal setup
- Criteria: price at ATH + RSI >75 on 2+ TFs + volume divergence + rejection candle + parabolic approach
- Entry: on rejection confirmation (shooting star, bearish engulfing), never before the turn
- Stop: above ATH wick extreme + 0.5-1% buffer
- T1: 0.618 Fibonacci golden pocket of the swing that produced the ATH
- T2: 0.786 Fibonacci or prior 4H/1D structure support
- Confidence boosters: crowded funding (>0.03%), 3/4+ TF overbought, BTC divergence
- Includes ATL mirror for long setups (inverse logic)
- Explicit safeguard: "This is NOT 'shorting because it went up a lot'" — requires multi-TF exhaustion confirmation
- Updated "Setups to AVOID" #2 to reference Setup 8 exception

**3. Fibonacci Retracement Framework** (`knowledge/03_market_structure.md`)
- Added "Fibonacci Retracement Levels" subsection under Support & Resistance
- Key levels documented: 0.382, 0.5, 0.618 (golden pocket), 0.786 with descriptions
- Golden pocket zone (0.618–0.65) highlighted as highest-probability reversal area
- Usage: target for mean reversion setups (Setup 8 T1), entry zone for trend pullbacks
- How to draw, crypto-specific reliability (self-fulfilling), confluence rules
- Cross-references Setup 8 for target usage

**Cost impact**: Zero. Changes are in knowledge files that are already loaded every run (~16.7k tokens cached). Setup 8 adds ~400 tokens to the knowledge section, well within the existing cached block.

**Expected impact**: On the HYPE scenario specifically — Claude would now: (1) not be blocked from shorts by strategic rules, (2) match HYPE's multi-TF overbought RSI + ATH against Setup 8 criteria, (3) recommend a short with T1 at the 0.618 golden pocket (~$35.30), (4) set stop above the ATH wick with tight risk. More broadly, any coin hitting ATH/ATL with exhaustion signals will now be a candidate for mean reversion setups.

### 2026-05-24 (v6) — Market Regime Detection + Short Enablement

**Problem**: May 21-22 produced 13 consecutive long-only trades that ALL hit stop loss (-1.0R each). The market reversed into a broad sell-off after a strong May 20, but the system had no concept of overall market direction — it analyzed each coin in isolation and kept recommending longs into a falling market. Additionally, a self-reinforcing feedback loop permanently blocked shorts: only 3 shorts were ever recommended (0% WR on tiny sample), so `strategic_rules.md` said "Avoid short setups", preventing Claude from ever trying shorts, preventing shorts from accumulating data.

**3 Features**:

**1. Market Regime Detection** (`momentum_pulse.py`, `config.py`)
- New `detect_market_regime()` function aggregates the same 50 tickers already fetched (zero extra API calls)
- Classifies market as `risk_off` (bearish), `neutral`, or `risk_on` (bullish) using 5 aggregate metrics:
  - % of coins declining (breadth), median 24h change, BTC 24h change, avg funding rate, large decline count
- Classification thresholds (tunable in config, updated v8 to 4-tier):
  - `risk_off`: ≥70% declining AND median ≤ -2%, OR BTC ≤ -4%, OR ≥60% declining AND BTC ≤ -3%
  - `cautious` (v8): ≥55% declining AND median ≤ -0.5%, OR BTC ≤ -2%, OR ≥50% declining AND BTC ≤ -1.5%
  - `risk_on`: ≤30% declining AND median ≥ +2%, OR BTC ≥ +4%, OR ≤40% declining AND BTC ≥ +3%
- Regime saved in both `hot_list.json` (for main scan) and `last_snapshot.json` (for transition detection)
- Telegram alert sent on regime transitions (e.g., "MARKET REGIME: NEUTRAL → RISK OFF")
- Coin-level alerts now show current regime context when non-neutral

**2. Regime-Aware Analysis** (`analyzer/prompts.py`, `analyzer/claude_client.py`, `fetchers/bybit_data.py`)
- `_load_hot_list()` now returns `(coins, market_regime)` tuple
- `get_full_market_snapshot()` passes `market_regime` through to Claude
- `claude_client.py` injects a "Market Regime" section into user content when non-neutral (~100 tokens)
- System prompt gains "Market Regime Awareness" instructions (~200 tokens, cached):
  - **RISK_OFF**: Be skeptical of longs (require 4/4 TF confluence), actively look for shorts, max 2 setups
  - **RISK_ON**: Favor trend-following longs, shorts only with clear distribution
  - **NEUTRAL** (no section): Standard analysis without directional bias

**3. Short Avoidance Feedback Loop Fix** (`weekly_eval.py`, `config.py`)
- Direction "avoid" rules now require `DIRECTION_RULE_MIN_TRADES = 15` trades (was 3)
- With <15 trades and 0% WR: rule says "NEEDS DATA — do NOT avoid based on small sample" instead of "Avoid"
- New "DIRECTIONAL BLIND SPOT" rule: when shorts <10 and longs >30, explicitly tells Claude to consider shorts during RISK_OFF to build data
- This breaks the permanent lock-out cycle: 3 losing shorts → "avoid shorts" → never try shorts → shorts stay at 0%

**Config additions** (`config.py`):
- `REGIME_BEARISH_DECLINE_PCT = 70`, `REGIME_BEARISH_MEDIAN_CHANGE = -2.0`, `REGIME_BEARISH_BTC_CHANGE = -4.0`
- `REGIME_BEARISH_COMBO_DECLINE = 60`, `REGIME_BEARISH_COMBO_BTC = -3.0`
- `REGIME_BULLISH_DECLINE_PCT = 30`, `REGIME_BULLISH_MEDIAN_CHANGE = 2.0`, `REGIME_BULLISH_BTC_CHANGE = 4.0`
- `REGIME_BULLISH_COMBO_DECLINE = 40`, `REGIME_BULLISH_COMBO_BTC = 3.0`
- `DIRECTION_RULE_MIN_TRADES = 15`

**Cost impact**: ~+30-200 tokens per run (regime prompt is cached; data section only injected when non-neutral). Well below the 2x threshold. Regime detection itself is zero cost (uses same Bybit data already fetched). GitHub Actions workflow unchanged.

**Expected impact**: During the May 21-22 sell-off, the regime detector would have classified the market as `risk_off` (BTC dropped >4%, >70% of coins declining). Claude would have been instructed to limit to 2 setups, be skeptical of longs, and actively look for shorts — instead of producing 13 long-only setups that all hit stop loss.

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
- [x] **Trade logger CLI** — `trade_logger.py` for managing my_trades.json (open/close/list), `trade` alias (v9.1)
- [ ] Run `scan` and verify ADX values appear in setup JSONs — check that ranging coins (ADX < 20) are NOT labeled "trend_pullback"
- [ ] Verify SEVERE DROUGHT alert fires (15/20 losses) and Claude outputs max 1-2 setups
- [ ] Verify BTC Daily Trend section appears in user content with RSI + ADX
- [ ] Check if `range_mean_reversion` setup type appears when coins are ranging at boundaries
- [ ] Run `quarterly-scan` — 156 trades is plenty for deep pattern analysis
- [ ] Monitor range_mean_reversion win rate once enough data accumulates
- [ ] Review per-symbol stats — BTCUSDT (1/8, 12% WR) and ETHUSDT (2/9, 22% WR) consistently underperform
- [ ] Track whether ADX-based filtering reduces the number of directionally-wrong trades (MFE < 0.3R)
- [ ] Run `eval-scan` after a few v9 runs to see if range setups perform differently from trend setups
- [x] **ADX trend strength indicator** — ADX(14) + range_pct per timeframe, distinguishes ranging from trending (v9)
- [x] **Choppy/range market rules** — new prompt section: ADX interpretation, range-boundary-only trading, max 2 setups when ranging (v9)
- [x] **BTC Daily Trend Guard** — extracts BTC 1D trend/RSI/ADX, warns when correlated alt longs are HIGH RISK (v9)
- [x] **Recent loss rate injection (drought alert)** — activates dead `recent_losses` code, 15+/20 → SEVERE DROUGHT max 1-2 setups (v9)
- [x] **range_mean_reversion setup type** — new type for fading range extremes, quick 4-8h holds (v9)
- [x] **ADX validation check** — mandatory pre-inclusion check: ADX < 20 → cannot be "trend_pullback", auto-DROP (v9)
- [x] **Cautious regime tier** — 4th tier between neutral and risk_off, catches soft bearish markets (v8)
- [x] **Losing streak circuit breaker** — reads eval files, 5+ SLs → max 2 setups + strict quality gate (v8)
- [x] **Regime always injected** — Claude always sees market breadth metrics, not just when non-neutral (v8)
- [x] **Dead cat bounce detection** — distinguishes real trend pullbacks from recovery bounces in downtrends (v8)
- [x] **T1 hard cap** — predicted_rr must be 1.5 (floor = ceiling), based on MFE avg of 1.08R (v8)
- [x] **Volume hard gate** — low volume environment → max 2 setups, not 5 with caveats (v8)
- [x] **Short requirement** — must search for shorts when >50% coins declining (v8)
- [x] **Default max 3 setups** — regime-specific: risk_off=2, cautious=3, neutral=3, risk_on=5 (v8)
- [x] **ATH/ATL Exhaustion Reversal setup** — Setup 8 in playbook: multi-TF overbought at ATH → short with golden pocket target (v7)
- [x] **Fibonacci retracement framework** — golden pocket (0.618) + key levels added to market structure knowledge (v7)
- [x] **Strategic rules short unblock** — re-ran eval-scan, "Avoid shorts" → "NEEDS DATA" + "DIRECTIONAL BLIND SPOT" (v7)
- [x] **Market regime detection** — risk_off/neutral/risk_on from 50-ticker aggregate, zero extra API calls (v6)
- [x] **Regime-aware analysis** — Claude instructed per regime: shorts during risk_off, longs during risk_on (v6)
- [x] **Short avoidance feedback loop fix** — direction rules require 15+ trades, NEEDS DATA for small samples (v6)
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
forcement — NOT Claude)
4. Model comparison data (Sonnet vs Haiku accuracy)
5. Explicit user approval
