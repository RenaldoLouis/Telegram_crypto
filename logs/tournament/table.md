# Paper tournament — tournament_v1 (2026-11-09 00:11 UTC)

Pre-registration: `logs/backtest_reports/prereg_tournament_20261026.md` · rules_hash `ce6337a4bd97ea7c` · paper only, no orders.

**Bar:** Stage 1 (2026-11-02 → 2027-01-31): an entrant whose drawdown passes 15% is out; at the end at most 2 entrants with net > 0 and a Sharpe above every random control go on. Stage 2 (2027-02-01 → 2027-08-01, fresh data): PASS = daily mean > 0 by a one-sided t-test, Holm at 5% across the picks; drawdown > 15% = FAIL. A PASS is not an order to trade real money.

Week = Mon–Sun ending 2026-11-08. Entrants and controls are at 10% volatility; per-trade lanes are % of the account at 0.5% risk per trade, by signal week, and fill in as 2-day windows close. Sharpe shows after 8 weeks. The leader is not a winner: selection 2027-02-01, confirmation to 2027-08-01.

| lane | role | week | since 11-02 | max DD | Sharpe | weeks green | status |
|---|---|---|---|---|---|---|---|
| 28-day momentum | entrant | +7.76% | +7.76% | 2.14% | — | 1/1 | stage 1 · week 1/13 |
| new-listing short, BTC-hedged | entrant | +1.30% | +1.30% | 0.47% | — | 1/1 | stage 1 · week 1/13 |
| BTC trend, long only | entrant | +0.00% | +0.00% | 0.00% | — | 0/1 | stage 1 · week 1/13 |
| funding carry 7d | entrant | -4.04% | -4.04% | 4.79% | — | 0/1 | stage 1 · week 1/13 |
| random control 1 | control | +0.25% | +0.25% | 0.42% | — | 1/1 | control |
| random control 2 | control | -0.99% | -0.99% | 0.99% | — | 0/1 | control |
| random control 3 | control | -0.64% | -0.64% | 0.66% | — | 0/1 | control |
| paper #3 blend | own clock | +1.80% | +1.80% | 0.25% | — | 1/1 | RUNNING |
| paper #2 momentum k56 | own clock | — | — | — | — | — | 4/26 weeks |
| paper #2 momentum k91 | own clock | — | — | — | — | — | 4/26 weeks |
| daily book | own clock | +3.47% | +3.47% | 0.00% | — | 1/1 | 55 trades scored |
| checklist ≥ 5 | own clock | +0.39% | +0.39% | 0.00% | — | 1/1 | 33/30 scored |