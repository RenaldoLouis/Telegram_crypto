# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**crypto-screener** is a personal, scheduled screener for Bybit USDT perpetual futures. It fetches market data, aggregates signals from Telegram groups, asks Claude (via the Anthropic API) to produce a structured analyst brief, and delivers the brief to the user's personal Telegram via a bot.

### Current Phase

**Phase A — Analyst mode (signal-only, NOT auto-trading).**
Claude analyzes data and surfaces setups. The human makes every trading decision and executes every order manually. Phase B (auto-execution) is explicitly out of scope until Phase A has shown measurable edge over 1–3 months of journaling.

### Non-Goals (Important)

- ❌ Do NOT add order execution logic, even if asked casually.
- ❌ Do NOT wire Claude output directly to the Bybit write API.
- ❌ Do NOT expand the Bybit API key permissions beyond Read-Only.
- ❌ Do NOT fabricate trading setups to fill the output template — "no trade" is a valid brief.

Auto-execution will only be considered after: (a) a documented backtest/journal of ≥60 days of Phase A output, (b) a separate, hard-coded risk engine (not Claude) enforcing position sizing and stop-losses, and (c) explicit user approval to begin Phase B.

---

## Architecture

```
main.py  (orchestrator, async)
  │
  ├── fetchers/bybit_data.py       → BybitFetcher: pybit → top movers + 1h klines + RSI, vol spike, breakout flags
  ├── fetchers/telegram_reader.py  → TelegramReader: Telethon → reads configured groups from last N hours
  │
  ├── analyzer/prompts.py          → SYSTEM_PROMPT + load_knowledge() (loads /knowledge/*.md)
  ├── analyzer/claude_client.py    → ClaudeAnalyzer: wraps Anthropic SDK, returns (brief_text, usage)
  │
  ├── delivery/telegram_bot.py     → send_brief(): posts brief to TELEGRAM_CHAT_ID via bot token
  │
  ├── knowledge/*.md               → User-editable trading rules, watchlists, context. Injected into system prompt.
  └── logs/briefs/*.md             → Every brief is archived here with timestamp (for later edge evaluation)
```

### Data Flow

1. `BybitFetcher.get_full_market_snapshot()` → dict with `top_movers` + `technicals`
2. `TelegramReader.read_groups()` → list of recent messages from configured signal groups
3. `ClaudeAnalyzer.analyze(market, messages)` → `(brief_str, usage_dict)`
4. Brief written to `logs/briefs/brief_YYYYMMDD_HHMM.md`
5. `send_brief()` delivers to user's Telegram

All steps are idempotent and stateless — each run is a full snapshot. No cross-run state.

---

## Tech Stack & Conventions

- **Python 3.12+** (user is on 3.14). Use native `bool`/`float` when returning to JSON — numpy types break `json.dumps` on 3.14.
- **venv**: project has a local `venv/`. Always activate before running: `source venv/bin/activate`.
- **Dependencies**: `anthropic`, `pybit`, `telethon`, `python-dotenv`, `requests`, `pandas`.
- **Secrets**: all secrets live in `.env` (gitignored). Never hardcode, never log, never commit.
- **Model**: defaults to `claude-haiku-4-5` for cost. Switch to Sonnet when tuning prompts or debugging analysis quality.

### Coding Conventions

- Async is used only where necessary (Telethon). Bybit + Claude calls are synchronous — do NOT make them async unless there's a real reason.
- Every function that hits an external API must have try/except and print a clear error; the pipeline should degrade gracefully (e.g., if Telegram reading fails, still run Claude with market data only).
- Always cast pandas/numpy values to native Python types (`float()`, `bool()`, `int()`) before putting them in dicts destined for `json.dumps`.
- Never log API keys, bot tokens, or raw `.env` contents.
- Telegram bot messages have a 4096 char limit — chunk long briefs.

### Dependency Management

- When adding a package, update `requirements.txt` and document why in the PR/commit message.
- Pin major versions only (`anthropic>=0.40.0`) unless there's a known breaking change.

---

## Environment Setup

Required `.env` keys (see `.env.example` if present; otherwise the list below):

```
ANTHROPIC_API_KEY=sk-ant-...
BYBIT_API_KEY=...               # Read-Only, IP-whitelisted
BYBIT_API_SECRET=...
TELEGRAM_API_ID=...              # from my.telegram.org (Telethon)
TELEGRAM_API_HASH=...            # from my.telegram.org (Telethon)
TELEGRAM_BOT_TOKEN=...           # from @BotFather (for delivery)
TELEGRAM_CHAT_ID=...             # user's personal chat ID for brief delivery
```

### Network Notes

- **Bybit is blocked by Indonesian ISPs.** Runtime environment (local dev or scheduled job host) needs a VPN or must run from a non-blocked region. Do NOT hardcode workarounds — the VPN is an environment concern, not a code concern.
- Bybit API key is region-aware; if IP whitelisting is on, the whitelisted IP must match wherever the script actually runs (including VPN exit IP if used). Document any changes.

---

## How to Run

```bash
# First time only
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Every run (manual)
source venv/bin/activate
python main.py
```

**Important**: inside the venv, always use `python` (not `python3`) — on macOS `python3` can bypass the venv and resolve to system Python, which won't have the installed packages.

### Scheduled Runs

On macOS, scheduling is via `launchd` (`~/Library/LaunchAgents/com.user.cryptoscreener.plist`). Default schedule: 7am + 9pm local.
Do NOT migrate to cron without reason — launchd handles wake-from-sleep better on macOS.

---

## Extending the System — Guardrails

When asked to add a feature, respect these guardrails:

1. **Never add write-path Bybit calls** (place_order, cancel_order, set_leverage, etc.), even behind flags. If the user asks, stop and confirm they are transitioning to Phase B and have the preconditions met.
2. **Never let Claude's free-text output drive an action directly.** If logic needs to act on Claude's analysis, require a structured output (JSON with validated fields) and a deterministic parser.
3. **New data sources are welcome** (news APIs, CoinGlass funding/OI, on-chain feeds) — wire them into `fetchers/` following the existing pattern and pass them into the Claude context.
4. **Prompt changes**: update `analyzer/prompts.py`. Knowledge files in `/knowledge/*.md` are user-editable and should stay human-readable. The system prompt should NEVER be edited to be more aggressive about calling trades, weaken the R:R 1:2 floor, or remove "no trade is valid" language.
5. **Token discipline**: before adding more data to the Claude call, estimate token impact. Current per-run is ~5–10k tokens; any feature that >3x's this needs a justification.

### Files That Should NOT Drift Without Discussion

- `analyzer/prompts.py` → system prompt's risk framework section
- `config.py` → Bybit permission scope expectations
- `.env.example` → the shape of required secrets

---

## Known Issues & Gotchas

- **Python 3.14 + numpy bools**: `json.dumps` will raise `TypeError: Object of type bool is not JSON serializable` for `numpy.bool_`. Always wrap in `bool()`. Same for `numpy.float64` → wrap in `float()`. See `fetchers/bybit_data.py::get_klines_with_indicators`.
- **Telethon session file**: first run prompts for phone + SMS code and creates `screener_session.session` in the project root. Treat that file as a secret (gitignore it).
- **Telegram bot token exposure**: if a token is ever pasted into a screenshot/log, revoke immediately via `@BotFather → /mybots → API Token → Revoke`.
- **Bybit rate limits**: `get_kline` is called once per symbol in the loop. At 40+ symbols this can hit limits — consider batching or a small `time.sleep(0.1)` if you see 429s.
- **Pandas rolling() warmup**: first 13–20 candles return NaN for RSI and volume-spike ratio. Code handles this with `pd.notna()` — preserve those guards on any edit.

---

## Journaling (the most important habit)

Every archived brief in `logs/briefs/` is meant to be reviewed after the fact. Before adding fancy features, make sure:

- Every brief is saved (it is — in `main.py`).
- The user can easily re-read the brief alongside what actually happened in the market.
- Eventually: a lightweight eval script that scores past briefs against subsequent price action. This is a prerequisite for Phase B, not a nice-to-have.

---

## Glossary

- **Brief**: the structured output Claude produces per run (Market Context, High-Conviction Setups, Watchlist, Risk Flags, Takeaway).
- **Setup**: a trading opportunity with entry, invalidation, target, and R:R. Must have R:R ≥ 1:2 to appear in High-Conviction.
- **Watchlist**: (a) the user's always-included symbols in `config.WATCHLIST`, or (b) symbols Claude flags as interesting but not ready.
- **Phase A / Phase B**: analyst-only vs. auto-execution. See top of file.
