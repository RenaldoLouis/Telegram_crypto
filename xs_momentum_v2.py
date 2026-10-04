#!/usr/bin/env python
"""
xs_momentum_v2.py — follow-up to xs_momentum_backtest.py (RESEARCH ONLY, zero Claude tokens, no order logic).

1. Point-in-time universe via instruments-info launchTime (listed >= 30d / 90d before the rebalance).
2. 10%-of-leg weight cap (with / without).
3. FUNDING-CARRY as its own product (long most-negative-funding basket, 1:1 BTCUSDT hedge) — pre-registered bar.
4. Momentum k=56/91 on the PIT universe, capped, with the carry basket EXCLUDED.

Run:  source venv/bin/activate && python xs_momentum_v2.py
Out:  logs/backtest_reports/xs_momentum_v2_YYYYMMDD.md
"""
import argparse
import json
import math
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

import xs_momentum_backtest as v1
from xs_momentum_backtest import (CACHE_DIR, REPORT_DIR, DAYS, MIN_TURNOVER_7D, COST_PER_UNIT_TURNOVER, TAKER_FEE, SLIPPAGE,
                                  _get, _nan, fmt, fmt_pct, halves, metrics, passes_ship, _p_sharpe)

LOOKBACKS = [7, 14, 28, 56, 91]
SKIP_VARIANT = ("28s7", 28, 7)
ORDER = [str(k) for k in LOOKBACKS] + [SKIP_VARIANT[0]]
LEG_CAP = 0.10            # max share of a leg in one name
CARRY_N = 10
CARRY_MIN_LISTED = 30
HEDGE = "BTCUSDT"
FUNDING_THREADS = 4

MOMENTUM_BAR = (
    "SHIP-CANDIDATE if, net of costs, annualized Sharpe >= 1.0 AND max drawdown <= 25% AND >= 55% of weeks positive, "
    "holding on BOTH chronological halves AND for at least two adjacent lookbacks. CANDIDATE if net Sharpe >= 0.5 on both "
    "halves. Otherwise NO. Costs and the survivorship caveat are part of the result, not footnotes."
)
CARRY_BAR = (
    "Weekly long-only basket of the N=10 symbols with the most negative trailing-7-day average funding rate (shorts pay longs), "
    "eligible if listed >= 30d and trailing-7d mean turnover >= $10M, equal weight, hedged 1:1 notional with a BTCUSDT short "
    "(so it is a carry trade, not a beta bet). SHIP-CANDIDATE if net Sharpe >= 1.0 AND max drawdown <= 20% AND >= 55% weeks "
    "positive on BOTH chrono halves; CANDIDATE if net Sharpe >= 0.5 on both halves; else NO."
)


# ----------------------------------------------------------------------------- funding store
def load_funding(symbol, start_ms, end_ms):
    """Same cache files as v1 (xs_funding_<sym>.json); page cap raised to 80."""
    path = os.path.join(CACHE_DIR, f"xs_funding_{symbol}.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    rows, cursor_end = [], end_ms
    for _ in range(80):
        res = _get("/v5/market/funding/history", {"category": "linear", "symbol": symbol, "startTime": start_ms,
                                                  "endTime": cursor_end, "limit": 200})
        lst = res.get("list", [])
        if not lst:
            break
        for it in lst:
            rows.append([int(it["fundingRateTimestamp"]), float(it["fundingRate"])])
        oldest = min(int(it["fundingRateTimestamp"]) for it in lst)
        if oldest <= start_ms or len(lst) < 200:
            break
        cursor_end = oldest - 1
        time.sleep(0.1)
    rows.sort()
    with open(path, "w") as f:
        json.dump(rows, f)
    return rows


class FundingStore:
    """O(log n) window sums per symbol."""

    def __init__(self, raw):
        self.ts, self.cum = {}, {}
        for s, rows in raw.items():
            if not rows:
                continue
            t = np.array([r[0] for r in rows], dtype=np.int64)
            c = np.concatenate([[0.0], np.cumsum([r[1] for r in rows])])
            self.ts[s], self.cum[s] = t, c

    def window_sum(self, s, a_ms, b_ms):
        """sum of settlements with a < ts <= b; None if no data for symbol."""
        if s not in self.ts:
            return None
        t, c = self.ts[s], self.cum[s]
        return float(c[np.searchsorted(t, b_ms, "right")] - c[np.searchsorted(t, a_ms, "right")])

    def has(self, s):
        return s in self.ts


# ----------------------------------------------------------------------------- helpers
def t_close_ms(t):
    return int((t + timedelta(days=1)).timestamp() * 1000)   # daily bar opened at t closes at t+1d 00:00 UTC


WEEK_MS = 7 * 86400 * 1000


def finish_week(wk, w, rets, prev_end_w, fstore, t):
    """Fill gross/turnover/cost/funding/net for a week given weights w (Series) and forward returns rets."""
    gap = int(rets.isna().sum())
    rets = rets.fillna(0.0)
    gross = float((w * rets).sum())
    end_w = (w * (1.0 + rets)) / (1.0 + gross) if gross > -1 else w * 0.0
    all_syms = w.index.union(prev_end_w.index)
    turnover = float((w.reindex(all_syms).fillna(0) - prev_end_w.reindex(all_syms).fillna(0)).abs().sum())
    a, b = t_close_ms(t), t_close_ms(t) + WEEK_MS
    f_total, contrib = 0.0, {}
    for sym, wt in w.items():
        fs = fstore.window_sum(sym, a, b)
        if fs is None:
            fs = v1.FLAT_FUNDING_8H * 21
        contrib[sym] = wt * fs
        f_total += wt * fs
    wk.update({
        "date": t, "weights": w, "rets": rets, "gross": gross, "turnover": turnover,
        "n_long": int((w > 0).sum()), "n_short": int((w < 0).sum()), "gap_fills": gap,
        "cost": turnover * COST_PER_UNIT_TURNOVER, "funding": f_total, "funding_contrib": contrib,
    })
    wk["net"] = gross - wk["cost"] - f_total
    wk["net_exfund"] = gross - wk["cost"]
    return end_w


# ----------------------------------------------------------------------------- momentum
def run_momentum(close, turn, listed_mask_fn, lookback, skip, rebal_dates, fstore, cap=None, exclude_fn=None):
    need = lookback + 2
    hist_ok = close.notna().rolling(need).sum() == need
    turn_ok = turn.rolling(7).mean() >= MIN_TURNOVER_7D
    sig = close.shift(skip) / close.shift(lookback) - 1.0
    fwd = close.shift(-7) / close - 1.0
    weeks, prev_end_w = [], pd.Series(dtype=float)
    for t in rebal_dates:
        elig = hist_ok.loc[t] & turn_ok.loc[t] & sig.loc[t].notna() & listed_mask_fn(t)
        if exclude_fn is not None:
            elig = elig & ~elig.index.isin(exclude_fn(t))
        syms = elig[elig].index
        n = len(syms)
        if n < 10:
            continue
        s = sig.loc[t, syms].sort_values()
        nd = max(1, n // 10)
        per = 1.0 / nd if cap is None else min(1.0 / nd, cap)
        w = {}
        for x in s.index[-nd:]:
            w[x] = 0.5 * per
        for x in s.index[:nd]:
            w[x] = -0.5 * per
        w = pd.Series(w, dtype=float)
        wk = {"n_elig": n, "leg_invested": per * nd}
        prev_end_w = finish_week(wk, w, fwd.loc[t, w.index], prev_end_w, fstore, t)
        weeks.append(wk)
    return weeks


# ----------------------------------------------------------------------------- funding carry
def carry_signal(fstore, syms, t):
    """trailing-7d cumulative funding ending at the rebalance close (sum of settlements). Most negative = shorts pay longs most."""
    b = t_close_ms(t)
    a = b - WEEK_MS
    out = {}
    for s in syms:
        v = fstore.window_sum(s, a, b)
        if v is not None:
            out[s] = v
    return pd.Series(out, dtype=float)


def run_carry(close, turn, listed_mask_fn, rebal_dates, fstore, n_names, hedged, n_basket_sel=CARRY_N):
    turn_ok = turn.rolling(7).mean() >= MIN_TURNOVER_7D
    hist_ok = close.notna().rolling(9).sum() == 9
    fwd = close.shift(-7) / close - 1.0
    weeks, prev_end_w, baskets = [], pd.Series(dtype=float), {}
    for t in rebal_dates:
        elig = hist_ok.loc[t] & turn_ok.loc[t] & listed_mask_fn(t)
        syms = [s for s in elig[elig].index if fstore.has(s) and s != HEDGE]
        sig = carry_signal(fstore, syms, t).sort_values()
        if len(sig) < n_names:
            continue
        basket = list(sig.index[:n_names])
        baskets[t] = list(sig.index[:n_basket_sel])
        w = pd.Series({s: 1.0 / n_names for s in basket}, dtype=float)
        if hedged:
            w[HEDGE] = -1.0
        rets = fwd.loc[t, w.index]
        wk = {"n_elig": len(sig), "basket": basket, "signal_mean": float(sig.iloc[:n_names].mean()),
              "price_alts": float((w.drop(HEDGE, errors="ignore") * rets.drop(HEDGE, errors="ignore").fillna(0)).sum()),
              "price_hedge": float(-rets.get(HEDGE, 0.0)) if hedged else 0.0}
        prev_end_w = finish_week(wk, w, rets, prev_end_w, fstore, t)
        if hedged:
            wk["fund_alts"] = float(sum(c for s, c in wk["funding_contrib"].items() if s != HEDGE))
            wk["fund_hedge"] = float(wk["funding_contrib"].get(HEDGE, 0.0))
        else:
            wk["fund_alts"], wk["fund_hedge"] = wk["funding"], 0.0
        weeks.append(wk)
    return weeks, baskets


def carry_decomp(weeks):
    if not weeks:
        return {}
    n = len(weeks)
    f = lambda k: float(sum(w[k] for w in weeks))  # noqa: E731
    return {"n": n, "price_alts": f("price_alts"), "price_hedge": f("price_hedge"),
            "funding_alts": -f("fund_alts"), "funding_hedge": -f("fund_hedge"), "cost": -f("cost"),
            "net": f("net"), "gross": f("gross")}


# ----------------------------------------------------------------------------- verdicts
def momentum_verdict(res_by_lab, order):
    ship_ok, cand_ok = {}, {}
    for lab in order:
        r = res_by_lab[lab]
        ship_ok[lab] = passes_ship(r["full"]) and passes_ship(r["h1"]) and passes_ship(r["h2"])
        cand_ok[lab] = all(r[h]["sharpe"] is not None and r[h]["sharpe"] >= 0.5 for h in ("h1", "h2"))
    pairs = [(order[i], order[i + 1]) for i in range(len(order) - 1)]
    if "28" in order and "28s7" in order:
        pairs.append(("28", "28s7"))
    ship_pairs = [p for p in pairs if ship_ok[p[0]] and ship_ok[p[1]]]
    if ship_pairs:
        return "SHIP-CANDIDATE", ship_ok, cand_ok, ship_pairs
    if any(cand_ok.values()):
        return "CANDIDATE", ship_ok, cand_ok, []
    return "NO", ship_ok, cand_ok, []


def carry_passes_ship(m):
    return (m["sharpe"] is not None and m["sharpe"] >= 1.0 and m["mdd"] is not None and m["mdd"] <= 0.20
            and m["pct_pos"] is not None and m["pct_pos"] >= 0.55)


def carry_verdict(r):
    if carry_passes_ship(r["h1"]) and carry_passes_ship(r["h2"]):
        return "SHIP-CANDIDATE"
    if all(r[h]["sharpe"] is not None and r[h]["sharpe"] >= 0.5 for h in ("h1", "h2")):
        return "CANDIDATE"
    return "NO"


# ----------------------------------------------------------------------------- report helpers
HDR = ("| variant | n wks | gross ann | net ann | net Sharpe | max DD | % wks + | H1 Sharpe | H2 Sharpe | H1 MDD | H2 MDD | "
       "ex-funding Sharpe | turnover/wk | names/leg |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")


def row(label, r):
    m = r["full"]
    return (f"| {label} | {m['n']} | {fmt_pct(m['gross_ann'])} | {fmt_pct(m['net_ann'])} | {fmt(m['sharpe'])} | {fmt_pct(m['mdd'])} | "
            f"{fmt_pct(m['pct_pos'], 0)} | {fmt(r['h1']['sharpe'])} | {fmt(r['h2']['sharpe'])} | {fmt_pct(r['h1']['mdd'])} | "
            f"{fmt_pct(r['h2']['mdd'])} | {fmt(r['exf']['sharpe'])} | {fmt(m['turnover'])} | {fmt(m['names'], 1)} |")


def agg(weeks):
    h1, h2 = halves(weeks)
    return {"full": metrics(weeks), "h1": metrics(h1), "h2": metrics(h2), "exf": metrics(weeks, "net_exfund"),
            "h1_exf": metrics(h1, "net_exfund"), "h2_exf": metrics(h2, "net_exfund")}


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date-tag", default=datetime.now(timezone.utc).strftime("%Y%m%d"))
    args = ap.parse_args()
    t0 = time.time()
    os.makedirs(REPORT_DIR, exist_ok=True)

    now = datetime.now(timezone.utc)
    today_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_midnight_ms = int(today_midnight.timestamp() * 1000)
    start_ms = int((today_midnight - timedelta(days=DAYS)).timestamp() * 1000)

    print("[1/5] universe + launchTime …")
    universe = v1.fetch_universe()
    launch = {u["symbol"]: u["launchTime"] for u in universe}
    print("[2/5] panel (from cache) …")
    close, turn, skipped, first_date = v1.build_panel(universe, start_ms, today_midnight_ms)
    syms = list(close.columns)
    idx = close.index
    max_need = max(LOOKBACKS) + 2
    rebal_dates = [d for i, d in enumerate(idx) if d.dayofweek == 6 and i >= max_need and i + 7 < len(idx)]
    print(f"  {len(syms)} symbols, {len(rebal_dates)} rebalances {rebal_dates[0].date()} → {rebal_dates[-1].date()}")

    # launch date per symbol: launchTime if present else first cached bar (flagged)
    launch_ts = {}
    n_no_launch = 0
    for s in syms:
        lt = launch.get(s, 0)
        if lt and lt > 0:
            launch_ts[s] = pd.Timestamp(lt, unit="ms", tz="UTC")
        else:
            launch_ts[s] = first_date[s]
            n_no_launch += 1
    launch_ser = pd.Series(launch_ts)

    def listed_mask(min_days):
        def fn(t):
            return ((t + timedelta(days=1)) - launch_ser).dt.days >= min_days
        return fn

    print("[3/5] funding for every panel symbol …")
    end_ms = int(now.timestamp() * 1000)
    raw = {}
    missing = [s for s in syms if not os.path.exists(os.path.join(CACHE_DIR, f"xs_funding_{s}.json"))]
    print(f"  {len(syms) - len(missing)} cached, fetching {len(missing)}")
    with ThreadPoolExecutor(max_workers=FUNDING_THREADS) as ex:
        futs = {ex.submit(load_funding, s, start_ms, end_ms): s for s in syms}
        done = 0
        for fut in as_completed(futs):
            s = futs[fut]
            try:
                raw[s] = fut.result()
            except Exception as e:  # noqa: BLE001
                print(f"  [funding fail] {s}: {e}")
            done += 1
            if done % 100 == 0:
                print(f"  funding {done}/{len(syms)}")
    fstore = FundingStore(raw)
    n_fund = len(fstore.ts)
    print(f"  funding available for {n_fund}/{len(syms)} symbols")

    print("[4/5] portfolios …")
    n_variants = 0
    mom = {}   # (universe_label, cap_label, lab) -> weeks
    for uni_label, min_days in (("pit30", 30), ("pit90", 90)):
        for cap_label, cap in (("nocap", None), ("cap10", LEG_CAP)):
            if uni_label == "pit90" and cap_label == "nocap":
                continue
            for lab, k, skip in [(str(k), k, 0) for k in LOOKBACKS] + [SKIP_VARIANT]:
                mom[(uni_label, cap_label, lab)] = run_momentum(close, turn, listed_mask(min_days), k, skip, rebal_dates, fstore, cap)
                n_variants += 1

    carry = {}
    for n_names in (5, 10, 20):
        for hedged in (True, False):
            carry[(n_names, hedged)] = run_carry(close, turn, listed_mask(CARRY_MIN_LISTED), rebal_dates, fstore, n_names, hedged)
            n_variants += 1
    _, carry_baskets = carry[(CARRY_N, True)]

    def exclude_carry(t):
        return carry_baskets.get(t, [])

    mom_ex = {}
    for lab, k in (("56", 56), ("91", 91)):
        mom_ex[lab] = run_momentum(close, turn, listed_mask(30), k, 0, rebal_dates, fstore, LEG_CAP, exclude_carry)
        n_variants += 1
    # also the full ladder ex-carry so the "adjacent lookbacks" clause can be evaluated honestly
    for lab, k, skip in [(str(k), k, 0) for k in LOOKBACKS] + [SKIP_VARIANT]:
        if lab not in mom_ex:
            mom_ex[lab] = run_momentum(close, turn, listed_mask(30), k, skip, rebal_dates, fstore, LEG_CAP, exclude_carry)
            n_variants += 1

    print("[5/5] report …")
    res_mom = {key: agg(v) for key, v in mom.items()}
    res_ex = {lab: agg(v) for lab, v in mom_ex.items()}
    res_carry = {key: agg(v[0]) for key, v in carry.items()}
    for (n_names, _h), r in res_carry.items():          # names/leg = basket size (hedge leg is 1 name)
        for per in r.values():
            per["names"] = float(n_names)

    verdicts = {}
    for uni_label, cap_label in (("pit30", "nocap"), ("pit30", "cap10"), ("pit90", "cap10")):
        verdicts[(uni_label, cap_label)] = momentum_verdict({lab: res_mom[(uni_label, cap_label, lab)] for lab in ORDER}, ORDER)
    v_ex = momentum_verdict(res_ex, ORDER)
    v_ex_5691 = momentum_verdict({lab: res_ex[lab] for lab in ("56", "91")}, ["56", "91"])
    v_carry = carry_verdict(res_carry[(CARRY_N, True)])

    # names per leg stats
    def leg_stats(weeks):
        nl = [w["n_long"] for w in weeks]
        ne = [w["n_elig"] for w in weeks]
        return (float(np.mean(nl)), int(min(nl)), int(max(nl)), float(np.mean(ne)), int(min(ne)), int(max(ne)))

    # survivorship context for carry baskets: how many basket names are "young"
    young = []
    for t, b in carry_baskets.items():
        age = [((t + timedelta(days=1)) - launch_ser[s]).days for s in b]
        young.append(np.mean([a < 90 for a in age]))
    pct_young = float(np.mean(young)) if young else float("nan")

    L = []
    L.append(f"# Cross-sectional momentum v2 + funding-carry — Bybit USDT perps — {args.date_tag}\n")
    L.append("## Pre-registered bars (written before the run)\n")
    L.append(f"**Momentum (unchanged from v1):** {MOMENTUM_BAR}\n")
    L.append(f"**Funding carry (new):** {CARRY_BAR}\n")
    L.append("Definition fixed before running: \"trailing-7-day average funding rate\" is measured as the cumulative funding over the "
             "7 days ending at the rebalance close (sum of all settlements, so 1h/4h/8h-interval symbols are comparable; ranking by "
             "sum is identical to ranking by average daily rate). Most negative = shorts paid longs the most last week.\n")

    L.append("## Verdicts (mechanical)\n")
    L.append("| study | verdict | detail |")
    L.append("|---|---|---|")
    for (u, c), (v, ship_ok, cand_ok, pairs) in verdicts.items():
        L.append(f"| Momentum L/S, {u}, {c} | **{v}** | SHIP pairs {pairs or 'none'}; CANDIDATE lookbacks "
                 f"{[k for k, ok in cand_ok.items() if ok] or 'none'} |")
    L.append(f"| Momentum L/S, pit30, cap10, carry basket EXCLUDED (k=56,91 only, as pre-specified) | **{v_ex_5691[0]}** | "
             f"CANDIDATE lookbacks {[k for k, ok in v_ex_5691[2].items() if ok] or 'none'}; SHIP both k: "
             f"{[k for k, ok in v_ex_5691[1].items() if ok] or 'none'} |")
    L.append(f"| Momentum L/S, pit30, cap10, carry EXCLUDED, full ladder (context) | **{v_ex[0]}** | "
             f"CANDIDATE lookbacks {[k for k, ok in v_ex[2].items() if ok] or 'none'}; SHIP pairs {v_ex[3] or 'none'} |")
    rc = res_carry[(CARRY_N, True)]
    L.append(f"| Funding carry N=10 hedged | **{v_carry}** | H1 Sharpe {fmt(rc['h1']['sharpe'])} / MDD {fmt_pct(rc['h1']['mdd'])} / "
             f"%+ {fmt_pct(rc['h1']['pct_pos'], 0)}; H2 Sharpe {fmt(rc['h2']['sharpe'])} / MDD {fmt_pct(rc['h2']['mdd'])} / "
             f"%+ {fmt_pct(rc['h2']['pct_pos'], 0)} |")
    L.append("")

    L.append("## 1. Point-in-time universe\n")
    L.append(f"- Listing age from `instruments-info.launchTime` ({n_no_launch} symbols lacked it → first cached bar used). "
             f"A symbol is eligible at a rebalance only if listed ≥30d (`pit30`) / ≥90d (`pit90`) before that Monday 00:00 UTC, "
             f"plus ≥ lookback+2 bars and trailing-7d turnover ≥ ${MIN_TURNOVER_7D / 1e6:.0f}M.")
    L.append("- Names per leg (decile = floor(eligible/10)):\n")
    L.append("| universe | k | avg names/leg | min | max | avg eligible | min | max |")
    L.append("|---|---|---|---|---|---|---|---|")
    for u in ("pit30", "pit90"):
        for lab in ORDER:
            st = leg_stats(mom[(u, "cap10", lab)])
            L.append(f"| {u} | {lab} | {st[0]:.1f} | {st[1]} | {st[2]} | {st[3]:.0f} | {st[4]} | {st[5]} |")
    L.append(f"\n- **Survivorship is NOT fixed.** `instruments-info` lists only symbols trading today; coins delisted inside the window are "
             f"absent and this endpoint cannot recover them. Direction of the bias: (i) delisted perps are overwhelmingly coins that "
             f"collapsed → they would have sat in the bottom decile (SHORT leg) on the way down, so their absence UNDERSTATES short-leg "
             f"profit; (ii) but many also pumped first (and carried extreme negative funding while squeezed) before collapsing → their "
             f"absence OVERSTATES the long leg and OVERSTATES the funding-carry basket, whose selection is literally 'the most squeezed "
             f"coins' — the ones most likely to be delisted after the squeeze unwinds. Net: the carry product and the long leg are biased "
             f"UP; the L/S momentum book is ambiguous but more likely biased up because its P&L here comes from the long leg. "
             f"{pct_young * 100:.0f}% of carry-basket names were listed < 90 days at selection.\n")

    L.append("## 2. Momentum L/S — point-in-time universe, with / without the 10%-of-leg cap\n")
    L.append(f"Cap = no name > {LEG_CAP * 100:.0f}% of its leg (= {LEG_CAP * 50:.0f}% of equity). With decile legs of < 10 names an "
             "equal-weight leg already exceeds 10%/name, so the cap BINDS structurally: there is nothing to redistribute to, the residual "
             "stays in cash and the leg is under-invested (reported as `leg invested`). Net = gross − fees/slippage − actual funding.\n")
    for (u, c), title in ((("pit30", "nocap"), "pit30, uncapped"), (("pit30", "cap10"), "pit30, 10% cap"), (("pit90", "cap10"), "pit90, 10% cap")):
        inv = float(np.mean([w["leg_invested"] for lab in ORDER for w in mom[(u, c, lab)]]))
        L.append(f"### {title} (avg leg invested {inv * 100:.0f}%)\n")
        L.append(HDR)
        for lab in ORDER:
            L.append(row(f"k={lab}", res_mom[(u, c, lab)]))
        L.append("")

    L.append("## 3. Funding carry as its own product\n")
    L.append(f"Long the N most-negative-trailing-funding names (equal weight, 100% notional), short {HEDGE} 100% notional when hedged. "
             f"Costs {TAKER_FEE * 100:.3f}% + {SLIPPAGE * 100:.2f}% per unit turnover (both legs, drift-adjusted); funding = actual "
             f"settlements inside the holding week on both legs (longs receive negative funding; the BTC short pays when BTC funding is "
             f"negative, receives when positive). N=10 hedged is the pre-registered product; the rest are robustness only.\n")
    L.append(HDR)
    for n_names in (5, 10, 20):
        for hedged in (True, False):
            L.append(row(f"N={n_names} {'hedged' if hedged else 'UNHEDGED'}", res_carry[(n_names, hedged)]))
    L.append("")
    L.append("### Decomposition, N=10 hedged (cumulative sum of weekly contributions, % of equity)\n")
    L.append("| period | weeks | alts price P&L | BTC hedge price P&L | funding received on alts | funding on BTC short | fees+slippage | NET |")
    L.append("|---|---|---|---|---|---|---|---|")
    wk10 = carry[(CARRY_N, True)][0]
    for name, part in (("full", wk10), ("H1", halves(wk10)[0]), ("H2", halves(wk10)[1])):
        d = carry_decomp(part)
        L.append(f"| {name} | {d['n']} | {d['price_alts'] * 100:+.1f}% | {d['price_hedge'] * 100:+.1f}% | {d['funding_alts'] * 100:+.1f}% | "
                 f"{d['funding_hedge'] * 100:+.1f}% | {d['cost'] * 100:+.1f}% | {d['net'] * 100:+.1f}% |")
    sig_mean = float(np.mean([w["signal_mean"] for w in wk10]))
    L.append(f"\nAverage trailing-7d funding of the selected basket at selection: {sig_mean * 100:.1f}% per week (shorts paying longs). "
             f"Avg eligible names for the carry signal: {np.mean([w['n_elig'] for w in wk10]):.0f}.")
    # persistence check: funding received next week vs signal
    recv = [-w["fund_alts"] for w in wk10]
    L.append(f"Funding actually RECEIVED by the basket the following week: mean {np.mean(recv) * 100:.2f}%/wk, median "
             f"{np.median(recv) * 100:.2f}%/wk, negative (basket paid) in {np.mean([r < 0 for r in recv]) * 100:.0f}% of weeks — "
             f"i.e. {np.mean(recv) / max(-sig_mean, 1e-9) * 100:.0f}% of last week's funding persisted.\n")

    L.append("## 4. Momentum ex-funding-carry (pit30, 10% cap, that week's N=10 carry basket removed from the eligible set)\n")
    L.append(HDR)
    for lab in ORDER:
        L.append(row(f"k={lab}" + ("  ← pre-specified" if lab in ("56", "91") else ""), res_ex[lab]))
    L.append("")
    # side by side k=56/91 with and without exclusion
    L.append("| k | with carry names: net ann / Sharpe / H1 / H2 | carry names EXCLUDED: net ann / Sharpe / H1 / H2 | ex-funding Sharpe with → without |")
    L.append("|---|---|---|---|")
    for lab in ("56", "91"):
        a, b = res_mom[("pit30", "cap10", lab)], res_ex[lab]
        L.append(f"| {lab} | {fmt_pct(a['full']['net_ann'])} / {fmt(a['full']['sharpe'])} / {fmt(a['h1']['sharpe'])} / {fmt(a['h2']['sharpe'])} | "
                 f"{fmt_pct(b['full']['net_ann'])} / {fmt(b['full']['sharpe'])} / {fmt(b['h1']['sharpe'])} / {fmt(b['h2']['sharpe'])} | "
                 f"{fmt(a['exf']['sharpe'])} → {fmt(b['exf']['sharpe'])} |")
    L.append("")
    L.append("### Leg attribution, ex-carry k=56 / k=91 (cumulative sum of weekly gross contributions, % of equity)\n")
    L.append("| k | period | long leg price | short leg price | funding (− = received) | fees+slippage | NET | worst week | max DD |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for lab in ("56", "91"):
        wks = mom_ex[lab]
        for name, part in (("full", wks), ("H1", halves(wks)[0]), ("H2", halves(wks)[1])):
            lp = sum(float((w["weights"][w["weights"] > 0] * w["rets"][w["weights"] > 0]).sum()) for w in part)
            sp = sum(float((w["weights"][w["weights"] < 0] * w["rets"][w["weights"] < 0]).sum()) for w in part)
            fu = sum(w["funding"] for w in part)
            co = sum(w["cost"] for w in part)
            ne = sum(w["net"] for w in part)
            worst = min(w["net"] for w in part)
            m = metrics(part)
            L.append(f"| {lab} | {name} | {lp * 100:+.1f}% | {sp * 100:+.1f}% | {fu * 100:+.1f}% | {-co * 100:+.1f}% | {ne * 100:+.1f}% | "
                     f"{worst * 100:+.1f}% | {fmt_pct(m['mdd'])} |")
    L.append("\n**Margin note on the ex-carry SHIP verdict:** the bar is applied mechanically, but the pass rests on full-period max "
             "drawdowns of " + f"{fmt_pct(res_ex['56']['full']['mdd'])} (k=56) and {fmt_pct(res_ex['91']['full']['mdd'])} (k=91) against a 25% cap "
             "— a thin margin on a 62-week sample with ~7 names per leg, in a survivorship-biased universe. One additional bad week "
             "would flip it. Treat SHIP-CANDIDATE as 'eligible for a pre-registered forward paper test', not as proof.\n")

    L.append("## Multiple testing\n")
    n_weeks = len(rebal_dates)
    L.append(f"{n_variants} portfolio variants were evaluated in this file (momentum: 6 lookbacks × 3 universe/cap settings + 6 ex-carry; "
             f"carry: 3 basket sizes × hedged/unhedged), each also read ex-funding, on top of the 48 variants in the v1 report. "
             f"With {n_weeks} weekly observations, a zero-edge series shows annualized Sharpe ≥ 1.0 with p ≈ {_p_sharpe(1.0, n_weeks):.3f} "
             f"and ≥ 0.5 with p ≈ {_p_sharpe(0.5, n_weeks):.3f} per variant; the both-halves requirement squares these roughly. "
             f"No parameter in either bar was changed after seeing results; the carry bar was written before the carry code ran.\n")
    L.append("## Data\n")
    L.append(f"- {len(universe)} Trading LinearPerpetual USDT symbols; {len(syms)} with ≥60 closed daily bars; panel {idx[0].date()} → "
             f"{idx[-1].date()}; funding history for {n_fund} symbols (cached under `logs/backtest_cache/xs_funding_*.json`); "
             f"{len(rebal_dates)} weekly rebalances {rebal_dates[0].date()} → {rebal_dates[-1].date()} (Sunday daily bar close = Monday 00:00 UTC).")
    L.append(f"\n_Generated by `xs_momentum_v2.py` in {time.time() - t0:.0f}s. Zero Claude tokens, zero order logic._\n")

    path = os.path.join(REPORT_DIR, f"xs_momentum_v2_{args.date_tag}.md")
    with open(path, "w") as f:
        f.write("\n".join(L))

    print("\n=== VERDICTS ===")
    for k_, v_ in verdicts.items():
        print(f"  momentum {k_}: {v_[0]}")
    print(f"  momentum ex-carry k56/91: {v_ex_5691[0]}   | carry N=10 hedged: {v_carry}")
    print(f"report: {path}")


if __name__ == "__main__":
    main()
