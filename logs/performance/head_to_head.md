# Head-to-Head: Mechanical vs Claude

Total evaluated trades: 319
Cost model: 0.170% round-trip (fee 0.055% + slippage 0.030% ×2) + funding; net = gross − cost.

## By source (gross → net of cost)

| source | n | win% | gross exp (R) | **net exp (R)** | net PF |
|---|---|---|---|---|---|
| claude | 286 | 32.9% | -0.112 | **-0.185** | 0.69 |
| mechanical | 33 | 48.5% | +0.010 | **-0.050** | 0.88 |

## By signal backing (gross → net of cost)

| backing | n | win% | gross exp (R) | **net exp (R)** | net PF |
|---|---|---|---|---|---|
| discretionary | 268 | 31.7% | -0.121 | **-0.196** | 0.68 |
| signal_backed | 51 | 49.0% | +0.015 | **-0.043** | 0.90 |

## By source × direction

| source | direction | n | win% | expectancy (R) | profit factor |
|---|---|---|---|---|---|
| claude | long | 185 | 29.2% | -0.182 | 0.70 |
| claude | short | 101 | 39.6% | +0.018 | 1.04 |
| mechanical | short | 33 | 48.5% | +0.010 | 1.03 |

## Mechanical by signal

| signal | n | win% | expectancy (R) | profit factor |
|---|---|---|---|---|
| trend_pullback_short | 31 | 48.4% | +0.015 | 1.04 |
| rsi_rejection_short | 2 | 50.0% | -0.055 | 0.89 |

## Verdict
**Mechanical LEADS on expectancy** (mechanical +0.010R vs claude -0.112R; n=33/286).
⚠️ CONCENTRATION: mechanical book is one-directional (short-only), 31/33 from a single signal — lead is not yet a broad edge. Do NOT flip PRIMARY_SOURCE until both directions and >1 signal have live data.

## Net-of-cost reality check
- Whole book: gross -0.099R → **net -0.171R** (PF 0.70, n=319)
- Mechanical: gross +0.010R → **net -0.050R** (n=33)
- Signal-backed: gross +0.015R → **net -0.043R** (n=51) — the only cut that should be near a real net edge
- **VERDICT: NO edge survives costs yet** — best source net -0.050R (mechanical). Every source is net-negative or breakeven. The gross edge is a cost illusion; the only path to a real edge is cutting the losing longs and/or raising per-trade R by widening targets or entering closer to stop — NOT more rule-tuning.