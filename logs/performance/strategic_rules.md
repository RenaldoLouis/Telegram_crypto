# Strategic Rules (derived from 295 evaluated trades — solid sample)
_Last updated: 2026-07-30 10:54 UTC_

0. **v11.3 VALIDATED**: 58 forward trades at 52% WR / +0.15R exp (targets 34% / +0.00R). The change is working — maintain it.

1. **MODERATE SELECTIVITY**: Win rate is 35%. ACTION: Output 2-4 setups per run. Prefer fewer, higher-conviction setups over padding to 5.
2. **CONFIDENCE MISCALIBRATED**: 'High' confidence is 3/11 (27% WR) but 'Medium' is 86/241 (36% WR). ACTION: Reserve 'high confidence' for setups with 3/4 TF confluence + volume confirmed + clean structure. Do NOT equate 4/4 confluence with high confidence (see confluence rule below). If unsure, label 'medium' — it actually performs better.
3. **3/4 CONFLUENCE BEATS 4/4**: 3/4 TF is 86/202 (43% WR, +0.05 avg R:R) but 4/4 TF is 13/67 (19% WR, -0.31 avg R:R). 4/4 alignment = exhausted/late move, not higher probability. ACTION: Treat 3/4 confluence as the sweet spot. When all 4 TFs already agree, the move is likely mature — demand a fresh pullback/retest entry or SKIP; never rank a 4/4 setup #1 just because it is 4/4.
4. **'failed_breakout' STRUGGLING** (7 trades): 0% WR, -1.00 avg R:R. ACTION: Apply extra scrutiny — check entries and stops.
5. **TARGETS TOO FAR**: Predicted avg 1.6R but actual is -0.09R (gap: 1.7R). Average MFE is 1.0R, so set T1 at max 0.7R from entry. Backtest: T1 at 0.75R would hit 55% of trades, T1 at 1.0R would hit 42% (vs current T1 hit rate of 107/295 = 36%). ACTION: Place T1 at the nearest REAL structural level. Use ATR: T1 should be 1.5-2× ATR from entry, NOT 3×+.
6. **WINNING SYMBOLS**: 1000BONKUSDT (6/6), FARTCOINUSDT (3/4), SKHYNIXUSDT (2/3). ACTION: Give these symbols slight priority when they appear in the scan.
7. **LOSING SYMBOLS**: WLDUSDT (0/5), ONDOUSDT (0/3), ZECUSDT (0/3), HYPEUSDT (0/3). ACTION: Require 3/4+ TF confluence + volume confirmed for these symbols. Do not include as filler.
8. **IMPROVING**: 2026-06 was 20% → 2026-07 is 47%. Current approach is working — maintain it.
9. **PARTIAL PROFIT HELPS**: With 50% close at T1 + BE stop, blended WR is 46% (vs raw 35%), avg blended R:R -0.09. ACTION: Always recommend taking 50% profit at T1 and moving stop to breakeven.
10. **BEST MODEL**: claude-sonnet-4-6 (35% WR, -0.07 avg R:R). Consider using this model for production runs.
11. **CAUTIOUS REGIME STRONG**: 17/37 (46% WR, +0.12 avg R:R over 37 trades). ACTION: During cautious, maintain current approach — it's working.
12. **EFFECTIVE RULES**: validated_signal (21/37=57%, +0.19R), regime_cautious (16/35=46%, +0.13R), short_bias (34/73=47%, +0.09R). ACTION: Continue applying these rules — they correlate with positive expectancy.
