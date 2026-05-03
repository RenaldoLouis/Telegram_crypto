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
- Do NOT weaken R:R 1:2 minimum floor or remove risk flags from output.

Auto-execution will only be considered after: (a) 60+ days of evaluated Phase A data, (b) a separate hard-coded risk engine (not Claude) for position sizing, (c) model comparison data (Sonnet vs Haiku), and (d) explicit user approval.

---

## Architecture

```
main.py  (orchestrator, async)
  │
  ├── fetchers/bybit_data.py       → BybitFetcher:
  │                                    get_top_movers(50) → single API call
  │                                    _ticker_interest_score() → knowledge-based pre-filter
  │                                    get_multi_tf_indicators() → 15m/1h/4h/1D klines
  │                                    get_full_market_snapshot() → 50 → score → top 25 → multi-TF
  │
  ├── fetchers/telegram_reader.py  → TelegramReader: Telethon (currently disabled)
  │
  ├── analyzer/prompts.py          → SYSTEM_PROMPT + load_knowledge() + performance feedback
  ├── analyzer/claude_client.py    → ClaudeAnalyzer: Anthropic SDK, prompt caching, compact JSON
  │
  ├── delivery/telegram_bot.py     → MD→HTML converter, smart chunking, retry with backoff
  │
  ├── weekly_eval.py               → Evaluation engine: scores past setups, tiered knowledge distillation
  ├── quarterly_analysis.py        → Claude-powered deep pattern analysis (run every ~3 months)
  │
  ├── knowledge/*.md               → 9 trading knowledge files (01–08 + trading_rules)
  └── logs/
        ├── briefs/*.md            → Archived readable briefs
        ├── setups/*.json          → Structured setup JSONs (with model name)
        ├── evaluations/*.json     → Scored results (win/loss, actual R:R)
        └── performance/
              ├── lifetime_stats.json    → Layer 1: Incremental running counters (never re-reads old evals)
              ├── strategic_rules.md     → Layer 2: Compact rules from all history (~500 tokens, sent to Claude)
              ├── recent_performance.md  → Layer 3: Rolling 4-week trade details (~800 tokens, sent to Claude)
              ├── summary.md             → Human-readable report (NOT sent to Claude)
              ├── win_rate_history.json   → Win rate snapshots over time
              └── quarterly/             → Deep analysis logs from quarterly_analysis.py
```

### Data Flow

1. `BybitFetcher.get_top_movers(50)` → 50 tickers by turnover (single API call)
2. `_ticker_interest_score()` → disqualify illiquid (<$10M vol, <$50M OI), score rest
3. Keep top 25 by score + watchlist → `get_multi_tf_indicators()` for each (4 TFs × 25 = 100 kline calls)
4. `ClaudeAnalyzer.analyze(market, messages)` → readable brief + `setups_json` block
5. `main.py` parses JSON block → saves to `logs/setups/` (includes model name)
6. Clean brief (JSON stripped) → archived to `logs/briefs/` + delivered via Telegram
7. Weekly: `weekly_eval.py` scores past setups → updates tiered knowledge:
   - `lifetime_stats.json` — incremental counters (O(1) per new eval, no file re-reads)
   - `strategic_rules.md` — compact algorithmic rules from lifetime stats (~500 tokens)
   - `recent_performance.md` — rolling 4-week trade details (~800 tokens)
   - `summary.md` — full human-readable report (NOT sent to Claude)
8. Next run: `build_system_prompt()` loads strategic_rules + recent_performance → Claude self-calibrates
9. Quarterly: `quarterly_analysis.py` uses Claude to find deep patterns → appends to strategic_rules.md

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

Current per-run: ~28k tokens (~20k input, ~8k output). Before adding data to the Claude call:
- Estimate token impact
- Anything that >2x's current input needs justification
- Prefer pre-filtering in Python (free) over sending raw data to Claude (costs tokens)
- Use compact JSON, not pretty-printed

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
# Nightly screener
source venv/bin/activate
python main.py

# Weekly evaluation (run Sundays or whenever)
source venv/bin/activate
python weekly_eval.py

# Quarterly deep analysis (run every ~3 months or after 50+ new trades)
source venv/bin/activate
python quarterly_analysis.py
```

### Scheduled Runs

macOS: `launchd` (`~/Library/LaunchAgents/com.user.cryptoscreener.plist`). Default: 9pm local.
Do NOT migrate to cron — launchd handles wake-from-sleep better.

---

## Extending the System — Guardrails

1. **Never add write-path Bybit calls** (place_order, cancel_order, etc.). Confirm Phase B preconditions first.
2. **Never let free-text output drive actions.** Use structured JSON (`setups_json`) with validated fields.
3. **New data sources welcome** — wire into `fetchers/`, pass to Claude context. Estimate token impact first.
4. **Prompt changes**: update `analyzer/prompts.py`. Never weaken R:R floor, remove risk framework, or make Claude more aggressive about calling trades.
5. **Knowledge files** in `/knowledge/*.md` are user-editable. Keep human-readable. Claude loads all `*.md` files on every run.
6. **Pre-filter scoring** in `bybit_data.py::_ticker_interest_score()` should reflect knowledge file rules. When knowledge changes, update scoring thresholds to match.

### Files That Should NOT Drift Without Discussion

- `analyzer/prompts.py` → risk framework, R:R floor, output format, JSON schema
- `config.py` → model choice, token limits, scan limits
- `weekly_eval.py` → evaluation logic, scoring rules
- `bybit_data.py::_ticker_interest_score()` → pre-filter rules tied to knowledge

---

## Known Issues & Gotchas

- **Python 3.14 + numpy bools**: `json.dumps` raises TypeError for `numpy.bool_`. Always wrap in `bool()`. Same for `numpy.float64` → `float()`.
- **Telethon session file**: first run prompts for phone + SMS code, creates `screener_session.session`. Treat as secret (gitignored).
- **Telegram bot token**: if exposed in screenshot/log, revoke via `@BotFather`.
- **Bybit rate limits**: 25 symbols × 4 TFs = 100 kline calls. `time.sleep(0.05)` between calls. If 429s appear, increase delay.
- **Pandas rolling() warmup**: first 13-20 candles return NaN for RSI and vol spike. Code guards with `pd.notna()` — preserve on edits.
- **Output truncation**: if `MAX_TOKENS_OUTPUT` is too low, the `setups_json` block gets cut off. Currently 8000 — sufficient for 5 setups + JSON. If output format grows, increase this.
- **Prompt caching**: TTL is ~5 minutes. Once-nightly runs always have cold cache. Caching only helps during testing/debugging bursts.

---

## The Evaluation System

`weekly_eval.py` is the feedback loop that makes this system improve over time:

1. Reads `logs/setups/*.json` (each has: symbol, entry, stop, targets, confidence, model)
2. Waits appropriate time: scalp=1d, intraday=2d, swing=7d
3. Fetches 15m klines from Bybit for the evaluation window
4. Checks: entry triggered? → stop or target hit first? → actual R:R
5. Saves to `logs/evaluations/eval_*.json`
6. Updates tiered knowledge distillation (see below)
7. `build_system_prompt()` loads strategic_rules + recent_performance → Claude reads on next run

### Tiered Knowledge Distillation

Instead of sending all historical data to Claude every run (which would grow unboundedly), the system distills evaluation data into three layers:

| Layer | File | Sent to Claude? | Size | Scales with time? |
|---|---|---|---|---|
| 1. Lifetime Stats | `lifetime_stats.json` | No (backing data) | Grows slowly | Yes but compact |
| 2. Strategic Rules | `strategic_rules.md` | **Yes** | ~500 tokens | **No** — fixed size |
| 3. Recent Performance | `recent_performance.md` | **Yes** | ~800 tokens | **No** — rolling 4-week window |
| Human Report | `summary.md` | No | ~2K tokens | Yes |

**Layer 1** (`lifetime_stats.json`): Incrementally updated running counters — win rate by setup type, confidence, rank, model, timeframe, direction, monthly trends, prediction gap, MFE stats. Updated O(1) per new eval (no need to re-read old eval files).

**Layer 2** (`strategic_rules.md`): Compact, durable rules derived algorithmically from Layer 1. Examples: "medium confidence has 0% WR — ban unless R:R >= 3:1", "targets are 2.7R too optimistic — use closer T1". Regenerated weekly but only changes when stats shift meaningfully.

**Layer 3** (`recent_performance.md`): Rolling 4-week window of individual trade outcomes. Gives Claude fresh context about what's working NOW without unbounded growth. Old trades fall off automatically.

**Total prompt overhead**: ~1300 tokens regardless of whether you've run for 1 month or 3 years.

### Quarterly Deep Analysis

`quarterly_analysis.py` uses Claude to find non-obvious patterns that algorithms can't detect:
- Temporal patterns (certain days/times perform better)
- Setup interaction effects (type + confidence + timeframe combos)
- Symbol-specific patterns (consistently winning/losing symbols)
- Sequence effects (overconfidence after wins, selectivity after losses)

Run manually every ~3 months or after 50+ new evaluated trades. Findings are appended to `strategic_rules.md` under a "Quarterly Deep Insights" section.

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
- **Setup**: a trading opportunity with entry zone, stop, target 1+2, R:R, and confidence. Must have R:R >= 1:2.
- **setups_json**: structured JSON block Claude appends to every brief for machine-readable tracking.
- **Pre-filter**: Python scoring of 50 tickers down to 25 before kline fetching, using knowledge-derived rules.
- **Multi-TF confluence**: how many of 4 timeframes agree on direction. 4/4=High, 3/4=Medium, 2/4=Low.
- **Watchlist**: symbols always analyzed regardless of pre-filter score (BTC, ETH, SOL).
- **Phase A / Phase B**: analyst-only (current) vs. auto-execution (future, requires preconditions).
- **Interest score**: numeric score from `_ticker_interest_score()` used to rank 50 tickers for pre-filtering.
