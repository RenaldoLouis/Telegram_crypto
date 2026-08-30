# Head-to-Head: Mechanical vs Claude

Total evaluated trades: 380
Cost model: 0.170% round-trip (fee 0.055% + slippage 0.030% ×2) + funding; net = gross − cost.

## By source (gross → net of cost)

| source | n | win% | gross exp (R) | **net exp (R)** | net PF |
|---|---|---|---|---|---|
| claude | 299 | 32.1% | -0.129 | **-0.202** | 0.67 |
| mechanical | 42 | 50.0% | -0.025 | **-0.086** | 0.80 |
| watch | 39 | 38.5% | -0.031 | **-0.061** | 0.86 |

## WATCH lane — promotion watch (paper-tracked, NOT in the edge book)

Bar to promote a watch signal into the gated EXECUTE book: **net-of-cost expectancy ≥ +0.050R over ≥ 30 trades** (then still needs a manual both-direction/robustness sanity check).

| watch signal | n | win% | gross exp (R) | **net exp (R)** | status |
|---|---|---|---|---|---|
| (unknown) | 39 | 38.5% | -0.031 | **-0.061** | ✗ below bar |

## By signal backing (gross → net of cost)

| backing | n | win% | gross exp (R) | **net exp (R)** | net PF |
|---|---|---|---|---|---|
| discretionary | 272 | 31.2% | -0.134 | **-0.208** | 0.66 |
| signal_backed | 69 | 46.4% | -0.049 | **-0.107** | 0.77 |

## By source × direction

| source | direction | n | win% | expectancy (R) | profit factor |
|---|---|---|---|---|---|
| claude | long | 186 | 29.0% | -0.186 | 0.69 |
| claude | short | 113 | 37.2% | -0.035 | 0.93 |
| mechanical | short | 42 | 50.0% | -0.025 | 0.94 |

## Mechanical by signal

| signal | n | win% | expectancy (R) | profit factor |
|---|---|---|---|---|
| rsi_rejection_short | 2 | 50.0% | -0.055 | 0.89 |
| trend_pullback_short | 40 | 50.0% | -0.023 | 0.94 |

## Verdict
**Mechanical LEADS on expectancy** (mechanical -0.025R vs claude -0.129R; n=42/299).
⚠️ CONCENTRATION: mechanical book is one-directional (short-only), 40/42 from a single signal — lead is not yet a broad edge. Do NOT flip PRIMARY_SOURCE until both directions and >1 signal have live data.

## Net-of-cost reality check
- Whole book: gross -0.108R → **net -0.175R** (PF 0.69, n=380)
- Mechanical: gross -0.025R → **net -0.086R** (n=42)
- Signal-backed: gross -0.049R → **net -0.107R** (n=69) — the only cut that should be near a real net edge
- **VERDICT: NO edge survives costs yet** — best source net -0.061R (watch). Every source is net-negative or breakeven. The gross edge is a cost illusion; the only path to a real edge is cutting the losing longs and/or raising per-trade R by widening targets or entering closer to stop — NOT more rule-tuning.