# Strategic Rules (derived from 336 evaluated trades — solid sample)
_Last updated: 2026-08-12 02:44 UTC_

0. **v11.3 NOT VALIDATING — REVIEW NEEDED**: 99 forward trades only reached 44% WR / -0.02R exp vs targets 34% / +0.00R. ACTION: the last change did NOT deliver — re-audit before adding more rules (do not pile on new delta insights, that is how the bad-logic loop returns).

1. **MODERATE SELECTIVITY**: Win rate is 35%. ACTION: Output 2-4 setups per run. Prefer fewer, higher-conviction setups over padding to 5.
2. **CONFIDENCE MISCALIBRATED**: 'High' confidence is 3/11 (27% WR) but 'Medium' is 100/282 (35% WR). ACTION: Reserve 'high confidence' for setups with 3/4 TF confluence + volume confirmed + clean structure. Do NOT equate 4/4 confluence with high confidence (see confluence rule below). If unsure, label 'medium' — it actually performs better.
3. **3/4 CONFLUENCE BEATS 4/4**: 3/4 TF is 97/239 (41% WR, -0.01 avg R:R) but 4/4 TF is 16/71 (23% WR, -0.27 avg R:R). 4/4 alignment = exhausted/late move, not higher probability. ACTION: Treat 3/4 confluence as the sweet spot. When all 4 TFs already agree, the move is likely mature — demand a fresh pullback/retest entry or SKIP; never rank a 4/4 setup #1 just because it is 4/4.
4. **'failed_breakout' STRUGGLING** (11 trades): 9% WR, -0.73 avg R:R. ACTION: Apply extra scrutiny — check entries and stops.
5. **TARGETS TOO FAR**: Predicted avg 1.5R but actual is -0.11R (gap: 1.6R). Average MFE is 1.0R, so set T1 at max 0.7R from entry. Backtest: T1 at 0.75R would hit 51% of trades, T1 at 1.0R would hit 39% (vs current T1 hit rate of 117/336 = 35%). ACTION: Place T1 at the nearest REAL structural level. Use ATR: T1 should be 1.5-2× ATR from entry, NOT 3×+.
6. **WINNING SYMBOLS**: 1000BONKUSDT (6/7), FARTCOINUSDT (4/5), DEXEUSDT (3/4), VANRYUSDT (2/3), EWYUSDT (2/3). ACTION: Give these symbols slight priority when they appear in the scan.
7. **LOSING SYMBOLS**: WLDUSDT (0/6), ONDOUSDT (0/3), ZECUSDT (0/3), HYPEUSDT (0/3), SOXLUSDT (0/3). ACTION: Require 3/4+ TF confluence + volume confirmed for these symbols. Do not include as filler.
8. **PARTIAL PROFIT HELPS**: With 50% close at T1 + BE stop, blended WR is 45% (vs raw 35%), avg blended R:R -0.12. ACTION: Always recommend taking 50% profit at T1 and moving stop to breakeven.
9. **BEST MODEL**: claude-sonnet-4-6 (35% WR, -0.10 avg R:R). Consider using this model for production runs.
10. **NEUTRAL REGIME LOSING**: 75/242 (31% WR, -0.16 avg R:R over 242 trades). ACTION: During neutral, reduce to max 1-2 setups and require 3/4 TF + volume + fresh entry.
11. **EFFECTIVE RULES**: regime_cautious (16/38=42%, +0.07R), short_bias (36/85=42%, +0.02R). ACTION: Continue applying these rules — they correlate with positive expectancy.
12. **INEFFECTIVE RULES**: partial_profit (11/33=33%, -0.16R). ACTION: Stop leaning on these rules — they correlate with net losses.
