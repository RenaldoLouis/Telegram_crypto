# Pre-registration — single-coin trend-following study (2026-10-19)

Written 2026-10-19 Asia/Jakarta, BEFORE any result of this study existed. Nothing below may
change after the run; a change = a new study with a new date.

**Question (user, 2026-10-19):** every rule tested so far has one shape — fade/pullback entry,
small fixed target (1.5–2R), out within 2 days — which is what the 70% win-rate goal pushes
toward and where fees hurt most. Does the opposite shape (breakout entry, trailing stop, let
winners run) make money net of all costs? **User decision: this study is judged on profit,
not win rate.** If it passes it is a separate product (like the momentum paper test), not a
change to the screener.

**Code:** `trend_study.py` → `logs/backtest_reports/trend_study_<date>.md`.

**Data:** the project's 15 majors (`historical_backtester.EXPANDED_SYMBOLS`: ADA, XRP, SOL, BTC,
ETH, DOGE, SUI, XLM, ENA, HBAR, TRX, NEAR, OP, ARB, INJ), fixed before the run. 1,095 days of
Bybit daily + 4h klines and actual funding history ending at run time. Survivorship caveat: all
15 are coins that survived to today.

**Trade rule (two variants, N = 20 primary, N = 55 secondary):**
- Signal on the daily close (UTC): long when the close is above the highest high of the previous
  N days; short when it is below the lowest low of the previous N days. Only when that coin
  has no open position.
- Entry at the next day's open, market order (taker 0.055% + 0.03% slippage).
- Initial stop 3 × ATR(20, daily) from the entry. Trailing (chandelier): after every daily
  close the stop moves to highest high since entry − 3 × ATR(20) (longs; mirror for shorts),
  never loosens.
- Exit when a 4h bar touches the stop (filled at the stop, or at the bar's open if it gapped
  through), or at market after 60 days. Taker + slippage on the exit.
- Funding: actual Bybit rates, paid or received at every settlement while open.
- 1R = the initial stop distance. All results are R per trade net of fees, slippage and funding.
- TRAIN = trades entered in the first 60% of the calendar period, TEST = the last 40%.

**Bar (per variant):**
- **PASS** — TEST n ≥ 30, TEST net expectancy > 0, TEST profit factor ≥ 1.3, TEST expectancy
  still > 0 with the single best TEST trade removed, TRAIN net expectancy > 0, and whole-period
  max drawdown of the closed-trade equity ≤ 20R (= 10% of equity at 0.5% risk per trade).
  → a forward paper test with its own pre-registration (CI, paper only). Not live money.
- **CANDIDATE** — TEST n ≥ 30, net > 0, PF ≥ 1.1, but misses another PASS condition → a paper
  test is optional and the result is labelled weak.
- **FAIL** — anything else → single-coin trend following is closed.
- Two variants → mild multiple testing; a PASS on N = 55 alone (N = 20 failing) is weaker
  evidence and is reported as such.

**Informational (not part of the bar):** long vs short; a random-entry baseline with the same
exit (every 10th flat day, alternating long/short) — shows whether the breakout entry adds
anything beyond the trailing exit; win rate, average win / loss, longest losing streak, trades
per week, per-year table, portfolio view at 0.5% risk per trade, bootstrap 95% CI of TEST
expectancy.

**Honest prior (written before the run):** single-coin trend following worked well in crypto in
2017–2021 and has weakened since; the TEST period (≈ May 2025 → Oct 2026) was choppy for alts.
Expected outcome: CANDIDATE or FAIL; any long-side profit is partly market beta.
