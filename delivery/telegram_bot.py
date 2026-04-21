import requests
import config


def send_brief(brief_text, usage=None):
    """Sends brief to your personal Telegram chat via bot."""
    # Telegram has a 4096 char limit per message — split if needed
    max_len = 4000
    chunks = [brief_text[i:i+max_len] for i in range(0, len(brief_text), max_len)]

    for i, chunk in enumerate(chunks):
        prefix = f"📈 *Crypto Brief* (part {i+1}/{len(chunks)})\n\n" if len(chunks) > 1 else "📈 *Crypto Brief*\n\n"
        payload = {
            "chat_id": config.TELEGRAM_CHAT_ID,
            "text": prefix + chunk,
            "parse_mode": "Markdown",
        }
        url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
        r = requests.post(url, json=payload)
        if r.status_code != 200:
            print(f"Telegram send failed: {r.text}")

    if usage:
        cost_est = (usage["input_tokens"] / 1_000_000 * 1.0 +
                    usage["output_tokens"] / 1_000_000 * 5.0)
        footer = f"\n\n_Tokens: {usage['input_tokens']} in / {usage['output_tokens']} out · ~${cost_est:.4f}_"
        requests.post(url, json={
            "chat_id": config.TELEGRAM_CHAT_ID,
            "text": footer,
            "parse_mode": "Markdown",
        })