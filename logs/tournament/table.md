# Paper tournament — tournament_v1 (2026-11-02 06:49 UTC)

Pre-registration: `logs/backtest_reports/prereg_tournament_20261026.md` · rules_hash `ce6337a4bd97ea7c` · paper only, no orders.

**Bar:** Stage 1 (2026-11-02 → 2027-01-31): an entrant whose drawdown passes 15% is out; at the end at most 2 entrants with net > 0 and a Sharpe above every random control go on. Stage 2 (2027-02-01 → 2027-08-01, fresh data): PASS = daily mean > 0 by a one-sided t-test, Holm at 5% across the picks; drawdown > 15% = FAIL. A PASS is not an order to trade real money.

**SHAKEDOWN — rows before 2026-11-02 are not counted.**

Week = Mon–Sun ending 2026-11-01. Entrants and controls are at 10% volatility; per-trade lanes are % of the account at 0.5% risk per trade, by signal week, and fill in as 2-day windows close. Sharpe shows after 8 weeks. The leader is not a winner: selection 2027-02-01, confirmation to 2027-08-01.

| lane | role | week | since 10-25 | max DD | Sharpe | weeks green | status |
|---|---|---|---|---|---|---|---|
| 28-day momentum | entrant | +1.09% | +1.04% | 1.85% | — | 1/1 | shakedown |
| new-listing short, BTC-hedged | entrant | +1.09% | +1.04% | 0.45% | — | 1/1 | shakedown |
| BTC trend, long only | entrant | +0.00% | +0.00% | 0.00% | — | 0/1 | shakedown |
| funding carry 7d | entrant | +3.88% | +3.80% | 0.82% | — | 1/1 | shakedown |
| random control 1 | control | +0.40% | +0.36% | 0.22% | — | 1/1 | shakedown |
| random control 2 | control | -1.26% | -1.30% | 1.60% | — | 0/1 | shakedown |
| random control 3 | control | +2.31% | +2.27% | 1.86% | — | 1/1 | shakedown |
| paper #3 blend | own clock | +2.47% | +2.41% | 0.62% | — | 1/1 | RUNNING |
| paper #2 momentum k56 | own clock | -8.66% | -8.66% | 8.66% | — | 0/1 | 4/26 weeks |
| paper #2 momentum k91 | own clock | -9.13% | -9.13% | 9.13% | — | 0/1 | 4/26 weeks |
| daily book | own clock | +0.56% | +0.56% | 0.00% | — | 1/1 | 36 trades scored |
| checklist ≥ 5 | own clock | +1.02% | +1.02% | 0.00% | — | 1/1 | 21/30 scored |