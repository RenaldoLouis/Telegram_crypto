# Why the screener can't reach 80% at 1:1, and where the evidence says edge lives

_Written 2026-10-19 after the daily-book replay (−0.087R over 6 months). The user asked: "focus on ~80% win rate with 1R only so we can be more consistent — why can't our system do this? Are we missing data? Are we looking from the wrong perspective?"_

Sources: our own measurements (scripts in the repo root) plus three research passes over academic papers, regulator/exchange filings and books. **Source-quality note:** the research agents' web fetches to most academic domains failed, so most papers were checked against abstracts, search snippets and secondary summaries rather than full texts. Each claim is tagged PR (peer-reviewed), WP (working paper/preprint), book, docs (exchange/protocol/regulator) or own (our computation). Treat "secondary" and "unverified" tags literally.

---

## 1. Short answer

1. **Win rate is a dial set by the target/stop ratio, not a measure of skill.** With no edge, P(+k·R before −1R) = 1/(1+k). A 0.25R target with a 1R stop gives 80% to a coin-flip. At 1:1 the no-edge rate is 50%.
2. **80% at 1:1 is an enormous edge**: +0.6R gross per trade, a per-trade Sharpe of 0.75 (≈ 14 annualised at one trade a day). Nothing in the cost-adjusted literature on directional trading comes close. Renaissance's own description of its edge is "right 50.75% of the time".
3. **Our entries are indistinguishable from random entries at every target size** (§2). This is what the literature on technical analysis predicts (§4): price-pattern rules on single coins do not survive costs and multiple-testing correction.
4. **The perspective is the problem, not a missing indicator.** The evidence that does survive is (a) *relative* (which coin beats which, market-neutral), (b) *structural* (getting paid for carrying a position others want to offload), and (c) *broad* (many independent bets). Consistency is measured per week/month of a portfolio, not per trade.

---

## 2. Our own measurements (2026-10-19)

**Daily book replay** (`daily_book_replay.py`, the live `main.select_daily_picks` on the 2026-09-23 unified backtest, 29 symbols, 03-29 → 09-23): 526 picks, 54.9% profitable, −0.087R/trade, −45.5R; 5 of 6 months red; longs −0.124R, shorts −0.040R; TEST third 59.2% / −0.016R. Own.

**Win-rate geometry** (`win_rate_geometry.py`): whole-position bracket, 1R stop, kR target, 2-day max hold, maker entry/target, taker + slippage on stop/expiry, funding. 1,884 signal entries vs 9,420 random twins (same symbol and stop size, random 4h close, random side). Median stop 2.32% of price; a stop-out costs ≈ 0.046R. Own.

| target | no-edge theory | our signals: hit / net R | random entries: hit / net R |
|---|---|---|---|
| 0.25R | 80.0% | 77.4% / −0.059 | 78.3% / −0.036 |
| 0.5R | 66.7% | 65.1% / −0.051 | 64.7% / −0.046 |
| 0.75R | 57.1% | 55.6% / −0.067 | 55.9% / −0.049 |
| 1.0R | 50.0% | 48.7% / −0.086 | 49.2% / −0.066 |
| 1.5R | 40.0% | 41.4% / −0.096 | 42.2% / −0.065 |
| 2.0R | 33.3% | 37.1% / −0.108 | 39.2% / −0.065 |

Earlier the same day: a 15m 1:1 scalp hit 46.6% (below a no-skill baseline of 48.5%), and a daily breakout trend-follow was matched by random entries with the same exit (`progress.md` 2026-10-19).

---

## 3. The math

- **Barrier hitting.** Driftless random walk: P(+a before −b) = b/(a+b) — the gambler's ruin problem, Feller, *An Introduction to Probability Theory and Its Applications* Vol. 1, Ch. XIV §2 (book; chapter verified, page not). López de Prado's *triple-barrier* labelling (*Advances in Financial Machine Learning*, 2018, §3.4) is the same set-up. With drift μ and volatility σ, P(+a before −a) = 1/(1+e^(−2μa/σ²)) (derived; textbook page unverified).
- **What 80% at 1:1 means.** 2μa/σ² = ln 4 ≈ 1.39 → gross expectancy +0.6R, per-trade Sharpe 0.75. By Wald's identity the price must, on average, travel 0.6 stop-distances your way during every trade. Mercer's "50.75%" is +0.015R per trade; 80% is ~46× that in log-odds.
- **Costs move the bar.** At 1:1, breakeven hit rate = (1 + c)/2 with c = round-trip cost in R. Our 2.3% stops make c ≈ 0.05R (breakeven 52.5%); a 0.6% scalp stop with taker fills makes c ≈ 0.2R (breakeven 60%). This is why the 15m scalp failed.
- **Consistency is a per-period number.** For roughly normal, independent returns: annual Sharpe 1 → ~61% of months green; Sharpe 2 → ~72%; 80% of months green needs Sharpe ≈ 2.9; 80% of *weeks* green needs Sharpe ≈ 6. (Own arithmetic.)
- **Fundamental law of active management.** IR ≈ IC × √breadth (Grinold 1989, *JPM*; Grinold & Kahn, *Active Portfolio Management*; via secondary sources). For a ±1 call with hit rate p, IC ≈ 2p − 1: 80% → IC 0.6, 52% → IC 0.04. Realistic ICs are a few hundredths; consistency comes from **many independent bets**, not precision. Three alt picks on the same 4h bar are closer to one bet than three.

## 4. What the evidence says about technical analysis

| Study | Finding | Type |
|---|---|---|
| Sullivan, Timmermann & White 1999, *J. Finance* 54:1647 — [doi](https://doi.org/10.1111/0022-1082.00163) | 7,846 rules on 100 years of the Dow; best rule held in-sample but out of sample (1987–96) not significant, before costs, after White's Reality Check | PR |
| Park & Irwin 2007, *J. Economic Surveys* 21(4) — [doi](https://doi.org/10.1111/j.1467-6419.2007.00519.x) | 95 studies: 56 positive, but most suffer data snooping, ex-post rule selection, poorly estimated costs/risk | PR (counts secondary) |
| Bajgrowicz & Scaillet 2012, *JFE* 106(3) — [doi](https://doi.org/10.1016/j.jfineco.2012.06.001) | Dow 1897–2011 with false-discovery control: investors could never have picked the future best rules; even in-sample gains vanish with low costs | PR |
| Hudson & Urquhart 2021, *Annals of OR* 297 — [link](https://link.springer.com/article/10.1007/s10479-019-03357-1) | ~15,000 rules on crypto; predictability survives multiple testing in-sample, **but no out-of-sample predictability for Bitcoin** (the most favourable study) | PR |
| Anghel 2021, *Finance Research Letters* 39 — [doi](https://doi.org/10.1016/j.frl.2020.101655) | ML + TA rules in crypto with data-snooping correction and frictions: significant excess returns "rarely achieved"; performance tracks beta/idiosyncratic volatility | PR |
| Aronson, *Evidence-Based Technical Analysis* (Wiley 2006) | 6,402 rules on S&P 500; none significant after Reality Check/permutation tests | book (secondary review) |
| Bailey, Borwein, López de Prado & Zhu, *J. Computational Finance* 2017 — [SSRN](https://papers.ssrn.com/abstract=2326253); Harvey, Liu & Zhu 2016, *RFS* 29(1) — [NBER](https://www.nber.org/papers/w20592) | Backtest overfitting is easy (≈45 trials on 5 years can show Sharpe 1 from a true 0); new factors should clear t > 3 | PR |

Our six months of studies replicate this literature on our own venue.

**Meta-labeling** (López de Prado 2018, §3.6) raises hit rate by skipping trades a second model dislikes — but it cannot create an edge the primary signal lacks, it cuts breadth, and every fitted filter is another trial. Not useful while the primary is breakeven.

## 5. How "high win rate" products are actually built

High hit rates without a large edge come from geometry (small target, big or no stop), martingale/grid sizing, or selling insurance (options/volatility, carry). All trade hit rate for negative skew:

- Carry trades are negatively skewed and crash when funding liquidity dries up — Brunnermeier, Nagel & Pedersen 2008, NBER WP 14473 / *NBER Macro Annual* ([link](https://www.nber.org/papers/w14473)). PR.
- Short straddles lose ~3%/week for the buyer, so sellers win most weeks — Coval & Shumway 2001, *J. Finance* 56(3); variance risk premium — Carr & Wu 2009, *RFS* 22(3). PR. The tail: XIV's indicative value fell 96% on 2018-02-05 ([Credit Suisse](https://www.credit-suisse.com/articles/media-releases/2018/02/en/xiv-trading-halt.html), docs); LJM short-vol funds lost >$1B ([SEC 2021-89](https://www.sec.gov/news/press-release/2021-89), docs).
- Retail outcomes: 74–89% of retail CFD accounts lose money ([ESMA 2018](https://www.esma.europa.eu/node/84933), docs); 97% of Brazilian day traders who persisted ≥300 days lost money (Chague, De-Losso & Giovannetti, "Day Trading for a Living?", WP).
- Pros: Virtu had one losing day in 1,238 (S-1, [SEC](https://www.sec.gov/Archives/edgar/data/0001592386/000104746914002070/a2218589zs-1.htm), docs) with ~51–52% winning trades (CEO, secondary) — consistency from breadth. Trend followers expect to lose 60–70% of trades (Clenow, practitioner).

## 6. Inputs with evidence that we do not use (horizon is everything)

| Input | Horizon where it works | Evidence | Fit for us | Data |
|---|---|---|---|---|
| **Cross-sectional momentum** | 1–4 week lookback, 1-week hold | Liu, Tsyvinski & Wu 2022, *J. Finance* ([SSRN](https://papers.ssrn.com/abstract=3379131)); post-2020 still 2.1%/wk gross, but 12- and 24-week momentum insignificant after 2020 — Borri et al. 2025 ([arXiv 2510.14435](https://arxiv.org/abs/2510.14435), WP); in futures "not statistically powerful" — Chi et al. 2023 (PR) | **In use**: paper test #2. Our own backtest found 7d dead (Sharpe 0.18), 14d 0.62, 28d 2.09, 56d 2.87, 91d 2.60 (crypto-only, 62 wks) — our best lookbacks sit where the papers find weakness, so k=56/91 rests on our 62 weeks more than on the literature | have |
| **BTC → altcoin lead-lag** | **minutes** (≈10 min; ≈0 at 1h) | Guo, Sang, Tu & Wang 2024, *J. Economic Dynamics & Control* ([RePEc](https://ideas.repec.org/a/eee/dyncon/v163y2024ics0165188924000551.html)): other coins' lagged returns predict a coin's return; the working-paper abstract (SSRN 3974583) places it in **minute** data, lasting about ten minutes (slow information diffusion), long-short profitable after costs at that frequency. _Correction 2026-10-20: the first version of this note said "daily" — wrong._ Khan 2026 WP: next-hour correlation 0.006 | poor — **tested at daily 2026-10-20: NO** (§9) | have (klines) |
| **Basis/funding cross-sectional sort** | daily strongest; monthly not significant | Chi, Hao, Hu & Ran 2023, *J. Futures Markets* ([RePEc](https://ideas.repec.org/a/wly/jfutmk/v43y2023i8p1161-1180.html)): basis is "the strongest signal" across crypto futures, 2017–21 (costs not stated; definition and sign not verified — full text paywalled) | **tested at daily 2026-10-20: NO** (§9) | have (funding) |
| **Aggregate carry as a crash warning** | ~1 month | Schmeling, Schrimpf & Todorov, BIS WP 1087 ([BIS](https://www.bis.org/publ/work1087.htm)): high carry predicts price falls and short-futures liquidations | risk filter, not entries | have |
| Stablecoin supply / USDT exchange inflows | 1–6h (flows); disputed | Griffin & Shams 2020 *J. Finance*; Kristoufek 2021 *FRL* (issuance follows price); Chi, Chu & Hao WP ([arXiv 2411.06327](https://arxiv.org/abs/2411.06327)) | low confidence | supply free (DefiLlama); flows paid |
| Options (Deribit DVOL, skew, flow) | volatility, not direction | Alexander, Deng, Feng & Wan 2023, *J. Financial Markets*: option order flow predicts volatility, not BTC returns at 1h–5d | sizing/risk input only | free (Deribit public API) |
| Order-flow imbalance / CVD | seconds–minutes | Cont, Kukanov & Stoikov 2014 (PR); Makarov & Schoar 2020 *JFE* (same-period, next day negative); Kim & Hansen 2026 WP: ~0.5 bp/event vs ~10 bp cost | poor — **our CVD test already failed** | have |
| Liquidations / OI / leverage | — | no peer-reviewed evidence of 4h–weekly directional power; cascade papers are descriptive | poor — **our liq-cluster test already failed** | have |
| Short-term reversal | 15 min, gone by 4h | Kitron & Wengrowicz 2026 WP: accuracy 0.531, 1.3 bp gross vs ≥5 bp cost | poor | have |
| Seasonality / settlement times | — | Monday effect inconclusive (Caporale & Plastun 2019); no settlement-time return pattern found | poor — **our session gating found nothing** | have |
| ETF flows, Coinbase premium | — | ETF link is a US-session timing artefact (Fabus et al. 2026 WP); Coinbase premium: no academic test | poor / untested | free |
| Sentiment / attention / Fear & Greed | — | Liu & Tsyvinski 2021 *RFS* (to 2018); later work: attention follows volatility (Urquhart 2018); F&G no OOS gain | poor | free |

**Reading:** we are not short of data. Almost every input with evidence at our horizon is *cross-sectional* (rank coins against each other) and we already held the data for the two strongest-looking ones (lead-lag, basis) — both failed a daily test on 2026-10-20 (§9). The directional single-coin inputs we tested — liquidations, CVD, order flow, sessions — are the ones the literature says live at seconds-to-minutes or not at all.

## 7. Consistent return sources (structural premia)

| Source | Return now / normal years | Green weeks | Worst case | Fit (manual, weekly) |
|---|---|---|---|---|
| BTC/ETH perp cash-and-carry (long spot, short perp, 1×) | 2.5–3% / 5–12% (≈40% in 2021) | ~90% of 342 weeks (funding only; own, Bybit API) | worst month of funding −1.45% of notional; real tail = exchange failure / ADL | yes |
| BTC quarterly basis, held to expiry | ~5.5% locked (Bybit/Deribit 2026-10-19; Bybit dated futures thin, <$1M/day) | price noise, locked at expiry | basis widening if leveraged | yes |
| Short volatility (Deribit) | positive, gross proxy only | ~68% of 276 weeks (own proxy) | −23.5% week, −31% drawdown | poorly |
| Market making | negative for a manual trader | — | adverse selection; latency races (Aquilina, Budish & O'Neill 2022 *QJE*) | no |

- **Bybit funding paid to a short, annualised** (own, from `api.bybit.com/v5/market/funding/history`): BTC 2021 38.3%, 2022 3.0%, 2023 8.9%, 2024 12.0%, 2025 5.1%, 2026 YTD 2.5%. Negative 8h prints: 28% of 2022, 29% of 2026.
- He, Manela, Ross & von Wachter, "Fundamentals of Perpetual Futures" ([arXiv 2212.06888](https://arxiv.org/abs/2212.06888), WP): BTC perp arbitrage Sharpe 1.80 at retail-like fees, ~6.4% p.a.; −0.01% in 2022; mispricing shrinks ~11%/year. Borri et al. 2025: carry Sharpe turned negative in 2025 (gross).
- Ethena sUSDe (the public version of this trade): 2024 17.5%, 2025 6.5%, today ~4.8%; on 2025-10-10 USDe printed $0.65 on Binance spot; supply fell from $14.8bn to $4.7bn ([DefiLlama](https://stablecoins.llama.fi/stablecoin/146), aggregator).
- Risks: Bybit lost ~$1.5bn to theft on 2025-02-21 ([FBI PSA](https://www.ic3.gov/PSA/2025/PSA250226), docs); ADL closed $2.1bn of positions on Hyperliquid in 12 minutes on 2025-10-10 (Chitra, [arXiv 2512.01112](https://arxiv.org/abs/2512.01112), WP) — your winning short is the ADL target; Bybit non-VIP round trip (spot 0.10% + perp) ≈ 0.24–0.31% of notional ≈ one month of today's BTC funding.
- **This is the honest form of an "80% win rate"**: ~90% green weeks, because each payoff is small and the losses are rare and large.

## 8. What this means for the project

1. **Stop measuring per-trade win rate as "consistency".** The meaningful number is % green weeks of the whole book, alongside Sharpe and max drawdown. Realistic professional targets: Sharpe 1–2 → ~60–70% green months.
2. **Single-coin directional picks on 1h–4h price patterns have no edge on our data or in the literature.** More indicators, more gates, or a smaller target will not change that. The daily book should stay paper-only.
3. **The shape that has evidence is a market-neutral, cross-sectional book with breadth.** We already run one (paper test #2: backtest 65% green weeks, Sharpe 2.6–2.9; forward 2/26 weeks, both green). The two inputs that looked best for a **daily** version of that shape (BTC→alt lead-lag, a basis/funding ranking) were tested on 2026-10-20 and failed (§9).
4. **If "consistent" matters more than "large", carry is the documented answer** — ~90% green weeks at ~3–6%/year now, with exchange/ADL tail risk. It needs a spot leg and is a manual set-up, not a signal.

### Candidate next tests (as written 2026-10-19; outcomes in §9)

1. **Daily cross-sectional book** (lead-lag + basis ranking) — run 2026-10-20 → NO on both.
2. **Carry crash filter** as a *shadow* overlay on paper test #2 (never on the frozen book): de-risk when aggregate carry is in its top decile — not run.
3. **Carry monitor** (description only) — shipped 2026-10-20 as the carry line of the Monday review (`carry_monitor.py`).

## 9. Follow-up 2026-10-20 — daily long/short book tested (pre-registered) → NO

Pre-registration `logs/backtest_reports/prereg_xs_daily_20261020.md` (written before the code), script `xs_daily_backtest.py`, report `logs/backtest_reports/xs_daily_20261020.md`. 501 crypto-only Bybit perps, daily bars 2025-04-12 → 2026-10-03, 509 daily rebalances, decile legs, 10%-of-leg cap, dollar-neutral, taker + slippage on turnover, actual funding. Random-ranking baseline: mean Sharpe −1.33 (costs), 95th percentile 0.17.

| signal | full Sharpe | H1 | H2 | max DD | % weeks green | verdict |
|---|---|---|---|---|---|---|
| `basis_24h` — long the lowest trailing-24h funding, short the highest | 0.07 | 0.49 | −0.29 | 37.6% | 44% | **NO** |
| `btc_catchup` — long the coins that lagged BTC's last daily move | −0.87 | −0.90 | −0.86 | 76.7% | 43% | **NO** |

- **Basis:** the book *received* about 183% a year in funding and lost about as much on price (gross −82% a year; long leg −241% cumulative). Coins with deeply negative funding keep falling; the funding is the price of holding them, not a free premium. Same lesson as the 2026-10-04 carry basket. At maker cost (context, not judged) Sharpe 0.35 — still below the bar.
- **Lead-lag:** gross ≈ 0 (−7.7% a year) before a 38%-a-year cost drag — consistent with the effect living in minutes, not days.
- Two judged trials; nothing was varied after the run.

**Where this leaves the search:** price patterns on single coins, and the two best-documented daily cross-sectional inputs, are now closed on our data. The open items are paper test #2 (weekly momentum, the only thing that has cleared a bar) and, for consistency rather than return, cash-and-carry — now visible every Monday.
