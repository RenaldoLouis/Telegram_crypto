# Paper tournament — tournament_v1 (2026-10-29 14:30 UTC)

Pre-registration: `logs/backtest_reports/prereg_tournament_20261026.md` · rules_hash `ce6337a4bd97ea7c` · paper only, no orders.

**Bar:** Stage 1 (2026-11-02 → 2027-01-31): an entrant whose drawdown passes 15% is out; at the end at most 2 entrants with net > 0 and a Sharpe above every random control go on. Stage 2 (2027-02-01 → 2027-08-01, fresh data): PASS = daily mean > 0 by a one-sided t-test, Holm at 5% across the picks; drawdown > 15% = FAIL. A PASS is not an order to trade real money.

**SHAKEDOWN — rows before 2026-11-02 are not counted.**

Week = Mon–Sun ending 2026-10-25. Entrants and controls are at 10% volatility; per-trade lanes are % of the account at 0.5% risk per trade, by signal week, and fill in as 2-day windows close. Sharpe shows after 8 weeks. The leader is not a winner: selection 2027-02-01, confirmation to 2027-08-01.

| lane | role | week | since 10-25 | max DD | Sharpe | weeks green | status |
|---|---|---|---|---|---|---|---|
| 28-day momentum | entrant | -0.05% | -0.05% | 0.05% | — | 0/0 | shakedown |
| new-listing short, BTC-hedged | entrant | -0.04% | -0.04% | 0.04% | — | 0/0 | shakedown |
| BTC trend, long only | entrant | +0.00% | +0.00% | 0.00% | — | 0/0 | shakedown |
| funding carry 7d | entrant | -0.08% | -0.08% | 0.08% | — | 0/0 | shakedown |
| random control 1 | control | -0.04% | -0.04% | 0.04% | — | 0/0 | shakedown |
| random control 2 | control | -0.04% | -0.04% | 0.04% | — | 0/0 | shakedown |
| random control 3 | control | -0.04% | -0.04% | 0.04% | — | 0/0 | shakedown |
| paper #3 blend | own clock | -0.06% | -0.06% | 0.06% | — | 0/0 | RUNNING |
| paper #2 momentum k56 | own clock | — | — | — | — | — | 3/26 weeks |
| paper #2 momentum k91 | own clock | — | — | — | — | — | 3/26 weeks |
| daily book | own clock | — | — | — | — | — | 25 trades scored |
| checklist ≥ 5 | own clock | — | — | — | — | — | 14/30 scored |