# XS momentum ex-carry — forward paper scorecard

## Pre-registered bar

> At n = 26 scored weeks per book: net Sharpe >= 1.0 AND max drawdown <= 20% AND >= 55% weeks positive -> PASS (eligible for small real capital, user decision); net Sharpe < 0.5 -> FAIL (retire); anything between -> extend to n = 52 under the same bar. Kill rule at any n: max drawdown > 25% -> KILLED (retire). The rule set is frozen (rules_hash); any change restarts the clock.

rules_hash `3d7e0eb5d26a0b61` · version `xs_mom_ex_carry_v2.1` · updated 2026-11-23T07:50:07.201279+00:00

## k56 — **BUILDING (7/26)**

| n weeks | cumulative net | ann. Sharpe | max DD | % weeks + | avg turnover | avg funding/wk |
|---|---|---|---|---|---|---|
| 7 | +3.82% | 0.93 | +10.8% | +71% | 0.56 | +0.20% |

**Last 4 weeks**

| week | names | gross | cost | funding | net | flags |
|---|---|---|---|---|---|---|
| 2026-10-26 | 10 | -9.09% | -0.04% | +0.48% | -8.66% | 0 |
| 2026-11-02 | 10 | +7.46% | -0.05% | -0.04% | +7.38% | 0 |
| 2026-11-09 | 8 | +2.71% | -0.05% | -0.06% | +2.61% | 0 |
| 2026-11-16 | 8 | +2.03% | -0.04% | -0.03% | +1.96% | 0 |

## k91 — **BUILDING (7/26)**

| n weeks | cumulative net | ann. Sharpe | max DD | % weeks + | avg turnover | avg funding/wk |
|---|---|---|---|---|---|---|
| 7 | +0.55% | 0.27 | +9.1% | +86% | 0.54 | +0.22% |

**Last 4 weeks**

| week | names | gross | cost | funding | net | flags |
|---|---|---|---|---|---|---|
| 2026-10-26 | 10 | -9.55% | -0.04% | +0.47% | -9.13% | 0 |
| 2026-11-02 | 10 | +0.97% | -0.06% | +0.10% | +1.00% | 0 |
| 2026-11-09 | 8 | +1.35% | -0.05% | +0.04% | +1.35% | 0 |
| 2026-11-16 | 8 | +1.23% | -0.04% | -0.03% | +1.16% | 0 |

_Paper test. Net = Σ w·(close/close − 1) − (0.055% + 0.03%)·turnover + funding received − funding paid. No orders are placed by this project._
