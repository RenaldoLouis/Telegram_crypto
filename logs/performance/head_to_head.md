# Head-to-Head: Mechanical vs Claude

Total evaluated trades: 375
Cost model: 0.170% round-trip (fee 0.055% + slippage 0.030% ×2) + funding; net = gross − cost.

## By source (gross → net of cost)

| source | n | win% | gross exp (R) | **net exp (R)** | net PF |
|---|---|---|---|---|---|
| claude | 299 | 32.1% | -0.129 | **-0.202** | 0.67 |
| mechanical | 41 | 51.2% | -0.001 | **-0.063** | 0.85 |
| watch | 35 | 34.3% | -0.087 | **-0.116** | 0.75 |

## WATCH lane — promotion watch (paper-tracked, NOT in the edge book)

Bar to promote a watch signal into the gated EXECUTE book: **net-of-cost expectancy ≥ +0.050R over ≥ 30 trades** (then still needs a manual both-direction/robustness sanity check).

| watch signal | n | win% | gross exp (R) | **net exp (R)** | status |
|---|---|---|---|---|---|
| (unknown) | 35 | 34.3% | -0.087 | **-0.116** | ✗ below bar |

## By signal backing (gross → net of cost)

| backing | n | win% | gross exp (R) | **net exp (R)** | net PF |
|---|---|---|---|---|---|
| discretionary | 272 | 31.2% | -0.134 | **-0.208** | 0.66 |
| signal_backed | 68 | 47.1% | -0.035 | **-0.093** | 0.80 |

## By source × direction

| source | direction | n | win% | expectancy (R) | profit factor |
|---|---|---|---|---|---|
| claude | long | 186 | 29.0% | -0.186 | 0.69 |
| claude | short | 113 | 37.2% | -0.035 | 0.93 |
| mechanical | short | 41 | 51.2% | -0.001 | 1.00 |

## Mechanical by signal

| signal | n | win% | expectancy (R) | profit factor |
|---|---|---|---|---|
| trend_pullback_short | 39 | 51.3% | +0.002 | 1.01 |
| rsi_rejection_short | 2 | 50.0% | -0.055 | 0.89 |

## Verdict
**Mechanical LEADS on expectancy** (mechanical -0.001R vs claude -0.129R; n=41/299).
⚠️ CONCENTRATION: mechanical book is one-directional (short-only), 39/41 from a single signal — lead is not yet a broad edge. Do NOT flip PRIMARY_SOURCE until both directions and >1 signal have live data.

## Net-of-cost reality check
- Whole book: gross -0.111R → **net -0.179R** (PF 0.69, n=375)
- Mechanical: gross -0.001R → **net -0.063R** (n=41)
- Signal-backed: gross -0.035R → **net -0.093R** (n=68) — the only cut that should be near a real net edge
- **VERDICT: NO edge survives costs yet** — best source net -0.063R (mechanical). Every source is net-negative or breakeven. The gross edge is a cost illusion; the only path to a real edge is cutting the losing longs and/or raising per-trade R by widening targets or entering closer to stop — NOT more rule-tuning.