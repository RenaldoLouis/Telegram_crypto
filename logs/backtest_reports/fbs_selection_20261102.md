# Does the live pre-filter pick the coins where failed_breakout_short works? — 2026-11-02

Pre-registration: `prereg_fbs_selection_20261102.md`. TEST = signal bars 2025-10-01 → 2026-09-20. Universe 523 coins with 4h data (of 571); selection replayed at every 4h close (median 31.0 coins per scan). Entry at the live time (close + 2 min → next 15m open), limit_open, trade_sim management, costs. 2-day dedup per coin within each group.

## Validity gate

- Live record 2026-09-21 → 10-22 marked selected by the reconstruction: 52/64 = **81%** (gate ≥ 80%) → **VALID**
- Same span, reconstructed: selected n=149 · 55.7% profitable · net -0.038R · PF 0.91 · 60% of 5 weeks green · not selected n=160 · 61.2% profitable · net +0.125R · PF 1.35 · 100% of 5 weeks green

## TEST results

- **Selected:** n=1253 · 57.4% profitable · net -0.015R · PF 0.96 · 53% of 51 weeks green
- **Not selected** (liquid, not in the scan): n=1865 · 58.5% profitable · net -0.010R · PF 0.97 · 49% of 51 weeks green
- Fires on liquid coins in TEST: 4119 (1613 selected) before dedup

| # | bar | result | |
|---|---|---|---|
| 1 | quality on the selected book: net > 0, PF ≥ 1.3, ≥ 55% weeks green | net -0.015R, PF 0.96, 53% weeks | ✗ |
| 2 | beats random shorts (same coin ±3.5 d) by ≥ +0.05R, CI lower > 0 | +0.209R (signal -0.015 vs random -0.224), per bet CI [+0.165, +0.269] | ✓ |
| 3 | selected − not selected ≥ +0.10R, CI lower > 0 | -0.005R, CI [-0.024, +0.126] | ✗ |
| 4 | selected net > 0 in both halves | -0.004R / -0.027R | ✗ |

**Verdict: FAIL**

## Descriptive

- Not selected vs its own random baseline: -0.010 vs -0.210R (n 1865)

| month | selected n | selected net R | not selected n | not selected net R |
|---|---|---|---|---|
| 2025-10 | 101 | -0.038 | 274 | +0.126 |
| 2025-11 | 98 | +0.028 | 192 | +0.111 |
| 2025-12 | 95 | -0.134 | 110 | +0.043 |
| 2026-01 | 120 | -0.118 | 173 | -0.021 |
| 2026-02 | 87 | +0.077 | 133 | +0.059 |
| 2026-03 | 116 | +0.178 | 177 | +0.063 |
| 2026-04 | 100 | -0.091 | 173 | +0.016 |
| 2026-05 | 121 | -0.030 | 173 | -0.186 |
| 2026-06 | 113 | +0.035 | 139 | +0.072 |
| 2026-07 | 98 | -0.018 | 97 | -0.208 |
| 2026-08 | 125 | -0.087 | 116 | -0.265 |
| 2026-09 | 79 | +0.038 | 108 | -0.229 |

_Approximations (stated in the pre-registration): non-crypto perps ignored in the top-100 ranking; daily open interest; settled funding instead of the predicted rate; the 2h momentum pulse replayed on the 4h grid; coins delisted before today may lack 4h data._
## Reading (post-hoc, written after the numbers)

- **The selection hypothesis is refuted.** Over 12 untouched months, coins the live pre-filter selects and coins it
  does not give the same result (−0.015R vs −0.010R per trade, about 3,100 trades). Even inside the live span the
  rebuilt selection points the other way (selected −0.04R vs not selected +0.13R), so the +0.33R vs +0.03R split in
  `fbs_check` Q4 was not the pre-filter. The live record is a subset of fires that happened to go well (likely in part because CI scan coverage
  before the 10-12 scan keeper decided which fires were taken; not verified here).
- **What the pattern does have:** it beats random shorts on the same coins by +0.21R per trade (CI [+0.17, +0.27])
  in both groups. Random shorts lose about −0.22R after costs and the T1/T2 structure, so the pattern lifts a losing
  entry to about breakeven: better than random, not enough to pay costs. (Unlike the pooled 2026-10-19
  `win_rate_geometry.py` result, where the signal entries were no better than random.)
- Per the pre-registration: the `failed_breakout_short` lead is closed and R-2026-10-16-1 is graded refuted. No live change.
