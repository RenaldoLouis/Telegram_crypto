# Head-to-Head: Mechanical vs Claude

Total evaluated trades: 512
Cost model: 0.170% round-trip (fee 0.055% + slippage 0.030% ×2) + funding; net = gross − cost.
Every expectancy / PF below is the MANAGED trade (50% at T1, BE/+0.3R trail, rest to T2/expiry) — the same definition as unified_backtest (pinned 2026-10-08). win% is the legacy full-position win.

Hit-rate metric (2026-09-23): **profitable%** = share of suggestions whose managed trade (50% at T1 + BE/+0.3R trail) closed green NET of cost; target ≥70% over ≥30 trades with net exp > 0. [lo–hi] = Wilson 95% CI.

## By source (gross → net of cost)

| source | n | win% | **profitable%** | gross exp (R) | **net exp (R)** | net PF |
|---|---|---|---|---|---|---|
| claude | 299 | 32.1% | **39.8% [34–45]** | -0.123 | **-0.195** | 0.67 |
| mechanical | 54 | 55.6% | **61.1% [48–73]** | +0.011 | **-0.048** | 0.88 |
| shadow | 30 | 46.7% | **60.0% [42–75]** | +0.051 | **-0.004** | 0.99 |
| watch | 129 | 34.9% | **50.4% [42–59]** | -0.082 | **-0.122** | 0.73 |

## WATCH lane — promotion watch (paper-tracked, NOT in the edge book)

Bar to promote a watch signal into the gated EXECUTE book: **profitable% ≥ 70% AND net-of-cost expectancy > 0 over ≥ 30 trades** (then still needs a manual both-direction/robustness sanity check).

| watch signal | n | win% | **profitable%** | gross exp (R) | **net exp (R)** | status |
|---|---|---|---|---|---|---|
| rsi_rejection_short | 19 | 57.9% | **68.4% [46–85]** | +0.218 | **+0.170** | building (19/30) |
| (unknown) | 12 | 50.0% | **66.7% [39–86]** | +0.192 | **+0.176** | building (12/30) |
| trend_pullback_short | 24 | 54.2% | **62.5% [43–79]** | +0.149 | **+0.106** | building (24/30) |
| failed_breakout_short | 38 | 36.8% | **55.3% [40–70]** | -0.024 | **-0.073** | ✗ below bar |
| range_reversion_short | 10 | 10.0% | **50.0% [24–76]** | -0.276 | **-0.350** | building (10/30) |
| liquidity_sweep_long | 27 | 29.6% | **48.1% [31–66]** | -0.208 | **-0.261** | building (27/30) |
| rsi_bounce_long | 18 | 27.8% | **33.3% [16–56]** | -0.205 | **-0.229** | building (18/30) |
| range_reversion_long | 3 | 0.0% | **33.3%** | -0.617 | **-0.667** | building (3/30) |
| observation | 8 | 12.5% | **12.5% [2–47]** | -0.527 | **-0.538** | building (8/30) |

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

## Eval engine v2 era (post-fix book — the one the 70% target is judged on)

n=32 v2-scored trades. Pre-fix records are not comparable.

| source | n | **profitable%** | net exp (R) | net PF | status vs target |
|---|---|---|---|---|---|
| shadow | 30 | **60.0% [42–75]** | -0.004 | 0.99 | ✗ below bar |
| watch | 2 | **100.0%** | +0.665 | ∞ | ↑ clears bar, building sample (2/30) |

_Forward-sample velocity: 2 surfaced v2 trades in 3 days (5.0/week) → ~6 more weeks to n=30 at this rate._

| source | signal | n | **profitable%** | net exp (R) | status vs target |
|---|---|---|---|---|---|
| shadow | liquidity_sweep_long | 18 | **61.1% [39–80]** | -0.031 | building (18/30) |
| shadow | failed_breakout_short | 8 | **62.5% [31–86]** | +0.097 | building (8/30) |
| shadow | trend_pullback_short | 4 | **50.0%** | -0.082 | building (4/30) |
| watch | range_reversion_short | 2 | **100.0%** | +0.665 | ↑ clears bar, building sample (2/30) |

## Verdict
**Mechanical LEADS on expectancy** (mechanical +0.011R vs claude -0.123R; n=54/299).
⚠️ CONCENTRATION: mechanical book is one-directional (short-only), 52/54 from a single signal — lead is not yet a broad edge. Do NOT flip PRIMARY_SOURCE until both directions and >1 signal have live data.

## Net-of-cost reality check
- Whole book: gross -0.088R → **net -0.150R** (PF 0.71, n=512)
- Mechanical: gross +0.011R → **net -0.048R** (n=54)
- Signal-backed: gross -0.025R → **net -0.082R** (n=81) — the only cut that should be near a real net edge
- **VERDICT: NOT DECIDABLE YET (2/30 trades)** — v2-era surfaced book (mechanical + watch; shadow excluded): n=2 trades = 2 independent bets, profitable 100.0%, net +0.665R. Below 30 trades the sign of any lane is noise — including the all-era rows above.