# Head-to-Head: Mechanical vs Claude

Total evaluated trades: 475
Cost model: 0.170% round-trip (fee 0.055% + slippage 0.030% ×2) + funding; net = gross − cost.

Hit-rate metric (2026-09-23): **profitable%** = share of suggestions whose managed trade (50% at T1 + BE/+0.3R trail) closed green NET of cost; target ≥70% over ≥30 trades with net exp > 0. [lo–hi] = Wilson 95% CI.

## By source (gross → net of cost)

| source | n | win% | **profitable%** | gross exp (R) | **net exp (R)** | net PF |
|---|---|---|---|---|---|---|
| claude | 299 | 32.1% | **39.8% [34–45]** | -0.129 | **-0.202** | 0.67 |
| mechanical | 54 | 53.7% | **61.1% [48–73]** | +0.016 | **-0.044** | 0.89 |
| watch | 122 | 32.8% | **47.5% [39–56]** | -0.171 | **-0.213** | 0.55 |

## WATCH lane — promotion watch (paper-tracked, NOT in the edge book)

Bar to promote a watch signal into the gated EXECUTE book: **profitable% ≥ 70% AND net-of-cost expectancy > 0 over ≥ 30 trades** (then still needs a manual both-direction/robustness sanity check).

| watch signal | n | win% | **profitable%** | gross exp (R) | **net exp (R)** | status |
|---|---|---|---|---|---|---|
| rsi_rejection_short | 19 | 57.9% | **68.4% [46–85]** | +0.202 | **+0.154** | building (19/30) |
| (unknown) | 12 | 50.0% | **66.7% [39–86]** | +0.185 | **+0.169** | building (12/30) |
| trend_pullback_short | 20 | 50.0% | **60.0% [39–78]** | +0.051 | **+0.012** | building (20/30) |
| failed_breakout_short | 26 | 23.1% | **46.2% [29–64]** | -0.280 | **-0.336** | building (26/30) |
| range_reversion_short | 8 | 0.0% | **37.5% [14–69]** | -0.625 | **-0.712** | building (8/30) |
| rsi_bounce_long | 18 | 27.8% | **33.3% [16–56]** | -0.232 | **-0.257** | building (18/30) |
| range_reversion_long | 3 | 0.0% | **33.3%** | -0.667 | **-0.717** | building (3/30) |
| liquidity_sweep_long | 9 | 11.1% | **22.2% [6–55]** | -0.744 | **-0.783** | building (9/30) |
| observation | 7 | 14.3% | **14.3% [3–51]** | -0.401 | **-0.413** | building (7/30) |

## By signal backing (gross → net of cost)

| backing | n | win% | **profitable%** | gross exp (R) | **net exp (R)** | net PF |
|---|---|---|---|---|---|---|
| discretionary | 272 | 31.2% | **39.3% [34–45]** | -0.134 | **-0.208** | 0.66 |
| signal_backed | 81 | 49.4% | **55.6% [45–66]** | -0.019 | **-0.076** | 0.83 |

## By source × direction

| source | direction | n | win% | expectancy (R) | profit factor |
|---|---|---|---|---|---|
| claude | long | 186 | 29.0% | -0.186 | 0.69 |
| claude | short | 113 | 37.2% | -0.035 | 0.93 |
| mechanical | short | 54 | 53.7% | +0.016 | 1.04 |

## Mechanical by signal

| signal | n | win% | **profitable%** | expectancy (R) | **net exp (R)** | profit factor |
|---|---|---|---|---|---|---|
| trend_pullback_short | 52 | 53.8% | **61.5% [48–74]** | +0.018 | **-0.035** | 1.05 |
| rsi_rejection_short | 2 | 50.0% | **50.0%** | -0.055 | **-0.299** | 0.89 |

## Eval engine v2 era (post-fix book — the one the 70% target is judged on)

_No v2-era trades yet (n=0): scored by the v2 engine AND produced by a scan at/after 2026-09-23T07:45:00+00:00 (v13 detector). Pre-fix records above are NOT comparable._

## Verdict
**Mechanical LEADS on expectancy** (mechanical +0.016R vs claude -0.129R; n=54/299).
⚠️ CONCENTRATION: mechanical book is one-directional (short-only), 52/54 from a single signal — lead is not yet a broad edge. Do NOT flip PRIMARY_SOURCE until both directions and >1 signal have live data.

## Net-of-cost reality check
- Whole book: gross -0.124R → **net -0.187R** (PF 0.66, n=475)
- Mechanical: gross +0.016R → **net -0.044R** (n=54)
- Signal-backed: gross -0.019R → **net -0.076R** (n=81) — the only cut that should be near a real net edge
- **VERDICT: NO edge survives costs yet** — best source net -0.044R (mechanical). Every source is net-negative or breakeven. The gross edge is a cost illusion; the only path to a real edge is cutting the losing longs and/or raising per-trade R by widening targets or entering closer to stop — NOT more rule-tuning.