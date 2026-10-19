import re
import time
import requests
from requests.exceptions import ConnectionError, Timeout
import config


def _send_with_retry(url, payload, max_retries=3):
    """Send a Telegram API request with retry on network errors."""
    for attempt in range(1, max_retries + 1):
        try:
            r = requests.post(url, json=payload, timeout=30)
            return r
        except (ConnectionError, Timeout) as e:
            if attempt < max_retries:
                wait = attempt * 2
                print(f"  Network error (attempt {attempt}/{max_retries}), retrying in {wait}s: {e}")
                time.sleep(wait)
            else:
                print(f"  Telegram send failed after {max_retries} attempts: {e}")
                return None


def _md_to_telegram_html(text):
    """Convert Claude's markdown brief to clean Telegram HTML."""
    lines = text.split("\n")
    result = []

    for line in lines:
        # --- horizontal rules → blank line
        if re.match(r"^-{3,}$", line.strip()):
            result.append("")
            continue

        # ### H3 headers → bold with emoji preserved
        if line.startswith("### "):
            content = line[4:].strip()
            content = _inline_format(content)
            result.append(f"\n<b>{content}</b>")
            continue

        # ## H2 headers → bold + separator line
        if line.startswith("## "):
            content = line[3:].strip()
            content = _inline_format(content)
            result.append(f"\n{'━' * 28}\n<b>{content}</b>")
            continue

        # # H1 headers → bold uppercase
        if line.startswith("# "):
            content = line[2:].strip()
            content = _inline_format(content)
            result.append(f"<b>{content}</b>")
            continue

        # Regular lines — convert inline markdown
        result.append(_inline_format(line))

    return "\n".join(result).strip()


def _inline_format(text):
    """Convert inline markdown (**bold**, *italic*, `code`) to HTML."""
    # Escape HTML special chars first (but not our tags)
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;").replace(">", "&gt;")

    # **bold** → <b>bold</b>
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)

    # *italic* → <i>italic</i> (but not inside already-converted <b> tags)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", text)

    # `code` → <code>code</code>
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)

    # _italic_ → <i>italic</i> (only standalone, not mid_word)
    text = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"<i>\1</i>", text)

    return text


def _smart_chunk(text, max_len=4000):
    """Split text on section boundaries (━━━ lines) rather than mid-sentence."""
    sections = re.split(r"(━{10,})", text)

    chunks = []
    current = ""

    for section in sections:
        if len(current) + len(section) + 1 > max_len and current:
            chunks.append(current.strip())
            current = ""
        current += section + "\n"

    if current.strip():
        chunks.append(current.strip())

    # If any chunk is still too long, hard-split it
    final = []
    for chunk in chunks:
        if len(chunk) <= max_len:
            final.append(chunk)
        else:
            for i in range(0, len(chunk), max_len):
                final.append(chunk[i:i + max_len])

    return final


def _fmt_price(p):
    """Format a price with a sensible number of significant digits."""
    try:
        p = float(p)
    except (TypeError, ValueError):
        return str(p)
    ap = abs(p)
    if ap >= 100:
        return f"{p:,.2f}"
    if ap >= 1:
        return f"{p:.4f}"
    return f"{p:.6f}"


def _t2_rr(setup):
    """R:R to target_2 from mid-entry (for display)."""
    try:
        entry_mid = (float(setup["entry_low"]) + float(setup["entry_high"])) / 2
        risk = abs(entry_mid - float(setup["stop_loss"]))
        t2 = float(setup["target_2"])
        if risk <= 0:
            return None
        return (t2 - entry_mid) / risk if setup.get("direction") == "long" else (entry_mid - t2) / risk
    except (KeyError, TypeError, ValueError):
        return None


def _format_watch_block(watch):
    """Render the WATCH section — every surfaced candidate (paper-track-only)."""
    plural = "s" if len(watch) > 1 else ""
    lines = [f"\n## 👀 Watch Candidate{plural} (below execute bar — paper-track only)"]
    for w in watch:
        lines.extend(_format_watch_one(w))
    return lines


def _format_watch_one(w):
    """One WATCH candidate's explanation + trade plan."""
    direction = (w.get("direction") or "?").capitalize()
    lines = []
    sig = w.get("signal_name", "?")
    if sig == "observation":
        lines.append("_No validated signal fired anywhere this scan. This is the "
                     "highest-interest coin in its dominant trend — an OBSERVATION, "
                     "not a signal. Track it on paper to feed the eval loop; do NOT "
                     "size it like an execute setup._")
    else:
        exp = w.get("signal_expectancy")
        exp_str = f" · backtest hit rate {exp*100:.0f}% (net of cost)" if isinstance(exp, (int, float)) else ""
        lines.append(f"_Signal `{sig}` passed the structural gates but has not yet proven the "
                     f"70% forward bar{exp_str}. Paper-track it; eval-scan scores it under the "
                     "unified trade model._")
    pr = w.get("predicted_rr")
    t2rr = _t2_rr(w)
    pr_str = f" (R:R {pr:.2f}:1)" if isinstance(pr, (int, float)) else ""
    t2_str = f" (R:R {t2rr:.2f}:1)" if t2rr is not None else ""
    lines.append(f"\n### {w.get('symbol','?')} | {direction} | Watch")
    lines.append("**Trade Plan:**")
    lines.append(_entry_line(w))
    lines.append(f"- Stop loss: {_fmt_price(w.get('stop_loss'))}")
    lines.append(f"- Target 1: {_fmt_price(w.get('target_1'))}{pr_str} — partial profit, take 50%")
    lines.append(f"- Target 2: {_fmt_price(w.get('target_2'))}{t2_str} — reward leg")
    lines.append(f"- Confidence: {w.get('confidence','low')} · TF confluence: {w.get('tf_confluence','?')}/4")
    kf = (w.get("reasoning") or {}).get("key_factor")
    if kf:
        lines.append(f"- Key factor: {kf}")
    return lines


def _entry_line(s):
    """Entry instruction consistent with config.ENTRY_MODEL (what the evaluator scores)."""
    lo, hi = s.get("entry_low"), s.get("entry_high")
    try:
        mid = (float(lo) + float(hi)) / 2
    except (TypeError, ValueError):
        mid = None
    if getattr(config, "ENTRY_MODEL", "market") == "limit_open":
        wait_min = int(getattr(config, "LIMIT_WAIT_BARS", 2)) * 15
        return (f"- Entry: post-only LIMIT at ~{_fmt_price(mid)} (current price; maker fee), "
                f"cancel if not filled within {wait_min} min — do NOT chase")
    return f"- Entry: at market now (signal bar closed; reference {_fmt_price(lo)} — {_fmt_price(hi)})"


def _format_engine_view(items):
    """Render the Engine View (2026-10-16): the best recent SHADOW candidates — rules that have
    not passed the surfacing bar — with their measured numbers and an explicit label. Shown so
    no day is blind; never a recommendation, never counted (source stays "shadow")."""
    bar = (f"≥{getattr(config, 'SURFACE_MIN_HIT_RATE', 0.6) * 100:.0f}% profitable on "
           f"≥{getattr(config, 'SURFACE_MIN_TEST_N', 30)} out-of-sample test trades")
    lines = ["\n## 🔬 Engine View (below bar — NOT a recommendation, not counted)",
             f"_What the engine saw but did not surface. Each rule below has not passed the bar ({bar}); "
             "these rows are paper-tracked in the shadow lane. Levels are the engine's, numbers are measured._"]
    for s in items:
        direction = (s.get("direction") or "?").capitalize()
        sig, tf = s.get("signal_name", "?"), s.get("signal_tf", "?")
        fired = s.get("_issued_at")
        exp, n = s.get("signal_expectancy"), s.get("signal_test_n")
        bt = (f"backtest TEST {exp * 100:.0f}% (n={n})" if isinstance(exp, (int, float)) else "backtest: n/a")
        live = s.get("_lane_live") or {}
        if live.get("n"):
            lv = f"live shadow last {live['n']}: {live['prof_pct']:.0f}% / {live['net']:+.2f}R"
        else:
            lv = "live shadow: no scored trades yet"
        lines.append(f"\n**{s.get('symbol', '?')} | {direction} | `{sig}` ({tf})"
                     + (f" · fired {fired}" if fired else "") + "**")
        lines.append(_entry_line(s))
        lines.append(f"- Stop {_fmt_price(s.get('stop_loss'))} · T1 {_fmt_price(s.get('target_1'))} · "
                     f"T2 {_fmt_price(s.get('target_2'))}")
        lines.append(f"- {bt} · {lv}")
    return lines


def _usd(x):
    if x is None:
        return "n/a"
    x = float(x)
    if abs(x) >= 1e9:
        return f"${x / 1e9:.1f}B"
    if abs(x) >= 1e6:
        return f"${x / 1e6:.1f}M"
    if abs(x) >= 1e3:
        return f"${x / 1e3:.0f}K"
    return f"${x:.0f}"


def _who_got_hit(long_usd, short_usd):
    if long_usd + short_usd <= 0:
        return "quiet"
    if long_usd >= 2 * short_usd:
        return "mostly longs wiped out"
    if short_usd >= 2 * long_usd:
        return "mostly shorts wiped out"
    return "both sides"


def _format_context(c, regime):
    """BTC-first market section (2026-10-19). Description only — never a trade input."""
    def pct(x, nd=1):
        return f"{x:+.{nd}f}%" if isinstance(x, (int, float)) else "n/a"
    lines = ["## 📈 Market — BTC first"]
    trend = f"daily {c.get('trend_1d') or 'n/a'}, 4h {c.get('trend_4h') or 'n/a'}"
    rsi = c.get("rsi_1d")
    adx = c.get("adx_1d")
    lines.append(f"- **BTC {_fmt_price(c.get('price'))}** ({pct(c.get('chg_24h'))} 24h) · trend: {trend}"
                 + (f" · daily RSI {rsi:.0f}" if isinstance(rsi, (int, float)) else "")
                 + (f", ADX {adx:.0f}" if isinstance(adx, (int, float)) else ""))
    vr = c.get("vol_ratio_1d")
    lines.append("- Volume: " + (f"yesterday {vr:.1f}× its 20-day average" if isinstance(vr, (int, float)) else "n/a")
                 + f" · 24h turnover {_usd(c.get('turnover_24h'))}")
    fp = c.get("funding_pct")
    lines.append("- Leverage: funding " + (f"{fp:+.4f}%/8h" if isinstance(fp, (int, float)) else "n/a")
                 + f" · open interest {pct(c.get('oi_chg_24h'))} (24h)")
    cov = c.get("liq_hours_covered") or 0
    if cov:
        lg, sh = c.get("liq_long_24h") or 0.0, c.get("liq_short_24h") or 0.0
        verdict = _who_got_hit(lg, sh) if cov >= 12 else "partial data, no verdict yet"
        nc = c.get("liq_coins", 0)
        lines.append(f"- Liquidations, last 24h ({nc} coin{'s' if nc != 1 else ''} with prints, "
                     f"feed up {cov}/24 h): longs {_usd(lg)} · shorts {_usd(sh)} → {verdict} · "
                     f"BTC longs {_usd(c.get('liq_btc_long_24h'))} / shorts {_usd(c.get('liq_btc_short_24h'))} · "
                     f"last 4h longs {_usd(c.get('liq_long_4h'))} / shorts {_usd(c.get('liq_short_4h'))}")
    else:
        lines.append("- Liquidations: no feed data in the last 24h yet")
    if c.get("prev_high") is not None:
        lines.append(f"- Levels: yesterday H {_fmt_price(c.get('prev_high'))} / L {_fmt_price(c.get('prev_low'))}"
                     + (f" · 20-day range {_fmt_price(c.get('low_20d'))} – {_fmt_price(c.get('high_20d'))}"
                        if c.get("high_20d") is not None else ""))
    pdcl = c.get("pct_declining")
    lines.append("- Breadth: " + (f"{pdcl:.0f}% of coins down (median {pct(c.get('median_chg'))})"
                                  if isinstance(pdcl, (int, float)) else "n/a")
                 + f" · regime: **{c.get('regime') or regime}**")
    return lines


def _trial_label():
    """'paper trial day N of D' for the daily book (config.DAILY_TRIAL_*), or None."""
    try:
        from datetime import date, datetime, timezone
        start = date.fromisoformat(getattr(config, "DAILY_TRIAL_START", ""))
        days = int(getattr(config, "DAILY_TRIAL_DAYS", 14))
        n = (datetime.now(timezone.utc).date() - start).days + 1
    except Exception:
        return None
    if n < 1:
        return None
    if n <= days:
        return f"paper trial, day {n} of {days}"
    return "paper trial over — real-money decision is yours"


def _format_pick(p):
    direction = (p.get("direction") or "?").capitalize()
    cap = getattr(config, "DAILY_PICKS_MAX", 3)
    lines = [f"\n### {p.get('symbol', '?')} | {direction} | `{p.get('signal_name', '?')}` "
             f"({p.get('signal_tf', '?')}) — pick {p.get('daily_pick_seq', '?')} of {cap} today"]
    lines.append(_entry_line(p))
    pr, t2rr = p.get("predicted_rr"), _t2_rr(p)
    lines.append(f"- Stop loss: {_fmt_price(p.get('stop_loss'))}")
    lines.append(f"- Target 1: {_fmt_price(p.get('target_1'))}"
                 + (f" ({pr:.2f}R)" if isinstance(pr, (int, float)) else "") + " — take 50%")
    lines.append(f"- Target 2: {_fmt_price(p.get('target_2'))}"
                 + (f" ({t2rr:.2f}R)" if t2rr is not None else ""))
    exp, n = p.get("signal_expectancy"), p.get("signal_test_n")
    rec = (f"backtest {exp * 100:.0f}% profitable (n={n})" if isinstance(exp, (int, float)) else "backtest n/a")
    live = p.get("_lane_live") or {}
    if live.get("n"):
        rec += f" · live last {live['n']}: {live['prof_pct']:.0f}% / {live['net']:+.2f}R"
    lines.append(f"- Record: {rec}")
    kf = (p.get("reasoning") or {}).get("key_factor")
    if kf:
        lines.append(f"- Why: {kf}")
    if p.get("source") == "watch":
        lines.append("- This is forward test #1's rule — it counts there too.")
    return lines


def _format_daily_brief(setups, regime, watch, engine_view, daily, earlier, context):
    """Daily trader brief (2026-10-19): BTC context, today's picks, then the legacy lanes."""
    cap = getattr(config, "DAILY_PICKS_MAX", 3)
    lines = _format_context(context, regime) if context else [f"## 📈 Market\nRegime: **{regime}**."]
    trial = _trial_label()
    lines.append(f"\n## 🎯 Today's Trades" + (f" ({trial})" if trial else ""))
    for p in daily:
        lines.extend(_format_pick(p))
    if not daily:
        lines.append("No new pick this scan." if earlier else
                     "No setup has cleared the engine's gates yet today — no forced trade.")
    if earlier:
        lines.append("\n**Earlier today:** " + "; ".join(
            f"{e.get('symbol', '?')} {e.get('direction', '?')} via `{e.get('signal_name', '?')}` "
            f"({e.get('_issued_at', '?')})" for e in earlier))
    lines.append(f"_{len(earlier) + len(daily)} of {cap} picks used today (UTC day). Every pick is scored "
                 "automatically and judged in Monday's weekly review._")
    if setups:
        lines.append("\n## 🏆 Validated Setups")
        for s in setups:
            lines.extend(_format_pick(dict(s, daily_pick_seq="—")))
    watch_show = [w for w in (watch or []) if not w.get("daily_pick")]
    if watch_show:
        lines.extend(_format_watch_block(watch_show))
    if engine_view:
        lines.extend(_format_engine_view(engine_view))
    if daily or setups or watch_show:
        lines.append("\n## ⚠️ Position Management")
        lines.append("- Take 50% at T1, move the stop to breakeven. Once +1R, tighten the stop to +0.3R "
                     "and let the rest run to T2. Paper: risk 0.5% of the account per trade.")
    lines.append("\n## 🧠 One-Line Takeaway")
    if daily:
        lines.append("Record these as paper trades. The system scores every pick; Monday's review "
                     "decides what stays.")
    else:
        lines.append("Nothing new to take this scan.")
    return "\n".join(lines)


def format_mechanical_brief(setups, regime="neutral", watch=None, engine_view=None,
                            daily=None, earlier=None, context=None):
    """Render mechanically-constructed setups as a markdown brief in the same style
    as Claude's output, so send_brief() can deliver it unchanged. Pure formatting —
    no analysis. Used when PRIMARY_SOURCE == 'mechanical' or Claude failed.

    `watch` (optional) is the list of surfaced WATCH candidates (every gated candidate
    whose rule clears the surfacing bars; may be empty — an empty brief is valid).
    `engine_view` (optional, 2026-10-16) is the list of best recent SHADOW candidates,
    rendered under an explicit below-bar label (see main._engine_view).
    `daily` (2026-10-19): when given (a list, possibly empty) the brief is the daily trader
    layout — BTC `context` first, this scan's daily-book picks, `earlier` picks of the day.
    When None the legacy layout below is produced unchanged.
    """
    if daily is not None:
        return _format_daily_brief(setups, regime, watch, engine_view, daily, earlier or [], context)
    ev_lines = _format_engine_view(engine_view) if engine_view else []
    lines = ["## 📊 Market Context (mechanical engine)"]
    if not setups:
        if watch:
            lines.append(
                f"Regime: **{regime}**. No signal cleared the validated execute bar this "
                "scan — 0 execute setups. Surfacing the best available candidate to watch "
                "(no forced trade)."
            )
            lines.extend(_format_watch_block(watch))
            lines.extend(ev_lines)
            lines.append("\n## 🧠 One-Line Takeaway")
            n_w = len(watch)
            lines.append(f"Nothing to EXECUTE — {n_w} candidate{'s' if n_w != 1 else ''} to WATCH "
                         "and paper-track. You make the call; no forced trade.")
            return "\n".join(lines)
        lines.append(
            f"Regime: **{regime}**. No backtest-validated signals fired this scan — "
            "0 setups. An empty scan is a valid outcome; no forced trades."
        )
        lines.extend(ev_lines)
        lines.append("\n## 🧠 One-Line Takeaway")
        if ev_lines:
            lines.append("Nothing met the validated-signal bar. Stand aside — the Engine View above is "
                         "what the engine saw, not a trade.")
        else:
            lines.append("Nothing met the validated-signal bar. Stand aside.")
        return "\n".join(lines)

    lines.append(
        f"Regime: **{regime}**. {len(setups)} setup(s) from backtest-validated signals "
        "(deterministic — no LLM). Ranked by out-of-sample expectancy."
    )
    lines.append("\n## 🏆 Top Opportunities")

    for s in setups:
        direction = (s.get("direction") or "?").capitalize()
        tf = (s.get("timeframe") or "?").capitalize()
        lines.append(f"\n### #{s.get('rank','?')} — {s.get('symbol','?')} | {direction} | {tf}")
        exp = s.get("signal_expectancy")
        exp_str = f" · backtest hit rate {exp*100:.0f}% (net of cost)" if isinstance(exp, (int, float)) else ""
        lines.append(f"**Signal:** `{s.get('signal_name','?')}` ({s.get('signal_tf','?')}){exp_str}")
        t2rr = _t2_rr(s)
        pr = s.get("predicted_rr")
        lines.append("**Trade Plan:**")
        lines.append(_entry_line(s))
        lines.append(f"- Stop loss: {_fmt_price(s.get('stop_loss'))}")
        pr_str = f" (R:R {pr:.2f}:1)" if isinstance(pr, (int, float)) else ""
        lines.append(f"- Target 1: {_fmt_price(s.get('target_1'))}{pr_str} — partial profit, take 50%")
        t2_str = f" (R:R {t2rr:.2f}:1)" if t2rr is not None else ""
        lines.append(f"- Target 2: {_fmt_price(s.get('target_2'))}{t2_str} — reward leg")
        lines.append(f"- Confidence: {s.get('confidence','?')}")
        lines.append(f"- TF confluence: {s.get('tf_confluence','?')}/4")
        lines.append(f"- Volume confirmed: {'Yes' if s.get('volume_confirmed') else 'No'}")
        kf = (s.get("reasoning") or {}).get("key_factor")
        if kf:
            lines.append(f"- Key factor: {kf}")

    lines.append("\n## ⚠️ Position Management")
    lines.append("- Take 50% at T1, move stop to breakeven. Once +1R, tighten stop to +0.3R and let the rest run to T2.")
    lines.extend(ev_lines)
    lines.append("\n## 🧠 One-Line Takeaway")
    lines.append("These are mechanical, backtest-validated signals — you make the final call and place every order manually.")
    return "\n".join(lines)


def send_brief(brief_text, usage=None):
    """Sends brief to your personal Telegram chat via bot."""
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"

    # Convert markdown to Telegram HTML
    html_text = _md_to_telegram_html(brief_text)
    chunks = _smart_chunk(html_text)

    for i, chunk in enumerate(chunks):
        if len(chunks) > 1:
            header = f"📈 <b>Crypto Brief</b> (part {i+1}/{len(chunks)})\n\n"
        else:
            header = "📈 <b>Crypto Brief</b>\n\n"

        # Try HTML first
        payload = {
            "chat_id": config.TELEGRAM_CHAT_ID,
            "text": header + chunk,
            "parse_mode": "HTML",
        }
        r = _send_with_retry(url, payload)
        if r is None:
            continue

        # Fall back to plain text if HTML can't be parsed
        if r.status_code != 200 and "can't parse entities" in r.text:
            print("HTML parse failed, sending as plain text...")
            plain = re.sub(r"<[^>]+>", "", header + chunk)
            payload_plain = {
                "chat_id": config.TELEGRAM_CHAT_ID,
                "text": plain,
            }
            r = _send_with_retry(url, payload_plain)

        if r and r.status_code != 200:
            print(f"Telegram send failed with status {r.status_code}")

    # Send cost footer
    if usage:
        cost_est = (usage["input_tokens"] / 1_000_000 * 1.0 +
                    usage["output_tokens"] / 1_000_000 * 5.0)
        footer = (
            f"\n💰 <i>Tokens: {usage['input_tokens']:,} in / "
            f"{usage['output_tokens']:,} out · ~${cost_est:.4f}</i>"
        )
        _send_with_retry(url, {
            "chat_id": config.TELEGRAM_CHAT_ID,
            "text": footer,
            "parse_mode": "HTML",
        })
