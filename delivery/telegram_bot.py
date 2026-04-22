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
            print(f"Telegram send failed: {r.text}")

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
