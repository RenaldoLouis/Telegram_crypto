# Pre-registration — `failed_breakout_short` forward-record check (2026-11-02)

Written before any of the numbers below were computed. Research only: no rule, gate or pick changes.

## Why

`head_to_head.md` (2026-11-02) marks `failed_breakout_short` 4h "PROMOTABLE": 81 v2-era forward trades
(shadow + watch), 70.4% profitable, net +0.275R, PF 2.03, 60% of weeks green. Against it: the
2026-10-19 replication on the unified engine over the same weeks gave 51.1% / −0.067R (n = 45,
30 fixed symbols) while the live record was 67.5% / +0.19R (n = 40); its 2026-09-23 backtest TEST was
54.5% / −0.12R; the 2026-10-16 monthly review asked for replication (R-2026-10-16-1). Shorts in general
did well in these weeks.

## Data

- **Live record:** every `failed_breakout_short` eval row with `eval_engine = v2_market_open`,
  `status = evaluated` (duplicates excluded), any source. Signal bar = run timestamp floored to the 4h close.
- **Backtest:** `unified_backtest.build_trades` + `sim_trade` (limit_open, the live trade model), signal
  `failed_breakout_short`, 4h, on **the symbols the live record traded**, signal bars inside the live
  record's span. Fresh Bybit klines.

## Questions and verdict rules (fixed now)

**Q1 — Independent bets.** Trades whose signal bars share a 4h close are one bet (mean net R of the
group). HOLDS if mean net R per bet > 0 with the 95% bootstrap CI lower bound > 0 **and** ≥ 55% of
ISO weeks green.

**Q2 — Random entries (the quality yardstick's "beats random").** For each live trade: shorts on the
same coin at every other 4h close within ±3.5 days of the signal bar, with the same stop distance in
ATR multiples, T1 0.75R / T2 2R, same management and limit_open entry, same engine. HOLDS if the live
trades' mean net R (re-simulated on the same engine) exceeds the matched random mean by **≥ +0.05R**
and the bootstrap CI of the difference (resampling independent bets) has its lower bound > 0.

**Q3 — Parity.** Live trades matched to a backtest trade on the same symbol + signal bar: ≥ 90% of
matched pairs within 0.05R net. Unmatched live trades and backtest-only trades are listed with the
reason (symbol/bar not in the backtest, dedup, warm-up). A parity failure is reported as a defect,
not as evidence for or against the rule.

**Q4 — Selection.** Backtest trades on the live symbols in the live span that the live system did NOT
take vs those it took. Descriptive (explains the 10-19 gap); no verdict.

**Q5 — History.** `failed_breakout_short` 4h in the existing 365-day unified backtest
(`unified_20261021_365d_trades.json`) by month. Descriptive.

## Overall

- **WORTH A FORWARD CLOCK** only if Q1 and Q2 both HOLD and Q3 shows parity. Then a separate
  pre-registration fixes the forward bar before any further data.
- Otherwise **NOT AN EDGE** (the forward record is market direction and/or clustering): no change,
  and R-2026-10-16-1 is graded refuted.
