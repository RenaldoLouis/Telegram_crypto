# Head-to-Head: Mechanical vs Claude

Total evaluated trades: 851
Cost model: 0.170% round-trip (fee 0.055% + slippage 0.030% ×2) + funding; net = gross − cost.
Every expectancy / PF below is the MANAGED trade (50% at T1, BE/+0.3R trail, rest to T2/expiry) — the same definition as unified_backtest (pinned 2026-10-08). win% is the legacy full-position win.

Quality yardstick (2026-10-21, replaced the ≥70% hit-rate bar): **net exp > 0 · net PF ≥ 1.3 · ≥ 55% of weeks green · over ≥ 30 trades**. **profitable%** (share of managed trades that closed green NET of cost) is reported, not gated. [lo–hi] = Wilson 95% CI.

## By source (gross → net of cost)

| source | n | win% | **profitable%** | gross exp (R) | **net exp (R)** | net PF |
|---|---|---|---|---|---|---|
| claude | 299 | 32.1% | **39.8% [34–45]** | -0.123 | **-0.195** | 0.67 |
| mechanical | 54 | 55.6% | **61.1% [48–73]** | +0.011 | **-0.048** | 0.88 |
| shadow | 365 | 43.8% | **53.4% [48–58]** | -0.023 | **-0.065** | 0.85 |
| watch | 133 | 35.3% | **51.1% [43–60]** | -0.072 | **-0.112** | 0.75 |

## WATCH lane — promotion watch (paper-tracked, NOT in the edge book; v2 era only)

Bar to promote a watch signal into the gated EXECUTE book: **net exp > 0 · net PF ≥ 1.3 · ≥ 55% of weeks green · over ≥ 30 trades** (then still needs a manual both-direction/robustness sanity check).

| watch signal | n | win% | **profitable%** | gross exp (R) | **net exp (R)** | net PF | weeks+ | status |
|---|---|---|---|---|---|---|---|---|
| range_reversion_short | 6 | 50.0% | **83.3% [44–97]** | +0.393 | **+0.374** | 3.21 | 100% | ↑ clears bar, building sample (6/30) |
| failed_breakout_short | 82 | 64.6% | **69.5% [59–78]** | +0.277 | **+0.259** | 1.94 | 60% | ✅ PROMOTABLE — review for EXECUTE |
| trend_pullback_short | 99 | 44.4% | **55.6% [46–65]** | +0.039 | **+0.006** | 1.02 | 33% | ✗ below bar |
| rsi_bounce_long | 65 | 43.1% | **49.2% [38–61]** | -0.108 | **-0.129** | 0.63 | 25% | ✗ below bar |
| liquidity_sweep_long | 112 | 30.4% | **44.6% [36–54]** | -0.205 | **-0.272** | 0.54 | 14% | ✗ below bar |
| range_reversion_long | 7 | 14.3% | **14.3% [3–51]** | -0.711 | **-0.944** | 0.13 | 0% | building (7/30) |

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

n=371 v2-scored trades. Pre-fix records are not comparable.

| source | n | **net exp (R)** | net PF | weeks+ | profitable% | status vs bar |
|---|---|---|---|---|---|---|
| shadow | 365 | **-0.065** | 0.85 | 43% | 53.4% [48–58] | ✗ below bar |
| watch | 6 | **+0.374** | 3.21 | 100% | 83.3% [44–97] | ↑ clears bar, building sample (6/30) |

_Forward-sample velocity: 6 surfaced v2 trades in 29 days (1.5/week) → ~16 more weeks to n=30 at this rate._

| source | signal | n | **net exp (R)** | net PF | weeks+ | profitable% | status vs bar |
|---|---|---|---|---|---|---|---|
| shadow | liquidity_sweep_long | 112 | **-0.272** | 0.54 | 14% | 44.6% [36–54] | ✗ below bar |
| shadow | trend_pullback_short | 99 | **+0.006** | 1.02 | 33% | 55.6% [46–65] | ✗ below bar |
| shadow | failed_breakout_short | 82 | **+0.259** | 1.94 | 60% | 69.5% [59–78] | ✅ PROMOTABLE — review for EXECUTE |
| shadow | rsi_bounce_long | 65 | **-0.129** | 0.63 | 25% | 49.2% [38–61] | ✗ below bar |
| shadow | range_reversion_long | 7 | **-0.944** | 0.13 | 0% | 14.3% [3–51] | building (7/30) |
| watch | range_reversion_short | 6 | **+0.374** | 3.21 | 100% | 83.3% [44–97] | ↑ clears bar, building sample (6/30) |

## Verdict
**Mechanical LEADS on expectancy** (mechanical +0.011R vs claude -0.123R; n=54/299).
⚠️ CONCENTRATION: mechanical book is one-directional (short-only), 52/54 from a single signal — lead is not yet a broad edge. Do NOT flip PRIMARY_SOURCE until both directions and >1 signal have live data.

## Net-of-cost reality check
- Whole book: gross -0.064R → **net -0.117R** (PF 0.76, n=851)
- Mechanical: gross +0.011R → **net -0.048R** (n=54)
- Signal-backed: gross -0.025R → **net -0.082R** (n=81) — the only cut that should be near a real net edge
- **VERDICT: NOT DECIDABLE YET (6/30 trades)** — v2-era surfaced book (mechanical + watch; shadow excluded): n=6 trades = 6 independent bets, profitable 83.3% [44–97], net +0.374R, 95% CI of net per bet [-0.45, +1.20]R. Below 30 trades the sign of any lane is noise — including the all-era rows above.