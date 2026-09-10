# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**crypto-screener** is a personal, scheduled screener for Bybit USDT perpetual futures. It scans 100 coins, pre-filters to 30 using knowledge-based scoring, builds setups across 4 timeframes with a pure-Python **mechanical engine** (zero Claude tokens — the project makes NO Claude API calls as of 2026-09-10), delivers the best validated setups (typically 0–2 EXECUTE per run, plus a WATCH candidate when the EXECUTE lane is empty) to Telegram, and self-evaluates past recommendations against actual price data.

## 🎯 Project Goal (NORTH STAR — every recommendation must serve this)

_Defined 2026-08-09. This is the single anchor. Before proposing any change, research, or feature, check it against this section: does it move us toward THE goal, measured THE one way, without violating a non-goal or the operating discipline? If not, don't propose it._

**THE GOAL:** a **proven, owned, fully-mechanical trading edge** for Bybit USDT perps that **eventually trades itself**. Emotion-free — every decision comes from our own Python calculation, never from gut and never from a hosted model. Phase A (analyst; human executes manually) exists to *prove the edge*; Phase B (auto-execution) is the payoff, unlocked ONLY after the edge is proven **and** a separate hardcoded risk engine exists **and** the user explicitly approves.

**THE ONE SUCCESS METRIC — net-of-cost expectancy (R per trade).** Not win rate, not gross R, not lifetime totals (the 2026-08-02 audit proved those are vanity/cost-illusion). **"Edge proven" = net-of-cost expectancy ≥ +0.05R sustained over ≥100 forward-evaluated trades, with BOTH directions and >1 signal contributing** (so it's a broad edge, not one lucky signal). That threshold is the line that flips the project from *searching* → *found it* + is the precondition to even discuss Phase B. (Note: the v12.0 *source* flip to mechanical-primary already happened 2026-08-26 on a philosophical basis — own the edge, stop paying for a shadow — and is NOT gated on this metric; this metric gates "edge proven", which is still unmet.)

**CURRENT STATE (updated 2026-09-10): still SEARCHING.** Best source is net −0.056R (mechanical, n=45, short-only); every source is net-negative. Improvement so far came by *subtraction* (cutting losers), which asymptotes at breakeven. 7 experiments (price signals ×4, OI proxy, structure/S-R filters) found no net edge → conclusion: price-pattern engineering is a dead end on this universe. The one live bet is **fork A: liquidation-cluster data** — first backtest 2026-09-10: promotion bar NOT met, but the 0.5–1.5-ATR near-ring is the strongest relative lead yet (near-ring longs +0.396R net / 62% WR, n=26, underpowered); one data-quality extension granted → **re-run ~2026-10-08**, and if the bar fails again → fork C, no second extension. If it ends empty, the honest end state is a rigorous **analyst tool** — an acceptable, explicit outcome, not a failure to paper over.

**OPERATING DISCIPLINE (how we pursue the goal — non-negotiable):**
1. **Optimize NET-of-cost expectancy only.** Never chase win rate or gross R.
2. **Prove before ship.** Every signal/feature must pass out-of-sample train/test (+ walk-forward where possible) on real data before it touches live. In-sample-only results are rejected on principle.
3. **Subtraction has a ceiling.** Cutting losers reaches ~breakeven, never profit. Real edge requires a *predictive* input, not another gate.
4. **Claude is never the decision-maker** (see CORE PRINCIPLE below). The edge lives in our Python.
5. **Honesty over hope.** Report negative results plainly; a proven "no edge" is a valid, valuable answer. No tuning a losing signal into fake positivity.
6. **Always an opinion, never a forced execution (EXECUTE vs WATCH — reframed 2026-08-20).** Every scan must surface at least the single best-ranked candidate — the system is never silent. But it is surfaced in one of two TIERS: **EXECUTE** (passed the validated net-of-cost bar → the real, counted edge book) or **WATCH** (best-available but below the bar → paper-track only, EXCLUDED from the edge book via `source="watch"`). **An empty EXECUTION is valid; an empty SURFACING is a bug.** We never force a *trade* (that re-adds the net-negative noise the 08-02 audit cut), but we never go blind either. WATCH exists to (a) guarantee a daily opinion and (b) *multiply eval velocity* — WATCH candidates are scored too, so the ≥100-forward-trade edge-proof clock moves faster — without ever corrupting the one metric. Rule 1 still governs what counts as edge: WATCH data never enters the expectancy/version/edge-proven aggregations.

**NON-GOALS (things that do NOT serve the goal — see also the Non-Goals list below):** vanity metrics; auto-execution before the edge bar + risk engine + approval; Claude as core decider; shipping unvalidated ideas; more price-pattern signal tuning (proven dead end 2026-08-09).

### Current Phase

**Phase A — Analyst mode (signal-only, NOT auto-trading).**
Claude analyzes data and surfaces setups. The human makes every trading decision and executes every order manually. Phase B (auto-execution) is explicitly out of scope until Phase A has shown measurable edge.

### Setup Source — Mechanical-Primary (v12.0, migration COMPLETE 2026-08-26)

The system runs on a pure-Python **mechanical engine** (`mechanical_setups.py` + `signal_levels.py`) as the ONLY setup source. **`config.PRIMARY_SOURCE = "mechanical"`** (flipped 2026-08-26, commit `8488cf7`). `main.py::run_screener` builds mechanical setups and **gates the Claude shadow call behind `PRIMARY_SOURCE=="claude"`**, so `analyzer.analyze()` is **never invoked on the scan path** (CI or local) → **zero scan Claude tokens everywhere**. Claude no longer touches the decision path at all. **As of 2026-09-10 the project makes ZERO Claude API calls anywhere** — delta analysis (the last remaining call) is retired under the zero-Claude policy (`config.DELTA_ANALYSIS_ENABLED=False`); the learning loop is fully algorithmic (see The Evaluation System). All Claude tooling stays in the repo, dormant and reversible: set `PRIMARY_SOURCE="claude"` to re-enable the shadow, flip `DELTA_ANALYSIS_ENABLED=True` to re-enable delta analysis.

**Head-to-head shadow experiment RETIRED.** It was decided vestigial: the real edge bar is **+0.05R net-of-cost**, not "beat Claude", so the mechanical-vs-Claude comparison was never load-bearing. `weekly_eval.py::generate_head_to_head()` still runs but the `claude` lane simply stops accruing new trades (history preserved). The original Phase-4 flip gate ("mechanical ≥ Claude over ≥20 trades each") was **bypassed deliberately by user decision** — the flip was philosophical (own the edge, stop paying for a non-decision-maker), not a proof that mechanical beats Claude. **Note: the edge itself is still UNPROVEN** — mechanical is net-negative and still searching per the north star; flipping the source does not change that.

**→ For live state, the Phase 5 (ML meta-filter) roadmap, and the data-gated forks (liq clusters, CVD), read `progress.md` § "Current Status & Roadmap (READ FIRST when resuming)" — it is the single source of truth (the original plan file has been retired).**

### Non-Goals (Important)

- Do NOT add order execution logic, even if asked casually.
- Do NOT wire Claude output directly to the Bybit write API.
- Do NOT expand the Bybit API key permissions beyond Read-Only.
- Do NOT weaken the 1.5:1 minimum R:R floor or remove risk flags from output. **The 1.5:1 floor lives on target_2 (the reward leg), NOT target_1.** T1 is a partial-profit level at 0.75–1.0R; T2 must be ≥1.5R. (History: floor lowered 2:1→1.5:1, then in v11.2 relocated from T1 to T2 based on a 237-trade backtest — avg MFE only 1.03R, so a 1.5R T1 was unreachable and setting T1 at 0.75R flipped the book from −24.8R to +5.2R. `main.py::setup_violations` flags T1 ≤ 1.0R AND T2 ≥ 1.5R and `enforce_setups` drops violators.)

### CORE PRINCIPLE — Claude is NEVER the trading decision-maker

**The trading edge MUST live in our own deterministic Python logic (`mechanical_setups.py`, `signal_levels.py`, validated signals, the enforcement gates). Claude is a HELPER at the edges — never the core that decides which trade to take, its direction, entry, stop, or targets.** This is a hard architectural rule, not a preference:

- **We cannot gauge or control Claude's output.** It's a hosted model — Anthropic can change, degrade, or deprecate it at any time, and its responses vary run-to-run. An edge we cannot measure, reproduce, or own is not an edge.
- **It is costly.** Every core decision routed through Claude is recurring token spend for something our own logic should do for free.
- **Therefore:** the decision path (selection, direction, price levels, risk) is ALWAYS Python. Claude may assist only in bounded, non-core, fully-optional roles (e.g. a shadow comparison, a veto/sanity layer on top of a mechanical setup, prose summarization, pattern research) — and the pipeline MUST degrade gracefully to mechanical-only if Claude is absent. A Claude failure must never change or block a trade decision. This is why `PRIMARY_SOURCE = "mechanical"` (migration complete 2026-08-26) and the scan Claude call is gated off entirely — and as of **2026-09-10 Claude has ZERO live role anywhere** (delta analysis retired under the zero-Claude policy; the bounded helper roles above remain permitted-but-dormant). Any new feature that would make Claude the primary generator of a trade decision is out of scope.

Auto-execution will only be considered after: (a) 60+ days of evaluated Phase A data, (b) a separate hard-coded risk engine (not Claude) for position sizing, (c) model comparison data (Sonnet vs Haiku), and (d) explicit user approval.

---

## Architecture

```
main.py  (orchestrator, async)
  │
  ├── fetchers/bybit_data.py       → BybitFetcher:
  │                                    get_top_movers(100) → single API call
  │                                    _ticker_interest_score() → knowledge-based pre-filter + hot list bonus
  │                                    _load_hot_list() → reads momentum pulse hot list
  │                                    get_multi_tf_indicators() → 15m/1h/4h/1D klines + validated signal check
  │                                    _compute_indicators() → RSI, EMA20/50, ATR, ADX, MACD, SMA200 (1D only), divergences
  │                                    _check_validated_signals() → 3 backtest-validated formulas (2 cross-TF, 1 4h-only)
  │                                    get_full_market_snapshot() → 100 → score → top 30 + hot list → multi-TF
  │
  ├── fetchers/telegram_reader.py  → TelegramReader: Telethon (currently disabled)
  │
  ├── mechanical_setups.py         → Mechanical setup constructor (the PRIMARY source): fired validated
  │                                    signals → full setups (entry/stop/T1/T2, deterministic rank/confidence)
  ├── signal_levels.py             → Shared pure entry/stop/target math (drift-guarded vs backtester)
  │
  ├── analyzer/prompts.py          → (DORMANT — zero-Claude policy 2026-09-10; used only if PRIMARY_SOURCE="claude")
  │                                    SYSTEM_PROMPT + load_knowledge() + performance feedback + regime awareness
  ├── analyzer/claude_client.py    → (DORMANT) ClaudeAnalyzer: Anthropic SDK, prompt caching, extended thinking,
  │                                    compact JSON, regime injection + explicit regime limits,
  │                                    effective limit computation, BTC daily trend guard,
  │                                    losing streak detection, recent loss rate injection
  │
  ├── delivery/telegram_bot.py     → MD→HTML converter, smart chunking, retry with backoff
  │
  ├── momentum_pulse.py            → Lightweight momentum detector (runs every 2h on GitHub Actions)
  │                                    Fetches 50 tickers, detects acceleration vs previous snapshot,
  │                                    flags coins to hot_list.json, sends Telegram alert. Zero Claude tokens.
  │                                    detect_market_regime() → classifies market as risk_off/cautious/neutral/risk_on
  │                                    Sends regime change alerts to Telegram. Regime saved in hot_list.json.
  │
  ├── weekly_eval.py               → Evaluation engine: scores past setups, tiered knowledge distillation,
  │                                    simulated T1 backtest, per-symbol tracking, prescriptive rules
  ├── quarterly_analysis.py        → (RETIRED 2026-09-10 — zero-Claude policy; calls the Claude API, do not run)
  ├── trade_logger.py              → CLI tool for managing my_trades.json (open/close/list trades)
  │
  ├── backtester.py                → What-if backtester: sweeps T1/filters/regime limits across eval logs
  ├── historical_backtester.py     → Historical strategy backtester: 18 signal rules, parameter optimizer,
  │                                    train/test validation, robustness scoring. Caches Bybit klines locally.
  │                                    validated formulas integrated into live screener pipeline (re-validated monthly).
  │
  ├── liquidation_collector.py     → Fork A: Bybit liquidation-WS forward-collector (CI chained + local daemon;
  │                                    stall-watchdog rebuilds the socket after 45 min of silence)
  ├── cvd_collector.py             → Roadmap #4 Phase 2: per-minute Bybit taker-flow collector (CI chained; watchdog)
  ├── liq_cluster_backtest.py      → Fork A harness: distance-to-liq-cluster vs outcome, chrono train/test
  ├── liq_cluster_deep_dive.py     → Fork A robustness slices (per-symbol/direction/month/coverage/alt splits)
  ├── cvd_backtest.py              → CVD/order-flow research on free Binance history (found the cvd_slope lead)
  │
  ├── knowledge/*.md               → 9 trading knowledge files (01–08 + trading_rules)
  └── logs/
        ├── briefs/*.md            → Archived readable briefs
        ├── setups/*.json          → Structured setup JSONs (with model name)
        ├── evaluations/*.json     → Scored results (win/loss, actual R:R, MFE, simulated T1)
        ├── momentum/
        │     ├── hot_list.json    → Active momentum-flagged coins + market regime (dynamic watchlist)
        │     └── last_snapshot.json → Previous pulse data + regime (for delta detection)
        ├── liquidations/          → Raw liq prints, gitignored (daemon monthly files; ci/ = merged canonical store)
        ├── cvd/                   → Per-minute taker buckets, gitignored (CI artifacts are the store)
        ├── performance/
        │     ├── lifetime_stats.json    → Layer 1: Incremental running counters (incl. by_symbol, simulated_t1)
        │     ├── strategic_rules.md     → Layer 2: Algorithmic prescriptive rules (analyst readout — no Claude consumer since v12.0)
        │     ├── recent_performance.md  → Layer 3: Rolling 4-week trade details (analyst readout)
        │     ├── summary.md             → Human-readable full report
        │     ├── win_rate_history.json   → Win rate snapshots over time
        │     ├── rule_registry.json     → Delta-analysis insight registry (frozen — delta retired 2026-09-10)
        │     └── quarterly/             → Deep analysis + delta analysis logs (historical)
        └── backtest_cache/              → Cached Bybit klines (JSON, no expiry — REFRESH before harness runs)
```

### Data Flow

0. Every 2h: `momentum_pulse.py` (GitHub Actions) → fetches 50 tickers, detects acceleration vs previous snapshot → flags coins to `logs/momentum/hot_list.json` + classifies market regime (`risk_off`/`cautious`/`neutral`/`risk_on`) → Telegram alert (regime changes + new flags)
1. `BybitFetcher.get_top_movers(100)` → 100 tickers by turnover (single API call)
2. `_load_hot_list()` → loads momentum pulse hot list (dynamic watchlist, 48h expiry) + market regime
3. `_ticker_interest_score()` → disqualify illiquid (<$10M vol, <$50M OI), score rest + volume acceleration bonus for hot list coins
4. Keep top 30 by score + watchlist + hot list → `get_multi_tf_indicators()` for each (4 TFs × 30 = 120 kline calls; liquidity filter usually caps the real set at ~24) + `_check_validated_signals()` on 1h/4h (zero extra API calls)
5. `mechanical_setups.build_*()` → turns fired validated signals into full setups (entry/stop/T1/T2 + deterministic rank/confidence — pure Python, zero tokens). The Claude path (`ClaudeAnalyzer.analyze` with regime/effective-limit/streak injection + `setups_json` parsing) is DORMANT — gated behind `PRIMARY_SOURCE=="claude"`, off since v12.0
6. `main.py::enforce_setups()` validates + DROPS violators (Python, free) → saves to `logs/setups/` (includes source, model tag, regime, interest_score); if the EXECUTE lane is empty, `build_watch_candidate()` surfaces one WATCH-tier candidate (`source="watch"`, paper-tracked)
7. `format_mechanical_brief()` output → archived to `logs/briefs/` + delivered via Telegram
8. Weekly: `weekly_eval.py` scores past setups (incl. simulated closer-T1 backtest) → updates tiered knowledge:
   - `lifetime_stats.json` — incremental counters incl. by_symbol, by_regime, by_rule_applied, simulated_t1 (O(1) per new eval)
   - `strategic_rules.md` — prescriptive rules with ACTION lines (~600-800 tokens) + delta insights
   - `recent_performance.md` — rolling 4-week trade details (~800 tokens)
   - `summary.md` — full human-readable report (NOT sent to Claude)
   - ~~Delta analysis~~ — **RETIRED 2026-09-10** (zero-Claude policy, `config.DELTA_ANALYSIS_ENABLED=False`; threshold had been raised 15→25 before retirement)
9. (dormant Claude path only) `build_system_prompt()` would load strategic_rules + recent_performance — today Layers 2-3 are the analyst readout and stay ready as Phase-5 ML inputs
10. ~~Quarterly: `quarterly_analysis.py`~~ — **RETIRED 2026-09-10** (calls the Claude API — zero-Claude policy)

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

Runs every 2 hours on GitHub Actions. Zero Claude tokens, single Bybit API call per run.
Detects intra-day momentum that the nightly scan would miss.

**Per-coin detection criteria** (any one triggers a flag):
- **Big move**: >8% price change AND >$200M turnover
- **Volume acceleration**: turnover >3x the previous pulse (2h earlier)
- **Funding squeeze**: |funding| >0.05% AND price moving >3%

Flagged coins are saved to `logs/momentum/hot_list.json` (48h expiry) and included as a
dynamic watchlist in the next main scan. A Telegram alert is sent immediately for new flags.

**Market regime detection** (aggregate, from the same 50-ticker data):
- Classifies overall market as `risk_off`, `cautious`, `neutral`, or `risk_on`
- Metrics: % of coins declining, median 24h change, BTC 24h change, avg funding rate, large decline count
- Regime metrics are saved with every pulse + stamped on scans; the DORMANT Claude path would inject them into user content
- Classification thresholds (tunable in config):
  - `risk_off`: (≥70% declining AND median ≤ -2%) OR (BTC ≤ -4%) OR (≥60% declining AND BTC ≤ -3%)
  - `cautious`: (≥55% declining AND median ≤ -0.5%) OR (BTC ≤ -2%) OR (≥50% declining AND BTC ≤ -1.5%)
  - `risk_on`: (≤30% declining AND median ≥ +2%) OR (BTC ≥ +4%) OR (≤40% declining AND BTC ≥ +3%)
  - `neutral`: everything else
- Regime saved in `hot_list.json` (read by main scan) and `last_snapshot.json` (for transition detection)
- Telegram alert sent on regime transitions (e.g., neutral → cautious → risk_off)
- The three `During …` bullets below are DORMANT Claude-path prompt rules; the LIVE mechanical path enforces regime intent via `LONG_CAP_BY_REGIME` / `SHORT_CAP_BY_REGIME` / `MAX_SAME_DIRECTION_PER_RUN` in `enforce_setups`
- During `risk_off`: Claude max 2 setups, at least 1 short, longs only with 4/4 TF + volume + structural support
- During `cautious`: Claude max 3 setups, longs require volume OR 4/4 TF, must include 1 short if bearish structure exists
- During `risk_on`: Claude favors trend-following longs, shorts only with clear distribution, max 5 setups

**Effective limit computation** (in `claude_client.py` — DORMANT, Claude path only):
- Resolves regime limit, losing streak limit, and loss rate limit into a single number
- Claude sees ONE directive: `EFFECTIVE LIMIT THIS RUN: MAXIMUM N SETUPS` with reasoning
- "Output more than N setups and the entire output is invalid" — removes all ambiguity
- Example: risk_off (max 2) + 3 consecutive SLs (max 3) → effective max = 2

**Losing streak circuit breaker** (in `claude_client.py` — DORMANT, Claude path only):
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

**Current Claude spend: ZERO tokens, everywhere (as of 2026-09-10).** The scan is mechanical-only (v12.0) and delta analysis — the last remaining Claude call — is retired under the zero-Claude policy. The rules below govern the DORMANT Claude path if it is ever re-enabled (historical per-run profile: ~29k input / ~8k output / ~10k thinking; extended thinking kept reasoning out of the Telegram brief).
Before adding data to any (re-enabled) Claude call:
- Estimate token impact
- Anything that >2x's current input needs justification
- Prefer pre-filtering in Python (free) over sending raw data to Claude (costs tokens)
- Use compact JSON, not pretty-printed
- New indicators should be token-efficient (e.g., SMA200 only included in 1D data, not all TFs)

---

## Environment Setup

Required `.env` keys:

Note: **no Bybit API key** — the screener reads only PUBLIC market data (get_tickers / get_kline), which needs no auth. This avoids the 90-day key expiry and IP-whitelist requirement.

```
ANTHROPIC_API_KEY=sk-ant-...     # OPTIONAL (zero-Claude policy 2026-09-10) — only for dormant Claude roles
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

# Momentum pulse (runs automatically on GitHub Actions every 2h, but can also run locally)
source venv/bin/activate
python momentum_pulse.py

# Liquidation collector (normally the CI chained workflow; run manually to spot-check)
source venv/bin/activate
python liquidation_collector.py     # Ctrl-C to stop; CI/daemon versions run persistently

# CVD collector (roadmap #4 Phase 2; CI chained workflow, run manually to spot-check)
source venv/bin/activate
python cvd_collector.py             # per-minute Bybit taker buckets; Ctrl-C to stop

# Liquidation-cluster backtest (FORK A; first pass 2026-09-10 — re-run ~2026-10-08 on ~2x data)
# Refresh the kline cache first (the harness reads cache-first!), re-download new `liquidations-*`
# artifacts + merge into logs/liquidations/ci/ (recipe: progress.md changelog 2026-09-10), then:
python liq_cluster_backtest.py --data-dir logs/liquidations/ci --interval 240
python liq_cluster_deep_dive.py     # robustness slices — kept identical between runs for comparability

# CVD / order-flow backtest (roadmap #4; uses FREE Binance deep history, no VPN, zero tokens)
python cvd_backtest.py --interval 4h --months 24 --deep   # --deep = absorption + cvd_slope tests

# Weekly evaluation (run Sundays or whenever)
source venv/bin/activate
python weekly_eval.py

# Quarterly deep analysis — RETIRED 2026-09-10 (calls the Claude API; zero-Claude policy — do not run)
# source venv/bin/activate && python quarterly_analysis.py

# Trade logger — manage manual trade journal
python trade_logger.py open      # Pick a setup, enter your entry price
python trade_logger.py close     # Close an open trade, enter exit price
python trade_logger.py list      # Show all trades with summary

# What-if backtester (uses existing eval data, zero tokens)
python backtester.py                    # Full report (all analyses, incl. version segment)
python backtester.py --t1-sweep         # T1 distance analysis
python backtester.py --combo            # Best filter combinations
python backtester.py --symbols          # Per-symbol breakdown
python backtester.py --version          # v11.3 PRE-vs-POST cutover segment + VALIDATED/UNPROVEN verdict

# Historical strategy backtester (uses cached Bybit klines, zero tokens)
python historical_backtester.py                              # Default: 6 coins, 1h
python historical_backtester.py --interval 240               # 4h timeframe
python historical_backtester.py --optimize all               # Parameter sweep all signals
python historical_backtester.py --validate all               # Train/test validation
python historical_backtester.py --validate all --interval 240 --symbols ADAUSDT,XRPUSDT,SOLUSDT,BTCUSDT,ETHUSDT,DOGEUSDT,SUIUSDT,XLMUSDT,ENAUSDT,HBARUSDT,TRXUSDT,NEARUSDT,OPUSDT,ARBUSDT,INJUSDT  # Full cross-TF validation
python historical_backtester.py --walkforward all --interval 240  # Walk-forward: robustness across rolling out-of-sample windows
```

**Terminal shortcuts** (defined in `~/.zshrc`):
- `scan` — run nightly screener (includes git pull for latest hot list)
- `pulse` — run momentum pulse locally
- `eval-scan` — run weekly evaluation (delta analysis RETIRED 2026-09-10 under the zero-Claude policy; the learning loop is fully algorithmic)
- `backtest` — full backtest pipeline: validate signal formulas on 4h + 1h (15 symbols, fresh data) + eval combo analysis + **v11.3 version segment** (PRE-vs-POST cutover verdict). NOTE: this validates the mechanical signal FORMULAS and re-analyzes PAST trades — it does NOT test whether v11.3's *selection* logic (confluence floor, rank de-trust, long cap) works. That is forward-only via `eval-scan` → the version segment.
- `trade` — manage manual trade log (`trade open`, `trade close`, `trade list`)
- `quarterly-scan` — RETIRED 2026-09-10 (calls the Claude API — zero-Claude policy; superseded by `backtest`)

**Recommended workflow:**
- **Daily:** `scan` (or let launchd run it at 09:00 / 17:00 / 22:00 local)
- **Weekly:** `eval-scan` (scores past setups, updates algorithmic rules + net-of-cost readouts)
- **Monthly:** `backtest` (re-validates signal formulas with fresh market data)

### Scheduled Runs

- **Momentum pulse + mechanical scan**: GitHub Actions, every 2 hours (`.github/workflows/momentum_pulse.yml`). One job runs the pulse, then `main.py`, then a single race-safe commit. The scan runs **mechanical-only** (as of 2026-08-26 this is true everywhere — `PRIMARY_SOURCE="mechanical"` skips the Claude call outright; CI also has **no `ANTHROPIC_API_KEY`** as a second layer). Reuses the WireGuard VPN (`WG_CONF`) for Bybit access. Auto-commits `hot_list.json` + `logs/setups/` + `logs/briefs/` back to the repo. Secrets are GitHub repository secrets.
- **Local scan**: macOS `launchd` (`~/Library/LaunchAgents/com.user.cryptoscreener.plist`) → runs `run_scan.sh` (the alias-equivalent wrapper) at **09:00 / 17:00 / 22:00 local**. As of 2026-08-26 this **no longer calls Claude** either (`PRIMARY_SOURCE="mechanical"` gates the scan Claude call off even though the local `.env` still has the key) → identical mechanical output to CI, zero scan tokens. Claude spend is ZERO everywhere as of 2026-09-10 (delta analysis retired). **Requires VPN up at those times** (Bybit + Telegram are ISP-blocked); a scan with VPN down fails at data fetch. launchd logs go to `~/Library/Logs/cryptoscreener_scan.{log,err}` (outside the repo so `git add -A` won't commit them). Reload after editing the plist: `launchctl unload … && launchctl load -w …`.
- **Cross-run dedup**: because the scan now runs 12×/day, `main.py::_active_setup_keys` / `_drop_active_duplicates` suppress a coin already carrying an active `(symbol, direction, source)` setup within the 2-day eval window — prevents correlated pseudo-replicate trades from polluting the eval / flip gate.
- **Commit races**: both CI (12×/day bot) and the local nightly push to `master`. The CI commit step does `git pull --rebase origin master` + retry; the local commit should do the same (`git add logs/ && git commit && for i in 1 2 3; do git pull --rebase && git push && break || sleep 5; done`). `eval-scan` must `git pull --rebase` first to pick up CI-pushed setups before scoring.
- **Liquidation collector** (FORK A, forward-collection): `liquidation_collector.py` subscribes to Bybit's `all_liquidation_stream` WS for ~20 liquid perps and appends raw prints to `logs/liquidations/liq_YYYY-MM.jsonl`. **Data-collector ONLY — zero trading decisions, no order API** (CORE PRINCIPLE). Purpose: true historical liquidation data isn't free, so accumulate it forward and backtest the liquidation-CLUSTER hypothesis (first pass 2026-09-10: bar not met, one extension → re-run ~2026-10-08; see progress.md item #3). A **stall-watchdog** (`LIQ_STALL_SECONDS`, default 45 min) rebuilds the WS after silence — pybit's auto-reconnect dies quietly after VPN blips, which is what caused the 44%-coverage finding. Two host modes:
  - **PRIMARY — CI chained job** (`.github/workflows/liquidation_collector.yml`, requires PUBLIC repo for free unlimited Actions minutes): ephemeral runners can't hold a stream, so it CHAINS ~5.5h jobs (every 6h, `LIQ_MAX_SECONDS=19800` self-exit) and uploads each run's JSONL as a 90-day **artifact** (NOT commits → no git bloat). Reuses `WG_CONF` VPN. Coverage ≈92% per 6h window minus cron jitter. Backtest later = download all artifacts + concat.
  - **STOPGAP — launchd daemon** (`com.user.liqcollector.plist` → `~/Library/LaunchAgents/`): persistent KeepAlive on the Mac; `LIQ_MAX_SECONDS` unset = runs forever. Collects while Mac awake + VPN up (gaps). Logs `~/Library/Logs/liqcollector.{log,err}`. **Kept running deliberately (decision 2026-09-10) as gap-filler while CI runs are flaky** — the backtest loader dedups exact repeats, so double-collection is harmless. `logs/liquidations/` is gitignored (local/artifact only; `ci/` subdir = merged canonical store).
- **CVD collector** (roadmap #4 Phase 2, forward-collection, live 2026-08-17): `cvd_collector.py` subscribes to Bybit's `publicTrade` WS for the same ~20 perps and aggregates trades into **per-minute taker buckets** (buy/sell base+quote volume, count) in `logs/cvd/cvd_YYYY-MM.jsonl` — NOT the raw tape (too big); per-bar CVD / cvd_slope is reconstructable from the minute deltas at backtest time. **Data-collector ONLY — zero trading decisions, no order API** (CORE PRINCIPLE). Purpose: `cvd_backtest.py` found a robust `cvd_slope`-confirm edge on Binance PROXY data; Bybit has no free historical trade feed, so collect on-venue forward and re-confirm before promoting (data gate reached 2026-09-10 at 3.4 weeks; still needs a small Bybit-bucket loader for `cvd_backtest.py`). Same stall-watchdog as the liq collector (`CVD_STALL_SECONDS`, default 10 min — publicTrade is continuous, so silence = dead socket). CI chained job `.github/workflows/cvd_collector.yml` — same pattern as the liq collector (chains ~5.5h jobs, `CVD_MAX_SECONDS=19800`, cron offset `30 */6` to spread VPN load, uploads `cvd-<run_id>` 90-day artifacts, reuses `WG_CONF`). `logs/cvd/` is gitignored.
- Do NOT migrate to cron — launchd handles wake-from-sleep better.

---

## Extending the System — Guardrails

1. **Never add write-path Bybit calls** (place_order, cancel_order, etc.). Confirm Phase B preconditions first.
2. **Never let free-text output drive actions.** Use structured JSON (`setups_json`) with validated fields.
3. **New data sources welcome** — wire into `fetchers/` and surface them to the mechanical engine. (Claude-context plumbing + token-impact estimates apply only on the dormant Claude path.)
4. **Prompt changes**: update `analyzer/prompts.py`. Never weaken the 1.5:1 R:R floor (now carried by target_2, not target_1), remove risk framework, or make Claude more aggressive about calling trades.
5. **Knowledge files** in `/knowledge/*.md` are user-editable. Keep human-readable. (Loaded into the prompt only on the dormant Claude path — the live pipeline makes no Claude call; the pre-filter encodes their rules in Python.)
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
- **Bybit rate limits**: 30 symbols × 4 TFs = 120 kline calls (liquidity filter usually trims to ~24 symbols). `time.sleep(0.05)` between calls. If 429s appear, increase delay.
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
5. **Trailing stop model (v11.2)**: once T1 is hit (MFE < 1R) the simulated stop moves to entry (breakeven). Once price runs **1.0R in profit, the stop tightens to +0.3R** (lock a partial gain) instead of breakeven — backtest showed many trades reached 1.0–2.2R MFE then reversed to a 0R exit. Worst case after 1R is +0.3R, not 0R or −1.0R. Tracked as `trail_stop_hit`. The trail decision uses prior-candle MFE (no intracandle look-ahead).
6. **Partial profit model**: calculates `blended_rr` = 50% closed at T1 + 50% trails with BE stop to T2/expiry. This models realistic position management.
7. **Simulated closer-T1 backtest**: also checks if T1 at 0.75R and 1.0R would have been hit before stop
8. Saves to `logs/evaluations/eval_*.json` (includes `blended_rr`, `be_stop_hit`, `sim_t1_*` fields)
9. Updates tiered knowledge distillation (see below)
10. (dormant Claude path only) `build_system_prompt()` would load strategic_rules + recent_performance — today Layers 2-3 serve as the analyst readout and as future Phase-5 ML inputs

### Tiered Knowledge Distillation

Instead of sending all historical data to Claude every run (which would grow unboundedly), the system distills evaluation data into three layers:

> **2026-09-10 (zero-Claude policy):** nothing is sent to Claude anymore. The "Sent to Claude?" column below describes the DORMANT Claude path; today Layers 2–3 are generated fully algorithmically each `eval-scan` and serve as the analyst readout + ready-made Phase-5 ML inputs.

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

### Self-Learning System

**The learning loop is FULLY ALGORITHMIC as of 2026-09-10 (zero-Claude policy).** The `scan` → `eval-scan` cycle is the loop: evals update `lifetime_stats.json` → `generate_strategic_rules()` derives prescriptive rules in pure Python (anti-overfit gated: `RULE_MIN_SAMPLE`, `REGIME_RULE_MIN_TRADES`, `DIRECTION_RULE_MIN_TRADES`) → `head_to_head.md` prints the net-of-cost verdict + WATCH promotion readout → the version segment prints the era verdict. Findings enter the live pipeline ONLY through the validated promotion path (monthly `backtest` out-of-sample validation → `_check_validated_signals` / config gates) — never auto-injected. The planned fully-closed ML loop is **Phase 5** (owned scikit-learn take/skip meta-filter), data-gated on real features (dist-to-level, dist-to-liq-cluster, CVD).

**Delta analysis — RETIRED 2026-09-10** (`config.DELTA_ANALYSIS_ENABLED=False`). It was the last remaining Claude API call; the description below is preserved for the dormant/reversible path:
- **Trigger**: auto-runs after every `eval-scan` when 25+ new evaluated trades have accumulated (`DELTA_ANALYSIS_TRADE_THRESHOLD`; execute-book trades only — watch excluded)
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

**Post-scan enforcement** (`main.py::enforce_setups()` + per-setup `setup_violations()`) — replaced the old log-only `validate_setups`:
- Pure Python (zero tokens) — runs after the setups are built/parsed, before saving; applied to whichever source is delivered
- `setup_violations()` flags per setup: valid types/directions/timeframes, T1 ≤ 1.0R cap, T2 ≥ 1.5R edge floor, confluence floor (≥3/4), **4/4 confluence REFUSED outright, both directions** (`config.REFUSE_4OF4_CONFLUENCE` — 4/4 is the worst bucket), long volume gate + long blacklist + long signal-backing gate
- `enforce_setups()` then **DROPS** violators (no longer log-only), dedupes by symbol, applies regime long/short caps + same-direction concentration cap, demotes any surviving 4/4 off rank #1, and re-ranks

### Quarterly Deep Analysis (Manual) — RETIRED 2026-09-10

`quarterly_analysis.py` stays in the repo but is NOT to be run — it calls the Claude API (zero-Claude policy). Historical description:
- Run via `quarterly-scan` terminal command
- More thorough than delta analysis (uses larger context, deeper prompt)
- Useful for periodic deep-dives after 50+ new trades
- Findings append to `strategic_rules.md` (may be overwritten by next delta analysis)

### Model Comparison

Every setup JSON includes a `model` field — since v12.0 mechanical setups carry `"model": "mechanical_v1"` (the claude lane is frozen with its history preserved). The eval tracks win rate and avg R:R per model in `lifetime_stats.json`; the strategic rules include a model comparison when 5+ trades per model exist.

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
- **Setup**: a trading opportunity with entry zone, stop, target 1+2, R:R, and confidence. T1 is a partial-profit level at 0.75–1.0R; T2 (the reward leg) must be >= 1.5R. Every long must also have `volume_confirmed=true`.
- **setups_json**: structured JSON block Claude appends to every brief for machine-readable tracking.
- **Pre-filter**: Python scoring of 100 tickers down to 30 before kline fetching, using knowledge-derived rules.
- **Multi-TF confluence**: how many of 4 timeframes agree on direction. Empirically (237 trades, audit 2026-07-13) **3/4 is the edge (+0.01R), 4/4 is the WORST bucket (−0.36R) — full alignment = exhausted/late move, not higher probability.** Do NOT map 4/4→high confidence. ALL setups require ≥3/4 (`config.LONG_MIN_CONFLUENCE`) and **4/4 is REFUSED outright, both directions** (`config.REFUSE_4OF4_CONFLUENCE`; net-of-cost cut 2026-08-09 confirmed 4/4 = −0.305R/n=71, still the worst) — enforced in `main.py::setup_violations`. `weekly_eval.py` tracks `by_confluence` and surfaces the 3/4-beats-4/4 rule.
- **Watchlist**: symbols always analyzed regardless of pre-filter score (BTC, ETH, SOL).
- **Phase A / Phase B**: analyst-only (current) vs. auto-execution (future, requires preconditions).
- **Interest score**: numeric score from `_ticker_interest_score()` used to rank 100 tickers for pre-filtering.
- **MFE (Max Favorable Excursion)**: how far price moved in Claude's predicted direction before outcome. Used to diagnose "direction right, execution wrong" and compute optimal T1 distance.
- **Simulated T1 backtest**: per-trade check of whether a closer T1 (at 0.75R or 1.0R) would have been hit before stop. Aggregated to quantify optimal T1 distance.
- **Blended R:R**: the partial profit model result. 50% of position closed at T1, remaining 50% trails with breakeven stop. Calculated as `0.5 * T1_rr + 0.5 * actual_rr`. More realistic than all-or-nothing scoring.
- **BE stop (breakeven stop)**: after T1 is hit (MFE < 1R) in the eval, the stop moves to entry price. If price reverses, the worst case is 0R instead of -1.0R. Tracked as `be_stop_hit` in eval results.
- **Trail stop (+0.3R lock)**: once price runs 1.0R in profit, the eval stop tightens to +0.3R instead of breakeven, so structural winners that reverse still exit green (+0.3R, not 0R). Tracked as `trail_stop_hit` and `partial_profit.trail_stops`. Uses prior-candle MFE (no look-ahead). Added v11.2.
- **Momentum pulse**: lightweight scanner (`momentum_pulse.py`) that runs every 2h on GitHub Actions. Fetches 50 tickers, compares against previous snapshot to detect volume/price acceleration. Zero Claude tokens. Flags coins to `logs/momentum/hot_list.json`.
- **Hot list**: dynamic watchlist generated by the momentum pulse. Coins flagged for big moves, volume acceleration, or funding squeezes. Entries expire after 48h. Main scan merges hot list into watchlist automatically.
- **Volume acceleration**: ratio of a coin's current turnover vs its turnover at the previous pulse (2h earlier). >3x triggers a flag. >2x gives a scoring bonus in the pre-filter. Detects coins that are ramping up before they appear in the top 50 by absolute turnover.
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
- **Delta analysis**: **RETIRED 2026-09-10** (zero-Claude policy, `config.DELTA_ANALYSIS_ENABLED=False`) — was the last remaining Claude API call. Historically: triggered every 25 new evaluated trades (raised from 15), called Claude to find patterns, grade previous insights, and generate ACTION rules appended to `strategic_rules.md` under `## Delta Insights`. The algorithmic rule generation (`generate_strategic_rules()`) continues unchanged.
- **Rule registry** (`rule_registry.json`): tracks delta analysis insights — when they were added, their status (`experimental`/`confirmed`/`expired`), and win rate snapshots. Enables insight effectiveness tracking over time.
- **Reasoning capture**: `reasoning` field in setup JSON containing `rules_applied` (list of rule IDs) and `key_factor` (one-line driver). Carried through to eval results, tracked in `by_rule_applied` stats. Enables rule-level attribution — "did setups citing this rule win more?"
- **WATCH tier / EXECUTE tier** (added 2026-08-20, the "always an opinion" reframe): every scan surfaces at least one candidate, tagged one of two tiers. **EXECUTE** = a validated net-of-cost signal that passed the full `enforce_setups` gates → delivered, `source` in {mechanical, claude}, counted in the edge-proven book. **WATCH** = the best available candidate when the EXECUTE lane is empty → `source="watch"`, `tier="watch"`, bypasses the protective gates (confluence floor, long-volume/backing, caps), paper-tracked only, and **excluded from every edge/expectancy/version counter** in `weekly_eval.py` (guarded at the top of `update_lifetime_stats`'s per-result loop; still bucketed under `by_source["watch"]` so head_to_head shows the WATCH lane separately). Built by `main.py::build_watch_candidate` with priority: (1) a watch-tier/gate-rejected signal that fired (e.g. `rsi_bounce_long`), else (2) `_observation_candidate` — the top-`interest_score` coin in its dominant multi-TF trend (`signal_name="observation"`, lowest confidence). Purpose: never a silent scan + faster eval velocity toward the ≥100-forward-trade edge proof, WITHOUT adding executed net-negative trades. Rendered under "👀 Watch Candidate" by `format_mechanical_brief(..., watch=...)`.
- **rsi_bounce_long** (WATCH-tier signal, added 2026-08-20): oversold mean-reversion long — RSI was <30, now crossing back up (30–45, rising) on 4h. Validated GROSS on the 2026-08-20 re-run (test +0.108R / N=20 / 100% robust) but **net-marginal after ~0.12R cost**, so it ships as `tier="watch"` (surfaced + paper-tracked, never executed). It is also the long-side coverage the EXECUTE gates reject — fired at a bottom it has low bullish confluence + no volume spike. Detected in `_check_validated_signals`; note it fires on OVERSOLD, so it does NOT chase an upward spike. `volume_breakout_long` (the literal momentum/breakout long) is DEAD — "no viable combos on train set." The **ride-the-wave continuation long** (`momentum_continuation_long`, enter the first pullback that holds above EMA20 after a breakout) was designed + validated 2026-08-20 and came back **OVERFIT** (train +0.66R → test −0.56R, WR 56%→15%) — NOT promoted; kept as a documented rejected candidate in `historical_backtester.py`. Upshot: there is **no validated price-pattern long that catches a spike**, up or down — the WATCH tier (not a manufactured signal) is what guarantees daily long-side coverage until a *predictive* input (liq clusters / CVD) lands.
- **Post-scan enforcement**: pure Python enforcer in `main.py` (`setup_violations()` per setup + `enforce_setups()` cross-setup) — replaced the old log-only `validate_setups`. Flags hard rules (setup count, T1 ≤ 1.0R cap, T2 ≥ 1.5R edge floor, confluence ≥3/4, **4/4 refused**, long volume gate + blacklist + signal-backing, valid types, regime requirements) and **DROPS** violators, then dedupes/applies caps/re-ranks. Zero token cost.
- **Validated signals**: mechanical signal formulas that passed out-of-sample train/test validation on 15 symbols. Detected by `_check_validated_signals()` in `bybit_data.py` during each scan and consumed by `mechanical_setups.py`. **Current EXECUTE set (2026-09-10 monthly re-validation):** `trend_pullback_short` (downtrend pullback to EMA20, **4h ONLY** — holds by a thread: top combo test +0.037 gross/100% robust but #2-5 marginal, net-negative after cost; kept until the ~Oct 8 fork-A checkpoint), `failed_breakout_short` (failed breakout of prior 20-candle high, **4h ONLY** — test +0.096/N=63/67% robust; STRUCTURAL stop at the fired candle's high +0.25 ATR via explicit `stop_price`), `liquidity_sweep_long` (wick sweeps prior 20-candle low then reclaims with RSI<50, **confirmed BOTH TFs again** — 1h +0.098/100% robust; structural stop at swept low −0.25 ATR; the only EXECUTE long, rarely fires live). **WATCH tier (paper-tracked, never executed):** `rsi_bounce_long` (4h), plus — added 2026-09-10 — `range_reversion_short` (4h, ★ +0.250 gross/N=30/100% robust) and `range_reversion_long` (4h, ★ +0.196/N=23/100% robust; doubles as long-side coverage): both were REJECTED in earlier re-runs, and a reject→strong flip requires a SECOND consecutive monthly pass before EXECUTE promotion. **REMOVED:** `rsi_rejection_short` **1h removed 2026-09-10** — failed the re-validation on fresh 1h data while its 4h variant flipped to ★ STRONG (+0.283/N=82/100%); the 4h variant is a promotion candidate pending a 2nd consecutive pass (the CVD slope-confirm fork pairs with it). `macd_momentum_long/short` stay out (repeat flip-floppers — passed again Sep 10 on one TF each). `failed_breakout_short_stacked` is now 100% robust on 4h but stays HELD (largely duplicates `failed_breakout_short`). Validation expectancies are GROSS — subtract ~0.07R for the net lens. The set is re-checked monthly via `backtest`; when a signal drifts, `_check_validated_signals()` is manually updated to match (done Jul 29, Sep 10).
- **Historical backtester** (`historical_backtester.py`): fetches Bybit klines (cached locally), defines 18 mechanical signal rules (incl. `failed_breakout`, `liquidity_sweep`, and confluence-`*_stacked` candidates added Phase 3), runs parameter sweep optimization (`--optimize`), train/test validation (`--validate`), and **walk-forward** validation across rolling out-of-sample windows (`--walkforward`). Signals without a hand-vectorized fast sweep are optimized/validated via a generic slow factory path (`_eval_combo`). Tests on 1h (42 days) and 4h (167 days) of data. Zero Claude tokens. New signals stay CANDIDATES until they pass validation on real data — only then are they promoted into `bybit_data._check_validated_signals`.
- **What-if backtester** (`backtester.py`): reads existing eval/setup logs, sweeps parameters (T1 distance, filters, regime limits, symbol blacklists), reports expectancy/WR/profit factor. Useful for answering "what if we changed X?" Zero Claude tokens. Also hosts `report_version_segments()` (`--version`).
- **CVD (cumulative volume delta) / order flow** (roadmap #4): net taker aggressor flow = taker-buy volume − taker-sell volume. **`cvd_slope`** = normalized CVD momentum over K bars; a positive on `rsi_rejection_short` = "confirm the short only when flow momentum is aligned (net selling)." Tested 2026-08-17 via **`cvd_backtest.py`** (research-only, zero trade decisions) on FREE Binance USD-M kline dumps (`data.binance.vision`, whose CSVs carry `taker_buy_base_volume` = per-bar CVD; reachable without VPN — only `fapi` REST is blocked). Net-of-cost, chrono train/test + parameter/robustness sweeps. Result: divergence + absorption + per-bar taker-share *level* filter all dead/overfit; **`cvd_slope`-confirm on `rsi_rejection_short` is the one robust lead** (+0.11..+0.13R net 4h, monotonic, OOS-stable, cross-TF). Binance is a PROXY — **`cvd_collector.py`** now forward-collects real Bybit CVD (see Scheduled Runs) to confirm on-venue before any promotion. Not yet a live signal.
- **Version segment / version_markers** (added v11.3): the mechanism that measures whether a shipped change actually improved live results. `logs/performance/version_markers.json` records a cutover (version, `cutover_trade_count`, baseline WR/rr_sum, `validation_target` = min_trades/wr_target/expectancy_target). `backtester.py::report_version_segments()` splits evaluated trades PRE vs POST cutover — POST = trades carrying `interest_score` (a field only the post-v11.3 pipeline writes, so it's an unambiguous era marker) — compares WR/expectancy/PF and prints a verdict: `UNPROVEN` (0 forward trades) → `VALIDATING (n/min)` → `VALIDATED` / `NOT VALIDATING`. It also audits POST trades for gate violations that should be impossible (confluence<3, 4/4-at-rank1). `weekly_eval.py::_version_validation_line()` prints the same verdict (from lifetime counters) as rule-0 of `strategic_rules.md` each eval-scan. **Key distinction**: the `backtest` command validates signal formulas + proposes rules from past trades; it CANNOT test a forward-selection change like v11.3 (past trades were picked by the old logic). Only `eval-scan` scoring new picks feeds the version segment. So a fresh v11.3 change reads `UNPROVEN` on the backtest until ~20 new trades are evaluated over the following weeks.
- **interest_score** (per-setup, added v11.3): the pre-filter `_ticker_interest_score()` value, now stamped onto each setup + eval record (`main.py` → `weekly_eval.py`). Two purposes: (1) makes pre-filter selection quality measurable (previously a blind spot), and (2) serves as the structural marker distinguishing v11.3-era trades from pre-v11.3 in the version segment.
- **Train/test validation**: splits cached kline data 60/40 — optimizes parameters on train half, evaluates on test (unseen) half. If test expectancy is negative, the formula is overfit and rejected. Prevents integrating patterns that only work in hindsight.
- **Robustness score**: for each top formula, checks if neighboring parameter values (±1 step) also have positive expectancy. High robustness (>50%) means the formula works across a range of conditions, not just one lucky parameterization.
