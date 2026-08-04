# Head-to-Head: Mechanical vs Claude

Total evaluated trades: 316
Cost model: 0.170% round-trip (fee 0.055% + slippage 0.030% ×2) + funding; net = gross − cost.

## By source (gross → net of cost)

| source | n | win% | gross exp (R) | **net exp (R)** | net PF |
|---|---|---|---|---|---|
| claude | 286 | 32.9% | -0.112 | **-0.185** | 0.69 |
| mechanical | 30 | 50.0% | +0.007 | **-0.048** | 0.88 |

## By signal backing (gross → net of cost)

| backing | n | win% | gross exp (R) | **net exp (R)** | net PF |
|---|---|---|---|---|---|
| discretionary | 268 | 31.7% | -0.121 | **-0.196** | 0.68 |
| signal_backed | 48 | 50.0% | +0.013 | **-0.041** | 0.90 |

## By source × direction

| source | direction | n | win% | expectancy (R) | profit factor |
|---|---|---|---|---|---|
| claude | long | 185 | 29.2% | -0.182 | 0.70 |
| claude | short | 101 | 39.6% | +0.018 | 1.04 |
| mechanical | short | 30 | 50.0% | +0.007 | 1.02 |

## Mechanical by signal

| signal | n | win% | expectancy (R) | profit factor |
|---|---|---|---|---|
| trend_pullback_short | 28 | 50.0% | +0.011 | 1.03 |
| rsi_rejection_short | 2 | 50.0% | -0.055 | 0.89 |

## Verdict
**Mechanical LEADS on expectancy** (mechanical +0.007R vs claude -0.112R; n=30/286).
⚠️ CONCENTRATION: mechanical book is one-directional (short-only), 28/30 from a single signal — lead is not yet a broad edge. Do NOT flip PRIMARY_SOURCE until both directions and >1 signal have live data.

## Net-of-cost reality check
- Whole book: gross -0.100R → **net -0.172R** (PF 0.70, n=316)
- Mechanical: gross +0.007R → **net -0.048R** (n=30)
- Signal-backed: gross +0.013R → **net -0.041R** (n=48) — the only cut that should be near a real net edge
- **VERDICT: NO edge survives costs yet** — best source net -0.048R (mechanical). Every source is net-negative or breakeven. The gross edge is a cost illusion; the only path to a real edge is cutting the losing longs and/or raising per-trade R by widening targets or entering closer to stop — NOT more rule-tuning.