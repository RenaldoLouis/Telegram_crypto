# Head-to-Head: Mechanical vs Claude

Total evaluated trades: 310
Cost model: 0.170% round-trip (fee 0.055% + slippage 0.030% ×2) + funding; net = gross − cost.

## By source (gross → net of cost)

| source | n | win% | gross exp (R) | **net exp (R)** | net PF |
|---|---|---|---|---|---|
| claude | 283 | 33.2% | -0.107 | **-0.181** | 0.70 |
| mechanical | 27 | 51.9% | +0.009 | **-0.043** | 0.88 |

## By signal backing (gross → net of cost)

| backing | n | win% | gross exp (R) | **net exp (R)** | net PF |
|---|---|---|---|---|---|
| discretionary | 268 | 31.7% | -0.121 | **-0.196** | 0.68 |
| signal_backed | 42 | 54.8% | +0.057 | **+0.001** | 1.00 |

## By source × direction

| source | direction | n | win% | expectancy (R) | profit factor |
|---|---|---|---|---|---|
| claude | long | 185 | 29.2% | -0.182 | 0.70 |
| claude | short | 98 | 40.8% | +0.036 | 1.08 |
| mechanical | short | 27 | 51.9% | +0.009 | 1.03 |

## Mechanical by signal

| signal | n | win% | expectancy (R) | profit factor |
|---|---|---|---|---|
| trend_pullback_short | 25 | 52.0% | +0.014 | 1.04 |
| rsi_rejection_short | 2 | 50.0% | -0.055 | 0.89 |

## Verdict
**Mechanical LEADS on expectancy** (mechanical +0.009R vs claude -0.107R; n=27/283).
⚠️ CONCENTRATION: mechanical book is one-directional (short-only), 25/27 from a single signal — lead is not yet a broad edge. Do NOT flip PRIMARY_SOURCE until both directions and >1 signal have live data.

## Net-of-cost reality check
- Whole book: gross -0.097R → **net -0.169R** (PF 0.71, n=310)
- Mechanical: gross +0.009R → **net -0.043R** (n=27)
- Signal-backed: gross +0.057R → **net +0.001R** (n=42) — the only cut that should be near a real net edge
- **VERDICT: NO edge survives costs yet** — best source net -0.043R (mechanical). Every source is net-negative or breakeven. The gross edge is a cost illusion; the only path to a real edge is cutting the losing longs and/or raising per-trade R by widening targets or entering closer to stop — NOT more rule-tuning.