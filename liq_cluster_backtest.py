"""
liq_cluster_backtest.py — FORK A backtest harness (2026-08-09, run in ~2-4 weeks).

Tests THE hypothesis the whole liquidation-collection experiment exists for:
does proximity to a LIQUIDATION CLUSTER predict trade outcome?

Idea: large liquidation volume piles up at specific prices (magnets). A forced
long-liquidation is a market SELL (longs blown up = capitulation, bullish
reversal fuel); a forced short-liquidation is a market BUY (shorts squeezed =
exhaustion, bearish reversal fuel). So the DIRECTION-ALIGNED test is:
  - LONG  entry near a big SELL-liq cluster (longs just flushed below) -> good?
  - SHORT entry near a big BUY-liq  cluster (shorts just squeezed above) -> good?

Method mirrors the S/R + downtrend prototypes that already passed/failed:
tag historical trend_pullback trades with distance-to-nearest-aligned-cluster,
partition outcomes, train/test on a chronological split. NO-LOOKAHEAD: the
cluster map for a trade at time T is built ONLY from liquidations in
[T - window, T]. Promote to a live feature ONLY if it survives OOS.

DATA: point --data-dir at a folder of the collector's JSONL files. Get them via
GitHub Actions -> the "Liquidation Collector" runs -> download each
`liquidations-<run_id>` artifact, unzip, drop all liq_*.jsonl into one dir:
    gh run download --name 'liquidations-*'   # (or download via the Actions UI)
Then:
    python liq_cluster_backtest.py --data-dir ./liq_data --interval 240

This is an ANALYSIS tool — zero trading decisions, reads logs only (CORE PRINCIPLE).
"""
import argparse, json, glob, os, bisect, statistics as st
from collections import defaultdict

import historical_backtester as hb

SYMBOLS = ["ADAUSDT","XRPUSDT","SOLUSDT","BTCUSDT","ETHUSDT","DOGEUSDT","SUIUSDT",
           "XLMUSDT","ENAUSDT","HBARUSDT","TRXUSDT","NEARUSDT","OPUSDT","ARBUSDT",
           "INJUSDT","LINKUSDT","AVAXUSDT","LTCUSDT","TONUSDT","WLDUSDT"]
COST = 0.072   # ~fixed round-trip cost in R (matches the other prototypes)


# ── liquidation data ─────────────────────────────────────────────────────────
def load_liquidations(data_dir):
    """Return {symbol: sorted list of (t_ms, side, price, notional)}. Dedups exact
    repeats (CI run boundaries / any Mac+CI overlap can double-log an event)."""
    per = defaultdict(set)
    files = sorted(glob.glob(os.path.join(data_dir, "*.jsonl")))
    for fp in files:
        with open(fp) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                    per[r["sym"]].add((int(r["t"]), r.get("side"),
                                       round(float(r["price"]), 10),
                                       round(float(r["notional"]), 2)))
                except Exception:
                    continue
    out = {}
    for sym, s in per.items():
        out[sym] = sorted(s)  # sort by t_ms
    return out, files


def build_clusters(events, t_lo, t_hi, bin_w, min_frac):
    """Cluster liquidations in (t_lo, t_hi] into price magnets.
    events: sorted [(t,side,price,notional)]. bin_w: price bin width (abs).
    Returns [{price, notional, sell_notional, buy_notional}] for bins holding
    >= min_frac of the window's total liquidation notional."""
    lo = bisect.bisect_right(events, (t_lo, chr(0x10ffff), 0, 0))
    hi = bisect.bisect_right(events, (t_hi, chr(0x10ffff), float("inf"), float("inf")))
    window = events[lo:hi]
    if not window or bin_w <= 0:
        return []
    bins = defaultdict(lambda: {"n": 0.0, "sell": 0.0, "buy": 0.0, "pw": 0.0})
    total = 0.0
    for _, side, price, notional in window:
        b = round(price / bin_w)
        d = bins[b]
        d["n"] += notional
        d["pw"] += price * notional
        if side == "Sell":
            d["sell"] += notional
        else:
            d["buy"] += notional
        total += notional
    if total <= 0:
        return []
    out = []
    for b, d in bins.items():
        if d["n"] >= min_frac * total:
            out.append({"price": d["pw"] / d["n"] if d["n"] else b * bin_w,
                        "notional": d["n"], "sell_notional": d["sell"],
                        "buy_notional": d["buy"]})
    return out


def nearest_aligned(clusters, entry, direction, atr):
    """Distance (in ATR) to the nearest DIRECTION-ALIGNED capitulation cluster:
      long  -> sell-dominant cluster at/below entry (longs flushed)
      short -> buy-dominant  cluster at/above entry (shorts squeezed)
    Returns (dist_atr, notional) or (None, 0)."""
    if atr <= 0:
        return (None, 0.0)
    best = None
    for c in clusters:
        sell_dom = c["sell_notional"] >= c["buy_notional"]
        if direction == "long" and sell_dom and c["price"] <= entry + 0.2 * atr:
            d = abs(c["price"] - entry) / atr
        elif direction == "short" and (not sell_dom) and c["price"] >= entry - 0.2 * atr:
            d = abs(c["price"] - entry) / atr
        else:
            continue
        if best is None or d < best[0]:
            best = (d, c["notional"])
    return best if best else (None, 0.0)


# ── stats ─────────────────────────────────────────────────────────────────────
def stats(rs):
    n = len(rs)
    if not n:
        return (0, 0, 0.0, 0.0)
    wr = round(100 * sum(1 for t in rs if t["actual_rr"] > 0) / n)
    e = st.mean(t["actual_rr"] for t in rs)
    return (n, wr, round(e - COST, 3), round(e, 3))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True, help="folder of collector *.jsonl files")
    ap.add_argument("--interval", default="240", help="kline interval (240=4h, 60=1h)")
    ap.add_argument("--target", type=float, default=1.5)
    ap.add_argument("--window-hours", type=float, default=48.0, help="trailing liq window")
    ap.add_argument("--bin-atr", type=float, default=0.5, help="price bin width in ATR")
    ap.add_argument("--cluster-min-frac", type=float, default=0.05,
                    help="a bin is a cluster if >= this fraction of window notional")
    ap.add_argument("--split", type=float, default=0.60, help="train fraction (chrono)")
    args = ap.parse_args()

    ivl_ms = int(args.interval) * 60 * 1000
    win_ms = int(args.window_hours * 3600 * 1000)

    liq, files = load_liquidations(args.data_dir)
    print(f"Loaded {len(files)} file(s); liquidation data for {len(liq)} symbols.")
    if not liq:
        print("NO liquidation data found — let the collector accumulate, then retry.")
        return
    # coverage
    spans = {s: (ev[0][0], ev[-1][0]) for s, ev in liq.items() if ev}
    if spans:
        cov_days = max((hi - lo) for lo, hi in spans.values()) / 86400000
        tot = sum(len(ev) for ev in liq.values())
        print(f"Total liq events: {tot:,} | widest coverage: {cov_days:.1f} days")
        if cov_days < 10:
            print("⚠ coverage < 10 days — results will be thin/underpowered; treat as a smoke test.")

    SIGS = {"trend_pullback_long": hb.signal_trend_pullback_long,
            "trend_pullback_short": hb.signal_trend_pullback_short}
    by_bucket = defaultdict(list)
    all_tagged = []
    covered = 0

    for sym in SYMBOLS:
        ev = liq.get(sym)
        if not ev:
            continue
        cov_lo, cov_hi = ev[0][0], ev[-1][0]
        try:
            candles = hb.fetch_klines(sym, args.interval, limit=1000, use_cache=True)
        except Exception:
            continue
        if not candles or len(candles) < 200:
            continue
        df = hb.compute_indicators_df(candles)
        covered += 1
        for name, fn in SIGS.items():
            last = -13
            for i in range(50, len(df) - 48):
                if i - last < 12:
                    continue
                T = int(df.iloc[i]["timestamp"])
                # only test trades whose entry AND its trailing window fall inside
                # the liquidation-data coverage (no-lookahead + real coverage)
                if T - win_ms < cov_lo or T > cov_hi:
                    continue
                s = fn(df, i)
                if s is None:
                    continue
                last = i
                res = hb.evaluate_forward(df, i, s, args.target, 48)
                if res is None:
                    continue
                atr = float(df.iloc[i]["atr_14"])
                bin_w = args.bin_atr * atr
                clusters = build_clusters(ev, T - win_ms, T, bin_w, args.cluster_min_frac)
                d, notional = nearest_aligned(clusters, s["entry"], s["direction"], atr)
                if d is None:
                    b = "noAlignedCluster"
                elif d <= 0.5:
                    b = "at(<=0.5A)"
                elif d <= 1.5:
                    b = "near(0.5-1.5A)"
                else:
                    b = "far(>1.5A)"
                res["_bucket"] = b
                res["_pos"] = i / len(df)
                by_bucket[b].append(res)
                all_tagged.append(res)

    print(f"\nSymbols with klines+liq overlap: {covered} | tagged trades: {len(all_tagged)}")
    if not all_tagged:
        print("No trades fell inside the liquidation coverage window yet. Retry once more data exists.")
        return

    a = stats(all_tagged)
    print(f"ALL: n={a[0]} wr{a[1]} net {a[2]:+.3f}\n")
    print("BY distance-to-ALIGNED-liq-cluster (long=sell-cluster below / short=buy-cluster above):")
    for b in ["at(<=0.5A)", "near(0.5-1.5A)", "far(>1.5A)", "noAlignedCluster"]:
        s = stats(by_bucket[b])
        if s[0]:
            print(f"  {b:<20} n={s[0]:>4} wr{s[1]:>3} net {s[2]:+.3f}")

    # train/test the "near an aligned cluster" cut, if there's enough data
    near = [t for t in all_tagged if t["_bucket"] in ("at(<=0.5A)", "near(0.5-1.5A)")]
    def seg(rs, frac):
        return (stats([t for t in rs if t["_pos"] < frac]),
                stats([t for t in rs if t["_pos"] >= frac]))
    print("\nTRAIN/TEST (chrono split) — is 'near an aligned liq cluster' better OOS?")
    if len(near) < 30 or len(all_tagged) < 60:
        print(f"  too few trades for a credible split (near={len(near)}, all={len(all_tagged)}). "
              "Need ~30+ near / ~60+ total — keep collecting.")
    else:
        for lbl, rs in [("ALL", all_tagged), ("NEAR-aligned", near)]:
            tr, te = seg(rs, args.split)
            print(f"  {lbl:<13} TRAIN net {tr[2]:+.3f}(n={tr[0]})  TEST net {te[2]:+.3f}(n={te[0]})")
        print("\n  VERDICT: promote to a live feature ONLY if NEAR-aligned TEST net clearly "
              "beats ALL TEST net AND is >= ~0 — else it's another empty lever (fork C).")


if __name__ == "__main__":
    main()
