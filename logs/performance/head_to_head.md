# Head-to-Head: Mechanical vs Claude

Total evaluated trades: 482
Cost model: 0.170% round-trip (fee 0.055% + slippage 0.030% ×2) + funding; net = gross − cost.

Hit-rate metric (2026-09-23): **profitable%** = share of suggestions whose managed trade (50% at T1 + BE/+0.3R trail) closed green NET of cost; target ≥70% over ≥30 trades with net exp > 0. [lo–hi] = Wilson 95% CI.

## By source (gross → net of cost)

| source | n | win% | **profitable%** | gross exp (R) | **net exp (R)** | net PF |
|---|---|---|---|---|---|---|
| claude | 299 | 32.1% | **39.8% [34–45]** | -0.129 | **-0.202** | 0.67 |
| mechanical | 55 | 54.5% | **61.8% [49–74]** | +0.023 | **-0.036** | 0.90 |
| shadow | 1 | 100.0% | **100.0%** | +1.240 | **+1.205** | ∞ |
| watch | 127 | 33.9% | **48.8% [40–57]** | -0.143 | **-0.184** | 0.61 |

## WATCH lane — promotion watch (paper-tracked, NOT in the edge book)

Bar to promote a watch signal into the gated EXECUTE book: **profitable% ≥ 70% AND net-of-cost expectancy > 0 over ≥ 30 trades** (then still needs a manual both-direction/robustness sanity check).

| watch signal | n | win% | **profitable%** | gross exp (R) | **net exp (R)** | status |
|---|---|---|---|---|---|---|
| rsi_rejection_short | 19 | 57.9% | **68.4% [46–85]** | +0.202 | **+0.154** | building (19/30) |
| (unknown) | 12 | 50.0% | **66.7% [39–86]** | +0.185 | **+0.169** | building (12/30) |
| trend_pullback_short | 20 | 50.0% | **60.0% [39–78]** | +0.051 | **+0.012** | building (20/30) |
| failed_breakout_short | 30 | 30.0% | **53.3% [36–70]** | -0.120 | **-0.172** | ✗ below bar |
| range_reversion_short | 8 | 0.0% | **37.5% [14–69]** | -0.625 | **-0.712** | building (8/30) |
| rsi_bounce_long | 18 | 27.8% | **33.3% [16–56]** | -0.232 | **-0.257** | building (18/30) |
| range_reversion_long | 3 | 0.0% | **33.3%** | -0.667 | **-0.717** | building (3/30) |
| liquidity_sweep_long | 10 | 20.0% | **30.0% [11–60]** | -0.546 | **-0.584** | building (10/30) |
| observation | 8 | 12.5% | **12.5% [2–47]** | -0.476 | **-0.487** | building (8/30) |

## By signal backing (gross → net of cost)

| backing | n | win% | **profitable%** | gross exp (R) | **net exp (R)** | net PF |
|---|---|---|---|---|---|---|
| discretionary | 272 | 31.2% | **39.3% [34–45]** | -0.134 | **-0.208** | 0.66 |
| signal_backed | 82 | 50.0% | **56.1% [45–66]** | -0.013 | **-0.070** | 0.84 |

## By source × direction

| source | direction | n | win% | expectancy (R) | profit factor |
|---|---|---|---|---|---|
| claude | long | 186 | 29.0% | -0.186 | 0.69 |
| claude | short | 113 | 37.2% | -0.035 | 0.93 |
| mechanical | short | 55 | 54.5% | +0.023 | 1.07 |

## Mechanical by signal

| signal | n | win% | **profitable%** | expectancy (R) | **net exp (R)** | profit factor |
|---|---|---|---|---|---|---|
| trend_pullback_short | 53 | 54.7% | **62.3% [49–74]** | +0.026 | **-0.026** | 1.07 |
| rsi_rejection_short | 2 | 50.0% | **50.0%** | -0.055 | **-0.299** | 0.89 |

## Eval engine v2 era (post-fix book — the one the 70% target is judged on)

n=1 v2-scored trades. Pre-fix records are not comparable.

| source | n | **profitable%** | net exp (R) | net PF | status vs target |
|---|---|---|---|---|---|
| shadow | 1 | **100.0%** | +1.205 | ∞ | ↑ clears bar, building sample (1/30) |

| source | signal | n | **profitable%** | net exp (R) | status vs target |
|---|---|---|---|---|---|
| shadow | liquidity_sweep_long | 1 | **100.0%** | +1.205 | ↑ clears bar, building sample (1/30) |

## Verdict
**Mechanical LEADS on expectancy** (mechanical +0.023R vs claude -0.129R; n=55/299).
⚠️ CONCENTRATION: mechanical book is one-directional (short-only), 53/55 from a single signal — lead is not yet a broad edge. Do NOT flip PRIMARY_SOURCE until both directions and >1 signal have live data.

## Net-of-cost reality check
- Whole book: gross -0.113R → **net -0.175R** (PF 0.68, n=482)
- Mechanical: gross +0.023R → **net -0.036R** (n=55)
- Signal-backed: gross -0.013R → **net -0.070R** (n=82) — the only cut that should be near a real net edge
- **VERDICT: an edge SURVIVES costs** — best source net +1.205R (shadow). Net-positive on a real cost model — this is tradeable-grade, keep pushing sample.