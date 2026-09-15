# Head-to-Head: Mechanical vs Claude

Total evaluated trades: 438
Cost model: 0.170% round-trip (fee 0.055% + slippage 0.030% ×2) + funding; net = gross − cost.

## By source (gross → net of cost)

| source | n | win% | gross exp (R) | **net exp (R)** | net PF |
|---|---|---|---|---|---|
| claude | 299 | 32.1% | -0.129 | **-0.202** | 0.67 |
| mechanical | 50 | 54.0% | +0.037 | **-0.022** | 0.94 |
| watch | 89 | 37.1% | -0.076 | **-0.115** | 0.73 |

## WATCH lane — promotion watch (paper-tracked, NOT in the edge book)

Bar to promote a watch signal into the gated EXECUTE book: **net-of-cost expectancy ≥ +0.050R over ≥ 30 trades** (then still needs a manual both-direction/robustness sanity check).

| watch signal | n | win% | gross exp (R) | **net exp (R)** | status |
|---|---|---|---|---|---|
| trend_pullback_short | 10 | 50.0% | +0.286 | **+0.257** | ↑ clears bar, building sample (10/30) |
| (unknown) | 12 | 50.0% | +0.185 | **+0.169** | ↑ clears bar, building sample (12/30) |
| rsi_rejection_short | 19 | 57.9% | +0.202 | **+0.154** | ↑ clears bar, building sample (19/30) |
| failed_breakout_short | 18 | 27.8% | -0.143 | **-0.211** | building (18/30) |
| rsi_bounce_long | 17 | 29.4% | -0.215 | **-0.240** | building (17/30) |
| observation | 4 | 0.0% | -0.698 | **-0.707** | building (4/30) |
| liquidity_sweep_long | 8 | 12.5% | -0.713 | **-0.750** | building (8/30) |
| range_reversion_long | 1 | 0.0% | -1.000 | **-1.061** | building (1/30) |

## By signal backing (gross → net of cost)

| backing | n | win% | gross exp (R) | **net exp (R)** | net PF |
|---|---|---|---|---|---|
| discretionary | 272 | 31.2% | -0.134 | **-0.208** | 0.66 |
| signal_backed | 77 | 49.4% | -0.006 | **-0.063** | 0.85 |

## By source × direction

| source | direction | n | win% | expectancy (R) | profit factor |
|---|---|---|---|---|---|
| claude | long | 186 | 29.0% | -0.186 | 0.69 |
| claude | short | 113 | 37.2% | -0.035 | 0.93 |
| mechanical | short | 50 | 54.0% | +0.037 | 1.11 |

## Mechanical by signal

| signal | n | win% | expectancy (R) | profit factor |
|---|---|---|---|---|
| trend_pullback_short | 48 | 54.2% | +0.041 | 1.12 |
| rsi_rejection_short | 2 | 50.0% | -0.055 | 0.89 |

## Verdict
**Mechanical LEADS on expectancy** (mechanical +0.037R vs claude -0.129R; n=50/299).
⚠️ CONCENTRATION: mechanical book is one-directional (short-only), 48/50 from a single signal — lead is not yet a broad edge. Do NOT flip PRIMARY_SOURCE until both directions and >1 signal have live data.

## Net-of-cost reality check
- Whole book: gross -0.100R → **net -0.164R** (PF 0.70, n=438)
- Mechanical: gross +0.037R → **net -0.022R** (n=50)
- Signal-backed: gross -0.006R → **net -0.063R** (n=77) — the only cut that should be near a real net edge
- **VERDICT: NO edge survives costs yet** — best source net -0.022R (mechanical). Every source is net-negative or breakeven. The gross edge is a cost illusion; the only path to a real edge is cutting the losing longs and/or raising per-trade R by widening targets or entering closer to stop — NOT more rule-tuning.