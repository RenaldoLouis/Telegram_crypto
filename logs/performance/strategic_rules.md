# Strategic Rules (derived from 277 evaluated trades — solid sample)
_Last updated: 2026-07-23 06:36 UTC_

0. **v11.3 VALIDATED**: 40 forward trades at 45% WR / +0.07R exp (targets 34% / +0.00R). The change is working — maintain it.

1. **MODERATE SELECTIVITY**: Win rate is 32%. ACTION: Output 2-4 setups per run. Prefer fewer, higher-conviction setups over padding to 5.
2. **CONFIDENCE MISCALIBRATED**: 'High' confidence is 2/9 (22% WR) but 'Medium' is 75/225 (33% WR). ACTION: Reserve 'high confidence' for setups with 3/4 TF confluence + volume confirmed + clean structure. Do NOT equate 4/4 confluence with high confidence (see confluence rule below). If unsure, label 'medium' — it actually performs better.
3. **3/4 CONFLUENCE BEATS 4/4**: 3/4 TF is 74/184 (40% WR, +0.03 avg R:R) but 4/4 TF is 13/67 (19% WR, -0.31 avg R:R). 4/4 alignment = exhausted/late move, not higher probability. ACTION: Treat 3/4 confluence as the sweet spot. When all 4 TFs already agree, the move is likely mature — demand a fresh pullback/retest entry or SKIP; never rank a 4/4 setup #1 just because it is 4/4.
4. **'failed_breakout' STRUGGLING** (7 trades): 0% WR, -1.00 avg R:R. ACTION: Apply extra scrutiny — check entries and stops.
5. **TARGETS TOO FAR**: Predicted avg 1.7R but actual is -0.11R (gap: 1.8R). Average MFE is 1.0R, so set T1 at max 0.8R from entry. Backtest: T1 at 0.75R would hit 54% of trades, T1 at 1.0R would hit 43% (vs current T1 hit rate of 95/277 = 34%). ACTION: Place T1 at the nearest REAL structural level. Use ATR: T1 should be 1.5-2× ATR from entry, NOT 3×+.
6. **WINNING SYMBOLS**: SKHYNIXUSDT (2/3). ACTION: Give these symbols slight priority when they appear in the scan.
7. **LOSING SYMBOLS**: WLDUSDT (0/4), ONDOUSDT (0/3), ZECUSDT (0/3), HYPEUSDT (0/3). ACTION: Require 3/4+ TF confluence + volume confirmed for these symbols. Do not include as filler.
8. **IMPROVING**: 2026-06 was 20% → 2026-07 is 43%. Current approach is working — maintain it.
9. **PARTIAL PROFIT HELPS**: With 50% close at T1 + BE stop, blended WR is 43% (vs raw 32%), avg blended R:R -0.13. ACTION: Always recommend taking 50% profit at T1 and moving stop to breakeven.
10. **BEST MODEL**: claude-sonnet-4-6 (33% WR, -0.10 avg R:R). Consider using this model for production runs.
11. **EFFECTIVE RULES**: regime_cautious (16/35=46%, +0.13R), short_bias (30/67=45%, +0.08R), confluence_3of4 (12/26=46%, +0.02R). ACTION: Continue applying these rules — they correlate with positive expectancy.
