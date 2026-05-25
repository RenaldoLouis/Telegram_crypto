# Setup Playbook — Your Trading Setups

> This is the user-editable file. Update it as your strategy evolves. The setups listed here are what Claude should look for when analyzing data. Setups NOT in this file should not be recommended.

---

## How This File Works

Each setup is a **template** Claude can match against market data. If current conditions match a setup's criteria, Claude includes it in the brief. If no setups match → "no trade today" is the correct output.

Add, remove, or refine setups based on your own experience. The 8 setups below are the most commonly profitable structures in crypto.

---

## Setup 1: HTF Trend Pullback

**Thesis**: strongest setup in crypto. Trade with the primary trend on a clean pullback.

### Criteria (ALL must be true)
- Daily trend is clearly up (higher highs + higher lows on daily) OR clearly down (opposite)
- Price has pulled back to 20 EMA or 50 EMA on 4H
- The pullback is corrective (3-5 candles, not an impulsive down-move)
- Lower timeframe (1H) shows a reversal signal: ChoCH back in trend direction, or bullish pin bar on support
- Volume on the pullback is declining (healthy retracement)

### Entry
- Enter on LTF confirmation (close of reversal candle, or break of pullback high)
- Scale in if wide zone (e.g., 50% on first signal, 50% on retest)

### Stop
- Below the pullback's swing low (long) or above the pullback's swing high (short)
- Roughly 1.5-2× ATR from entry

### Target
- Prior swing high (long) or swing low (short)
- Second target: 1.5× the pullback depth projected from entry
- Minimum R:R: 2:1

### Confidence Factors (+ higher conviction)
- BTC is moving in the same direction
- 50 and 200 EMA are stacked (50 above 200 for long, vice versa for short)
- Pullback touched a major horizontal S/R level

---

## Setup 2: Range Breakout with Retest

**Thesis**: Price breaks out of a consolidation range, then retests the broken level as new support/resistance.

### Criteria
- Clean horizontal range for 20+ candles on 4H or 1H
- Volume has been declining during the range (compression)
- Breakout candle closes beyond the range with 1.5×+ average volume
- Price returns to retest the broken level within 1-5 candles
- Retest holds (rejection wick, lower volume on retest)

### Entry
- On the retest hold — when LTF shows rejection (pin bar, engulfing)
- NOT on the initial breakout candle (too many fakeouts)

### Stop
- Back inside the range (below breakout level for long, above for short)

### Target
- Projected range height from the breakout point
- Example: range is $1,000 tall, breakout at $50,000 → target $51,000

### Confidence Factors
- Higher TF is trending in the breakout direction
- Range formed *after* a strong trending move (continuation pattern)
- Multiple failed attempts to break the opposite side strengthened the level

### Warning
- Low-volume breakouts often fail. Always require volume confirmation.
- Breakouts against major HTF trends usually fail — prefer with-trend breakouts.

---

## Setup 3: Wyckoff Spring Reversal

**Thesis**: False breakdown below a clear support range, followed by rapid reclaim. Highest R:R setup.

### Criteria
- Asset has been in a clear range for 15+ candles on 4H
- Range is at the bottom of a prior downtrend (accumulation context)
- Volume during the range has been declining (supply drying up)
- Price breaks below the range low (the "spring")
- Price reclaims the range within 1-3 candles
- Reclaim is on strong volume

### Entry
- On the reclaim — specifically when 4H candle closes back above the range low
- Aggressive entry: at the range low on signs of rejection
- Conservative entry: on retest of range low from above (the "Last Point of Support")

### Stop
- Below the spring low (the actual wick extreme)
- Typically 2-3% below entry

### Target
- Top of the range (first target)
- 1.5-2× the range height projected above (second target)
- Typical R:R: 3:1 to 5:1

### Confidence Factors
- Spring accompanied by visible long liquidations (Coinglass)
- Funding rate was negative before the spring (shorts crowded, fuel for rally)
- BTC.D is declining (altseason context)

---

## Setup 4: Liquidity Sweep / Stop Hunt Reversal

**Thesis**: Price wicks past an obvious S/R level where retail stops cluster, then reverses. "Money on the floor."

### Criteria
- Clear prior swing high or swing low visible on 4H/1H
- That level has been tested 2+ times and held
- Large amounts of open interest / long positions built up (visible on funding + OI)
- Price suddenly wicks past the level with large volume (stop hunt)
- Price reclaims back into the prior range within 1-3 candles

### Entry
- On the reclaim candle close
- Can use LTF (15M/5M) for precise entry timing

### Stop
- Beyond the wick extreme (tightest possible — use the actual high/low of the sweep)

### Target
- Opposite side of the prior range / structure
- Second target: next major S/R level
- Typical R:R: 2:1 to 4:1

### Warnings
- Only valid at MAJOR levels (prior ATH/ATL, weekly high/low, psychological levels like $60k, $70k)
- Minor level sweeps are just noise
- Requires quick execution — these reverse fast

---

## Setup 5: Funding Rate Squeeze

**Thesis**: Crowded positioning on one side + price stalling → squeeze setup against the crowd.

### Criteria
- Funding rate has been extreme for 24+ hours:
  - > +0.05% per 8h (longs crowded) — short setup
  - < -0.05% per 8h (shorts crowded) — long setup
- Price has stopped making new highs/lows in the direction of the crowd
- Open interest has grown significantly (10%+ over 24-48h)
- Technical structure supports the counter-trade (e.g., price at resistance with crowded longs)

### Entry
- On rejection of a recent swing high (short setup) or swing low (long setup)
- With LTF confirmation (ChoCH in counter-direction)

### Stop
- Beyond the recent swing extreme

### Target
- Prior range midpoint or opposite side
- Typical R:R: 2:1 to 3:1

### Why This Works
- When one side is crowded and paying funding, any adverse move triggers cascading liquidations.
- The squeeze is self-reinforcing — each liquidation creates more supply/demand flow against the crowd.

### Warnings
- Don't short just because funding is positive. Price action must confirm.
- Trends can stay "overbought" in funding terms. Use this at key technical levels only.

---

## Setup 6: Post-Liquidation Cascade Reversal

**Thesis**: Major liquidation flush clears out late entrants. Remaining positions are stronger hands. Reversal likely.

### Criteria
- Large liquidation event visible on Coinglass ($50M+ in a single 1H window for BTC/ETH, lower for alts)
- Price moved sharply in one direction (5%+ in under an hour)
- Volume spiked to 5x+ the 20-candle average
- Price rejected at or near a major S/R level
- Open interest declined sharply (longs being force-closed)
- Candle shows a long tail/wick in the direction of the flush

### Entry
- On reversal candle close (ideally engulfing the liquidation candle partially)
- LTF confirmation of trend change

### Stop
- Below the flush low (for long) — must be BELOW the wick

### Target
- Pre-flush level (first target) — this is where the move started
- Prior swing high/low (second target)
- Typical R:R: 3:1+

### Why This Works
- Liquidation cascades represent forced, non-discretionary selling/buying. It's emotional/structural, not informed.
- Once the cascade completes, price often rapidly returns toward fair value.

### Best Variant
- BTC flush during Asian hours (low liquidity) followed by European/US session reclaim → very reliable.

---

## Setup 7: Failed Breakout (Reversal on Distribution)

**Thesis**: Attempted breakout that fails = strong signal the move is done. Counter-trade.

### Criteria
- Strong trending move in one direction (daily trend)
- Price attempts to break a key resistance (up move) or support (down move)
- Breakout is weak: below-average volume, immediate reversal, wick only
- Price closes back inside the prior range/structure
- HTF shows signs of distribution (declining volume on highs) or accumulation (rising volume on lows)

### Entry
- After the failed breakout candle closes back inside
- Aggressive: at the failure
- Conservative: on retest of the former breakout level from the other side

### Stop
- Beyond the failed breakout high/low

### Target
- Opposite side of the prior range
- Typical R:R: 2:1 to 3:1

### Why This Works
- A failed breakout traps aggressive breakout traders.
- They become forced sellers (longs) or buyers (shorts) on the retrace, fueling the counter-move.

---

## Setup 8: ATH/ATL Exhaustion Reversal

**Thesis**: Parabolic move into ATH (or ATL) exhausts buyers (or sellers). Multi-timeframe overbought/oversold signals + volume divergence = high-probability mean reversion trade.

### Criteria (ALL must be true)
- Price is at or within 2% of the all-time high (for short) or all-time low (for long)
- RSI is overbought (>75) on at least 2 timeframes, ideally 3+ (short setup). Or oversold (<25) on 2+ TFs (long setup).
- Volume divergence: price making new highs but volume declining compared to the prior leg up (distribution signal). Or volume spike on the final push (climactic/blow-off top).
- At least one rejection signal: shooting star / long upper wick on 4H or 1D, bearish engulfing, or doji at the extreme.
- The move into ATH was parabolic: 3+ consecutive strong candles in one direction, accelerating.

### Entry
- On the first confirmed rejection candle close (shooting star, bearish engulfing on 4H or 1H)
- Aggressive: at the first 1H ChoCH away from the ATH after the rejection
- Conservative: wait for 4H ChoCH confirmation (lower high forming on 4H)
- Do NOT short into strength before a rejection signal — wait for the turn

### Stop
- Above the ATH wick extreme + small buffer (0.5-1% above the absolute high)
- This is tight because if price makes a new ATH after your entry, the thesis is dead

### Target
- T1: 0.618 Fibonacci retracement (golden pocket) of the most recent swing — measured from the swing low that started the parabolic move to the ATH. This is the highest-probability reversal zone.
- T2: 0.786 Fibonacci retracement or the prior 4H/1D structure support (whichever is closer)
- Minimum R:R: 2:1 (ATH setups should offer wide targets due to the extended nature of the move)

### Why This Works
- Parabolic moves are unsustainable. The last buyers at ATH are latecomers with tight stops.
- Multi-TF overbought RSI means momentum is exhausted across all participant timeframes.
- Volume divergence at ATH = smart money distributing while retail chases.
- ATH is a psychological level where profit-taking accelerates.
- The golden pocket (0.618 fib) is where institutional re-accumulation typically begins, making it a reliable T1.

### Confidence Factors (+ higher conviction)
- Funding rate highly positive (>0.03%) at ATH = longs extremely crowded, squeeze fuel for shorts
- Multiple TFs showing RSI >80 simultaneously (3/4 or 4/4)
- Daily candle closes as a shooting star or doji after the ATH touch
- BTC is showing weakness while the alt is at ATH (correlation breakdown)

### Warnings
- **This is NOT "shorting because it went up a lot."** The criteria require multi-TF exhaustion confirmation + rejection signals. A coin at ATH with healthy RSI and rising volume is a breakout, not an exhaustion — do not short it.
- Parabolic moves can extend further than expected. Never short before the rejection signal.
- Works best on coins with established trading history (prior swing lows to measure Fibonacci from).
- In strong bull markets (risk_on regime), ATH breakouts are more common than reversals — reduce conviction.

### ATL Exhaustion (Mirror for Longs)
- Same logic inverted: price at ATL, RSI <25 on 2+ TFs, volume divergence on the downside, hammer/bullish engulfing rejection.
- Target: 0.618 fib retracement of the decline (golden pocket from the swing high to the ATL).
- Works especially well during risk_off → neutral regime transitions.

---

## Setups to AVOID

These are common retail traps. Don't trade them, and Claude should never recommend them:

1. **Buying because "it's gone down a lot"** — falling knife catching.
2. **Shorting because "it's gone up a lot"** — fighting momentum. (Exception: Setup 8 ATH Exhaustion requires multi-TF overbought RSI + rejection signal, not just "big move up.")
3. **"Breakout" after 3+ green daily candles** — too late, already extended.
4. **RSI oversold / overbought alone** — can stay extreme for weeks in strong trends.
5. **Social media hype trades** — you're buying from the person who got in early.
6. **"I'll just buy a bit more to average down"** — not a setup. A prayer.
7. **Trading during major scheduled news without a news-trading plan.**

---

## How Claude Uses This Playbook

For each screening run:
1. **Check current market data against each setup's criteria.**
2. **A setup qualifies only if ALL criteria are met.** No partial matches.
3. **Rank qualifying setups by confidence factors** (more factors = higher conviction).
4. **Maximum 3 High-Conviction setups per brief.** If more qualify, take the top 3 by R:R and context.
5. **Report "no trade" explicitly** if nothing qualifies. This is correct behavior.
