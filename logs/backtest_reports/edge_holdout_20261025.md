# Edge search — HOLDOUT (2026-10-25)

Finalists committed in `logs/backtest_reports/edge_finalists.json` (N at selection = 114). HOLDOUT = 2025-01-01 → 2026-10-24, read once. Scale = each finalist's DISCOVERY scale. PASS = net > 0, ≥ 60% months green, Sharpe ≥ 0.75, DD ≤ 25% at that scale.

| line | net @20v | Sharpe | months green | worst month @20v | DD @20v | verdict |
|---|---|---|---|---|---|---|
| combo_5_sleeves_with_harvest | +49.0% | +0.90 | 17/22 (77%) | -25.9% | 50% | **FAIL** |
| volman_combo_4_sleeves | +35.1% | +0.89 | 14/22 (64%) | -8.7% | 26% | **FAIL** |
| equal-risk combination | +42.0% | +0.94 | 15/22 (68%) | -15.0% | 38% | **FAIL** |
## Reading (written after the one-shot run; the verdicts above do not change)

- **Waiver:** no DISCOVERY variant met the finalist bar after 5 rounds (114 variants). By the user's decision
  (2026-10-25, recorded in `edge_finalists.json` before this run) the two best blends were sent here with the
  finalist conditions on Sharpe, worst year and drawdown waived. The holdout PASS rule was not changed.
- **Both FAIL on drawdown only.** `volman_combo_4_sleeves` passed net (+35% at 20% vol), months green
  (14/22 = 64%) and Sharpe (0.89 ≥ 0.75), and missed the drawdown limit by 0.6 point (25.6% vs 25%: four red
  months Jul → Oct 2025, peak 2025-06-27, bottom 2025-11-10). By year at 20% vol: 2025 +13.8%, 2026 +21.4%.
  Market over the same window: BTC −14%, equal-weight eligible alts far worse.
- **The sleeves did not keep their DISCOVERY ranks:** 28-day cross-sectional momentum Sharpe +1.70 (weak in
  2021–24), new-listing short (hedged) +0.54, BTC trend (vol-managed, long only) +0.36, funding carry 7d −0.80
  (the steadiest sleeve in DISCOVERY), funding harvest +0.37. The blend held up because the sleeves are
  uncorrelated, not because any one of them is reliable.
- **The holdout is spent.** Per the protocol, nothing more is judged on 2025-01 → 2026-10; any next step is a
  forward paper test.
