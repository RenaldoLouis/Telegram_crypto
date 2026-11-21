# Paper tournament — tournament_v1 (2026-11-21 15:28 UTC)

Pre-registration: `logs/backtest_reports/prereg_tournament_20261026.md` · rules_hash `ce6337a4bd97ea7c` · paper only, no orders.

**Bar:** Stage 1 (2026-11-02 → 2027-01-31): an entrant whose drawdown passes 15% is out; at the end at most 2 entrants with net > 0 and a Sharpe above every random control go on. Stage 2 (2027-02-01 → 2027-08-01, fresh data): PASS = daily mean > 0 by a one-sided t-test, Holm at 5% across the picks; drawdown > 15% = FAIL. A PASS is not an order to trade real money.

Week = Mon–Sun ending 2026-11-15. Entrants and controls are at 10% volatility; per-trade lanes are % of the account at 0.5% risk per trade, by signal week, and fill in as 2-day windows close. Sharpe shows after 8 weeks. The leader is not a winner: selection 2027-02-01, confirmation to 2027-08-01.

| lane | role | week | since 11-02 | max DD | Sharpe | weeks green | status |
|---|---|---|---|---|---|---|---|
| 28-day momentum | entrant | -6.70% | +1.06% | 8.38% | — | 1/2 | stage 1 · week 3/13 |
| new-listing short, BTC-hedged | entrant | -0.58% | +0.72% | 0.59% | — | 1/2 | stage 1 · week 3/13 |
| BTC trend, long only | entrant | +0.00% | +0.00% | 0.00% | — | 0/2 | stage 1 · week 3/13 |
| funding carry 7d | entrant | +7.24% | +3.20% | 5.61% | — | 1/2 | stage 1 · week 3/13 |
| random control 1 | control | -6.76% | -6.51% | 7.69% | — | 1/2 | control |
| random control 2 | control | -1.45% | -2.44% | 2.44% | — | 0/2 | control |
| random control 3 | control | -0.32% | -0.96% | 0.99% | — | 0/2 | control |
| paper #3 blend | own clock | -0.01% | +1.80% | 0.44% | — | 1/2 | RUNNING |
| paper #2 momentum k56 | own clock | +2.61% | +9.98% | 0.00% | — | 2/2 | 6/26 weeks |
| paper #2 momentum k91 | own clock | +1.35% | +2.35% | 0.00% | — | 2/2 | 6/26 weeks |
| daily book | own clock | -0.79% | +2.86% | 0.79% | — | 1/2 | 88 trades scored |
| checklist ≥ 5 | own clock | +2.30% | +3.20% | 0.00% | — | 2/2 | 51/30 scored |