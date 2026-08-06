# Head-to-Head: Mechanical vs Claude

Total evaluated trades: 324
Cost model: 0.170% round-trip (fee 0.055% + slippage 0.030% ×2) + funding; net = gross − cost.

## By source (gross → net of cost)

| source | n | win% | gross exp (R) | **net exp (R)** | net PF |
|---|---|---|---|---|---|
| claude | 286 | 32.9% | -0.112 | **-0.185** | 0.69 |
| mechanical | 38 | 47.4% | -0.044 | **-0.107** | 0.76 |

## By signal backing (gross → net of cost)

| backing | n | win% | gross exp (R) | **net exp (R)** | net PF |
|---|---|---|---|---|---|
| discretionary | 268 | 31.7% | -0.121 | **-0.196** | 0.68 |
| signal_backed | 56 | 48.2% | -0.022 | **-0.082** | 0.81 |

## By source × direction

| source | direction | n | win% | expectancy (R) | profit factor |
|---|---|---|---|---|---|
| claude | long | 185 | 29.2% | -0.182 | 0.70 |
| claude | short | 101 | 39.6% | +0.018 | 1.04 |
| mechanical | short | 38 | 47.4% | -0.044 | 0.89 |

## Mechanical by signal

| signal | n | win% | expectancy (R) | profit factor |
|---|---|---|---|---|
| rsi_rejection_short | 2 | 50.0% | -0.055 | 0.89 |
| trend_pullback_short | 36 | 47.2% | -0.044 | 0.89 |

## Verdict
**Mechanical LEADS on expectancy** (mechanical -0.044R vs claude -0.112R; n=38/286).
⚠️ CONCENTRATION: mechanical book is one-directional (short-only), 36/38 from a single signal — lead is not yet a broad edge. Do NOT flip PRIMARY_SOURCE until both directions and >1 signal have live data.

## Net-of-cost reality check
- Whole book: gross -0.104R → **net -0.176R** (PF 0.70, n=324)
- Mechanical: gross -0.044R → **net -0.107R** (n=38)
- Signal-backed: gross -0.022R → **net -0.082R** (n=56) — the only cut that should be near a real net edge
- **VERDICT: NO edge survives costs yet** — best source net -0.107R (mechanical). Every source is net-negative or breakeven. The gross edge is a cost illusion; the only path to a real edge is cutting the losing longs and/or raising per-trade R by widening targets or entering closer to stop — NOT more rule-tuning.