"""
Quarterly deep analysis — uses Claude to find non-obvious patterns in evaluation data.

Run manually every ~3 months (or whenever you have 50+ new evaluated trades):
    source venv/bin/activate
    python quarterly_analysis.py

What it does:
1. Loads lifetime_stats.json (compact aggregate stats)
2. Loads recent evaluation details for qualitative context
3. Asks Claude to find deeper patterns an algorithm can't easily detect
4. Appends qualitative insights to strategic_rules.md
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import anthropic
import config

LIFETIME_STATS_FILE = Path("logs/performance/lifetime_stats.json")
STRATEGIC_RULES_FILE = Path("logs/performance/strategic_rules.md")
EVALS_DIR = Path("logs/evaluations")
QUARTERLY_LOG_DIR = Path("logs/performance/quarterly")


ANALYSIS_PROMPT = """You are a quantitative trading analyst reviewing the performance data of a crypto screener system.

This system scans Bybit USDT perpetual futures, recommends 1-5 trade setups per run, and evaluates them against actual price data.

## Your Task

Analyze the data below and identify NON-OBVIOUS patterns that a simple algorithm would miss. Focus on actionable insights that will improve the system's win rate.

## Lifetime Aggregate Stats
```json
{lifetime_stats}
```

## Recent Individual Trade Outcomes (last 20 evaluated trades)
```json
{recent_trades}
```

## Current Algorithmic Rules
{current_rules}

## What to Look For

1. **Temporal patterns**: Do certain days/times perform better? Are there patterns in consecutive wins/losses?
2. **Setup interactions**: Do certain setup_type + confidence + timeframe combinations work unusually well or poorly?
3. **Symbol patterns**: Are there symbols that consistently win or lose? Should certain symbols be avoided?
4. **Sequence effects**: Does the system perform worse after a winning streak (overconfidence)? Better after losses (more selective)?
5. **R:R distribution**: Are there clusters of outcomes? Is the system leaving money on the table with T1 placement?
6. **Direction bias**: Does the system have a long/short bias? Does one direction perform better in certain conditions?
7. **Meta-patterns**: Anything else you notice that isn't captured by the algorithmic rules.

## Output Format

Return ONLY a numbered list of 3-7 actionable insights. Each insight should be:
- A clear observation (what the data shows)
- Why it matters (impact on win rate)
- A specific recommendation (what to change)

Be concrete and specific. "Be more selective" is too vague. "Avoid short setups on intraday timeframe — 0/8 wins vs 3/12 for longs" is specific.

Only include insights that are NOT already captured by the current algorithmic rules. Don't repeat what's already known.
"""


def load_recent_trades(limit=20):
    """Load the most recent evaluated trades with full detail."""
    all_trades = []
    for ef in sorted(EVALS_DIR.glob("eval_*.json"), reverse=True):
        try:
            ev = json.loads(ef.read_text(encoding="utf-8"))
            for r in ev["results"]:
                if r.get("status") == "evaluated":
                    r["run_tag"] = ev["run_tag"]
                    r["model"] = ev.get("model", "unknown")
                    all_trades.append(r)
        except Exception:
            pass
        if len(all_trades) >= limit:
            break
    return all_trades[:limit]


def run_quarterly_analysis():
    """Run Claude-powered deep analysis of evaluation data."""
    if not LIFETIME_STATS_FILE.exists():
        print("No lifetime_stats.json found. Run weekly_eval.py first.")
        return

    stats = json.loads(LIFETIME_STATS_FILE.read_text(encoding="utf-8"))
    total = stats.get("total_evaluated", 0)

    if total < 15:
        print(f"Only {total} evaluated trades. Need at least 15 for meaningful analysis.")
        return

    print(f"Running quarterly deep analysis on {total} evaluated trades...")

    # Load data
    recent_trades = load_recent_trades(20)

    current_rules = ""
    if STRATEGIC_RULES_FILE.exists():
        current_rules = STRATEGIC_RULES_FILE.read_text(encoding="utf-8")

    # Build the prompt
    prompt = ANALYSIS_PROMPT.format(
        lifetime_stats=json.dumps(stats, indent=2),
        recent_trades=json.dumps(recent_trades, indent=2),
        current_rules=current_rules if current_rules else "(no rules yet)",
    )

    # Call Claude
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    print("Calling Claude for deep analysis...")

    response = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    analysis = response.content[0].text
    usage = response.usage

    print(f"Analysis complete. Used {usage.input_tokens}+{usage.output_tokens} tokens.")
    print(f"\n{'='*50}")
    print(analysis)
    print(f"{'='*50}\n")

    # Save the raw analysis to quarterly log
    QUARTERLY_LOG_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    log_file = QUARTERLY_LOG_DIR / f"analysis_{now.strftime('%Y%m%d')}.md"
    log_content = (
        f"# Quarterly Deep Analysis — {now.strftime('%Y-%m-%d %H:%M UTC')}\n"
        f"_Based on {total} evaluated trades. Model: {config.CLAUDE_MODEL}_\n"
        f"_Tokens: {usage.input_tokens} input + {usage.output_tokens} output_\n\n"
        f"{analysis}\n"
    )
    log_file.write_text(log_content, encoding="utf-8")
    print(f"Full analysis saved to {log_file}")

    # Append qualitative insights to strategic_rules.md
    if STRATEGIC_RULES_FILE.exists():
        existing = STRATEGIC_RULES_FILE.read_text(encoding="utf-8").rstrip()
    else:
        existing = "# Strategic Rules\n_No algorithmic rules yet._"

    # Remove previous quarterly section if present (replace with new)
    marker = "\n## Quarterly Deep Insights"
    if marker in existing:
        existing = existing[:existing.index(marker)]

    updated = (
        f"{existing}\n"
        f"\n## Quarterly Deep Insights\n"
        f"_Generated {now.strftime('%Y-%m-%d')} by Claude ({config.CLAUDE_MODEL}) "
        f"from {total} trades._\n\n"
        f"{analysis}\n"
    )
    STRATEGIC_RULES_FILE.write_text(updated, encoding="utf-8")
    print(f"Insights appended to {STRATEGIC_RULES_FILE}")


if __name__ == "__main__":
    print("=" * 50)
    print("Crypto Screener — Quarterly Deep Analysis")
    print("=" * 50)
    run_quarterly_analysis()
