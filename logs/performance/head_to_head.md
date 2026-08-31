# Head-to-Head: Mechanical vs Claude

Total evaluated trades: 382
Cost model: 0.170% round-trip (fee 0.055% + slippage 0.030% ×2) + funding; net = gross − cost.

## By source (gross → net of cost)

| source | n | win% | gross exp (R) | **net exp (R)** | net PF |
|---|---|---|---|---|---|
| claude | 299 | 32.1% | -0.129 | **-0.202** | 0.67 |
| mechanical | 43 | 51.2% | -0.019 | **-0.080** | 0.81 |
| watch | 40 | 37.5% | -0.036 | **-0.066** | 0.85 |

## WATCH lane — promotion watch (paper-tracked, NOT in the edge book)

Bar to promote a watch signal into the gated EXECUTE book: **net-of-cost expectancy ≥ +0.050R over ≥ 30 trades** (then still needs a manual both-direction/robustness sanity check).

| watch signal | n | win% | gross exp (R) | **net exp (R)** | status |
|---|---|---|---|---|---|
| (unknown) | 40 | 37.5% | -0.036 | **-0.066** | ✗ below bar |

## By signal backing (gross → net of cost)

| backing | n | win% | gross exp (R) | **net exp (R)** | net PF |
|---|---|---|---|---|---|
| discretionary | 272 | 31.2% | -0.134 | **-0.208** | 0.66 |
| signal_backed | 70 | 47.1% | -0.045 | **-0.103** | 0.78 |

## By source × direction

| source | direction | n | win% | expectancy (R) | profit factor |
|---|---|---|---|---|---|
| claude | long | 186 | 29.0% | -0.186 | 0.69 |
| claude | short | 113 | 37.2% | -0.035 | 0.93 |
| mechanical | short | 43 | 51.2% | -0.019 | 0.95 |

## Mechanical by signal

| signal | n | win% | expectancy (R) | profit factor |
|---|---|---|---|---|
| rsi_rejection_short | 2 | 50.0% | -0.055 | 0.89 |
| trend_pullback_short | 41 | 51.2% | -0.017 | 0.95 |

## Verdict
**Mechanical LEADS on expectancy** (mechanical -0.019R vs claude -0.129R; n=43/299).
⚠️ CONCENTRATION: mechanical book is one-directional (short-only), 41/43 from a single signal — lead is not yet a broad edge. Do NOT flip PRIMARY_SOURCE until both directions and >1 signal have live data.

## Net-of-cost reality check
- Whole book: gross -0.107R → **net -0.174R** (PF 0.69, n=382)
- Mechanical: gross -0.019R → **net -0.080R** (n=43)
- Signal-backed: gross -0.045R → **net -0.103R** (n=70) — the only cut that should be near a real net edge
- **VERDICT: NO edge survives costs yet** — best source net -0.066R (watch). Every source is net-negative or breakeven. The gross edge is a cost illusion; the only path to a real edge is cutting the losing longs and/or raising per-trade R by widening targets or entering closer to stop — NOT more rule-tuning.