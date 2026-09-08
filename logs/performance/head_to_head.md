# Head-to-Head: Mechanical vs Claude

Total evaluated trades: 412
Cost model: 0.170% round-trip (fee 0.055% + slippage 0.030% ×2) + funding; net = gross − cost.

## By source (gross → net of cost)

| source | n | win% | gross exp (R) | **net exp (R)** | net PF |
|---|---|---|---|---|---|
| claude | 299 | 32.1% | -0.129 | **-0.202** | 0.67 |
| mechanical | 45 | 51.1% | +0.005 | **-0.056** | 0.87 |
| watch | 68 | 39.7% | -0.057 | **-0.092** | 0.77 |

## WATCH lane — promotion watch (paper-tracked, NOT in the edge book)

Bar to promote a watch signal into the gated EXECUTE book: **net-of-cost expectancy ≥ +0.050R over ≥ 30 trades** (then still needs a manual both-direction/robustness sanity check).

| watch signal | n | win% | gross exp (R) | **net exp (R)** | status |
|---|---|---|---|---|---|
| (unknown) | 68 | 39.7% | -0.057 | **-0.092** | ✗ below bar |

## By signal backing (gross → net of cost)

| backing | n | win% | gross exp (R) | **net exp (R)** | net PF |
|---|---|---|---|---|---|
| discretionary | 272 | 31.2% | -0.134 | **-0.208** | 0.66 |
| signal_backed | 72 | 47.2% | -0.029 | **-0.087** | 0.81 |

## By source × direction

| source | direction | n | win% | expectancy (R) | profit factor |
|---|---|---|---|---|---|
| claude | long | 186 | 29.0% | -0.186 | 0.69 |
| claude | short | 113 | 37.2% | -0.035 | 0.93 |
| mechanical | short | 45 | 51.1% | +0.005 | 1.01 |

## Mechanical by signal

| signal | n | win% | expectancy (R) | profit factor |
|---|---|---|---|---|
| trend_pullback_short | 43 | 51.2% | +0.008 | 1.02 |
| rsi_rejection_short | 2 | 50.0% | -0.055 | 0.89 |

## Verdict
**Mechanical LEADS on expectancy** (mechanical +0.005R vs claude -0.129R; n=45/299).
⚠️ CONCENTRATION: mechanical book is one-directional (short-only), 43/45 from a single signal — lead is not yet a broad edge. Do NOT flip PRIMARY_SOURCE until both directions and >1 signal have live data.

## Net-of-cost reality check
- Whole book: gross -0.103R → **net -0.168R** (PF 0.70, n=412)
- Mechanical: gross +0.005R → **net -0.056R** (n=45)
- Signal-backed: gross -0.029R → **net -0.087R** (n=72) — the only cut that should be near a real net edge
- **VERDICT: NO edge survives costs yet** — best source net -0.056R (mechanical). Every source is net-negative or breakeven. The gross edge is a cost illusion; the only path to a real edge is cutting the losing longs and/or raising per-trade R by widening targets or entering closer to stop — NOT more rule-tuning.