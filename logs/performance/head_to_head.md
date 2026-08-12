# Head-to-Head: Mechanical vs Claude

Total evaluated trades: 336
Cost model: 0.170% round-trip (fee 0.055% + slippage 0.030% ×2) + funding; net = gross − cost.

## By source (gross → net of cost)

| source | n | win% | gross exp (R) | **net exp (R)** | net PF |
|---|---|---|---|---|---|
| claude | 296 | 32.4% | -0.121 | **-0.193** | 0.68 |
| mechanical | 40 | 50.0% | -0.015 | **-0.079** | 0.81 |

## By signal backing (gross → net of cost)

| backing | n | win% | gross exp (R) | **net exp (R)** | net PF |
|---|---|---|---|---|---|
| discretionary | 270 | 31.5% | -0.127 | **-0.202** | 0.67 |
| signal_backed | 66 | 47.0% | -0.030 | **-0.090** | 0.80 |

## By source × direction

| source | direction | n | win% | expectancy (R) | profit factor |
|---|---|---|---|---|---|
| claude | long | 186 | 29.0% | -0.186 | 0.69 |
| claude | short | 110 | 38.2% | -0.009 | 0.98 |
| mechanical | short | 40 | 50.0% | -0.015 | 0.96 |

## Mechanical by signal

| signal | n | win% | expectancy (R) | profit factor |
|---|---|---|---|---|
| rsi_rejection_short | 2 | 50.0% | -0.055 | 0.89 |
| trend_pullback_short | 38 | 50.0% | -0.013 | 0.96 |

## Verdict
**Mechanical LEADS on expectancy** (mechanical -0.015R vs claude -0.121R; n=40/296).
⚠️ CONCENTRATION: mechanical book is one-directional (short-only), 38/40 from a single signal — lead is not yet a broad edge. Do NOT flip PRIMARY_SOURCE until both directions and >1 signal have live data.

## Net-of-cost reality check
- Whole book: gross -0.108R → **net -0.180R** (PF 0.69, n=336)
- Mechanical: gross -0.015R → **net -0.079R** (n=40)
- Signal-backed: gross -0.030R → **net -0.090R** (n=66) — the only cut that should be near a real net edge
- **VERDICT: NO edge survives costs yet** — best source net -0.079R (mechanical). Every source is net-negative or breakeven. The gross edge is a cost illusion; the only path to a real edge is cutting the losing longs and/or raising per-trade R by widening targets or entering closer to stop — NOT more rule-tuning.