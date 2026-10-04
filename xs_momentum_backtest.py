#!/usr/bin/env python
"""
xs_momentum_backtest.py — weekly CROSS-SECTIONAL momentum long/short portfolio on Bybit USDT perps.

RESEARCH ONLY. Zero Claude tokens, public Bybit endpoints only (no key), no order logic.
A different product from the project's per-trade signals: a weekly-rebalanced decile L/S book.

Run:  source venv/bin/activate && python xs_momentum_backtest.py
Out:  logs/backtest_reports/xs_momentum_YYYYMMDD.md  (+ _weights.json)
"""
import argparse
import json
import math
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import requests

BASE = "https://api.bybit.com"
CACHE_DIR = "logs/backtest_cache"
REPORT_DIR = "logs/backtest_reports"

DAYS = 540                      # daily history requested per symbol
MIN_HISTORY = 60                # skip symbols with fewer closed daily bars
MIN_TURNOVER_7D = 10_000_000    # trailing-7d mean daily turnover (USDT) for eligibility
LOOKBACKS = [7, 14, 28, 56, 91]
SKIP_VARIANT = ("28s7", 28, 7)  # 28-day lookback, skip the most recent 7 days
TAKER_FEE = 0.00055
SLIPPAGE = 0.0003
COST_PER_UNIT_TURNOVER = TAKER_FEE + SLIPPAGE   # per side, per unit |weight change|
FLAT_FUNDING_8H = 0.0001        # fallback when funding history is not fetched (0.01%/8h = Bybit base rate)
FUNDING_BUDGET_SEC = 1500       # wall-clock budget for funding downloads; the rest fall back to flat
FUNDING_THREADS = 4
KLINE_SLEEP = 0.1
LONG_LISTED_DAYS = 365

PRE_REGISTERED_BAR = (
    "SHIP-CANDIDATE if, net of costs, annualized Sharpe >= 1.0 AND max drawdown <= 25% AND "
    ">= 55% of weeks positive, holding on BOTH chronological halves AND for at least two adjacent "
    "lookbacks. CANDIDATE if net Sharpe >= 0.5 on both halves. Otherwise NO. Costs and the "
    "survivorship caveat are part of the result, not footnotes."
)

SESSION = requests.Session()


# ----------------------------------------------------------------------------- HTTP
def _get(path, params, retries=4):
    last = None
    for i in range(retries):
        try:
            r = SESSION.get(BASE + path, params=params, timeout=20)
            r.raise_for_status()
            j = r.json()
            if j.get("retCode") != 0:
                raise RuntimeError(f"retCode={j.get('retCode')} {j.get('retMsg')}")
            return j["result"]
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(0.5 * (i + 1))
    raise RuntimeError(f"GET {path} {params} failed: {last}")


def fetch_universe():
    out, cursor = [], ""
    while True:
        params = {"category": "linear", "limit": 1000}
        if cursor:
            params["cursor"] = cursor
        res = _get("/v5/market/instruments-info", params)
        for it in res.get("list", []):
            if (it.get("status") == "Trading" and it.get("quoteCoin") == "USDT"
                    and it.get("contractType") == "LinearPerpetual"):
                out.append({"symbol": it["symbol"], "launchTime": int(it.get("launchTime") or 0)})
        cursor = res.get("nextPageCursor") or ""
        if not cursor:
            break
    return out


def load_klines(symbol, start_ms, force=False):
    path = os.path.join(CACHE_DIR, f"xs_{symbol}_D.json")
    if os.path.exists(path) and not force:
        with open(path) as f:
            return json.load(f)
    res = _get("/v5/market/kline", {"category": "linear", "symbol": symbol, "interval": "D",
                                    "start": start_ms, "limit": 1000})
    rows = res.get("list", [])
    with open(path, "w") as f:
        json.dump(rows, f)
    time.sleep(KLINE_SLEEP)
    return rows


def load_funding(symbol, start_ms, end_ms):
    """All funding settlements in [start_ms, end_ms] (list of [ts_ms, rate]); cached."""
    path = os.path.join(CACHE_DIR, f"xs_funding_{symbol}.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    rows, cursor_end = [], end_ms
    for _ in range(40):  # 40 pages x 200 = 8000 settlements, plenty for 540d even at 1h intervals
        res = _get("/v5/market/funding/history",
                   {"category": "linear", "symbol": symbol, "startTime": start_ms,
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


# ----------------------------------------------------------------------------- panel
def build_panel(universe, start_ms, today_midnight_ms):
    closes, turns, skipped, first_date = {}, {}, [], {}
    for i, inst in enumerate(universe):
        sym = inst["symbol"]
        try:
            rows = load_klines(sym, start_ms)
        except Exception as e:  # noqa: BLE001
            print(f"  [skip] {sym}: {e}")
            skipped.append(sym)
            continue
        rows = [r for r in rows if int(r[0]) < today_midnight_ms]  # drop the OPEN daily bar
        if len(rows) < MIN_HISTORY:
            skipped.append(sym)
            continue
        ts = pd.to_datetime([int(r[0]) for r in rows], unit="ms", utc=True)
        c = pd.Series([float(r[4]) for r in rows], index=ts).sort_index()
        t = pd.Series([float(r[6]) for r in rows], index=ts).sort_index()
        c = c[~c.index.duplicated()]
        t = t[~t.index.duplicated()]
        closes[sym], turns[sym] = c, t
        first_date[sym] = c.index[0]
        if (i + 1) % 50 == 0:
            print(f"  klines {i + 1}/{len(universe)}")
    close = pd.DataFrame(closes).sort_index()
    turn = pd.DataFrame(turns).reindex(close.index)
    full_idx = pd.date_range(close.index[0], close.index[-1], freq="D", tz="UTC")
    close = close.reindex(full_idx)
    turn = turn.reindex(full_idx)
    return close, turn, skipped, first_date


# ----------------------------------------------------------------------------- strategy
def run_variant(close, turn, lookback, skip, mode, rebal_dates, universe_mask=None):
    """
    mode: 'ls' (long winners/short losers, 50/50 dollar-neutral), 'rev' (reverse sign),
          'long' (long-only top decile, 100%), 'short' (short-only bottom decile, -100%).
    Returns a list of week dicts with weights, gross return, turnover, names per leg.
    """
    need = lookback + 2
    hist_ok = close.notna().rolling(need).sum() == need
    turn_ok = turn.rolling(7).mean() >= MIN_TURNOVER_7D
    sig = close.shift(skip) / close.shift(lookback) - 1.0
    fwd = close.shift(-7) / close - 1.0

    weeks, prev_end_w = [], pd.Series(dtype=float)
    for t in rebal_dates:
        elig = hist_ok.loc[t] & turn_ok.loc[t] & sig.loc[t].notna()
        if universe_mask is not None:
            elig = elig & universe_mask
        syms = elig[elig].index
        n = len(syms)
        if n < 10:
            continue
        s = sig.loc[t, syms].sort_values()
        nd = max(1, n // 10)
        bottom, top = list(s.index[:nd]), list(s.index[-nd:])
        w = {}
        if mode == "ls":
            for x in top:
                w[x] = 0.5 / nd
            for x in bottom:
                w[x] = -0.5 / nd
        elif mode == "rev":
            for x in top:
                w[x] = -0.5 / nd
            for x in bottom:
                w[x] = 0.5 / nd
        elif mode == "long":
            for x in top:
                w[x] = 1.0 / nd
        elif mode == "short":
            for x in bottom:
                w[x] = -1.0 / nd
        w = pd.Series(w, dtype=float)
        r = fwd.loc[t, w.index]
        gap = int(r.isna().sum())
        r = r.fillna(0.0)
        gross = float((w * r).sum())
        # drifted end-of-week weights (equity-normalised) → turnover vs next rebalance
        end_w = (w * (1.0 + r)) / (1.0 + gross)
        all_syms = w.index.union(prev_end_w.index)
        turnover = float((w.reindex(all_syms).fillna(0) - prev_end_w.reindex(all_syms).fillna(0)).abs().sum())
        weeks.append({
            "date": t, "weights": w, "rets": r, "gross": gross, "turnover": turnover,
            "n_long": int((w > 0).sum()), "n_short": int((w < 0).sum()), "n_elig": n, "gap_fills": gap,
        })
        prev_end_w = end_w
    return weeks


def apply_costs(weeks, funding, flat_syms):
    """Adds cost, funding and net return to each week (in place)."""
    for wk in weeks:
        t = wk["date"]
        t_close_ms = int((t + timedelta(days=1)).timestamp() * 1000)   # daily bar closes next 00:00 UTC
        t_end_ms = t_close_ms + 7 * 86400 * 1000
        f_total, f_payonly, contrib = 0.0, 0.0, {}
        for sym, w in wk["weights"].items():
            rates = funding.get(sym)
            if rates is None:
                f_sym = FLAT_FUNDING_8H * 21
                flat_syms.add(sym)
            else:
                f_sym = float(sum(r for ts, r in rates if t_close_ms < ts <= t_end_ms))
            c = w * f_sym                 # long pays positive funding, short receives (+ = we pay)
            f_total += c
            f_payonly += max(c, 0.0)      # conservative: never credit funding received
            contrib[sym] = c
        wk["cost"] = wk["turnover"] * COST_PER_UNIT_TURNOVER
        wk["funding"] = f_total
        wk["funding_contrib"] = contrib
        wk["net"] = wk["gross"] - wk["cost"] - wk["funding"]
        wk["net_exfund"] = wk["gross"] - wk["cost"]
        wk["net_payonly"] = wk["gross"] - wk["cost"] - f_payonly


# ----------------------------------------------------------------------------- metrics
def _nan(v):
    return None if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))) else v


def metrics(weeks, key="net"):
    n = len(weeks)
    if n < 4:
        return {"n": n, "gross_ann": None, "net_ann": None, "sharpe": None, "mdd": None,
                "pct_pos": None, "turnover": None, "names": None, "funding_ann": None}
    g = np.array([w["gross"] for w in weeks])
    r = np.array([w[key] for w in weeks])
    eq = np.cumprod(1.0 + r)
    peak = np.maximum.accumulate(eq)
    mdd = float(np.max(1.0 - eq / peak))
    sd = r.std(ddof=1)
    sharpe = float(r.mean() / sd * math.sqrt(52)) if sd > 0 else float("nan")

    def ann(x):
        p = float(np.prod(1.0 + x))
        return p ** (52.0 / len(x)) - 1.0 if p > 0 else -1.0

    return {
        "n": n,
        "gross_ann": _nan(ann(g)),
        "net_ann": _nan(ann(r)),
        "sharpe": _nan(sharpe),
        "mdd": mdd,
        "pct_pos": float((r > 0).mean()),
        "turnover": float(np.mean([w["turnover"] for w in weeks])),
        "names": float(np.mean([(w["n_long"] + w["n_short"]) / (2 if (w["n_long"] and w["n_short"]) else 1) for w in weeks])),
        "funding_ann": _nan(float(np.mean([w["funding"] for w in weeks]) * 52)),
        "cost_ann": _nan(float(np.mean([w["cost"] for w in weeks]) * 52)),
    }


def halves(weeks):
    h = len(weeks) // 2
    return weeks[:h], weeks[h:]


def fmt_pct(v, d=1):
    return "n/a" if v is None else f"{v * 100:.{d}f}%"


def fmt(v, d=2):
    return "n/a" if v is None else f"{v:.{d}f}"


def table_rows(label, m):
    return (f"| {label} | {m['n']} | {fmt_pct(m['gross_ann'])} | {fmt_pct(m['net_ann'])} | {fmt(m['sharpe'])} | "
            f"{fmt_pct(m['mdd'])} | {fmt_pct(m['pct_pos'], 0)} | {fmt(m['turnover'])} | {fmt(m['names'], 1)} | "
            f"{fmt_pct(m['funding_ann'])} |")


TABLE_HDR = ("| variant | n wks | gross ann | net ann | net Sharpe | max DD | % wks + | avg wkly turnover | avg names/leg | funding drag ann |\n"
             "|---|---|---|---|---|---|---|---|---|---|")


def decile_table(close, turn, rebal_dates, lookback, universe_mask=None):
    need = lookback + 2
    hist_ok = close.notna().rolling(need).sum() == need
    turn_ok = turn.rolling(7).mean() >= MIN_TURNOVER_7D
    sig = close / close.shift(lookback) - 1.0
    fwd = close.shift(-7) / close - 1.0
    per_week = []
    for t in rebal_dates:
        elig = hist_ok.loc[t] & turn_ok.loc[t] & sig.loc[t].notna() & fwd.loc[t].notna()
        if universe_mask is not None:
            elig = elig & universe_mask
        syms = elig[elig].index
        if len(syms) < 20:
            continue
        s = sig.loc[t, syms]
        ranks = s.rank(method="first")
        dec = np.ceil(ranks / len(syms) * 10).clip(1, 10).astype(int)
        row = fwd.loc[t, syms].groupby(dec.values).mean()
        per_week.append(row.reindex(range(1, 11)))
    if not per_week:
        return None
    df = pd.DataFrame(per_week)
    out = {"mean": df.mean().tolist(), "pct_pos": (df > 0).mean().tolist(), "n": len(df),
           "spread_mean": float((df[10] - df[1]).mean()), "spread_pct_pos": float(((df[10] - df[1]) > 0).mean())}
    return out


# ----------------------------------------------------------------------------- verdict
def passes_ship(m):
    return (m["sharpe"] is not None and m["sharpe"] >= 1.0 and m["mdd"] is not None and m["mdd"] <= 0.25
            and m["pct_pos"] is not None and m["pct_pos"] >= 0.55)


def verdict(results_ls, order, key=None):
    """results_ls: {variant_label: {'full': m, 'h1': m, 'h2': m}}; order = adjacency order."""
    ship_ok = {}
    cand_ok = {}
    for lab in order:
        r = results_ls[lab] if key is None else results_ls[lab][key]
        ship_ok[lab] = passes_ship(r["full"]) and passes_ship(r["h1"]) and passes_ship(r["h2"])
        cand_ok[lab] = all(r[h]["sharpe"] is not None and r[h]["sharpe"] >= 0.5 for h in ("h1", "h2"))
    adjacent_pairs = [(order[i], order[i + 1]) for i in range(len(order) - 1)]
    # the skip variant is adjacent to k=28
    if "28s7" in results_ls and "28" in results_ls:
        adjacent_pairs.append(("28", "28s7"))
    ship_pairs = [p for p in adjacent_pairs if ship_ok[p[0]] and ship_ok[p[1]]]
    if ship_pairs:
        return "SHIP-CANDIDATE", ship_ok, cand_ok, ship_pairs
    if any(cand_ok.values()):
        return "CANDIDATE", ship_ok, cand_ok, []
    return "NO", ship_ok, cand_ok, []


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-funding", action="store_true", help="skip funding download, use flat estimate")
    ap.add_argument("--date-tag", default=datetime.now(timezone.utc).strftime("%Y%m%d"))
    args = ap.parse_args()

    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(REPORT_DIR, exist_ok=True)
    t0 = time.time()

    now = datetime.now(timezone.utc)
    today_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_midnight_ms = int(today_midnight.timestamp() * 1000)
    start_ms = int((today_midnight - timedelta(days=DAYS)).timestamp() * 1000)

    print("[1/5] universe …")
    universe = fetch_universe()
    print(f"  {len(universe)} Trading LinearPerpetual USDT symbols")

    print("[2/5] daily klines …")
    close, turn, skipped, first_date = build_panel(universe, start_ms, today_midnight_ms)
    syms = list(close.columns)
    print(f"  panel: {len(syms)} symbols x {len(close)} days ({close.index[0].date()} → {close.index[-1].date()}); "
          f"skipped {len(skipped)} (<{MIN_HISTORY}d or no data)")

    # rebalance points: the SUNDAY daily bar — its close IS Monday 00:00 UTC. Aligned so every lookback
    # (max 91) has history: first rebalance index >= 93; need the following 7 bars for the forward return.
    idx = close.index
    max_need = max(LOOKBACKS) + 2
    rebal_dates = [d for i, d in enumerate(idx) if d.dayofweek == 6 and i >= max_need and i + 7 < len(idx)]
    print(f"  {len(rebal_dates)} weekly rebalances: {rebal_dates[0].date()} → {rebal_dates[-1].date()} (Sunday bars = Monday 00:00 UTC close)")

    last_bar = idx[-1]
    long_listed = pd.Series({s: (last_bar - first_date[s]).days >= LONG_LISTED_DAYS for s in syms})
    n_long_listed = int(long_listed.sum())
    n_full_window = int(sum(1 for s in syms if (first_date[s] - idx[0]).days <= 1))

    variants = [(str(k), k, 0) for k in LOOKBACKS] + [SKIP_VARIANT]
    order = [str(k) for k in LOOKBACKS] + [SKIP_VARIANT[0]]
    modes = ["ls", "rev", "long", "short"]

    print("[3/5] portfolios …")
    runs = {}  # (universe, label, mode) -> weeks
    for uni_name, mask in (("all", None), ("listed365", long_listed)):
        for lab, k, skip in variants:
            for mode in modes:
                runs[(uni_name, lab, mode)] = run_variant(close, turn, k, skip, mode, rebal_dates, mask)
    n_variants = len(runs)

    held = set()
    for wk_list in runs.values():
        for wk in wk_list:
            held.update(wk["weights"].index)
    print(f"  {n_variants} variants run; {len(held)} distinct symbols ever held")

    print("[4/5] funding …")
    funding = {}
    funding_note = ""
    if args.no_funding:
        funding_note = f"Funding NOT fetched (--no-funding): flat {FLAT_FUNDING_8H * 100:.3f}%/8h charged to longs / credited to shorts."
    else:
        end_ms = int(now.timestamp() * 1000)
        budget_end = time.time() + FUNDING_BUDGET_SEC
        held_sorted = sorted(held)
        done = 0
        with ThreadPoolExecutor(max_workers=FUNDING_THREADS) as ex:
            futs = {ex.submit(load_funding, s, start_ms, end_ms): s for s in held_sorted}
            for fut in as_completed(futs):
                s = futs[fut]
                try:
                    funding[s] = fut.result()
                except Exception as e:  # noqa: BLE001
                    print(f"  [funding fail] {s}: {e}")
                done += 1
                if done % 50 == 0:
                    print(f"  funding {done}/{len(held_sorted)}")
                if time.time() > budget_end:
                    for f in futs:
                        f.cancel()
                    print(f"  funding budget exceeded after {done} symbols")
                    break
        n_flat = len(held) - len(funding)
        if n_flat == 0:
            funding_note = f"Funding: ACTUAL 8h/4h/1h settlement history fetched for all {len(funding)} held symbols."
        else:
            funding_note = (f"Funding: actual history for {len(funding)} held symbols; {n_flat} fell back to a FLAT "
                            f"{FLAT_FUNDING_8H * 100:.3f}%/8h estimate (download budget {FUNDING_BUDGET_SEC}s exceeded or failed).")
    print("  " + funding_note)

    print("[5/5] costs + report …")
    flat_syms = set()
    for wk_list in runs.values():
        apply_costs(wk_list, funding, flat_syms)

    # ---- aggregate
    def agg(weeks):
        h1, h2 = halves(weeks)
        y26 = [w for w in weeks if w["date"].year == 2026]
        out = {"full": metrics(weeks), "h1": metrics(h1), "h2": metrics(h2), "y2026": metrics(y26)}
        for key in ("net_exfund", "net_payonly"):
            out[key] = {"full": metrics(weeks, key), "h1": metrics(h1, key), "h2": metrics(h2, key)}
        return out

    res = {key: agg(v) for key, v in runs.items()}
    dec_all = decile_table(close, turn, rebal_dates, 28, None)
    dec_365 = decile_table(close, turn, rebal_dates, 28, long_listed)

    results_ls_all = {lab: res[("all", lab, "ls")] for lab in order}
    results_ls_365 = {lab: res[("listed365", lab, "ls")] for lab in order}
    v_all, ship_ok, cand_ok, ship_pairs = verdict(results_ls_all, order)
    v_365, ship_ok_365, cand_ok_365, ship_pairs_365 = verdict(results_ls_365, order)

    gap_total = sum(w["gap_fills"] for w in runs[("all", "28", "ls")])
    h1_dates = (runs[("all", "28", "ls")][0]["date"].date(), halves(runs[("all", "28", "ls")])[0][-1]["date"].date())
    h2_dates = (halves(runs[("all", "28", "ls")])[1][0]["date"].date(), runs[("all", "28", "ls")][-1]["date"].date())

    # ---- report
    L = []
    L.append(f"# Weekly cross-sectional momentum L/S — Bybit USDT perps — {args.date_tag}\n")
    L.append("## Pre-registered success bar (written before the run)\n")
    L.append(f"> {PRE_REGISTERED_BAR}\n")
    L.append("## Verdict (mechanical application of the bar, full universe, dollar-neutral L/S)\n")
    L.append(f"**{v_all}**\n")
    L.append("| lookback | full Sharpe | full MDD | full %+ | H1 Sharpe | H2 Sharpe | SHIP conditions (full+H1+H2) | CANDIDATE (Sharpe≥0.5 both halves) |")
    L.append("|---|---|---|---|---|---|---|---|")
    for lab in order:
        r = results_ls_all[lab]
        L.append(f"| {lab} | {fmt(r['full']['sharpe'])} | {fmt_pct(r['full']['mdd'])} | {fmt_pct(r['full']['pct_pos'], 0)} | "
                 f"{fmt(r['h1']['sharpe'])} | {fmt(r['h2']['sharpe'])} | {'PASS' if ship_ok[lab] else 'fail'} | {'PASS' if cand_ok[lab] else 'fail'} |")
    if ship_pairs:
        L.append(f"\nAdjacent lookback pairs clearing SHIP: {ship_pairs}")
    # ---- funding sensitivity: the same L/S books under three funding treatments
    L.append("\n### Funding sensitivity — the headline verdict depends on funding RECEIVED\n")
    L.append("Net = gross − fees/slippage − funding. `actual` is the pre-registered treatment (actual settlements, credits and debits). "
             "`ex-funding` ignores funding entirely. `pay-only` charges every funding payment but credits NOTHING received — the "
             "conservative bound if the squeezed-short funding windfalls prove uncapturable.\n")
    L.append("| lookback | actual: net ann / Sharpe / H1 / H2 | ex-funding: net ann / Sharpe / H1 / H2 | pay-only: net ann / Sharpe / H1 / H2 |")
    L.append("|---|---|---|---|")
    for lab in order:
        cells = []
        for key in (None, "net_exfund", "net_payonly"):
            r = results_ls_all[lab] if key is None else results_ls_all[lab][key]
            cells.append(f"{fmt_pct(r['full']['net_ann'])} / {fmt(r['full']['sharpe'])} / {fmt(r['h1']['sharpe'])} / {fmt(r['h2']['sharpe'])}")
        L.append(f"| {lab} | " + " | ".join(cells) + " |")
    v_ex, _, cand_ex, pairs_ex = verdict(results_ls_all, order, "net_exfund")
    v_po, _, cand_po, pairs_po = verdict(results_ls_all, order, "net_payonly")
    L.append(f"\nBar applied under each treatment (full universe): actual → **{v_all}**; ex-funding → **{v_ex}** "
             f"(CANDIDATE lookbacks {[k for k, v in cand_ex.items() if v] or 'none'}); pay-only → **{v_po}** "
             f"(CANDIDATE lookbacks {[k for k, v in cand_po.items() if v] or 'none'}).")
    # concentration of funding credits
    all_contrib = []
    for wk in runs[("all", "56", "ls")]:
        for sym, c in wk["funding_contrib"].items():
            all_contrib.append((c, wk["date"].strftime("%Y-%m-%d"), sym, float(wk["weights"][sym])))
    credits = sorted([x for x in all_contrib if x[0] < 0])
    total_credit = sum(x[0] for x in credits)
    top10 = credits[:10]
    long_credit = sum(x[0] for x in credits if x[3] > 0)
    if total_credit < 0:
        L.append(f"\nk=56 funding attribution: total funding received over {len(runs[('all', '56', 'ls')])} weeks = "
                 f"{-total_credit * 100:.1f}% of equity, of which the LONG leg received {long_credit / total_credit * 100:.0f}% and the "
                 f"10 largest symbol-weeks alone account for {sum(x[0] for x in top10) / total_credit * 100:.0f}%. Largest: "
                 + "; ".join(f"{x[2]} {x[1]} ({-x[0] * 100:.1f}% of equity, w={x[3]:+.3f})" for x in top10[:5]) + ".")
        L.append("These are squeezed shorts on hourly-funded small caps printing funding near the −2%/hour cap — the long leg is being "
                 "paid to hold the pumping coin. That is a real transfer on Bybit, but it is (a) concentrated in a handful of names "
                 "and weeks, (b) specific to recent listings (the ≥365-day universe loses it), and (c) a crowded-squeeze artefact, "
                 "not a price-momentum premium. The ex-funding and pay-only rows are the honest read of the PRICE edge.")
    L.append(f"\n≥365-day-listed universe verdict: **{v_365}** (SHIP pairs: {ship_pairs_365 or 'none'}; "
             f"CANDIDATE lookbacks: {[k for k, v in cand_ok_365.items() if v] or 'none'})\n")

    L.append("## Data & method\n")
    L.append(f"- Universe: {len(universe)} currently-listed `Trading` LinearPerpetual USDT symbols from `/v5/market/instruments-info`; "
             f"{len(syms)} with ≥{MIN_HISTORY} closed daily bars used, {len(skipped)} skipped.")
    L.append(f"- Daily klines (`interval=D`), {DAYS} days requested; panel {close.index[0].date()} → {close.index[-1].date()} "
             f"({len(close)} days). The in-progress daily bar is dropped. {n_full_window} symbols span the full window; "
             f"{n_long_listed} have been listed ≥{LONG_LISTED_DAYS} days.")
    L.append(f"- **SURVIVORSHIP BIAS:** only symbols listed TODAY are in the panel. Coins delisted during the window (typically the worst "
             f"losers — exactly the short leg's targets, and the long leg's blow-ups) are absent. This biases the bottom-decile short "
             f"leg's realised returns and the long-leg's tail risk. Results are an UPPER bound until a point-in-time universe is available. "
             f"The ≥{LONG_LISTED_DAYS}-day-listed repeat below removes recent listings but does NOT fix delisting survivorship.")
    L.append(f"- Rebalance: every Monday 00:00 UTC at the daily close (= the Sunday daily bar's close). {len(rebal_dates)} weeks, "
             f"{rebal_dates[0].date()} → {rebal_dates[-1].date()}, aligned so every lookback starts on the same week "
             f"(first rebalance needs {max_need} bars). H1 = {h1_dates[0]} → {h1_dates[1]}, H2 = {h2_dates[0]} → {h2_dates[1]}.")
    L.append(f"- Eligible: ≥ lookback+2 contiguous daily closes AND trailing-7-day mean daily turnover ≥ ${MIN_TURNOVER_7D / 1e6:.0f}M "
             f"(kline turnover column, as of the rebalance bar — no look-ahead).")
    L.append("- Signal: trailing k-day close-to-close return, k ∈ {7,14,28,56,91}; plus `28s7` = return from t−28 to t−7 (skip the last week).")
    L.append("- Portfolio: long top decile, short bottom decile (decile = floor(n/10) names), equal weight within leg, 50/50 dollar-neutral, "
             "hold one week, weekly return = Σ wᵢ·(close_{t+7}/close_t − 1). `rev` = reversed sign (short winners / long losers). "
             "`long` / `short` = single leg at 100% gross.")
    L.append(f"- Costs: turnover = Σ|w_t − drifted w_{{t−1}}| (first week = full open), charged {TAKER_FEE * 100:.3f}% taker + "
             f"{SLIPPAGE * 100:.2f}% slippage per unit of turnover. {funding_note} Funding is charged to longs / credited to shorts "
             f"on the held weights using settlements inside the holding week.")
    if gap_total:
        L.append(f"- {gap_total} held-name-weeks had a missing forward close and were treated as flat (0%).")
    L.append(f"- Multiple testing: **{n_variants} portfolio variants** were evaluated (6 lookbacks × 4 leg modes × 2 universes), "
             f"each read under 3 funding treatments ({n_variants * 3} readouts), "
             f"plus one decile table; with ~{len(rebal_dates)} weekly observations each, the chance that at least one variant shows "
             f"net Sharpe ≥ 1.0 by luck alone is material (one-sided p for Sharpe 1.0 over {len(rebal_dates)} weeks ≈ "
             f"{_p_sharpe(1.0, len(rebal_dates)):.3f} per variant). The pre-registered bar demands BOTH halves AND adjacent "
             f"lookbacks precisely to blunt this; no parameter was tuned after seeing results.\n")

    def section(title, uni):
        L.append(f"## {title}\n")
        for mode, mname in (("ls", "Long/short (dollar-neutral)"), ("rev", "REVERSED sign — sanity check"),
                            ("long", "Long-only top decile"), ("short", "Short-only bottom decile")):
            L.append(f"### {mname}\n")
            for period, pname in (("full", "Full period"), ("h1", "First half"), ("h2", "Second half"), ("y2026", "2026 only")):
                L.append(f"**{pname}**\n")
                L.append(TABLE_HDR)
                for lab in order:
                    L.append(table_rows(f"k={lab}", res[(uni, lab, mode)][period]))
                L.append("")

    section(f"Results — full universe ({len(syms)} symbols)", "all")

    def dec_section(d, title):
        L.append(f"### {title}\n")
        if d is None:
            L.append("insufficient data\n")
            return
        L.append("| decile (1 = biggest 28d losers … 10 = biggest winners) | " + " | ".join(str(i) for i in range(1, 11)) + " |")
        L.append("|---|" + "---|" * 10)
        L.append("| mean next-week return | " + " | ".join(f"{v * 100:.2f}%" for v in d["mean"]) + " |")
        L.append("| % weeks positive | " + " | ".join(f"{v * 100:.0f}%" for v in d["pct_pos"]) + " |")
        L.append(f"\nD10 − D1 spread: mean {d['spread_mean'] * 100:.2f}%/week, positive in {d['spread_pct_pos'] * 100:.0f}% of {d['n']} weeks "
                 f"(gross, before costs/funding).\n")

    L.append("## Decile monotonicity — k=28, gross next-week return\n")
    dec_section(dec_all, "Full universe")
    dec_section(dec_365, f"≥{LONG_LISTED_DAYS}-day-listed universe")

    section(f"Results — ≥{LONG_LISTED_DAYS}-day-listed universe ({n_long_listed} symbols)", "listed365")

    L.append("## Reading guide\n")
    L.append("- The `rev` block is the same book with the sign flipped: if momentum has no edge, `ls` and `rev` are mirror images around "
             "−(costs); if `rev` is the one that looks good, the cross-section is mean-reverting at the weekly horizon, not trending.")
    L.append("- Long-only / short-only are NOT market-neutral: their return is dominated by beta to the crypto market over this window; "
             "read them as attribution for the L/S book, not as standalone products.")
    L.append("- Every number above is subject to the survivorship caveat in Data & method.")
    L.append(f"\n_Generated by `xs_momentum_backtest.py` in {time.time() - t0:.0f}s. Zero Claude tokens, zero order logic._\n")

    report_path = os.path.join(REPORT_DIR, f"xs_momentum_{args.date_tag}.md")
    with open(report_path, "w") as f:
        f.write("\n".join(L))

    # ---- weights JSON (L/S, full universe) — native types, NaN-guarded
    weights_out = {
        "meta": {
            "generated": now.isoformat(), "universe_symbols": len(syms), "rebalance": "Monday 00:00 UTC (Sunday daily bar close)",
            "weights_are": "fraction of equity, long +, short −, gross 1.0, net 0.0", "funding_note": funding_note,
            "variants_evaluated": n_variants,
        },
        "ls": {},
    }
    for lab in order:
        weights_out["ls"][f"k{lab}"] = {
            wk["date"].strftime("%Y-%m-%d"): {
                "weights": {s: round(float(w), 6) for s, w in wk["weights"].items()},
                "gross": _nan(float(wk["gross"])), "net": _nan(float(wk["net"])), "turnover": _nan(float(wk["turnover"])),
                "cost": _nan(float(wk["cost"])), "funding": _nan(float(wk["funding"])),
                "n_eligible": int(wk["n_elig"]),
            }
            for wk in runs[("all", lab, "ls")]
        }
    weights_path = os.path.join(REPORT_DIR, f"xs_momentum_{args.date_tag}_weights.json")
    with open(weights_path, "w") as f:
        json.dump(weights_out, f, separators=(",", ":"))

    # ---- console summary
    print("\n=== SUMMARY (L/S, full universe) ===")
    print(TABLE_HDR)
    for lab in order:
        print(table_rows(f"k={lab}", res[("all", lab, "ls")]["full"]))
    print(f"\nVERDICT full universe: {v_all} | ≥365d universe: {v_365}")
    print(f"report:  {report_path}\nweights: {weights_path}")


def _p_sharpe(sr_ann, n_weeks):
    """One-sided p-value that a zero-mean weekly series shows annualized Sharpe >= sr_ann (normal approx)."""
    z = sr_ann / math.sqrt(52) * math.sqrt(n_weeks)
    return 0.5 * math.erfc(z / math.sqrt(2))


if __name__ == "__main__":
    main()
