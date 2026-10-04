# Regime Scorecard — does the market-regime label understand the market?

_Generated 2026-10-04T09:10:01+00:00 by `regime_scorecard.py`. Research only: zero Claude calls, zero order logic._

## Pre-registered success bar (written before any number was computed)

> The regime label is INFORMATIVE if the 7-day forward median cross-sectional return differs between risk_on and risk_off observations with non-overlapping 90% block-bootstrap CIs AND the sign of the difference is the same in both chronological halves. It is USEFUL only if it also beats the naive baseline (the sign of the 24h median change that feeds it) on the same test. Otherwise: NOT INFORMATIVE.

```
Operationalisation fixed BEFORE any number was computed:

* Observation = one deduplicated `generated_utc` stamp of `hot_list.json` carrying a
  `market_regime.regime` label. t = `generated_utc`.
* Entry price = the first DAILY close at/after t (the close of the UTC day containing t);
  forward return for horizon k = close[entry+k] / close[entry] - 1. Observations whose
  7-day horizon is not yet complete are dropped. The still-open daily bar is never used.
* Per-observation outcome = cross-sectional MEDIAN forward return over the universe,
  BREADTH = share of symbols with positive forward return, plus BTC forward return.
* "The 7-day forward median cross-sectional return" of a group = the MEAN across the
  group's observations of the per-observation 7d cross-sectional median return (primary
  statistic). The median-of-medians is reported as a secondary statistic only.
* 90% CIs: block bootstrap, blocks = consecutive 7-calendar-day bins, resampled with
  replacement (B = number of blocks), 2000 reps, seed 20261004, percentile 5/95.
* INFORMATIVE test: (a) the 90% CIs of the primary statistic for risk_on and risk_off do
  not overlap on the FULL sample; (b) sign(mean_risk_on - mean_risk_off) is identical in
  the first and second chronological halves (split at the median observation time).
* Naive baseline = sign of `metrics.median_change_pct` (>0 vs <0); it is put through the
  identical test (a)+(b). USEFUL requires INFORMATIVE AND |gap_regime| > |gap_baseline|
  (point estimates, where gap = risk_on - risk_off and pos - neg respectively) AND the
  paired block-bootstrap 90% CI of (|gap_regime| - |gap_baseline|) lies above zero.
* Either sign of the gap counts as "informative" (the label could be a momentum OR a
  contrarian signal); the sign is reported because it matters for use.
* Every group-vs-group comparison and every correlation printed is counted toward the
  multiple-testing caveat at the end.
```

## Data

- hot_list.json commits scanned: **643**; unparseable 0; without `market_regime` 19; missing timestamp 0; bad label 0; duplicate `generated_utc` 0.
- Regime observations with a label: **624** spanning 2026-05-24 13:42 → 2026-10-03 21:07 UTC.
- Usable after requiring a complete 7-day forward window: **606** observations on **120** distinct entry days, 2026-05-24 → 2026-09-26 UTC (median 5.0 obs/day; the schedule is ~2h so gaps = CI outages).
- Daily-subsample (first observation per entry day): **120** observations.
- Universe: top 60 USDT linear perps by turnover24h on 20261004 (+BTCUSDT) — **survivorship bias**: coins that were liquid in May–Sep but have since faded are missing, and coins that are hot now were not necessarily tradeable then. 59 symbols with ≥30 daily bars; failed/thin: ['LONGXIAUSDT'].
- Daily klines: 2026-03-19 → 2026-10-03 (closed bars only; the open bar is dropped). Symbols per 7d cross-section: min 56, median 58.
- Chronological split at 2026-07-21 06:31 UTC (H1 n=303, H2 n=303).
- Block bootstrap: 7-day blocks, 18 blocks, 2000 reps, seed 20261004.

### Label distribution

| regime | n obs | share % | n days (any obs) | fresh transitions |
|---|---|---|---|---|
| risk_off | 96 | 15.8 | 38 | 37 |
| cautious | 136 | 22.4 | 65 | 71 |
| neutral | 266 | 43.9 | 94 | 84 |
| risk_on | 108 | 17.8 | 44 | 39 |

Unconditional base rates (all observations): mean 7d med ret +0.17%, median -1.22%, mean breadth 48.5%, mean BTC 7d +0.75%.

## A. By regime label — 7-day horizon (primary), all observations

**All observations (every ~2h), 7d forward**

| regime | n | days | mean 7d med ret % [90% CI] | median 7d med ret % [90% CI] | mean breadth % [90% CI] | mean BTC 7d % |
|---|---|---|---|---|---|---|
| risk_off | 96 | 38 | -0.04 [-2.08, +2.69] | -0.07 [-3.61, +1.67] | 51.3 [44.3, 59.8] | +0.17 |
| cautious | 136 | 65 | +1.29 [-1.35, +4.22] | -1.20 [-2.25, +0.77] | 51.5 [43.2, 60.6] | +1.50 |
| neutral | 266 | 94 | -0.13 [-2.95, +3.11] | -1.89 [-3.78, +0.08] | 46.0 [38.5, 55.0] | +0.52 |
| risk_on | 108 | 44 | -0.31 [-2.72, +1.24] | -1.65 [-3.66, +0.33] | 48.6 [37.2, 57.0] | +0.88 |

### A2. Same, daily subsample (one observation per entry day)

**Daily subsample, 7d forward**

| regime | n | days | mean 7d med ret % [90% CI] | median 7d med ret % [90% CI] | mean breadth % [90% CI] | mean BTC 7d % |
|---|---|---|---|---|---|---|
| risk_off | 20 | 20 | -0.18 [-3.19, +3.23] | +0.53 [-3.61, +3.76] | 52.3 [42.0, 63.2] | +0.02 |
| cautious | 22 | 22 | +1.77 [-0.87, +5.39] | -1.08 [-2.73, +3.63] | 51.2 [42.3, 61.7] | +1.89 |
| neutral | 58 | 58 | +0.42 [-3.10, +4.19] | -1.13 [-4.44, +1.07] | 48.5 [38.8, 58.4] | +0.63 |
| risk_on | 20 | 20 | -0.14 [-2.39, +1.73] | -1.91 [-3.28, +2.29] | 48.3 [36.5, 58.9] | +0.83 |

### A3. All horizons (point estimates only)

| regime | n | mean med 1d % / breadth 1d % / BTC 1d % | mean med 3d % / breadth 3d % / BTC 3d % | mean med 7d % / breadth 7d % / BTC 7d % |
|---|---|---|---|---|
| risk_off | 96 | -0.33 / 49.3 / +0.15 | -0.25 / 49.4 / +0.24 | -0.04 / 51.3 / +0.17 |
| cautious | 136 | +0.15 / 51.8 / +0.29 | +0.13 / 49.1 / +0.35 | +1.29 / 51.5 / +1.50 |
| neutral | 266 | -0.52 / 43.3 / -0.14 | -0.45 / 44.8 / -0.00 | -0.13 / 46.0 / +0.52 |
| risk_on | 108 | +0.88 / 53.7 / +0.39 | +0.37 / 48.7 / +0.44 | -0.31 / 48.6 / +0.88 |

### A4. The pre-registered contrast: risk_on − risk_off, 7d mean cross-sectional median return

| sample | n risk_on | n risk_off | gap (pp) | 90% block-bootstrap CI | CIs of the two groups overlap? |
|---|---|---|---|---|---|
| all obs | 108 | 96 | -0.27 | [-3.17, +1.65] | YES |
| daily subsample | 20 | 20 | +0.04 | [-4.04, +3.39] | YES |

## B. Chronological halves — by regime, 7d

**H1: 2026-05-24 → 2026-07-21 (n=303)**

| regime | n | days | mean 7d med ret % [90% CI] | median 7d med ret % [90% CI] | mean breadth % [90% CI] | mean BTC 7d % |
|---|---|---|---|---|---|---|
| risk_off | 62 | 22 | -1.44 [-3.70, +1.17] | -1.22 [-5.54, +1.67] | 49.3 [40.4, 59.3] | -0.38 |
| cautious | 67 | 35 | -1.70 [-4.92, +1.19] | -1.33 [-5.54, +0.77] | 45.4 [34.4, 56.6] | -0.44 |
| neutral | 121 | 43 | -3.87 [-7.09, -0.75] | -3.66 [-6.03, -0.45] | 38.4 [28.8, 49.1] | -2.81 |
| risk_on | 53 | 20 | -0.25 [-4.39, +2.05] | +0.23 [-3.83, +2.29] | 53.2 [35.4, 65.4] | +0.78 |

**H2: 2026-07-21 → 2026-09-26 (n=303)**

| regime | n | days | mean 7d med ret % [90% CI] | median 7d med ret % [90% CI] | mean breadth % [90% CI] | mean BTC 7d % |
|---|---|---|---|---|---|---|
| risk_off | 34 | 16 | +2.52 [-0.95, +7.78] | -0.07 [-3.61, +3.76] | 55.0 [42.8, 69.3] | +1.17 |
| cautious | 69 | 30 | +4.19 [+0.96, +8.50] | -0.34 [-1.70, +10.45] | 57.4 [46.2, 70.1] | +3.40 |
| neutral | 145 | 52 | +2.98 [-1.05, +7.79] | -0.91 [-3.11, +6.74] | 52.3 [39.3, 66.7] | +3.30 |
| risk_on | 55 | 24 | -0.36 [-3.18, +1.45] | -1.89 [-4.76, -0.74] | 44.2 [30.4, 53.4] | +0.97 |

| half | n risk_on | n risk_off | gap risk_on − risk_off (pp) | 90% CI | sign |
|---|---|---|---|---|---|
| H1 | 53 | 62 | +1.19 | [-1.69, +2.49] | + |
| H2 | 55 | 34 | -2.88 | [-9.32, +1.37] | − |

## C. Naive baselines — the raw inputs that feed the label

**Sign of metrics.median_change_pct (the breadth-median input), 7d forward, all obs**

| base_med | n | days | mean 7d med ret % [90% CI] | median 7d med ret % [90% CI] | mean breadth % [90% CI] | mean BTC 7d % |
|---|---|---|---|---|---|---|
| med24h<0 | 288 | 89 | +0.39 [-1.81, +3.14] | -1.20 [-3.11, +0.74] | 50.0 [43.0, 58.0] | +0.64 |
| med24h>0 | 318 | 95 | -0.04 [-2.35, +2.24] | -1.65 [-3.11, +0.16] | 47.2 [39.7, 54.2] | +0.85 |
| med24h=0/nan | 0 | 0 | n/a | n/a | n/a | n/a |

**Same, daily subsample**

| base_med | n | days | mean 7d med ret % [90% CI] | median 7d med ret % [90% CI] | mean breadth % [90% CI] | mean BTC 7d % |
|---|---|---|---|---|---|---|
| med24h<0 | 56 | 56 | +0.16 [-2.09, +2.92] | -0.84 [-3.11, +1.02] | 49.9 [43.2, 58.0] | +0.46 |
| med24h>0 | 64 | 64 | +0.74 [-1.99, +3.45] | -1.29 [-3.28, +0.31] | 49.3 [41.2, 56.9] | +1.09 |

**Sign of metrics.btc_change_pct, 7d forward, all obs**

| base_btc | n | days | mean 7d med ret % [90% CI] | median 7d med ret % [90% CI] | mean breadth % [90% CI] | mean BTC 7d % |
|---|---|---|---|---|---|---|
| btc24h<0 | 290 | 92 | -0.09 [-2.59, +2.60] | -1.33 [-3.11, +0.74] | 49.0 [41.5, 56.8] | +0.51 |
| btc24h>0 | 315 | 88 | +0.39 [-1.94, +2.87] | -1.20 [-2.68, +0.23] | 48.0 [40.5, 55.4] | +0.95 |
| btc24h=0/nan | 1 | 1 | +6.65 [n/a, n/a] | +6.65 [n/a, n/a] | 86.2 [n/a, n/a] | +6.30 |

All horizons (point estimates):

| base_med | n | mean med 1d % / breadth 1d % / BTC 1d % | mean med 3d % / breadth 3d % / BTC 3d % | mean med 7d % / breadth 7d % / BTC 7d % |
|---|---|---|---|---|
| med24h<0 | 288 | -0.19 / 48.5 / +0.12 | -0.20 / 47.6 / +0.14 | +0.39 / 50.0 / +0.64 |
| med24h>0 | 318 | +0.01 / 47.5 / +0.08 | -0.08 / 46.9 / +0.24 | -0.04 / 47.2 / +0.85 |

| base_btc | n | mean med 1d % / breadth 1d % / BTC 1d % | mean med 3d % / breadth 3d % / BTC 3d % | mean med 7d % / breadth 7d % / BTC 7d % |
|---|---|---|---|---|
| btc24h<0 | 290 | -0.29 / 47.9 / -0.00 | -0.72 / 45.5 / -0.16 | -0.09 / 49.0 / +0.51 |
| btc24h>0 | 315 | +0.11 / 48.2 / +0.20 | +0.39 / 48.7 / +0.51 | +0.39 / 48.0 / +0.95 |

### C2. Baseline contrast: med24h>0 − med24h<0, 7d mean cross-sectional median return

| sample | n pos | n neg | gap (pp) | 90% CI | group CIs overlap? |
|---|---|---|---|---|---|
| all obs | 318 | 288 | -0.43 | [-1.79, +0.76] | YES |
| H1 | 146 | 157 | -0.40 | [-1.74, +0.18] | — |
| H2 | 172 | 131 | -1.32 | [-4.10, +1.01] | — |
| (btc sign, all obs) | 315 | 290 | +0.48 | [-1.54, +2.78] | — |

Paired block-bootstrap of |gap_regime| − |gap_baseline| (7d): point -0.16 pp, 90% CI [-0.51, +1.69].

## D. Spearman rank correlation of each regime metric with forward outcomes (all obs)

| metric | n | ρ vs 7d med ret [90% CI] | ρ vs 7d breadth [90% CI] | ρ vs 7d BTC | ρ vs 3d med ret | ρ vs 1d med ret |
|---|---|---|---|---|---|---|
| pct_declining | 606 | +0.048 [-0.04, +0.16] | +0.068 [-0.02, +0.18] | +0.031 | +0.050 | +0.002 |
| median_change_pct | 606 | -0.026 [-0.13, +0.05] | -0.043 [-0.15, +0.04] | +0.002 | -0.028 | +0.007 |
| btc_change_pct | 606 | +0.047 [-0.09, +0.17] | +0.030 [-0.10, +0.15] | +0.032 | +0.061 | +0.041 |
| avg_funding_pct | 606 | -0.177 [-0.30, -0.02] | -0.167 [-0.29, -0.00] | -0.160 | -0.039 | +0.022 |
| large_decline_count | 606 | +0.169 [+0.09, +0.25] | +0.194 [+0.11, +0.28] | +0.146 | +0.173 | +0.113 |
| regime (ordinal 0..3) | 606 | -0.048 [-0.17, +0.04] | -0.059 [-0.19, +0.04] | -0.023 | -0.046 | -0.002 |

Note: the regime metrics are strongly inter-correlated by construction (pct_declining and median_change_pct are two views of the same 50-ticker cross-section), so these rows are not independent tests. The 1d/3d columns are shown for completeness only; the pre-registered horizon is 7d.

## E. Transitions — fresh regime change vs persistent label, 7d

**Observation where regime != previous_regime (fresh) vs unchanged (persistent)**

| regime_fresh | n | days | mean 7d med ret % [90% CI] | median 7d med ret % [90% CI] | mean breadth % [90% CI] | mean BTC 7d % |
|---|---|---|---|---|---|---|
| risk_off (fresh) | 37 | 32 | -0.60 [-3.33, +2.59] | -1.22 [-4.31, +1.14] | 48.2 [37.9, 60.2] | -0.59 |
| risk_off (persistent) | 59 | 27 | +0.32 [-1.63, +2.93] | +0.77 [-1.33, +3.16] | 53.3 [45.4, 61.8] | +0.64 |
| cautious (fresh) | 71 | 61 | +1.52 [-1.62, +5.28] | -0.47 [-3.11, +2.44] | 52.0 [42.6, 62.3] | +1.43 |
| cautious (persistent) | 65 | 33 | +1.03 [-1.43, +3.87] | -1.20 [-2.49, +0.74] | 50.9 [41.8, 60.7] | +1.59 |
| neutral (fresh) | 84 | 69 | +0.17 [-2.47, +3.12] | -1.27 [-3.66, +0.70] | 48.2 [39.8, 57.1] | +0.78 |
| neutral (persistent) | 182 | 68 | -0.28 [-3.32, +3.30] | -2.26 [-4.12, -0.08] | 44.9 [36.7, 54.5] | +0.40 |
| risk_on (fresh) | 39 | 34 | -1.55 [-3.93, +0.62] | -1.89 [-3.78, +0.00] | 43.9 [35.7, 52.6] | -0.55 |
| risk_on (persistent) | 69 | 26 | +0.40 [-2.73, +2.01] | -1.20 [-3.87, +2.28] | 51.3 [35.0, 61.5] | +1.68 |

Fresh-vs-persistent gap within label (7d mean med ret, pp, 90% CI):

| regime | n fresh | n persistent | fresh − persistent | 90% CI |
|---|---|---|---|---|
| risk_off | 37 | 59 | -0.92 | [-2.85, +1.10] |
| cautious | 71 | 65 | +0.49 | [-1.98, +3.39] |
| neutral | 84 | 182 | +0.45 | [-1.65, +2.32] |
| risk_on | 39 | 69 | -1.95 | [-4.42, +1.07] |

Fresh risk_on − fresh risk_off (7d): -0.95 pp, 90% CI [-3.86, +1.63] (n 39 vs 37). Fresh transitions are few and clustered, so treat these rows as descriptive.

Run lengths (consecutive observations with the same label; ~2h each when CI was healthy):

| regime | runs | median run (obs) | max run (obs) |
|---|---|---|---|
| risk_off | 37 | 2 | 13 |
| cautious | 71 | 1 | 7 |
| neutral | 84 | 2 | 17 |
| risk_on | 39 | 1 | 20 |

## F. Verdict — pre-registered bar applied mechanically

**VERDICT: NOT INFORMATIVE**

| check | value | pass? |
|---|---|---|
| (a) risk_on 7d mean med ret 90% CI | [-2.72, +1.24] pp (n=108) | — |
| (a) risk_off 7d mean med ret 90% CI | [-2.08, +2.69] pp (n=96) | — |
| (a) CIs non-overlapping | overlap = True; gap -0.27 pp, gap CI [-3.17, +1.65] | FAIL |
| (b) sign of gap same in both halves | H1 +1.19 pp, H2 -2.88 pp | FAIL |
| INFORMATIVE = (a) AND (b) | | NO |
| baseline (sign of median_change_pct) on the same test | CIs non-overlap: False; halves -0.40 / -1.32 pp → fails | — |
| regime beats baseline: \|gap_regime\| − \|gap_base\| | point -0.16 pp (regime +0.27 vs base +0.43); paired 90% CI [-0.51, +1.69] | FAIL |
| USEFUL = INFORMATIVE AND beats baseline | | NO |

Direction of the point estimate: risk_on observations were followed by LOWER 7d cross-sectional returns than risk_off (contrarian/mean-reversion reading). Daily-subsample gap +0.04 pp, CI [-4.04, +3.39].

## G. Multiple-testing caveat

This report printed **124** numbers that could be read as a test (breakdown below). At a 90% CI, roughly 1 in 10 null comparisons will look 'significant' by chance, so only the ONE pre-registered contrast (risk_on vs risk_off, 7d, mean of cross-sectional medians, full sample + halves) carries the verdict; everything else is descriptive and would need a fresh out-of-sample period to confirm. Observations also overlap heavily (every ~2h with a 7-day horizon → each 7-day block is effectively ONE independent draw), which is why the block bootstrap and the daily subsample exist; even so the effective sample is on the order of 18 independent blocks, not 606 observations.

| category | count |
|---|---|
| group tables (4-row, with CIs) | 4 |
| horizon point-estimate cells | 72 |
| gap tests (A vs B, 7d primary) | 14 |
| group tables (baseline, with CIs) | 3 |
| spearman correlations | 30 |
| group tables (transitions, with CIs) | 1 |

## H. Caveats

- Survivorship: universe = top-60 by turnover TODAY. Cross-sectional medians are robust to a few outliers, but the sample systematically includes coins that survived/grew.
- The regime label is computed from a different (top-50 at the time) ticker set than the forward universe; this is deliberate — the question is whether the label generalises to the tradeable universe.
- One summer-to-autumn 2026 window: ~4.5 months, dominated by whatever macro regime prevailed; any result here is a single-period observation, not a general law.
- Daily entry at the UTC close after t: a label seen at 02:00 UTC waits ~22h before the measured entry; this is realizable but smooths away intraday information.
- No costs are modelled — this is a label-quality test, not a strategy backtest.
