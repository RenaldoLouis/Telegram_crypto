# Strategic Rules (derived from 324 evaluated trades — solid sample)
_Last updated: 2026-08-06 05:29 UTC_

0. **v11.3 VALIDATED**: 87 forward trades at 46% WR / +0.01R exp (targets 34% / +0.00R). The change is working — maintain it.

1. **MODERATE SELECTIVITY**: Win rate is 35%. ACTION: Output 2-4 setups per run. Prefer fewer, higher-conviction setups over padding to 5.
2. **CONFIDENCE MISCALIBRATED**: 'High' confidence is 3/11 (27% WR) but 'Medium' is 96/270 (36% WR). ACTION: Reserve 'high confidence' for setups with 3/4 TF confluence + volume confirmed + clean structure. Do NOT equate 4/4 confluence with high confidence (see confluence rule below). If unsure, label 'medium' — it actually performs better.
3. **3/4 CONFLUENCE BEATS 4/4**: 3/4 TF is 94/228 (41% WR, +0.01 avg R:R) but 4/4 TF is 15/70 (21% WR, -0.30 avg R:R). 4/4 alignment = exhausted/late move, not higher probability. ACTION: Treat 3/4 confluence as the sweet spot. When all 4 TFs already agree, the move is likely mature — demand a fresh pullback/retest entry or SKIP; never rank a 4/4 setup #1 just because it is 4/4.
4. **'failed_breakout' STRUGGLING** (8 trades): 0% WR, -1.00 avg R:R. ACTION: Apply extra scrutiny — check entries and stops.
5. **TARGETS TOO FAR**: Predicted avg 1.5R but actual is -0.10R (gap: 1.6R). Average MFE is 1.0R, so set T1 at max 0.7R from entry. Backtest: T1 at 0.75R would hit 52% of trades, T1 at 1.0R would hit 39% (vs current T1 hit rate of 113/324 = 35%). ACTION: Place T1 at the nearest REAL structural level. Use ATR: T1 should be 1.5-2× ATR from entry, NOT 3×+.
6. **WINNING SYMBOLS**: 1000BONKUSDT (6/6), FARTCOINUSDT (4/5), VANRYUSDT (2/3), EWYUSDT (2/3). ACTION: Give these symbols slight priority when they appear in the scan.
7. **LOSING SYMBOLS**: WLDUSDT (0/6), ONDOUSDT (0/3), ZECUSDT (0/3), HYPEUSDT (0/3). ACTION: Require 3/4+ TF confluence + volume confirmed for these symbols. Do not include as filler.
8. **DECLINING**: 2026-07 was 46% → 2026-08 is 29%. ACTION: Tighten entries and widen stops. Review if market regime changed.
9. **PARTIAL PROFIT HELPS**: With 50% close at T1 + BE stop, blended WR is 45% (vs raw 35%), avg blended R:R -0.12. ACTION: Always recommend taking 50% profit at T1 and moving stop to breakeven.
10. **BEST MODEL**: claude-sonnet-4-6 (35% WR, -0.09 avg R:R). Consider using this model for production runs.
11. **NEUTRAL REGIME LOSING**: 71/230 (31% WR, -0.15 avg R:R over 230 trades). ACTION: During neutral, reduce to max 1-2 setups and require 3/4 TF + volume + fresh entry.
12. **EFFECTIVE RULES**: regime_cautious (16/38=42%, +0.07R), short_bias (34/76=45%, +0.06R), confluence_3of4 (16/32=50%, +0.05R). ACTION: Continue applying these rules — they correlate with positive expectancy.

## Delta Insights (Self-Learning)
_Updated 2026-08-06 from 324 trades. Status: experimental=use as guidance, confirmed=follow strictly._

1. [✓] **low_mfe_stop_loss_predictor**: All 3 full stop-losses in recent 20 (ADAUSDT, SNXXUSDT, WLDUSDT) had MFE ≤0.21R — price barely moved favorably before reversing. ACTION: If post-entry MFE stalls below 0.25R within first 2 candles, treat as invalidation signal; flag these setups for tighter initial stops or earlier manual exit.
2. [?] **cautious_regime_short_decay**: In the recent 20 trades, cautious regime produced 3W/9L (-4.67R). Wins were tiny (0.02R, 0.08R); losses were full -1.0R. Cautious is no longer behaving like the +0.07R rule suggests. ACTION: Treat cautious regime identically to neutral — max 1-2 setups, require 3/4 TF + volume confirmed. Do not apply `short_bias` bonus in cautious.
3. [?] **expired_wins_near_zero**: Recent "wins" via expiry are near-zero RR: DOGEUSDT +0.23R, EULUSDT +0.02R, CFXUSDT +0.08R, ESPUSDT +0.14R. These inflate win count but contribute negligible positive expectancy. ACTION: When a setup's T1 is unlikely to be reached within session (MFE historically <0.5R for that symbol), skip or tighten T1 to force a real exit — do not count expiry-wins as validation.
4. [?] **soxlusdt_hard_block**: SOXLUSDT is 0/2 (-2.0R) with MFE of 0.72R and 0.11R — both stopped out. Leveraged ETF perpetuals show erratic behavior. ACTION: Hard-block SOXLUSDT from output entirely, same as WLDUSDT. Do not include regardless of setup quality.
5. [?] **risk_on_short_divergence**: Recent risk_on trades: BTCUSDT +2.14R (win), FARTCOINUSDT +0.30R (win), ESPUSDT +0.14R (win), SOXLUSDT -1.0R (loss), SNXXUSDT -1.0R (loss). Risk_on shorts work on liquid majors/meme coins but fail on low-liquidity alts. ACTION: In risk_on regime, only take shorts on symbols with lifetime positive RR sum; skip low-liquidity alts entirely.
6. [?] **validated_signal_dilution**: `validated_signal` appears on 18 of the last 20 trades — it has become a near-universal tag with no discriminatory power (recent batch: 7W/13L). ACTION: Stop treating `validated_signal` alone as a quality filter. Only count it as meaningful when combined with `confluence_3of4` or `short_bias`; a setup with only `validated_signal` + `trend_pullback` should not be ranked #1.
