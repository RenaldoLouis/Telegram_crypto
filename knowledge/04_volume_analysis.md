# Volume & Order Flow Analysis

> Synthesized from Wyckoff's Effort vs Result, Volume Spread Analysis (VSA), and modern order flow literature.

Price tells you *what* is happening. Volume tells you *how strong* it is. Together they tell the story.

---

## The Core Principle

> **Effort (volume) should be proportional to result (price movement).** When they diverge, something is happening beneath the surface.

---

## Wyckoff's Third Law: Effort vs. Result

- **High volume + big price move** in trend direction → legitimate, sustainable move.
- **High volume + small/no price move** → hidden supply/demand absorbing the effort. Warning sign.
- **Low volume + big price move** → thin liquidity, vulnerable. Unsustainable.
- **Low volume + small price move** → typical consolidation. No information.

---

## Volume Spike Interpretation

### What "high volume" means

- **2x+ the 20-candle average** = meaningful spike.
- **5x+ average** = exceptional event (news, liquidations, breakout).
- **10x+ average** = climactic — often marks exhaustion or key turning points.

### At key locations, spikes are significant:

| Location | Volume Spike Meaning |
|---|---|
| At support in downtrend | Potential climactic selling / capitulation (bullish) |
| At resistance in uptrend | Potential exhaustion / distribution (bearish) |
| On breakout above resistance | Validates breakout (if follow-through appears) |
| On breakdown below support | Validates breakdown |
| During consolidation | Accumulation or distribution happening |

### In the middle of a range with no context: volume spikes mean little.

---

## Volume Patterns That Matter

### 1. Volume Confirms Trend (Healthy)
In an uptrend:
- Rising candles should show **increasing volume**.
- Pullback candles should show **decreasing volume**.
- If this pattern holds → trend is healthy, continue trading it.

### 2. Volume Diverges from Trend (Warning)
- Price makes new high but volume is lower than prior highs → **bearish divergence**.
- Price makes new low but volume is lower than prior lows → **bullish divergence**.
- Divergence doesn't mean immediate reversal — it means momentum is weakening.

### 3. Climactic Volume (Exhaustion)
- After a strong trend, a massive volume spike with a reversal candle.
- "Selling climax" at lows: huge down-volume, then rally.
- "Buying climax" at highs: huge up-volume, then decline.
- Often marks major turning points.

### 4. Low Volume Breakout (Trap)
- Price breaks out of a range but volume is average or low.
- High probability of failure / fakeout.
- **Rule**: don't chase low-volume breakouts. Wait for a retest with volume.

### 5. Absorption
- Large volume prints but price barely moves.
- Indicates a big player absorbing the opposing flow.
- At support: bullish (big buyer absorbing sellers).
- At resistance: bearish (big seller absorbing buyers).
- Often precedes strong moves in the absorber's direction.

---

## Relative Volume (Critical Concept)

Raw volume numbers lie. Always use **relative volume**:

```
Relative Volume = Current Candle Volume / 20-candle SMA Volume
```

- Relative volume < 1 → below normal activity.
- Relative volume 1-2 → normal.
- Relative volume 2-5 → meaningfully elevated.
- Relative volume > 5 → unusual, investigate immediately.

This normalizes for:
- Weekend vs weekday volumes in crypto
- Low-cap vs large-cap differences
- Time-of-day variations (Asian vs European vs US sessions)

---

## Order Flow Concepts (Advanced)

For when simple volume isn't enough. These require tools like ATAS, Cignals, Bookmap, CoinGlass.

### Cumulative Volume Delta (CVD)
- **Delta** = buying volume (market orders hitting ask) − selling volume (market orders hitting bid).
- **CVD** is the running sum of delta over time.
- **Rising CVD + rising price** = genuine buying pressure.
- **Flat CVD + rising price** = passive buying (limit orders) — less aggressive.
- **Falling CVD + rising price** = *CVD divergence* — aggressive sellers, but price held up. Often means absorption or squeeze setup.

### Footprint Charts
- Show buy vs. sell volume at *each price level within each candle*.
- Reveals "where" within a candle the action happened.
- Look for imbalances (e.g., 90% of volume on the ask side = aggressive buying).
- Useful for precise entries but beyond most retail setups.

### Open Interest (OI) — Perp-Specific
- Total notional of open contracts.
- **Rising OI + rising price** = new longs entering — trend confirmation.
- **Rising OI + falling price** = new shorts entering — trend confirmation (down).
- **Falling OI + rising price** = shorts closing (short squeeze) — often near a top.
- **Falling OI + falling price** = longs closing — often near a bottom / capitulation.

### Liquidation Clusters
- Zones where large amounts of leveraged positions will be liquidated at specific prices.
- Price is often "magnetic" to liquidation zones — market makers hunt these levels.
- Major liquidation cascades mark local tops/bottoms.
- Tools: Coinglass Liquidation Heatmap.

---

## Volume Profile (Advanced but Practical)

Volume profile shows **how much volume traded at each price level** (vs time).

### Key levels:

- **Point of Control (POC)**: the price with the highest volume in the period. Major support/resistance.
- **Value Area (VA)**: the price range containing 70% of volume. Fair value zone.
- **Volume Nodes**:
  - **High Volume Nodes (HVN)** = consolidation / support-resistance zones.
  - **Low Volume Nodes (LVN)** = price vacuum, moves fast through these zones.

### Application:
- Price entering an LVN → expect fast movement.
- Price entering an HVN → expect consolidation or rejection.
- Daily / weekly POCs are major reference levels.

---

## Funding Rate as Sentiment Proxy (Crypto Perps)

Funding rates tell you **who is crowded** in the market.

### Interpretation:

| Funding Rate (per 8h) | Meaning |
|---|---|
| > +0.03% | Longs crowded, paying shorts. Crowded bullish. |
| +0.01% to +0.03% | Mildly bullish. |
| ~0% (normal) | Balanced. |
| -0.01% to -0.03% | Mildly bearish. |
| < -0.03% | Shorts crowded, paying longs. Crowded bearish. |

### Actionable extremes:
- **Sustained extreme positive funding (>0.05%+ for multiple periods)** → long squeeze risk. Late longs get punished.
- **Sustained extreme negative funding (<-0.05%+)** → short squeeze setup. Shorts get squeezed on any rally.

### Counter-positioning rule
When funding is extreme and price stops going in the crowded direction → often a reversal. "The crowd is wrong at extremes."

### Pitfalls:
- Funding alone is not a signal. Use it as *context* for directional bets made on structure.
- During strong trends, funding can stay elevated for extended periods. "Overbought" funding can stay overbought.

---

## Open Interest Interpretation Framework

Combine OI with price to understand positioning:

```
Price ↑  +  OI ↑   →  NEW MONEY LONG     (bullish, trend continuation)
Price ↑  +  OI ↓   →  SHORTS COVERING    (squeeze, often near tops)
Price ↓  +  OI ↑   →  NEW MONEY SHORT    (bearish, trend continuation)
Price ↓  +  OI ↓   →  LONGS CLOSING      (capitulation, often near bottoms)
```

### Examples:
- BTC makes a new high, OI surges → **healthy trend**. Fresh longs fueling move.
- BTC makes a new high, OI declines → **short squeeze**. Price moving up because shorts cover, not because new buyers. Often fades.
- BTC crashes, OI surges → **bearish continuation**. Fresh shorts piling in.
- BTC crashes, OI drops sharply → **capitulation**. Longs giving up. Often bottom signal.

---

## Volume-Based Rules for Entries

1. **Don't enter breakouts without volume expansion** (≥ 1.5× average on breakout candle).
2. **Enter breakout retests with declining volume** (shows no fresh supply/demand at old level).
3. **Reversal entries need volume climax** — large candle + volume spike at S/R.
4. **Skip trades on declining volume trends** — momentum is dying.
5. **Trust "effort vs. result" divergences** more than most indicators.

---

## Common Volume Mistakes

- **Chasing volume for its own sake.** A 10x volume spike on a random low-cap doesn't mean take the trade. Volume is context, not signal.
- **Ignoring relative volume.** Looking at raw volume bars without normalization.
- **Trusting volume during news events.** Algorithmic activity and emotional retail flow create noise.
- **Using exchange-specific volume on low-volume venues.** Always aggregate or use the dominant venue (Binance/Bybit for most perps).
- **Over-interpreting delta on low-liquidity pairs.** Delta is noisy when overall volume is thin.

---

## How Claude Should Apply This

When analyzing technicals:

1. **Always compute relative volume**, not raw. Report as ratio (e.g., "3.2x average").
2. **Flag effort vs. result divergences.** A price move on below-average volume is lower conviction.
3. **Interpret OI + price jointly.** Don't report OI in isolation.
4. **Use funding rate as sentiment context, never as sole signal.** "Funding is -0.07% suggests short-crowding" — not "go long because funding is negative."
5. **Trust volume confirmation on breakouts.** Down-weight breakouts with below-average volume.
6. **At major S/R levels, watch for volume climax** as potential reversal signal.
