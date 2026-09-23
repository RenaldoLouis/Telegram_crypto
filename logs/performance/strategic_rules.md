# Strategic Rules (derived from 353 evaluated trades — solid sample)
_Last updated: 2026-09-23 10:04 UTC_

0. **v13.0 UNPROVEN (MONITOR)**: deployed 2026-09-23; 0 v2-engine forward trades yet. Target ≥70% profitable (net, partial model) and net exp > +0.00R over 30 trades; baseline (pre-fix, not comparable) 43.1% profitable / -0.178R net. ACTION: nothing is proven until the forward book says so.

1. **MODERATE SELECTIVITY**: Win rate is 35%. ACTION: Output 2-4 setups per run. Prefer fewer, higher-conviction setups over padding to 5.
2. **CONFIDENCE MISCALIBRATED**: 'High' confidence is 3/11 (27% WR) but 'Medium' is 109/299 (36% WR). ACTION: Reserve 'high confidence' for setups with 3/4 TF confluence + volume confirmed + clean structure. Do NOT equate 4/4 confluence with high confidence (see confluence rule below). If unsure, label 'medium' — it actually performs better.
3. **3/4 CONFLUENCE BEATS 4/4**: 3/4 TF is 106/256 (41% WR, -0.01 avg R:R) but 4/4 TF is 16/71 (23% WR, -0.27 avg R:R). 4/4 alignment = exhausted/late move, not higher probability. ACTION: Treat 3/4 confluence as the sweet spot. When all 4 TFs already agree, the move is likely mature — demand a fresh pullback/retest entry or SKIP; never rank a 4/4 setup #1 just because it is 4/4.
4. **'failed_breakout' STRUGGLING** (12 trades): 8% WR, -0.76 avg R:R. ACTION: Apply extra scrutiny — check entries and stops.
5. **TARGETS TOO FAR**: Predicted avg 1.5R but actual is -0.11R (gap: 1.6R). Average MFE is 0.9R, so set T1 at max 0.7R from entry. Backtest: T1 at 0.75R would hit 51% of trades, T1 at 1.0R would hit 38% (vs current T1 hit rate of 126/353 = 36%). ACTION: Place T1 at the nearest REAL structural level. Use ATR: T1 should be 1.5-2× ATR from entry, NOT 3×+.
6. **WINNING SYMBOLS**: 1000BONKUSDT (6/7), FARTCOINUSDT (5/6), DEXEUSDT (3/4), VANRYUSDT (2/3), EWYUSDT (2/3). ACTION: Give these symbols slight priority when they appear in the scan.
7. **LOSING SYMBOLS**: WLDUSDT (0/6), ONDOUSDT (0/3), ZECUSDT (0/3), HYPEUSDT (0/3). ACTION: Require 3/4+ TF confluence + volume confirmed for these symbols. Do not include as filler.
8. **IMPROVING**: 2026-08 was 33% → 2026-09 is 60%. Current approach is working — maintain it.
9. **PARTIAL PROFIT HELPS**: With 50% close at T1 + BE stop, blended WR is 46% (vs raw 35%), avg blended R:R -0.12. ACTION: Always recommend taking 50% profit at T1 and moving stop to breakeven.
10. **BEST MODEL**: claude-sonnet-4-6 (36% WR, -0.10 avg R:R). Consider using this model for production runs.
11. **NEUTRAL REGIME LOSING**: 79/252 (31% WR, -0.16 avg R:R over 252 trades). ACTION: During neutral, reduce to max 1-2 setups and require 3/4 TF + volume + fresh entry.
12. **EFFECTIVE RULES**: regime_cautious (16/38=42%, +0.07R), trend_pullback (29/55=53%, +0.02R). ACTION: Continue applying these rules — they correlate with positive expectancy.
13. **INEFFECTIVE RULES**: partial_profit (11/33=33%, -0.16R). ACTION: Stop leaning on these rules — they correlate with net losses.
