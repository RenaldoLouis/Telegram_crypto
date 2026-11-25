# Paper tournament — tournament_v1 (2026-11-25 09:14 UTC)

Pre-registration: `logs/backtest_reports/prereg_tournament_20261026.md` · rules_hash `ce6337a4bd97ea7c` · paper only, no orders.

**Bar:** Stage 1 (2026-11-02 → 2027-01-31): an entrant whose drawdown passes 15% is out; at the end at most 2 entrants with net > 0 and a Sharpe above every random control go on. Stage 2 (2027-02-01 → 2027-08-01, fresh data): PASS = daily mean > 0 by a one-sided t-test, Holm at 5% across the picks; drawdown > 15% = FAIL. A PASS is not an order to trade real money.

Week = Mon–Sun ending 2026-11-22. Entrants and controls are at 10% volatility; per-trade lanes are % of the account at 0.5% risk per trade, by signal week, and fill in as 2-day windows close. Sharpe shows after 8 weeks. The leader is not a winner: selection 2027-02-01, confirmation to 2027-08-01.

| lane | role | week | since 11-02 | max DD | Sharpe | weeks green | status |
|---|---|---|---|---|---|---|---|
| 28-day momentum | entrant | +0.76% | +1.82% | 8.38% | — | 2/3 | stage 1 · week 4/13 |
| new-listing short, BTC-hedged | entrant | -1.05% | -0.33% | 2.74% | — | 1/3 | stage 1 · week 4/13 |
| BTC trend, long only | entrant | +0.00% | +0.00% | 0.00% | — | 0/3 | stage 1 · week 4/13 |
| funding carry 7d | entrant | -0.69% | +2.51% | 5.61% | — | 1/3 | stage 1 · week 4/13 |
| random control 1 | control | +0.14% | -6.37% | 7.69% | — | 2/3 | control |
| random control 2 | control | -0.71% | -3.14% | 3.14% | — | 0/3 | control |
| random control 3 | control | +0.25% | -0.71% | 1.19% | — | 1/3 | control |
| paper #3 blend | own clock | -0.32% | +1.48% | 0.82% | — | 1/3 | RUNNING |
| paper #2 momentum k56 | own clock | +1.96% | +11.94% | 0.00% | — | 3/3 | 7/26 weeks |
| paper #2 momentum k91 | own clock | +1.16% | +3.51% | 0.00% | — | 3/3 | 7/26 weeks |
| daily book | own clock | +2.22% | +5.08% | 0.79% | — | 2/3 | 97 trades scored |
| checklist ≥ 5 | own clock | +1.01% | +4.21% | 0.00% | — | 3/3 | 53/30 scored |