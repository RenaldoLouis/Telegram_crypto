# Knowledge Library — crypto-screener

This folder contains the knowledge base that Claude reads every time it generates a brief. Each `.md` file is loaded and injected into Claude's system prompt via `analyzer/prompts.py → load_knowledge()`.

---

## File Structure

| File | Purpose | Edit Frequency |
|---|---|---|
| `00_recommended_reading.md` | Reference to books & resources (for YOU, not Claude) | Rare |
| `01_trading_philosophy.md` | Psychology & mindset rules | Rare |
| `02_risk_management.md` | Non-negotiable risk rules | Rare — core principles |
| `03_market_structure.md` | How to read charts & structure | Occasional refinements |
| `04_volume_analysis.md` | Volume, order flow, funding, OI | Occasional refinements |
| `05_crypto_specifics.md` | What makes crypto markets unique | Occasional updates |
| `06_setup_playbook.md` | **The setups Claude should match against** | Often — as you evolve |
| `07_watchlist.md` | **Your personal context & preferences** | Often — weekly |
| `08_glossary.md` | Term definitions | As needed |

---

## How Claude Consumes This

From `analyzer/prompts.py`:

```python
def load_knowledge():
    knowledge = {}
    for f in KNOWLEDGE_DIR.glob("*.md"):
        knowledge[f.stem] = f.read_text(encoding="utf-8")
    return knowledge
```

All `.md` files are loaded, concatenated with headers, and appended to the base system prompt. Claude treats them as **authoritative rules**, not suggestions.

---

## Token Cost Awareness

The full knowledge library is ~35-45k tokens when loaded. At Haiku pricing:
- Input: ~$0.04 per brief
- Cached input (second run): ~$0.004 per brief (prompt caching discount)

If you want to reduce cost, you can:
1. Enable prompt caching in `claude_client.py` (Anthropic API supports this) → 90% reduction on subsequent runs.
2. Trim files you don't need (e.g., delete `00_recommended_reading.md` — it's for you, not Claude).
3. Condense setups in `06_setup_playbook.md` once you know which ones you actually use.

---

## Adding PDFs of Trading Books

If you have PDFs of trading books you want Claude to reference:

1. Process them through Claude Code with:
   > "Parse this PDF and extract the key rules into `/knowledge/09_bookname_extracts.md` following the style of the existing files."
2. Review and trim the output (don't include the whole book — just the usable rules).
3. Claude will automatically pick it up on the next run.

---

## Versioning / History

As you iterate, consider:
- Keep a `logs/briefs/` journal of every brief.
- Review weekly: which setups hit? Which failed? Why?
- Update `06_setup_playbook.md` based on what you learn.
- Document lessons in `07_watchlist.md` under "Lessons from last week."

Over time, this knowledge library becomes uniquely tuned to your approach — which is the real edge.
