# Pre-registration — forward paper test #3: the 4-sleeve blend at 10% volatility (2026-10-25)

Written 2026-10-25 Asia/Jakarta, BEFORE the first paper position. The book and the bar below are
frozen; a change = a new paper test with a new date (the run refuses if the frozen code changes).

**Why (user, 2026-10-25):** "yes build the paper test" — after the edge search
(`prereg_edge_search_20261025.md`): 114 variants on DISCOVERY found no finalist; by the user's
waiver the best blend went to the locked 2025-01 → 2026-10 holdout and made +35% at 20% vol
(Sharpe 0.89, 14/22 months green) but FAILED its drawdown limit by 0.6 point (25.6% vs 25%). The
holdout is spent, so the only honest next test is forward, on paper.

**Code:** `blend_paper.py` + `.github/workflows/blend_paper.yml` → `logs/blend_paper/`. Paper only:
no order API, no hosted model.

## The book (frozen)

- `edge_search` variant **`volman_combo_4_sleeves`**, exactly as tested: equal-risk blend of
  (1) BTC above its 50-day average → long BTC, vol-managed; (2) funding carry: long the 20% of
  eligible perps whose funding over 7 days was lowest, short the 20% highest, weekly; (3) 28-day
  cross-sectional momentum, top/bottom 10%, weekly; (4) short every new perp from day 1 to day 60
  after listing, 10% of capital each, hedged 1:1 with BTC long. Each sleeve × its frozen
  DISCOVERY 20%-vol scale, averaged; the whole book then scaled by 20% / its trailing-30-day
  realised volatility (cap 2×).
- **Size: × 0.5 of the DISCOVERY 20%-vol scale (1.039297 → 0.5196) = a 10% annual-volatility book.**
- Universe: Bybit linear USDT perps, trading, crypto only (Bybit `symbolType` stock/ETF/commodity/
  forex and pegged tokens excluded), listed ≥ 30 days, 30-day median turnover ≥ $5M.
- Weights decided at every UTC daily close from closed data (the last 200 days, which reproduce
  the full-history weights exactly — checked at three dates, max difference 3e-15); held over the
  next day. Costs: taker 0.055% + slippage 0.03/0.06/0.12% by liquidity on every weight change;
  actual funding. P&L accounting = `edge_search.run_weights` (asserted on every run).
- First decision: the close of **2026-10-25** (computed after 2026-10-26 00:00 UTC). A day the job
  misses is recorded later from data cut at that day (marked late); more than 7 days missed = a
  gap, during which the paper book is flat.

## Readouts

- Every day: weights + score committed to `logs/blend_paper/` (no message).
- **Every Monday:** one Telegram line for the week just completed.
- **Every month end:** the month's result (green / red) in that message.
- 3 months (end of January 2027): interim read, informational only.

## Decision (fixed now)

- **KILL at any time:** max drawdown > 15% (at 10% vol), or 4 red calendar months in a row.
- **After 6 full months (Nov 2026 – Apr 2027):**
  - **PASS** — net > 0, ≥ 4 of 6 months green, Sharpe ≥ 0.75, max drawdown ≤ 12.5%.
  - **FAIL** — net ≤ 0, or Sharpe < 0.25.
  - Otherwise **EXTEND** to 12 months (Nov 2026 – Oct 2027) under the same bar with ≥ 60% of months
    green; then PASS or FAIL.
- A PASS is not an order to trade real money. The book holds ~50–160 positions and changes ~70 of
  them each Monday, which cannot be traded by hand; the next decision would be the user's: a smaller
  hand-tradeable version with its own forward test, or automated execution under Phase B (hard-coded
  risk engine + explicit approval).

## Honest prior

Out of sample the blend's sleeves swapped roles (momentum carried, carry lost) and the 2025 drawdown
ran four months. Expect a coin-flip-to-modest result: positive with ~60% green months is the hope,
a 4-month losing stretch is entirely possible.
