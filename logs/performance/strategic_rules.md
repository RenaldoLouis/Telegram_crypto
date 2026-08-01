# Strategic Rules (derived from 298 evaluated trades — solid sample)
_Last updated: 2026-08-01 03:34 UTC_

0. **v11.3 VALIDATED**: 61 forward trades at 51% WR / +0.14R exp (targets 34% / +0.00R). The change is working — maintain it.

1. **MODERATE SELECTIVITY**: Win rate is 35%. ACTION: Output 2-4 setups per run. Prefer fewer, higher-conviction setups over padding to 5.
2. **CONFIDENCE MISCALIBRATED**: 'High' confidence is 3/11 (27% WR) but 'Medium' is 87/244 (36% WR). ACTION: Reserve 'high confidence' for setups with 3/4 TF confluence + volume confirmed + clean structure. Do NOT equate 4/4 confluence with high confidence (see confluence rule below). If unsure, label 'medium' — it actually performs better.
3. **3/4 CONFLUENCE BEATS 4/4**: 3/4 TF is 87/205 (42% WR, +0.05 avg R:R) but 4/4 TF is 13/67 (19% WR, -0.31 avg R:R). 4/4 alignment = exhausted/late move, not higher probability. ACTION: Treat 3/4 confluence as the sweet spot. When all 4 TFs already agree, the move is likely mature — demand a fresh pullback/retest entry or SKIP; never rank a 4/4 setup #1 just because it is 4/4.
4. **'failed_breakout' STRUGGLING** (7 trades): 0% WR, -1.00 avg R:R. ACTION: Apply extra scrutiny — check entries and stops.
5. **TARGETS TOO FAR**: Predicted avg 1.6R but actual is -0.09R (gap: 1.7R). Average MFE is 1.0R, so set T1 at max 0.7R from entry. Backtest: T1 at 0.75R would hit 56% of trades, T1 at 1.0R would hit 42% (vs current T1 hit rate of 109/298 = 37%). ACTION: Place T1 at the nearest REAL structural level. Use ATR: T1 should be 1.5-2× ATR from entry, NOT 3×+.
6. **WINNING SYMBOLS**: 1000BONKUSDT (6/6), FARTCOINUSDT (3/4), VANRYUSDT (2/3), SKHYNIXUSDT (2/3). ACTION: Give these symbols slight priority when they appear in the scan.
7. **LOSING SYMBOLS**: WLDUSDT (0/5), ONDOUSDT (0/3), ZECUSDT (0/3), HYPEUSDT (0/3). ACTION: Require 3/4+ TF confluence + volume confirmed for these symbols. Do not include as filler.
8. **IMPROVING**: 2026-06 was 20% → 2026-07 is 47%. Current approach is working — maintain it.
9. **PARTIAL PROFIT HELPS**: With 50% close at T1 + BE stop, blended WR is 46% (vs raw 35%), avg blended R:R -0.09. ACTION: Always recommend taking 50% profit at T1 and moving stop to breakeven.
10. **BEST MODEL**: claude-sonnet-4-6 (35% WR, -0.07 avg R:R). Consider using this model for production runs.
11. **EFFECTIVE RULES**: validated_signal (22/40=55%, +0.17R), regime_cautious (16/35=46%, +0.13R), short_bias (34/73=47%, +0.09R). ACTION: Continue applying these rules — they correlate with positive expectancy.

## Delta Insights (Self-Learning)
_Updated 2026-08-01 from 298 trades. Status: experimental=use as guidance, confirmed=follow strictly._

1. [?] **bonk_short_dominance**: 1000BONKUSDT shorts are 6/6 lifetime (100% WR, +4.03R), appearing across risk_on and neutral regimes with MFE consistently ≥0.77R. ACTION: When 1000BONKUSDT short appears with `validated_signal` + `trend_pullback`, rank it #1 automatically regardless of other candidates.
2. [?] **sui_be_stop_pattern**: SUIUSDT shorts triggered BE stop twice consecutively (MFE 0.85–0.86R, never reaching T1). Lifetime SUIUSDT is 2/11 (-1.61R). ACTION: For SUIUSDT shorts, set T1 tighter (≤0.7R) or skip entirely — price consistently reverses just before T1.
3. [?] **validated_signal_trend_pullback_combo**: Trades carrying both `validated_signal` AND `trend_pullback` rules in recent 20 went 8/12 (67% WR). This dual-rule combo is the strongest recent signal. ACTION: Prioritize setups where both rules apply simultaneously; deprioritize setups with only one of the two.
4. [?] **low_mfe_stop_loss_predictor**: All 3 full stop-losses in recent 20 (ADAUSDT, SNXXUSDT, WLDUSDT) had MFE ≤0.21R — price barely moved favorably before reversing. ACTION: If post-entry MFE stalls below 0.25R within first 2 candles, treat as invalidation signal; flag these setups for tighter initial stops or earlier manual exit.
5. [?] **wldusdt_symbol_avoid_ignored**: WLDUSDT appeared despite `symbol_avoid` rule being applied — and lost (-1.0R, MFE 0.17R). Lifetime 0/5. ACTION: Hard-block WLDUSDT from output entirely. Do not include even with `symbol_avoid` tag as a caveat — the rule is being applied but the setup is still being logged and losing.
6. [?] **cautious_regime_shorts_failing**: In the recent 20 trades, cautious-regime shorts went 1/8 (12% WR), with 5 full stops and near-zero MFE on failures. The regime label "cautious" is not filtering adequately — shorts are being taken anyway. ACTION: In cautious regime, require MFE signal (price must move 0.3R toward target before committing mentally) or skip shorts entirely unless confluence is 3/4 AND volume confirmed is present.
