#!/usr/bin/env python
"""
xs_momentum_v2_crypto.py — re-validate the v2 "momentum ex-carry, pit30, 10% cap" book on a CRYPTO-ONLY universe.
RESEARCH ONLY (zero Claude tokens, no order logic). Appends a section to logs/backtest_reports/xs_momentum_v2_<date>.md.

Exclusion mechanism: Bybit instruments-info `symbolType` in {stock, ETF, commodity, forex} (Bybit's own classification of
tokenized TradFi perps) PLUS a frozen supplement for pegged assets Bybit leaves blank (gold-backed tokens, USD stablecoins).
"""
import argparse
import json
import os
import time
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

import xs_momentum_backtest as v1
import xs_momentum_v2 as v2
from xs_momentum_backtest import _get, fmt, fmt_pct, halves, metrics
from xs_momentum_v2 import ORDER, LOOKBACKS, SKIP_VARIANT, LEG_CAP, CARRY_N, CARRY_MIN_LISTED, run_momentum, run_carry, FundingStore, momentum_verdict

TRADFI_SYMBOL_TYPES = ["stock", "ETF", "commodity", "forex"]
PEGGED_SUPPLEMENT = ["XAUTUSDT", "PAXGUSDT", "USDCUSDT", "USDEUSDT", "USD1USDT"]
PANEL_END = "2026-10-03"      # same last bar as the v2 report so numbers are comparable


def fetch_instruments():
    out, cursor = [], ""
    while True:
        p = {"category": "linear", "limit": 1000}
        if cursor:
            p["cursor"] = cursor
        res = _get("/v5/market/instruments-info", p)
        out += res.get("list", [])
        cursor = res.get("nextPageCursor") or ""
        if not cursor:
            break
    return [x for x in out if x.get("status") == "Trading" and x.get("quoteCoin") == "USDT" and x.get("contractType") == "LinearPerpetual"]


def tradfi_set(instruments):
    flagged = {x["symbol"]: x.get("symbolType", "") for x in instruments if x.get("symbolType") in TRADFI_SYMBOL_TYPES}
    return flagged, set(flagged) | set(PEGGED_SUPPLEMENT)


def agg(weeks):
    h1, h2 = halves(weeks)
    return {"full": metrics(weeks), "h1": metrics(h1), "h2": metrics(h2), "exf": metrics(weeks, "net_exfund")}


def run_book(close, turn, launch_ser, fstore, rebal_dates, uni_mask):
    def listed_mask(min_days):
        def fn(t):
            return (((t + timedelta(days=1)) - launch_ser).dt.days >= min_days) & uni_mask
        return fn

    _, baskets = run_carry(close, turn, listed_mask(CARRY_MIN_LISTED), rebal_dates, fstore, CARRY_N, hedged=True)
    res, weeks = {}, {}
    for lab, k, skip in [(str(k), k, 0) for k in LOOKBACKS] + [SKIP_VARIANT]:
        w = run_momentum(close, turn, listed_mask(30), k, skip, rebal_dates, fstore, LEG_CAP, lambda t: baskets.get(t, []))
        weeks[lab], res[lab] = w, agg(w)
    return res, weeks, baskets


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date-tag", default="20261004")
    args = ap.parse_args()
    t0 = time.time()
    now = datetime.now(timezone.utc)
    today_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_ms = int((today_midnight - timedelta(days=v1.DAYS)).timestamp() * 1000)

    inst = fetch_instruments()
    flagged, tradfi = tradfi_set(inst)
    universe = [{"symbol": x["symbol"], "launchTime": int(x.get("launchTime") or 0)} for x in inst]
    close, turn, skipped, first_date = v1.build_panel(universe, start_ms, int(today_midnight.timestamp() * 1000))
    close, turn = close.loc[:PANEL_END], turn.loc[:PANEL_END]
    syms = list(close.columns)
    idx = close.index
    rebal_dates = [d for i, d in enumerate(idx) if d.dayofweek == 6 and i >= max(LOOKBACKS) + 2 and i + 7 < len(idx)]
    launch_ser = pd.Series({s: (pd.Timestamp(next(u["launchTime"] for u in universe if u["symbol"] == s), unit="ms", tz="UTC")
                                if next(u["launchTime"] for u in universe if u["symbol"] == s) > 0 else first_date[s]) for s in syms})
    raw = {s: v2.load_funding(s, start_ms, int(now.timestamp() * 1000)) for s in syms}
    fstore = FundingStore(raw)
    crypto_mask = pd.Series({s: s not in tradfi for s in syms})
    print(f"panel {len(syms)} symbols → {int(crypto_mask.sum())} crypto-only ({len(syms) - int(crypto_mask.sum())} TradFi/pegged in panel); "
          f"{len(rebal_dates)} weeks")

    res_all, wk_all, _ = run_book(close, turn, launch_ser, fstore, rebal_dates, pd.Series(True, index=syms))
    res_cry, wk_cry, baskets_cry = run_book(close, turn, launch_ser, fstore, rebal_dates, crypto_mask)
    n_variants = 2 * len(ORDER)

    # TradFi share of leg-weeks in the ALL-perps book
    share = {}
    for lab in ("56", "91"):
        rows = []
        for w in wk_all[lab]:
            ws = w["weights"]
            longs, shorts = ws[ws > 0].index, ws[ws < 0].index
            rows.append((np.mean([s in tradfi for s in longs]), np.mean([s in tradfi for s in shorts]),
                         any(s in tradfi for s in ws.index), w["date"]))
        h = len(rows) // 2
        share[lab] = {
            "long": float(np.mean([r[0] for r in rows])), "short": float(np.mean([r[1] for r in rows])),
            "weeks_any": int(sum(r[2] for r in rows)), "n": len(rows),
            "h2_long": float(np.mean([r[0] for r in rows[h:]])), "h2_short": float(np.mean([r[1] for r in rows[h:]])),
            "first_week": next((r[3].strftime("%Y-%m-%d") for r in rows if r[2]), "never"),
            # P&L attribution: cumulative gross contribution of TradFi names (price only) in the all-perps book
            "pnl_tradfi": float(sum(float((w["weights"][[s for s in w["weights"].index if s in tradfi]]
                                           * w["rets"][[s for s in w["weights"].index if s in tradfi]]).sum()) for w in wk_all[lab])),
            "pnl_total_gross": float(sum(w["gross"] for w in wk_all[lab])),
        }

    v_cry_5691 = momentum_verdict({lab: res_cry[lab] for lab in ("56", "91")}, ["56", "91"])
    v_cry_ladder = momentum_verdict(res_cry, ORDER)
    v_all_5691 = momentum_verdict({lab: res_all[lab] for lab in ("56", "91")}, ["56", "91"])

    L = ["", "---", "", f"## 5. Crypto-only universe re-validation (appended {now.strftime('%Y-%m-%d %H:%M')} UTC)", ""]
    L.append("**Why:** the first paper weights (2026-10-05) had 6/7 k=56 shorts in tokenized TradFi perps (SOXS, XAG, XAU, XAUT, NVDA, CL). "
             "Shorting gold/oil/NVDA against long alts is a cross-asset bet with weekend gaps and different funding, not the crypto "
             "momentum that was validated. The paper clock has not started (first scoring 2026-10-12), so the rule set may change once.\n")
    L.append("**Exclusion mechanism (principled, frozen into RULES/rules_hash):** Bybit `instruments-info` exposes `symbolType` "
             f"∈ {{{', '.join(TRADFI_SYMBOL_TYPES)}}} for tokenized TradFi perps (blank or `innovation` for crypto) plus `marketRegion` / "
             f"`underlyingTicker`. Today that flags **{len(flagged)}** of {len(inst)} Trading USDT perps "
             f"(stock {sum(v == 'stock' for v in flagged.values())}, ETF {sum(v == 'ETF' for v in flagged.values())}, "
             f"commodity {sum(v == 'commodity' for v in flagged.values())}, forex {sum(v == 'forex' for v in flagged.values())}). "
             f"Bybit leaves pegged crypto tokens blank, so a frozen supplement is added: {', '.join(PEGGED_SUPPLEMENT)} "
             "(gold-backed tokens, USD stablecoins). The live filter reads `symbolType` at each rebalance (new TradFi listings are caught "
             "automatically); the supplement is a constant. Classification is a static property of the symbol, so applying it to history "
             f"is not look-ahead. {len(syms) - int(crypto_mask.sum())} of the {len(syms)} panel symbols are excluded "
             f"(earliest TradFi launch in panel: {min((launch_ser[s] for s in syms if s in tradfi), default=pd.NaT)}).\n")
    L.append("### TradFi presence in the earlier ALL-perps ex-carry book (share of leg-weeks)\n")
    L.append("| k | long leg share | short leg share | H2 long | H2 short | weeks with any TradFi | first week | TradFi price P&L (cum, gross) | total gross P&L |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for lab in ("56", "91"):
        s = share[lab]
        L.append(f"| {lab} | {s['long'] * 100:.1f}% | {s['short'] * 100:.1f}% | {s['h2_long'] * 100:.1f}% | {s['h2_short'] * 100:.1f}% | "
                 f"{s['weeks_any']}/{s['n']} | {s['first_week']} | {s['pnl_tradfi'] * 100:+.1f}% | {s['pnl_total_gross'] * 100:+.1f}% |")
    L.append("")
    L.append("### Side by side — momentum ex-carry, pit30, 10% cap (net of fees/slippage/actual funding)\n")
    L.append("| k | universe | n wks | gross ann | net ann | net Sharpe | max DD | % wks + | H1 Sharpe | H2 Sharpe | H1 MDD | H2 MDD | ex-funding Sharpe | names/leg |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for lab in ORDER:
        for name, res in (("ALL perps (prev.)", res_all), ("CRYPTO-ONLY", res_cry)):
            r = res[lab]
            m = r["full"]
            L.append(f"| {lab}{' ←' if lab in ('56', '91') else ''} | {name} | {m['n']} | {fmt_pct(m['gross_ann'])} | {fmt_pct(m['net_ann'])} | "
                     f"{fmt(m['sharpe'])} | {fmt_pct(m['mdd'])} | {fmt_pct(m['pct_pos'], 0)} | {fmt(r['h1']['sharpe'])} | {fmt(r['h2']['sharpe'])} | "
                     f"{fmt_pct(r['h1']['mdd'])} | {fmt_pct(r['h2']['mdd'])} | {fmt(r['exf']['sharpe'])} | {fmt(m['names'], 1)} |")
    L.append("")
    L.append("### Mechanical verdict (original pre-registered momentum bar)\n")
    L.append("| book | verdict | detail |")
    L.append("|---|---|---|")
    L.append(f"| ALL perps, k=56+91 (reproduction of §4) | **{v_all_5691[0]}** | SHIP both k: {[k for k, ok in v_all_5691[1].items() if ok] or 'none'} |")
    L.append(f"| CRYPTO-ONLY, k=56+91 (pre-specified) | **{v_cry_5691[0]}** | SHIP: {[k for k, ok in v_cry_5691[1].items() if ok] or 'none'}; "
             f"CANDIDATE: {[k for k, ok in v_cry_5691[2].items() if ok] or 'none'} |")
    L.append(f"| CRYPTO-ONLY, full ladder (context) | **{v_cry_ladder[0]}** | SHIP pairs {v_cry_ladder[3] or 'none'}; "
             f"CANDIDATE: {[k for k, ok in v_cry_ladder[2].items() if ok] or 'none'} |")
    L.append("")
    L.append(f"Multiple testing: {n_variants} additional variants in this section ({len(ORDER)} lookbacks × 2 universes), on top of 30 (v2) + 48 (v1). "
             "The crypto-only rerun was pre-specified for k=56 and k=91 only; the other lookbacks are context.\n")
    L.append("### Full TradFi exclusion list (Bybit `symbolType` flag, as of this run)\n")
    for typ in TRADFI_SYMBOL_TYPES:
        names = sorted(s for s, v in flagged.items() if v == typ)
        L.append(f"- **{typ}** ({len(names)}): {', '.join(names)}")
    L.append(f"- **supplement (pegged)**: {', '.join(PEGGED_SUPPLEMENT)}")
    L.append(f"\n_Generated by `xs_momentum_v2_crypto.py` in {time.time() - t0:.0f}s._\n")

    path = os.path.join(v1.REPORT_DIR, f"xs_momentum_v2_{args.date_tag}.md")
    with open(path, "a") as f:
        f.write("\n".join(L))
    json.dump({"tradfi_symbol_types": TRADFI_SYMBOL_TYPES, "pegged_supplement": PEGGED_SUPPLEMENT, "flagged": flagged},
              open(os.path.join(v1.REPORT_DIR, f"xs_momentum_tradfi_list_{args.date_tag}.json"), "w"), indent=1)
    print("\n".join(L[4:8]))
    print("\n".join(x for x in L if x.startswith("| 56") or x.startswith("| 91") or x.startswith("| ALL") or x.startswith("| CRYPTO")))
    print(f"appended to {path}")


if __name__ == "__main__":
    main()
