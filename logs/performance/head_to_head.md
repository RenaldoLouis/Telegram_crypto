# Head-to-Head: Mechanical vs Claude

Total evaluated trades: 331
Cost model: 0.170% round-trip (fee 0.055% + slippage 0.030% ×2) + funding; net = gross − cost.

## By source (gross → net of cost)

| source | n | win% | gross exp (R) | **net exp (R)** | net PF |
|---|---|---|---|---|---|
| claude | 292 | 32.5% | -0.119 | **-0.192** | 0.68 |
| mechanical | 39 | 48.7% | -0.036 | **-0.098** | 0.77 |

## By signal backing (gross → net of cost)

| backing | n | win% | gross exp (R) | **net exp (R)** | net PF |
|---|---|---|---|---|---|
| discretionary | 269 | 31.6% | -0.124 | **-0.199** | 0.67 |
| signal_backed | 62 | 46.8% | -0.043 | **-0.103** | 0.77 |

## By source × direction

| source | direction | n | win% | expectancy (R) | profit factor |
|---|---|---|---|---|---|
| claude | long | 185 | 29.2% | -0.182 | 0.70 |
| claude | short | 107 | 38.3% | -0.009 | 0.98 |
| mechanical | short | 39 | 48.7% | -0.036 | 0.91 |

## Mechanical by signal

| signal | n | win% | expectancy (R) | profit factor |
|---|---|---|---|---|
| rsi_rejection_short | 2 | 50.0% | -0.055 | 0.89 |
| trend_pullback_short | 37 | 48.6% | -0.035 | 0.91 |

## Verdict
**Mechanical LEADS on expectancy** (mechanical -0.036R vs claude -0.119R; n=39/292).
⚠️ CONCENTRATION: mechanical book is one-directional (short-only), 37/39 from a single signal — lead is not yet a broad edge. Do NOT flip PRIMARY_SOURCE until both directions and >1 signal have live data.

## Net-of-cost reality check
- Whole book: gross -0.109R → **net -0.181R** (PF 0.69, n=331)
- Mechanical: gross -0.036R → **net -0.098R** (n=39)
- Signal-backed: gross -0.043R → **net -0.103R** (n=62) — the only cut that should be near a real net edge
- **VERDICT: NO edge survives costs yet** — best source net -0.098R (mechanical). Every source is net-negative or breakeven. The gross edge is a cost illusion; the only path to a real edge is cutting the losing longs and/or raising per-trade R by widening targets or entering closer to stop — NOT more rule-tuning.