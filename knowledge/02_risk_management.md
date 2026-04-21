# Risk Management — The Non-Negotiables

> Synthesized from Van Tharp, Mark Douglas, Kelly Criterion literature, and CFA Institute guidelines.

**This is the single most important knowledge file.** A mediocre strategy with excellent risk management beats a brilliant strategy with poor risk management. Every time. Over thousands of trades.

---

## The Golden Rule

> **The purpose of risk management is not to maximize gains. It is to guarantee survival.**

You cannot compound if you blow up. Every risk decision is evaluated through this lens: *does this preserve my ability to trade tomorrow?*

---

## Rule 1: Fixed Fractional Position Sizing (1% Rule)

Risk a **fixed percentage** of account equity on each trade, recalculated per trade.

- **Beginner**: 0.5% per trade
- **Experienced, proven strategy**: 1% per trade
- **Professional with documented edge**: up to 2%, rarely more

For crypto perpetuals, which are highly leveraged and volatile, **stay at 1% or below**.

### Position Size Formula

```
Position Size (USDT notional) = (Account Equity × Risk %) / Stop Distance %

Where:
  Stop Distance % = |Entry Price − Stop Loss Price| / Entry Price
```

**Example:**
- Account: $10,000
- Risk: 1% → $100 maximum loss
- Entry: BTCUSDT at $60,000
- Stop Loss: $58,800 (2% away)
- Position size = $100 / 0.02 = **$5,000 notional**
- On 5x leverage that's $1,000 margin used

### What "Risk" Means

- **Risk = what you lose if stop hits.** NOT position size. NOT margin used.
- If stop loss is wider, position size must be *smaller* to keep risk constant.
- If stop loss is tighter, position size can be *larger* — but only up to leverage limits.

---

## Rule 2: R:R Minimum of 1:2

**Reward-to-risk ratio** = distance to target ÷ distance to stop.

- **Minimum acceptable: 1:2** (skip setups below this)
- **Target: 1:3+** for swing trades
- **Scalping exception**: 1:1.5 acceptable IF win rate > 55% proven

### Why 1:2 is the floor

If you take only 1:2 setups, you can be wrong 60% of the time and still be profitable:
- 10 trades × 40% win × 2R = +8R
- 10 trades × 60% loss × 1R = -6R
- Net: +2R

Below 1:2, you need win rates that are rarely achievable in practice.

---

## Rule 3: Stop Loss Placement

### Where to place stops (pick ONE method, don't mix)

1. **Structure-based** (preferred): just below/above a significant swing low/high or support/resistance zone.
2. **ATR-based**: 1.5× to 3× the Average True Range from entry.
3. **Volatility-based**: fixed % (e.g., 2-3% for BTC, up to 5-8% for mid-caps).
4. **Invalidation-based**: the price level that disproves your thesis.

### Stop loss rules

- **Set BEFORE entry.** Never after.
- **Hard stops on the exchange** — not mental stops. Set as an actual stop order.
- **Never widen a stop.** Ever. If the trade is going wrong, accept it.
- **Can tighten to breakeven** once price moves in your favor by 1R, reducing risk to zero.
- **Trail stops** only after 1.5R profit, using structure or ATR.

---

## Rule 4: Daily and Weekly Limits

### Daily hard stops

| Trigger | Action |
|---|---|
| 2 losing trades in a day | **Stop trading for the day** |
| -3% account drawdown in a day | **Stop trading for the day** |
| Feeling tilted/emotional | **Stop trading immediately** |

### Weekly hard stops

| Trigger | Action |
|---|---|
| -6% account drawdown in a week | **Stop trading for the week, review** |
| 5+ consecutive losses | **Halve position size until 3 wins in a row** |

Why these matter: most blown accounts come from a cascade — a bad trade → revenge trade → bigger loss → tilt → 10% down before lunch.

---

## Rule 5: Leverage Discipline

**Leverage does not change risk** — position sizing does. But leverage amplifies the consequences of poor sizing.

### Recommended leverage by setup type

| Trade Type | Max Leverage | Reasoning |
|---|---|---|
| Swing trade (BTC/ETH, 4H+) | 3-5x | Wider stops, less funding drag |
| Day trade (major alts) | 5-10x | Tighter stops, shorter hold |
| Scalp (high-conviction) | up to 20x | Very tight stops, very short hold |
| Low-cap altcoin | ≤ 3x | High volatility, wicks can liquidate |

### The liquidation buffer rule

Ensure liquidation price is **at least 2× further** than your stop loss.
- Stop loss at 2% → liquidation should be ≥ 4% away.
- This protects against funding rate changes, exchange glitches, and sudden wicks.

---

## Rule 6: Position Correlation

Avoid stacking correlated risk. In crypto, *almost all alts correlate heavily with BTC*.

- If BTC is long, ETH is long, SOL is long → that's **one bet**, not three.
- Multi-position limit: **max 2% total account risk across all correlated positions**.
- True diversification requires uncorrelated assets — rare in crypto during risk-off events.

---

## Rule 7: The Kelly Criterion — Use With Extreme Caution

Full Kelly is:
```
Kelly % = W − (1 − W) / R

Where:
  W = win rate (decimal)
  R = avg win / avg loss
```

### Why never use Full Kelly

- Full Kelly assumes your win rate and R are **perfectly known**. They aren't.
- Even if you have positive edge, Full Kelly produces drawdowns of 30-60%.
- Psychologically intolerable. Most traders quit in the drawdown.

### Recommended: Quarter Kelly or less

- **Quarter Kelly (25%)**: for experienced traders with 100+ trade sample size.
- **For crypto, go even lower.** 10-15% of Kelly is safer given volatility.
- **If calculation gives you more than 1-2% risk per trade**, override and stick with fixed fractional 1%.

Kelly is a ceiling, not a target. The 1% rule wins long-term because it survives.

---

## Rule 8: Hard Rules That Never Change

These rules are **hard-coded**. Not negotiable based on "conviction level" or "sure thing" gut calls:

1. Never risk more than 2% of account on a single trade.
2. Never have open positions risking more than 6% of account combined.
3. Never add to a losing position (no averaging down).
4. Always have a stop loss set on the exchange.
5. Never trade without a defined invalidation level.
6. Never use more than 10x leverage on altcoins, 20x on BTC/ETH.
7. Always keep at least 50% of account as unused margin buffer.
8. Never trade with money you can't afford to lose in full.
9. Never take tips, signals, or calls from Telegram/Twitter as the sole reason to enter.
10. Never trade 1 hour before/after major news (FOMC, CPI, etc.) without a specific news-trading plan.

---

## How Claude Should Apply This

When analyzing setups and producing briefs:

1. **Reject setups with R:R < 2:1.** They don't appear in High-Conviction section.
2. **Always state invalidation level.** Never "buy X, target Y" without "stop at Z."
3. **Flag when funding rate implies over-crowded positioning** (e.g., > 0.05% per 8h). Entering late on the crowded side is risky.
4. **Flag low-liquidity instruments.** Any perp below $50M open interest or $10M daily volume should be avoided or flagged explicitly.
5. **Respect the trader's hard stops.** If the user has already had 2 losses today (from journal context), recommend "no trade" regardless of setup quality.

---

## The Summary Test

Before every trade, the trader asks:
1. What is my entry, stop, and target?
2. What is my risk in dollars?
3. Is risk ≤ 1% of account?
4. Is R:R ≥ 2:1?
5. Would I still take this trade knowing it might lose?

If any answer is unclear → **no trade**.
