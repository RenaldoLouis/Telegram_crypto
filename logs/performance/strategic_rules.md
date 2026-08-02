# Strategic Rules (derived from 306 evaluated trades — solid sample)
_Last updated: 2026-08-02 04:00 UTC_

0. **v11.3 VALIDATED**: 69 forward trades at 48% WR / +0.05R exp (targets 34% / +0.00R). The change is working — maintain it.

1. **MODERATE SELECTIVITY**: Win rate is 34%. ACTION: Output 2-4 setups per run. Prefer fewer, higher-conviction setups over padding to 5.
2. **CONFIDENCE MISCALIBRATED**: 'High' confidence is 3/11 (27% WR) but 'Medium' is 89/252 (35% WR). ACTION: Reserve 'high confidence' for setups with 3/4 TF confluence + volume confirmed + clean structure. Do NOT equate 4/4 confluence with high confidence (see confluence rule below). If unsure, label 'medium' — it actually performs better.
3. **3/4 CONFLUENCE BEATS 4/4**: 3/4 TF is 88/212 (42% WR, +0.02 avg R:R) but 4/4 TF is 14/68 (21% WR, -0.30 avg R:R). 4/4 alignment = exhausted/late move, not higher probability. ACTION: Treat 3/4 confluence as the sweet spot. When all 4 TFs already agree, the move is likely mature — demand a fresh pullback/retest entry or SKIP; never rank a 4/4 setup #1 just because it is 4/4.
4. **'failed_breakout' STRUGGLING** (7 trades): 0% WR, -1.00 avg R:R. ACTION: Apply extra scrutiny — check entries and stops.
5. **TARGETS TOO FAR**: Predicted avg 1.6R but actual is -0.10R (gap: 1.7R). Average MFE is 1.0R, so set T1 at max 0.7R from entry. Backtest: T1 at 0.75R would hit 54% of trades, T1 at 1.0R would hit 41% (vs current T1 hit rate of 111/306 = 36%). ACTION: Place T1 at the nearest REAL structural level. Use ATR: T1 should be 1.5-2× ATR from entry, NOT 3×+.
6. **WINNING SYMBOLS**: 1000BONKUSDT (6/6), FARTCOINUSDT (3/4), VANRYUSDT (2/3), EWYUSDT (2/3). ACTION: Give these symbols slight priority when they appear in the scan.
7. **LOSING SYMBOLS**: WLDUSDT (0/5), ONDOUSDT (0/3), ZECUSDT (0/3), HYPEUSDT (0/3). ACTION: Require 3/4+ TF confluence + volume confirmed for these symbols. Do not include as filler.
8. **IMPROVING**: 2026-06 was 20% → 2026-07 is 45%. Current approach is working — maintain it.
9. **PARTIAL PROFIT HELPS**: With 50% close at T1 + BE stop, blended WR is 45% (vs raw 34%), avg blended R:R -0.11. ACTION: Always recommend taking 50% profit at T1 and moving stop to breakeven.
10. **BEST MODEL**: claude-sonnet-4-6 (35% WR, -0.09 avg R:R). Consider using this model for production runs.
11. **CAUTIOUS REGIME STRONG**: 18/39 (46% WR, +0.11 avg R:R over 39 trades). ACTION: During cautious, maintain current approach — it's working.
12. **EFFECTIVE RULES**: regime_cautious (16/35=46%, +0.13R), short_bias (34/73=47%, +0.09R), confluence_3of4 (16/32=50%, +0.05R). ACTION: Continue applying these rules — they correlate with positive expectancy.
