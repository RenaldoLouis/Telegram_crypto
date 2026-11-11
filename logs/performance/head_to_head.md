# Head-to-Head: Mechanical vs Claude

Total evaluated trades: 932
Cost model: 0.170% round-trip (fee 0.055% + slippage 0.030% ×2) + funding; net = gross − cost.
Every expectancy / PF below is the MANAGED trade (50% at T1, BE/+0.3R trail, rest to T2/expiry) — the same definition as unified_backtest (pinned 2026-10-08). win% is the legacy full-position win.

Quality yardstick (2026-10-21, replaced the ≥70% hit-rate bar): **net exp > 0 · net PF ≥ 1.3 · ≥ 55% of weeks green · over ≥ 30 trades**. **profitable%** (share of managed trades that closed green NET of cost) is reported, not gated. [lo–hi] = Wilson 95% CI.

## By source (gross → net of cost)

| source | n | win% | **profitable%** | gross exp (R) | **net exp (R)** | net PF |
|---|---|---|---|---|---|---|
| claude | 299 | 32.1% | **39.8% [34–45]** | -0.123 | **-0.195** | 0.67 |
| mechanical | 54 | 55.6% | **61.1% [48–73]** | +0.011 | **-0.048** | 0.88 |
| shadow | 446 | 47.8% | **56.5% [52–61]** | +0.035 | **-0.008** | 0.98 |
| watch | 133 | 35.3% | **51.1% [43–60]** | -0.072 | **-0.112** | 0.75 |

## WATCH lane — promotion watch (paper-tracked, NOT in the edge book; v2 era only)

Bar to promote a watch signal into the gated EXECUTE book: **net exp > 0 · net PF ≥ 1.3 · ≥ 55% of weeks green · over ≥ 30 trades** (then still needs a manual both-direction/robustness sanity check).

| watch signal | n | win% | **profitable%** | gross exp (R) | **net exp (R)** | net PF | weeks+ | status |
|---|---|---|---|---|---|---|---|---|
| range_reversion_short | 6 | 50.0% | **83.3% [44–97]** | +0.393 | **+0.374** | 3.21 | 100% | ↑ clears bar, building sample (6/30) |
| failed_breakout_short | 89 | 62.9% | **68.5% [58–77]** | +0.260 | **+0.243** | 1.85 | 67% | ✅ PROMOTABLE — review for EXECUTE |
| trend_pullback_short | 128 | 51.6% | **61.7% [53–70]** | +0.173 | **+0.139** | 1.39 | 57% | ✅ PROMOTABLE — review for EXECUTE |
| rsi_bounce_long | 75 | 44.0% | **49.3% [38–60]** | -0.110 | **-0.132** | 0.64 | 20% | ✗ below bar |
| liquidity_sweep_long | 146 | 38.4% | **50.0% [42–58]** | -0.114 | **-0.185** | 0.65 | 25% | ✗ below bar |
| range_reversion_long | 8 | 25.0% | **25.0% [7–59]** | -0.585 | **-0.791** | 0.17 | 20% | building (8/30) |

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

n=452 v2-scored trades. Pre-fix records are not comparable.

| source | n | **net exp (R)** | net PF | weeks+ | profitable% | status vs bar |
|---|---|---|---|---|---|---|
| shadow | 446 | **-0.008** | 0.98 | 50% | 56.5% [52–61] | ✗ below bar |
| watch | 6 | **+0.374** | 3.21 | 100% | 83.3% [44–97] | ↑ clears bar, building sample (6/30) |

_Forward-sample velocity: 6 surfaced v2 trades in 37 days (1.1/week) → ~21 more weeks to n=30 at this rate._

| source | signal | n | **net exp (R)** | net PF | weeks+ | profitable% | status vs bar |
|---|---|---|---|---|---|---|---|
| shadow | liquidity_sweep_long | 146 | **-0.185** | 0.65 | 25% | 50.0% [42–58] | ✗ below bar |
| shadow | trend_pullback_short | 128 | **+0.139** | 1.39 | 57% | 61.7% [53–70] | ✅ PROMOTABLE — review for EXECUTE |
| shadow | failed_breakout_short | 89 | **+0.243** | 1.85 | 67% | 68.5% [58–77] | ✅ PROMOTABLE — review for EXECUTE |
| shadow | rsi_bounce_long | 75 | **-0.132** | 0.64 | 20% | 49.3% [38–60] | ✗ below bar |
| shadow | range_reversion_long | 8 | **-0.791** | 0.17 | 20% | 25.0% [7–59] | building (8/30) |
| watch | range_reversion_short | 6 | **+0.374** | 3.21 | 100% | 83.3% [44–97] | ↑ clears bar, building sample (6/30) |

## Verdict
**Mechanical LEADS on expectancy** (mechanical +0.011R vs claude -0.123R; n=54/299).
⚠️ CONCENTRATION: mechanical book is one-directional (short-only), 52/54 from a single signal — lead is not yet a broad edge. Do NOT flip PRIMARY_SOURCE until both directions and >1 signal have live data.

## Net-of-cost reality check
- Whole book: gross -0.032R → **net -0.085R** (PF 0.82, n=932)
- Mechanical: gross +0.011R → **net -0.048R** (n=54)
- Signal-backed: gross -0.025R → **net -0.082R** (n=81) — the only cut that should be near a real net edge
- **VERDICT: NOT DECIDABLE YET (6/30 trades)** — v2-era surfaced book (mechanical + watch; shadow excluded): n=6 trades = 6 independent bets, profitable 83.3% [44–97], net +0.374R, 95% CI of net per bet [-0.45, +1.20]R. Below 30 trades the sign of any lane is noise — including the all-era rows above.