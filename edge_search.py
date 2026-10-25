"""Edge search with a locked holdout (2026-10-25) — pre-registered, research-only.

The user: "if you are a trader who trades for a living, keep finding another strategy to profit
monthly until you find it." Searching until something passes finds a false winner unless the
final judgement uses data the search never saw, so the protocol in
`logs/backtest_reports/prereg_edge_search_20261025.md` is enforced in code:

  discover  DISCOVERY data only (the panel is cut at 2024-12-31 when it is LOADED). Every
            variant evaluated is appended to the ledger; N = ledger lines; the finalist Sharpe
            bar is max(1, √(2 ln N) / √years) and rises as the search grows.
  report    ranks the ledger against the finalist bar.
  confirm   HOLDOUT (2025-01-01 → end), once, only for finalists committed to git in
            `logs/backtest_reports/edge_finalists.json`.

Universe: every Bybit USDT perp ever listed (incl. delisted; `edge_data.py`), point in time:
listed ≥ 30 days, trailing-30-day median turnover ≥ $5M. Trading model: weights decided at the
daily close, held over the next day; taker + liquidity-tiered slippage on every weight change;
actual funding. Zero trading decisions, no order API, no hosted model.

Usage:
    venv/bin/python edge_search.py discover [--families mom,carry]
    venv/bin/python edge_search.py report
    venv/bin/python edge_search.py confirm
"""

import argparse
import json
import math
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import config
from edge_data import CACHE, DAY_MS

BASE_DIR = Path(__file__).resolve().parent
REPORT_DIR = BASE_DIR / "logs" / "backtest_reports"
LEDGER = REPORT_DIR / "edge_search_ledger.jsonl"
FINALISTS = REPORT_DIR / "edge_finalists.json"
SERIES = CACHE / "series_discovery.pkl"

DISCOVERY_END = pd.Timestamp("2024-12-31", tz="UTC")
HOLDOUT_START = pd.Timestamp("2025-01-01", tz="UTC")
FULL_YEARS = (2021, 2022, 2023, 2024)

MIN_AGE_DAYS, MIN_TURNOVER, MIN_NAMES = 30, 5e6, 20
TAKER = config.TAKER_FEE_PCT
SPOT_TAKER = 0.0010
SLIP_TIERS = ((200e6, 0.0003), (50e6, 0.0006))          # else 0.0012
SLIP_ILLIQUID = 0.0012
TARGET_VOL = 0.20
LEG_FRACS = (0.1, 0.2)

BAR_GREEN, BAR_YEARS_UP, BAR_YEAR_FLOOR, BAR_DD, BAR_ALPHA_T, BAR_MIN_SHARPE = 0.60, 3, -0.10, 0.25, 2.0, 1.0
HOLDOUT_SHARPE, HOLDOUT_GREEN, HOLDOUT_DD = 0.75, 0.60, 0.25
MAX_FINALISTS = 3


# ─── Data ────────────────────────────────────────────────────────────────────

class Panel:
    """Daily close / turnover / funding for every symbol, cut at `end` while loading, plus the
    point-in-time eligibility, per-side cost and the equal-weight eligible market."""

    def __init__(self, end=DISCOVERY_END, symbols=None):
        insts = json.loads((CACHE / "instruments.json").read_text())["instruments"]
        end_ms = None if end is None else int(end.timestamp() * 1000)
        cl, tu, fu = {}, {}, {}
        for x in insts:
            s = x["symbol"]
            if symbols is not None and s not in symbols:
                continue
            kp = CACHE / f"{s}_D.json"
            if not kp.exists():
                continue
            rows = [r for r in json.loads(kp.read_text()) if end_ms is None or r[0] <= end_ms]
            if not rows:
                continue
            idx = pd.to_datetime([r[0] for r in rows], unit="ms", utc=True)
            cl[s] = pd.Series([r[4] for r in rows], index=idx, dtype=float)
            tu[s] = pd.Series([r[6] for r in rows], index=idx, dtype=float)
            # A settlement at a day's end (incl. 00:00 of the next day) is paid by the position held
            # over that day: day = floor((ts − 1) / 1 day).
            fr = [r for r in json.loads((CACHE / f"{s}_funding.json").read_text())
                  if end_ms is None or r[0] <= end_ms + DAY_MS]
            if fr:
                days = pd.to_datetime([(t - 1) // DAY_MS * DAY_MS for t, _ in fr], unit="ms", utc=True)
                fu[s] = pd.Series([r for _, r in fr], index=days, dtype=float).groupby(level=0).sum()
        self.build(cl, tu, fu)

    def build(self, cl, tu, fu):
        close = pd.DataFrame(cl).sort_index()
        idx = pd.date_range(close.index.min(), close.index.max(), freq="D")
        self.close = close.reindex(idx)
        cols = self.close.columns
        self.turn = pd.DataFrame(tu).reindex(index=idx, columns=cols)
        self.fund = pd.DataFrame(fu).reindex(index=idx, columns=cols).fillna(0.0)
        self.ret = self.close.pct_change(fill_method=None)
        self.age = self.close.notna().cumsum()
        self.med_turn = self.turn.rolling(30, min_periods=1).median()
        self.elig = (self.age >= MIN_AGE_DAYS) & (self.med_turn >= MIN_TURNOVER) & self.close.notna()
        mt = self.med_turn.fillna(0.0).to_numpy()
        slip = np.select([mt >= SLIP_TIERS[0][0], mt >= SLIP_TIERS[1][0]], [SLIP_TIERS[0][1], SLIP_TIERS[1][1]],
                         SLIP_ILLIQUID)
        self.cost = pd.DataFrame(TAKER + slip, index=idx, columns=cols)
        self.mkt = self.ret.where(self.elig.shift(1, fill_value=False)).mean(axis=1).fillna(0.0)
        self.vol30 = self.ret.rolling(30, min_periods=20).std()


def from_frames(close, turn, fund):
    """A Panel from ready-made frames (tests)."""
    p = Panel.__new__(Panel)
    p.build({c: close[c] for c in close}, {c: turn[c] for c in turn}, {c: fund[c] for c in fund})
    return p


# ─── Engine ──────────────────────────────────────────────────────────────────

def run_weights(P, W):
    """Daily net return of weights W (row d = decided at d's close, held over day d+1): price
    return − funding paid − taker + slippage on every change (a coin that stops trading is
    closed at its last close)."""
    W = W.reindex(index=P.close.index, columns=P.close.columns).fillna(0.0)
    W = W.where(P.close.notna(), 0.0)
    prev = W.shift(1).fillna(0.0)
    gross = (prev * P.ret.fillna(0.0)).sum(axis=1)
    fund = (prev * P.fund).sum(axis=1)
    cost = ((W - prev).abs() * P.cost.fillna(TAKER + SLIP_ILLIQUID)).sum(axis=1)
    return gross - fund - cost


def run_harvest(P, W):
    """Hedged funding harvest: W ≤ 0 = short perp + long the same notional spot, so price cancels
    (basis changes ignored — an approximation). Earns funding; pays both legs' costs."""
    W = W.reindex(index=P.close.index, columns=P.close.columns).fillna(0.0).where(P.close.notna(), 0.0)
    prev = W.shift(1).fillna(0.0)
    fund = (prev * P.fund).sum(axis=1)
    side = P.cost.fillna(TAKER + SLIP_ILLIQUID)
    cost = ((W - prev).abs() * (side + SPOT_TAKER + (side - TAKER))).sum(axis=1)
    return -fund - cost


def hold_weekly(W):
    """Keep the weights decided on Sunday's close (= Monday 00:00 UTC) for the week."""
    W = W.copy()
    W.loc[W.index.dayofweek != 6] = np.nan
    return W.ffill().fillna(0.0)


def xs_book(P, score, frac, weekly=True, invvol=False, elig=None):
    """Long the top `frac` of eligible names by score, short the bottom `frac`; 0.5 gross per leg."""
    s = score.where(P.elig if elig is None else elig)
    n = s.count(axis=1)
    k = np.floor(n * frac).clip(lower=1)
    r = s.rank(axis=1, method="first")
    long, short = r.gt(n - k, axis=0), r.le(k, axis=0)
    if invvol:
        iv = (1 / P.vol30).replace([np.inf, -np.inf], np.nan)
        lw, sw = iv.where(long), iv.where(short)
    else:
        lw, sw = long.astype(float).where(long), short.astype(float).where(short)
    W = (0.5 * lw.div(lw.sum(axis=1), axis=0)).fillna(0.0) - (0.5 * sw.div(sw.sum(axis=1), axis=0)).fillna(0.0)
    W.loc[n < MIN_NAMES] = 0.0
    return hold_weekly(W) if weekly else W


def momentum(P, lookback, skip=0):
    return P.close.shift(skip) / P.close.shift(skip + lookback) - 1


def liquid(P, top):
    """Eligible AND among the `top` names by trailing-30-day median turnover that day."""
    return P.elig & (P.med_turn.where(P.elig).rank(axis=1, ascending=False) <= top)


def xs_z(df, elig):
    x = df.where(elig)
    return x.sub(x.mean(axis=1), axis=0).div(x.std(axis=1), axis=0)


# ─── Strategy families ───────────────────────────────────────────────────────

def f_xs_momentum(P, lookback, skip, frac):
    return xs_book(P, momentum(P, lookback, skip), frac)


def f_tsmom(P, lookback, long_only):
    sig = np.sign(momentum(P, lookback)).where(P.elig)
    raw = sig / P.vol30
    raw = raw.replace([np.inf, -np.inf], np.nan)
    W = raw.div(raw.abs().sum(axis=1), axis=0).fillna(0.0)
    if long_only:
        W = W.clip(lower=0.0)
    W.loc[P.elig.sum(axis=1) < MIN_NAMES] = 0.0
    return hold_weekly(W)


def f_carry(P, days, frac):
    """Long the names whose perps paid the least funding, short the ones paying the most."""
    return xs_book(P, -P.fund.rolling(days, min_periods=days).sum(), frac)


def f_reversal(P, lookback, frac):
    return xs_book(P, -momentum(P, lookback), frac, weekly=lookback >= 7)


def f_new_listing_short(P, delay, hold, hedge):
    """Short every new perp from `delay` days after its first bar for `hold` days, 10% of capital
    each (scaled down when more than 10 are open); optional 1:1 BTC long hedge."""
    first = P.close.notna().idxmax()
    W = pd.DataFrame(0.0, index=P.close.index, columns=P.close.columns)
    mt = P.med_turn
    for s, f in first.items():
        if f == P.close.index[0]:
            continue                                    # listed before the data starts — not new
        start = f + pd.Timedelta(days=delay)
        if start not in mt.index or not (mt.at[start, s] >= MIN_TURNOVER):
            continue
        end = start + pd.Timedelta(days=hold - 1)
        W.loc[start:end, s] = -0.1
    count = (W < 0).sum(axis=1)
    W = W.mul(np.minimum(1.0, 10 / count.replace(0, np.nan)).fillna(0.0), axis=0)
    if hedge and "BTCUSDT" in W:
        W["BTCUSDT"] = W["BTCUSDT"] - W.drop(columns="BTCUSDT").sum(axis=1)
    return W


def f_low_vol(P, window, frac):
    vol = P.ret.rolling(window, min_periods=int(window * 0.7)).std()
    return xs_book(P, -vol, frac)


def f_low_beta(P, window, frac):
    m = P.mkt
    cov = P.ret.rolling(window, min_periods=int(window * 0.7)).cov(m)
    beta = cov.div(m.rolling(window, min_periods=int(window * 0.7)).var(), axis=0)
    return xs_book(P, -beta, frac)


def f_turnover_shock(P, sign, frac):
    shock = P.turn.rolling(7, min_periods=5).mean() / P.turn.rolling(30, min_periods=20).mean()
    return xs_book(P, sign * shock, frac)


def f_high_52w(P, frac):
    return xs_book(P, P.close / P.close.rolling(365, min_periods=90).max(), frac)


def f_btc_trend(P, sma, short):
    c = P.close["BTCUSDT"]
    up = c > c.rolling(sma, min_periods=sma).mean()
    W = pd.DataFrame(0.0, index=P.close.index, columns=P.close.columns)
    W["BTCUSDT"] = np.where(up, 1.0, -1.0 if short else 0.0)
    W.loc[c.rolling(sma, min_periods=sma).mean().isna(), "BTCUSDT"] = 0.0
    return W


def f_weekend(P, weekend):
    W = pd.DataFrame(0.0, index=P.close.index, columns=P.close.columns)
    nxt = (W.index + pd.Timedelta(days=1)).dayofweek          # the day the position is held over
    W["BTCUSDT"] = np.where(np.isin(nxt, (5, 6)) == weekend, 1.0, 0.0)
    return W


def f_harvest(P, top):
    """Each week: the `top` eligible names with the highest positive 7-day funding, hedged."""
    f7 = P.fund.rolling(7, min_periods=7).sum().where(P.elig)
    r = f7.rank(axis=1, ascending=False, method="first")
    pick = (r <= top) & (f7 > 0)
    W = -(pick.astype(float).div(top))
    return hold_weekly(W)


def f_xs_momentum_liquid(P, lookback, top, frac):
    return xs_book(P, momentum(P, lookback), frac, elig=liquid(P, top))


def f_reversal_liquid(P, lookback, top, frac):
    return xs_book(P, -momentum(P, lookback), frac, elig=liquid(P, top))


def f_mom_carry(P, lookback, days, frac):
    """Equal blend of the cross-sectional momentum and carry z-scores."""
    score = xs_z(momentum(P, lookback), P.elig) + xs_z(-P.fund.rolling(days, min_periods=days).sum(), P.elig)
    return xs_book(P, score, frac)


def f_mom_long_btc_hedged(P, lookback, frac):
    """The momentum long leg at gross 1, hedged with the same notional short BTC."""
    W = f_xs_momentum(P, lookback, 0, frac).clip(lower=0.0) * 2
    W["BTCUSDT"] = W["BTCUSDT"] - W.sum(axis=1)
    return W


def f_combo(P):
    """Fixed before any result (literature priors): momentum 56d + carry 7d + new-listing short,
    one third of capital each."""
    return (f_xs_momentum(P, 56, 0, 0.1) + f_carry(P, 7, 0.1) + f_new_listing_short(P, 1, 30, False)) / 3


def variants():
    """(family, name, fn, params, engine) — the full DISCOVERY menu, in a fixed order."""
    v = []
    for lb in (7, 14, 28, 56, 91, 182):
        for skip in ((0, 7) if lb >= 28 else (0,)):
            for fr in LEG_FRACS:
                v.append(("mom", f"xs_mom_{lb}d_skip{skip}_{int(fr * 100)}pct", f_xs_momentum,
                          {"lookback": lb, "skip": skip, "frac": fr}, "weights"))
    for lb in (14, 28, 56, 91):
        for lo in (False, True):
            v.append(("tsmom", f"tsmom_{lb}d_{'long' if lo else 'ls'}", f_tsmom, {"lookback": lb, "long_only": lo}, "weights"))
    for d in (3, 7, 14, 30):
        for fr in LEG_FRACS:
            v.append(("carry", f"xs_carry_{d}d_{int(fr * 100)}pct", f_carry, {"days": d, "frac": fr}, "weights"))
    for lb in (1, 3, 7):
        for fr in LEG_FRACS:
            v.append(("reversal", f"xs_rev_{lb}d_{int(fr * 100)}pct", f_reversal, {"lookback": lb, "frac": fr}, "weights"))
    for delay in (1, 7):
        for hold in (14, 30, 60):
            for hedge in (False, True):
                v.append(("listing", f"new_listing_short_d{delay}_h{hold}{'_btc' if hedge else ''}", f_new_listing_short,
                          {"delay": delay, "hold": hold, "hedge": hedge}, "weights"))
    for w in (30, 90):
        for fr in LEG_FRACS:
            v.append(("lowvol", f"low_vol_{w}d_{int(fr * 100)}pct", f_low_vol, {"window": w, "frac": fr}, "weights"))
    for fr in LEG_FRACS:
        v.append(("lowvol", f"low_beta_90d_{int(fr * 100)}pct", f_low_beta, {"window": 90, "frac": fr}, "weights"))
    for sign in (1, -1):
        v.append(("turnover", f"turnover_shock_{'long' if sign > 0 else 'short'}_10pct", f_turnover_shock,
                  {"sign": sign, "frac": 0.1}, "weights"))
    for fr in LEG_FRACS:
        v.append(("high52", f"near_52w_high_{int(fr * 100)}pct", f_high_52w, {"frac": fr}, "weights"))
    for sma in (20, 50, 100, 200):
        for short in (False, True):
            v.append(("btc_trend", f"btc_sma{sma}_{'ls' if short else 'long'}", f_btc_trend, {"sma": sma, "short": short}, "weights"))
    for wk in (True, False):
        v.append(("calendar", f"btc_{'weekend' if wk else 'weekday'}_long", f_weekend, {"weekend": wk}, "weights"))
    for top in (5, 10):
        v.append(("harvest", f"funding_harvest_top{top}", f_harvest, {"top": top}, "harvest"))
    # Batch 2 — added and committed before the first DISCOVERY run.
    for lb in (28, 56, 91):
        v.append(("mom", f"xs_mom_{lb}d_top50_20pct", f_xs_momentum_liquid, {"lookback": lb, "top": 50, "frac": 0.2}, "weights"))
        v.append(("mom", f"xs_mom_long_{lb}d_btc_hedged", f_mom_long_btc_hedged, {"lookback": lb, "frac": 0.1}, "weights"))
    for fr in LEG_FRACS:
        v.append(("mom_carry", f"mom56_carry7_{int(fr * 100)}pct", f_mom_carry, {"lookback": 56, "days": 7, "frac": fr}, "weights"))
    v.append(("reversal", "xs_rev_7d_top50_20pct", f_reversal_liquid, {"lookback": 7, "top": 50, "frac": 0.2}, "weights"))
    v.append(("combo", "combo_mom56_carry7_listing30", f_combo, {}, "weights"))
    return v


def build_series(P, fn, params, engine):
    W = fn(P, **params)
    return run_harvest(P, W) if engine == "harvest" else run_weights(P, W), W


# ─── Metrics ─────────────────────────────────────────────────────────────────

def metrics(r, mkt, start=None, end=None, scale=None):
    """Net daily returns → Sharpe, months green, years, drawdown at 20% vol, alpha vs market.
    The window starts at the first day with a non-zero return (the strategy's active life)."""
    r = r.loc[start:end]
    nz = r[r != 0]
    if len(nz) < 60:
        return None
    r = r.loc[nz.index[0]:]
    m = mkt.reindex(r.index).fillna(0.0)
    sd = r.std()
    vol = sd * math.sqrt(365)
    scale = scale if scale is not None else (TARGET_VOL / vol if vol > 0 else 1.0)
    months = r.resample("ME").sum()
    years = r.resample("YE").sum()
    eq = (r * scale).cumsum()
    dd = float((eq.cummax() - eq).max())
    x, y = m.to_numpy(), r.to_numpy()
    xm, ym = x.mean(), y.mean()
    sxx = ((x - xm) ** 2).sum()
    beta = float(((x - xm) * (y - ym)).sum() / sxx) if sxx else 0.0
    alpha = ym - beta * xm
    resid = y - alpha - beta * x
    se = math.sqrt(resid.var(ddof=2) * (1 / len(y) + xm ** 2 / sxx)) if sxx else float("inf")
    return {"start": str(r.index[0].date()), "end": str(r.index[-1].date()), "years": len(r) / 365.25,
            "ann": float(r.mean() * 365), "vol": float(vol), "sharpe": float(r.mean() / sd * math.sqrt(365)) if sd else 0.0,
            "months": int(len(months)), "green": int((months > 0).sum()), "green_pct": float((months > 0).mean()),
            "worst_month_20v": float(months.min() * scale), "scale": float(scale), "dd_20v": dd,
            "years_20v": {str(k.year): float(v * scale) for k, v in years.items()},
            "beta": beta, "alpha_ann": float(alpha * 365), "alpha_t": float(alpha / se) if se else 0.0}


def sharpe_bar(n_trials, years):
    """The best Sharpe expected from n strategies with no edge over `years` (≥ 1.0)."""
    return max(BAR_MIN_SHARPE, math.sqrt(2 * math.log(max(n_trials, 2))) / math.sqrt(max(years, 0.5)))


def finalist_checks(m, n_trials):
    """The pre-registered finalist bar → (passed, list of misses)."""
    if m is None:
        return False, ["< 60 active days"]
    misses = []
    bar = sharpe_bar(n_trials, m["years"])
    if m["sharpe"] < bar:
        misses.append(f"Sharpe {m['sharpe']:.2f} < {bar:.2f}")
    if m["green_pct"] < BAR_GREEN:
        misses.append(f"green {m['green_pct'] * 100:.0f}%")
    yrs = [m["years_20v"].get(str(y)) for y in FULL_YEARS]
    yrs = [y for y in yrs if y is not None]
    if sum(1 for y in yrs if y > 0) < BAR_YEARS_UP:
        misses.append(f"{sum(1 for y in yrs if y > 0)}/4 years up")
    if yrs and min(yrs) < BAR_YEAR_FLOOR:
        misses.append(f"worst year {min(yrs) * 100:.0f}%")
    if m["dd_20v"] > BAR_DD:
        misses.append(f"DD {m['dd_20v'] * 100:.0f}%")
    if m["alpha_t"] < BAR_ALPHA_T:
        misses.append(f"alpha t {m['alpha_t']:.1f}")
    return not misses, misses


# ─── Ledger ──────────────────────────────────────────────────────────────────

def read_ledger():
    if not LEDGER.exists():
        return []
    return [json.loads(x) for x in LEDGER.read_text().splitlines() if x.strip()]


def append_ledger(rows):
    with LEDGER.open("a") as f:
        for r in rows:
            f.write(json.dumps(r, separators=(",", ":")) + "\n")


# ─── Commands ────────────────────────────────────────────────────────────────

def cmd_discover(args):
    t0 = time.time()
    P = Panel(end=DISCOVERY_END)
    assert P.close.index.max() <= DISCOVERY_END, "holdout data leaked into DISCOVERY"
    print(f"DISCOVERY panel {P.close.index.min().date()} → {P.close.index.max().date()}, "
          f"{P.close.shape[1]} symbols ({time.time() - t0:.0f}s)")
    fams = set(args.families.split(",")) if args.families else None
    done = {r["name"] for r in read_ledger()}
    store = pd.read_pickle(SERIES) if SERIES.exists() else {}
    rows = []
    for fam, name, fn, params, engine in variants():
        if (fams and fam not in fams) or (name in done and not args.again):
            continue
        r, W = build_series(P, fn, params, engine)
        m = metrics(r, P.mkt)
        gross = W.abs().sum(axis=1)
        rows.append({"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "family": fam, "name": name,
                     "params": params, "engine": engine, "metrics": m,
                     "avg_gross": float(gross[gross > 0].mean()) if (gross > 0).any() else 0.0})
        store[name] = r
        s = "—" if m is None else f"Sharpe {m['sharpe']:+.2f} green {m['green_pct'] * 100:.0f}% alpha t {m['alpha_t']:+.1f}"
        print(f"  {name}: {s} ({time.time() - t0:.0f}s)", flush=True)
    append_ledger(rows)
    pd.to_pickle(store, SERIES)
    print(f"Ledger: {len(read_ledger())} variants (+{len(rows)})")
    cmd_report(args)


def cmd_report(args):
    led = read_ledger()
    n = len(led)
    L = [f"# Edge search — DISCOVERY ledger ({datetime.now(timezone.utc):%Y-%m-%d})",
         f"\nProtocol: `logs/backtest_reports/prereg_edge_search_20261025.md`. DISCOVERY = first bar → "
         f"{DISCOVERY_END.date()}; the holdout has not been read. **N = {n} variants tried** → the Sharpe bar is "
         f"max(1, √(2 ln {n}) / √years) = {sharpe_bar(n, 4):.2f} for 4 active years. Returns are net of taker + "
         f"slippage + funding at each strategy's own gross exposure; '@20v' = scaled to 20% annual volatility.\n",
         "| family | variant | active | Sharpe | bar | ann @20v | months green | worst month @20v | 2021 | 2022 | 2023 | 2024 "
         "| DD @20v | beta | alpha t | finalist? |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    ranked = sorted((r for r in led if r["metrics"]), key=lambda r: -r["metrics"]["sharpe"])
    for r in ranked:
        m = r["metrics"]
        ok, miss = finalist_checks(m, n)
        y = [m["years_20v"].get(str(k)) for k in FULL_YEARS]
        L.append(f"| {r['family']} | {r['name']} | {m['start'][:7]}→ | {m['sharpe']:+.2f} | {sharpe_bar(n, m['years']):.2f} | "
                 f"{m['ann'] * m['scale'] * 100:+.0f}% | {m['green']}/{m['months']} ({m['green_pct'] * 100:.0f}%) | "
                 f"{m['worst_month_20v'] * 100:+.1f}% | " + " | ".join("—" if v is None else f"{v * 100:+.0f}%" for v in y) +
                 f" | {m['dd_20v'] * 100:.0f}% | {m['beta']:+.2f} | {m['alpha_t']:+.1f} | "
                 f"{'**YES**' if ok else '; '.join(miss)} |")
    for r in led:
        if not r["metrics"]:
            L.append(f"| {r['family']} | {r['name']} | — | inactive (< 60 days) | | | | | | | | | | | | |")
    out = REPORT_DIR / f"edge_search_{datetime.now(timezone.utc):%Y%m%d}.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"Report: {out}")


def _committed(path):
    try:
        rel = str(path.relative_to(BASE_DIR))
    except ValueError:
        return False
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=BASE_DIR, capture_output=True).returncode == 0
    clean = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", rel], cwd=BASE_DIR).returncode == 0
    return tracked and clean


def cmd_confirm(args):
    if not FINALISTS.exists() or not _committed(FINALISTS):
        raise SystemExit("Refusing: edge_finalists.json must exist and be committed unchanged before the holdout is read.")
    fin = json.loads(FINALISTS.read_text())
    menu = {name: (fam, fn, params, engine) for fam, name, fn, params, engine in variants()}
    P = Panel(end=None)
    L = [f"# Edge search — HOLDOUT ({datetime.now(timezone.utc):%Y-%m-%d})",
         f"\nFinalists committed in `{FINALISTS.relative_to(BASE_DIR)}` (N at selection = {fin['n_trials']}). "
         f"HOLDOUT = {HOLDOUT_START.date()} → {P.close.index.max().date()}, read once. Scale = each finalist's "
         f"DISCOVERY scale. PASS = net > 0, ≥ {HOLDOUT_GREEN * 100:.0f}% months green, Sharpe ≥ {HOLDOUT_SHARPE}, "
         f"DD ≤ {HOLDOUT_DD * 100:.0f}% at that scale.\n",
         "| line | net @20v | Sharpe | months green | worst month @20v | DD @20v | verdict |", "|---|---|---|---|---|---|---|"]
    combo = []
    for f in fin["finalists"]:
        fam, fn, params, engine = menu[f["name"]]
        r, _ = build_series(P, fn, params, engine)
        combo.append(r * f["scale"])
        L.append(_holdout_row(f["name"], r, P.mkt, f["scale"]))
    if len(combo) > 1:
        c = sum(combo) / len(combo)
        L.append(_holdout_row("equal-risk combination", c, P.mkt, 1.0))
    out = REPORT_DIR / f"edge_holdout_{datetime.now(timezone.utc):%Y%m%d}.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))
    print(f"Saved {out}")


def _holdout_row(name, r, mkt, scale):
    m = metrics(r, mkt, start=HOLDOUT_START, scale=scale)
    if m is None:
        return f"| {name} | inactive | | | | | **FAIL** |"
    ok = (m["ann"] > 0 and m["green_pct"] >= HOLDOUT_GREEN and m["sharpe"] >= HOLDOUT_SHARPE and m["dd_20v"] <= HOLDOUT_DD)
    return (f"| {name} | {m['ann'] * scale * m['years'] * 100:+.1f}% | {m['sharpe']:+.2f} | {m['green']}/{m['months']} "
            f"({m['green_pct'] * 100:.0f}%) | {m['worst_month_20v'] * 100:+.1f}% | {m['dd_20v'] * 100:.0f}% | "
            f"**{'PASS' if ok else 'FAIL'}** |")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("discover")
    d.add_argument("--families", help="comma list of families to run (default: all)")
    d.add_argument("--again", action="store_true", help="re-evaluate variants already in the ledger (adds lines)")
    d.set_defaults(fn=cmd_discover)
    sub.add_parser("report").set_defaults(fn=cmd_report)
    sub.add_parser("confirm").set_defaults(fn=cmd_confirm)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
