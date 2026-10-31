# Head-to-Head: Mechanical vs Claude

Total evaluated trades: 810
Cost model: 0.170% round-trip (fee 0.055% + slippage 0.030% ×2) + funding; net = gross − cost.
Every expectancy / PF below is the MANAGED trade (50% at T1, BE/+0.3R trail, rest to T2/expiry) — the same definition as unified_backtest (pinned 2026-10-08). win% is the legacy full-position win.

Quality yardstick (2026-10-21, replaced the ≥70% hit-rate bar): **net exp > 0 · net PF ≥ 1.3 · ≥ 55% of weeks green · over ≥ 30 trades**. **profitable%** (share of managed trades that closed green NET of cost) is reported, not gated. [lo–hi] = Wilson 95% CI.

## By source (gross → net of cost)

| source | n | win% | **profitable%** | gross exp (R) | **net exp (R)** | net PF |
|---|---|---|---|---|---|---|
| claude | 299 | 32.1% | **39.8% [34–45]** | -0.123 | **-0.195** | 0.67 |
| mechanical | 54 | 55.6% | **61.1% [48–73]** | +0.011 | **-0.048** | 0.88 |
| shadow | 325 | 41.8% | **52.6% [47–58]** | -0.046 | **-0.088** | 0.80 |
| watch | 132 | 34.8% | **50.8% [42–59]** | -0.081 | **-0.121** | 0.73 |

## WATCH lane — promotion watch (paper-tracked, NOT in the edge book; v2 era only)

Bar to promote a watch signal into the gated EXECUTE book: **net exp > 0 · net PF ≥ 1.3 · ≥ 55% of weeks green · over ≥ 30 trades** (then still needs a manual both-direction/robustness sanity check).

| watch signal | n | win% | **profitable%** | gross exp (R) | **net exp (R)** | net PF | weeks+ | status |
|---|---|---|---|---|---|---|---|---|
| failed_breakout_short | 73 | 63.0% | **68.5% [57–78]** | +0.263 | **+0.246** | 1.83 | 60% | ✅ PROMOTABLE — review for EXECUTE |
| range_reversion_short | 5 | 40.0% | **80.0% [38–96]** | +0.256 | **+0.235** | 2.16 | 100% | ↑ clears bar, building sample (5/30) |
| trend_pullback_short | 86 | 41.9% | **54.7% [44–65]** | +0.003 | **-0.031** | 0.93 | 33% | ✗ below bar |
| rsi_bounce_long | 60 | 41.7% | **48.3% [36–61]** | -0.109 | **-0.130** | 0.63 | 50% | ✗ below bar |
| liquidity_sweep_long | 101 | 28.7% | **44.6% [35–54]** | -0.225 | **-0.292** | 0.52 | 33% | ✗ below bar |
| range_reversion_long | 5 | 0.0% | **0.0% [0–43]** | -1.000 | **-1.313** | 0.00 | 0% | building (5/30) |

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

n=330 v2-scored trades. Pre-fix records are not comparable.

| source | n | **net exp (R)** | net PF | weeks+ | profitable% | status vs bar |
|---|---|---|---|---|---|---|
| shadow | 325 | **-0.088** | 0.80 | 50% | 52.6% [47–58] | ✗ below bar |
| watch | 5 | **+0.235** | 2.16 | 100% | 80.0% [38–96] | ↑ clears bar, building sample (5/30) |

_Forward-sample velocity: 5 surfaced v2 trades in 26 days (1.4/week) → ~18 more weeks to n=30 at this rate._

| source | signal | n | **net exp (R)** | net PF | weeks+ | profitable% | status vs bar |
|---|---|---|---|---|---|---|---|
| shadow | liquidity_sweep_long | 101 | **-0.292** | 0.52 | 33% | 44.6% [35–54] | ✗ below bar |
| shadow | trend_pullback_short | 86 | **-0.031** | 0.93 | 33% | 54.7% [44–65] | ✗ below bar |
| shadow | failed_breakout_short | 73 | **+0.246** | 1.83 | 60% | 68.5% [57–78] | ✅ PROMOTABLE — review for EXECUTE |
| shadow | rsi_bounce_long | 60 | **-0.130** | 0.63 | 50% | 48.3% [36–61] | ✗ below bar |
| shadow | range_reversion_long | 5 | **-1.313** | 0.00 | 0% | 0.0% [0–43] | building (5/30) |
| watch | range_reversion_short | 5 | **+0.235** | 2.16 | 100% | 80.0% [38–96] | ↑ clears bar, building sample (5/30) |

## Verdict
**Mechanical LEADS on expectancy** (mechanical +0.011R vs claude -0.123R; n=54/299).
⚠️ CONCENTRATION: mechanical book is one-directional (short-only), 52/54 from a single signal — lead is not yet a broad edge. Do NOT flip PRIMARY_SOURCE until both directions and >1 signal have live data.

## Net-of-cost reality check
- Whole book: gross -0.076R → **net -0.130R** (PF 0.74, n=810)
- Mechanical: gross +0.011R → **net -0.048R** (n=54)
- Signal-backed: gross -0.025R → **net -0.082R** (n=81) — the only cut that should be near a real net edge
- **VERDICT: NOT DECIDABLE YET (5/30 trades)** — v2-era surfaced book (mechanical + watch; shadow excluded): n=5 trades = 5 independent bets, profitable 80.0% [38–96], net +0.235R, 95% CI of net per bet [-0.74, +1.21]R. Below 30 trades the sign of any lane is noise — including the all-era rows above.