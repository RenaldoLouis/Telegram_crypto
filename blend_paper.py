"""blend_paper.py — FORWARD PAPER TEST #3 (2026-10-25): the edge search's 4-sleeve blend at 10% volatility.

PAPER ONLY: no order API, no API key, no hosted model. Pre-registration:
`logs/backtest_reports/prereg_blend_paper_20261025.md`.

The book is edge_search's frozen variant `volman_combo_4_sleeves` (vol-managed BTC trend + funding
carry 7d + cross-sectional momentum 28d + BTC-hedged new-listing short, equal risk, the whole book
vol-targeted) at half its DISCOVERY 20%-vol scale = a 10%-volatility book. Weights come from the SAME
functions as the backtest; their source is fingerprinted (FROZEN_CODE) and a run refuses if it changed.

Daily, shortly after 00:00 UTC (scan-keeper dispatch + backup crons), `run`:
  1. fetches the last 200 days of daily bars + funding for every trading crypto perp (+ any held symbol);
  2. records weights for every closed day not yet recorded (≤ 7 back, each from data cut at that day);
  3. scores every recorded day: the previous day's RECORDED weights × the day's returns − funding −
     trading costs (the accounting of edge_search.run_weights, asserted);
  4. sends one Telegram message when a Mon–Sun week (and, at month end, a month) completes.

Usage:
    venv/bin/python blend_paper.py run [--no-telegram]
    venv/bin/python blend_paper.py status
"""

import argparse
import hashlib
import inspect
import json
import math
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import edge_data as ed
import edge_search as es

BASE_DIR = Path(__file__).resolve().parent
OUT_DIR = BASE_DIR / "logs" / "blend_paper"
LIVE_CACHE = BASE_DIR / "logs" / "backtest_cache" / "blend_live"
DAY_MS = ed.DAY_MS

VERSION = "blend4_v1"
VARIANT = "volman_combo_4_sleeves"
DISCOVERY_SCALE_20V = 1.039297             # edge_finalists.json, scale to 20% vol on DISCOVERY
TARGET_VOL = 0.10
SCALE = DISCOVERY_SCALE_20V * TARGET_VOL / es.TARGET_VOL
START_DAY = pd.Timestamp("2026-10-25", tz="UTC")
LOOKBACK_DAYS = 200
MAX_BACKFILL_DAYS = 7
MIN_UNIVERSE = 300
THREADS = 6

BAR = {"kill_dd": 0.15, "kill_red_run": 4, "months_decide": 6, "months_extend": 12, "pass_green_6": 4,
       "pass_green_pct": 0.60, "pass_sharpe": 0.75, "pass_dd": 0.125, "fail_sharpe": 0.25}
BAR_TEXT = ("KILL any time: max DD > 15% or 4 red months in a row. After 6 full months (Nov 2026 – Apr 2027): "
            "PASS = net > 0, ≥ 4/6 months green, Sharpe ≥ 0.75, DD ≤ 12.5%; FAIL = net ≤ 0 or Sharpe < 0.25; "
            "else EXTEND to 12 months (≥ 60% months green). A PASS is not an order to trade real money.")

# The functions the paper book runs. Changing any of them changes what is being tested.
FROZEN_FUNCS = (es.Panel.__init__, es.Panel.build, es.run_weights, es.hold_weekly, es.xs_book, es.momentum,
                es.f_xs_momentum, es.f_carry, es.f_new_listing_short, es.f_btc_trend, es.vol_managed,
                es.f_vol_managed, es.f_combination)
FROZEN_CODE = "61abac0a5ee0b8f5"


def code_fingerprint():
    params = next(v[3] for v in es.variants() if v[1] == VARIANT)
    consts = [es.MIN_AGE_DAYS, es.MIN_TURNOVER, es.MIN_NAMES, es.TAKER, es.SLIP_TIERS, es.SLIP_ILLIQUID,
              es.TARGET_VOL, sorted((k, f.__name__) for k, f in es.BASES.items())]
    src = "".join(inspect.getsource(f) for f in FROZEN_FUNCS) + json.dumps(params, sort_keys=True) + json.dumps(consts)
    return hashlib.sha256(src.encode()).hexdigest()[:16]


RULES = {"version": VERSION, "variant": VARIANT, "discovery_scale_20v": DISCOVERY_SCALE_20V, "target_vol": TARGET_VOL,
         "start_day": str(START_DAY.date()), "lookback_days": LOOKBACK_DAYS, "frozen_code": FROZEN_CODE, "bar": BAR}


def rules_hash():
    return hashlib.sha256(json.dumps(RULES, sort_keys=True).encode()).hexdigest()[:16]


# ─── Data ────────────────────────────────────────────────────────────────────

class BybitSource:
    """Public Bybit endpoints through edge_data (paced, retried)."""

    def instruments(self):
        return ed.fetch_instruments()

    def daily(self, symbol, start_ms, end_ms):
        return ed.fetch_daily(symbol, start_ms, end_ms)

    def funding(self, symbol, start_ms, end_ms):
        return ed.fetch_funding(symbol, start_ms, end_ms)


def fetch_live(source, cache, end_ms, held, min_universe=MIN_UNIVERSE):
    """Rewrite `cache` with the last LOOKBACK_DAYS of closed daily bars + funding for every trading
    crypto perp and every held symbol. Any failed symbol aborts the run: a partial universe would
    produce a different book than the one under test."""
    insts = source.instruments()
    trading = [x for x in insts if x["status"] == "Trading"]
    if len(trading) < min_universe:
        raise RuntimeError(f"only {len(trading)} trading symbols from instruments-info (< {min_universe})")
    keep = trading + [x for x in insts if x["status"] != "Trading" and x["symbol"] in held]
    missing = set(held) - {x["symbol"] for x in keep}
    if missing:
        raise RuntimeError(f"held symbols unknown to instruments-info: {sorted(missing)}")
    start_ms = end_ms - LOOKBACK_DAYS * DAY_MS
    if cache.exists():
        shutil.rmtree(cache)
    cache.mkdir(parents=True)
    (cache / "instruments.json").write_text(json.dumps({"end_ms": end_ms, "instruments": keep}))

    def one(x):
        s = x["symbol"]
        rows = source.daily(s, max(x["launchTime"], start_ms), end_ms)
        fund = source.funding(s, start_ms, end_ms) if rows else []
        (cache / f"{s}_funding.json").write_text(json.dumps(fund, separators=(",", ":")))
        (cache / f"{s}_D.json").write_text(json.dumps(rows, separators=(",", ":")))

    failed = []
    with ThreadPoolExecutor(THREADS) as ex:
        futs = {ex.submit(one, x): x["symbol"] for x in keep}
        for f in as_completed(futs):
            try:
                f.result()
            except Exception as e:                       # noqa: BLE001 — collected, then abort
                failed.append(f"{futs[f]}: {e}")
    if failed:
        raise RuntimeError(f"{len(failed)} symbols failed, no partial book: {failed[:5]}")
    return len(keep)


def panel_at(day, cache):
    """The panel a trader had at `day`'s close: the LOOKBACK_DAYS window ending that day."""
    return es.Panel(end=day, start=day - pd.Timedelta(days=LOOKBACK_DAYS - 1), cache=cache)


def target_weights(P):
    _, _, fn, params, _ = next(v for v in es.variants() if v[1] == VARIANT)
    return fn(P, **params) * SCALE


# ─── State ───────────────────────────────────────────────────────────────────

def _day(s):
    return pd.Timestamp(s, tz="UTC")


def load_weights(out):
    rec = {}
    for p in sorted(out.glob("weights_*.json")):
        d = json.loads(p.read_text())
        rec[_day(d["day"])] = d
    return rec


def load_scores(out):
    p = out / "scores.jsonl"
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []


def days_to_record(now, rec, start=START_DAY):
    """Closed days from the one after the last record (or `start`) to yesterday, at most 7 back."""
    last_closed = pd.Timestamp(now).tz_convert("UTC").normalize() - pd.Timedelta(days=1)
    first = max(rec) + pd.Timedelta(days=1) if rec else start
    first = max(first, start, last_closed - pd.Timedelta(days=MAX_BACKFILL_DAYS - 1))
    return list(pd.date_range(first, last_closed, freq="D")) if first <= last_closed else []


def record(day, now, cache, out):
    P = panel_at(day, cache)
    if P.close.index.max() != day:
        raise RuntimeError(f"data ends {P.close.index.max().date()}, not at {day.date()}")
    w = target_weights(P).loc[day]
    w = w[w.abs() > 1e-12]
    decided = day + pd.Timedelta(days=1)
    doc = {"day": str(day.date()), "decided_at_utc": decided.isoformat(), "computed_at_utc": pd.Timestamp(now).isoformat(),
           "late_hours": round((pd.Timestamp(now) - decided).total_seconds() / 3600, 2), "version": VERSION,
           "rules_hash": rules_hash(), "scale": SCALE, "n_positions": int(len(w)), "gross": float(w.abs().sum()),
           "net_exposure": float(w.sum()), "weights": {s: round(float(x), 10) for s, x in w.sort_index().items()}}
    (out / f"weights_{day.date()}.json").write_text(json.dumps(doc, indent=1))
    return doc


def score(rec, scored, cache, now, start=START_DAY):
    """One row per recorded day not yet scored: previous recorded weights × the day's returns −
    funding − cost of the change made at the day's close (= edge_search.run_weights)."""
    todo = [d for d in sorted(rec) if str(d.date()) not in scored]
    if not todo:
        return []
    last = max(rec)
    P = panel_at(last, cache)
    held = sorted({s for d in rec.values() for s in d["weights"]})
    missing = [s for s in held if s not in P.close.columns]
    if missing:
        raise RuntimeError(f"no prices for held symbols {missing[:5]}")
    W = pd.DataFrame({d: pd.Series(x["weights"], dtype=float) for d, x in rec.items()}).T
    W = W.reindex(index=P.close.index, columns=P.close.columns).fillna(0.0)
    prev = W.shift(1).fillna(0.0)
    gross = (prev * P.ret.fillna(0.0)).sum(axis=1)
    fund = (prev * P.fund).sum(axis=1)
    cost = ((W - prev).abs() * P.cost.fillna(es.TAKER + es.SLIP_ILLIQUID)).sum(axis=1)
    net = gross - fund - cost
    assert np.allclose(net.to_numpy(), es.run_weights(P, W).to_numpy(), atol=1e-12), "accounting differs from run_weights"
    rows = []
    for d in todo:
        if d not in net.index:
            raise RuntimeError(f"{d.date()} outside the scoring window")
        rows.append({"day": str(d.date()), "net": float(net[d]), "gross": float(gross[d]), "funding": float(-fund[d]),
                     "cost": float(-cost[d]), "n_positions": rec[d]["n_positions"], "gap_before": bool(
                         d > start and (d - pd.Timedelta(days=1)) not in rec),
                     "rules_hash": rules_hash(), "scored_at_utc": pd.Timestamp(now).isoformat()})
    return rows


# ─── Scorecard ───────────────────────────────────────────────────────────────

def stats(rows):
    s = pd.Series({_day(r["day"]): r["net"] for r in rows}, dtype=float).sort_index()
    if s.empty:
        return None
    eq = s.cumsum()
    months = s.resample("ME").sum()
    last = s.index[-1]
    complete = [m for m in months.index if m <= last]       # a month counts once its last day is scored
    sd = s.std()
    return {"days": int(len(s)), "first": str(s.index[0].date()), "last": str(last.date()), "net": float(s.sum()),
            "sharpe": float(s.mean() / sd * math.sqrt(365)) if len(s) >= 20 and sd > 0 else None,
            "dd": float((eq.cummax() - eq).max()) if len(eq) else 0.0,
            "months": {str(m.date())[:7]: float(months[m]) for m in complete}}


def bar_status(st):
    """The pre-registered decision on the complete calendar months (October 2026 is a partial start)."""
    if st is None:
        return "RUNNING", "no scored day yet"
    m = [v for k, v in st["months"].items() if k >= "2026-11"]
    if st["dd"] > BAR["kill_dd"]:
        return "KILLED", f"max DD {st['dd'] * 100:.1f}% > {BAR['kill_dd'] * 100:.0f}%"
    run = 0
    for v in m:
        run = run + 1 if v < 0 else 0
        if run >= BAR["kill_red_run"]:
            return "KILLED", f"{run} red months in a row"
    sharpe = st["sharpe"] if st["sharpe"] is not None else 0.0
    green = sum(1 for v in m if v > 0)
    if len(m) >= BAR["months_extend"]:
        ok = (st["net"] > 0 and green / len(m) >= BAR["pass_green_pct"] and sharpe >= BAR["pass_sharpe"]
              and st["dd"] <= BAR["pass_dd"])
        return ("PASS" if ok else "FAIL"), f"12-month decision: {green}/{len(m)} months green, Sharpe {sharpe:.2f}"
    if len(m) >= BAR["months_decide"]:
        if st["net"] <= 0 or sharpe < BAR["fail_sharpe"]:
            return "FAIL", f"6-month decision: net {st['net'] * 100:+.1f}%, Sharpe {sharpe:.2f}"
        if (green >= BAR["pass_green_6"] and sharpe >= BAR["pass_sharpe"] and st["dd"] <= BAR["pass_dd"]
                and len(m) == BAR["months_decide"]):
            return "PASS", f"6-month decision: {green}/6 months green, Sharpe {sharpe:.2f}"
        return "EXTEND", f"{green}/{len(m)} months green, Sharpe {sharpe:.2f} — running to 12 months"
    return "RUNNING", f"{len(m)}/{BAR['months_decide']} full months"


def write_scorecard(out, rows, rec):
    st = stats(rows)
    status, why = bar_status(st)
    L = [f"# Paper test #3 — 4-sleeve blend at 10% volatility ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)",
         f"\nPre-registration: `logs/backtest_reports/prereg_blend_paper_20261025.md` · version `{VERSION}` · "
         f"rules_hash `{rules_hash()}` · paper only, no orders.\n", f"**Bar:** {BAR_TEXT}\n",
         f"**Status: {status}** — {why}\n"]
    if st:
        sharpe = "—" if st["sharpe"] is None else f"{st['sharpe']:.2f}"
        L.append(f"Scored days {st['days']} ({st['first']} → {st['last']}) · net **{st['net'] * 100:+.2f}%** of capital · "
                 f"Sharpe {sharpe} · max drawdown {st['dd'] * 100:.2f}%\n")
        L.append("| month | net | |\n|---|---|---|")
        for k, v in st["months"].items():
            L.append(f"| {k} | {v * 100:+.2f}% | {'✓' if v > 0 else '✗'} |")
        s = pd.Series({_day(r["day"]): r["net"] for r in rows}).sort_index()
        wk = s.resample("W-SUN").sum()
        L.append("\n| week ending (Sun) | net | days |\n|---|---|---|")
        cnt = s.resample("W-SUN").count()
        for d, v in wk.items():
            L.append(f"| {d.date()} | {v * 100:+.2f}% | {int(cnt[d])} |")
        late = [str(d.date()) for d, x in rec.items() if x["late_hours"] > 6]
        L.append(f"\nWeights recorded more than 6 h after the close: {', '.join(late) if late else 'none'}. "
                 f"Days scored after a gap: {', '.join(r['day'] for r in rows if r['gap_before']) or 'none'}.")
    (out / "scorecard.md").write_text("\n".join(L), encoding="utf-8")
    return st, status, why


def write_latest(out, doc):
    w = pd.Series(doc["weights"], dtype=float)
    w = w.reindex(w.abs().sort_values(ascending=False).index)
    L = [f"# Paper book for {doc['day']} (held over the next UTC day) — 10% volatility target",
         f"\n{doc['n_positions']} positions · gross {doc['gross'] * 100:.1f}% of capital · net exposure "
         f"{doc['net_exposure'] * 100:+.1f}% · computed {doc['computed_at_utc']} · paper only, no orders.\n",
         "| symbol | side | weight (% of capital) |", "|---|---|---|"]
    L += [f"| {s} | {'long' if x > 0 else 'short'} | {x * 100:+.2f}% |" for s, x in w.items()]
    (out / "latest_weights.md").write_text("\n".join(L), encoding="utf-8")


# ─── Telegram ────────────────────────────────────────────────────────────────

def telegram_text(new_rows, all_rows, status, why):
    """A message only when the new rows complete a Mon–Sun week or a calendar month; else None."""
    days = [_day(r["day"]) for r in new_rows]
    weeks = [d for d in days if d.dayofweek == 6]
    month_ends = [d for d in days if (d + pd.Timedelta(days=1)).month != d.month]
    if not weeks and not month_ends:
        return None
    s = pd.Series({_day(r["day"]): r["net"] for r in all_rows}).sort_index()
    st = stats(all_rows)
    L = ["<b>Paper test #3 — 4-sleeve blend (10% vol)</b>"]
    for d in weeks:
        wk = s[d - pd.Timedelta(days=6):d]
        part = "" if len(wk) == 7 else f" ({len(wk)} day{'s' if len(wk) > 1 else ''} scored)"
        L.append(f"Week {(d - pd.Timedelta(days=6)).date():%m-%d} → {d.date():%m-%d}: {wk.sum() * 100:+.2f}%{part}")
    for d in month_ends:
        v = s[d.replace(day=1):d].sum()
        L.append(f"<b>{d:%B}: {v * 100:+.2f}% {'✓' if v > 0 else '✗'}</b>")
    green = sum(1 for k, v in st["months"].items() if k >= "2026-11" and v > 0)
    full = sum(1 for k in st["months"] if k >= "2026-11")
    L.append(f"Since start {st['net'] * 100:+.2f}% ({st['days']} days) · max DD {st['dd'] * 100:.2f}% · "
             f"months green {green}/{full}")
    L.append(f"Status {status} — {why}")
    L.append("paper only — no orders")
    return "\n".join(L)


def send_telegram(text):
    try:
        import config
        from delivery.telegram_bot import _send_with_retry
    except Exception as e:                                   # noqa: BLE001
        print(f"[telegram] helper unavailable ({e}); message:\n{text}")
        return False
    if not (config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID):
        print(f"[telegram] TELEGRAM env missing; message:\n{text}")
        return False
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    r = _send_with_retry(url, {"chat_id": config.TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"})
    ok = r is not None and r.status_code == 200
    print(f"[telegram] {'sent' if ok else 'FAILED'}")
    return ok


# ─── Commands ────────────────────────────────────────────────────────────────

def run(now=None, source=None, out=OUT_DIR, cache=LIVE_CACHE, telegram=True, start=START_DAY, min_universe=MIN_UNIVERSE):
    now = pd.Timestamp(now or datetime.now(timezone.utc)).tz_convert("UTC")
    fp = code_fingerprint()
    if fp != FROZEN_CODE:
        raise SystemExit(f"Refusing: the frozen book's code changed (fingerprint {fp} ≠ {FROZEN_CODE}). "
                         "A change to the tested book is a new paper test with its own pre-registration.")
    out.mkdir(parents=True, exist_ok=True)
    rec = load_weights(out)
    todo = days_to_record(now, rec, start)
    scored = {r["day"] for r in load_scores(out)}
    if not todo and all(str(d.date()) in scored for d in rec):
        print("[blend-paper] nothing to record or score")
        return []
    held = sorted({s for d in rec.values() for s in d["weights"]})
    end_ms = int(now.normalize().timestamp() * 1000)
    n = fetch_live(source or BybitSource(), cache, end_ms, held, min_universe)
    print(f"[blend-paper] data: {n} symbols, last {LOOKBACK_DAYS} days to {now.normalize().date()}")
    for day in todo:
        doc = record(day, now, cache, out)
        rec[day] = doc
        print(f"[blend-paper] weights {doc['day']}: {doc['n_positions']} positions, gross {doc['gross']:.2f}, "
              f"late {doc['late_hours']:.1f} h")
    if todo:
        write_latest(out, rec[max(rec)])
    new = score(rec, scored, cache, now, start)
    if new:
        with (out / "scores.jsonl").open("a") as f:
            for r in new:
                f.write(json.dumps(r, separators=(",", ":")) + "\n")
    rows = load_scores(out)
    st, status, why = write_scorecard(out, rows, rec)
    for r in new:
        print(f"[blend-paper] scored {r['day']}: {r['net'] * 100:+.3f}%")
    text = telegram_text(new, rows, status, why) if new else None
    if text and telegram:
        send_telegram(text)
    elif text:
        print(text)
    return new


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--no-telegram", action="store_true")
    sub.add_parser("status")
    args = ap.parse_args(argv)
    if args.cmd == "status":
        rows = load_scores(OUT_DIR)
        st = stats(rows)
        print(json.dumps({"status": bar_status(st), "stats": st, "rules_hash": rules_hash(),
                          "code_ok": code_fingerprint() == FROZEN_CODE}, indent=1, default=str))
        return 0
    try:
        run(telegram=not args.no_telegram)
    except SystemExit:
        raise
    except Exception as e:                                   # noqa: BLE001
        print(f"[blend-paper] FAILED: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
