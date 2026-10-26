"""tournament_paper.py — FORWARD PAPER TOURNAMENT (pre-registered 2026-10-26).

PAPER ONLY: no order API, no API key, no hosted model. Pre-registration:
`logs/backtest_reports/prereg_tournament_20261026.md`.

New clean data only comes from the calendar, so this runs several frozen candidates forward at
the same time instead of one after another. It never crowns the leader of a short run: a book
with no edge passes paper #3's 6-month bar 23% of the time, and one of ten such books 93%.
Two stages:

  stage 1  selection, 2026-11-02 → 2027-01-31 (13 weeks). The four sleeves of paper #3's blend,
           each alone at 10% volatility, against three random-control books built like the
           momentum sleeve with a random ranking. An entrant whose drawdown passes 15% is out.
           At the end at most two entrants with net > 0 and a Sharpe above every control's go
           on (`selection.json`, written once, never recomputed).
  stage 2  confirmation, 2027-02-01 → 2027-08-01 (26 weeks), on data the selection never saw:
           PASS = one-sided t-test of the daily mean > 0, Holm at 5% across the picks.

Rows before 2026-11-02 are a shakedown: recorded and shown, never counted. The other forward
lanes (paper #2, paper #3, the daily book, checklist ≥ 5) appear in the same weekly table on
their own clocks; nothing here changes them.

Runs in blend_paper.yml right after paper #3 and reuses its data download (`blend_live` cache)
when it is complete and current; otherwise it downloads the same data itself
(blend_paper.fetch_live). Weights come from the edge_search functions. Their source and this
module's lane code are fingerprinted (FROZEN_CODE), and a run refuses if any of it changed.

Usage:
    venv/bin/python tournament_paper.py run [--no-telegram]
    venv/bin/python tournament_paper.py status
"""

import argparse
import hashlib
import inspect
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import blend_paper as bp
import edge_search as es

BASE_DIR = Path(__file__).resolve().parent
OUT_DIR = BASE_DIR / "logs" / "tournament"
BLEND_SCORES = BASE_DIR / "logs" / "blend_paper" / "scores.jsonl"
XS_SCORES = BASE_DIR / "logs" / "xs_momentum" / "scores.jsonl"

VERSION = "tournament_v1"
TARGET_VOL = 0.10
VOL_FACTOR = TARGET_VOL / es.TARGET_VOL                   # DISCOVERY scales are for 20% volatility
START_DAY = pd.Timestamp("2026-10-25", tz="UTC")       # shakedown from here, not counted
STAGE1_START = pd.Timestamp("2026-11-02", tz="UTC")
STAGE1_END = pd.Timestamp("2027-01-31", tz="UTC")
STAGE2_START = STAGE1_END + pd.Timedelta(days=1)
STAGE2_END = pd.Timestamp("2027-08-01", tz="UTC")

# The blend's four sleeves with their DISCOVERY 20%-vol scales, read from the frozen variant itself.
BLEND_SLEEVES = dict(next(v[3] for v in es.variants() if v[1] == bp.VARIANT)["params"]["components"])
ENTRANTS = {"mom28": "xs_mom_28d_skip0_10pct", "listing_short": "new_listing_short_d1_h60_btc",
            "btc_trend": "volman_btc_sma50_long", "carry7": "xs_carry_7d_20pct"}
CONTROL_SHAPE = "xs_mom_28d_skip0_10pct"                # the controls copy this book, ranking random
CONTROLS = {"random_1": 1, "random_2": 2, "random_3": 3}
LANES = list(ENTRANTS) + list(CONTROLS)
LABELS = {"mom28": "28-day momentum", "listing_short": "new-listing short, BTC-hedged",
          "btc_trend": "BTC trend, long only", "carry7": "funding carry 7d",
          "random_1": "random control 1", "random_2": "random control 2", "random_3": "random control 3"}

BAR = {"kill_dd": 0.15, "max_picks": 2, "alpha": 0.05}
BAR_TEXT = ("Stage 1 (2026-11-02 → 2027-01-31): an entrant whose drawdown passes 15% is out; at the end at most "
            "2 entrants with net > 0 and a Sharpe above every random control go on. Stage 2 (2027-02-01 → "
            "2027-08-01, fresh data): PASS = daily mean > 0 by a one-sided t-test, Holm at 5% across the picks; "
            "drawdown > 15% = FAIL. A PASS is not an order to trade real money.")
SHARPE_MIN_WEEKS = 8                                    # fewer weeks: Sharpe is noise, the table shows —


def random_score(P, seed):
    """A ranking that knows nothing: a fixed pseudo-random number per (seed, day, symbol) on Sundays
    (the only rows xs_book keeps), independent of the data window so every record reproduces it."""
    S = pd.DataFrame(np.nan, index=P.close.index, columns=P.close.columns)
    for d in P.close.index[P.close.index.dayofweek == 6]:
        S.loc[d] = [int.from_bytes(hashlib.sha256(f"{seed}|{d.date()}|{s}".encode()).digest()[:8], "big") / 2 ** 64
                    for s in P.close.columns]
    return S


def lane_weights(P, lane):
    """A lane's weights at 10% volatility: the sleeve exactly as the blend builds it, alone."""
    menu = {name: (fn, params) for _, name, fn, params, _ in es.variants()}
    if lane in CONTROLS:
        _, params = menu[CONTROL_SHAPE]
        W = es.xs_book(P, random_score(P, CONTROLS[lane]), params["frac"])
        return W * BLEND_SLEEVES[CONTROL_SHAPE] * VOL_FACTOR
    fn, params = menu[ENTRANTS[lane]]
    return fn(P, **params) * BLEND_SLEEVES[ENTRANTS[lane]] * VOL_FACTOR


FROZEN_CODE = "832fb9edcb1f97c0"


def code_fingerprint():
    """Paper #3's frozen functions + the data path + this module's lane code and lane menu."""
    funcs = bp.FROZEN_FUNCS + (bp.fetch_live, bp.panel_at, bp.days_to_record, random_score, lane_weights)
    menu = {name: params for _, name, _, params, _ in es.variants()}
    consts = [es.MIN_AGE_DAYS, es.MIN_TURNOVER, es.MIN_NAMES, es.TAKER, es.SLIP_TIERS, es.SLIP_ILLIQUID,
              es.TARGET_VOL, sorted((k, f.__name__) for k, f in es.BASES.items()), bp.LOOKBACK_DAYS,
              {n: menu[n] for n in sorted(set(ENTRANTS.values()) | {CONTROL_SHAPE})}]
    src = "".join(inspect.getsource(f) for f in funcs) + json.dumps(consts, sort_keys=True, default=str)
    return hashlib.sha256(src.encode()).hexdigest()[:16]


RULES = {"version": VERSION, "entrants": ENTRANTS, "controls": CONTROLS, "control_shape": CONTROL_SHAPE,
         "scales_20v": BLEND_SLEEVES, "target_vol": TARGET_VOL, "start_day": str(START_DAY.date()),
         "stage1": [str(STAGE1_START.date()), str(STAGE1_END.date())],
         "stage2": [str(STAGE2_START.date()), str(STAGE2_END.date())], "frozen_code": FROZEN_CODE, "bar": BAR}


def rules_hash():
    return hashlib.sha256(json.dumps(RULES, sort_keys=True).encode()).hexdigest()[:16]


# ─── Data, record, score ─────────────────────────────────────────────────────

def ensure_data(now, source, cache, held, min_universe):
    """Reuse paper #3's download when it ends today and holds every symbol it lists plus our held
    ones; otherwise download the same data (any failed symbol aborts — no partial book)."""
    end_ms = int(now.normalize().timestamp() * 1000)
    meta = cache / "instruments.json"
    if meta.exists():
        d = json.loads(meta.read_text())
        syms = {x["symbol"] for x in d["instruments"]}
        complete = all((cache / f"{s}_D.json").exists() and (cache / f"{s}_funding.json").exists() for s in syms)
        if d.get("end_ms") == end_ms and complete and set(held) <= syms:
            return "reused", len(syms)
    return "fetched", bp.fetch_live(source or bp.BybitSource(), cache, end_ms, held, min_universe)


def record(day, now, cache, out):
    P = bp.panel_at(day, cache)
    if P.close.index.max() != day:
        raise RuntimeError(f"data ends {P.close.index.max().date()}, not at {day.date()}")
    lanes = {}
    for lane in LANES:
        w = lane_weights(P, lane).loc[day]
        w = w[w.abs() > 1e-12]
        lanes[lane] = {"n_positions": int(len(w)), "gross": float(w.abs().sum()), "net_exposure": float(w.sum()),
                       "weights": {s: round(float(x), 10) for s, x in w.sort_index().items()}}
    decided = day + pd.Timedelta(days=1)
    doc = {"day": str(day.date()), "decided_at_utc": decided.isoformat(), "computed_at_utc": pd.Timestamp(now).isoformat(),
           "late_hours": round((pd.Timestamp(now) - decided).total_seconds() / 3600, 2), "version": VERSION,
           "rules_hash": rules_hash(), "lanes": lanes}
    (out / f"weights_{day.date()}.json").write_text(json.dumps(doc, indent=1))
    return doc


def held_symbols(rec):
    return sorted({s for d in rec.values() for x in d["lanes"].values() for s in x["weights"]})


def score(rec, scored, cache, now, start=START_DAY):
    """One row per lane and recorded day not yet scored, with the accounting of blend_paper.score
    (previous recorded weights × the day's returns − funding − cost of the change at the close)."""
    todo = [d for d in sorted(rec) if str(d.date()) not in scored]
    if not todo:
        return []
    P = bp.panel_at(max(rec), cache)
    missing = [s for s in held_symbols(rec) if s not in P.close.columns]
    if missing:
        raise RuntimeError(f"no prices for held symbols {missing[:5]}")
    rows = []
    for lane in LANES:
        W = pd.DataFrame({d: pd.Series(x["lanes"][lane]["weights"], dtype=float) for d, x in rec.items()}).T
        W = W.reindex(index=P.close.index, columns=P.close.columns).fillna(0.0)
        prev = W.shift(1).fillna(0.0)
        gross = (prev * P.ret.fillna(0.0)).sum(axis=1)
        fund = (prev * P.fund).sum(axis=1)
        cost = ((W - prev).abs() * P.cost.fillna(es.TAKER + es.SLIP_ILLIQUID)).sum(axis=1)
        net = gross - fund - cost
        assert np.allclose(net.to_numpy(), es.run_weights(P, W).to_numpy(), atol=1e-12), "accounting differs from run_weights"
        for d in todo:
            if d not in net.index:
                raise RuntimeError(f"{d.date()} outside the scoring window")
            rows.append({"day": str(d.date()), "lane": lane, "net": float(net[d]), "gross": float(gross[d]),
                         "funding": float(-fund[d]), "cost": float(-cost[d]),
                         "n_positions": rec[d]["lanes"][lane]["n_positions"],
                         "gap_before": bool(d > start and (d - pd.Timedelta(days=1)) not in rec),
                         "rules_hash": rules_hash(), "scored_at_utc": pd.Timestamp(now).isoformat()})
    return rows


# ─── Stages ──────────────────────────────────────────────────────────────────

def _phi(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _series(by_time):
    """{UTC Timestamp: value} → a sorted float Series that keeps a DatetimeIndex even when empty."""
    return pd.Series(list(by_time.values()), index=pd.DatetimeIndex(list(by_time), tz="UTC"), dtype=float).sort_index()


def lane_series(rows, lane):
    return _series({bp._day(r["day"]): r["net"] for r in rows if r["lane"] == lane})


def window_stats(s, per_year=365):
    """Net, max drawdown from the window's start (additive, as every paper scorecard), annualised
    Sharpe, the first day the drawdown passed the kill line, and the one-sided p of mean > 0."""
    if s.empty:
        return None
    eq = s.cumsum().to_numpy()
    under = np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:] - eq
    breach = np.flatnonzero(under > BAR["kill_dd"])
    sd = float(s.std()) if len(s) > 1 else 0.0
    t = float(s.mean()) / sd * math.sqrt(len(s)) if sd > 0 else None
    return {"n": int(len(s)), "net": float(s.sum()), "dd": float(under.max()),
            "sharpe": float(s.mean()) / sd * math.sqrt(per_year) if sd > 0 else None,
            "killed_on": str(s.index[breach[0]].date()) if len(breach) else None,
            "p": None if t is None else 1 - _phi(t)}


def select(rows):
    """The stage-1 rule: not killed, net > 0, Sharpe above every random control; best Sharpe first."""
    st = {lane: window_stats(lane_series(rows, lane)[STAGE1_START:STAGE1_END]) for lane in LANES}
    ctrl = [st[c]["sharpe"] for c in CONTROLS if st[c] and st[c]["sharpe"] is not None]
    best_ctrl = max(ctrl) if ctrl else None
    ok = [lane for lane in ENTRANTS if st[lane] and not st[lane]["killed_on"] and st[lane]["net"] > 0
          and st[lane]["sharpe"] is not None and (best_ctrl is None or st[lane]["sharpe"] > best_ctrl)]
    picks = sorted(ok, key=lambda x: -st[x]["sharpe"])[:BAR["max_picks"]]
    return {"picks": picks, "best_control_sharpe": best_ctrl, "stage1": st}


def maybe_select(rows, out, now):
    """Write selection.json once, when stage 1's last day is scored for every lane."""
    p = out / "selection.json"
    if p.exists():
        return json.loads(p.read_text()), False
    last = str(STAGE1_END.date())
    if {r["lane"] for r in rows if r["day"] == last} != set(LANES):
        return None, False
    sel = select(rows)
    sel.update({"rules_hash": rules_hash(), "selected_at_utc": pd.Timestamp(now).isoformat()})
    p.write_text(json.dumps(sel, indent=1))
    return sel, True


def stage2(rows, picks):
    """{lane: (verdict, stats)} on stage-2 days only. Holm: the smallest p must clear α/m, the next α/(m−1)."""
    st = {lane: window_stats(lane_series(rows, lane)[STAGE2_START:STAGE2_END]) for lane in picks}
    done = all(st[x] and lane_series(rows, x).index.max() >= STAGE2_END for x in picks)
    out = {}
    for lane in picks:
        if st[lane] and st[lane]["killed_on"]:
            out[lane] = ("FAIL", st[lane])
        elif not done:
            out[lane] = ("RUNNING", st[lane])
    if done:
        live = sorted([x for x in picks if x not in out], key=lambda x: st[x]["p"] if st[x]["p"] is not None else 1.0)
        m, passing = len(picks), True
        for i, lane in enumerate(live):
            p = st[lane]["p"]
            passing = passing and p is not None and p <= BAR["alpha"] / (m - i)
            out[lane] = ("PASS" if passing else "FAIL", st[lane])
    return out


def lane_status(lane, rows, sel, last_day):
    """The one-word state of a tournament lane, as of `last_day` (the last scored day)."""
    if last_day is None or last_day < STAGE1_START:
        return "shakedown"
    s1 = window_stats(lane_series(rows, lane)[STAGE1_START:STAGE1_END])
    if lane in CONTROLS:
        return "control"
    if s1 and s1["killed_on"]:
        return f"KILLED {s1['killed_on']}"
    if last_day <= STAGE1_END or sel is None:
        weeks = min(13, (min(last_day, STAGE1_END) - STAGE1_START).days // 7 + 1)
        return f"stage 1 · week {weeks}/13"
    if lane not in sel["picks"]:
        return "not selected"
    verdict, _ = stage2(rows, sel["picks"])[lane]
    if verdict == "RUNNING":
        return f"stage 2 · week {min(26, (last_day - STAGE2_START).days // 7 + 1)}/26"
    return f"stage 2 {verdict}"


# ─── The weekly table ────────────────────────────────────────────────────────

def _monday(ts):
    return (ts - pd.Timedelta(days=ts.dayofweek)).normalize()


def other_lanes():
    """The lanes on their own clocks, as {name: (label, freq, series, status)}: daily % for paper
    #3, weekly % (Monday-labelled) for the others. A lane that fails to load is left out."""
    out = {}
    try:
        rows = [r for r in bp.load_scores(BLEND_SCORES.parent) if r.get("rules_hash") == bp.rules_hash()]
        st = bp.bar_status(bp.stats(rows)) if rows else ("RUNNING", "")
        out["blend"] = ("paper #3 blend", "D", _series({bp._day(r["day"]): r["net"] for r in rows}), st[0])
    except Exception as e:                                   # noqa: BLE001 — a display lane
        print(f"[tournament] paper #3 lane unavailable: {e}")
    try:
        xs = [json.loads(x) for x in XS_SCORES.read_text().splitlines() if x.strip()]
        h = xs[-1]["rules_hash"]
        for book in ("k56", "k91"):
            s = _series({pd.Timestamp(r["week"], tz="UTC"): r["net"] for r in xs if r["book"] == book and r["rules_hash"] == h})
            out[book] = (f"paper #2 momentum {book}", "W", s, f"{len(s)}/26 weeks")
    except Exception as e:                                   # noqa: BLE001
        print(f"[tournament] paper #2 lanes unavailable: {e}")
    try:
        out.update(trade_lanes())
    except Exception as e:                                   # noqa: BLE001
        print(f"[tournament] per-trade lanes unavailable: {e}")
    return out


def trade_lanes(all_evals=None, setups_dir=None):
    """The daily book and checklist ≥ 5 as weekly % of the account at weekly_review.RISK_PCT per
    trade, by the Monday of the signal. A trade's R lands once its 2-day window closes, so the
    latest week fills in over the next days."""
    import monthly_review as mr
    import weekly_review as wr
    all_evals = mr.load_evals() if all_evals is None else all_evals
    picks = wr.load_picks(all_evals, setups_dir or wr.SETUPS_DIR)

    def weekly(pairs):
        by_week = {}
        for ts, r in pairs:
            by_week[_monday(ts)] = by_week.get(_monday(ts), 0.0) + r * wr.RISK_PCT / 100
        return _series(by_week)

    book = [(pd.Timestamp(p["ts"]), mr.we._managed_rr(p["row"])[1]) for p in picks if p["row"]]
    chk = [(pd.Timestamp(r["_run_ts"]), mr.we._managed_rr(r)[1]) for r in mr.collect(all_evals)
           if (r.get("checklist") or {}).get("derivs_ok") and r["checklist"]["score"] >= wr.CHECKLIST_MIN_SCORE]
    return {"daily_book": ("daily book", "W", weekly(book), f"{len(book)} trades scored"),
            "checklist": (f"checklist ≥ {wr.CHECKLIST_MIN_SCORE}", "W", weekly(chk),
                          f"{len(chk)}/{wr.CHECKLIST_N_DECIDE} scored")}


def summarize(freq, s, window_start, week_end):
    """One table row's numbers: the reported week, the window total, drawdown, Sharpe, green weeks."""
    if week_end is None:
        return None
    mon = week_end - pd.Timedelta(days=6)
    if freq == "D":
        s = s[window_start:week_end]
        weeks = s.groupby(s.index.map(_monday)).sum() if len(s) else _series({})
        st = window_stats(s, 365)
    else:
        s = s[window_start:mon]
        weeks = s
        st = window_stats(s, 52)
    if st is None:
        return {"week": None, "net": None, "dd": None, "sharpe": None, "green": "—"}
    full = weeks[weeks.index >= window_start]
    return {"week": float(weeks[mon]) if mon in weeks.index else None, "net": st["net"], "dd": st["dd"],
            "sharpe": st["sharpe"] if len(full) >= SHARPE_MIN_WEEKS else None,
            "green": f"{int((full > 0).sum())}/{len(full)}"}


def table(rows, others, sel):
    """(markdown lines, the reported week's Sunday, the window start)."""
    days = sorted({bp._day(r["day"]) for r in rows})
    last = days[-1] if days else None
    sundays = [d for d in days if d.dayofweek == 6]
    week_end = sundays[-1] if sundays else None
    start = STAGE1_START if last is not None and last >= STAGE1_START else START_DAY
    pct = lambda v: "—" if v is None else f"{v * 100:+.2f}%"
    L = ["| lane | role | week | since " + f"{start.date():%m-%d}" + " | max DD | Sharpe | weeks green | status |",
         "|---|---|---|---|---|---|---|---|"]
    entries = [(LABELS[x], "entrant" if x in ENTRANTS else "control", "D", lane_series(rows, x),
                lane_status(x, rows, sel, last)) for x in LANES]
    entries += [(lab, "own clock", f, s, status) for lab, f, s, status in others.values()]
    for label, role, freq, s, status in entries:
        m = summarize(freq, s, start, week_end)
        if m is None:
            continue
        dd = "—" if m["dd"] is None else f"{m['dd'] * 100:.2f}%"
        sh = "—" if m["sharpe"] is None else f"{m['sharpe']:.2f}"
        L.append(f"| {label} | {role} | {pct(m['week'])} | {pct(m['net'])} | {dd} | {sh} | {m['green']} | {status} |")
    return L, week_end, start


def write_table(out, rows, others, sel):
    L, week_end, start = table(rows, others, sel)
    head = [f"# Paper tournament — {VERSION} ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)",
            f"\nPre-registration: `logs/backtest_reports/prereg_tournament_20261026.md` · rules_hash `{rules_hash()}` · "
            "paper only, no orders.\n", f"**Bar:** {BAR_TEXT}\n"]
    if start == START_DAY:
        head.append("**SHAKEDOWN — rows before 2026-11-02 are not counted.**\n")
    if week_end is not None:
        head.append(f"Week = Mon–Sun ending {week_end.date()}. Entrants and controls are at 10% volatility; per-trade "
                    "lanes are % of the account at 0.5% risk per trade, by signal week, and fill in as 2-day windows "
                    f"close. Sharpe shows after {SHARPE_MIN_WEEKS} weeks. The leader is not a winner: selection "
                    f"{STAGE2_START.date()}, confirmation to {STAGE2_END.date()}.\n")
    if sel is not None:
        head.append(f"**Stage-1 selection:** {', '.join(sel['picks']) or 'none'} (best control Sharpe "
                    f"{sel['best_control_sharpe'] if sel['best_control_sharpe'] is None else round(sel['best_control_sharpe'], 2)}).\n")
    (out / "table.md").write_text("\n".join(head + L), encoding="utf-8")
    return week_end


# ─── Telegram ────────────────────────────────────────────────────────────────

def telegram_text(new_rows, rows, others, sel, killed_now, selected_now):
    """A message when the new rows complete a Mon–Sun week, kill an entrant or close stage 1."""
    sundays = sorted({bp._day(r["day"]) for r in new_rows if bp._day(r["day"]).dayofweek == 6})
    if not sundays and not killed_now and not selected_now:
        return None
    L = ["<b>Paper tournament</b>"]
    for lane in killed_now:
        L.append(f"KILLED: {LABELS[lane]} — drawdown passed {BAR['kill_dd'] * 100:.0f}%")
    if selected_now:
        L.append(f"<b>Stage 1 closed — picks: {', '.join(LABELS[x] for x in sel['picks']) or 'none'}</b> "
                 "(net > 0, Sharpe above every random control). Stage 2 runs on fresh data to "
                 f"{STAGE2_END.date()}.")
    if sundays:
        L_tab, week_end, start = table(rows, others, sel)
        mon = week_end - pd.Timedelta(days=6)
        tag = "shakedown, not counted" if week_end < STAGE1_START else (
            f"stage 1 · week {(week_end - STAGE1_START).days // 7 + 1}/13" if week_end <= STAGE1_END else "stage 2")
        L.append(f"Week {mon.date():%m-%d} → {week_end.date():%m-%d} ({tag}) · week / since {start.date():%m-%d}")
        for line in L_tab[2:]:
            c = [x.strip() for x in line.strip("|").split("|")]
            L.append(f"{c[0]}: {c[2]} / {c[3]} · {c[7]}")
        L.append(f"The leader is not a winner: selection {STAGE2_START.date()}, "
                 f"confirmation to {STAGE2_END.date()}.")
    L.append("paper only — no orders")
    return "\n".join(L)


# ─── Commands ────────────────────────────────────────────────────────────────

def killed(rows):
    return {x for x in ENTRANTS if (s := window_stats(lane_series(rows, x)[STAGE1_START:])) and s["killed_on"]}


def run(now=None, source=None, out=OUT_DIR, cache=bp.LIVE_CACHE, telegram=True, start=START_DAY,
        min_universe=bp.MIN_UNIVERSE, others=None):
    """Record + score every closed day not done yet, then rewrite the table (also on no-op runs:
    the other lanes may have moved). `others=None` loads the real own-clock lanes."""
    now = pd.Timestamp(now or datetime.now(timezone.utc)).tz_convert("UTC")
    fp = code_fingerprint()
    if fp != FROZEN_CODE:
        raise SystemExit(f"Refusing: the tournament's code changed (fingerprint {fp} ≠ {FROZEN_CODE}). "
                         "A change to a tested book is a new tournament with its own pre-registration.")
    out.mkdir(parents=True, exist_ok=True)
    rec = bp.load_weights(out)
    todo = bp.days_to_record(now, rec, start)
    old = bp.load_scores(out)
    scored = {r["day"] for r in old}
    new = []
    if todo or not all(str(d.date()) in scored for d in rec):
        how, n = ensure_data(now, source, cache, held_symbols(rec), min_universe)
        print(f"[tournament] data {how}: {n} symbols, last {bp.LOOKBACK_DAYS} days to {now.normalize().date()}")
        for day in todo:
            doc = record(day, now, cache, out)
            rec[day] = doc
            print(f"[tournament] weights {doc['day']}: " + ", ".join(
                f"{k} {v['n_positions']}" for k, v in doc["lanes"].items()) + f" · late {doc['late_hours']:.1f} h")
        new = score(rec, scored, cache, now, start)
        if new:
            with (out / "scores.jsonl").open("a") as f:
                for r in new:
                    f.write(json.dumps(r, separators=(",", ":")) + "\n")
    else:
        print("[tournament] nothing to record or score")
    rows = bp.load_scores(out)
    sel, selected_now = maybe_select(rows, out, now)
    others = other_lanes() if others is None else others
    write_table(out, rows, others, sel)
    for d in sorted({r["day"] for r in new}):
        print(f"[tournament] scored {d}: " + ", ".join(f"{r['lane']} {r['net'] * 100:+.3f}%" for r in new if r["day"] == d))
    text = telegram_text(new, rows, others, sel, sorted(killed(rows) - killed(old)), selected_now) if new else None
    if text and telegram:
        bp.send_telegram(text)
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
        rows = bp.load_scores(OUT_DIR)
        sel = json.loads((OUT_DIR / "selection.json").read_text()) if (OUT_DIR / "selection.json").exists() else None
        last = max((bp._day(r["day"]) for r in rows), default=None)
        print(json.dumps({"rules_hash": rules_hash(), "code_ok": code_fingerprint() == FROZEN_CODE, "last_day": str(last),
                          "lanes": {x: lane_status(x, rows, sel, last) for x in LANES}, "selection": sel},
                         indent=1, default=str))
        return 0
    try:
        run(telegram=not args.no_telegram)
    except SystemExit:
        raise
    except Exception as e:                                   # noqa: BLE001
        print(f"[tournament] FAILED: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
