# XS momentum ex-carry — forward paper scorecard

## Pre-registered bar

> At n = 26 scored weeks per book: net Sharpe >= 1.0 AND max drawdown <= 20% AND >= 55% weeks positive -> PASS (eligible for small real capital, user decision); net Sharpe < 0.5 -> FAIL (retire); anything between -> extend to n = 52 under the same bar. Kill rule at any n: max drawdown > 25% -> KILLED (retire). The rule set is frozen (rules_hash); any change restarts the clock.

rules_hash `3d7e0eb5d26a0b61` · version `xs_mom_ex_carry_v2.1` · updated 2026-10-26T04:56:14.239790+00:00

## k56 — **BUILDING (3/26)**

| n weeks | cumulative net | ann. Sharpe | max DD | % weeks + | avg turnover | avg funding/wk |
|---|---|---|---|---|---|---|
| 3 | +1.18% | 1.10 | +2.3% | +67% | 0.62 | +0.35% |

**Last 4 weeks**

| week | names | gross | cost | funding | net | flags |
|---|---|---|---|---|---|---|
| 2026-10-05 | 12 | +3.22% | -0.05% | -0.01% | +3.17% | 0 |
| 2026-10-12 | 12 | +0.39% | -0.05% | +0.05% | +0.40% | 0 |
| 2026-10-19 | 12 | -3.27% | -0.06% | +1.01% | -2.31% | 0 |

## k91 — **BUILDING (3/26)**

| n weeks | cumulative net | ann. Sharpe | max DD | % weeks + | avg turnover | avg funding/wk |
|---|---|---|---|---|---|---|
| 3 | +6.85% | 11.16 | +0.0% | +100% | 0.52 | +0.33% |

**Last 4 weeks**

| week | names | gross | cost | funding | net | flags |
|---|---|---|---|---|---|---|
| 2026-10-05 | 12 | +0.77% | -0.05% | +0.00% | +0.72% | 0 |
| 2026-10-12 | 12 | +3.67% | -0.05% | -0.01% | +3.60% | 0 |
| 2026-10-19 | 10 | +1.42% | -0.03% | +1.00% | +2.40% | 0 |

_Paper test. Net = Σ w·(close/close − 1) − (0.055% + 0.03%)·turnover + funding received − funding paid. No orders are placed by this project._
