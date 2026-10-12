# Head-to-Head: Mechanical vs Claude

Total evaluated trades: 551
Cost model: 0.170% round-trip (fee 0.055% + slippage 0.030% ×2) + funding; net = gross − cost.
Every expectancy / PF below is the MANAGED trade (50% at T1, BE/+0.3R trail, rest to T2/expiry) — the same definition as unified_backtest (pinned 2026-10-08). win% is the legacy full-position win.

Hit-rate metric (2026-09-23): **profitable%** = share of suggestions whose managed trade (50% at T1 + BE/+0.3R trail) closed green NET of cost; target ≥70% over ≥30 trades with net exp > 0. [lo–hi] = Wilson 95% CI.

## By source (gross → net of cost)

| source | n | win% | **profitable%** | gross exp (R) | **net exp (R)** | net PF |
|---|---|---|---|---|---|---|
| claude | 299 | 32.1% | **39.8% [34–45]** | -0.123 | **-0.195** | 0.67 |
| mechanical | 54 | 55.6% | **61.1% [48–73]** | +0.011 | **-0.048** | 0.88 |
| shadow | 69 | 47.8% | **56.5% [45–68]** | +0.037 | **-0.005** | 0.99 |
| watch | 129 | 34.9% | **50.4% [42–59]** | -0.082 | **-0.122** | 0.73 |

## WATCH lane — promotion watch (paper-tracked, NOT in the edge book)

Bar to promote a watch signal into the gated EXECUTE book: **profitable% ≥ 70% AND net-of-cost expectancy > 0 over ≥ 30 trades** (then still needs a manual both-direction/robustness sanity check).

| watch signal | n | win% | **profitable%** | gross exp (R) | **net exp (R)** | status |
|---|---|---|---|---|---|---|
| rsi_rejection_short | 19 | 57.9% | **68.4% [46–85]** | +0.218 | **+0.170** | building (19/30) |
| (unknown) | 12 | 50.0% | **66.7% [39–86]** | +0.192 | **+0.176** | building (12/30) |
| failed_breakout_short | 48 | 43.8% | **60.4% [46–73]** | +0.084 | **+0.041** | ✗ below bar |
| trend_pullback_short | 31 | 48.4% | **58.1% [41–74]** | +0.090 | **+0.053** | ✗ below bar |
| range_reversion_short | 10 | 10.0% | **50.0% [24–76]** | -0.276 | **-0.350** | building (10/30) |
| liquidity_sweep_long | 34 | 29.4% | **44.1% [29–60]** | -0.226 | **-0.284** | ✗ below bar |
| rsi_bounce_long | 32 | 40.6% | **43.8% [28–61]** | -0.118 | **-0.141** | ✗ below bar |
| range_reversion_long | 4 | 0.0% | **25.0%** | -0.713 | **-0.765** | building (4/30) |
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

n=71 v2-scored trades. Pre-fix records are not comparable.

| source | n | **profitable%** | net exp (R) | net PF | status vs target |
|---|---|---|---|---|---|
| shadow | 69 | **56.5% [45–68]** | -0.005 | 0.99 | ✗ below bar |
| watch | 2 | **100.0%** | +0.665 | ∞ | ↑ clears bar, building sample (2/30) |

_Forward-sample velocity: 2 surfaced v2 trades in 7 days (2.1/week) → ~14 more weeks to n=30 at this rate._

| source | signal | n | **profitable%** | net exp (R) | status vs target |
|---|---|---|---|---|---|
| shadow | liquidity_sweep_long | 25 | **52.0% [34–70]** | -0.126 | building (25/30) |
| shadow | failed_breakout_short | 18 | **72.2% [49–88]** | +0.305 | ↑ clears bar, building sample (18/30) |
| shadow | rsi_bounce_long | 14 | **57.1% [33–79]** | -0.028 | building (14/30) |
| shadow | trend_pullback_short | 11 | **45.5% [21–72]** | -0.112 | building (11/30) |
| watch | range_reversion_short | 2 | **100.0%** | +0.665 | ↑ clears bar, building sample (2/30) |
| shadow | range_reversion_long | 1 | **0.0%** | -1.057 | building (1/30) |

## Verdict
**Mechanical LEADS on expectancy** (mechanical +0.011R vs claude -0.123R; n=54/299).
⚠️ CONCENTRATION: mechanical book is one-directional (short-only), 52/54 from a single signal — lead is not yet a broad edge. Do NOT flip PRIMARY_SOURCE until both directions and >1 signal have live data.

## Net-of-cost reality check
- Whole book: gross -0.080R → **net -0.140R** (PF 0.73, n=551)
- Mechanical: gross +0.011R → **net -0.048R** (n=54)
- Signal-backed: gross -0.025R → **net -0.082R** (n=81) — the only cut that should be near a real net edge
- **VERDICT: NOT DECIDABLE YET (2/30 trades)** — v2-era surfaced book (mechanical + watch; shadow excluded): n=2 trades = 2 independent bets, profitable 100.0%, net +0.665R. Below 30 trades the sign of any lane is noise — including the all-era rows above.