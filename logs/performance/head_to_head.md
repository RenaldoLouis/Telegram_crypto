# Head-to-Head: Mechanical vs Claude

Total evaluated trades: 306
Cost model: 0.170% round-trip (fee 0.055% + slippage 0.030% ×2) + funding; net = gross − cost.

## By source (gross → net of cost)

| source | n | win% | gross exp (R) | **net exp (R)** | net PF |
|---|---|---|---|---|---|
| claude | 283 | 33.2% | -0.107 | **-0.181** | 0.70 |
| mechanical | 23 | 47.8% | -0.011 | **-0.066** | 0.85 |

## By signal backing (gross → net of cost)

| backing | n | win% | gross exp (R) | **net exp (R)** | net PF |
|---|---|---|---|---|---|
| discretionary | 268 | 31.7% | -0.121 | **-0.196** | 0.68 |
| signal_backed | 38 | 52.6% | +0.049 | **-0.009** | 0.98 |

## By source × direction

| source | direction | n | win% | expectancy (R) | profit factor |
|---|---|---|---|---|---|
| claude | long | 185 | 29.2% | -0.182 | 0.70 |
| claude | short | 98 | 40.8% | +0.036 | 1.08 |
| mechanical | short | 23 | 47.8% | -0.011 | 0.97 |

## Mechanical by signal

| signal | n | win% | expectancy (R) | profit factor |
|---|---|---|---|---|
| rsi_rejection_short | 2 | 50.0% | -0.055 | 0.89 |
| trend_pullback_short | 21 | 47.6% | -0.007 | 0.98 |

## Verdict
**Mechanical LEADS on expectancy** (mechanical -0.011R vs claude -0.107R; n=23/283).
⚠️ CONCENTRATION: mechanical book is one-directional (short-only), 21/23 from a single signal — lead is not yet a broad edge. Do NOT flip PRIMARY_SOURCE until both directions and >1 signal have live data.

## Net-of-cost reality check
- Whole book: gross -0.100R → **net -0.172R** (PF 0.70, n=306)
- Mechanical: gross -0.011R → **net -0.066R** (n=23)
- Signal-backed: gross +0.049R → **net -0.009R** (n=38) — the only cut that should be near a real net edge
- **VERDICT: NO edge survives costs yet** — best source net -0.066R (mechanical). Every source is net-negative or breakeven. The gross edge is a cost illusion; the only path to a real edge is cutting the losing longs and/or raising per-trade R by widening targets or entering closer to stop — NOT more rule-tuning.