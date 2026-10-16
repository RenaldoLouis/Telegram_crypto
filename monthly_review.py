#!/usr/bin/env python
"""Monthly strategy review (added 2026-10-16) — facts from Python, opinion from a read-only AI pass.

Two halves, deliberately separated:

1. FACTS — pure Python, zero tokens, CI-safe. `maybe_write_facts()` runs at the end of every
   `weekly_eval.run_evaluation()` and, once >= config.MONTHLY_REVIEW_DAYS have passed since the
   last facts file (or none exists), writes logs/performance/monthly/facts_<date>.{json,md}:
   every pre-registered forward test judged against ITS OWN decision rule, the hit-rate band on
   the surfaced book, the shadow lane per rule / direction / month, the forward daily-pick study,
   the frozen rule's monthly profile in the latest unified backtest (fade check), scan coverage
   and the open recommendation ledger. Nothing in this file can change a trading rule.

2. AI PASS — optional, LOCAL only, report-only. `python monthly_review.py ai` feeds the facts
   file + prompts/monthly_review.md to the Codex CLI (the user's subscription; `-s read-only`,
   so it can read the repo but cannot write to it), saves the answer as review_<date>.md, then
   Python flags every figure in the review that does not appear in the facts file and ingests
   the review's JSON block into recommendations.jsonl (status "open" until a later review
   grades it). If codex is missing or fails, the facts file stands on its own. The hosted model
   reads a report and writes a report — it never touches the pipeline (CORE PRINCIPLE).

Run:
  python monthly_review.py facts [--force]     # write facts if due (or forced)
  python monthly_review.py ai [--dry-run]      # Codex pass on the latest facts lacking a review
  python monthly_review.py check <review.md>   # re-run the figure check on a review
  python monthly_review.py refresh-backtest    # unified_backtest on the frozen rule, last 90 d (VPN)
  python monthly_review.py status              # one-screen state
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import config
import weekly_eval as we

OUT_DIR = Path("logs/performance/monthly")
PROMPT_FILE = Path("prompts/monthly_review.md")
REPORT_DIR = Path("logs/backtest_reports")
COVERAGE = Path("logs/scan_keeper/coverage.jsonl")
XS_SCORES = Path("logs/xs_momentum/scores.jsonl")
SETUPS_DIR = Path("logs/setups")

SURFACED = ("mechanical", "watch")          # the counted book
LANES = ("mechanical", "watch", "shadow")   # everything the engine produced and eval scored

FROZEN_RULE = "range_reversion_short"
FROZEN_TF = "4h"
# Pre-registered forward test #1 (progress.md banner 2026-09-23 + 2026-10-04 amendment). Copied
# here so the facts file can judge the test by its own rule; the banner is the source of truth.
FT1 = {"n_decide": 30, "n_extend": 50, "promote_pct": 70.0, "extend_floor_pct": 60.0,
       "kill_after_n": 20, "kill_below_pct": 60.0, "expiry": "2026-12-31"}
# Hit-rate band on the surfaced book (user decision 2026-10-16): judged on the last 30 trades,
# not the calendar month, because a 65% rule shows a sub-60% month ~1 time in 4 by luck.
BAND = {"window": 30, "target_pct": float(getattr(config, "HIT_RATE_TARGET_PCT", 70)),
        "floor_pct": 60.0, "red_max_wins": 12}   # 12/30 = 40%: below 60% even at 95% confidence


def _ledger():
    return OUT_DIR / "recommendations.jsonl"


def _band_history():
    return OUT_DIR / "band_history.jsonl"


# ---- small helpers --------------------------------------------------------------------------
def _utc(ts):
    t = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def _read_jsonl(path):
    p = Path(path)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


def _write_jsonl(path, recs):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps(r) + "\n" for r in recs), encoding="utf-8")


def load_evals(evals_dir=None):
    out = []
    for f in sorted(Path(evals_dir or we.EVALS_DIR).glob("eval_*.json")):
        try:
            out.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            pass
    return out


def collect(all_evals):
    """Flatten eval records -> evaluated result rows stamped with their run timestamp."""
    rows = []
    for ev in all_evals:
        ts = ev.get("run_timestamp_utc")
        if not ts:
            continue
        for r in ev.get("results", []):
            if r.get("status") != "evaluated":
                continue
            r = dict(r)
            r["_run_ts"] = ts
            r["_run_tag"] = ev.get("run_tag")
            rows.append(r)
    return rows


def v2_rows(rows, sources=LANES):
    return [r for r in rows if r.get("source") in sources and we._v2_era(r)]


def _stats(rows):
    """Hit rate (+Wilson CI) and managed net R (+CI) of a list of evaluated rows."""
    n = len(rows)
    if not n:
        return {"n": 0, "wins": 0, "prof_pct": None, "prof_ci": None, "net": None, "net_ci": None}
    wins = sum(1 for r in rows if we._profitable(r))
    nets = [we._managed_rr(r)[1] for r in rows]
    ci = we._mean_ci(nets)
    return {"n": n, "wins": wins, "prof_pct": round(100 * wins / n, 1), "prof_ci": we._wilson(wins, n),
            "net": round(sum(nets) / n, 3),
            "net_ci": (round(ci[1], 3), round(ci[2], 3)) if ci else None}


def _ts_key(r):
    return _utc(r["_run_ts"])


# ---- 1. forward test #1 (the frozen rule) --------------------------------------------------
def ft1_decision(s, now):
    n, p, net = s["n"], s["prof_pct"], s["net"]
    expiry = _utc(FT1["expiry"] + "T23:59:59+00:00")
    if n >= FT1["n_decide"]:
        if p >= FT1["promote_pct"] and (net or 0) > 0:
            return "PROMOTE to EXECUTE at small size (>=70% profitable AND net>0 at n>=30)"
        if p >= FT1["extend_floor_pct"]:
            return "EXTEND to n=50 under the same bar (60-70%, or >=70% with net<=0) — no changes"
        return "RETIRE — <60% at n>=30: the 4h mean-reversion family is closed"
    if n > FT1["kill_after_n"] and p is not None and p < FT1["kill_below_pct"]:
        return "KILL — <60% after n=20 (pre-registered hard stop): family closed, no re-tuning"
    if now > expiry:
        return "EXPIRED — n<30 by 2026-12-31 (pre-registered hard expiry): family closed"
    return f"BUILDING ({n}/{FT1['n_decide']}) — no decision yet; the rule stays frozen"


def forward_test_1(v2_surfaced, now):
    rows = sorted([r for r in v2_surfaced if r.get("signal_name") == FROZEN_RULE], key=_ts_key)
    s = _stats(rows)
    out = {"rule": f"{FROZEN_RULE} {FROZEN_TF} + vol_spike>={getattr(config, 'RANGE_REVERSION_SHORT_MIN_VOL_SPIKE', 1.5)} (frozen)",
           **s, "independent_bets": len(we._independent_bets(rows)) if rows else 0, "bar": FT1,
           "trades": [{"date": _ts_key(r).strftime("%Y-%m-%d"), "symbol": r.get("symbol"),
                       "profitable": bool(we._profitable(r)), "net": round(we._managed_rr(r)[1], 3)}
                      for r in rows]}
    expiry = _utc(FT1["expiry"] + "T23:59:59+00:00")
    out["days_to_expiry"] = (expiry - now).days
    if rows:
        first = _ts_key(rows[0])
        days = max((now - first).days, 1)
        out["first_trade_utc"] = first.isoformat()
        out["days_running"] = days
        out["pace_per_week"] = round(7 * len(rows) / days, 2)
        out["projected_n_at_expiry"] = round(len(rows) + out["pace_per_week"] * max(out["days_to_expiry"], 0) / 7, 1)
    out["decision"] = ft1_decision(s, now)
    return out


# ---- 2. hit-rate band on the surfaced book --------------------------------------------------
def band(v2_surfaced, previous_status=None):
    rows = sorted(v2_surfaced, key=_ts_key)[-BAND["window"]:]
    s = _stats(rows)
    if s["n"] < BAND["window"]:
        status = "BUILDING"
    elif s["wins"] <= BAND["red_max_wins"]:
        status = "RED"
    elif s["prof_pct"] < BAND["floor_pct"]:
        status = "RED" if previous_status in ("YELLOW", "RED") else "YELLOW"
    elif s["prof_pct"] >= BAND["target_pct"] and (s["net"] or 0) > 0:
        status = "GREEN"
    else:
        status = "OK"
    return {**s, "window": BAND["window"], "status": status, "previous_status": previous_status,
            "rule": {"GREEN": f">={BAND['target_pct']:.0f}% profitable AND net>0 — the real-money bar",
                     "OK": f"{BAND['floor_pct']:.0f}-{BAND['target_pct']:.0f}% — inside the band, nothing to do",
                     "YELLOW": f"<{BAND['floor_pct']:.0f}% once — explain it; change nothing",
                     "RED": f"<{BAND['floor_pct']:.0f}% on two consecutive reviews, or <= {BAND['red_max_wins']}/{BAND['window']} wins — act: retire, promote a shadow rule that passed, or test a recorded recommendation; never re-tune on the losing month",
                     "BUILDING": f"fewer than {BAND['window']} surfaced trades scored in the v2 era"}}


# ---- 3. paper test #2 (xs momentum) ---------------------------------------------------------
def paper_test_2():
    try:
        import xs_momentum_paper as xp
    except Exception as e:  # pandas/numpy missing in a stripped env — never fail the facts
        return {"error": f"xs_momentum_paper unavailable: {e}"}
    recs = _read_jsonl(XS_SCORES)
    h = xp.rules_hash()
    books = {}
    for book in ("k56", "k91"):
        mine = [r for r in recs if r.get("book") == book and r.get("rules_hash") == h]
        nets = [float(r["net"]) for r in mine]
        verdict, st = xp.apply_bar(nets)
        books[book] = {"n_weeks": st["n"], "cum_net_pct": round(st["cum"] * 100, 2),
                       "sharpe": round(st["sharpe"], 2) if st["sharpe"] is not None else None,
                       "max_dd_pct": round(st["mdd"] * 100, 1),
                       "pct_weeks_positive": round(st["pct_pos"] * 100, 0) if st["pct_pos"] is not None else None,
                       "verdict": verdict,
                       "weeks": [{"week": r["week"], "net_pct": round(float(r["net"]) * 100, 2)} for r in mine]}
    return {"rules_hash": h, "bar": xp.BAR, "books": books}


# ---- 4. shadow lane --------------------------------------------------------------------------
def _surface_bar_for(sig):
    try:
        import mechanical_setups as ms
        for (s, tf), hit in ms.EXPECTANCY.items():
            if s == sig:
                n = ms.TEST_N.get((s, tf))
                ok = hit >= getattr(config, "SURFACE_MIN_HIT_RATE", 0.6) and (n or 0) >= getattr(config, "SURFACE_MIN_TEST_N", 30)
                return {"tf": tf, "backtest_test_hit_pct": round(hit * 100, 1), "backtest_test_n": n, "meets_surface_bar": bool(ok)}
    except Exception:
        pass
    return {"tf": None, "backtest_test_hit_pct": None, "backtest_test_n": None, "meets_surface_bar": False}


def shadow_lane(v2_all, now):
    d30 = now - timedelta(days=30)
    by_sig = defaultdict(list)
    for r in v2_all:
        by_sig[r.get("signal_name") or "?"].append(r)
    out = {}
    for sig, rows in sorted(by_sig.items(), key=lambda kv: -len(kv[1])):
        months = defaultdict(list)
        for r in rows:
            months[_ts_key(r).strftime("%Y-%m")].append(r)
        out[sig] = {"lanes": sorted({r.get("source") for r in rows}),
                    "all": _stats(rows),
                    "last_30d": _stats([r for r in rows if _ts_key(r) >= d30]),
                    "by_direction": {d: _stats([r for r in rows if r.get("direction") == d])
                                     for d in ("short", "long") if any(r.get("direction") == d for r in rows)},
                    "by_month": {m: _stats(v) for m, v in sorted(months.items())},
                    "surface_bar": _surface_bar_for(sig)}
    return {"by_signal": out,
            "by_direction": {d: _stats([r for r in v2_all if r.get("direction") == d]) for d in ("short", "long")},
            "total": _stats(v2_all),
            "note": "all lanes (surfaced + shadow), v2 era, managed trade net of cost. ~6 rules x 2 directions x months = many cells: expect ~1 in 20 to look good by chance."}


# ---- 5. daily-pick study (forward) ----------------------------------------------------------
def daily_pick_study(v2_all, now):
    """Forward (live, v2-era) test of 'post the best candidate every day'. The priority order is
    FIXED from the 2026-09-23 backtest table (mechanical_setups.EXPECTANCY, descending) — chosen
    before any of this data existed — so these are out-of-sample numbers, not a fit."""
    try:
        import mechanical_setups as ms
        min_n = int(getattr(config, "SURFACE_MIN_TEST_N", 30) or 0)
        pri = {}
        # rules resting on >= SURFACE_MIN_TEST_N test trades first (by TEST hit rate), then the
        # thin-sample ones — a 73% on n=11 must not outrank a 66% on n=41
        for (sig, tf), hit in sorted(ms.EXPECTANCY.items(),
                                     key=lambda kv: ((ms.TEST_N.get(kv[0]) or 0) < min_n, -kv[1])):
            pri.setdefault(sig, len(pri))
    except Exception:
        pri = {}

    def key(r):
        return (pri.get(r.get("signal_name"), 99), r.get("rank") or 99, r["_run_ts"])

    def one_per_day(rows):
        days = defaultdict(list)
        for r in rows:
            days[_ts_key(r).date()].append(r)
        return [sorted(v, key=key)[0] for v in days.values()]

    if not v2_all:
        return {"priority": sorted(pri, key=pri.get), "span_days": 0, "policies": {}}
    first = min(_ts_key(r) for r in v2_all)
    span = max((now - first).days, 1)
    policies = {"best_rule_each_day": v2_all,
                "shorts_only": [r for r in v2_all if r.get("direction") == "short"],
                "longs_only": [r for r in v2_all if r.get("direction") == "long"]}
    for sig in sorted({r.get("signal_name") for r in v2_all if r.get("signal_name")}):
        policies[f"only_{sig}"] = [r for r in v2_all if r.get("signal_name") == sig]
    out = {"priority": sorted(pri, key=pri.get), "span_days": span, "policies": {}}
    for name, pool in policies.items():
        picks = one_per_day(pool)
        s = _stats(picks)
        s["days_with_pick"] = len(picks)
        s["days_with_pick_pct"] = round(100 * len(picks) / span, 1)
        out["policies"][name] = s
    out["bar"] = ("a daily policy becomes a promotion CANDIDATE only at >=60% profitable AND net>0 on >=30 "
                  "forward days, and may be surfaced only at >=70% + net>0; the 2026-09-23 backtest put "
                  "'best rule each day' at 54.5% / -0.112R on TEST (Jul-Sep), decaying month by month")
    return out


# ---- 6. backtest fade check ------------------------------------------------------------------
def backtest_fade(now, rule=FROZEN_RULE, tf=FROZEN_TF):
    # only full harness runs (unified_YYYYMMDD_trades.json) — study runs such as
    # unified_YYYYMMDD_cvd_trades.json use a smaller universe/window and are not comparable
    files = sorted(f for f in REPORT_DIR.glob("unified_*_trades.json")
                   if re.fullmatch(r"unified_\d{8}_trades\.json", f.name))
    if not files:
        return {"note": "no unified backtest trade log found — run `python monthly_review.py refresh-backtest`"}
    f = files[-1]
    try:
        ran = datetime.strptime(f.name[len("unified_"):len("unified_") + 8], "%Y%m%d").replace(tzinfo=timezone.utc)
        age = (now - ran).days
    except ValueError:
        ran, age = None, None
    freshness = "unknown" if age is None else ("fresh" if age <= 45 else "aging" if age <= 90 else "STALE")
    try:
        trades = json.loads(f.read_text(encoding="utf-8"))
    except Exception as e:
        return {"file": f.name, "error": str(e)}
    vmin = getattr(config, "RANGE_REVERSION_SHORT_MIN_VOL_SPIKE", None) if rule == FROZEN_RULE else None
    sel = [t for t in trades if t.get("signal") == rule and t.get("tf") == tf and t.get("result")
           and (vmin is None or (t.get("vol_spike") or 0) >= vmin)]

    def st(ts):
        n = len(ts)
        if not n:
            return {"n": 0, "prof_pct": None, "net": None}
        k = sum(1 for t in ts if t["result"].get("profitable"))
        nets = [t["result"].get("net_blended_rr") or 0.0 for t in ts]
        return {"n": n, "prof_pct": round(100 * k / n, 1), "net": round(sum(nets) / n, 3)}

    months = defaultdict(list)
    for t in sel:
        months[t["signal_time"][:7]].append(t)
    by_month = {m: st(v) for m, v in sorted(months.items())}
    keys = sorted(months)
    latest = by_month[keys[-1]] if keys else None
    prior = st([t for m in keys[:-1] for t in months[m]]) if len(keys) > 1 else None
    fading = bool(latest and prior and latest["n"] >= 5 and latest["prof_pct"] is not None
                  and prior["prof_pct"] is not None and latest["prof_pct"] < 60.0 <= prior["prof_pct"])
    return {"file": f.name, "run_date": ran.strftime("%Y-%m-%d") if ran else None, "age_days": age,
            "freshness": freshness, "rule": f"{rule} {tf}" + (f" + vol_spike>={vmin}" if vmin else ""),
            "all": st(sel), "by_month": by_month, "latest_month": keys[-1] if keys else None,
            "latest": latest, "prior_months": prior, "fading": fading,
            "note": "backtest = simulated trades on ~30 symbols (same rule, same trade_sim); ~17/month vs ~3 live, so this is the early warning. Treat a STALE file as no information."}


# ---- 7. scan coverage ------------------------------------------------------------------------
def coverage(now, days=30):
    recs = _read_jsonl(COVERAGE)
    cut = now - timedelta(days=days)
    out = {"days": days}
    if recs:
        start = max(cut, _utc(recs[0]["close"]))
        recent = [r for r in recs if _utc(r["close"]) >= cut]
        expected = max(int((now - start).total_seconds() // (4 * 3600)), 1)
        ok = sum(1 for r in recent if r.get("ok"))
        out.update({"ledger_since": recs[0]["close"], "closes_expected": expected, "closes_ok": ok,
                    "closes_logged": len(recent), "ok_pct": round(100 * ok / expected, 1)})
    else:
        out["note"] = "no scan-keeper ledger yet"
    n_scans = 0
    for f in SETUPS_DIR.glob("setups_*.json"):
        try:
            if datetime.strptime(f.name[len("setups_"):len("setups_") + 8], "%Y%m%d").replace(tzinfo=timezone.utc) >= cut:
                n_scans += 1
        except ValueError:
            pass
    out["scans_with_any_setup"] = n_scans
    return out


# ---- 8. recommendations ledger ---------------------------------------------------------------
def open_recommendations():
    return [r for r in _read_jsonl(_ledger()) if r.get("status") == "open"]


def ingest(review_text, tag):
    """Parse the review's fenced JSON block: new recommendations -> ledger (status open);
    grades for open ids -> appended, status updated when supported/refuted. Returns (new, graded)."""
    m = re.search(r"```json\s*(\{.*?\})\s*```", review_text, re.S)
    if not m:
        return 0, 0
    try:
        data = json.loads(m.group(1))
    except Exception:
        return 0, 0
    ledger = _read_jsonl(_ledger())
    by_id = {r.get("id"): r for r in ledger}
    graded = 0
    for g in data.get("grades") or []:
        rec = by_id.get(g.get("id"))
        grade = g.get("grade")
        if rec and rec.get("status") == "open" and grade in ("supported", "refuted", "inconclusive"):
            rec.setdefault("grades", []).append({"date": tag, "grade": grade, "evidence": g.get("evidence", "")})
            if grade != "inconclusive":
                rec["status"] = grade
            graded += 1
    new = 0
    existing = {r.get("id") for r in ledger}
    for i, rc in enumerate(data.get("recommendations") or [], 1):
        if not rc.get("claim"):
            continue
        rid = f"R-{tag}-{i}"
        if rid in existing:
            continue
        ledger.append({"id": rid, "date": tag, "claim": rc["claim"], "test": rc.get("test", ""),
                       "would_be_wrong_if": rc.get("would_be_wrong_if", ""),
                       "lane": rc.get("lane", "research"), "status": "open", "grades": []})
        new += 1
    _write_jsonl(_ledger(), ledger)
    return new, graded


# ---- facts file ------------------------------------------------------------------------------
def latest_facts(before_tag=None):
    files = sorted(OUT_DIR.glob("facts_*.json"))
    if before_tag:
        files = [f for f in files if f.stem.replace("facts_", "") < before_tag]
    return files[-1] if files else None


def _previous_summary(tag):
    f = latest_facts(before_tag=tag)
    if not f:
        return None
    try:
        p = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return None
    ft, b = p.get("forward_test_1", {}), p.get("band", {})
    books = (p.get("paper_test_2") or {}).get("books") or {}
    return {"date": f.stem.replace("facts_", ""),
            "forward_test_1": {k: ft.get(k) for k in ("n", "prof_pct", "net", "decision")},
            "band": {k: b.get(k) for k in ("n", "prof_pct", "net", "status")},
            "paper_test_2": {k: {"n_weeks": v.get("n_weeks"), "verdict": v.get("verdict")} for k, v in books.items()}}


def build_facts(all_evals, now=None):
    now = now or datetime.now(timezone.utc)
    tag = now.strftime("%Y-%m-%d")
    rows = collect(all_evals)
    v2_all = v2_rows(rows, LANES)
    v2_surf = v2_rows(rows, SURFACED)
    hist = _read_jsonl(_band_history())
    prev_band = next((h["status"] for h in reversed(hist) if h.get("date") != tag), None)
    return {
        "generated_at": now.isoformat(), "tag": tag, "review_cadence_days": int(getattr(config, "MONTHLY_REVIEW_DAYS", 30)),
        "goal": ("a proven, owned, fully mechanical Bybit USDT-perp edge that eventually trades itself; success = "
                 f">= {getattr(config, 'HIT_RATE_TARGET_PCT', 70)}% of SURFACED suggestions profitable (managed trade, net of cost) "
                 f"over >= {getattr(config, 'HIT_RATE_MIN_TRADES', 30)} forward trades AND net expectancy > 0"),
        "rules_in_force": {
            "surface_bar": f"a rule is shown only with TEST hit rate >= {getattr(config, 'SURFACE_MIN_HIT_RATE', 0.6) * 100:.0f}% on >= "
                           f"{getattr(config, 'SURFACE_MIN_TEST_N', 30)} out-of-sample trades; everything else is the shadow lane (scored, never shown, never counted)",
            "entry_model": getattr(config, "ENTRY_MODEL", "market"),
            "frozen_forward_test_1": FT1, "band": BAND,
            "validation_path": "unified_backtest.py only (chrono train/test, costs, same trade_sim as the evaluator); a rule that lives only in a backtest or only live is a bug",
            "frozen_while_clock_runs": "signal_rules.py detection of the frozen rule, its volume gate, ENTRY_MODEL, trade_sim management",
            "ai_reviewer": "report-only; read-only sandbox; may not change any rule; proposals go to the shadow lane / a new unified_backtest run with their own forward clock",
        },
        "forward_test_1": forward_test_1(v2_surf, now),
        "band": band(v2_surf, prev_band),
        "paper_test_2": paper_test_2(),
        "shadow_lane": shadow_lane(v2_all, now),
        "daily_pick_study": daily_pick_study(v2_all, now),
        "backtest_fade": backtest_fade(now),
        "coverage": coverage(now),
        "recommendations_open": open_recommendations(),
        "previous_review": _previous_summary(tag),
    }


def _p(x):
    return "—" if x is None else f"{x:.1f}%"


def _r(x):
    return "—" if x is None else f"{x:+.3f}R"


def _cell(s):
    if not s or not s.get("n"):
        return "n=0"
    ci = f" [{s['prof_ci'][0]:.0f}–{s['prof_ci'][1]:.0f}]" if s.get("prof_ci") and s["n"] >= 5 else ""
    return f"n={s['n']} · {_p(s['prof_pct'])}{ci} · {_r(s['net'])}"


def render_md(f):
    L = [f"# Monthly review facts — {f['tag']}",
         "_Generated by `monthly_review.py` (pure Python, zero tokens). Every figure comes from the eval logs and "
         "the pre-registered rules; the AI review may quote these figures and no others._", "",
         "## 0. Goal and rules in force", f"- Goal: {f['goal']}"]
    for k, v in f["rules_in_force"].items():
        L.append(f"- {k}: {v}")
    ft = f["forward_test_1"]
    L += ["", "## 1. Forward test #1 — the frozen rule (pre-registered 2026-09-23)",
          f"- Rule: {ft['rule']}",
          f"- Surfaced v2-era trades: **{_cell(ft)}** · net 95% CI {ft['net_ci']} · independent bets {ft['independent_bets']}",
          f"- Pre-registered rule: decide at n={FT1['n_decide']} (>= {FT1['promote_pct']:.0f}% + net>0 → EXECUTE small; "
          f"{FT1['extend_floor_pct']:.0f}–{FT1['promote_pct']:.0f}% → extend to n={FT1['n_extend']}; < {FT1['extend_floor_pct']:.0f}% → retire); "
          f"hard stops: < {FT1['kill_below_pct']:.0f}% after n={FT1['kill_after_n']}, or n<{FT1['n_decide']} by {FT1['expiry']} → family closed",
          f"- Days to expiry: {ft['days_to_expiry']}"
          + (f" · running {ft['days_running']} d · pace {ft['pace_per_week']} trades/week · projected n at expiry ≈ {ft['projected_n_at_expiry']}" if ft.get("days_running") else ""),
          f"- **Decision now: {ft['decision']}**"]
    if ft["trades"]:
        L.append("- Trades: " + ", ".join(f"{t['date']} {t['symbol']} {'✓' if t['profitable'] else '✗'} {t['net']:+.2f}R" for t in ft["trades"]))
    b = f["band"]
    L += ["", "## 2. Hit-rate band — surfaced book, last 30 trades",
          f"- Window: last {b['window']} surfaced v2 trades → **{_cell(b)}** → status **{b['status']}** (previous: {b['previous_status']})",
          f"- Meaning: {b['rule'][b['status']]}"]
    pt = f["paper_test_2"]
    L += ["", "## 3. Forward paper test #2 — XS momentum (pre-registered 2026-10-05)"]
    if "error" in pt:
        L.append(f"- {pt['error']}")
    else:
        L.append(f"- Bar: {pt['bar']} (rules_hash {pt['rules_hash']})")
        for book, s in pt["books"].items():
            L.append(f"- {book}: n={s['n_weeks']} weeks · cum {s['cum_net_pct']:+.2f}% · Sharpe {s['sharpe']} · maxDD {s['max_dd_pct']}% · "
                     f"weeks+ {s['pct_weeks_positive']}% → **{s['verdict']}**")
            if s["weeks"]:
                L.append("  - weeks: " + ", ".join(f"{w['week']} {w['net_pct']:+.2f}%" for w in s["weeks"]))
    sl = f["shadow_lane"]
    L += ["", "## 4. Shadow lane — everything the engine produced (v2 era, all lanes)", f"- {sl['note']}",
          f"- Total: {_cell(sl['total'])} · shorts: {_cell(sl['by_direction']['short'])} · longs: {_cell(sl['by_direction']['long'])}", "",
          "| rule | lanes | backtest TEST (bar?) | all v2 | last 30 d | shorts | longs | by month |", "|---|---|---|---|---|---|---|---|"]
    for sig, s in sl["by_signal"].items():
        sb = s["surface_bar"]
        bt = f"{_p(sb['backtest_test_hit_pct'])} n={sb['backtest_test_n']} ({'meets' if sb['meets_surface_bar'] else 'below'})"
        months = "; ".join(f"{m} {_cell(v)}" for m, v in s["by_month"].items())
        L.append(f"| {sig} | {','.join(s['lanes'])} | {bt} | {_cell(s['all'])} | {_cell(s['last_30d'])} | "
                 f"{_cell(s['by_direction'].get('short'))} | {_cell(s['by_direction'].get('long'))} | {months} |")
    dp = f["daily_pick_study"]
    L += ["", "## 5. Daily-pick study — 'one recommendation every day', forward", f"- Fixed priority: {' > '.join(dp['priority'])} · span {dp['span_days']} d",
          f"- Bar: {dp.get('bar', '')}", "", "| policy | days with a pick | result |", "|---|---|---|"]
    for name, s in dp["policies"].items():
        L.append(f"| {name} | {s['days_with_pick']} ({s['days_with_pick_pct']}%) | {_cell(s)} |")
    bf = f["backtest_fade"]
    L += ["", "## 6. Fade check — the frozen rule in the latest unified backtest"]
    if bf.get("note") and "by_month" not in bf:
        L.append(f"- {bf['note']}")
    elif "error" in bf:
        L.append(f"- {bf['file']}: {bf['error']}")
    else:
        L += [f"- File {bf['file']} (run {bf['run_date']}, {bf['age_days']} d old → **{bf['freshness']}**) · {bf['rule']}",
              f"- All period: {_cell(bf['all'])} · latest month {bf['latest_month']}: {_cell(bf['latest'])} · prior months: {_cell(bf['prior_months'])} → fading: **{bf['fading']}**",
              "- By month: " + "; ".join(f"{m} {_cell(v)}" for m, v in bf["by_month"].items()), f"- {bf['note']}"]
    cv = f["coverage"]
    L += ["", "## 7. Scan coverage — last 30 days"]
    if "closes_expected" in cv:
        L.append(f"- 4h closes scanned OK: {cv['closes_ok']}/{cv['closes_expected']} ({cv['ok_pct']}%) since ledger start {cv['ledger_since']} · scans that produced any setup: {cv['scans_with_any_setup']}")
    else:
        L.append(f"- {cv.get('note')} · scans that produced any setup: {cv['scans_with_any_setup']}")
    L += ["", "## 8. Open recommendations from earlier reviews (grade them)"]
    if f["recommendations_open"]:
        for r in f["recommendations_open"]:
            L.append(f"- {r['id']} ({r['date']}, lane {r.get('lane')}): {r['claim']} — test: {r.get('test')} — wrong if: {r.get('would_be_wrong_if', '')}")
    else:
        L.append("- none")
    pv = f["previous_review"]
    L += ["", "## 9. Previous review"]
    if pv:
        L.append(f"- {pv['date']}: forward test #1 {pv['forward_test_1']} · band {pv['band']} · paper {pv['paper_test_2']}")
    else:
        L.append("- none (first review)")
    return "\n".join(L) + "\n"


def maybe_write_facts(all_evals=None, force=False, now=None):
    """Write facts_<date>.{json,md} when the last facts file is >= MONTHLY_REVIEW_DAYS old (or
    none exists, or force). Returns the JSON path or None. Never raises past the caller's guard."""
    now = now or datetime.now(timezone.utc)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cadence = int(getattr(config, "MONTHLY_REVIEW_DAYS", 30))
    latest = latest_facts()
    if latest and not force:
        try:
            age = (now - _utc(json.loads(latest.read_text(encoding="utf-8"))["generated_at"])).days
        except Exception:
            age = cadence
        if age < cadence:
            print(f"Monthly review: last facts {latest.name} is {age} d old (< {cadence}) — not due.")
            return None
    if all_evals is None:
        all_evals = load_evals()
    facts = build_facts(all_evals, now)
    tag = facts["tag"]
    jp, mp = OUT_DIR / f"facts_{tag}.json", OUT_DIR / f"facts_{tag}.md"
    jp.write_text(json.dumps(facts, indent=2, default=str), encoding="utf-8")
    mp.write_text(render_md(facts), encoding="utf-8")
    hist = [h for h in _read_jsonl(_band_history()) if h.get("date") != tag]
    hist.append({"date": tag, **{k: facts["band"][k] for k in ("n", "wins", "prof_pct", "net", "status")}})
    hist.sort(key=lambda h: h.get("date", ""))   # a forced re-run keeps the ledger chronological
    _write_jsonl(_band_history(), hist)
    print(f"Monthly review: facts written → {mp} (forward test #1: {facts['forward_test_1']['decision']}; "
          f"band {facts['band']['status']}). Run `python monthly_review.py ai` locally for the AI pass.")
    return jp


# ---- figure check ----------------------------------------------------------------------------
_NUM = re.compile(r"[-+]?\d[\d,]*(?:\.\d+)?")


def _norm(tok):
    t = tok.replace(",", "").lstrip("+-").rstrip("%")
    if "." in t:
        t = t.rstrip("0").rstrip(".")
    return t or "0"


def facts_numbers(facts):
    """Every number the facts can legitimately support, in a few renderings (rounded, as %)."""
    nums = set()

    def walk(o):
        if isinstance(o, bool):
            return
        if isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, (list, tuple)):
            for v in o:
                walk(v)
        elif isinstance(o, (int, float)):
            for d in (0, 1, 2, 3):
                nums.add(_norm(f"{o:.{d}f}"))
            if isinstance(o, float) and abs(o) <= 1.0:
                for d in (0, 1):
                    nums.add(_norm(f"{o * 100:.{d}f}"))
        elif isinstance(o, str):
            for m in _NUM.finditer(o):
                nums.add(_norm(m.group()))
    walk(facts)
    for m in _NUM.finditer(render_md(facts)):
        nums.add(_norm(m.group()))
    return nums


_STRIP = [re.compile(r"\d{4}-\d{2}-\d{2}"), re.compile(r"\b\d{1,2}:\d{2}\b"), re.compile(r"\bR-[\d-]+\b"),
          re.compile(r"\bv\d+(?:\.\d+)*\b"), re.compile(r"```json.*?```", re.S), re.compile(r"\bk\d{2,3}\b"),
          re.compile(r"\b(?:1h|4h|15m|1d)\b")]


def check_figures(review_text, facts):
    """Figures in the review that the facts cannot support: list of (figure, context)."""
    allowed = facts_numbers(facts)
    text = review_text
    for rx in _STRIP:
        text = rx.sub(" ", text)
    bad = []
    for m in _NUM.finditer(text):
        tok = m.group()
        norm = _norm(tok)
        if "." not in norm and len(norm) == 1:   # single-digit counts ("2 of 3", "section 5") are free
            continue
        if norm in allowed:
            continue
        ctx = text[max(0, m.start() - 40):m.end() + 40].replace("\n", " ")
        bad.append((tok, ctx.strip()))
    return bad


# ---- AI pass (local, read-only) --------------------------------------------------------------
def build_prompt(facts_json_path):
    jp = Path(facts_json_path)
    mp = jp.with_suffix(".md")
    instructions = PROMPT_FILE.read_text(encoding="utf-8") if PROMPT_FILE.exists() else "Review the facts below."
    facts_md = mp.read_text(encoding="utf-8") if mp.exists() else render_md(json.loads(jp.read_text(encoding="utf-8")))
    return f"{instructions}\n\n---\n\n# FACTS FILE ({mp.name})\n\n{facts_md}"


def _telegram(text):
    try:
        import requests
        token, chat = getattr(config, "TELEGRAM_BOT_TOKEN", None), getattr(config, "TELEGRAM_CHAT_ID", None)
        if not token or not chat:
            return
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                      json={"chat_id": chat, "text": text[:3900]}, timeout=15)
    except Exception as e:
        print(f"  (telegram skipped: {e})")


def run_ai(facts_path=None, dry_run=False):
    jp = Path(facts_path) if facts_path else latest_facts()
    if not jp or not jp.exists():
        print("Monthly review: no facts file yet — run `python monthly_review.py facts --force`.")
        return 0
    tag = jp.stem.replace("facts_", "")
    review = OUT_DIR / f"review_{tag}.md"
    if review.exists():
        print(f"Monthly review: {review.name} already exists — nothing to do.")
        return 0
    prompt = build_prompt(jp)
    if dry_run:
        print(prompt)
        return 0
    codex = shutil.which("codex")
    if not codex:
        print("Monthly review: `codex` CLI not found — the facts file stands on its own.")
        return 0
    model = getattr(config, "MONTHLY_REVIEW_MODEL", "gpt-6.1-sol")
    effort = getattr(config, "MONTHLY_REVIEW_EFFORT", "medium")
    timeout = int(getattr(config, "MONTHLY_REVIEW_TIMEOUT_S", 1800))
    cmd = [codex, "exec", "-m", model, "-c", f'model_reasoning_effort="{effort}"', "-s", "read-only",
           "-C", str(Path.cwd()), "-o", str(review), "-"]
    print(f"Monthly review: running Codex ({model}, effort {effort}, read-only sandbox) on {jp.name} …")
    try:
        p = subprocess.run(cmd, input=prompt, text=True, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f"Monthly review: codex timed out after {timeout}s — facts stand alone.")
        return 0
    except Exception as e:
        print(f"Monthly review: codex failed to start ({e}) — facts stand alone.")
        return 0
    if p.returncode != 0 or not review.exists() or not review.read_text(encoding="utf-8").strip():
        print(f"Monthly review: codex failed (rc={p.returncode}) — facts stand alone.\n{p.stderr[-1200:]}")
        if review.exists():
            review.unlink()
        return 0
    text = review.read_text(encoding="utf-8")
    facts = json.loads(jp.read_text(encoding="utf-8"))
    bad = check_figures(text, facts)
    new, graded = ingest(text, tag)
    footer = [f"---", f"_Review by {model} (effort {effort}) via `codex exec -s read-only` on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC. "
              f"Report-only: nothing in the pipeline was changed. Recommendations recorded: {new}; earlier ones graded: {graded}._"]
    if bad:
        footer.append(f"\n### ⚠️ {len(bad)} figure(s) not found in the facts file — treat as unverified")
        for tok, ctx in bad[:40]:
            footer.append(f"- `{tok}` … {ctx}")
    else:
        footer.append("\n_Figure check: every number in this review appears in the facts file._")
    review.write_text(text.rstrip() + "\n\n" + "\n".join(footer) + "\n", encoding="utf-8")
    ft, b = facts["forward_test_1"], facts["band"]
    head = (f"🗓 Monthly review {tag}\nForward test #1: {ft['decision']}\nBand: {b['status']} ({_cell(b)})\n"
            f"Recommendations recorded: {new} · unverified figures: {len(bad)}\n→ {review}")
    print(head)
    _telegram(head)
    return 0


def refresh_backtest(days=90, max_symbols=30):
    """Fresh unified backtest for the frozen rule only (the fade check reads the newest trade log)."""
    cmd = [sys.executable, "unified_backtest.py", "--signals", FROZEN_RULE, "--tfs", FROZEN_TF,
           "--days", str(days), "--max-symbols", str(max_symbols), "--no-derivs"]
    print("Monthly review: " + " ".join(cmd))
    return subprocess.run(cmd).returncode


def status():
    jp = latest_facts()
    if not jp:
        print("No facts file yet.")
        return
    f = json.loads(jp.read_text(encoding="utf-8"))
    review = OUT_DIR / f"review_{f['tag']}.md"
    print(f"Facts: {jp.name} ({f['generated_at'][:16]})")
    print(f"  forward test #1: {f['forward_test_1']['decision']}")
    print(f"  band: {f['band']['status']} — {_cell(f['band'])}")
    for book, s in (f.get("paper_test_2") or {}).get("books", {}).items():
        print(f"  paper {book}: {s['verdict']}")
    print(f"  review: {'present → ' + str(review) if review.exists() else 'not yet (run: python monthly_review.py ai)'}")
    opens = open_recommendations()
    print(f"  open recommendations: {len(opens)}" + ("".join(f"\n    - {r['id']}: {r['claim']}" for r in opens) if opens else ""))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    s = sub.add_parser("facts"); s.add_argument("--force", action="store_true")
    s = sub.add_parser("ai"); s.add_argument("--facts"); s.add_argument("--dry-run", action="store_true")
    s = sub.add_parser("check"); s.add_argument("review"); s.add_argument("--facts")
    s = sub.add_parser("refresh-backtest"); s.add_argument("--days", type=int, default=90); s.add_argument("--max-symbols", type=int, default=30)
    sub.add_parser("status")
    a = ap.parse_args(argv)
    if a.cmd == "facts":
        return 0 if maybe_write_facts(force=a.force) or not a.force else 1
    if a.cmd == "ai":
        return run_ai(a.facts, a.dry_run)
    if a.cmd == "check":
        jp = Path(a.facts) if a.facts else latest_facts()
        bad = check_figures(Path(a.review).read_text(encoding="utf-8"), json.loads(jp.read_text(encoding="utf-8")))
        print(f"{len(bad)} unverified figure(s)" + "".join(f"\n- {t} … {c}" for t, c in bad))
        return 0
    if a.cmd == "refresh-backtest":
        return refresh_backtest(a.days, a.max_symbols)
    status()
    return 0


if __name__ == "__main__":
    sys.exit(main())
