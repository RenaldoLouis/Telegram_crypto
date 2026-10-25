# Pre-registration — daily trader's playbook study (2026-10-25)

Written 2026-10-25 Asia/Jakarta, BEFORE any result of this study existed. Nothing below may
change after the run; a change = a new study with a new date.

**Question (user, 2026-10-25):** "forget what we have built … you are a daily trader and the
goal is profit, monthly — backtest multiple strategies, ideas and setups on old Bybit data and
see which one is profitable." So this study ignores the screener's signal rules, its trade shape
(T1/T2, 2-day window) and its 70% / quality bars, and asks one question per strategy: **does it
make money after costs, month after month?**

**Code:** `playbook_study.py` → `logs/backtest_reports/playbook_<date>.md` (+ `_trades.json`).
Research only: no live change, no order API, no hosted model.

## Data (fixed before the run)

- The project's 15 majors (ADA, XRP, SOL, BTC, ETH, DOGE, SUI, XLM, ENA, HBAR, TRX, NEAR, OP,
  ARB, INJ), Bybit USDT perps, **4h klines 2023-10-20 → 2026-10-19** (3 years, zero gaps) and
  actual Bybit funding history — the cache written by `trend_study.py` on 2026-10-19. ENA starts
  2024-04-02. Daily bars are built from the 4h bars (UTC day = six 4h bars).
- Why this set: the VPN is down on 2026-10-25 so no fresh fetch; these are the only 3-year
  series on disk. Survivorship caveat: all 15 are coins that survived to today.
- **TRAIN** = the first 60% of the days (2023-10-20 → ≈ 2025-08-07), **TEST** = the last 40%
  (≈ 2025-08-07 → 2026-10-19, ≈ 14 months). Only C3 fits anything, and only on TRAIN.

## Costs and sizing (all strategies)

- Taker 0.055% + slippage 0.03% on every entry and exit (0.17% round trip), market orders
  everywhere (conservative for the limit-style exits).
- Actual Bybit funding paid/received on every settlement a position is held over.
- Event strategies: each position = 1/15 of capital (C4: 1/2 each for BTC and ETH). Position
  strategies: the weights stated per strategy, gross ≤ 1. No leverage in the unit result.
- P&L is marked to market on every 4h close (fixed notional from the entry), summed per UTC day.
- Comparable view: each strategy is also scaled to 20% annual volatility with the scale fixed on
  TRAIN (capped at 5×); TEST return and drawdown are reported at that scale.

## The strategies (11 in the family; parameters are textbook defaults, not fitted)

**A — Trend (hold days to weeks)**
- **A1 Time-series momentum, long/short.** Each UTC day: every coin long if its 30-day return
  > 0, short if < 0; inverse-volatility weights (30-day stdev of daily returns), Σ|w| = 1.
- **A2 Time-series momentum, long/flat.** Same, shorts replaced by cash.
- **A3 Turtle System 1.** Daily close above the prior 20-day high → long at the next open (below
  the 20-day low → short). Stop 2 × ATR(20) checked on 4h bars; exit at the next open after a
  daily close beyond the 10-day opposite channel. One position per coin. (The "skip after a
  winner" filter is not used.)

**B — Mean reversion (hold 1–10 days)**
- **B1 Connors RSI(2).** Long when RSI(2) < 10 and close > SMA(200); short when RSI(2) > 90 and
  close < SMA(200); entry next open; exit at the next open after a close beyond SMA(5), or after
  10 days. No stop (as published).
- **B2 Cross-sectional daily reversal.** Each UTC day: long the 3 worst coins of the previous
  day, short the 3 best, 1/6 each, hold one day.
- **B3 Fade extreme 4h moves.** 4h return z-score (vs the prior 180 bars' stdev) ≤ −3 → long at
  the next 4h open; ≥ +3 → short; exit 24h later. One position per coin.

**C — Intraday and calendar**
- **C1 Volatility breakout (Larry Williams, k = 0.5).** Each UTC day: long when price trades
  above open + 0.5 × yesterday's range, short below open − 0.5 × range; first trigger only,
  filled at the trigger (or the 4h open if it gapped through); exit at the day's close. A 4h
  bar that hits both triggers → the day is skipped (order unknown).
- **C2 Opening-range breakout.** Range = the first 4h bar of the UTC day (00:00–04:00). First
  later 4h bar trading above the range → long at the range high (below → short at the low),
  stop at the other side of the range, exit at the day's close. Both sides in one bar → skip.
- **C3 Session seasonality.** On TRAIN only: mean equal-weight 15-coin return of each 4h
  session (00, 04, 08, 12, 16, 20 UTC). The best session with t ≥ 2 → long the basket during
  that session; the worst with t ≤ −2 → short it. Judged on TEST only. No session clears
  |t| ≥ 2 → NO.
- **C4 CME-gap fill (BTC, ETH).** Reference = price at Friday 20:00 UTC; at Monday 00:00 UTC a
  gap ≥ 1% from it → trade toward it: target = the Friday price, stop the same distance on the
  other side (1:1), exit at Friday 20:00 UTC at the latest. Target and stop in one 4h bar →
  counted as the stop.

**D — Positioning**
- **D1 Funding extremes, contrarian.** At each settlement: average of the last 3 funding rates
  ≥ its trailing-90-day 95th percentile and > 0.02% → short at the next 4h open; ≤ the 5th
  percentile and < 0 → long. Hold 72h, no stop. One position per coin.

**Reference lines (outside the family, never a PASS):** BTC buy-and-hold; equal-weight 15-coin
buy-and-hold; delta-neutral carry on BTC + ETH (long spot / short perp while the trailing 7-day
funding is positive; spot taker 0.10% + 0.03%; basis changes ignored — a stated simplification).
Single-coin trend following with a chandelier stop is NOT repeated: `trend_study.py` (2026-10-19)
→ CANDIDATE (weak, random entries matched it). Weekly cross-sectional momentum is NOT repeated:
it is forward paper test #2.

## Controls

- Event strategies (A3, B1, B3, C1, C2, C4, D1): 20 random-entry runs per strategy — every real
  trade is replaced by one at a random 4h bar of the same coin in the same half, same side, same
  exit rule (same stop/target distance where the rule has one).
- Position strategies (A1, A2, B2, C3): alpha = intercept of the TEST daily returns regressed on
  the equal-weight 15-coin buy-and-hold.

## Bar (per strategy, fixed now)

- **PASS** — all of:
  1. net return > 0 on TRAIN **and** on TEST (C3: TEST only);
  2. TEST Sharpe (daily, annualised) ≥ 1.0;
  3. **TEST ≥ 60% of calendar months green** (the user's goal: profitable month after month);
  4. TEST max drawdown ≤ 25% at the 20%-volatility scale;
  5. beats chance: event strategies — TEST Sharpe above ≥ 18 of the 20 random-entry runs;
     position strategies — TEST alpha > 0.
  → candidate for a forward paper test with its own pre-registration. Never real money from a
  backtest alone.
- **CANDIDATE** — condition 1 holds and TEST ≥ 55% of months green, but 2, 4 or 5 fails.
- **NO** — anything else.

**Multiple testing:** 11 strategies. Under no edge, each has roughly a 5% chance of a PASS
(both halves positive × a 14-month Sharpe ≥ 1 × the random control), so about 0.5 false PASSes
are expected. One PASS is therefore a reason for a forward paper test, not proof.

**Informational:** per-year net table, long vs short, win rate, profit factor, trades per month,
the monthly P&L table of anything that is PASS or CANDIDATE, correlation between survivors.

## Honest prior (written before the run)

The screener's own history says single-coin patterns rarely survive costs on these coins. Expected:
A1/A2 positive on TRAIN (the 2023–24 bull) and weak or negative on TEST (choppier); A2 mostly
beta. C1/C2/C3 pay 0.17% per trade on a daily hold and are likely eaten by costs. B2 and D1 have
some literature support but small effects. C4 is trader lore with no published support. Most
likely outcome: zero or one PASS.
