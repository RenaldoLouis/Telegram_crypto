# Head-to-Head: Mechanical vs Claude

Total evaluated trades: 448
Cost model: 0.170% round-trip (fee 0.055% + slippage 0.030% ×2) + funding; net = gross − cost.

## By source (gross → net of cost)

| source | n | win% | gross exp (R) | **net exp (R)** | net PF |
|---|---|---|---|---|---|
| claude | 299 | 32.1% | -0.129 | **-0.202** | 0.67 |
| mechanical | 52 | 53.8% | +0.030 | **-0.030** | 0.92 |
| watch | 97 | 37.1% | -0.067 | **-0.106** | 0.74 |

## WATCH lane — promotion watch (paper-tracked, NOT in the edge book)

Bar to promote a watch signal into the gated EXECUTE book: **net-of-cost expectancy ≥ +0.050R over ≥ 30 trades** (then still needs a manual both-direction/robustness sanity check).

| watch signal | n | win% | gross exp (R) | **net exp (R)** | status |
|---|---|---|---|---|---|
| trend_pullback_short | 14 | 57.1% | +0.299 | **+0.262** | ↑ clears bar, building sample (14/30) |
| (unknown) | 12 | 50.0% | +0.185 | **+0.169** | ↑ clears bar, building sample (12/30) |
| rsi_rejection_short | 19 | 57.9% | +0.202 | **+0.154** | ↑ clears bar, building sample (19/30) |
| range_reversion_short | 2 | 0.0% | +0.000 | **-0.064** | building (2/30) |
| failed_breakout_short | 19 | 26.3% | -0.135 | **-0.200** | building (19/30) |
| rsi_bounce_long | 17 | 29.4% | -0.215 | **-0.240** | building (17/30) |
| observation | 4 | 0.0% | -0.698 | **-0.707** | building (4/30) |
| liquidity_sweep_long | 8 | 12.5% | -0.713 | **-0.750** | building (8/30) |
| range_reversion_long | 2 | 0.0% | -1.000 | **-1.055** | building (2/30) |

## By signal backing (gross → net of cost)

| backing | n | win% | gross exp (R) | **net exp (R)** | net PF |
|---|---|---|---|---|---|
| discretionary | 272 | 31.2% | -0.134 | **-0.208** | 0.66 |
| signal_backed | 79 | 49.4% | -0.010 | **-0.067** | 0.85 |

## By source × direction

| source | direction | n | win% | expectancy (R) | profit factor |
|---|---|---|---|---|---|
| claude | long | 186 | 29.0% | -0.186 | 0.69 |
| claude | short | 113 | 37.2% | -0.035 | 0.93 |
| mechanical | short | 52 | 53.8% | +0.030 | 1.08 |

## Mechanical by signal

| signal | n | win% | expectancy (R) | profit factor |
|---|---|---|---|---|
| trend_pullback_short | 50 | 54.0% | +0.033 | 1.10 |
| rsi_rejection_short | 2 | 50.0% | -0.055 | 0.89 |

## Verdict
**Mechanical LEADS on expectancy** (mechanical +0.030R vs claude -0.129R; n=52/299).
⚠️ CONCENTRATION: mechanical book is one-directional (short-only), 50/52 from a single signal — lead is not yet a broad edge. Do NOT flip PRIMARY_SOURCE until both directions and >1 signal have live data.

## Net-of-cost reality check
- Whole book: gross -0.097R → **net -0.161R** (PF 0.70, n=448)
- Mechanical: gross +0.030R → **net -0.030R** (n=52)
- Signal-backed: gross -0.010R → **net -0.067R** (n=79) — the only cut that should be near a real net edge
- **VERDICT: NO edge survives costs yet** — best source net -0.030R (mechanical). Every source is net-negative or breakeven. The gross edge is a cost illusion; the only path to a real edge is cutting the losing longs and/or raising per-trade R by widening targets or entering closer to stop — NOT more rule-tuning.