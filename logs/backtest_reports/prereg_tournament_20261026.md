# Pre-registration — forward paper tournament (2026-10-26)

Written 2026-10-26, BEFORE the first recorded weight. The entrants, controls, stages and bars below
are frozen; a change = a new tournament with a new date (the run refuses if the frozen code changes).

**Why (user, 2026-10-26):** the user asked whether a Go bot (talking to other bots over Discord)
could search for the best strategy. Answer: no. Speed was never the limit, a bigger search only
finds better-looking noise (the best of N no-edge strategies over 4 years reaches Sharpe 1.54 at
N = 114, 2.15 at 10,000 and 2.63 at 1,000,000), and the 2025–26 holdout is spent. The honest
version of "search harder" is to run many frozen candidates FORWARD in parallel, so the calendar
is spent once for all of them. The user approved this design and its options (entrants as
proposed, two stages 13 + 26 weeks, the daily book kept as a paper lane after the 2026-11-02 review).

**Code:** `tournament_paper.py` + a step in `.github/workflows/blend_paper.yml` → `logs/tournament/`.
Tests: `test_tournament_paper.py`. Paper only: no order API, no hosted model.

## Why two stages (measured before writing this)

- A book with no edge passes paper #3's 6-month bar (net > 0, ≥ 4/6 months green, Sharpe ≥ 0.75,
  drawdown ≤ 12.5%) **23% of the time**; at least one of 10 independent such books passes **93%**
  (Monte Carlo, 200,000 runs, 10% volatility). Crowning the 6-month leader would crown luck.
- So stage 1 only **selects**; stage 2 **judges** on days the selection never saw — the
  discovery → holdout protocol of `prereg_edge_search_20261025.md`, run forward.

## Entrants (frozen)

The four sleeves of paper #3's blend (`edge_search` variant `volman_combo_4_sleeves`), each run
alone. Each lane = the sleeve's weights exactly as the blend builds them × its frozen DISCOVERY
20%-vol scale × 0.5 = **a 10% annual-volatility book**. Scales are read from the frozen variant.

| lane | edge_search variant | 20%-vol scale | 2025–26 holdout Sharpe (as a sleeve) |
|---|---|---|---|
| `mom28` — 28-day momentum | `xs_mom_28d_skip0_10pct` | 0.5152 | +1.70 |
| `listing_short` — new-listing short, BTC-hedged | `new_listing_short_d1_h60_btc` | 0.3387 | +0.54 |
| `btc_trend` — BTC trend, long only | `volman_btc_sma50_long` | 0.7378 | +0.36 |
| `carry7` — funding carry 7d | `xs_carry_7d_20pct` | 0.9855 | −0.80 |

## Random controls (frozen)

`random_1`, `random_2`, `random_3`: the 28-day momentum book (`xs_book`, top/bottom 10% of eligible
names, 0.5 gross per leg, held Monday → Monday, same 0.5152 × 0.5 scale) with the ranking replaced
by a fixed pseudo-random number per (seed, Sunday, symbol) — seeds 1, 2, 3 (sha256, independent of
the data window). Same universe, costs and funding as the entrants. They show every week how good
luck can look, and stage 1 requires beating all three.

## Shown, on their own clocks (nothing here changes them)

Paper #2 momentum k56 and k91 (weekly), paper #3 blend (daily), the daily book and checklist ≥ 5
(per trade, converted to % of the account at 0.5% risk per trade, by the Monday of the signal).
They are never selected by this tournament; each keeps its own pre-registered decision.

## Data and accounting

Identical to paper #3: every trading crypto Bybit USDT perp (stock/ETF/commodity/forex and pegged
tokens excluded), the last 200 days of closed daily bars + funding, eligibility listed ≥ 30 days
and 30-day median turnover ≥ $5M; weights decided at each UTC daily close, held over the next
day; taker 0.055% + slippage 0.03/0.06/0.12% by liquidity on every weight change; actual funding.
P&L = `edge_search.run_weights` (asserted on every run). The tournament reuses paper #3's download
when it is complete and current, else downloads the same data; any failed symbol aborts the run.
Window weights reproduce the full-history weights for every lane (test). A missed day is recorded
later from data cut at that day (marked late); more than 7 days missed = a gap (flat).

## Timeline and rules

- **Shakedown:** rows from the close of 2026-10-25 to 2026-11-01 are recorded and shown, never counted.
- **Stage 1 — selection, 2026-11-02 → 2027-01-31 (13 weeks).**
  - KILL at any time: an entrant whose drawdown from 2026-11-02 passes **15%** is out.
  - At the end (the 2027-01-31 row scored for every lane), at most **2** entrants go on that are
    not killed, have **net > 0**, and a daily **Sharpe above every random control's**; best Sharpe
    first. Written once to `logs/tournament/selection.json`, never recomputed. No pick = the
    tournament ends with "none selected".
- **Stage 2 — confirmation, 2027-02-01 → 2027-08-01 (26 weeks), stage-2 days only.**
  - KILL / FAIL at any time: drawdown from 2027-02-01 passes 15%.
  - At the end: one-sided t-test of the daily mean > 0; **Holm at 5%** across the picks (the best p
    must be ≤ 2.5% with two picks, the other ≤ 5%; a lone pick ≤ 5%). PASS = clears it.
  - In Sharpe terms over 182 days: **≥ 2.33** for a lone pick, **≥ 2.78** for the better of two.
- **A PASS is not an order to trade real money**: it leads to a decision by the user (sizing,
  execution, a risk engine) — Phase B preconditions stand.

## What the bar can and cannot see (stated before any data)

| true Sharpe | passes stage 2 alone | passes as the better of two |
|---|---|---|
| 0 (no edge) | 5.1% | 2.6% |
| 1.0 | 17.5% | 10.6% |
| 1.5 | 28.3% | 18.7% |
| 2.0 | 40.9% | 29.4% |

(Monte Carlo, 100,000 runs, normal daily returns at 10% volatility.) 26 weeks is short: a real
Sharpe-1.5 book fails stage 2 more often than it passes. That is the price of not crowning luck;
nothing honest makes it faster. Honest prior: the entrants are parts of a blend that failed its
holdout on drawdown, and carry lost on the holdout. Expect most lanes to end flat or killed.

## Readouts

- Every day: weights + scores committed to `logs/tournament/`; `table.md` rewritten on every run.
- **Every Monday** (after Sunday's row is scored, in the paper-test job right after paper #3):
  one Telegram message with the week and the running totals of every lane. The Monday weekly
  review of the daily book runs earlier in the scan keeper, so the table is its own message.
- Immediately: a kill; the stage-1 selection.
