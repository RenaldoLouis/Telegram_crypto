"""Weekly review of the daily trader book (user decision 2026-10-19).

"A trader for a living reviews every week." Every Monday (the scan keeper runs this after the
00:00 UTC close and the daily auto-score) this writes
logs/performance/weekly/review_<monday>.md for the week that just ended and sends a short
Telegram version. It reads only the daily-book picks (`daily_pick` on the setup/eval records):

  * the week: picks made, scored / not filled / still inside their 2-day window, profitable %,
    net R per trade and total (the managed trade, same definition as every other readout)
  * by direction and by setup, the trial so far, and the last weeks side by side
  * the rule fixed 2026-10-19: a direction or setup with >= DAILY_CUT_MIN_TRADES scored picks and
    net < 0 is flagged CUT. The review RECOMMENDS; the cut itself is one line in config.py
    (DAILY_DIRECTIONS / DAILY_DISABLED_SIGNALS) so the system never rewrites its own rules.
  * the carry line (`carry_monitor.py`, 2026-10-20): what BTC/ETH cash-and-carry pays on Bybit now
    (description only — the one Bybit fetch in this script; the review still saves if it fails).

Pure Python, zero Claude, no order API.

Usage:
    python weekly_review.py                    # the last completed week (Mon-Sun, UTC)
    python weekly_review.py --week 2026-10-19  # a specific week (its Monday)
    python weekly_review.py --no-telegram
"""

import argparse
import json
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import carry_monitor
import config
import monthly_review as mr

OUT_DIR = Path(__file__).parent / "logs" / "performance" / "weekly"
SETUPS_DIR = Path(__file__).parent / "logs" / "setups"
RISK_PCT = 0.5   # paper sizing in the brief: % of the account risked per trade
# Trader's checklist forward test (pre-registered 2026-10-21, prereg_checklist_confirm_20261021.md)
CHECKLIST_MIN_SCORE = 5
CHECKLIST_N_DECIDE = 30


def _monday(d):
    return d - timedelta(days=d.weekday())


def load_picks(all_evals=None, setups_dir=SETUPS_DIR):
    """Every daily-book pick with its status: 'scored' (eval row attached), 'not_filled',
    'duplicate', or 'waiting' (no eval yet). Returns a list of dicts, oldest first."""
    all_evals = mr.load_evals() if all_evals is None else all_evals
    status, scored = {}, {}
    for ev in all_evals:
        for r in ev.get("results", []):
            k = (ev.get("run_tag"), r.get("symbol"), r.get("source", "claude"))
            status[k] = r.get("status")
    for r in mr.collect(all_evals):
        if r.get("daily_pick"):
            scored[(r.get("_run_tag"), r.get("symbol"), r.get("source", "claude"))] = r
    picks = []
    for f in sorted(Path(setups_dir).glob("setups_*.json")):
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        ts = datetime.fromisoformat(rec["run_timestamp_utc"])
        for s in rec.get("setups", []):
            if not s.get("daily_pick"):
                continue
            k = (rec.get("run_tag"), s.get("symbol"), s.get("source", "claude"))
            st = status.get(k)
            picks.append({
                "ts": ts, "symbol": s.get("symbol"), "direction": s.get("direction"),
                "signal": s.get("signal_name"), "source": s.get("source"),
                "status": "scored" if k in scored else (st if st in ("not_filled", "duplicate") else "waiting"),
                "row": scored.get(k),
            })
    return sorted(picks, key=lambda p: p["ts"])


def _line(rows):
    s = mr._stats(rows)
    if not s["n"]:
        return "no scored picks", s
    total = s["net"] * s["n"]
    return (f"{s['n']} scored · **{s['prof_pct']:.0f}% profitable** · net {s['net']:+.2f}R/trade · "
            f"total {total:+.1f}R (≈ {total * RISK_PCT:+.1f}% of the account at {RISK_PCT}% risk)"), s


def cut_flags(rows, min_n=None):
    """{('direction'|'setup', name): (verdict, stats)} — CUT when n >= min_n and net < 0."""
    min_n = int(min_n or getattr(config, "DAILY_CUT_MIN_TRADES", 20))
    groups = defaultdict(list)
    for r in rows:
        groups[("direction", r.get("direction"))].append(r)
        groups[("setup", r.get("signal_name"))].append(r)
    out = {}
    for k, rs in sorted(groups.items(), key=lambda kv: (kv[0][0], str(kv[0][1]))):
        s = mr._stats(rs)
        if s["n"] >= min_n:
            out[k] = ("CUT" if s["net"] < 0 else "KEEP", s)
        else:
            out[k] = (f"building {s['n']}/{min_n}", s)
    return out


def checklist_lines(rows):
    """Forward test of the trader's checklist: every scored candidate (all lanes) stamped with a
    checklist that had its funding/OI data — score >= CHECKLIST_MIN_SCORE vs all. Ready for the
    user's decision at CHECKLIST_N_DECIDE scored high-score candidates with net > 0 and above all."""
    rows = [r for r in rows if (r.get("checklist") or {}).get("derivs_ok")]
    high = [r for r in rows if r["checklist"]["score"] >= CHECKLIST_MIN_SCORE]
    s_all, s_hi = mr._stats(rows), mr._stats(high)
    fmt = lambda s: (f"{s['n']} scored · {s['prof_pct']:.0f}% profitable · net {s['net']:+.2f}R/trade"
                     if s["n"] else "none scored yet")
    L = [f"\n## Checklist forward test (score ≥ {CHECKLIST_MIN_SCORE} of 9; logged since 2026-10-21, changes no pick)",
         f"- score ≥ {CHECKLIST_MIN_SCORE}: {fmt(s_hi)}", f"- all candidates: {fmt(s_all)}"]
    if s_hi["n"] < CHECKLIST_N_DECIDE:
        L.append(f"- Status: building {s_hi['n']}/{CHECKLIST_N_DECIDE}.")
    elif s_hi["net"] > 0 and s_hi["net"] > s_all["net"]:
        L.append("- Status: **READY** — high-score candidates are net positive and beat all candidates; "
                 "your call whether the daily book picks by checklist score.")
    else:
        L.append("- Status: **NOT CONFIRMED** — high-score candidates are not net positive or do not beat all.")
    return L


def build(week_monday, picks, today=None, carry=None, checklist_rows=None):
    today = today or datetime.now(timezone.utc).date()
    week_end = week_monday + timedelta(days=6)
    start = date.fromisoformat(getattr(config, "DAILY_TRIAL_START", week_monday.isoformat()))
    trial_days = int(getattr(config, "DAILY_TRIAL_DAYS", 14))
    decision_day = _monday(start + timedelta(days=trial_days - 1)) + timedelta(days=7)
    week = [p for p in picks if week_monday <= p["ts"].date() <= week_end]
    trial = [p for p in picks if p["ts"].date() >= start]
    rows_week = [p["row"] for p in week if p["row"]]
    rows_trial = [p["row"] for p in trial if p["row"]]

    L = [f"# Weekly review — {week_monday:%a %Y-%m-%d} → {week_end:%a %Y-%m-%d}",
         f"\nDaily trader book (up to {getattr(config, 'DAILY_PICKS_MAX', 3)} picks a day, both directions). "
         f"Paper trial started {start}, {trial_days} days; real-money decision after the {decision_day} review. "
         f"Generated {today}."]

    counts = defaultdict(int)
    for p in week:
        counts[p["status"]] += 1
    L.append("\n## This week")
    L.append(f"- Picks made: {len(week)} (scored {counts['scored']}, not filled {counts['not_filled']}, "
             f"still inside their 2-day window {counts['waiting']}"
             + (f", duplicates {counts['duplicate']}" if counts["duplicate"] else "") + ")")
    wl, _ = _line(rows_week)
    L.append(f"- Result: {wl}")
    for d in ("short", "long"):
        dl, _ = _line([r for r in rows_week if r.get("direction") == d])
        L.append(f"- {d}s: {dl}")

    L.append("\n## Trial so far")
    tl, _ = _line(rows_trial)
    L.append(f"- {tl}")

    L.append("\n## Weeks side by side")
    L.append("| week | picks | scored | profitable | net R/trade | total R |")
    L.append("|---|---|---|---|---|---|")
    by_w = defaultdict(list)
    for p in trial:
        by_w[_monday(p["ts"].date())].append(p)
    for w in sorted(by_w):
        rs = [p["row"] for p in by_w[w] if p["row"]]
        s = mr._stats(rs)
        L.append(f"| {w} | {len(by_w[w])} | {s['n']} | "
                 + (f"{s['prof_pct']:.0f}% | {s['net']:+.2f} | {s['net'] * s['n']:+.1f} |" if s["n"] else "– | – | – |"))

    L.append(f"\n## Keep or cut (rule fixed 2026-10-19: ≥ {getattr(config, 'DAILY_CUT_MIN_TRADES', 20)} "
             "scored picks with net < 0 → cut)")
    flags = cut_flags(rows_trial)
    actions = []
    for (kind, name), (verdict, s) in flags.items():
        stat = f"{s['n']} scored, {s['prof_pct']:.0f}% / {s['net']:+.2f}R" if s["n"] else "0 scored"
        L.append(f"- {kind} `{name}`: **{verdict}** ({stat})")
        if verdict == "CUT":
            actions.append(f"{kind} {name}")
    if actions:
        L.append("\n**ACTION:** cut " + ", ".join(actions) + " — one line in config.py "
                 "(DAILY_DIRECTIONS / DAILY_DISABLED_SIGNALS). The system does not change its own rules.")
    else:
        L.append("\nNo cut this week.")

    L.append("")
    L.extend(carry_monitor.format_lines(carry))

    if checklist_rows is not None:
        L.extend(checklist_lines(checklist_rows))

    L.append("\n## Picks this week")
    L.append("| when (UTC) | coin | side | setup | status | net R |")
    L.append("|---|---|---|---|---|---|")
    for p in week:
        r = p["row"]
        net = f"{mr.we._managed_rr(r)[1]:+.2f}" if r else "–"
        L.append(f"| {p['ts']:%a %m-%d %H:%M} | {p['symbol']} | {p['direction']} | {p['signal']} | {p['status']} | {net} |")
    return "\n".join(L), actions


def telegram_text(md):
    """Short version: header, this week, trial so far, cut verdicts."""
    keep = []
    for block in md.split("\n## "):
        head = block.split("\n", 1)[0]
        if (block.startswith("# ") or head in ("This week", "Trial so far") or head.startswith("Keep or cut")
                or head.startswith("Carry") or head.startswith("Checklist")):
            keep.append(block if block.startswith("# ") else "## " + block)
    return "\n".join(keep).replace("# Weekly review", "📅 Weekly review", 1)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--week", help="Monday of the week to review (default: the last completed week)")
    ap.add_argument("--no-telegram", action="store_true")
    args = ap.parse_args(argv)
    today = datetime.now(timezone.utc).date()
    monday = date.fromisoformat(args.week) if args.week else _monday(today) - timedelta(days=7)
    carry = None
    try:
        from fetchers.bybit_data import BybitFetcher
        carry = carry_monitor.fetch(BybitFetcher())
    except Exception as e:
        print(f"⚠ carry fetch failed ({type(e).__name__}: {e}) — the review says so")
    all_evals = mr.load_evals()
    md, actions = build(monday, load_picks(all_evals), today, carry=carry, checklist_rows=mr.collect(all_evals))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"review_{monday}.md"
    out.write_text(md, encoding="utf-8")
    print(md)
    print(f"\nSaved {out}")
    if not args.no_telegram:
        try:
            from delivery.telegram_bot import send_brief
            send_brief(telegram_text(md))
        except Exception as e:
            print(f"⚠ Telegram send failed ({type(e).__name__}: {e}) — the file is saved")


if __name__ == "__main__":
    main()
