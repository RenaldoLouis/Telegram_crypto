"""Stablecoin supply flows as a new input — pre-registered study (2026-11-17).

Pre-registration: logs/backtest_reports/prereg_stablecoin_20261117.md (frozen before this file).
Three market-wide daily features (`stablecoin_data.py`), all read as "follow the money" (positive =
supply growing faster than usual = favours a LONG): `stable_7d`, `stable_30d` (total USD stablecoins) and
`usdt_7d` (USDT only), each a z-score of the % change. The test machinery is `dvol_study.py`'s (same
population, periods, bars, trade shape and controls), so the inputs are judged alike. 9 trials.

    python stablecoin_data.py fetch && python stablecoin_study.py   # → logs/backtest_reports/stablecoin_<date>.md

Research only: no trade decision, no order API, no hosted model.
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone

import dvol_study as ds
import stablecoin_data as sd
from checklist_study import C_FROM, C_TRADES, REPORT_DIR
from mtf_entry_study import LIVE
from quality_study import CUTOFF

PREREG = "prereg_stablecoin_20261117.md"
KINDS = tuple(sd.FEATURES)
A_VARIANTS = tuple((k, thr) for k in KINDS for thr in (0.5, 1.0))
B_VARIANTS = tuple((k, 1.0) for k in KINDS)
TITLE = "Stablecoin supply flows (DefiLlama)"
INTRO = ("Data: total USD stablecoin supply and USDT supply, daily (`stablecoin_data.py`), the row dated D used "
         "from D + 1 day; one market-wide value for every coin; every feature is read as FOLLOW THE MONEY "
         "(positive = supply growing faster than usual = favours a LONG).")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--date-tag", default=datetime.now(timezone.utc).strftime("%Y%m%d"))
    a = ap.parse_args(argv)
    t0 = time.time()
    idx = sd.StableIndex.load()
    trades = [t for t in json.loads(C_TRADES.read_text())
              if (t["signal"], t["tf"]) in LIVE and t["result"].get("filled") and C_FROM <= t["signal_ms"] < CUTOFF
              and t["symbol"] in ds.SYMBOLS]
    symbols = sorted({t["symbol"] for t in trades})
    print(f"test A population: {len(trades)} trades, {len(symbols)} symbols")
    a_rows, a_table, a_verdict = ds.run_test_a(idx, trades, A_VARIANTS)
    print(f"A: {a_verdict}")
    b_rows, b_table, b_verdict = ds.run_test_b(idx, symbols, B_VARIANTS)
    print(f"B: {b_verdict}")
    cov = ds.coverage(idx, C_FROM, CUTOFF, KINDS, sd.DAY_MS)
    out = ds.write_report(a.date_tag, cov, a_table, a_verdict, b_table, b_verdict, len(trades), time.time() - t0,
                          title=TITLE, intro=INTRO, prereg=PREREG, out_name="stablecoin", input_name="stablecoin supply")
    (REPORT_DIR / f"stablecoin_{a.date_tag}_rows.json").write_text(
        json.dumps({"A": a_rows, "B": b_rows, "A_verdict": a_verdict, "B_verdict": b_verdict}, default=str))
    print(f"report → {out}")


if __name__ == "__main__":
    main()
