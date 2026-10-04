"""regime_scorecard.py -- RESEARCH ONLY (zero Claude calls, zero order logic).

Measures directly whether the momentum-pulse market-regime label "understands
the market": does the label at time t predict the 1/3/7-day forward
cross-sectional return / breadth of the liquid Bybit USDT-perp universe?

Data:
  * regime history reconstructed from the git history of logs/momentum/hot_list.json
  * daily klines (interval D, last 200 days) for the top-60 USDT perps by
    CURRENT turnover24h (+BTCUSDT), cached under logs/backtest_cache/regime_<sym>_D.json

Usage:
  source venv/bin/activate && python regime_scorecard.py
  -> logs/backtest_reports/regime_scorecard_YYYYMMDD.md
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import requests

ROOT = os.path.dirname(os.path.abspath(__file__))
HOT_LIST_PATH = "logs/momentum/hot_list.json"
CACHE_DIR = os.path.join(ROOT, "logs", "backtest_cache")
REPORT_DIR = os.path.join(ROOT, "logs", "backtest_reports")
BYBIT = "https://api.bybit.com"
UNIVERSE_N = 60
KLINE_DAYS = 200
HORIZONS = (1, 3, 7)
PRIMARY_K = 7
BOOT_REPS = 2000
BLOCK_DAYS = 7
CI = 90
SEED = 20261004
CACHE_MAX_AGE_H = 20
REGIMES = ("risk_off", "cautious", "neutral", "risk_on")

PRE_REGISTERED_BAR = (
    "The regime label is INFORMATIVE if the 7-day forward median cross-sectional "
    "return differs between risk_on and risk_off observations with non-overlapping "
    "90% block-bootstrap CIs AND the sign of the difference is the same in both "
    "chronological halves. It is USEFUL only if it also beats the naive baseline "
    "(the sign of the 24h median change that feeds it) on the same test. "
    "Otherwise: NOT INFORMATIVE."
)

OPERATIONALISATION = """Operationalisation fixed BEFORE any number was computed:

* Observation = one deduplicated `generated_utc` stamp of `hot_list.json` carrying a
  `market_regime.regime` label. t = `generated_utc`.
* Entry price = the first DAILY close at/after t (the close of the UTC day containing t);
  forward return for horizon k = close[entry+k] / close[entry] - 1. Observations whose
  7-day horizon is not yet complete are dropped. The still-open daily bar is never used.
* Per-observation outcome = cross-sectional MEDIAN forward return over the universe,
  BREADTH = share of symbols with positive forward return, plus BTC forward return.
* "The 7-day forward median cross-sectional return" of a group = the MEAN across the
  group's observations of the per-observation 7d cross-sectional median return (primary
  statistic). The median-of-medians is reported as a secondary statistic only.
* 90% CIs: block bootstrap, blocks = consecutive 7-calendar-day bins, resampled with
  replacement (B = number of blocks), 2000 reps, seed 20261004, percentile 5/95.
* INFORMATIVE test: (a) the 90% CIs of the primary statistic for risk_on and risk_off do
  not overlap on the FULL sample; (b) sign(mean_risk_on - mean_risk_off) is identical in
  the first and second chronological halves (split at the median observation time).
* Naive baseline = sign of `metrics.median_change_pct` (>0 vs <0); it is put through the
  identical test (a)+(b). USEFUL requires INFORMATIVE AND |gap_regime| > |gap_baseline|
  (point estimates, where gap = risk_on - risk_off and pos - neg respectively) AND the
  paired block-bootstrap 90% CI of (|gap_regime| - |gap_baseline|) lies above zero.
* Either sign of the gap counts as "informative" (the label could be a momentum OR a
  contrarian signal); the sign is reported because it matters for use.
* Every group-vs-group comparison and every correlation printed is counted toward the
  multiple-testing caveat at the end.
"""

COMPARISONS = Counter()


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# 1. Regime history from git
# ---------------------------------------------------------------------------
def parse_iso(s: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def load_regime_history() -> tuple[pd.DataFrame, dict]:
    hashes = subprocess.run(
        ["git", "log", "--format=%H", "--", HOT_LIST_PATH],
        capture_output=True, text=True, cwd=ROOT, check=True,
    ).stdout.split()
    stats = {"commits": len(hashes), "unparseable": 0, "no_regime": 0,
             "no_generated_utc": 0, "bad_label": 0, "duplicates": 0}
    rows = {}
    for h in hashes:
        raw = subprocess.run(["git", "show", f"{h}:{HOT_LIST_PATH}"],
                             capture_output=True, text=True, cwd=ROOT).stdout
        try:
            d = json.loads(raw)
        except Exception:
            stats["unparseable"] += 1
            continue
        if not isinstance(d, dict):
            stats["unparseable"] += 1
            continue
        mr = d.get("market_regime")
        if not isinstance(mr, dict) or not mr.get("regime"):
            stats["no_regime"] += 1
            continue
        t = parse_iso(d.get("generated_utc") or mr.get("detected_utc") or "")
        if t is None:
            stats["no_generated_utc"] += 1
            continue
        regime = str(mr.get("regime"))
        if regime not in REGIMES:
            stats["bad_label"] += 1
            continue
        key = t.isoformat()
        if key in rows:
            stats["duplicates"] += 1
            continue
        m = mr.get("metrics") if isinstance(mr.get("metrics"), dict) else {}

        def f(k):
            v = m.get(k)
            try:
                v = float(v)
                return v if math.isfinite(v) else float("nan")
            except Exception:
                return float("nan")

        rows[key] = {
            "t": t,
            "regime": regime,
            "previous_regime": mr.get("previous_regime"),
            "pct_declining": f("pct_declining"),
            "median_change_pct": f("median_change_pct"),
            "btc_change_pct": f("btc_change_pct"),
            "avg_funding_pct": f("avg_funding_pct"),
            "large_decline_count": f("large_decline_count"),
            "commit": h,
        }
    df = pd.DataFrame(list(rows.values())).sort_values("t").reset_index(drop=True)
    stats["usable_raw"] = int(len(df))
    return df, stats


# ---------------------------------------------------------------------------
# 2. Universe + daily klines
# ---------------------------------------------------------------------------
def bybit_get(path: str, params: dict, retries: int = 3) -> dict:
    last = None
    for i in range(retries):
        try:
            r = requests.get(BYBIT + path, params=params, timeout=20)
            r.raise_for_status()
            d = r.json()
            if d.get("retCode") != 0:
                raise RuntimeError(f"retCode={d.get('retCode')} {d.get('retMsg')}")
            return d
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.0 * (i + 1))
    raise RuntimeError(f"Bybit {path} failed after {retries} tries: {last}")


def get_universe(n: int) -> list[str]:
    d = bybit_get("/v5/market/tickers", {"category": "linear"})
    lst = [x for x in d["result"]["list"] if x.get("symbol", "").endswith("USDT")]
    lst.sort(key=lambda x: -float(x.get("turnover24h") or 0))
    syms = [x["symbol"] for x in lst[:n]]
    if "BTCUSDT" not in syms:
        syms.append("BTCUSDT")
    return syms


def fetch_daily(symbol: str) -> pd.DataFrame | None:
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, f"regime_{symbol}_D.json")
    data = None
    if os.path.exists(path):
        age_h = (time.time() - os.path.getmtime(path)) / 3600
        if age_h < CACHE_MAX_AGE_H:
            try:
                with open(path) as fh:
                    data = json.load(fh)
            except Exception:
                data = None
    if data is None:
        try:
            d = bybit_get("/v5/market/kline",
                          {"category": "linear", "symbol": symbol, "interval": "D",
                           "limit": KLINE_DAYS})
        except Exception as e:  # noqa: BLE001
            log(f"  kline fetch failed for {symbol}: {e}")
            return None
        data = {"symbol": symbol, "interval": "D", "fetched_utc": datetime.now(timezone.utc).isoformat(),
                "list": d["result"]["list"]}
        with open(path, "w") as fh:
            json.dump(data, fh, separators=(",", ":"))
        time.sleep(0.1)
    rows = data.get("list") or []
    if len(rows) < 30:
        return None
    df = pd.DataFrame(rows, columns=["start", "open", "high", "low", "close", "volume", "turnover"])
    df["start"] = pd.to_datetime(df["start"].astype("int64"), unit="ms", utc=True)
    for c in ("open", "high", "low", "close"):
        df[c] = df[c].astype(float)
    df = df.sort_values("start").reset_index(drop=True)
    # newest row is the bar in progress -> drop it
    df = df.iloc[:-1].reset_index(drop=True)
    return df[["start", "close"]]


# ---------------------------------------------------------------------------
# 3. Forward returns per observation
# ---------------------------------------------------------------------------
def build_outcomes(obs: pd.DataFrame, closes: dict[str, pd.Series]) -> pd.DataFrame:
    """closes: symbol -> Series indexed by bar start (UTC midnight) of close prices."""
    # Daily bar starting at day D closes at D+1 00:00. First close at/after t is the bar
    # whose start = floor(t to UTC day).
    out = []
    panel = pd.DataFrame(closes).sort_index()  # index = bar start, columns = symbols
    idx = panel.index
    for _, r in obs.iterrows():
        entry_day = pd.Timestamp(r["t"]).floor("D")
        if entry_day not in idx:
            continue
        i = idx.get_loc(entry_day)
        if i + max(HORIZONS) >= len(idx):
            continue  # horizon not yet complete
        base = panel.iloc[i]
        rec = {"t": r["t"], "entry_day": entry_day}
        for k in HORIZONS:
            fwd = panel.iloc[i + k] / base - 1.0
            fwd = fwd.dropna()
            fwd = fwd[np.isfinite(fwd)]
            rec[f"med_{k}"] = float(fwd.median()) * 100 if len(fwd) else float("nan")
            rec[f"breadth_{k}"] = float((fwd > 0).mean()) * 100 if len(fwd) else float("nan")
            rec[f"btc_{k}"] = float(fwd.get("BTCUSDT", float("nan"))) * 100
            rec[f"nsym_{k}"] = int(len(fwd))
        out.append(rec)
    o = pd.DataFrame(out)
    return obs.merge(o, on="t", how="inner")


# ---------------------------------------------------------------------------
# 4. Block bootstrap
# ---------------------------------------------------------------------------
def assign_blocks(df: pd.DataFrame) -> np.ndarray:
    t0 = pd.Timestamp(df["t"].min()).floor("D")
    days = ((pd.to_datetime(df["t"]) - t0).dt.total_seconds() // 86400).astype(int)
    return (days // BLOCK_DAYS).to_numpy()


def block_bootstrap(df: pd.DataFrame, stat_fn, reps: int = BOOT_REPS, seed: int = SEED):
    """stat_fn(sub_df) -> float or array. Returns array of stats (reps x ...)."""
    rng = np.random.default_rng(seed)
    blocks = assign_blocks(df)
    uniq = np.unique(blocks)
    groups = {b: df.index[blocks == b].to_numpy() for b in uniq}
    B = len(uniq)
    res = []
    for _ in range(reps):
        pick = rng.choice(uniq, size=B, replace=True)
        rows = np.concatenate([groups[b] for b in pick])
        res.append(stat_fn(df.loc[rows]))
    return np.asarray(res, dtype=float)


def ci_of(arr: np.ndarray) -> tuple[float, float]:
    arr = arr[np.isfinite(arr)]
    if len(arr) < 20:
        return (float("nan"), float("nan"))
    lo, hi = np.percentile(arr, [(100 - CI) / 2, 100 - (100 - CI) / 2])
    return float(lo), float(hi)


def fmt(x, nd=2) -> str:
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return "n/a"
    return f"{x:+.{nd}f}" if nd else f"{x:.0f}"


def fmtp(x, nd=1) -> str:
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return "n/a"
    return f"{x:.{nd}f}"


# ---------------------------------------------------------------------------
# 5. Group tables
# ---------------------------------------------------------------------------
def group_table(df: pd.DataFrame, col: str, labels: list[str], k: int = PRIMARY_K,
                title: str = "", boot: bool = True) -> tuple[str, dict]:
    """Table: n, mean/median of k-day cross-sectional median return, mean breadth, BTC, with 90% block-bootstrap CIs."""
    mcol, bcol, btcol = f"med_{k}", f"breadth_{k}", f"btc_{k}"
    lines = [f"**{title}**" if title else "", "",
             f"| {col} | n | days | mean {k}d med ret % [90% CI] | median {k}d med ret % [90% CI] | mean breadth % [90% CI] | mean BTC {k}d % |",
             "|---|---|---|---|---|---|---|"]
    summary = {}
    for lab in labels:
        sub = df[df[col] == lab]
        n = int(len(sub))
        ndays = int(sub["entry_day"].nunique()) if n else 0
        if n == 0:
            lines.append(f"| {lab} | 0 | 0 | n/a | n/a | n/a | n/a |")
            summary[lab] = {"n": 0}
            continue
        mean_m = float(sub[mcol].mean()); med_m = float(sub[mcol].median())
        mean_b = float(sub[bcol].mean()); mean_btc = float(sub[btcol].mean())
        ci_mean = ci_med = ci_b = (float("nan"), float("nan"))
        if boot and n >= 5:
            def _st(s, lab=lab):
                ss = s[s[col] == lab]
                if len(ss) < 3:
                    return [np.nan, np.nan, np.nan]
                return [ss[mcol].mean(), ss[mcol].median(), ss[bcol].mean()]
            arr = block_bootstrap(df, _st)
            ci_mean, ci_med, ci_b = ci_of(arr[:, 0]), ci_of(arr[:, 1]), ci_of(arr[:, 2])
        lines.append(
            f"| {lab} | {n} | {ndays} | {fmt(mean_m)} [{fmt(ci_mean[0])}, {fmt(ci_mean[1])}] "
            f"| {fmt(med_m)} [{fmt(ci_med[0])}, {fmt(ci_med[1])}] "
            f"| {fmtp(mean_b)} [{fmtp(ci_b[0])}, {fmtp(ci_b[1])}] | {fmt(mean_btc)} |")
        summary[lab] = {"n": n, "days": ndays, "mean": mean_m, "median": med_m, "breadth": mean_b,
                        "btc": mean_btc, "ci_mean": ci_mean, "ci_median": ci_med, "ci_breadth": ci_b}
    return "\n".join(lines), summary


def horizon_table(df: pd.DataFrame, col: str, labels: list[str]) -> str:
    lines = [f"| {col} | n | " + " | ".join(f"mean med {k}d % / breadth {k}d % / BTC {k}d %" for k in HORIZONS) + " |",
             "|---|---|" + "---|" * len(HORIZONS)]
    for lab in labels:
        sub = df[df[col] == lab]
        if len(sub) == 0:
            lines.append(f"| {lab} | 0 |" + " n/a |" * len(HORIZONS))
            continue
        cells = []
        for k in HORIZONS:
            cells.append(f"{fmt(float(sub[f'med_{k}'].mean()))} / {fmtp(float(sub[f'breadth_{k}'].mean()))} / {fmt(float(sub[f'btc_{k}'].mean()))}")
        lines.append(f"| {lab} | {len(sub)} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def gap_stats(df: pd.DataFrame, col: str, a: str, b: str, k: int = PRIMARY_K) -> dict:
    """gap = mean(a) - mean(b) of k-day cross-sectional median return, with block-bootstrap CI."""
    mcol = f"med_{k}"
    sa, sb = df[df[col] == a], df[df[col] == b]
    out = {"a": a, "b": b, "n_a": int(len(sa)), "n_b": int(len(sb))}
    if len(sa) == 0 or len(sb) == 0:
        out.update({"gap": float("nan"), "ci": (float("nan"), float("nan"))})
        return out
    out["gap"] = float(sa[mcol].mean() - sb[mcol].mean())

    def _st(s):
        x, y = s[s[col] == a][mcol], s[s[col] == b][mcol]
        if len(x) < 3 or len(y) < 3:
            return np.nan
        return x.mean() - y.mean()
    arr = block_bootstrap(df, _st)
    out["ci"] = ci_of(arr)
    out["boot"] = arr
    COMPARISONS["gap tests (A vs B, 7d primary)"] += 1
    return out


def spearman(x: pd.Series, y: pd.Series) -> tuple[float, int]:
    m = x.notna() & y.notna()
    if m.sum() < 5:
        return float("nan"), int(m.sum())
    rx, ry = x[m].rank(method="average"), y[m].rank(method="average")
    if rx.std() == 0 or ry.std() == 0:
        return float("nan"), int(m.sum())
    return float(np.corrcoef(rx.to_numpy(), ry.to_numpy())[0, 1]), int(m.sum())


def spearman_ci(df: pd.DataFrame, xcol: str, ycol: str) -> tuple[float, float]:
    def _st(s):
        r, n = spearman(s[xcol], s[ycol])
        return r
    return ci_of(block_bootstrap(df, _st, reps=500))


def daily_subsample(df: pd.DataFrame) -> pd.DataFrame:
    return df.sort_values("t").groupby("entry_day", as_index=False).first().sort_values("t").reset_index(drop=True)


# ---------------------------------------------------------------------------
# 6. Main
# ---------------------------------------------------------------------------
def main() -> int:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    os.makedirs(REPORT_DIR, exist_ok=True)
    report_path = os.path.join(REPORT_DIR, f"regime_scorecard_{today}.md")
    R: list[str] = []
    R.append(f"# Regime Scorecard — does the market-regime label understand the market?\n")
    R.append(f"_Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')} by `regime_scorecard.py`. Research only: zero Claude calls, zero order logic._\n")
    R.append("## Pre-registered success bar (written before any number was computed)\n")
    R.append(f"> {PRE_REGISTERED_BAR}\n")
    R.append("```\n" + OPERATIONALISATION + "```\n")

    # --- regime history
    log("Reconstructing regime history from git ...")
    obs, hstats = load_regime_history()
    log(f"  {hstats}")

    # --- universe + klines
    log("Fetching universe ...")
    universe = get_universe(UNIVERSE_N)
    log(f"  {len(universe)} symbols; fetching daily klines ...")
    closes: dict[str, pd.Series] = {}
    failed = []
    for i, s in enumerate(universe):
        d = fetch_daily(s)
        if d is None:
            failed.append(s)
            continue
        closes[s] = pd.Series(d["close"].to_numpy(), index=d["start"])
        if (i + 1) % 10 == 0:
            log(f"  {i + 1}/{len(universe)}")
    if "BTCUSDT" not in closes:
        log("FATAL: no BTCUSDT klines")
        return 1
    panel_first = min(s.index.min() for s in closes.values())
    panel_last = max(s.index.max() for s in closes.values())

    # --- outcomes
    df = build_outcomes(obs, closes)
    df = df.sort_values("t").reset_index(drop=True)
    if len(df) < 20:
        R.append(f"\n**FATAL: only {len(df)} usable observations — nothing to test.**\n")
        with open(report_path, "w") as fh:
            fh.write("\n".join(R))
        return 1
    df["fresh"] = (df["previous_regime"].notna()) & (df["previous_regime"] != df["regime"])
    df["base_med"] = np.where(df["median_change_pct"] > 0, "med24h>0",
                              np.where(df["median_change_pct"] < 0, "med24h<0", "med24h=0/nan"))
    df["base_btc"] = np.where(df["btc_change_pct"] > 0, "btc24h>0",
                              np.where(df["btc_change_pct"] < 0, "btc24h<0", "btc24h=0/nan"))
    t_split = df["t"].iloc[len(df) // 2]
    df["half"] = np.where(df["t"] < t_split, "H1", "H2")
    daily = daily_subsample(df)

    # --- data section
    R.append("## Data\n")
    R.append(f"- hot_list.json commits scanned: **{hstats['commits']}**; unparseable {hstats['unparseable']}; "
             f"without `market_regime` {hstats['no_regime']}; missing timestamp {hstats['no_generated_utc']}; "
             f"bad label {hstats['bad_label']}; duplicate `generated_utc` {hstats['duplicates']}.")
    R.append(f"- Regime observations with a label: **{hstats['usable_raw']}** spanning "
             f"{obs['t'].min():%Y-%m-%d %H:%M} → {obs['t'].max():%Y-%m-%d %H:%M} UTC.")
    R.append(f"- Usable after requiring a complete 7-day forward window: **{len(df)}** observations on "
             f"**{df['entry_day'].nunique()}** distinct entry days, {df['t'].min():%Y-%m-%d} → {df['t'].max():%Y-%m-%d} UTC "
             f"(median {len(df) / max(df['entry_day'].nunique(), 1):.1f} obs/day; the schedule is ~2h so gaps = CI outages).")
    R.append(f"- Daily-subsample (first observation per entry day): **{len(daily)}** observations.")
    R.append(f"- Universe: top {UNIVERSE_N} USDT linear perps by turnover24h on {today} (+BTCUSDT) — "
             f"**survivorship bias**: coins that were liquid in May–Sep but have since faded are missing, and coins "
             f"that are hot now were not necessarily tradeable then. {len(closes)} symbols with ≥30 daily bars; failed/thin: {failed or 'none'}.")
    R.append(f"- Daily klines: {panel_first:%Y-%m-%d} → {panel_last:%Y-%m-%d} (closed bars only; the open bar is dropped). "
             f"Symbols per 7d cross-section: min {int(df['nsym_7'].min())}, median {int(df['nsym_7'].median())}.")
    R.append(f"- Chronological split at {t_split:%Y-%m-%d %H:%M} UTC (H1 n={int((df['half'] == 'H1').sum())}, H2 n={int((df['half'] == 'H2').sum())}).")
    R.append(f"- Block bootstrap: {BLOCK_DAYS}-day blocks, {int(len(np.unique(assign_blocks(df))))} blocks, {BOOT_REPS} reps, seed {SEED}.\n")

    # label distribution
    R.append("### Label distribution\n")
    R.append("| regime | n obs | share % | n days (any obs) | fresh transitions |")
    R.append("|---|---|---|---|---|")
    for lab in REGIMES:
        sub = df[df["regime"] == lab]
        R.append(f"| {lab} | {len(sub)} | {100 * len(sub) / len(df):.1f} | {sub['entry_day'].nunique()} | {int(sub['fresh'].sum())} |")
    R.append("")
    R.append("Unconditional base rates (all observations): "
             f"mean 7d med ret {fmt(float(df['med_7'].mean()))}%, median {fmt(float(df['med_7'].median()))}%, "
             f"mean breadth {fmtp(float(df['breadth_7'].mean()))}%, mean BTC 7d {fmt(float(df['btc_7'].mean()))}%.\n")

    # --- by regime, 7d primary
    R.append("## A. By regime label — 7-day horizon (primary), all observations\n")
    tbl, full_sum = group_table(df, "regime", list(REGIMES), 7, "All observations (every ~2h), 7d forward")
    COMPARISONS["group tables (4-row, with CIs)"] += 1
    R.append(tbl + "\n")
    R.append("### A2. Same, daily subsample (one observation per entry day)\n")
    tbl, daily_sum = group_table(daily, "regime", list(REGIMES), 7, "Daily subsample, 7d forward")
    COMPARISONS["group tables (4-row, with CIs)"] += 1
    R.append(tbl + "\n")
    R.append("### A3. All horizons (point estimates only)\n")
    R.append(horizon_table(df, "regime", list(REGIMES)) + "\n")
    COMPARISONS["horizon point-estimate cells"] += len(REGIMES) * len(HORIZONS) * 3

    # primary gap
    gap_full = gap_stats(df, "regime", "risk_on", "risk_off", 7)
    gap_daily = gap_stats(daily, "regime", "risk_on", "risk_off", 7)
    R.append("### A4. The pre-registered contrast: risk_on − risk_off, 7d mean cross-sectional median return\n")
    R.append("| sample | n risk_on | n risk_off | gap (pp) | 90% block-bootstrap CI | CIs of the two groups overlap? |")
    R.append("|---|---|---|---|---|---|")

    def overlap(s, a="risk_on", b="risk_off"):
        ca, cb = s.get(a, {}).get("ci_mean"), s.get(b, {}).get("ci_mean")
        if not ca or not cb or any(not math.isfinite(v) for v in ca + cb):
            return None
        return not (ca[1] < cb[0] or cb[1] < ca[0])
    ov_full, ov_daily = overlap(full_sum), overlap(daily_sum)
    R.append(f"| all obs | {gap_full['n_a']} | {gap_full['n_b']} | {fmt(gap_full['gap'])} | [{fmt(gap_full['ci'][0])}, {fmt(gap_full['ci'][1])}] | {'n/a' if ov_full is None else ('YES' if ov_full else 'NO')} |")
    R.append(f"| daily subsample | {gap_daily['n_a']} | {gap_daily['n_b']} | {fmt(gap_daily['gap'])} | [{fmt(gap_daily['ci'][0])}, {fmt(gap_daily['ci'][1])}] | {'n/a' if ov_daily is None else ('YES' if ov_daily else 'NO')} |")
    R.append("")

    # --- halves
    R.append("## B. Chronological halves — by regime, 7d\n")
    half_sum = {}
    half_gap = {}
    for h in ("H1", "H2"):
        sub = df[df["half"] == h].reset_index(drop=True)
        tbl, s = group_table(sub, "regime", list(REGIMES), 7,
                             f"{h}: {sub['t'].min():%Y-%m-%d} → {sub['t'].max():%Y-%m-%d} (n={len(sub)})")
        COMPARISONS["group tables (4-row, with CIs)"] += 1
        half_sum[h] = s
        half_gap[h] = gap_stats(sub, "regime", "risk_on", "risk_off", 7) if len(sub) else {"gap": float("nan"), "ci": (np.nan, np.nan), "n_a": 0, "n_b": 0}
        R.append(tbl + "\n")
    R.append("| half | n risk_on | n risk_off | gap risk_on − risk_off (pp) | 90% CI | sign |")
    R.append("|---|---|---|---|---|---|")
    for h in ("H1", "H2"):
        g = half_gap[h]
        sgn = "n/a" if not math.isfinite(g["gap"]) else ("+" if g["gap"] > 0 else ("−" if g["gap"] < 0 else "0"))
        R.append(f"| {h} | {g['n_a']} | {g['n_b']} | {fmt(g['gap'])} | [{fmt(g['ci'][0])}, {fmt(g['ci'][1])}] | {sgn} |")
    R.append("")

    # --- naive baselines
    R.append("## C. Naive baselines — the raw inputs that feed the label\n")
    base_labels_med = ["med24h<0", "med24h>0"]
    base_labels_btc = ["btc24h<0", "btc24h>0"]
    tbl, base_med_sum = group_table(df, "base_med", base_labels_med + ["med24h=0/nan"], 7, "Sign of metrics.median_change_pct (the breadth-median input), 7d forward, all obs")
    COMPARISONS["group tables (baseline, with CIs)"] += 1
    R.append(tbl + "\n")
    tbl, _ = group_table(daily, "base_med", base_labels_med, 7, "Same, daily subsample")
    COMPARISONS["group tables (baseline, with CIs)"] += 1
    R.append(tbl + "\n")
    tbl, base_btc_sum = group_table(df, "base_btc", base_labels_btc + ["btc24h=0/nan"], 7, "Sign of metrics.btc_change_pct, 7d forward, all obs")
    COMPARISONS["group tables (baseline, with CIs)"] += 1
    R.append(tbl + "\n")
    R.append("All horizons (point estimates):\n")
    R.append(horizon_table(df, "base_med", base_labels_med) + "\n")
    R.append(horizon_table(df, "base_btc", base_labels_btc) + "\n")
    COMPARISONS["horizon point-estimate cells"] += 4 * len(HORIZONS) * 3

    gap_base = gap_stats(df, "base_med", "med24h>0", "med24h<0", 7)
    gap_base_btc = gap_stats(df, "base_btc", "btc24h>0", "btc24h<0", 7)
    base_half_gap = {}
    for h in ("H1", "H2"):
        sub = df[df["half"] == h].reset_index(drop=True)
        base_half_gap[h] = gap_stats(sub, "base_med", "med24h>0", "med24h<0", 7)
    ov_base = overlap(base_med_sum, "med24h>0", "med24h<0")
    R.append("### C2. Baseline contrast: med24h>0 − med24h<0, 7d mean cross-sectional median return\n")
    R.append("| sample | n pos | n neg | gap (pp) | 90% CI | group CIs overlap? |")
    R.append("|---|---|---|---|---|---|")
    R.append(f"| all obs | {gap_base['n_a']} | {gap_base['n_b']} | {fmt(gap_base['gap'])} | [{fmt(gap_base['ci'][0])}, {fmt(gap_base['ci'][1])}] | {'n/a' if ov_base is None else ('YES' if ov_base else 'NO')} |")
    for h in ("H1", "H2"):
        g = base_half_gap[h]
        R.append(f"| {h} | {g['n_a']} | {g['n_b']} | {fmt(g['gap'])} | [{fmt(g['ci'][0])}, {fmt(g['ci'][1])}] | — |")
    R.append(f"| (btc sign, all obs) | {gap_base_btc['n_a']} | {gap_base_btc['n_b']} | {fmt(gap_base_btc['gap'])} | [{fmt(gap_base_btc['ci'][0])}, {fmt(gap_base_btc['ci'][1])}] | — |")
    R.append("")

    # paired comparison |gap_regime| - |gap_base|
    def _paired(s):
        a = s[s["regime"] == "risk_on"]["med_7"]; b = s[s["regime"] == "risk_off"]["med_7"]
        c = s[s["base_med"] == "med24h>0"]["med_7"]; d = s[s["base_med"] == "med24h<0"]["med_7"]
        if min(len(a), len(b), len(c), len(d)) < 3:
            return np.nan
        return abs(a.mean() - b.mean()) - abs(c.mean() - d.mean())
    paired_arr = block_bootstrap(df, _paired)
    paired_ci = ci_of(paired_arr)
    paired_point = abs(gap_full["gap"]) - abs(gap_base["gap"]) if math.isfinite(gap_full["gap"]) and math.isfinite(gap_base["gap"]) else float("nan")
    COMPARISONS["gap tests (A vs B, 7d primary)"] += 1
    R.append(f"Paired block-bootstrap of |gap_regime| − |gap_baseline| (7d): point {fmt(paired_point)} pp, 90% CI [{fmt(paired_ci[0])}, {fmt(paired_ci[1])}].\n")

    # --- Spearman
    R.append("## D. Spearman rank correlation of each regime metric with forward outcomes (all obs)\n")
    R.append("| metric | n | ρ vs 7d med ret [90% CI] | ρ vs 7d breadth [90% CI] | ρ vs 7d BTC | ρ vs 3d med ret | ρ vs 1d med ret |")
    R.append("|---|---|---|---|---|---|---|")
    for m in ("pct_declining", "median_change_pct", "btc_change_pct", "avg_funding_pct", "large_decline_count"):
        r7, n = spearman(df[m], df["med_7"]); c7 = spearman_ci(df, m, "med_7")
        rb, _ = spearman(df[m], df["breadth_7"]); cb = spearman_ci(df, m, "breadth_7")
        rbtc, _ = spearman(df[m], df["btc_7"])
        r3, _ = spearman(df[m], df["med_3"]); r1, _ = spearman(df[m], df["med_1"])
        COMPARISONS["spearman correlations"] += 5
        R.append(f"| {m} | {n} | {fmt(r7, 3)} [{fmt(c7[0], 2)}, {fmt(c7[1], 2)}] | {fmt(rb, 3)} [{fmt(cb[0], 2)}, {fmt(cb[1], 2)}] | {fmt(rbtc, 3)} | {fmt(r3, 3)} | {fmt(r1, 3)} |")
    # ordinal regime code
    code = df["regime"].map({"risk_off": 0, "cautious": 1, "neutral": 2, "risk_on": 3}).astype(float)
    r7, n = spearman(code, df["med_7"]); c7 = spearman_ci(df.assign(_code=code), "_code", "med_7")
    rb, _ = spearman(code, df["breadth_7"]); cb = spearman_ci(df.assign(_code=code), "_code", "breadth_7")
    rbtc, _ = spearman(code, df["btc_7"]); r3, _ = spearman(code, df["med_3"]); r1, _ = spearman(code, df["med_1"])
    COMPARISONS["spearman correlations"] += 5
    R.append(f"| regime (ordinal 0..3) | {n} | {fmt(r7, 3)} [{fmt(c7[0], 2)}, {fmt(c7[1], 2)}] | {fmt(rb, 3)} [{fmt(cb[0], 2)}, {fmt(cb[1], 2)}] | {fmt(rbtc, 3)} | {fmt(r3, 3)} | {fmt(r1, 3)} |")
    R.append("\nNote: the regime metrics are strongly inter-correlated by construction (pct_declining and median_change_pct are two views of the same 50-ticker cross-section), so these rows are not independent tests. The 1d/3d columns are shown for completeness only; the pre-registered horizon is 7d.\n")

    # --- Transitions
    R.append("## E. Transitions — fresh regime change vs persistent label, 7d\n")
    df["regime_fresh"] = df["regime"] + np.where(df["fresh"], " (fresh)", " (persistent)")
    labs = [f"{r} ({s})" for r in REGIMES for s in ("fresh", "persistent")]
    tbl, trans_sum = group_table(df, "regime_fresh", labs, 7, "Observation where regime != previous_regime (fresh) vs unchanged (persistent)")
    COMPARISONS["group tables (transitions, with CIs)"] += 1
    R.append(tbl + "\n")
    R.append("Fresh-vs-persistent gap within label (7d mean med ret, pp, 90% CI):\n")
    R.append("| regime | n fresh | n persistent | fresh − persistent | 90% CI |")
    R.append("|---|---|---|---|---|")
    for r in REGIMES:
        g = gap_stats(df, "regime_fresh", f"{r} (fresh)", f"{r} (persistent)", 7)
        R.append(f"| {r} | {g['n_a']} | {g['n_b']} | {fmt(g['gap'])} | [{fmt(g['ci'][0])}, {fmt(g['ci'][1])}] |")
    gf = gap_stats(df, "regime_fresh", "risk_on (fresh)", "risk_off (fresh)", 7)
    R.append(f"\nFresh risk_on − fresh risk_off (7d): {fmt(gf['gap'])} pp, 90% CI [{fmt(gf['ci'][0])}, {fmt(gf['ci'][1])}] (n {gf['n_a']} vs {gf['n_b']}). "
             "Fresh transitions are few and clustered, so treat these rows as descriptive.\n")
    # how long do regimes last
    runs = []
    cur, start, cnt = None, None, 0
    for _, r in df.iterrows():
        if r["regime"] != cur:
            if cur is not None:
                runs.append((cur, cnt))
            cur, cnt = r["regime"], 1
        else:
            cnt += 1
    if cur is not None:
        runs.append((cur, cnt))
    runs_df = pd.DataFrame(runs, columns=["regime", "obs"])
    R.append("Run lengths (consecutive observations with the same label; ~2h each when CI was healthy):\n")
    R.append("| regime | runs | median run (obs) | max run (obs) |")
    R.append("|---|---|---|---|")
    for r in REGIMES:
        s = runs_df[runs_df["regime"] == r]["obs"]
        R.append(f"| {r} | {len(s)} | {fmtp(float(s.median()), 0) if len(s) else 'n/a'} | {int(s.max()) if len(s) else 'n/a'} |")
    R.append("")

    # --- Verdict
    R.append("## F. Verdict — pre-registered bar applied mechanically\n")
    ci_on = full_sum.get("risk_on", {}).get("ci_mean", (np.nan, np.nan))
    ci_off = full_sum.get("risk_off", {}).get("ci_mean", (np.nan, np.nan))
    cond_a = (ov_full is False)
    s1, s2 = half_gap["H1"]["gap"], half_gap["H2"]["gap"]
    cond_b = all(math.isfinite(v) for v in (s1, s2)) and np.sign(s1) == np.sign(s2) and s1 != 0
    informative = bool(cond_a and cond_b)
    # baseline same test
    bs1, bs2 = base_half_gap["H1"]["gap"], base_half_gap["H2"]["gap"]
    base_cond_a = (ov_base is False)
    base_cond_b = all(math.isfinite(v) for v in (bs1, bs2)) and np.sign(bs1) == np.sign(bs2) and bs1 != 0
    base_informative = bool(base_cond_a and base_cond_b)
    beats_point = math.isfinite(paired_point) and paired_point > 0
    beats_ci = math.isfinite(paired_ci[0]) and paired_ci[0] > 0
    useful = bool(informative and beats_point and beats_ci)
    verdict = "USEFUL" if useful else ("INFORMATIVE (but not USEFUL)" if informative else "NOT INFORMATIVE")

    R.append(f"**VERDICT: {verdict}**\n")
    R.append("| check | value | pass? |")
    R.append("|---|---|---|")
    R.append(f"| (a) risk_on 7d mean med ret 90% CI | [{fmt(ci_on[0])}, {fmt(ci_on[1])}] pp (n={full_sum.get('risk_on', {}).get('n', 0)}) | — |")
    R.append(f"| (a) risk_off 7d mean med ret 90% CI | [{fmt(ci_off[0])}, {fmt(ci_off[1])}] pp (n={full_sum.get('risk_off', {}).get('n', 0)}) | — |")
    R.append(f"| (a) CIs non-overlapping | overlap = {'n/a' if ov_full is None else ov_full}; gap {fmt(gap_full['gap'])} pp, gap CI [{fmt(gap_full['ci'][0])}, {fmt(gap_full['ci'][1])}] | {'PASS' if cond_a else 'FAIL'} |")
    R.append(f"| (b) sign of gap same in both halves | H1 {fmt(s1)} pp, H2 {fmt(s2)} pp | {'PASS' if cond_b else 'FAIL'} |")
    R.append(f"| INFORMATIVE = (a) AND (b) | | {'YES' if informative else 'NO'} |")
    R.append(f"| baseline (sign of median_change_pct) on the same test | CIs non-overlap: {'n/a' if ov_base is None else (not ov_base)}; halves {fmt(bs1)} / {fmt(bs2)} pp → {'passes' if base_informative else 'fails'} | — |")
    R.append(f"| regime beats baseline: \\|gap_regime\\| − \\|gap_base\\| | point {fmt(paired_point)} pp (regime {fmt(abs(gap_full['gap']) if math.isfinite(gap_full['gap']) else float('nan'))} vs base {fmt(abs(gap_base['gap']) if math.isfinite(gap_base['gap']) else float('nan'))}); paired 90% CI [{fmt(paired_ci[0])}, {fmt(paired_ci[1])}] | {'PASS' if (beats_point and beats_ci) else 'FAIL'} |")
    R.append(f"| USEFUL = INFORMATIVE AND beats baseline | | {'YES' if useful else 'NO'} |")
    R.append("")
    if math.isfinite(gap_full["gap"]):
        direction = ("risk_on observations were followed by HIGHER 7d cross-sectional returns than risk_off (momentum-type reading)"
                     if gap_full["gap"] > 0 else
                     "risk_on observations were followed by LOWER 7d cross-sectional returns than risk_off (contrarian/mean-reversion reading)")
        R.append(f"Direction of the point estimate: {direction}. Daily-subsample gap {fmt(gap_daily['gap'])} pp, CI [{fmt(gap_daily['ci'][0])}, {fmt(gap_daily['ci'][1])}].\n")

    # --- multiple testing
    total = sum(COMPARISONS.values())
    R.append("## G. Multiple-testing caveat\n")
    R.append(f"This report printed **{total}** numbers that could be read as a test (breakdown below). "
             "At a 90% CI, roughly 1 in 10 null comparisons will look 'significant' by chance, so only the ONE "
             "pre-registered contrast (risk_on vs risk_off, 7d, mean of cross-sectional medians, full sample + halves) "
             "carries the verdict; everything else is descriptive and would need a fresh out-of-sample period to confirm. "
             "Observations also overlap heavily (every ~2h with a 7-day horizon → each 7-day block is effectively "
             "ONE independent draw), which is why the block bootstrap and the daily subsample exist; even so the effective "
             f"sample is on the order of {int(len(np.unique(assign_blocks(df))))} independent blocks, not {len(df)} observations.\n")
    R.append("| category | count |")
    R.append("|---|---|")
    for k, v in COMPARISONS.items():
        R.append(f"| {k} | {v} |")
    R.append("")
    R.append("## H. Caveats\n")
    R.append("- Survivorship: universe = top-60 by turnover TODAY. Cross-sectional medians are robust to a few outliers, but the sample systematically includes coins that survived/grew.")
    R.append("- The regime label is computed from a different (top-50 at the time) ticker set than the forward universe; this is deliberate — the question is whether the label generalises to the tradeable universe.")
    R.append("- One summer-to-autumn 2026 window: ~4.5 months, dominated by whatever macro regime prevailed; any result here is a single-period observation, not a general law.")
    R.append("- Daily entry at the UTC close after t: a label seen at 02:00 UTC waits ~22h before the measured entry; this is realizable but smooths away intraday information.")
    R.append("- No costs are modelled — this is a label-quality test, not a strategy backtest.")
    R.append("")

    with open(report_path, "w") as fh:
        fh.write("\n".join(R))
    log(f"Report written: {report_path}")

    # compact machine-readable summary (native types only)
    summary = {
        "usable_obs": int(len(df)), "entry_days": int(df["entry_day"].nunique()),
        "date_range": [df["t"].min().isoformat(), df["t"].max().isoformat()],
        "verdict": verdict,
        "gap_risk_on_minus_risk_off_7d_pp": None if not math.isfinite(gap_full["gap"]) else round(gap_full["gap"], 3),
        "gap_ci": [None if not math.isfinite(v) else round(v, 3) for v in gap_full["ci"]],
        "ci_risk_on": [None if not math.isfinite(v) else round(v, 3) for v in ci_on],
        "ci_risk_off": [None if not math.isfinite(v) else round(v, 3) for v in ci_off],
        "half_gaps": [None if not math.isfinite(v) else round(v, 3) for v in (s1, s2)],
        "baseline_gap_7d_pp": None if not math.isfinite(gap_base["gap"]) else round(gap_base["gap"], 3),
        "paired_regime_minus_baseline": [None if not math.isfinite(v) else round(v, 3) for v in (paired_point, *paired_ci)],
        "by_regime_7d": {r: {k: (None if isinstance(v, float) and not math.isfinite(v) else (list(v) if isinstance(v, tuple) else v))
                             for k, v in full_sum.get(r, {}).items()} for r in REGIMES},
        "comparisons": int(total), "report": report_path,
    }
    print(json.dumps(summary, indent=1, default=float))
    return 0


if __name__ == "__main__":
    sys.exit(main())
