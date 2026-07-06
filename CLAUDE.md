# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**crypto-screener** is a personal, scheduled screener for Bybit USDT perpetual futures. It scans 50 coins, pre-filters to 25 using knowledge-based scoring, analyzes them across 4 timeframes via Claude API, delivers the 5 best trade setups to Telegram, and self-evaluates past recommendations against actual price data.

### Current Phase

**Phase A — Analyst mode (signal-only, NOT auto-trading).**
Claude analyzes data and surfaces setups. The human makes every trading decision and executes every order manually. Phase B (auto-execution) is explicitly out of scope until Phase A has shown measurable edge.

### Non-Goals (Important)

- Do NOT add order execution logic, even if asked casually.
- Do NOT wire Claude output directly to the Bybit write API.
- Do NOT expand the Bybit API key permissions beyond Read-Only.
- Do NOT weaken R:R below 1.5:1 minimum floor or remove risk flags from output. (Lowered from 2:1 to 1.5:1 based on 98-trade backtest showing avg MFE of 1.15R — the old 2:1 floor forced unreachable targets.)

Auto-execution will only be considered after: (a) 60+ days of evaluated Phase A data, (b) a separate hard-coded risk engine (not Claude) for position sizing, (c) model comparison data (Sonnet vs Haiku), and (d) explicit user approval.

---

## Architecture

```
main.py  (orchestrator, async)
  │
  ├── fetchers/bybit_data.py       → BybitFetcher:
  │                                    get_top_movers(50) → single API call
  │                                    _ticker_interest_score() → knowledge-based pre-filter + hot list bonus
  │                                    _load_hot_list() → reads momentum pulse hot list
  │                                    get_multi_tf_indicators() → 15m/1h/4h/1D klines + validated signal check
  │                                    _compute_indicators() → RSI, EMA20/50, ATR, ADX, MACD, SMA200 (1D only), divergences
  │                                    _check_validated_signals() → 3 backtest-validated formulas (2 cross-TF, 1 4h-only)
  │                                    get_full_market_snapshot() → 50 → score → top 25 + hot list → multi-TF
  │
  ├── fetchers/telegram_reader.py  → TelegramReader: Telethon (currently disabled)
  │
  ├── analyzer/prompts.py          → SYSTEM_PROMPT + load_knowledge() + performance feedback + regime awareness
  ├── analyzer/claude_client.py    → ClaudeAnalyzer: Anthropic SDK, prompt caching, extended thinking,
  │                                    compact JSON, regime injection + explicit regime limits,
  │                                    effective limit computation, BTC daily trend guard,
  │                                    losing streak detection, recent loss rate injection
  │
  ├── delivery/telegram_bot.py     → MD→HTML converter, smart chunking, retry with backoff
  │
  ├── momentum_pulse.py            → Lightweight momentum detector (runs every 4h on GitHub Actions)
  │                                    Fetches 50 tickers, detects acceleration vs previous snapshot,
  │                                    flags coins to hot_list.json, sends Telegram alert. Zero Claude tokens.
  │                                    detect_market_regime() → classifies market as risk_off/cautious/neutral/risk_on
  │                                    Sends regime change alerts to Telegram. Regime saved in hot_list.json.
  │
  ├── weekly_eval.py               → Evaluation engine: scores past setups, tiered knowledge distillation,
  │                                    simulated T1 backtest, per-symbol tracking, prescriptive rules
  ├── quarterly_analysis.py        → Claude-powered deep pattern analysis (run every ~3 months)
  ├── trade_logger.py              → CLI tool for managing my_trades.json (open/close/list trades)
  │
  ├── backtester.py                → What-if backtester: sweeps T1/filters/regime limits across eval logs
  ├── historical_backtester.py     → Historical strategy backtester: 12 signal rules, parameter optimizer,
  │                                    train/test validation, robustness scoring. Caches Bybit klines locally.
  │                                    validated formulas integrated into live screener pipeline (re-validated monthly).
  │
  ├── knowledge/*.md               → 9 trading knowledge files (01–08 + trading_rules)
  └── logs/
        ├── briefs/*.md            → Archived readable briefs
        ├── setups/*.json          → Structured setup JSONs (with model name)
        ├── evaluations/*.json     → Scored results (win/loss, actual R:R, MFE, simulated T1)
        ├── momentum/
        │     ├── hot_list.json    → Active momentum-flagged coins + market regime (dynamic watchlist)
        │     └── last_snapshot.json → Previous pulse data + regime (for delta detection)
        ├── performance/
        │     ├── lifetime_stats.json    → Layer 1: Incremental running counters (incl. by_symbol, simulated_t1)
        │     ├── strategic_rules.md     → Layer 2: Prescriptive rules from all history (~600-800 tokens, sent to Claude)
        │     ├── recent_performance.md  → Layer 3: Rolling 4-week trade details (~800 tokens, sent to Claude)
        │     ├── summary.md             → Human-readable report (NOT sent to Claude)
        │     ├── win_rate_history.json   → Win rate snapshots over time
        │     ├── rule_registry.json     → Delta analysis registry (insight tracking, effectiveness)
        │     └── quarterly/             → Deep analysis + delta analysis logs
        └── backtest_cache/              → Cached Bybit klines for historical backtesting (JSON, no expiry)
```

### Data Flow

0. Every 4h: `momentum_pulse.py` (GitHub Actions) → fetches 50 tickers, detects acceleration vs previous snapshot → flags coins to `logs/momentum/hot_list.json` + classifies market regime (`risk_off`/`cautious`/`neutral`/`risk_on`) → Telegram alert (regime changes + new flags)
1. `BybitFetcher.get_top_movers(50)` → 50 tickers by turnover (single API call)
2. `_load_hot_list()` → loads momentum pulse hot list (dynamic watchlist, 48h expiry) + market regime
3. `_ticker_interest_score()` → disqualify illiquid (<$10M vol, <$50M OI), score rest + volume acceleration bonus for hot list coins
4. Keep top 25 by score + watchlist + hot list → `get_multi_tf_indicators()` for each (4 TFs × 25 = 100 kline calls) + `_check_validated_signals()` on 1h/4h (zero extra API calls)
5. `ClaudeAnalyzer.analyze(market, messages)` → extended thinking enabled (reasoning in separate thinking block, not in output) → injects regime metrics + explicit regime limits + effective limit computation + losing streak detection + BTC trend guard + **validated signals** into user content → readable brief + `setups_json` block
6. `main.py` parses JSON block → validates against rules (Python, free) → saves to `logs/setups/` (includes model name, regime, reasoning)
7. Clean brief (JSON stripped + pre-analysis stripped) → archived to `logs/briefs/` + delivered via Telegram
8. Weekly: `weekly_eval.py` scores past setups (incl. simulated closer-T1 backtest) → updates tiered knowledge:
   - `lifetime_stats.json` — incremental counters incl. by_symbol, by_regime, by_rule_applied, simulated_t1 (O(1) per new eval)
   - `strategic_rules.md` — prescriptive rules with ACTION lines (~600-800 tokens) + delta insights
   - `recent_performance.md` — rolling 4-week trade details (~800 tokens)
   - `summary.md` — full human-readable report (NOT sent to Claude)
   - **Delta analysis** — auto-triggered every 15 new trades: Claude finds patterns, grades previous insights, generates new ACTION rules → appended to strategic_rules.md
9. Next run: `build_system_prompt()` loads strategic_rules (incl. delta insights) + recent_performance → Claude self-calibrates
10. Quarterly: `quarterly_analysis.py` uses Claude for deep patterns → can still be run manually for thorough analysis

### Pre-Filter Scoring (Python, free)

Runs on ticker-level data before any kline fetching. Rules from knowledge files:

| Factor | Source | Thresholds |
|---|---|---|
| Hard disqualify | `02_risk_management` | <$10M turnover or <$50M OI |
| Liquidity tiers | `04_volume_analysis` | $50M→1pt, $100M→2, $500M→3, $1B+→4 |
| Price action | `05_crypto_specifics` | 1.5%→1, 3%→2, 5%→3, 10%→4, 15%+→5 |
| Funding extremes | `04_volume_analysis`, `06_setup_playbook` | ±0.01%→1, ±0.03%→3, ±0.05%+→5 |
| OI + big move | `04_volume_analysis` | $200M+ OI and >5% change → +2 |
| Funding squeeze | `06_setup_playbook` Setup 5 | Extreme funding + price flat (<3%) → +3 |
| Post-liquidation | `06_setup_playbook` Setup 6 | >10% move + >$200M turnover → +2 |
| Volume acceleration | `momentum_pulse.py` hot list | >2x previous pulse → +2, >5x → +4 |

### Momentum Pulse (GitHub Actions, free)

Runs every 4 hours on GitHub Actions. Zero Claude tokens, single Bybit API call per run.
Detects intra-day momentum that the nightly scan would miss.

**Per-coin detection criteria** (any one triggers a flag):
- **Big move**: >8% price change AND >$200M turnover
- **Volume acceleration**: turnover >3x the previous pulse (4h earlier)
- **Funding squeeze**: |funding| >0.05% AND price moving >3%

Flagged coins are saved to `logs/momentum/hot_list.json` (48h expiry) and included as a
dynamic watchlist in the next main scan. A Telegram alert is sent immediately for new flags.

**Market regime detection** (aggregate, from the same 50-ticker data):
- Classifies overall market as `risk_off`, `cautious`, `neutral`, or `risk_on`
- Metrics: % of coins declining, median 24h change, BTC 24h change, avg funding rate, large decline count
- Regime metrics are ALWAYS injected into Claude's user content (not just when non-neutral)
- Classification thresholds (tunable in config):
  - `risk_off`: (≥70% declining AND median ≤ -2%) OR (BTC ≤ -4%) OR (≥60% declining AND BTC ≤ -3%)
  - `cautious`: (≥55% declining AND median ≤ -0.5%) OR (BTC ≤ -2%) OR (≥50% declining AND BTC ≤ -1.5%)
  - `risk_on`: (≤30% declining AND median ≥ +2%) OR (BTC ≥ +4%) OR (≤40% declining AND BTC ≥ +3%)
  - `neutral`: everything else
- Regime saved in `hot_list.json` (read by main scan) and `last_snapshot.json` (for transition detection)
- Telegram alert sent on regime transitions (e.g., neutral → cautious → risk_off)
- During `risk_off`: Claude max 2 setups, at least 1 short, longs only with 4/4 TF + volume + structural support
- During `cautious`: Claude max 3 setups, longs require volume OR 4/4 TF, must include 1 short if bearish structure exists
- During `risk_on`: Claude favors trend-following longs, shorts only with clear distribution, max 5 setups

**Effective limit computation** (in `claude_client.py`):
- Resolves regime limit, losing streak limit, and loss rate limit into a single number
- Claude sees ONE directive: `EFFECTIVE LIMIT THIS RUN: MAXIMUM N SETUPS` with reasoning
- "Output more than N setups and the entire output is invalid" — removes all ambiguity
- Example: risk_off (max 2) + 3 consecutive SLs (max 3) → effective max = 2

**Losing streak circuit breaker** (in `claude_client.py`):
- `_detect_losing_streak()` reads recent eval files and counts consecutive stop losses
- 5+ consecutive SLs: LOSING STREAK ALERT injected — max 2 setups, require volume OR 4/4 TF
- 3-4 consecutive SLs: CAUTION injected — max 3 setups, increase quality bar

---

## Tech Stack & Conventions

- **Python 3.14** (macOS). Use native `bool`/`float` — numpy types break `json.dumps`.
- **venv**: `source venv/bin/activate`. Use `python` not `python3` inside venv.
- **Dependencies**: `anthropic`, `pybit`, `telethon`, `python-dotenv`, `requests`, `pandas`.
- **Secrets**: all in `.env` (gitignored). Never hardcode, never log, never commit.
- **Model**: currently `claude-sonnet-4-6`. Model name is recorded in setup JSONs for comparison.

### Coding Conventions

- Async only where necessary (Telethon). Bybit + Claude calls are synchronous.
- Every external API call must have try/except with clear error message. Pipeline degrades gracefully.
- Always cast pandas/numpy to native Python types before JSON serialization.
- Telegram messages have 4096 char limit — `telegram_bot.py` handles chunking.
- Use compact JSON (`separators=(',',':')`) for data sent to Claude to save tokens.
- Rate limiting: `time.sleep(0.05)` between kline calls, `time.sleep(0.1)` in eval.

### Token Discipline

Current per-run: ~29k input tokens, ~8k output tokens, ~10k thinking tokens (extended thinking).
Extended thinking is enabled — Claude's reasoning goes into a separate thinking block (not sent to Telegram), keeping output clean and focused on the formatted brief.
Before adding data to the Claude call:
- Estimate token impact
- Anything that >2x's current input needs justification
- Prefer pre-filtering in Python (free) over sending raw data to Claude (costs tokens)
- Use compact JSON, not pretty-printed
- New indicators should be token-efficient (e.g., SMA200 only included in 1D data, not all TFs)

---

## Environment Setup

Required `.env` keys:

```
ANTHROPIC_API_KEY=sk-ant-...
BYBIT_API_KEY=...               # Read-Only, IP-whitelisted
BYBIT_API_SECRET=...
TELEGRAM_API_ID=...              # from my.telegram.org (Telethon)
TELEGRAM_API_HASH=...            # from my.telegram.org (Telethon)
TELEGRAM_BOT_TOKEN=...           # from @BotFather (for delivery)
TELEGRAM_CHAT_ID=...             # user's personal chat ID
```

### Network Notes

- **Bybit AND Telegram API are blocked by Indonesian ISPs.** VPN required.
- Bybit API key is region-aware; whitelisted IP must match VPN exit IP.
- `telegram_bot.py` has retry with backoff (3 attempts) for network failures.

---

## How to Run

```bash
# Nightly screener (git pull first to get latest hot list from GitHub Actions)
git pull && source venv/bin/activate && python main.py

# Momentum pulse (runs automatically on GitHub Actions every 4h, but can also run locally)
source venv/bin/activate
python momentum_pulse.py

# Weekly evaluation (run Sundays or whenever)
source venv/bin/activate
python weekly_eval.py

# Quarterly deep analysis (run every ~3 months or after 50+ new trades)
source venv/bin/activate
python quarterly_analysis.py

# Trade logger — manage manual trade journal
python trade_logger.py open      # Pick a setup, enter your entry price
python trade_logger.py close     # Close an open trade, enter exit price
python trade_logger.py list      # Show all trades with summary

# What-if backtester (uses existing eval data, zero tokens)
python backtester.py                    # Full report (all analyses)
python backtester.py --t1-sweep         # T1 distance analysis
python backtester.py --combo            # Best filter combinations
python backtester.py --symbols          # Per-symbol breakdown

# Historical strategy backtester (uses cached Bybit klines, zero tokens)
python historical_backtester.py                              # Default: 6 coins, 1h
python historical_backtester.py --interval 240               # 4h timeframe
python historical_backtester.py --optimize all               # Parameter sweep all signals
python historical_backtester.py --validate all               # Train/test validation
python historical_backtester.py --validate all --interval 240 --symbols ADAUSDT,XRPUSDT,SOLUSDT,BTCUSDT,ETHUSDT,DOGEUSDT,SUIUSDT,XLMUSDT,ENAUSDT,HBARUSDT,TRXUSDT,NEARUSDT,OPUSDT,ARBUSDT,INJUSDT  # Full cross-TF validation
```

**Terminal shortcuts** (defined in `~/.zshrc`):
- `scan` — run nightly screener (includes git pull for latest hot list)
- `pulse` — run momentum pulse locally
- `eval-scan` — run weekly evaluation + delta analysis (auto-triggers every 15 new trades)
- `backtest` — full backtest pipeline: validate signal formulas on 4h + 1h (15 symbols, fresh data) + eval combo analysis
- `trade` — manage manual trade log (`trade open`, `trade close`, `trade list`)
- `quarterly-scan` — quarterly deep analysis (optional — superseded by `backtest` + delta analysis)

**Recommended workflow:**
- **Daily:** `scan` (or let launchd run it at 9pm)
- **Weekly:** `eval-scan` (scores past setups, updates rules, triggers delta analysis)
- **Monthly:** `backtest` (re-validates signal formulas with fresh market data)

### Scheduled Runs

- **Momentum pulse**: GitHub Actions, every 4 hours (`.github/workflows/momentum_pulse.yml`). Zero Claude tokens. Auto-commits hot_list.json back to repo. Secrets stored as GitHub repository secrets.
- **Nightly screener**: macOS `launchd` (`~/Library/LaunchAgents/com.user.cryptoscreener.plist`). Default: 9pm local.
- Do NOT migrate to cron — launchd handles wake-from-sleep better.

---

## Extending the System — Guardrails

1. **Never add write-path Bybit calls** (place_order, cancel_order, etc.). Confirm Phase B preconditions first.
2. **Never let free-text output drive actions.** Use structured JSON (`setups_json`) with validated fields.
3. **New data sources welcome** — wire into `fetchers/`, pass to Claude context. Estimate token impact first.
4. **Prompt changes**: update `analyzer/prompts.py`. Never weaken R:R below 1.5:1 floor, remove risk framework, or make Claude more aggressive about calling trades.
5. **Knowledge files** in `/knowledge/*.md` are user-editable. Keep human-readable. Claude loads all `*.md` files on every run.
6. **Pre-filter scoring** in `bybit_data.py::_ticker_interest_score()` should reflect knowledge file rules. When knowledge changes, update scoring thresholds to match.

### Files That Should NOT Drift Without Discussion

- `analyzer/prompts.py` → risk framework, R:R floor, output format, JSON schema
- `config.py` → model choice, token limits, scan limits, momentum pulse thresholds, regime detection thresholds
- `weekly_eval.py` → evaluation logic, scoring rules, strategic rules generator, simulated T1 backtest
- `bybit_data.py::_ticker_interest_score()` → pre-filter rules tied to knowledge
- `momentum_pulse.py` → momentum detection criteria, hot list expiry, regime detection logic
- `.github/workflows/momentum_pulse.yml` → GitHub Actions schedule, secrets mapping

---

## Known Issues & Gotchas

- **Python 3.14 + numpy bools**: `json.dumps` raises TypeError for `numpy.bool_`. Always wrap in `bool()`. Same for `numpy.float64` → `float()`.
- **Telethon session file**: first run prompts for phone + SMS code, creates `screener_session.session`. Treat as secret (gitignored).
- **Telegram bot token**: if exposed in screenshot/log, revoke via `@BotFather`.
- **Bybit rate limits**: 25 symbols × 4 TFs = 100 kline calls. `time.sleep(0.05)` between calls. If 429s appear, increase delay.
- **Pandas rolling() warmup**: first 13-20 candles return NaN for RSI and vol spike. Code guards with `pd.notna()` — preserve on edits.
- **Output truncation**: with extended thinking, reasoning uses its own budget (`THINKING_BUDGET=10000`) separate from text output (`MAX_TOKENS_OUTPUT=8000`). The old issue of pre-analysis notes eating all output tokens is resolved. If the brief still truncates, increase `MAX_TOKENS_OUTPUT`.
- **Prompt caching**: TTL is ~5 minutes. Once-nightly runs always have cold cache. Caching only helps during testing/debugging bursts.
- **SMA200 warmup**: SMA(200) requires 200 candles. Only the 1D timeframe fetches 210 candles — SMA200 is NaN (omitted from output) on 15m/1h/4h. This is intentional to save tokens.

---

## The Evaluation System

`weekly_eval.py` is the feedback loop that makes this system improve over time:

1. Reads `logs/setups/*.json` (each has: symbol, entry, stop, targets, confidence, model)
2. Waits appropriate time: scalp=1d, intraday=2d (swing removed in v9.2 — system only recommends scalp/intraday)
3. Fetches 15m klines from Bybit for the evaluation window
4. Checks: entry triggered? → stop or target hit first? → actual R:R
5. **Breakeven stop model**: once T1 is hit, the simulated stop moves to entry (breakeven). If price reverses after T1, worst case is 0R, not -1.0R.
6. **Partial profit model**: calculates `blended_rr` = 50% closed at T1 + 50% trails with BE stop to T2/expiry. This models realistic position management.
7. **Simulated closer-T1 backtest**: also checks if T1 at 0.75R and 1.0R would have been hit before stop
8. Saves to `logs/evaluations/eval_*.json` (includes `blended_rr`, `be_stop_hit`, `sim_t1_*` fields)
9. Updates tiered knowledge distillation (see below)
10. `build_system_prompt()` loads strategic_rules + recent_performance → Claude reads on next run

### Tiered Knowledge Distillation

Instead of sending all historical data to Claude every run (which would grow unboundedly), the system distills evaluation data into three layers:

| Layer | File | Sent to Claude? | Size | Scales with time? |
|---|---|---|---|---|
| 1. Lifetime Stats | `lifetime_stats.json` | No (backing data) | Grows slowly | Yes but compact |
| 2. Strategic Rules | `strategic_rules.md` | **Yes** | ~600-800 tokens | **No** — fixed size |
| 3. Recent Performance | `recent_performance.md` | **Yes** | ~800 tokens | **No** — rolling 4-week window |
| Human Report | `summary.md` | No | ~2K tokens | Yes |

**Layer 1** (`lifetime_stats.json`): Incrementally updated running counters — win rate by setup type, confidence, rank, model, timeframe, direction, **symbol**, **regime**, **rule_applied**, monthly trends, prediction gap, MFE stats, **simulated T1 results**. Updated O(1) per new eval (no need to re-read old eval files).

**Layer 2** (`strategic_rules.md`): **Prescriptive** rules derived from Layer 1. Each rule includes an "ACTION:" line telling Claude exactly what to do. Examples:
- "CONFIDENCE MISCALIBRATED: High is 22% but Medium is 43%. ACTION: Only label 'high' if 4/4 TF confluence + volume."
- "TARGETS TOO FAR: avg MFE is 1.3R. Backtest: T1 at 0.75R hits 65% vs current 28%. ACTION: Set T1 at max 1.0R."
- "WINNING SYMBOLS: DOGEUSDT (4/6). ACTION: Give priority when in scan."
- "CAUTIOUS REGIME LOSING: 3/20 (15% WR). ACTION: During cautious, reduce to max 1-2 setups."
- "EFFECTIVE RULES: ada_priority (5/8=63%). ACTION: Continue applying — correlates with wins."

Rules cover: selectivity, confidence calibration, timeframe/direction performance, setup types, rank anomalies, T1 placement (MFE-based), per-symbol patterns, stop timing, model comparison, directional blind spots, **per-regime performance**, **rule-applied effectiveness**.

**Direction rule safeguard**: "Avoid direction" rules require 15+ trades (`DIRECTION_RULE_MIN_TRADES`) before becoming hard rules. With fewer trades, the rule says "NEEDS DATA" instead of "avoid" — this prevents a self-reinforcing feedback loop where a direction (e.g., shorts) gets permanently blocked by a statistically insignificant sample size.

**Layer 3** (`recent_performance.md`): Rolling 4-week window of individual trade outcomes. Gives Claude fresh context about what's working NOW without unbounded growth. Old trades fall off automatically.

**Total prompt overhead**: ~1500-1800 tokens regardless of whether you've run for 1 month or 3 years.

### Self-Learning System (Delta Analysis)

The system automatically improves through a multi-layered feedback loop that does NOT require manual trading. The `scan` → `eval-scan` cycle is sufficient — the eval checks Claude's recommendations against actual price data.

**Delta analysis** (`weekly_eval.py::maybe_run_delta_analysis()`) replaces the slow quarterly cadence:
- **Trigger**: auto-runs after every `eval-scan` when 15+ new evaluated trades have accumulated (`DELTA_ANALYSIS_TRADE_THRESHOLD` in config)
- **What it does**: calls Claude to find patterns in recent performance changes, grade previous insights, and generate new ACTION rules
- **Previous insight grading**: each prior insight is graded EFFECTIVE (→ `confirmed`), INEFFECTIVE (→ `expired`/removed), or INCONCLUSIVE (→ stays `experimental`)
- **Output**: 2-5 new insights in ACTION format, appended to `strategic_rules.md` under `## Delta Insights`
- **Rule lifecycle**: `experimental` (new, use as guidance) → `confirmed` (graded effective, follow strictly) → `expired` (graded ineffective, removed from rules)
- **Registry**: `logs/performance/rule_registry.json` tracks insight history, win rate snapshots, and grading results
- **Cost**: ~10-15k input + ~1.5k output tokens per delta analysis (far less than nightly scan)

**Reasoning capture** (in setup JSON):
- Each setup includes a `reasoning` field: `rules_applied` (list of rule IDs that influenced the setup) + `key_factor` (one-line primary driver)
- Carried through to eval results → tracked in `lifetime_stats.json::by_rule_applied`
- Enables **rule-level attribution**: "When Claude cited `ada_priority`, did those setups win more?"
- `generate_strategic_rules()` surfaces effective and ineffective rules in the prompt

**Regime tagging** (in setup + eval records):
- Market regime (`risk_off`/`cautious`/`neutral`/`risk_on`) is saved in both setup and eval records
- Tracked in `lifetime_stats.json::by_regime`
- `generate_strategic_rules()` surfaces per-regime win rates — enables regime-specific learning

**Post-scan validation** (`main.py::validate_setups()`):
- Pure Python (zero tokens) — runs after Claude's output is parsed, before saving
- Checks: setup count vs regime limit, valid types/directions/timeframes, predicted_rr cap, duplicates, direction requirements
- Violations are logged as warnings — does NOT block saving (so eval can still track the outcome)

### Quarterly Deep Analysis (Manual)

`quarterly_analysis.py` is still available for manual deep analysis:
- Run via `quarterly-scan` terminal command
- More thorough than delta analysis (uses larger context, deeper prompt)
- Useful for periodic deep-dives after 50+ new trades
- Findings append to `strategic_rules.md` (may be overwritten by next delta analysis)

### Model Comparison

Every setup JSON includes `"model": "claude-sonnet-4-6"` (or whichever was used). The eval tracks win rate and avg R:R per model in `lifetime_stats.json`. When enough data accumulates (5+ trades per model), the strategic rules include a model comparison.

---

## Project Tracking

See `progress.md` for:
- Full changelog of all improvements
- Current cost estimation (monthly)
- Performance data (once eval runs)
- Backlog of planned features
- Phase B prerequisites checklist

---

## Glossary

- **Brief**: the structured output Claude produces per run (Market Context, Top 5 Opportunities, Risk Flags, Takeaway).
- **Setup**: a trading opportunity with entry zone, stop, target 1+2, R:R, and confidence. Must have R:R >= 1.5:1.
- **setups_json**: structured JSON block Claude appends to every brief for machine-readable tracking.
- **Pre-filter**: Python scoring of 50 tickers down to 25 before kline fetching, using knowledge-derived rules.
- **Multi-TF confluence**: how many of 4 timeframes agree on direction. 4/4=High, 3/4=Medium, 2/4=Low.
- **Watchlist**: symbols always analyzed regardless of pre-filter score (BTC, ETH, SOL).
- **Phase A / Phase B**: analyst-only (current) vs. auto-execution (future, requires preconditions).
- **Interest score**: numeric score from `_ticker_interest_score()` used to rank 50 tickers for pre-filtering.
- **MFE (Max Favorable Excursion)**: how far price moved in Claude's predicted direction before outcome. Used to diagnose "direction right, execution wrong" and compute optimal T1 distance.
- **Simulated T1 backtest**: per-trade check of whether a closer T1 (at 0.75R or 1.0R) would have been hit before stop. Aggregated to quantify optimal T1 distance.
- **Blended R:R**: the partial profit model result. 50% of position closed at T1, remaining 50% trails with breakeven stop. Calculated as `0.5 * T1_rr + 0.5 * actual_rr`. More realistic than all-or-nothing scoring.
- **BE stop (breakeven stop)**: after T1 is hit in the eval, the stop moves to entry price. If price reverses, the worst case is 0R instead of -1.0R. Tracked as `be_stop_hit` in eval results.
- **Momentum pulse**: lightweight scanner (`momentum_pulse.py`) that runs every 4h on GitHub Actions. Fetches 50 tickers, compares against previous snapshot to detect volume/price acceleration. Zero Claude tokens. Flags coins to `logs/momentum/hot_list.json`.
- **Hot list**: dynamic watchlist generated by the momentum pulse. Coins flagged for big moves, volume acceleration, or funding squeezes. Entries expire after 48h. Main scan merges hot list into watchlist automatically.
- **Volume acceleration**: ratio of a coin's current turnover vs its turnover at the previous pulse (4h earlier). >3x triggers a flag. >2x gives a scoring bonus in the pre-filter. Detects coins that are ramping up before they appear in the top 50 by absolute turnover.
- **Market regime**: overall market classification detected by the momentum pulse from 50-ticker aggregate data. Four states: `risk_off` (broad sell-off, favor shorts, max 2 setups), `cautious` (soft bearish, max 3 setups, require volume/4TF for longs), `neutral` (no directional bias, max 3 setups), `risk_on` (broad rally, favor longs, max 5 setups). Saved in `hot_list.json` and always injected into Claude's user content with metrics.
- **Risk off / Cautious / Risk on**: market regime labels. `risk_off` = bearish (≥70% declining or BTC ≤ -4%), max 2 setups. `cautious` = soft bearish (≥55% declining or BTC ≤ -2%), max 3 setups, longs need volume OR 4/4 TF. `risk_on` = bullish (≤30% declining or BTC ≥ +4%), favor longs.
- **Losing streak circuit breaker**: `_detect_losing_streak()` in `claude_client.py` counts consecutive stop losses from recent evals. 5+ SLs → LOSING STREAK ALERT (max 2 setups, require volume/4TF). 3-4 SLs → CAUTION (max 3 setups). Also tracks total recent losses: 15+/20 → SEVERE DROUGHT (max 1-2 setups, prefer range setups). 12+/20 → HIGH LOSS RATE (max 2-3 setups).
- **ADX (Average Directional Index)**: trend strength indicator computed per timeframe. ADX < 20 = ranging/choppy (trend_pullback WILL fail), 20-25 = weak trend, > 25 = trending. Used by Claude to choose between trend-following and range-based setups.
- **range_pct**: 20-candle high-low range as % of price, computed per timeframe. < 5% on 4h = tight consolidation, 5-10% = standard range, > 10% = wide/volatile. Helps Claude gauge range width for target placement.
- **Range mean reversion**: setup type for fading range extremes. Short near 20-candle high with RSI > 65, long near 20-candle low with RSI < 35. Target = range midpoint. Quick 4-8h hold. Only valid when ADX < 20.
- **BTC Daily Trend Guard**: injected into Claude's user content when BTC daily trend is extracted. When BTC is bearish with RSI < 40, correlated alt longs are flagged as HIGH RISK. Only decoupled alts (moving opposite to BTC) are valid longs.
- **Dead cat bounce**: a brief recovery bounce during a larger downtrend that gets sold into. Detected when daily RSI was sub-35 within last 3 candles. Must be labeled as "recovery_bounce" with LOW confidence, NOT as "trend_pullback" with medium confidence.
- **ATH/ATL Exhaustion Reversal (Setup 8)**: mean reversion short at ATH (or long at ATL) when multi-TF RSI is overbought/oversold + rejection candle confirms the turn. Target: golden pocket (0.618 fib). Requires multi-TF confirmation — not just "it went up a lot."
- **Golden pocket (0.618 Fibonacci)**: the 61.8% Fibonacci retracement level — highest-probability reversal zone. Used as T1 for Setup 8 (ATH Exhaustion) and as entry zone for trend pullback setups. Measured from the swing low that started the move to the swing high where it ended.
- **Fibonacci retracement**: a framework for identifying key pullback/target levels. Levels: 0.382 (shallow), 0.5 (midpoint), 0.618 (golden pocket), 0.786 (deep). Defined in `03_market_structure.md` under S&R. Self-fulfilling in crypto due to wide adoption.
- **Effective limit**: the resolved maximum number of setups per run, computed as `min(regime_max, streak_max, loss_rate_max)`. Injected into Claude's user content as a single non-negotiable number. Removes ambiguity when multiple constraints overlap (e.g., risk_off says max 2, losing streak says max 3 → effective limit is 2).
- **Extended thinking**: Anthropic API feature enabled in `claude_client.py`. Claude's reasoning (pre-analysis, candidate scanning, rule checking) goes into a separate `thinking` block with its own token budget (`THINKING_BUDGET`). Only the formatted brief text is extracted and sent to Telegram. This prevents reasoning from consuming output tokens and keeps Telegram messages clean.
- **MACD (Moving Average Convergence Divergence)**: momentum indicator computed per timeframe. `macd` = EMA(12) - EMA(26), measures momentum direction (>0 bullish, <0 bearish). `macd_hist` = MACD - signal(EMA9 of MACD), measures momentum acceleration (>0 accelerating, <0 decelerating). Sign flip = momentum shift. Used to confirm trend entries and spot divergences.
- **Divergence (regular)**: price makes a new extreme (higher high or lower low) but RSI/MACD does NOT confirm it. Regular bearish: price higher high + indicator lower high = momentum weakening, reversal warning. Regular bullish: price lower low + indicator higher low = selling exhausting, reversal potential. Detected programmatically from swing points (order=3, lookback=40 candles). Labels: `rsi_bear`, `rsi_bull`, `macd_bear`, `macd_bull`.
- **Divergence (hidden)**: opposite of regular — the indicator makes a new extreme but price does NOT. Hidden bullish: price higher low + indicator lower low = uptrend continuation signal. Hidden bearish: price lower high + indicator higher high = downtrend continuation signal. Labels: `rsi_h_bull`, `rsi_h_bear`, `macd_h_bull`, `macd_h_bear`.
- **SMA200 (200-period Simple Moving Average)**: long-term trend filter computed on 1D only (requires 200+ candles). Price above SMA200 = macro uptrend, below = macro downtrend. Acts as major dynamic support/resistance. Only present in 1D timeframe data to save tokens (15m/1h/4h fetch too few candles).
- **Delta analysis**: automated self-learning system in `weekly_eval.py`. Triggers every 15 new evaluated trades. Calls Claude to find patterns, grade previous insights, and generate new ACTION rules. Replaces the slow quarterly cadence with faster feedback. Results appended to `strategic_rules.md` under `## Delta Insights`.
- **Rule registry** (`rule_registry.json`): tracks delta analysis insights — when they were added, their status (`experimental`/`confirmed`/`expired`), and win rate snapshots. Enables insight effectiveness tracking over time.
- **Reasoning capture**: `reasoning` field in setup JSON containing `rules_applied` (list of rule IDs) and `key_factor` (one-line driver). Carried through to eval results, tracked in `by_rule_applied` stats. Enables rule-level attribution — "did setups citing this rule win more?"
- **Post-scan validation**: pure Python validator in `main.py` that checks Claude's output against hard rules (setup count, predicted_rr cap, valid types, regime requirements). Zero token cost. Logs violations as warnings.
- **Validated signals**: mechanical signal formulas that passed out-of-sample train/test validation on 15 symbols. Detected by `_check_validated_signals()` in `bybit_data.py` during each scan. When they fire, injected into Claude's user content as `BACKTESTED SIGNALS` section. Current confirmed signals (Jul 2026 re-validation): `rsi_rejection_short` (RSI exhaustion at >75, ★ STRONG both TFs), `macd_momentum_long` (MACD hist flip positive in uptrend, confirmed both TFs), `trend_pullback_short` (downtrend pullback to EMA20, **4h ONLY** — 1h rejected as overfit). `macd_momentum_short` was removed after degrading to overfit on both TFs. Other signals (trend_pullback_long, range_reversion_long/short, rsi_bounce_long) remain rejected/single-TF-only. The set is re-checked monthly via `backtest`; when a signal drifts, `_check_validated_signals()` is manually updated to match.
- **Historical backtester** (`historical_backtester.py`): fetches Bybit klines (cached locally), defines 12 mechanical signal rules, runs parameter sweep optimization (`--optimize`), and validates with train/test split (`--validate`). Tests on 1h (42 days) and 4h (167 days) of data. Zero Claude tokens.
- **What-if backtester** (`backtester.py`): reads existing eval/setup logs, sweeps parameters (T1 distance, filters, regime limits, symbol blacklists), reports expectancy/WR/profit factor. Useful for answering "what if we changed X?" Zero Claude tokens.
- **Train/test validation**: splits cached kline data 60/40 — optimizes parameters on train half, evaluates on test (unseen) half. If test expectancy is negative, the formula is overfit and rejected. Prevents integrating patterns that only work in hindsight.
- **Robustness score**: for each top formula, checks if neighboring parameter values (±1 step) also have positive expectancy. High robustness (>50%) means the formula works across a range of conditions, not just one lucky parameterization.
