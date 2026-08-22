# Strategic Rules (derived from 339 evaluated trades — solid sample)
_Last updated: 2026-08-22 07:42 UTC_

0. **v11.3 NOT VALIDATING — REVIEW NEEDED**: 102 forward trades only reached 43% WR / -0.05R exp vs targets 34% / +0.00R. ACTION: the last change did NOT deliver — re-audit before adding more rules (do not pile on new delta insights, that is how the bad-logic loop returns).

1. **MODERATE SELECTIVITY**: Win rate is 34%. ACTION: Output 2-4 setups per run. Prefer fewer, higher-conviction setups over padding to 5.
2. **CONFIDENCE MISCALIBRATED**: 'High' confidence is 3/11 (27% WR) but 'Medium' is 100/285 (35% WR). ACTION: Reserve 'high confidence' for setups with 3/4 TF confluence + volume confirmed + clean structure. Do NOT equate 4/4 confluence with high confidence (see confluence rule below). If unsure, label 'medium' — it actually performs better.
3. **3/4 CONFLUENCE BEATS 4/4**: 3/4 TF is 97/242 (40% WR, -0.02 avg R:R) but 4/4 TF is 16/71 (23% WR, -0.27 avg R:R). 4/4 alignment = exhausted/late move, not higher probability. ACTION: Treat 3/4 confluence as the sweet spot. When all 4 TFs already agree, the move is likely mature — demand a fresh pullback/retest entry or SKIP; never rank a 4/4 setup #1 just because it is 4/4.
4. **'failed_breakout' STRUGGLING** (12 trades): 8% WR, -0.76 avg R:R. ACTION: Apply extra scrutiny — check entries and stops.
5. **TARGETS TOO FAR**: Predicted avg 1.5R but actual is -0.12R (gap: 1.6R). Average MFE is 0.9R, so set T1 at max 0.7R from entry. Backtest: T1 at 0.75R would hit 50% of trades, T1 at 1.0R would hit 38% (vs current T1 hit rate of 117/339 = 35%). ACTION: Place T1 at the nearest REAL structural level. Use ATR: T1 should be 1.5-2× ATR from entry, NOT 3×+.
6. **WINNING SYMBOLS**: 1000BONKUSDT (6/7), FARTCOINUSDT (4/5), DEXEUSDT (3/4), VANRYUSDT (2/3), EWYUSDT (2/3). ACTION: Give these symbols slight priority when they appear in the scan.
7. **LOSING SYMBOLS**: WLDUSDT (0/6), ONDOUSDT (0/3), ZECUSDT (0/3), HYPEUSDT (0/3), SOXLUSDT (0/3). ACTION: Require 3/4+ TF confluence + volume confirmed for these symbols. Do not include as filler.
8. **DECLINING**: 2026-07 was 46% → 2026-08 is 28%. ACTION: Tighten entries and widen stops. Review if market regime changed.
9. **PARTIAL PROFIT HELPS**: With 50% close at T1 + BE stop, blended WR is 44% (vs raw 34%), avg blended R:R -0.14. ACTION: Always recommend taking 50% profit at T1 and moving stop to breakeven.
10. **BEST MODEL**: claude-sonnet-4-6 (35% WR, -0.11 avg R:R). Consider using this model for production runs.
11. **NEUTRAL REGIME LOSING**: 75/245 (31% WR, -0.17 avg R:R over 245 trades). ACTION: During neutral, reduce to max 1-2 setups and require 3/4 TF + volume + fresh entry.
12. **EFFECTIVE RULES**: regime_cautious (16/38=42%, +0.07R). ACTION: Continue applying these rules — they correlate with positive expectancy.
13. **INEFFECTIVE RULES**: partial_profit (11/33=33%, -0.16R). ACTION: Stop leaning on these rules — they correlate with net losses.
