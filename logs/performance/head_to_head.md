# Head-to-Head: Mechanical vs Claude

Total evaluated trades: 693
Cost model: 0.170% round-trip (fee 0.055% + slippage 0.030% ×2) + funding; net = gross − cost.
Every expectancy / PF below is the MANAGED trade (50% at T1, BE/+0.3R trail, rest to T2/expiry) — the same definition as unified_backtest (pinned 2026-10-08). win% is the legacy full-position win.

Quality yardstick (2026-10-21, replaced the ≥70% hit-rate bar): **net exp > 0 · net PF ≥ 1.3 · ≥ 55% of weeks green · over ≥ 30 trades**. **profitable%** (share of managed trades that closed green NET of cost) is reported, not gated. [lo–hi] = Wilson 95% CI.

## By source (gross → net of cost)

| source | n | win% | **profitable%** | gross exp (R) | **net exp (R)** | net PF |
|---|---|---|---|---|---|---|
| claude | 299 | 32.1% | **39.8% [34–45]** | -0.123 | **-0.195** | 0.67 |
| mechanical | 54 | 55.6% | **61.1% [48–73]** | +0.011 | **-0.048** | 0.88 |
| shadow | 210 | 44.3% | **55.2% [48–62]** | -0.012 | **-0.055** | 0.87 |
| watch | 130 | 34.6% | **50.0% [42–58]** | -0.089 | **-0.129** | 0.71 |

## WATCH lane — promotion watch (paper-tracked, NOT in the edge book; v2 era only)

Bar to promote a watch signal into the gated EXECUTE book: **net exp > 0 · net PF ≥ 1.3 · ≥ 55% of weeks green · over ≥ 30 trades** (then still needs a manual both-direction/robustness sanity check).

| watch signal | n | win% | **profitable%** | gross exp (R) | **net exp (R)** | net PF | weeks+ | status |
|---|---|---|---|---|---|---|---|---|
| failed_breakout_short | 47 | 57.4% | **63.8% [50–76]** | +0.137 | **+0.119** | 1.33 | 25% | ✗ below bar |
| range_reversion_short | 3 | 33.3% | **66.7%** | +0.127 | **+0.105** | 1.31 | 100% | ↑ clears bar, building sample (3/30) |
| trend_pullback_short | 53 | 52.8% | **62.3% [49–74]** | +0.129 | **+0.094** | 1.27 | 40% | ✗ below bar |
| rsi_bounce_long | 40 | 40.0% | **47.5% [33–62]** | -0.145 | **-0.165** | 0.58 | 33% | ✗ below bar |
| liquidity_sweep_long | 67 | 32.8% | **50.7% [39–62]** | -0.105 | **-0.166** | 0.69 | 40% | ✗ below bar |
| range_reversion_long | 3 | 0.0% | **0.0%** | -1.000 | **-1.452** | 0.00 | 0% | building (3/30) |

## By signal backing (gross → net of cost)

| backing | n | win% | **profitable%** | gross exp (R) | **net exp (R)** | net PF |
|---|---|---|---|---|---|---|
| discretionary | 272 | 31.2% | **39.3% [34–45]** | -0.125 | **-0.200** | 0.67 |
| signal_backed | 81 | 50.6% | **55.6% [45–66]** | -0.025 | **-0.082** | 0.81 |

## By source × direction

| source | direction | n | win% | expectancy (R) | profit factor |
|---|---|---|---|---|---|
| claude | long | 186 | 29.0% | -0.170 | 0.72 |
| claude | short | 113 | 37.2% | -0.045 | 0.90 |
| mechanical | short | 54 | 55.6% | +0.011 | 1.03 |

## Mechanical by signal

| signal | n | win% | **profitable%** | expectancy (R) | **net exp (R)** | profit factor |
|---|---|---|---|---|---|---|
| trend_pullback_short | 52 | 55.8% | **61.5% [48–74]** | +0.014 | **-0.038** | 1.04 |
| rsi_rejection_short | 2 | 50.0% | **50.0%** | -0.055 | **-0.299** | 0.89 |

## Eval engine v2 era (post-fix book — the one the quality yardstick is judged on)

n=213 v2-scored trades. Pre-fix records are not comparable.

| source | n | **net exp (R)** | net PF | weeks+ | profitable% | status vs bar |
|---|---|---|---|---|---|---|
| shadow | 210 | **-0.055** | 0.87 | 60% | 55.2% [48–62] | ✗ below bar |
| watch | 3 | **+0.105** | 1.31 | 100% | 66.7% | ↑ clears bar, building sample (3/30) |

_Forward-sample velocity: 3 surfaced v2 trades in 17 days (1.3/week) → ~21 more weeks to n=30 at this rate._

| source | signal | n | **net exp (R)** | net PF | weeks+ | profitable% | status vs bar |
|---|---|---|---|---|---|---|---|
| shadow | liquidity_sweep_long | 67 | **-0.166** | 0.69 | 40% | 50.7% [39–62] | ✗ below bar |
| shadow | trend_pullback_short | 53 | **+0.094** | 1.27 | 40% | 62.3% [49–74] | ✗ below bar |
| shadow | failed_breakout_short | 47 | **+0.119** | 1.33 | 25% | 63.8% [50–76] | ✗ below bar |
| shadow | rsi_bounce_long | 40 | **-0.165** | 0.58 | 33% | 47.5% [33–62] | ✗ below bar |
| shadow | range_reversion_long | 3 | **-1.452** | 0.00 | 0% | 0.0% | building (3/30) |
| watch | range_reversion_short | 3 | **+0.105** | 1.31 | 100% | 66.7% | ↑ clears bar, building sample (3/30) |

## Verdict
**Mechanical LEADS on expectancy** (mechanical +0.011R vs claude -0.123R; n=54/299).
⚠️ CONCENTRATION: mechanical book is one-directional (short-only), 52/54 from a single signal — lead is not yet a broad edge. Do NOT flip PRIMARY_SOURCE until both directions and >1 signal have live data.

## Net-of-cost reality check
- Whole book: gross -0.072R → **net -0.129R** (PF 0.74, n=693)
- Mechanical: gross +0.011R → **net -0.048R** (n=54)
- Signal-backed: gross -0.025R → **net -0.082R** (n=81) — the only cut that should be near a real net edge
- **VERDICT: NOT DECIDABLE YET (3/30 trades)** — v2-era surfaced book (mechanical + watch; shadow excluded): n=3 trades = 3 independent bets, profitable 66.7%, net +0.105R. Below 30 trades the sign of any lane is noise — including the all-era rows above.