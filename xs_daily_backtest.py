#!/usr/bin/env python
"""
xs_daily_backtest.py — pre-registered study (logs/backtest_reports/prereg_xs_daily_20261020.md):
a DAILY-rebalanced cross-sectional long/short book on crypto-only Bybit perps, two judged signals:

  S1 basis_24h    long the lowest trailing-24h funding (perp at a discount), short the highest
  S2 btc_catchup  long the coins that lagged BTC's last daily move most (beta * r_BTC - r), short the most ahead

Same sizing and costs as paper test #2 (decile legs, 10%-of-leg cap, dollar-neutral, taker + slippage on
turnover, actual funding). RESEARCH ONLY (zero Claude tokens, no order logic). Reads the momentum study's
caches (no download).

Run:  source venv/bin/activate && python xs_daily_backtest.py
Out:  logs/backtest_reports/xs_daily_YYYYMMDD.md
"""
import argparse
import json
import math
import os
import re
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

import xs_momentum_backtest as v1
from xs_momentum_backtest import CACHE_DIR, REPORT_DIR, MIN_TURNOVER_7D, COST_PER_UNIT_TURNOVER, fmt, fmt_pct
from xs_momentum_v2 import FundingStore, LEG_CAP

PANEL_END = "2026-10-03"          # same last bar as xs_momentum_v2_crypto.py
TRADFI_LIST = os.path.join(REPORT_DIR, "xs_momentum_tradfi_list_20261004.json")
MIN_LISTED_DAYS = 30
MIN_ELIGIBLE = 20
BETA_DAYS = 30
BETA_MIN_PAIRS = 25
FIRST_REBALANCE_BAR = 30          # 0-based: the 31st bar of the panel
MAKER_COST = 0.0002               # context only: maker fee per unit turnover, no slippage
BASELINE_SEEDS = 20
DAY_MS = 86_400_000
BTC = "BTCUSDT"

BAR = ("SHIP-CANDIDATE if full period, H1 and H2 each have net Sharpe >= 1.0, max drawdown <= 25% and >= 55% weeks "
       "green, and full-period Sharpe > the random baseline's 95th percentile; CANDIDATE if net Sharpe >= 0.5 on both "
       "halves and full-period Sharpe > the baseline's 95th percentile; otherwise NO.")


# ----------------------------------------------------------------------------- data
def load_panel():
    syms = sorted(m.group(1) for f in os.listdir(CACHE_DIR) if (m := re.fullmatch(r"xs_(.+)_D\.json", f)))
    end_ms = int((pd.Timestamp(PANEL_END, tz="UTC") + pd.Timedelta(days=1)).timestamp() * 1000)
    close, turn, _, first = v1.build_panel([{"symbol": s} for s in syms], 0, end_ms)
    close, turn = close.loc[:PANEL_END], turn.loc[:PANEL_END]
    tl = json.load(open(TRADFI_LIST))
    tradfi = set(tl["flagged"]) | set(tl["pegged_supplement"])
    crypto = [s for s in close.columns if s not in tradfi]
    raw = {}
    for s in crypto:
        p = os.path.join(CACHE_DIR, f"xs_funding_{s}.json")
        if os.path.exists(p):
            raw[s] = json.load(open(p))
    return close[crypto], turn[crypto], pd.Series({s: first[s] for s in crypto}), FundingStore(raw), len(syms) - len(crypto)


def close_ms(t):
    return int(t.timestamp() * 1000) + DAY_MS   # bar opening at t closes at t + 1 day


def settlements(fstore, s, a_ms, b_ms):
    """(count, sum) of funding settlements with a < ts <= b; (0, None) if no file."""
    if not fstore.has(s):
        return 0, None
    t, c = fstore.ts[s], fstore.cum[s]
    i, j = np.searchsorted(t, a_ms, "right"), np.searchsorted(t, b_ms, "right")
    return int(j - i), float(c[j] - c[i])


def rolling_beta(ret, btc):
    """OLS slope of each column on BTC over the last BETA_DAYS bars, pairwise-valid, >= BETA_MIN_PAIRS pairs."""
    x = pd.DataFrame({c: btc for c in ret.columns}, index=ret.index)
    m = ret.notna() & x.notna()
    xv, yv = x.where(m, 0.0), ret.where(m, 0.0)
    roll = lambda d: d.rolling(BETA_DAYS, min_periods=1).sum()
    n, sx, sy = roll(m.astype(float)), roll(xv), roll(yv)
    sxx, sxy = roll(xv * xv), roll(xv * yv)
    den = n * sxx - sx * sx
    beta = (n * sxy - sx * sy) / den.where(den > 0)
    return beta.where(n >= BETA_MIN_PAIRS)


# ----------------------------------------------------------------------------- book
def run_book(sig_fn, days, nxt, fstore):
    """sig_fn(t) -> Series over eligible symbols (higher = long) or None. One row per rebalance day."""
    rows, prev_end = [], pd.Series(dtype=float)
    for t in days:
        sig = sig_fn(t)
        if sig is None or len(sig) < MIN_ELIGIBLE:
            w = pd.Series(dtype=float)
        else:
            s = sig.sort_values(kind="mergesort")
            nd = len(s) // 10
            per = 0.5 * min(1.0 / nd, LEG_CAP)
            w = pd.Series({**{x: per for x in s.index[-nd:]}, **{x: -per for x in s.index[:nd]}}, dtype=float)
        rets = nxt.loc[t, w.index].fillna(0.0) if len(w) else pd.Series(dtype=float)
        gross = float((w * rets).sum())
        union = w.index.union(prev_end.index)
        turnover = float((w.reindex(union).fillna(0) - prev_end.reindex(union).fillna(0)).abs().sum())
        a = close_ms(t)
        funding = 0.0
        for sym, wt in w.items():
            _, fs = settlements(fstore, sym, a, a + DAY_MS)
            funding += wt * (fs if fs is not None else v1.FLAT_FUNDING_8H * 3)
        rows.append({
            "date": t, "gross": gross, "turnover": turnover, "funding": funding,
            "net": gross - turnover * COST_PER_UNIT_TURNOVER - funding,
            "net_maker": gross - turnover * MAKER_COST - funding,
            "cost": turnover * COST_PER_UNIT_TURNOVER, "names": len(w) / 2,
            "long_gross": float((w[w > 0] * rets[w > 0]).sum()), "short_gross": float((w[w < 0] * rets[w < 0]).sum()),
        })
        prev_end = (w * (1.0 + rets)) / (1.0 + gross) if len(w) and gross > -1 else pd.Series(dtype=float)
    return rows


def metrics(rows, key="net"):
    if len(rows) < 28:
        return None
    r = np.array([x[key] for x in rows])
    g = np.array([x["gross"] for x in rows])
    eq = np.cumprod(1.0 + r)
    sd = r.std(ddof=1)
    wk = [float(np.prod(1.0 + r[i:i + 7]) - 1.0) for i in range(0, len(r) - len(r) % 7, 7)]

    def ann(x):
        p = float(np.prod(1.0 + x))
        return p ** (365.0 / len(x)) - 1.0 if p > 0 else -1.0

    return {
        "n": len(r), "gross_ann": ann(g), "net_ann": ann(r),
        "sharpe": float(r.mean() / sd * math.sqrt(365)) if sd > 0 else float("nan"),
        "mdd": float(np.max(1.0 - eq / np.maximum.accumulate(eq))),
        "pct_weeks": float(np.mean(np.array(wk) > 0)), "pct_days": float(np.mean(r > 0)),
        "turnover": float(np.mean([x["turnover"] for x in rows])),
        "names": float(np.mean([x["names"] for x in rows])),
        "funding_ann": float(np.mean([x["funding"] for x in rows]) * 365),
        "cost_ann": float(np.mean([x["cost"] for x in rows]) * 365),
        "long_cum": float(sum(x["long_gross"] for x in rows)), "short_cum": float(sum(x["short_gross"] for x in rows)),
    }


def judged(rows):
    h = len(rows) // 2
    return {"full": metrics(rows), "h1": metrics(rows[:h]), "h2": metrics(rows[h:]), "maker": metrics(rows, "net_maker")}


def verdict(res, base_p95):
    def ship(m):
        return m["sharpe"] >= 1.0 and m["mdd"] <= 0.25 and m["pct_weeks"] >= 0.55
    beats = res["full"]["sharpe"] > base_p95
    if all(ship(res[h]) for h in ("full", "h1", "h2")) and beats:
        return "SHIP-CANDIDATE"
    if all(res[h]["sharpe"] >= 0.5 for h in ("h1", "h2")) and beats:
        return "CANDIDATE"
    return "NO"


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date-tag", default=datetime.now(timezone.utc).strftime("%Y%m%d"))
    args = ap.parse_args()
    t0 = time.time()
    close, turn, first, fstore, n_tradfi = load_panel()
    idx = close.index
    days = list(idx[FIRST_REBALANCE_BAR:-1])
    turn_ok = turn.rolling(7).mean() >= MIN_TURNOVER_7D
    ret = close / close.shift(1) - 1.0
    nxt = close.shift(-1) / close - 1.0
    beta = rolling_beta(ret, ret[BTC])
    print(f"panel {len(close.columns)} crypto-only symbols ({n_tradfi} TradFi/pegged or too-short-history files excluded), "
          f"{idx[0]:%Y-%m-%d} → {idx[-1]:%Y-%m-%d}, {len(days)} rebalance days")

    def base_elig(t):
        listed = (t - first).dt.days >= MIN_LISTED_DAYS
        e = close.loc[t].notna() & turn_ok.loc[t] & listed
        return list(e[e].index)

    def s1_basis(t):
        b = close_ms(t)
        out = {}
        for s in base_elig(t):
            n, f = settlements(fstore, s, b - DAY_MS, b)
            if n >= 1:
                out[s] = -f                      # higher = long → long the lowest funding
        return pd.Series(out, dtype=float)

    def s2_catchup(t):
        rb = ret.at[t, BTC]
        if pd.isna(rb):
            return None
        e = [s for s in base_elig(t) if s != BTC]
        sig = beta.loc[t, e] * rb - ret.loc[t, e]
        return sig.dropna()

    books = {"basis_24h": s1_basis, "btc_catchup": s2_catchup}
    rows = {k: run_book(f, days, nxt, fstore) for k, f in books.items()}
    res = {k: judged(r) for k, r in rows.items()}

    base_sh = []
    for seed in range(BASELINE_SEEDS):
        rng = np.random.default_rng(seed)

        def rnd(t, rng=rng):
            s = s1_basis(t)
            return pd.Series(rng.random(len(s)), index=s.index)
        base_sh.append(metrics(run_book(rnd, days, nxt, fstore))["sharpe"])
    base_mean, base_p95 = float(np.mean(base_sh)), float(np.percentile(base_sh, 95))
    verdicts = {k: verdict(res[k], base_p95) for k in books}

    L = [f"# Daily cross-sectional long/short book — pre-registered study ({args.date_tag})", ""]
    L.append("Pre-registration: `logs/backtest_reports/prereg_xs_daily_20261020.md` (written before this code). "
             f"Panel: {len(close.columns)} crypto-only Bybit USDT perps, daily bars {idx[0]:%Y-%m-%d} → {idx[-1]:%Y-%m-%d}, "
             f"{len(days)} daily rebalances; decile legs, 10%-of-leg cap, dollar-neutral; cost "
             f"{COST_PER_UNIT_TURNOVER * 100:.3f}% per unit turnover + actual funding.\n")
    L.append(f"**Bar:** {BAR}\n")
    L.append("## Verdict\n")
    L.append("| signal | verdict | full Sharpe | H1 Sharpe | H2 Sharpe | max DD | % weeks green |")
    L.append("|---|---|---|---|---|---|---|")
    for k in books:
        r = res[k]
        L.append(f"| `{k}` | **{verdicts[k]}** | {fmt(r['full']['sharpe'])} | {fmt(r['h1']['sharpe'])} | "
                 f"{fmt(r['h2']['sharpe'])} | {fmt_pct(r['full']['mdd'])} | {fmt_pct(r['full']['pct_weeks'], 0)} |")
    L.append(f"\nNo-skill baseline (random ranking, S1 eligibility, {BASELINE_SEEDS} seeds): mean Sharpe {fmt(base_mean)}, "
             f"95th percentile {fmt(base_p95)} — a signal must beat the 95th percentile.\n")
    L.append("## Detail (net of taker cost + slippage + funding)\n")
    L.append("| signal | period | days | gross ann | net ann | net Sharpe | max DD | % weeks + | % days + | turnover/day | "
             "names/leg | cost ann | funding ann | long leg cum gross | short leg cum gross |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for k in books:
        for h in ("full", "h1", "h2", "maker"):
            m = res[k][h]
            lab = {"full": "full", "h1": "H1", "h2": "H2", "maker": "full @ maker cost (context)"}[h]
            L.append(f"| `{k}` | {lab} | {m['n']} | {fmt_pct(m['gross_ann'])} | {fmt_pct(m['net_ann'])} | {fmt(m['sharpe'])} | "
                     f"{fmt_pct(m['mdd'])} | {fmt_pct(m['pct_weeks'], 0)} | {fmt_pct(m['pct_days'], 0)} | {fmt(m['turnover'])} | "
                     f"{fmt(m['names'], 1)} | {fmt_pct(m['cost_ann'])} | {fmt_pct(-m['funding_ann'])} | "
                     f"{fmt_pct(m['long_cum'])} | {fmt_pct(m['short_cum'])} |")
    L.append("\n_funding ann is funding received (+) / paid (−) by the book; leg columns are the sum of daily gross "
             "contributions (price only)._\n")
    L.append("## By month (compounded net)\n")
    months = sorted({x["date"].strftime("%Y-%m") for x in rows["basis_24h"]})
    L.append("| month | " + " | ".join(f"`{k}`" for k in books) + " |")
    L.append("|---|" + "---|" * len(books))
    for mo in months:
        cells = []
        for k in books:
            r = [x["net"] for x in rows[k] if x["date"].strftime("%Y-%m") == mo]
            cells.append(fmt_pct(float(np.prod(1.0 + np.array(r)) - 1.0)) if r else "–")
        L.append(f"| {mo} | " + " | ".join(cells) + " |")
    L.append(f"\nMultiple testing: 2 judged trials (+ maker-cost context, not judged), on top of 90 momentum/carry variants "
             f"in the xs_momentum reports. Survivorship: today's listings only.\n")
    L.append(f"_Generated by `xs_daily_backtest.py` in {time.time() - t0:.0f}s._\n")

    path = os.path.join(REPORT_DIR, f"xs_daily_{args.date_tag}.md")
    with open(path, "w") as f:
        f.write("\n".join(L))
    print("\n".join(L[5:13]))
    print(f"report: {path}")


if __name__ == "__main__":
    main()
