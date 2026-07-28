# Crypto Screener — Progress Tracker

_Last updated: 2026-07-21 (v12.0)_

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
    → RSI(14), EMA 20/50, MACD(12,26,9), volume spike ratio, breakout flags, ADX(14), range_pct per TF
    → SMA(200) on 1D only (long-term trend filter, requires 210 daily candles)
    → **Validated signal check on 1h + 4h** (4 cross-TF confirmed formulas, zero extra API calls)
    ↓
Claude (Sonnet 4.6 daily, extended thinking enabled) analyzes as professional trader
    → **BACKTESTED SIGNALS section**: prioritizes empirically-validated setups when they fire
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
    → Extended thinking: reasoning in separate thinking block (not in output)
    → Outputs 0-3 ranked setups (quality over quantity) + structured JSON with reasoning
    ↓
main.py parses JSON → validates against rules (Python, free) → saves to logs/setups/ (incl. regime + reasoning)
    ↓
Brief archived to logs/briefs/ (clean: JSON stripped + pre-analysis stripped)
    ↓
Telegram delivery (HTML formatted, retry on failure, plain text fallback)
    ↓
Weekly eval (weekly_eval.py, run Sundays or whenever)
    → Evaluates NEW setups from last 7 weeks only (not all-time)
    → Loads ALL past evaluations for cumulative learning
    → Fetches actual prices from Bybit for each past setup
    → Scores: triggered? stop or target hit first? actual R:R? MFE?
    → Breakeven stop model: after T1 hit, stop moves to entry (0R worst case, not -1R)
    → Partial profit model: blended_rr = 50% at T1 + 50% trails with BE stop
    → Tiered Knowledge Distillation:
      Layer 1: lifetime_stats.json — incremental counters incl. by_regime, by_rule_applied (O(1) update)
      Layer 2: strategic_rules.md — algorithmic rules + delta insights (~600-800 tokens, sent to Claude)
      Layer 3: recent_performance.md — rolling 4-week trade details (~800 tokens, sent to Claude)
      Human:  summary.md — full report with all tables (NOT sent to Claude)
    → Claude reads strategic_rules + recent_performance + validation checklist → feedback loop
    → Total performance tokens: ~1,500-1,800 (FIXED regardless of history length)
    ↓
Delta analysis (auto-triggered every 15 new evaluated trades)
    → Grades previous insights: EFFECTIVE → confirmed, INEFFECTIVE → expired
    → Finds 2-5 new patterns, outputs ACTION rules
    → Updates rule_registry.json + appends to strategic_rules.md
    → Cost: ~13.5k tokens per analysis (~every 2 weeks)
    ↓
Quarterly deep analysis (quarterly_analysis.py, manual — still available for deep-dives)
    → Feeds lifetime_stats.json + recent trades to Claude
    → Finds non-obvious patterns: temporal, symbol-specific, interaction effects
```

---

## Current Status & Roadmap (READ FIRST when resuming)

_As of 2026-07-21 (v12.0). Single source of truth for where the mechanical-primary migration stands and what to do next. Full plan: `~/.claude/plans/ok-becauase-in-my-refactored-locket.md`._

**Big picture.** Migrating from *Claude-as-decision-maker* to a pure-Python **mechanical engine as the primary setup source**, with Claude running in **shadow** (built + logged + evaluated head-to-head, not necessarily delivered). Goal: prove mechanical beats Claude on **expectancy**, then Claude can be dropped → independence from a model Anthropic can change/deprecate anytime. Optimize expectancy, NOT win rate.

**CURRENT MODE = SHADOW.** `config.PRIMARY_SOURCE = "claude"`. `scan` still delivers *Claude's* brief to Telegram; mechanical setups are built + saved silently alongside for comparison. Delivery behavior is unchanged until Phase 4. A Claude failure (quota/$cap/timeout) now degrades to mechanical-only delivery instead of crashing.

**Done (committed 2026-07-21 `3fada87`, Phases 0-3):**
- Phase 0: prompt cleanup; `enforce_setups()` now DROPS rule-breakers (was log-only) + re-ranks.
- Phase 1: `signal_levels.py`, `mechanical_setups.py`, structural levels surfaced in `bybit_data`, `run_screener` rebuilt (mechanical-first + Claude in try/except), `format_mechanical_brief`, `PRIMARY_SOURCE` flag.
- Phase 2: `weekly_eval` tags `source`/`backtested_signal`, `by_source`/`by_signal_backed` buckets, `generate_head_to_head()` → `logs/performance/head_to_head.md`.
- Phase 3: new backtester signals (`failed_breakout`, `liquidity_sweep`, `*_stacked`), generic slow factory path (`_eval_combo`) + walk-forward (`--walkforward`). Promoted `failed_breakout_short` LIVE (4h-only).

**Live validated signals (4):** `rsi_rejection_short` (both TF), `macd_momentum_long` (both TF), `trend_pullback_short` (4h-only), `failed_breakout_short` (4h-only, NEW). Mechanical is LOW-FREQUENCY (0-1 setups/scan) until more signals validate — this is the main thing Phase 3 keeps chipping at.

**Roadmap / what's next:**
1. **Ongoing:** the **mechanical scan now runs every 4h on GitHub Actions** (mechanical-only, no ANTHROPIC key on CI) alongside the pulse — see CLAUDE.md § "Scheduled Runs". The 9pm local `launchd` run is the only Claude call. Run `eval-scan` (which now `git pull --rebase`s the CI-pushed setups first) weekly. Watch `logs/performance/head_to_head.md`.
2. **Phase 4 — flip to mechanical-primary.** ONLY after head_to_head shows **mechanical expectancy ≥ Claude expectancy AND ≥20 evaluated trades EACH source**. Then set `PRIMARY_SOURCE="mechanical"` + write a `version_markers.json` cutover marker. One line, reversible. Do NOT flip early. **CAVEAT (4h cadence):** mechanical now accumulates ~6×/day vs Claude's 1×/day (nightly only), so the head-to-head is **asymmetric** — mechanical will hit "≥20" long before Claude. Judge the flip on **expectancy per source**, and treat "≥20 each" as a floor, not a trigger. Cross-run dedup (`main.py::_active_setup_keys`) already strips same-coin/overlapping-window pseudo-replicates so the counts aren't inflated by correlated repeats.
3. **Phase 5 — owned ML meta-filter.** Train a scikit-learn take/skip model on `logs/evaluations/*` to replace Claude's discretion (fully owned, deterministic). Only after enough eval data accumulates (avoid overfitting).
4. **Ongoing signal expansion:** monthly `backtest`; promote signals passing out-of-sample validation on REAL data into `_check_validated_signals` + `mechanical_setups.EXPECTANCY/SETUP_TYPE/SETUP_RULE`. **HELD candidates:** `failed_breakout_short_stacked` (4h strong but 1h overfit), `liquidity_sweep_*` (overfit) — re-check with more data.

**Gotchas for future sessions (avoid re-learning the hard way):**
- Use `venv/bin/python` or the `scan`/`eval-scan`/`backtest` aliases — bare `python` is **Python 2** on this Mac (the aliases already use the venv).
- `failed_breakout_short` uses a STRUCTURAL stop → its signal dict carries an explicit `stop_price`, which `mechanical_setups._build_one` honors. Any future structural-stop signal must do the same (a flat `stop_atr` won't represent it).
- **Walk-forward is uninformative at 4h** — windows too sparse, everything (incl. proven live signals) shows 0/N. Use `--validate` (single split) at 4h; walk-forward needs 1h or `--wf-windows 2`.
- A new backtester signal needs a `PARAM_GRIDS` entry **with a `factory`** to be optimize/validate-able (generic slow path). A `FAST_SWEEP_MAP` entry is optional (speed only).
- A signal goes LIVE only after passing out-of-sample validation on REAL Bybit data. Never hardcode unvalidated signals into `_check_validated_signals`.
- The `backtest`/`--validate` gate tests signal FORMULAS; the head_to_head + version-segment (forward, via `eval-scan`) tests SELECTION. They answer different questions.

---

## Current Architecture

| File | Lines | Purpose |
|---|---|---|
| `main.py` | ~360 | Orchestrator — fetch → **build mechanical setups (primary)** → **Claude in try/except (shadow)** → `enforce_setups` (drops violators) → save BOTH sources tagged `source` → deliver per `config.PRIMARY_SOURCE` (mechanical fallback if Claude fails) |
| `mechanical_setups.py` | ~150 | **Mechanical setup constructor** — turns fired validated signals into full setups (entry/stop/T1/T2 + deterministic rank/confidence), zero LLM |
| `signal_levels.py` | ~90 | Shared pure entry/stop/target math (drift-guarded vs backtester by `test_signal_levels.py`) |
| `config.py` | 79 | Settings: API keys, model, limits, timeframes, watchlist, momentum + regime thresholds, delta analysis |
| `fetchers/bybit_data.py` | ~475 | Bybit API: 50 tickers → scoring + hot list + regime → top 25 → multi-TF klines (incl. ADX, range_pct, MACD, SMA200) + validated signal detection (4 cross-TF confirmed formulas) |
| `fetchers/telegram_reader.py` | — | Telethon: reads signal groups (currently disabled) |
| `analyzer/prompts.py` | 380 | Professional trader prompt + knowledge + tiered performance feedback + regime/streak/volume/bounce/ADX/range rules + reasoning capture |
| `analyzer/claude_client.py` | ~280 | Anthropic API wrapper with prompt caching + **extended thinking** + compact JSON + regime enforcement + effective limit computation + losing streak + drought alert + BTC trend injection + **validated signal injection** |
| `delivery/telegram_bot.py` | 160 | MD→HTML converter, smart section-based chunking, retry with backoff |
| `momentum_pulse.py` | 397 | Momentum detector + 4-tier market regime detection — runs every 4h on GitHub Actions (zero Claude tokens) |
| `weekly_eval.py` | 2087 | Evaluation engine + BE stop/partial profit model + tiered knowledge distillation + delta analysis self-learning |
| `quarterly_analysis.py` | 130 | Claude-powered deep pattern analysis (run every ~3 months) |
| `trade_logger.py` | 195 | CLI trade journal manager — open/close/list trades from recent setups |
| `backtester.py` | ~350 | **What-if backtester**: loads eval/setup logs, sweeps parameters (T1 distance, filters, regime limits, symbols, combos), reports expectancy/WR/PF. Zero Claude tokens. |
| `historical_backtester.py` | ~2100 | **Historical strategy backtester**: fetches Bybit klines, 18 mechanical signal rules, parameter sweep optimizer, train/test validation + robustness scoring, **walk-forward validation** (`--walkforward`), generic slow factory path for signals without a vectorized sweep. Caches data locally. Zero Claude tokens. |
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
    lifetime_stats.json    → Layer 1: Incremental running counters incl. by_regime, by_rule_applied (backing data, not sent to Claude)
    strategic_rules.md     → Layer 2: Compact algorithmic rules + delta insights (~600-800 tokens, sent to Claude)
    recent_performance.md  → Layer 3: Rolling 4-week trade details (~800 tokens, sent to Claude)
    summary.md             → Human-readable full report (NOT sent to Claude)
    win_rate_history.json  → Persistent win rate snapshots across eval runs
    rule_registry.json     → Delta analysis registry: insight tracking, effectiveness grading, win rate snapshots
    quarterly/             → Deep analysis + delta analysis logs
  backtest_cache/          → Cached Bybit klines for historical backtesting (JSON, no expiry)
```

---

## Current Settings

| Setting | Value |
|---|---|
| Model | `claude-sonnet-4-6` (current) — model name tracked per setup for comparison |
| Max output tokens | 8000 (text) + 10000 (thinking) |
| Extended thinking | Enabled — reasoning in separate block, not sent to Telegram |
| Broad scan pool | 50 tickers (by turnover) |
| Pre-filter to | 25 coins (by knowledge-based interest score + watchlist + hot list) |
| Timeframes | 15m (100 candles), 1h (100), 4h (100), 1D (210) |
| Indicators per TF | RSI(14), EMA 20/50, MACD(12,26,9), volume spike ratio, 20-candle breakout, ADX(14), range_pct |
| 1D-only indicators | SMA(200) — long-term trend filter |
| Watchlist (always included) | BTCUSDT, ETHUSDT, SOLUSDT + momentum pulse hot list |
| Momentum pulse | Every 4h on GitHub Actions (zero Claude tokens) |
| Schedule | Nightly screener (launchd, 9pm local) + momentum pulse (GitHub Actions, every 4h) |
| Delivery | Telegram bot (HTML formatted) |

---

## Cost Estimation (Monthly)

### Per Run (once/night)
| Component | Tokens | Cost (Sonnet 4.6) | Cost (Haiku 4.5) |
|---|---|---|---|
| System prompt + knowledge | ~17,000 input | $0.051 | $0.014 |
| Market data (25 coins × 4 TFs + MACD + SMA200) | ~3,800 input | $0.011 | $0.003 |
| Extended thinking (reasoning) | ~8,000-10,000 | $0.120-0.150 | $0.032-0.040 |
| Output (brief + JSON, no pre-analysis) | ~4,000-6,000 output | $0.060-0.090 | $0.016-0.024 |
| **Total per run** | **~33,000-37,000** | **~$0.24-0.30** | **~$0.07-0.08** |

### Monthly (30 runs)
| Model | Est. Cost |
|---|---|
| **Sonnet 4.6 (current)** | **$7.20-9.00/month** |
| Haiku 4.5 | $2.10-2.40/month |

_Note: Extended thinking increases per-run cost ~60% but dramatically improves output quality — Claude now thinks thoroughly in a separate block and only outputs the clean formatted brief. Previous runs often exhausted all output tokens on pre-analysis notes before producing the actual brief._

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

> **⚠️ HISTORICAL SNAPSHOT (2026-06-05, pre-v8/v9 fixes). NOT current — do not read these as today's numbers.** Kept because the stats + diagnoses below explain *why* the v7–v11 changes were made. For LIVE performance read `logs/performance/lifetime_stats.json` (backing data) and `logs/performance/summary.md` (human report); for mechanical-vs-Claude read `logs/performance/head_to_head.md`.

### Historical Stats (snapshot 2026-06-05)
| Metric | Value |
|---|---|
| Overall win rate | **29.8%** (48W / 113L) ⚠️ declining |
| Avg actual R:R | -0.20 |
| Avg predicted R:R | 2.0 |
| **Prediction gap** | **2.2R** |
| T1 hit rate | 47/161 (29%) |
| Direction accuracy (MFE ≥ 0.5R) | **61%** (99/161) |
| Avg MFE | 1.03R |
| Simulated T1 at 0.75R | **53% hit rate** |
| Simulated T1 at 1.0R | **41% hit rate** |
| Blended WR (partial profit) | 30% (18W / 42L, with 8 BE stops) |
| Blended avg R:R | -0.40 |

### By Confidence Level
| Confidence | Win Rate | Trades | Note |
|---|---|---|---|
| High | 22% (2/9) | 9 | Worse than medium — calibration issue |
| Medium | **34% (38/111)** | 111 | Best performing |
| Low | 33% (7/21) | 21 | Acceptable |

### By Model
| Model | Win Rate | Avg R:R | Trades |
|---|---|---|---|
| claude-sonnet-4-6 | **31%** | -0.19 | 149 |
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
| 2026-06-01 | 156 | 30.8% | -0.18 |
| 2026-06-05 | 161 | **29.8%** | **-0.20** |

**Win rate peaked at 43.1% (May 10) then collapsed to 29.8%. The May 21-Jun 5 losing streak (3W/52L = 6% WR) dragged cumulative from 43% to 30%. Root causes: (1) all-long setups in risk_off market, (2) regime limits only in system prompt not user content — Claude ignored them, (3) swing timeframe added unnecessary overnight risk, (4) JSON example showed predicted_rr 2.5 contradicting the 1.5 rule. v9.2 adds explicit regime enforcement in user content, effective limit computation, drops swing timeframe, and fixes the contradictory example.**

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
- **Per-regime performance** — win rate per market regime (risk_off/cautious/neutral/risk_on)
- **Per-rule-applied effectiveness** — win rate for each reasoning rule Claude cites
- **Delta analysis insight grading** — tracks which insights helped (confirmed) vs hurt (expired)
- **Post-scan validation** — logs violations of hard rules (regime limits, predicted_rr cap, etc.)
- Prescriptive rules auto-derived from `lifetime_stats.json` with specific ACTIONs

### How evaluation data reaches Claude (Tiered Knowledge Distillation)

| Layer | File | Tokens | Scales? | Purpose |
|---|---|---|---|---|
| 1. Lifetime Stats | `lifetime_stats.json` | N/A (backing data) | Grows slowly | Incremental counters incl. by_regime, by_rule_applied — O(1) update per eval |
| 2. Strategic Rules | `strategic_rules.md` | ~600-800 | **Fixed** | Algorithmic rules + delta insights from all history |
| 3. Recent Window | `recent_performance.md` | ~800 | **Fixed** (rolling) | Last 4 weeks of trade-by-trade outcomes |
| Human Report | `summary.md` | ~2K+ | Grows | Full tables for human review (NOT sent to Claude) |
| Delta Insights | Appended to `strategic_rules.md` | ~200-400 | **Fixed** | Auto-triggered every 15 new trades, grades previous insights |
| Rule Registry | `rule_registry.json` | N/A (tracking) | Grows slowly | Insight lifecycle: experimental → confirmed → expired |

**Total performance context in Claude's prompt: ~1,500-1,800 tokens** — regardless of running for 1 month or 3 years. Previous approach would grow to ~6K+ tokens after a year.

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

### 2026-07-22 — Keyless Bybit (removed API key entirely)

**Why:** The Bybit API key expired (ErrCode 33004). Investigation showed the whole system only ever calls **public** Bybit endpoints (`get_tickers`, `get_kline`) — verified live: identical 755 tickers returned WITH the expired key and with NO key. The key authenticated only *private account* endpoints (balance/positions/orders), which this Phase-A analyst system deliberately never touches. Without an IP whitelist Bybit keys auto-expire every 90 days, and a dynamic VPN IP can't be usefully whitelisted (whitelist = fixed IP list) — so going keyless kills the whole recurring problem. `momentum_pulse.py` was already keyless; this makes the rest consistent.

**Changes:**
- Keyless `HTTP(testnet=False)` in `fetchers/bybit_data.py`, `weekly_eval.py::get_bybit_client()`, `historical_backtester.py`.
- Removed `BYBIT_API_KEY`/`BYBIT_API_SECRET` from `config.py` (comment left explaining why — do NOT re-add unless a private/order endpoint is ever added in Phase B), `.env`, and the `.github/workflows/momentum_pulse.yml` env block.
- Docs updated: `CLAUDE.md` (Environment Setup) + `progress.md` (GitHub Actions secrets line).

**Unchanged / notes:**
- **Data accuracy unaffected** — public market data is identical regardless of key.
- **VPN still required** for local runs — Indonesian ISPs block Bybit's servers (network reachability, not auth).
- User-side (optional): delete `BYBIT_API_KEY`/`BYBIT_API_SECRET` from GitHub repo secrets; revoke the old expired key on Bybit.

**Verification:** `config` no longer exposes the key vars; keyless `get_top_movers(5)` + `get_kline` → `retMsg: OK`; grep confirms zero remaining `BYBIT_API_*` references in code/docs.

### 2026-07-21 (v12.0) — Mechanical-Primary / Claude-Shadow Architecture (Phases 0-3)

**Why:** Claude was inventing every price (entry/stop/T1/T2) + ranking/direction — the system's core edge depended on a black box Anthropic can change or deprecate anytime, and a Claude API failure crashed the entire scan. Goal: make a pure-Python mechanical engine the primary source, run Claude in shadow, and prove (with our own eval data) whether mechanical beats Claude on expectancy → path to full independence. See "Current Status & Roadmap" at top for live state and next steps.

**Phase 0 — enforce + prompt cleanup:**
- `analyzer/prompts.py`: removed stale "predicted_rr = 1.5" lines that contradicted the 0.75-1.0R T1 rule.
- `main.py`: split `validate_setups` → `setup_violations()` (per-setup blocking checks) + `enforce_setups()` which now **DROPS** rule-breakers (T1>1.0R, T2<1.5R, long-volume, blacklist, confluence<3, bad enums) and re-ranks — previously violations were only logged.

**Phase 1 — mechanical engine + graceful degradation (shadow: delivery unchanged):**
- `signal_levels.py` (new): shared entry/stop/target math, drift-guarded by `test_signal_levels.py` (6 tests).
- `mechanical_setups.py` (new): `build_mechanical_setups()` turns fired validated signals into full setups (entry/stop/T1/T2 + deterministic rank/confidence/confluence), zero LLM.
- `fetchers/bybit_data.py`: surface `high_20`/`low_20`/`swing_high`/`swing_low` for structural T1.
- `main.py`: `run_screener` rebuilt — mechanical built FIRST, Claude wrapped in try/except → any Claude failure (quota/$cap/timeout/API) degrades to mechanical-only delivery, never crashes. Both sources saved to one setup file tagged `source`.
- `delivery/telegram_bot.py`: `format_mechanical_brief()`. `config.py`: `PRIMARY_SOURCE` (default `"claude"` = shadow) + `MECHANICAL_MODEL_TAG`.

**Phase 2 — head-to-head measurement:**
- `weekly_eval.py`: per-result `source` + `backtested_signal` tags, `by_source`/`by_signal_backed` lifetime buckets, `generate_head_to_head()` → `logs/performance/head_to_head.md` (WR/expectancy/PF, mechanical vs Claude; "INSUFFICIENT DATA" until ≥20/source). Fixed partial-eval dedup to key on `(symbol, source)`.

**Phase 3 — expand + harden signal library:**
- `historical_backtester.py`: new candle-only signals `failed_breakout_long/short`, `liquidity_sweep_long/short` + confluence-`*_stacked` variants (min_confirms sweep); generic slow factory path (`_eval_combo`) so signals without a hand-vectorized sweep are still optimize/validate-able; walk-forward validation (`run_walkforward`, `--walkforward`/`--wf-windows`, `_slice_arrays`). (No funding_squeeze/post_liquidation — backtester has no funding/OI columns.)
- Real 4h+1h validation across 15 symbols → **promoted `failed_breakout_short` LIVE (4h-only)** into `_check_validated_signals` (test +0.120R, N=75, 100% robust; buffer_atr=0.25/rsi_gate=45/2.0R). Uses a structural stop → carries explicit `stop_price` honored by `mechanical_setups`. Confluence-stacking helped on 4h (+0.667 vs +0.120) but stacked overfit on 1h → held. `failed_breakout_long`/`liquidity_sweep_*` rejected (overfit).

**Verification:** unit tests + mocked/synthetic integration tests all green; real-data validation run. Committed `3fada87`. Still shadow mode — Telegram delivery behavior unchanged.

### 2026-07-13 (v11.3) — Self-Learning De-Noise + Core-Logic De-Inversion

**Context**: Audit (`AUDIT_2026-07-13.md`) of the full flow found the system stuck in a bad-logic loop AND running on inverted premises. Evidence (237 trades): 4/4 TF confluence is the WORST bucket (18% WR, −0.36R avg) while 3/4 is the only edge (+0.01R); rank-1 picks lose (−19.7R) vs rank-2 (+2.8R); trend_pullback was crowned "BEST TYPE" on WR despite −20.7R net; longs run 29%/−33R (the entire net loss). The learning loop amplified noise: ~120 free-text rule IDs across 60 setups (n=1–3 each), 20 delta insights that never expired (0 confirmed/0 expired), openly contradicting each other (ADA 3×, BTC-anchor 2×, risk_off shorts-only→no-trade). Regime was written at file level but read per-record → 100% defaulted, so regime learning was fiction.

**Fixes (Tier 0 + Tier 2 + hard long gate):**
- **De-noise the loop**: canonical rule taxonomy (`config.CANONICAL_RULES`, 28 IDs) — Claude may only cite these; non-canonical IDs dropped on save (`main.py`) and ignored in stats. Delta insights capped at `MAX_ACTIVE_DELTA_INSIGHTS=6`, stale-expire after 2× threshold, removed the dangerous auto-graduate-to-confirmed. Delta trigger raised 15→25 trades. Purged all 20 contradictory insights.
- **Expectancy over win-rate**: BEST-TYPE, EFFECTIVE/INEFFECTIVE-rules, and regime rules now gate on `avg R:R` sign + `RULE_MIN_SAMPLE=20` / `REGIME_RULE_MIN_TRADES=20` (regimes below threshold emit a soft NEEDS-DATA note, not a hard block — mirrors the direction safeguard).
- **De-invert core logic**: new `by_confluence` bucket + "3/4 CONFLUENCE BEATS 4/4" rule; killed the false "label high-confidence with 4/4" instruction and stale "require 4/4" texts. **Rank de-trust**: hard rule (prompt + `validate_setups`) that a 4/4-confluence setup may never be ranked #1 (rank-1 lost −19.7R, 4/4 bucket −0.36R exp).
- **Validated on history**: replaying the shipped gates over 237 trades moves the book from −34R/PF 0.75 → ≈−13R/PF 0.87, WR 30%→33% (the long gate removed the 20 worst longs at −0.544R each). See `AUDIT_2026-07-13.md` §C.
- **Hard long structural gate**: longs require volume_confirmed AND `tf_confluence≥3` (`LONG_MIN_CONFLUENCE`) AND a stated 2-TF higher-low (prompt) — enforced in `validate_setups`. Confluence floor `≥3` extended to BOTH directions (2/4 loses in longs and shorts).
- **Regime-aware long cap** (`LONG_CAP_BY_REGIME`): risk_off/cautious ≤1 long, neutral ≤2, risk_on ≤5. Longs are the entire net loss (29% WR / −33R over 181 trades); shorts ~breakeven. The excess-long trades this removes are −0.191R exp / −13R over 68 trades. Serves regime-adaptivity + win rate.
- **Fix regime plumbing**: regime stamped per eval result + per setup; `by_regime` prefers per-result. Historical backfilled by rebuilding `lifetime_stats.json` from all 89 eval files.
- Strategic rules went from 34 (20 base + 14 contradictory delta) → 13 clean, non-contradictory, expectancy-gated rules. Pre-audit artifacts backed up in `logs/performance/_pre_audit_bak/`.

**Forward-measurement tooling (how we'll know if v11.3 actually worked):**
- `logs/performance/version_markers.json` records the v11.3 cutover (237 trades, baseline 30.4% WR / −0.144R / PF 0.75, targets: ≥34% WR & ≥0 expectancy over 20 trades).
- `weekly_eval.py::_version_validation_line()` prints a rule-0 verdict at the top of `strategic_rules.md` every `eval-scan`.
- `backtester.py::report_version_segments()` (`python backtester.py --version`, also wired into `backtest` Step 3b) splits trades PRE vs POST v11.3 (POST = trades carrying `interest_score`), compares WR/expectancy/PF, prints `UNPROVEN→VALIDATING→VALIDATED/NOT-VALIDATING`, and audits POST for gate violations (confluence<3, 4/4-at-rank1 — expect 0).
- **CRITICAL for future sessions**: the monthly `backtest` (signal-formula validation + eval combo) does NOT test v11.3's *selection* logic — it reads the 237 pre-v11.3 trades and validates mechanical formulas v11.3 never touched. v11.3's gates are FORWARD selection; the ONLY way to validate them is `eval-scan` scoring new picks → the version segment. As of 2026-07-13 the verdict is `UNPROVEN` (0 v11.3 trades evaluated; ADA/XRP shorts from the first v11.3 scan still open, need ~2 days + an `eval-scan`).

**Files**: config.py, main.py, weekly_eval.py, analyzer/prompts.py, fetchers/bybit_data.py (interest_score), backtester.py + historical_backtester.py (version segment), CLAUDE.md, progress.md, AUDIT_2026-07-13.md, logs/performance/version_markers.json. No R:R-floor change, no execution path, no expanded perms. Commits: aa66077 (v11.3 core), 02097c7 (version segment report).

### 2026-07-12 (v11.2) — Execution Overhaul: T1→T2 Floor Relocation, Long Volume Gate, +0.3R Trail

**Context**: With 237 evaluated trades (30% WR, −34R, PF 0.75), re-ran `backtester.py` to quantify fixes for the long-standing execution leak. Diagnosis held: **direction is right 64% of the time (avg MFE 1.03R) but targets sit past the average excursion** — trades reach ~1R, never tag T1, reverse, and pay the full −1R stop. Three fixes implemented and backtested; #4 (regime tightening) scoped out for now.

**1. T1 is now a partial-profit level; the 1.5:1 floor moved to T2** (`analyzer/prompts.py`, `main.py::validate_setups`)
- The old prompt *pinned* `predicted_rr` (R:R to T1) at exactly 1.5 — the leak itself. Since avg MFE is only 1.03R, a 1.5R T1 was unreachable (T1 hit rate 31%).
- **New rule: T1 at 0.75–1.0R (predicted_rr 0.75–1.0), and the 1.5:1 minimum-edge floor now lives on target_2** (the reward leg). Risk framework intact — not weakened, relocated.
- `validate_setups()` now enforces both: flags `predicted_rr > 1.1` (T1 too far) AND computes R:R to T2, flagging `< 1.4` (edge floor). JSON schema example + notes updated.
- **Backtest**: current blended −24.8R → **T1@0.75R = +5.2R (+30R)**; T1@1.0R = −9.1R. 0.75R would have hit 54% vs current 31%. Flips the whole book positive.

**2. Long volume gate + long blacklist** (`analyzer/prompts.py`, `main.py::validate_setups`)
- Longs = 52/181 (−33.2R) vs shorts 20/56 (−0.9R) — longs are essentially the entire loss. But the real discriminator is volume, not direction: longs **without** volume = −0.24R expect / PF 0.60; longs **with** volume = **+0.15R / PF 1.25** (`vol_confirmed + rank≤3 + long` → +0.39R / PF 1.70).
- **New rule: every long MUST have `volume_confirmed=true`, in every regime.** Validator rejects volume-less longs. This is the `vol_confirmed` slice v11.1 flagged but deferred (Goodhart risk, n=25) — now acted on at n=237.
- Long blacklist (deeply negative history, shorts still allowed): ENA/ETH/HBAR/WLD/HYPE/ONDO/LAB.

**3. Eval model: +0.3R trail replaces bare breakeven** (`weekly_eval.py::evaluate_setup`)
- Old model returned the runner all the way to breakeven (0R). 18 BE-stops gave back MFE of 1.0–2.2R — structural winners handed back to zero.
- **New model: once price runs 1.0R in profit, the stop tightens to +0.3R (not BE).** Worst case after 1R is +0.3R. Uses prior-candle MFE (no intracandle look-ahead). New `trail_stop_hit` field + `partial_profit.trail_stops` counter. Prompt position-management guidance updated to match.
- **Backtest (floor-at-+0.3R-after-1R model)**: −34R → **+2.2R (+36R)**, 44 trades rescued (22 were full −1R stops, 22 were BE-to-zero).
- Overlaps #1 (same "reached 1R then reversed" bucket) — the two do not add linearly.

**Two free findings surfaced (not yet acted on)**: (a) 3/4 TF confluence *beats* 4/4 — the "4/4 = high confidence" mapping is inverted (4/4 = already-extended = late entry); noted in prompt. (b) `risk_off` loses in both directions (shorts 0/5, longs mixed) — regime gate should be zero setups in risk_off; deferred to the #4 regime pass.

**Verification**: all files compile; trail model unit-tested through real `evaluate_setup` on synthetic klines (ran-1.1R-then-reversed → +0.3R rescue; T1-hit-MFE<1 → BE preserved; dead-on-arrival → −1R intact); validator 6/6 cases correct. Live `scan` ran clean (exit 0, zero violations): 2 shorts, both `trend_pullback`, T1 at 0.88–0.89R / T2 at 1.57–1.72R — T1 placement fix visibly working vs the old 1.5R.

**Note**: #3 only affects NEW evals going forward (existing eval JSONs keep old scores unless re-run). Effect proves out as these setups resolve under `eval-scan`.

### 2026-07-06 (v11.1) — Backtest Re-Validation + Root-Cause Analysis + Entry-Indicator Instrumentation

**Context**: Re-ran the `backtest` pipeline (monthly re-validation) on fresh 15-symbol data, then dug into why the live system is net-losing over 206 evaluated trades. A proposed prompt fix was rejected after a data double-check; shipped instrumentation instead so the next round can be decided by evidence.

**1. Backtest reconciliation — updated live validated signals** (`fetchers/bybit_data.py::_check_validated_signals`)
- The Jul-2026 re-run changed which formulas hold out-of-sample. Reconciled the hardcoded live set to match:
  - `rsi_rejection_short` — kept (★ STRONG both TFs: 4h test +0.44, 1h test +0.81)
  - `macd_momentum_long` — kept (confirmed both TFs: 4h +0.25, 1h +0.59)
  - `trend_pullback_short` — **gated to 4h ONLY** (4h test +0.28, N=111, 100% robust; 1h now rejected as overfit, all variants negative test exp)
  - `macd_momentum_short` — **REMOVED** (degraded to overfit on BOTH TFs — was actively injecting a losing signal into Claude's context every scan)
- Refreshed docstring + `historical:` strings to new test numbers. CLAUDE.md architecture/data-flow/glossary updated to describe the 3-signal set and monthly re-validation cadence.

**2. Root-cause analysis of the net-loss (206 triggered trades: 29% WR, −0.166R, PF 0.72)**
- **Direction is right 61% of the time** (MFE ≥0.5R) — the reads are good. The leak is execution.
- **One-trick pony**: `trend_pullback` = 175/206 (85%) of all trades; runs −0.116R, 54% stop rate. System performance ≈ trend_pullback performance.
- **Stop shakeout is the dominant leak**: 57% hit stop; ~34 trades (17%) eventually ran ≥1.0R in the predicted direction but were stopped out first (MFE≥1.0R = 42% vs sim-T1@1.0R-before-stop = 25%).
- **Confidence is anti-predictive**: `high` = 22% WR (worst, 78% stop), `low` = 32% (best).
- **tf_confluence runs backwards for trend_pullback**: 4/4 = 17% WR (worst), 3/4 = 36% (best), 2/4 = 22%. More alignment → worse (chase signature).

**3. Proposed prompt edits REJECTED after double-check** (not implemented)
- Edit A (make trend_pullback "earn" its label via strict ADX>25 / near-EMA20 / MACD gate) and Edit B (gate "high" confidence on a fired backtested signal) were drafted, then killed:
  - **Edit B is inert**: confidence is a pure label — never gates selection or drops a setup (confirmed: no confidence filter in `main.py`/`claude_client.py`; `weekly_eval.py` scores ALL output setups). Win-rate impact = 0.
  - **Edit A unproven / contradicted**: the only logged strictness proxy (tf_confluence) runs backwards; the +0.28R justifying the strict gate is from the mechanical backtester (different population from Claude's discretionary label); and setup records store NO entry indicators, so the thesis is unmeasurable with current data.

**4. Instrumentation added** (`main.py::enrich_with_entry_indicators`, new helper)
- Every saved setup now carries an `entry_indicators` block: 4h + 1h `{adx, rsi, macd, macd_hist, trend, ema20_dist_atr, range_pct}` + `backtested_signal` (which validated signal fired for that symbol/direction, or null).
- Values pulled from `market['technicals']` at save time. **Zero tokens, changes no behavior.** Missing-symbol setups are skipped gracefully.
- Purpose: unblock the strict-gate thesis. After ~15-20 new trades carrying this data are eval-scored, we can finally test whether stricter trend_pullbacks (and backtested-signal-backed setups) actually win — see "What's Next".

**Decisions deferred (thin data)**: `vol_confirmed` is the only slice that flips positive (long+vol_confirmed +0.204 vs long alone −0.172), BUT it's Claude-self-reported (Goodhart risk) and n=25. Left untouched until more data accumulates.

### 2026-07-03 (v11.0) — Historical Backtester + Empirically Validated Signal Pre-Filters

**Problem**: Claude was generating all trade setups from scratch using indicator data + knowledge files, but there was no empirical validation of WHICH indicator combinations actually predict price movement. The system had no way to distinguish real patterns from noise. Some of Claude's "best" setups (rank #1) were actually the worst performers (22.8% WR vs 34% for rank #2). Direction was right 63% of the time (MFE ≥ 0.5R) but targets were too far — an execution problem, not an analysis problem.

**Solution**: Built a complete backtesting pipeline that tests mechanical signal rules against historical Bybit data, optimizes parameters via grid search, and validates findings with train/test split to eliminate overfitting. Only formulas that pass out-of-sample validation on BOTH 1h and 4h timeframes across 15 symbols are integrated into the screener.

**4 New Components:**

**1. What-If Backtester** (`backtester.py`, new file)
- Reads all 185 evaluated trades from `logs/evaluations/` + `logs/setups/`
- Sweeps: T1 distance, filters (confidence/direction/regime/rank/type/confluence), regime limits, symbol blacklists
- Auto-discovers best filter combinations (tested 100+ combos)
- Reports: baseline stats, dimension breakdowns, T1 sweep, rank cutoff, regime limit sweep, symbol report, MFE analysis, combined filter discovery, actionable findings
- Key finding: T1 at 0.75R saves 26 losing trades → +20R blended sum improvement
- Zero Claude tokens, runs in <1 second

**2. Historical Strategy Backtester** (`historical_backtester.py`, new file)
- Fetches 1000 candles per symbol from Bybit (1h = 42 days, 4h = 167 days), caches locally in `logs/backtest_cache/`
- 12 mechanical signal rules defined from knowledge files: trend_pullback (long/short), range_reversion (long/short), volume_breakout (long/short), ema_crossover (long/short), macd_momentum (long/short), rsi_bounce/rejection
- Each signal uses: RSI, EMA 20/50, ADX, MACD, ATR — same indicators already computed by the screener
- Forward evaluation engine: for each fired signal, checks forward candles for target/stop hit, computes actual R:R and MFE
- Initial test on 6 coins, 1h: 574 signals → shorts outperform longs (+0.142 vs -0.018 expectancy)
- Zero Claude tokens, reuses cached kline data

**3. Parameter Sweep Optimizer** (`--optimize` flag in historical_backtester.py)
- Parameterized signal factories for each signal type (tunable: RSI range, ADX threshold, ATR stop multiplier, EMA proximity, volume requirement, MACD confirmation)
- Fast numpy-based evaluation engine: sweeps 2,048 parameter combos × 5 target levels in ~30 seconds per signal
- Sensitivity analysis: shows which parameters matter most (e.g., `require_macd=True` consistently outperforms `False`)
- Grid search across all 10 signal types with parameter grids defined per signal

**4. Train/Test Validation + Robustness Scoring** (`--validate` flag)
- Splits cached data 60/40: optimizes parameters on train half, evaluates on test half
- If test expectancy drops to 0 or negative → overfit, discard
- Robustness score: checks if neighboring parameter values also have positive expectancy
- Run on 15 symbols across BOTH 1h and 4h timeframes for cross-TF confirmation
- **Result: 4 out of 8 signal types were overfit → discarded. Only 4 passed cross-TF validation.**

**Validation Results (15 symbols, 60/40 train/test split):**

| Signal | 4h Test Expect | 1h Test Expect | Robust | Verdict |
|---|---|---|---|---|
| rsi_rejection_short | +0.362 | +1.100 | 67-100% | **CONFIRMED** |
| macd_momentum_long | +0.500 | +0.389 | 67-100% | **CONFIRMED** |
| macd_momentum_short | +0.357 | +0.157 | 86-100% | **CONFIRMED** |
| trend_pullback_short | +0.080 | +0.151 | 100% | **CONFIRMED** |
| trend_pullback_long | -0.149 | -0.529 | — | **OVERFIT → REJECTED** |
| range_reversion_short | -0.286 | +0.154 | — | **1h only → REJECTED** |
| range_reversion_long | -0.250 | -0.423 | — | **OVERFIT → REJECTED** |
| rsi_bounce_long | -0.217 | +0.397 | — | **1h only → REJECTED** |

**5. Integration into Screener Pipeline** (`bybit_data.py`, `claude_client.py`)
- New `_check_validated_signals()` in `bybit_data.py`: checks 4 confirmed formulas on each coin's 1h and 4h candles during `get_multi_tf_indicators()` — zero extra API calls
- Validated signal parameters (cross-TF consensus):
  - `rsi_rejection_short`: RSI was >75, recovering below 72, 2.0 ATR stop, target 2.0R
  - `macd_momentum_long`: MACD hist flips positive, EMA20>EMA50, ADX>20, RSI 35-65, 1.5 ATR stop, target 1.5R
  - `macd_momentum_short`: MACD hist flips negative, EMA20<EMA50, ADX>15, RSI 30-55, 1.0 ATR stop, target 1.5R
  - `trend_pullback_short`: EMA20<EMA50, RSI 50-70, near EMA20, MACD negative, ADX>15, 1.5 ATR stop, target 2.0R
- New `BACKTESTED SIGNALS` section injected into Claude's user content when signals fire
- Claude sees: symbol, signal name, direction, target, stop, historical WR/expectancy
- Claude is told to PRIORITIZE validated signals, not override their direction
- Token impact: ~50-170 tokens per signal (typically 0-3 per run, <1% of total budget)

**What stays the same:**
- Claude still makes final selection — validated signals are guidance, not override
- Eval system tracks validated setups normally → we'll see if WR improves over weeks
- No new API calls, no new dependencies, no changes to main.py
- All existing knowledge files, regime detection, streak detection unchanged

**Usage:**
```bash
# What-if backtester (existing eval data)
python backtester.py                              # Full report
python backtester.py --t1-sweep                   # Just T1 analysis
python backtester.py --combo                      # Best filter combos

# Historical backtester (Bybit kline data)
python historical_backtester.py                   # Default: 6 coins, 1h, fixed signals
python historical_backtester.py --interval 240    # 4h timeframe
python historical_backtester.py --optimize all    # Parameter sweep all signals
python historical_backtester.py --validate all    # Train/test validation
python historical_backtester.py --full            # Full pipeline: 4h + 1h validate + eval combos (recommended)

# Screener (validated signals now included automatically)
python main.py                                    # scan as usual — validated signals injected if they fire
```

**Terminal shortcuts** (defined in `~/.zshrc`):
- `scan` — nightly screener (daily)
- `eval-scan` — weekly evaluation + delta analysis
- `backtest` — full backtest pipeline: validate 4h + 1h + eval combos (monthly)
- `trade` — manual trade logger
- `pulse` — momentum pulse (runs automatically on GitHub Actions)
- `quarterly-scan` — deep analysis (optional — superseded by `backtest` + delta analysis)

**Recommended workflow:**
- **Daily:** `scan` (or let launchd run it at 9pm)
- **Weekly:** `eval-scan` (scores past setups, updates rules, triggers delta analysis)
- **Monthly:** `backtest` (re-validates signal formulas with fresh market data)

**Cost impact**: Zero for backtesting tools (pure Python + cached Bybit data). Signal detection in live pipeline: zero extra API calls, ~100-200 tokens per run in Claude prompt. Total monthly cost unchanged.

---

### 2026-06-25 (v10.1) — Self-Learning System: Delta Analysis, Reasoning Capture, Regime Tracking

**Problem**: The system's feedback loop was shallow — it tracked WHAT failed (aggregate win rates by type, confidence, rank) but not WHY (which rules Claude applied, under what market regime). The quarterly deep analysis ran every ~3 months, far too slow for meaningful self-improvement. There was no mechanism to verify whether insights from past analyses actually helped.

**6 Improvements:**

**1. Reasoning Capture in Setup JSON** (`analyzer/prompts.py`)
- New `reasoning` field in every setup: `rules_applied` (list of rule IDs) + `key_factor` (one-line primary driver)
- Example: `{"rules_applied": ["trend_pullback_priority", "btc_bearish_guard"], "key_factor": "4h pullback to EMA20 with volume surge"}`
- Carried through to eval results → tracked in `lifetime_stats.json::by_rule_applied`
- Enables rule-level attribution: "When Claude cited `ada_priority`, did those setups win more?"

**2. Regime Tagging** (`main.py`, `weekly_eval.py`)
- Market regime (`risk_off`/`cautious`/`neutral`/`risk_on`) saved in both setup records and eval records
- Tracked in `lifetime_stats.json::by_regime`
- Enables regime-specific learning: "Do trend_pullback longs work in cautious regime?"

**3. Delta Analysis — Automated Self-Learning** (`weekly_eval.py`, `config.py`)
- Auto-triggers after every `eval-scan` when 15+ new evaluated trades have accumulated
- Calls Claude to: (a) grade previous insights as EFFECTIVE/INEFFECTIVE/INCONCLUSIVE, (b) find 2-5 new patterns
- Insight lifecycle: `experimental` (new, use as guidance) → `confirmed` (graded effective, follow strictly) → `expired` (graded ineffective, removed)
- Registry: `logs/performance/rule_registry.json` tracks insight history and win rate snapshots
- Replaces the slow quarterly cadence — faster feedback loop without any new commands
- Cost: ~12k input + 1.5k output tokens per analysis (far less than nightly scan)
- Config: `DELTA_ANALYSIS_TRADE_THRESHOLD = 15`, `DELTA_ANALYSIS_MIN_TRADES = 20`

**4. Regime-Aware Strategic Rules** (`weekly_eval.py::generate_strategic_rules()`)
- New per-regime performance rules: surfaces win rate per regime (e.g., "CAUTIOUS REGIME LOSING: 3/20, 15% WR")
- New rule-applied effectiveness rules: surfaces which reasoning rules correlate with wins/losses

**5. Post-Scan Python Validation** (`main.py::validate_setups()`)
- Pure Python (zero tokens) — runs after Claude's output is parsed, before saving
- Checks: setup count vs regime limit, valid types/directions/timeframes, predicted_rr cap (1.5), duplicate symbols, direction requirements per regime
- Violations logged as warnings — does not block saving (eval can still track outcomes)

**6. Delta Insights in Strategic Rules** (`weekly_eval.py`)
- Active delta insights appended to `strategic_rules.md` under `## Delta Insights (Self-Learning)`
- Status markers: `[?]` = experimental (guidance), `[✓]` = confirmed (follow strictly)
- Expired insights auto-removed from rules
- Old quarterly section replaced by delta insights (quarterly_analysis.py still available for manual deep-dives)

**Workflow unchanged**: `scan` daily + `eval-scan` weekly. Delta analysis piggybacks on eval-scan when threshold is met. No new commands needed.

**What the eval tracks (new):**
- Per-regime win rate (`by_regime`)
- Per-rule-applied win rate (`by_rule_applied`)
- Insight effectiveness (graded by delta analysis)
- Setup validation violations (logged as warnings)

**Cost impact**: ~250 extra output tokens per nightly scan (reasoning field). Delta analysis: ~13.5k tokens every ~15 trades (~2 weeks). Post-scan validation: 0 tokens.

---

### 2026-06-17 (v10.0) — Extended Thinking + MACD & SMA200 Indicators

**Problem 1: Telegram flooded with working notes, not actionable briefs.**
Claude was writing 300+ lines of pre-analysis reasoning (candidate scanning, rule checking, R:R calculations) directly in its output, consuming all 8k output tokens before the actual formatted brief was produced. Telegram received raw thinking instead of trade setups.

**Problem 2: Missing momentum and long-term trend indicators.**
No MACD for momentum confirmation/divergence detection. No SMA200 for macro trend filtering on the daily timeframe.

**4 Changes:**

**1. Extended Thinking Enabled** (`analyzer/claude_client.py`, `config.py`)
- Enabled Anthropic's extended thinking API feature (`thinking.type: "enabled"`)
- Claude's reasoning now goes into a separate `thinking` block (budget: 10k tokens via `THINKING_BUDGET`)
- Only `text` content blocks are extracted for the brief — thinking blocks are never sent to Telegram
- `max_tokens` = `MAX_TOKENS_OUTPUT` (8k) + `THINKING_BUDGET` (10k) = 18k total
- Claude thinks more thoroughly AND the output is cleaner

**2. Pre-Analysis Safety Net** (`main.py`, `analyzer/prompts.py`)
- Added `strip_pre_analysis()` — strips any text before the first `## ` header as a safety net
- Prompt now instructs Claude: "Output ONLY the formatted brief. Do NOT write pre-analysis notes."
- Applied before both archiving and Telegram delivery

**3. MACD Indicator Added** (`fetchers/bybit_data.py`, `analyzer/prompts.py`)
- MACD(12,26,9) computed on all 4 timeframes
- Output: `macd` (momentum direction: >0 bullish, <0 bearish) + `macd_hist` (acceleration: >0 gaining, <0 fading)
- Token impact: ~600 tokens (+3% of input)
- Prompt includes interpretation guide: confirms trends, spots divergences

**4. SMA200 Indicator Added** (`fetchers/bybit_data.py`, `config.py`, `analyzer/prompts.py`)
- SMA(200) computed on 1D only — requires 200+ candles
- 1D kline limit bumped: 60 → 210 candles (same API call count, slightly larger response)
- Only included in output when not NaN (i.e., only 1D data) — zero token bloat on 15m/1h/4h
- Token impact: ~75 tokens (<0.5%)
- Prompt includes interpretation: macro trend filter, dynamic S/R, mean reversion gauge

**Cost impact:** Per-run increases ~60% ($0.15→$0.25 Sonnet) due to thinking tokens, but output quality dramatically improves — Claude now always produces a complete formatted brief instead of exhausting tokens on working notes.

---

### 2026-06-05 (v9.2) — Regime Enforcement Fix + Drop Swing Timeframe

**Problem**: Last 12 eval runs (May 21 - Jun 5) produced 3W/52L = 6% win rate, dragging cumulative WR from 43% to 29.8%. Despite market being risk_off (84% declining, BTC -3%), system kept recommending all-long setups. Analysis revealed: (1) regime limits existed only in system prompt — Claude saw "RISK_OFF" label and metrics in user content but no explicit "max 2 setups" instruction, (2) multiple overlapping limits (regime, streak, loss rate) with no single resolved directive, (3) JSON example showed `predicted_rr: 2.5` while rules said "exactly 1.5", (4) swing trades added overnight risk for no benefit (25% WR vs 30% intraday).

**4 Fixes:**

**1. Explicit Regime Enforcement in User Content** (`analyzer/claude_client.py`)
- Each regime now injects MANDATORY limits directly into user message (not just system prompt)
- risk_off: "MAXIMUM 2 setups, at least 1 SHORT, longs ONLY with 4/4 TF + volume + structural support"
- cautious: "MAXIMUM 3 setups, every long MUST have volume OR 4/4 TF, include 1 SHORT"
- risk_on: "Maximum 5 setups, favor trend-following longs"
- neutral: "Maximum 3 setups, no directional bias"
- Missing regime data now defaults to neutral with explicit max 3 (was silent empty string)

**2. Effective Limit Computation** (`analyzer/claude_client.py`)
- New logic resolves regime limit, losing streak limit, and loss rate limit into ONE number
- Claude sees a single clear directive: `EFFECTIVE LIMIT THIS RUN: MAXIMUM 2 SETUPS`
- Shows the reasoning: "resolved from regime (2) + losing streak (3). Strictest applies: 2"
- "Output more than 2 setups and the entire output is invalid" — removes all ambiguity

**3. Drop Swing Timeframe** (`analyzer/prompts.py`, `weekly_eval.py`, `knowledge/07_watchlist.md`, `knowledge/trading_rules.md`, `config.py`)
- Removed "swing" as a valid timeframe option — only "scalp" and "intraday" allowed
- Data justification: swing was 25% WR (3/9) vs intraday 30% (45/103), and 92% of trades were already intraday
- Reduced overnight/macro risk — crypto is 24/7, geopolitics can nuke positions while sleeping
- Faster eval feedback loop — no more 7-day wait for swing evaluation
- Legacy swing setups in eval files handled gracefully (fall through to 2-day default window)
- Updated: prompts.py (SL/target guidelines, JSON schema, TF options, example), weekly_eval.py (EVAL_WINDOWS), knowledge files (07_watchlist.md, trading_rules.md), config.py (comment)

**4. Prompt Consistency Fixes** (`analyzer/prompts.py`)
- Fixed JSON example: `predicted_rr: 2.5` → `1.5` (was contradicting the "exactly 1.5" rule)
- Regime enforcement language: "ENFORCE" → "LAW — not guidance", pointed to EFFECTIVE LIMIT
- Performance guidance language: removed blanket "apply judgment" escape, now tiered by sample size (50+=mandate, 30-49=strong, <30=hint)
- Short requirement strengthened: in risk_off "shorts should be your DEFAULT direction", added specific short setup types to look for
- Updated MFE stats to 161-trade data (was 141)

**What Claude sees differently (before vs after, in current risk_off market):**

Before:
```
## Market Regime: RISK_OFF
- 84.0% of top 50 coins declining
- BTC 24h: -3.06%
```
(No limits, no direction requirement, no effective max)

After:
```
## Market Regime: RISK_OFF
- 84.0% of top 50 coins declining
- BTC 24h: -3.06%

⚠️ MANDATORY REGIME LIMITS (non-negotiable):
- Output MAXIMUM 2 setups this run. No exceptions.
- At least 1 setup MUST be a SHORT...
- Longs ONLY if 4/4 TF + volume confirmed + structural support...

⚠️ EFFECTIVE LIMIT THIS RUN: MAXIMUM 2 SETUPS
This is the resolved limit from regime (2) + losing streak (3). Strictest applies: 2.
Output more than 2 setups and the entire output is invalid.
```

**Cost impact**: ~+100-200 tokens per run (regime limits section + effective limit section). Well below 2x threshold. No additional API calls.

**Expected impact**: With current risk_off regime + 3 consecutive SLs, the system would output max 2 setups with at least 1 short — instead of 3-5 all-long setups fighting the market. The explicit effective limit removes the ambiguity that let Claude ignore regime constraints.

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
- Secrets stored as GitHub repository secrets (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID) — no Bybit key (public data only)
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

### Short Term

_The active roadmap + "resume here" pointer live in **"Current Status & Roadmap (READ FIRST)"** at the TOP of this file — that supersedes any older "next session" note that used to sit here. Completed work is in the Changelog below and is NOT repeated as a checklist._

- [ ] **Monthly `backtest` re-validation** — re-run `backtest`, reconcile `_check_validated_signals` + `mechanical_setups.EXPECTANCY/SETUP_TYPE/SETUP_RULE` to fresh results, promote/demote signals (last full run 2026-07-21).
- [ ] **Per-symbol / long-blacklist review** — BTCUSDT/ETHUSDT historically weak; ETHUSDT already long-blacklisted. Revisit the blacklist with fresh eval data.
- [ ] _(Superseded by the mechanical migration)_ the old v11.1 "strict-gate re-check" for Claude's trend_pullback labeling — the same ADX/EMA/MACD confirmation gate is now tested mechanically via confluence-stacking (Phase 3). Context in memory `project-root-cause-trend-pullback`; no separate action needed.

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
