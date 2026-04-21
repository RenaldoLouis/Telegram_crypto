# Crypto Market Specifics

> Crypto is not equities. The rules are different. This file captures the *specific* dynamics of crypto markets that make them unique — and how to exploit / avoid being exploited by them.

---

## How Crypto Differs from Traditional Markets

| Factor | Traditional | Crypto |
|---|---|---|
| Hours | 9:30 – 16:00 weekdays | 24/7/365 |
| Participants | Mostly institutional | Mix of retail + whales + market makers |
| Leverage (retail) | 2-4x max | Up to 100x on many exchanges |
| Market-moving news | Earnings, Fed | Exchange news, regulatory, on-chain events, tweets |
| Correlation | Varies | Very high — most alts correlate 0.7+ with BTC |
| Volatility (daily) | 0.5-2% typical | 3-10% normal, 20%+ during events |
| Liquidity fragmentation | Low (few venues) | High (100+ exchanges, DEXs, OTC) |
| Transparency | Quarterly reporting | On-chain, real-time |
| Weekend behavior | Closed | Often thin, manipulable |

**Implication:** strategies from equities don't transfer 1:1. Position sizing must account for higher vol. Weekends and holidays are different animals.

---

## The Bitcoin Dominance Rule

- When **BTC is stable or rising**, alts tend to rally (alt season).
- When **BTC is crashing**, alts crash harder — historically ~1.5-2× the BTC drawdown.
- When **BTC is pumping hard**, liquidity flows out of alts *into* BTC — many alts underperform despite overall market being "up."

**Rule**: always check BTC first. Even if your setup is on SOL, the trade depends on what BTC is doing.

### Bitcoin Dominance (BTC.D)
- Rising BTC.D + rising BTC = BTC-only rally. Alts lag.
- Falling BTC.D + rising BTC = altseason. Alts outperform.
- Rising BTC.D + falling BTC = flight to BTC. Alts bleed.
- Falling BTC.D + falling BTC = rare. Often precedes alt capitulation.

---

## The Bitcoin 4-Year Cycle

Historically, BTC has followed a roughly 4-year cycle driven by the halving:

1. **Year 1 (post-halving)**: Recovery / slow accumulation.
2. **Year 2 (bull year)**: Markup begins. New ATH typically set.
3. **Year 3 (parabolic then correction)**: Speculative excess, blowoff top, followed by 60-80% drawdown.
4. **Year 4 (bear/accumulation)**: Consolidation, accumulation at lows.

Most recent halvings: 2012, 2016, 2020, 2024. Each was followed by the above pattern with variation.

**Implication for strategy:**
- Know what part of the cycle you're in. It changes your bias:
  - Bull year → favor long setups, take pullbacks as buys.
  - Bear year → favor short setups, sell rallies.
  - Accumulation → range-trade, wait for clear breakout.
  - Distribution → reduce size, prepare for the flip.

**Caveat**: cycles can change. 2024-2025 has seen institutional flows (ETFs, corporations) distort historical patterns. Always defer to price action, not calendar expectation.

---

## Perpetual Futures Mechanics (Bybit Specific)

### What you need to know:

1. **Funding rate**: paid every 8 hours (Bybit: 00:00, 08:00, 16:00 UTC).
   - Longs pay shorts when positive.
   - Shorts pay longs when negative.
   - Rates > +0.05% or < -0.05% per 8h are extreme.

2. **Mark Price vs Last Price**:
   - Liquidations use **mark price** (a weighted index of major spot exchanges), not the volatile last price on the exchange.
   - This is a *protection* for traders — prevents liquidation from wick spikes on the Bybit book alone.

3. **Liquidation price**:
   - Depends on margin mode (isolated vs cross), leverage, position size.
   - Always know your liquidation price before entering. Should be at least 2× further than your stop loss.

4. **Insurance fund / Auto-Deleveraging (ADL)**:
   - If a position's losses exceed its margin, the insurance fund absorbs it.
   - If insurance fund is depleted, ADL may close profitable opposite positions to balance the book.
   - Very rare in normal conditions, but happens during extreme volatility.

### Margin Modes
- **Isolated Margin**: each position has its own margin. Liquidation of one doesn't affect others. Safer for individual trades.
- **Cross Margin**: all positions share account margin. Liquidation of one can cascade. Only use if you know exactly what you're doing.

**Recommendation for Phase A**: always use isolated margin. Clearer risk, no surprises.

---

## Crypto-Specific High-Probability Setups

### 1. Funding Flip Reversal
- Funding rate has been positive for days (or negative), then flips.
- Often marks short-term extremes.
- Combine with price action: funding flips + price rejection at resistance → short setup.

### 2. Weekend Liquidity Squeeze
- Volume drops on Saturdays/Sundays.
- Whales can move price more easily with smaller capital.
- Weekend breakouts often fake; weekend crashes often reverse by Monday.
- **Rule**: be skeptical of weekend moves, wait for Monday volume to confirm.

### 3. Post-Liquidation Bounce / Flush
- Major liquidation cascade (visible on Coinglass) → often marks local low.
- Look for: big red candle, huge volume, long-tail wick, then rapid reclaim of prior level.
- High win rate reversal setup.

### 4. CME Gap Fill
- Bitcoin's CME futures close weekends; BTC spot trades 24/7.
- When spot moves during CME closure, a "gap" is created when CME reopens Sunday evening UTC.
- Historically, ~70-80% of CME gaps fill within days.
- Useful as a target/magnetic level — not a primary setup.

### 5. Altcoin BTC-Lag Rotation
- BTC rallies hard → alts lag for 1-3 days → alt catch-up rally when BTC stabilizes.
- Watch for BTC to stop making new highs + alts starting to tick up → altseason beginning.

### 6. Exchange Reserves Outflow / Inflow
- Large outflows from exchanges = coins going to self-custody = bullish (less sell pressure).
- Large inflows = coins moving to exchanges = often bearish (preparing to sell).
- Data: CryptoQuant, Glassnode, Santiment.

### 7. Spot vs Perp Basis
- **Perp price > Spot price** = contango → longs paying. Bullish-biased positioning.
- **Perp price < Spot price** = backwardation → shorts paying. Bearish-biased or fear.
- Extreme backwardation on spot-led rallies is a bullish signal.

---

## Crypto-Specific Risks

### 1. Exchange Risk
- Not your keys, not your coins.
- CEX insolvency: FTX (2022), Mt. Gox (2014), Celsius, BlockFi, etc.
- **Rule**: don't keep more than 1-2 months of trading capital on any single exchange.
- Withdraw profits regularly to cold storage.

### 2. Liquidation Hunts / Wicks
- Whales and market makers can intentionally push price to liquidation clusters.
- Wide stops and ≤2× leverage buffer help avoid being hunted.

### 3. Regulatory Events
- Sudden bans, SEC actions, tax policies move markets fast.
- Indonesian users: Kominfo blocks, Bappebti regulations can affect access overnight.
- Have a backup exchange, backup on-ramp, and backup VPN.

### 4. Smart Contract Risk (DeFi)
- For DeFi trading, smart contract exploits, rug pulls, oracle attacks.
- For CEX perps (Bybit, Binance), this risk is low but not zero.

### 5. Correlation Breakdown During Stress
- In normal conditions, many alts have 0.7-0.9 correlation with BTC.
- During extreme stress (March 2020, May 2022, FTX collapse): correlation goes to 1.
- Your "diversified" crypto portfolio all moves together. Plan accordingly.

### 6. News / Social Velocity
- Single tweet can move markets 10%+.
- Telegram / Twitter trends lead price more than in equities.
- **Dangerous for automated systems** that can't understand context.

---

## Common Crypto Trader Mistakes

1. **Leveraging into volatile alts**: 10x on a low-cap alt = near-certain liquidation.
2. **Ignoring funding rates**: paying 0.1% per 8h is 110%+ annualized drag.
3. **Trading during FOMO / panic**: emotional responses to 10%+ moves.
4. **Not checking BTC**: "my alt setup" ignoring the whole market is trending down.
5. **Assuming the 4-year cycle will repeat exactly**: it may, it may not.
6. **Overtrading weekends**: low liquidity = whipsaw = small account death.
7. **Trusting "signals" from Telegram without verification**: many are pump coordinators.
8. **Holding through major news events**: no point being right on TA if a Black Swan happens.
9. **Not taking profit**: "it'll go higher" — unrealized gains aren't real gains.
10. **Averaging down on losers**: crypto drawdowns can be 80-95%. Averaging down can destroy accounts.

---

## Sources for Crypto Intelligence

### For Real-Time Data
- **Bybit / Binance / OKX**: primary spot and perp data.
- **Coinglass**: liquidations, funding rates aggregated, OI heatmaps.
- **CryptoQuant**: on-chain + exchange flow data.
- **Glassnode**: on-chain metrics, long-term holder behavior.
- **TradingView**: charting, indicator community.

### For News
- **Laura Shin** (podcast, articles)
- **The Block**, **CoinDesk**, **CoinTelegraph** — primary.
- **Bitcoin Magazine** for BTC-specific.

### For Community Signal (with skepticism)
- Crypto Twitter (CT) — huge noise, occasional signal from proven accounts.
- Telegram signal groups — mostly noise. Use as sentiment proxy, not setup source.
- Reddit (r/cryptocurrency, r/bitcoinmarkets) — occasional sharp posts, mostly retail sentiment.

### For Research
- **Messari**: deep crypto research reports.
- **Delphi Digital**: professional research (some paid).
- **Artemis**: on-chain + fundamentals.

---

## How Claude Should Apply This

When producing briefs:

1. **Always anchor analysis to BTC.** If BTC context isn't clear, alt setups are unreliable.
2. **State current cycle bias** when relevant (e.g., "Currently in mid-bull cycle territory" — if that's true at the time).
3. **Flag weekend setups with additional caution.**
4. **Flag funding rate extremes** as squeeze setup potential, not as primary signal.
5. **For alts, always note correlation to BTC.** A "strong alt setup" during a BTC breakdown is a weak trade.
6. **Call out news risk** if a major scheduled event is within 24h (FOMC, CPI, major unlocks, etc.).
7. **Never recommend adding risk on low-volume weekends or in thin markets.**
