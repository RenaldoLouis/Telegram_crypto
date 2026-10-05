#!/usr/bin/env python
"""
xs_momentum_paper.py — FORWARD PAPER TEST of the v2 "momentum ex-carry, pit30, 10% cap" L/S books (k=56, k=91).

PAPER ONLY: zero Claude tokens, zero order/execution logic, public Bybit endpoints, no API key.
Weights are produced by the SAME functions as the v2 backtest (xs_momentum_v2.run_momentum / run_carry), so the
forward book is the backtested book by construction. The rule set is frozen in RULES and fingerprinted (rules_hash).

  python xs_momentum_paper.py rebalance [--asof YYYY-MM-DD]   # Monday shortly after 00:00 UTC → logs/xs_momentum/weights_<Monday>.json
  python xs_momentum_paper.py score                            # scores every weights file whose next Monday close exists → scores.jsonl + scorecard.md
"""
import argparse
import hashlib
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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import xs_momentum_v2 as v2  # noqa: E402  (imports xs_momentum_backtest as v1; module-level constants only)

OUT_DIR = os.path.join(BASE_DIR, "logs", "xs_momentum")
BYBIT = "https://api.bybit.com"
VERSION = "xs_mom_ex_carry_v2.1"
BOOKS = {"k56": 56, "k91": 91}
DAY_MS = 86400 * 1000
WEEK_MS = 7 * DAY_MS
MIN_UNIVERSE = 50          # sanity guard on instruments-info (tests lower it)

# ------------------------------------------------------------------ FROZEN RULES (any change → new rules_hash → clock restarts)
RULES = {
    "version": VERSION,
    "signal": "trailing k-day close-to-close return on CLOSED daily bars, asof Sunday bar close = Monday 00:00 UTC",
    "lookbacks": [56, 91],
    "skip_days": 0,
    "universe": "Bybit linear USDT perpetuals, status Trading, CRYPTO ONLY",
    "crypto_only": {
        "exclude_symbolType": ["stock", "ETF", "commodity", "forex"],          # Bybit's own TradFi flag (instruments-info)
        "exclude_symbols": ["XAUTUSDT", "PAXGUSDT", "USDCUSDT", "USDEUSDT", "USD1USDT"],  # pegged assets Bybit leaves blank
    },
    "min_listed_days": 30,
    "min_history_bars": "lookback + 2",
    "min_turnover_7d_usdt": 10_000_000,
    "decile": 0.10,
    "leg_notional": 0.50,
    "per_name_cap_of_leg": 0.10,
    "cap_residual": "cash (leg under-invested)",
    "dollar_neutral": True,
    "carry_exclusion": {"n": 10, "signal": "most negative trailing-7d cumulative funding", "min_listed_days": 30,
                        "min_turnover_7d_usdt": 10_000_000, "min_history_bars": 9, "exclude_symbol": "BTCUSDT"},
    "hold": "one week, close-to-close",
    "costs": {"taker_fee": 0.00055, "slippage": 0.0003, "charged_on": "sum |w_t - drifted w_{t-1}|; first week full open"},
    "funding": "actual settlements in (Mon 00:00, next Mon 00:00], long pays positive / short receives positive",
}
COST_PER_UNIT = RULES["costs"]["taker_fee"] + RULES["costs"]["slippage"]

BAR_TEXT = (
    "At n = 26 scored weeks per book: net Sharpe >= 1.0 AND max drawdown <= 20% AND >= 55% weeks positive -> PASS "
    "(eligible for small real capital, user decision); net Sharpe < 0.5 -> FAIL (retire); anything between -> extend to "
    "n = 52 under the same bar. Kill rule at any n: max drawdown > 25% -> KILLED (retire). The rule set is frozen "
    "(rules_hash); any change restarts the clock."
)
BAR = {"n_decide": 26, "n_extend": 52, "sharpe_pass": 1.0, "mdd_pass": 0.20, "pct_pos_pass": 0.55, "sharpe_fail": 0.5, "mdd_kill": 0.25}


def rules_hash(rules=RULES):
    return hashlib.sha256(json.dumps(rules, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]


# ------------------------------------------------------------------ data source (injectable for tests)
class BybitSource:
    def __init__(self, sleep=0.1):
        self.s = requests.Session()
        self.sleep = sleep

    def _get(self, path, params, retries=4):
        last = None
        for i in range(retries):
            try:
                r = self.s.get(BYBIT + path, params=params, timeout=20)
                r.raise_for_status()
                j = r.json()
                if j.get("retCode") != 0:
                    raise RuntimeError(f"retCode={j.get('retCode')} {j.get('retMsg')}")
                return j["result"]
            except Exception as e:  # noqa: BLE001
                last = e
                time.sleep(0.7 * (i + 1))
        raise RuntimeError(f"GET {path} {params}: {last}")

    def instruments(self):
        out, cursor = [], ""
        while True:
            p = {"category": "linear", "limit": 1000}
            if cursor:
                p["cursor"] = cursor
            res = self._get("/v5/market/instruments-info", p)
            for it in res.get("list", []):
                if it.get("status") == "Trading" and it.get("quoteCoin") == "USDT" and it.get("contractType") == "LinearPerpetual":
                    out.append({"symbol": it["symbol"], "launchTime": int(it.get("launchTime") or 0),
                                "symbolType": it.get("symbolType") or ""})
            cursor = res.get("nextPageCursor") or ""
            if not cursor:
                break
        return out

    def klines(self, symbol, start_ms, end_ms, limit=200):
        res = self._get("/v5/market/kline", {"category": "linear", "symbol": symbol, "interval": "D",
                                             "start": start_ms, "end": end_ms, "limit": limit})
        time.sleep(self.sleep)
        return res.get("list", [])

    def funding(self, symbol, start_ms, end_ms):
        rows, cursor_end = [], end_ms
        for _ in range(20):
            res = self._get("/v5/market/funding/history", {"category": "linear", "symbol": symbol, "startTime": start_ms,
                                                           "endTime": cursor_end, "limit": 200})
            lst = res.get("list", [])
            if not lst:
                break
            rows += [[int(x["fundingRateTimestamp"]), float(x["fundingRate"])] for x in lst]
            oldest = min(int(x["fundingRateTimestamp"]) for x in lst)
            if oldest <= start_ms or len(lst) < 200:
                break
            cursor_end = oldest - 1
        rows.sort()
        return rows


# ------------------------------------------------------------------ helpers
def is_crypto(inst_row):
    """Crypto-only universe filter (RULES['crypto_only']): drop Bybit-flagged TradFi perps and the pegged-asset supplement."""
    co = RULES["crypto_only"]
    return (inst_row.get("symbolType") or "") not in co["exclude_symbolType"] and inst_row["symbol"] not in co["exclude_symbols"]


def ms(dt):
    return int(dt.timestamp() * 1000)


def monday_asof(now=None, asof=None):
    """The rebalance Monday 00:00 UTC: explicit --asof, else the most recent Monday 00:00 UTC <= now."""
    if asof:
        d = datetime.strptime(asof, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if d.weekday() != 0:
            raise ValueError(f"{asof} is not a Monday")
        return d
    now = now or datetime.now(timezone.utc)
    d = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return d - timedelta(days=d.weekday())


def _fetch_many(fn, symbols, threads, label):
    out, fails = {}, []
    with ThreadPoolExecutor(max_workers=threads) as ex:
        futs = {ex.submit(fn, s): s for s in symbols}
        for i, fut in enumerate(as_completed(futs)):
            s = futs[fut]
            try:
                out[s] = fut.result()
            except Exception as e:  # noqa: BLE001
                fails.append(s)
                print(f"  [{label} fail] {s}: {e}")
            if (i + 1) % 100 == 0:
                print(f"  {label} {i + 1}/{len(symbols)}")
    return out, fails


def build_panel(rows_by_symbol, end_exclusive_ms):
    """rows: Bybit kline rows [ts, o, h, l, c, v, turnover]. Keeps bars with open ts < end_exclusive_ms (closed bars only)."""
    closes, turns = {}, {}
    for sym, rows in rows_by_symbol.items():
        rows = [r for r in rows if int(r[0]) < end_exclusive_ms]
        if not rows:
            continue
        ts = pd.to_datetime([int(r[0]) for r in rows], unit="ms", utc=True)
        c = pd.Series([float(r[4]) for r in rows], index=ts).sort_index()
        t = pd.Series([float(r[6]) for r in rows], index=ts).sort_index()
        closes[sym], turns[sym] = c[~c.index.duplicated()], t[~t.index.duplicated()]
    if not closes:
        return pd.DataFrame(), pd.DataFrame()
    close = pd.DataFrame(closes).sort_index()
    turn = pd.DataFrame(turns).reindex(close.index)
    full = pd.date_range(close.index[0], close.index[-1], freq="D", tz="UTC")
    return close.reindex(full), turn.reindex(full)


def _native(w):
    return {str(k): round(float(v), 8) for k, v in w.items() if not (isinstance(v, float) and math.isnan(v))}


# ------------------------------------------------------------------ REBALANCE
def compute_books(close, turn, launch_ser, fstore, t):
    """
    Exact v2 book: t = the Sunday daily bar (its close is Monday 00:00 UTC). Returns (books, carry_excluded).
    Uses xs_momentum_v2.run_carry / run_momentum unchanged.
    """
    def listed_mask(min_days):
        def fn(tt):
            return ((tt + timedelta(days=1)) - launch_ser.reindex(close.columns)).dt.days >= min_days
        return fn

    _, baskets = v2.run_carry(close, turn, listed_mask(RULES["carry_exclusion"]["min_listed_days"]), [t], fstore,
                              RULES["carry_exclusion"]["n"], hedged=True)
    carry_excluded = list(baskets.get(t, []))

    books = {}
    for name, k in BOOKS.items():
        wks = v2.run_momentum(close, turn, listed_mask(RULES["min_listed_days"]), k, RULES["skip_days"], [t], fstore,
                              RULES["per_name_cap_of_leg"], lambda tt: carry_excluded)
        if not wks:
            books[name] = {"weights": {}, "n_long": 0, "n_short": 0, "n_eligible": 0, "leg_invested": 0.0, "note": "fewer than 10 eligible names"}
            continue
        wk = wks[0]
        books[name] = {"weights": _native(wk["weights"]), "n_long": int(wk["n_long"]), "n_short": int(wk["n_short"]),
                       "n_eligible": int(wk["n_elig"]), "leg_invested": round(float(wk["leg_invested"]), 6)}
    return books, carry_excluded


def rebalance(source, asof_monday, out_dir=OUT_DIR, threads=4):
    os.makedirs(out_dir, exist_ok=True)
    tag = asof_monday.strftime("%Y-%m-%d")
    path = os.path.join(out_dir, f"weights_{tag}.json")
    if os.path.exists(path):
        print(f"[rebalance] {path} exists — nothing to do (idempotent)")
        return None
    t0 = time.time()
    asof_ms = ms(asof_monday)
    bar_t = pd.Timestamp(asof_monday - timedelta(days=1))          # the Sunday bar
    print(f"[rebalance] asof close {asof_monday.isoformat()} (Sunday bar {bar_t.date()})")

    inst_all = source.instruments()
    inst = [u for u in inst_all if is_crypto(u)]
    tradfi_excluded = sorted(u["symbol"] for u in inst_all if not is_crypto(u))
    print(f"  crypto-only filter: {len(inst_all)} listed → {len(inst)} crypto ({len(tradfi_excluded)} TradFi/pegged excluded)")
    if len(inst) < MIN_UNIVERSE:
        raise RuntimeError(f"universe too small ({len(inst)})")
    launch_ser = pd.Series({u["symbol"]: pd.Timestamp(u["launchTime"], unit="ms", tz="UTC") for u in inst if u["launchTime"] > 0})
    symbols = [u["symbol"] for u in inst]
    print(f"  {len(symbols)} symbols; fetching {max(BOOKS.values()) + 35} daily bars each …")

    need_days = max(BOOKS.values()) + 35
    rows, fails = _fetch_many(lambda s: source.klines(s, asof_ms - need_days * DAY_MS, asof_ms - 1, limit=200), symbols, 1, "klines")
    close, turn = build_panel(rows, asof_ms)
    if close.empty or bar_t not in close.index:
        raise RuntimeError("panel missing the Sunday bar — is it closed yet?")
    close, turn = close.loc[:bar_t], turn.loc[:bar_t]
    for s in close.columns:                                            # symbols without launchTime → first bar
        if s not in launch_ser.index:
            launch_ser[s] = close[s].first_valid_index()
    print(f"  panel {close.shape[1]} symbols x {len(close)} days (kline failures: {len(fails)})")

    # funding for the carry signal: only names that can be carry-eligible (same filters as v2.run_carry)
    ce = RULES["carry_exclusion"]
    elig = ((turn.rolling(7).mean().loc[bar_t] >= ce["min_turnover_7d_usdt"])
            & (close.notna().rolling(ce["min_history_bars"]).sum().loc[bar_t] == ce["min_history_bars"])
            & (((bar_t + timedelta(days=1)) - launch_ser.reindex(close.columns)).dt.days >= ce["min_listed_days"]))
    cand = [s for s in elig[elig].index if s != ce["exclude_symbol"]]
    print(f"  funding (trailing 7d) for {len(cand)} carry-eligible names …")
    fraw, ffails = _fetch_many(lambda s: source.funding(s, asof_ms - WEEK_MS - 1, asof_ms), cand, threads, "funding")
    fstore = v2.FundingStore(fraw)

    books, carry_excluded = compute_books(close, turn, launch_ser, fstore, bar_t)
    out = {
        "version": VERSION, "rules_hash": rules_hash(), "rules": RULES,
        "asof_close": asof_monday.isoformat(), "asof_bar_open": bar_t.strftime("%Y-%m-%d"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "universe_size": int(close.shape[1]), "instruments_listed": len(inst_all), "tradfi_excluded": tradfi_excluded,
        "kline_failures": sorted(fails), "funding_failures": sorted(ffails),
        "carry_excluded": carry_excluded, "books": books,
    }
    with open(path, "w") as f:
        json.dump(out, f, indent=1)
    _write_latest_md(out, os.path.join(out_dir, "latest_weights.md"))
    for name, b in books.items():
        print(f"  {name}: {b['n_long']} long / {b['n_short']} short of {b['n_eligible']} eligible, leg invested {b['leg_invested'] * 100:.0f}%")
    print(f"[rebalance] wrote {path} in {time.time() - t0:.0f}s")
    return path


def _write_latest_md(out, path):
    L = [f"# XS momentum ex-carry — paper weights asof {out['asof_close']}",
         f"version `{out['version']}` · rules_hash `{out['rules_hash']}` · universe {out['universe_size']} crypto symbols "
         f"({len(out.get('tradfi_excluded', []))} TradFi/pegged perps excluded) · "
         f"carry names excluded: {', '.join(out['carry_excluded']) or 'none'}", ""]
    for name, b in out["books"].items():
        L.append(f"## {name} — {b['n_long']} long / {b['n_short']} short (eligible {b['n_eligible']}, leg invested {b['leg_invested'] * 100:.0f}%)")
        L.append("| symbol | weight |\n|---|---|")
        for s, w in sorted(b["weights"].items(), key=lambda x: -x[1]):
            L.append(f"| {s} | {w:+.4f} |")
        L.append("")
    L.append("_Paper test only. Weights are fractions of equity; long +, short −, net 0. No orders are placed by this project._")
    with open(path, "w") as f:
        f.write("\n".join(L))


# ------------------------------------------------------------------ SCORE
def score_book(weights, prev_end_weights, rets, funding_sums):
    """
    Pure arithmetic for one book-week.
      weights: {sym: w}  rets: {sym: close-to-close return}  funding_sums: {sym: Σ funding rates in the week}
      prev_end_weights: {sym: drifted end-of-week weight of the previous week} or None (first week → full open)
    Funding: long pays positive rates, short receives → P&L = −Σ w·F.
    """
    w = pd.Series(weights, dtype=float)
    r = pd.Series({s: rets.get(s, 0.0) for s in w.index}, dtype=float).fillna(0.0)
    f = pd.Series({s: funding_sums.get(s, 0.0) for s in w.index}, dtype=float).fillna(0.0)
    gross = float((w * r).sum())
    prev = pd.Series(prev_end_weights or {}, dtype=float)
    allsyms = w.index.union(prev.index)
    turnover = float((w.reindex(allsyms).fillna(0) - prev.reindex(allsyms).fillna(0)).abs().sum())
    cost = turnover * COST_PER_UNIT
    funding_pnl = float(-(w * f).sum())
    net = gross - cost + funding_pnl
    end_w = (w * (1 + r)) / (1 + gross) if gross > -1 else w * 0
    return {"gross": gross, "turnover": turnover, "cost": cost, "funding": funding_pnl, "net": net, "end_weights": _native(end_w)}


def load_scores(out_dir=OUT_DIR):
    p = os.path.join(out_dir, "scores.jsonl")
    if not os.path.exists(p):
        return []
    with open(p) as f:
        return [json.loads(line) for line in f if line.strip()]


def score(source, out_dir=OUT_DIR, now=None, threads=4):
    now = now or datetime.now(timezone.utc)
    os.makedirs(out_dir, exist_ok=True)
    records = load_scores(out_dir)
    done = {(r["week"], r["book"]) for r in records}
    files = sorted(f for f in os.listdir(out_dir) if f.startswith("weights_") and f.endswith(".json"))
    new = []
    for fn in files:
        week = fn[len("weights_"):-len(".json")]
        wmon = datetime.strptime(week, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        next_mon = wmon + timedelta(days=7)
        if now < next_mon + timedelta(minutes=5):
            continue                                                   # following Monday close not available yet
        if all((week, b) in done for b in BOOKS):
            continue
        with open(os.path.join(out_dir, fn)) as f:
            wf = json.load(f)
        held = sorted({s for b in wf["books"].values() for s in b["weights"]})
        if not held:
            continue
        print(f"[score] week {week}: {len(held)} held names")
        start_bar = ms(wmon) - DAY_MS            # Sunday bar before the Monday
        end_bar = ms(next_mon) - DAY_MS          # Sunday bar before the next Monday
        kl, kfail = _fetch_many(lambda s: source.klines(s, start_bar - DAY_MS, ms(next_mon) - 1, limit=20), held, 1, "klines")
        fr, ffail = _fetch_many(lambda s: source.funding(s, ms(wmon), ms(next_mon)), held, threads, "funding")
        if kfail:
            print(f"  kline failures {kfail} — week {week} left unscored, will retry next run")
            continue
        rets, flags = {}, {}
        for s, rows in kl.items():
            bars = {int(r[0]): float(r[4]) for r in rows if int(r[0]) < ms(next_mon)}
            c0, c1 = bars.get(start_bar), bars.get(end_bar)
            if c0 is None:
                flags[s] = "no_start_bar"
                continue
            if c1 is None:                        # delisted / halted mid-week → last available close
                later = [c for ts, c in bars.items() if ts > start_bar]
                c1 = later[-1] if later else c0
                flags[s] = "no_end_bar_last_close_used"
            rets[s] = c1 / c0 - 1.0
        fsums = {s: float(sum(r for ts, r in rows if ms(wmon) < ts <= ms(next_mon))) for s, rows in fr.items()}
        for s in ffail:
            flags[s] = flags.get(s, "") + "|funding_missing_flat_0"
        prev_week = (wmon - timedelta(days=7)).strftime("%Y-%m-%d")
        for book, b in wf["books"].items():
            if (week, book) in done or not b["weights"]:
                continue
            prev = next((r["end_weights"] for r in records if r["week"] == prev_week and r["book"] == book
                         and r.get("rules_hash") == wf["rules_hash"]), None)
            sc = score_book(b["weights"], prev, rets, fsums)
            rec = {"week": week, "book": book, "rules_hash": wf["rules_hash"], "version": wf.get("version"),
                   "n_names": len(b["weights"]), "first_week": prev is None, "flags": flags,
                   "scored_at": datetime.now(timezone.utc).isoformat(), **sc}
            rec = {k: (_native(v) if isinstance(v, dict) and k == "end_weights" else v) for k, v in rec.items()}
            records.append(rec)
            new.append(rec)
            done.add((week, book))
            print(f"  {book}: gross {sc['gross'] * 100:+.2f}%  cost {sc['cost'] * 100:.2f}%  funding {sc['funding'] * 100:+.2f}%  net {sc['net'] * 100:+.2f}%")
    if new:
        with open(os.path.join(out_dir, "scores.jsonl"), "a") as f:
            for r in new:
                f.write(json.dumps(r, separators=(",", ":")) + "\n")
    card = write_scorecard(records, out_dir)
    return new, card


# ------------------------------------------------------------------ bar + scorecard
def book_stats(nets):
    n = len(nets)
    if n == 0:
        return {"n": 0, "cum": 0.0, "sharpe": None, "mdd": 0.0, "pct_pos": None}
    r = np.array(nets, dtype=float)
    eq = np.cumprod(1 + r)
    mdd = float(np.max(1 - eq / np.maximum.accumulate(eq)))
    sd = r.std(ddof=1) if n > 1 else 0.0
    sharpe = float(r.mean() / sd * math.sqrt(52)) if sd > 0 else None
    return {"n": n, "cum": float(eq[-1] - 1), "sharpe": sharpe, "mdd": mdd, "pct_pos": float((r > 0).mean())}


def apply_bar(nets):
    st = book_stats(nets)
    n = st["n"]
    if n and st["mdd"] > BAR["mdd_kill"]:
        return "KILLED", st
    if n < BAR["n_decide"]:
        return f"BUILDING ({n}/{BAR['n_decide']})", st
    sh = st["sharpe"] if st["sharpe"] is not None else 0.0
    if sh >= BAR["sharpe_pass"] and st["mdd"] <= BAR["mdd_pass"] and st["pct_pos"] >= BAR["pct_pos_pass"]:
        return "PASS", st
    if sh < BAR["sharpe_fail"]:
        return "FAIL", st
    if n < BAR["n_extend"]:
        return f"EXTENDED ({n}/{BAR['n_extend']})", st
    return "FAIL (bar not met by n=52)", st


def _f(v, pct=True, d=2):
    if v is None:
        return "n/a"
    return f"{v * 100:+.{d}f}%" if pct else f"{v:.{d}f}"


def write_scorecard(records, out_dir=OUT_DIR):
    cur = rules_hash()
    L = [f"# XS momentum ex-carry — forward paper scorecard", "",
         "## Pre-registered bar", "", f"> {BAR_TEXT}", "",
         f"rules_hash `{cur}` · version `{VERSION}` · updated {datetime.now(timezone.utc).isoformat()}", ""]
    stale = [r for r in records if r.get("rules_hash") != cur]
    if stale:
        L.append(f"NOTE: {len(stale)} record(s) carry a different rules_hash and are EXCLUDED below (clock restarted).\n")
    summary = {}
    for book in BOOKS:
        recs = sorted([r for r in records if r["book"] == book and r.get("rules_hash") == cur], key=lambda r: r["week"])
        status, st = apply_bar([r["net"] for r in recs])
        summary[book] = (status, st, recs)
        L.append(f"## {book} — **{status}**\n")
        L.append("| n weeks | cumulative net | ann. Sharpe | max DD | % weeks + | avg turnover | avg funding/wk |")
        L.append("|---|---|---|---|---|---|---|")
        L.append(f"| {st['n']} | {_f(st['cum'])} | {_f(st['sharpe'], False)} | {_f(st['mdd'], d=1)} | "
                 f"{_f(st['pct_pos'], d=0) if st['pct_pos'] is not None else 'n/a'} | "
                 f"{_f(np.mean([r['turnover'] for r in recs]), False) if recs else 'n/a'} | "
                 f"{_f(np.mean([r['funding'] for r in recs])) if recs else 'n/a'} |")
        L.append("\n**Last 4 weeks**\n")
        L.append("| week | names | gross | cost | funding | net | flags |")
        L.append("|---|---|---|---|---|---|---|")
        for r in recs[-4:]:
            L.append(f"| {r['week']} | {r['n_names']} | {_f(r['gross'])} | {_f(-r['cost'])} | {_f(r['funding'])} | {_f(r['net'])} | "
                     f"{len(r.get('flags') or {})} |")
        if not recs:
            L.append("| — | | | | | | |")
        L.append("")
    L.append("_Paper test. Net = Σ w·(close/close − 1) − (0.055% + 0.03%)·turnover + funding received − funding paid. "
             "No orders are placed by this project._\n")
    with open(os.path.join(out_dir, "scorecard.md"), "w") as f:
        f.write("\n".join(L))
    return summary


# ------------------------------------------------------------------ telegram
def send_telegram(text):
    try:
        import config  # noqa: WPS433
        from delivery.telegram_bot import _send_with_retry
    except Exception as e:  # noqa: BLE001
        print(f"[telegram] helper unavailable ({e}); message:\n{text}")
        return False
    if not (config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID):
        print(f"[telegram] TELEGRAM env missing; message:\n{text}")
        return False
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    r = _send_with_retry(url, {"chat_id": config.TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"})
    if r is not None and r.status_code != 200:
        r = _send_with_retry(url, {"chat_id": config.TELEGRAM_CHAT_ID, "text": text})
    ok = r is not None and r.status_code == 200
    print(f"[telegram] {'sent' if ok else 'FAILED'}")
    return ok


def telegram_text(new, summary):
    weeks = sorted({r["week"] for r in new})
    L = [f"<b>XS momentum paper — week {weeks[-1]} scored</b>"]
    for book in BOOKS:
        status, st, _ = summary[book]
        rec = next((r for r in new if r["book"] == book), None)
        wk = f"{rec['net'] * 100:+.2f}% (gross {rec['gross'] * 100:+.2f}%, fund {rec['funding'] * 100:+.2f}%)" if rec else "no new week"
        L.append(f"<b>{book}</b>: week {wk}")
        L.append(f"  cum {st['cum'] * 100:+.1f}% · Sharpe {st['sharpe'] if st['sharpe'] is None else round(st['sharpe'], 2)} · "
                 f"MDD {st['mdd'] * 100:.1f}% · n {st['n']}/{BAR['n_decide']} · {status}")
    L.append("paper only — no orders")
    return "\n".join(L[:15])


# ------------------------------------------------------------------ CLI
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("rebalance")
    r.add_argument("--asof", help="Monday YYYY-MM-DD (default: most recent Monday 00:00 UTC)")
    sub.add_parser("score")
    args = ap.parse_args(argv)
    src = BybitSource()
    if args.cmd == "rebalance":
        try:
            rebalance(src, monday_asof(asof=args.asof))
        except Exception as e:  # noqa: BLE001
            print(f"[rebalance] FAILED: {e}")
            return 1
        return 0
    try:
        new, summary = score(src)
    except Exception as e:  # noqa: BLE001
        print(f"[score] FAILED: {e}")
        return 1
    if new:
        send_telegram(telegram_text(new, summary))
    else:
        print("[score] no new week to score; scorecard regenerated, no Telegram")
    return 0


if __name__ == "__main__":
    sys.exit(main())
