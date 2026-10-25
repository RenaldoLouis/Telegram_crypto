# Pre-registration — edge search with a locked holdout (2026-10-25)

Written 2026-10-25 Asia/Jakarta, BEFORE any result of this search existed and while the data
was still downloading. Nothing below may change after a result is seen; a change = a new
protocol with a new date.

**Question (user, 2026-10-25):** "If you are a trader who trades for a living, keep finding
another strategy to profit monthly until you find it." The playbook study (same day) found no
classic single strategy on 15 survivor coins. This search widens the data (every Bybit USDT
perp ever listed, back to 2020) and the ideas (portfolio and structural strategies), and keeps
going until something passes.

**Why a protocol:** "search until something passes" guarantees a false winner if every idea is
judged on the same data — with enough tries one always looks good by chance. So the search may
try as many ideas as it likes, but only on DISCOVERY data, and every variant is counted. The
last 22 months stay locked until at most 3 finalists are named, then each gets one test there.

## Data

- Every Bybit linear USDT perpetual, trading AND delisted (313 delisted ones are served when the
  request names a window inside their life), daily bars + every funding settlement, from 2020-01
  (or listing) to 2026-10-24. Tokenized stocks / ETFs / commodities / forex (`symbolType`) and
  pegged tokens excluded, as in the live scan. Code: `edge_data.py`; cache `logs/backtest_cache/edge/`.
- Point-in-time universe on day t: listed ≥ 30 days, trailing-30-day median daily turnover
  ≥ $5M, a close on day t−1. A coin that stops trading is closed at its last close.

## Split

- **DISCOVERY:** first bar → 2024-12-31. All ideas, variants and choices are made here. The
  search code cuts the data at 2024-12-31 when it loads it, so later prices are never read.
- **HOLDOUT (locked):** 2025-01-01 → 2026-10-24 (≈ 22 months). Read only by `edge_search.py
  confirm`, which refuses to run unless `logs/backtest_reports/edge_finalists.json` is committed
  to git and unchanged. One run. Honest caveat: the 11 playbook strategies were already judged on
  Aug 2025 → Oct 2026 on 15 coins, so the holdout is fresh for every new idea but its market is
  known (a falling market from late 2025).

## Trading model (all strategies)

- Decide at the daily close (00:00 UTC) with closed data only; trade at that price with market
  orders; hold for the day. Weekly strategies rebalance on Mondays and hold their weights.
- Costs per side: taker 0.055% + slippage by the coin's trailing-30-day median daily turnover:
  ≥ $200M 0.03%, $50–200M 0.06%, $5–50M 0.12%. Charged on every weight change.
- Funding: actual settlements, paid or received on the position held over the day.
- Results are daily net returns at the strategy's own gross exposure (≤ 1, no leverage), also
  shown scaled to 20% annual volatility (scale fixed on DISCOVERY).

## Families to search (more may be added; every evaluated variant is counted)

Cross-sectional momentum · time-series momentum across the universe · cross-sectional funding
carry · short-term reversal · new-listing short · low volatility / betting against beta ·
turnover shocks · BTC/ETH trend timing · calendar effects · distance from the 52-week high ·
hedged funding harvest (approximation) · combinations of the above.

## Ledger

Every variant evaluated on DISCOVERY is appended to `logs/backtest_reports/edge_search_ledger.jsonl`
with its parameters and results. **N = the number of ledger lines**; nothing is ever deleted.

## Finalist bar (DISCOVERY, all of)

1. Net Sharpe ≥ max(1.0, √(2·ln N) / √Y), Y = years the strategy was active in DISCOVERY
   (the expected best Sharpe of N strategies with no edge — the bar rises as the search grows).
2. ≥ 60% of DISCOVERY months green.
3. Positive in at least 3 of the 4 full years 2021–2024, and no year worse than −10% at 20% vol.
4. Max drawdown ≤ 25% at 20% vol.
5. Not just the market: alpha vs the equal-weight eligible universe with t ≥ 2.
At most 3 finalists (highest Sharpe first, at most one per family), written with their exact
parameters to `edge_finalists.json` and committed BEFORE `confirm` runs. Their equal-risk
combination (each scaled to 20% vol on DISCOVERY, averaged) is tested too.

## Holdout bar (one shot, per finalist and for the combination)

**PASS** — net > 0, **≥ 60% of HOLDOUT months green** (the user's goal), Sharpe ≥ 0.75, max
drawdown ≤ 25% at the DISCOVERY scale. A PASS goes to a forward paper test (weekly readout,
monthly verdict); real money only after ≥ 8 weeks of paper and the user's decision, small size.
**FAIL** — anything else. If nothing passes, the holdout is spent: later ideas can only be
judged forward, on paper — not by re-mining these 22 months.

## Honest prior (written before any result)

Most single families will fail the rising Sharpe bar. The best chances, from the literature
and our own paper test #2: cross-sectional momentum, funding carry and the new-listing short —
and above all a combination of uncorrelated sleeves, because consistent months come from
diversification more than from any one signal. Expect 0–2 finalists and at most one holdout PASS.
