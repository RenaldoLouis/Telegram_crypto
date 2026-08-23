# Head-to-Head: Mechanical vs Claude

Total evaluated trades: 345
Cost model: 0.170% round-trip (fee 0.055% + slippage 0.030% ×2) + funding; net = gross − cost.

## By source (gross → net of cost)

| source | n | win% | gross exp (R) | **net exp (R)** | net PF |
|---|---|---|---|---|---|
| claude | 299 | 32.1% | -0.129 | **-0.202** | 0.67 |
| mechanical | 40 | 50.0% | -0.015 | **-0.079** | 0.81 |
| watch | 6 | 33.3% | -0.170 | **-0.223** | 0.43 |

## WATCH lane — promotion watch (paper-tracked, NOT in the edge book)

Bar to promote a watch signal into the gated EXECUTE book: **net-of-cost expectancy ≥ +0.050R over ≥ 30 trades** (then still needs a manual both-direction/robustness sanity check).

| watch signal | n | win% | gross exp (R) | **net exp (R)** | status |
|---|---|---|---|---|---|
| (unknown) | 6 | 33.3% | -0.170 | **-0.223** | building (6/30) |

## By signal backing (gross → net of cost)

| backing | n | win% | gross exp (R) | **net exp (R)** | net PF |
|---|---|---|---|---|---|
| discretionary | 272 | 31.2% | -0.134 | **-0.208** | 0.66 |
| signal_backed | 67 | 46.3% | -0.044 | **-0.103** | 0.78 |

## By source × direction

| source | direction | n | win% | expectancy (R) | profit factor |
|---|---|---|---|---|---|
| claude | long | 186 | 29.0% | -0.186 | 0.69 |
| claude | short | 113 | 37.2% | -0.035 | 0.93 |
| mechanical | short | 40 | 50.0% | -0.015 | 0.96 |

## Mechanical by signal

| signal | n | win% | expectancy (R) | profit factor |
|---|---|---|---|---|
| rsi_rejection_short | 2 | 50.0% | -0.055 | 0.89 |
| trend_pullback_short | 38 | 50.0% | -0.013 | 0.96 |

## Verdict
**Mechanical LEADS on expectancy** (mechanical -0.015R vs claude -0.129R; n=40/299).
⚠️ CONCENTRATION: mechanical book is one-directional (short-only), 38/40 from a single signal — lead is not yet a broad edge. Do NOT flip PRIMARY_SOURCE until both directions and >1 signal have live data.

## Net-of-cost reality check
- Whole book: gross -0.117R → **net -0.188R** (PF 0.68, n=345)
- Mechanical: gross -0.015R → **net -0.079R** (n=40)
- Signal-backed: gross -0.044R → **net -0.103R** (n=67) — the only cut that should be near a real net edge
- **VERDICT: NO edge survives costs yet** — best source net -0.079R (mechanical). Every source is net-negative or breakeven. The gross edge is a cost illusion; the only path to a real edge is cutting the losing longs and/or raising per-trade R by widening targets or entering closer to stop — NOT more rule-tuning.