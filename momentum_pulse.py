"""
Momentum Pulse Scanner — lightweight intra-day momentum detection.

Runs every 4 hours on GitHub Actions (free). Zero Claude tokens.
Fetches top 50 tickers, compares against previous snapshot, flags acceleration.
Sends quick Telegram alerts for flagged coins.
Results feed into the main scan via logs/momentum/hot_list.json.

Run locally:
    source venv/bin/activate
    python momentum_pulse.py
"""

import json
import time
import os
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
from pybit.unified_trading import HTTP
from requests.exceptions import ConnectionError, Timeout

import config


HOT_LIST_FILE = Path(config.MOMENTUM_HOT_LIST_PATH)
SNAPSHOT_FILE = Path(config.MOMENTUM_SNAPSHOT_PATH)


def fetch_tickers():
    """Fetch top 50 USDT perps by 24h turnover. Single API call."""
    try:
        client = HTTP(
            testnet=False,
            api_key=config.BYBIT_API_KEY,
            api_secret=config.BYBIT_API_SECRET,
        )
        res = client.get_tickers(category=config.BYBIT_CATEGORY)
        tickers = res["result"]["list"]

        usdt_perps = [t for t in tickers if t["symbol"].endswith("USDT")]
        by_turnover = sorted(
            usdt_perps,
            key=lambda t: float(t.get("turnover24h", 0)),
            reverse=True,
        )[:50]

        return [
            {
                "symbol": t["symbol"],
                "last_price": float(t["lastPrice"]),
                "price_change_24h_pct": float(t["price24hPcnt"]) * 100,
                "turnover_24h_usd": float(t["turnover24h"]),
                "volume_24h": float(t["volume24h"]),
                "funding_rate_pct": float(t.get("fundingRate", 0)) * 100,
                "open_interest": float(t.get("openInterest", 0)),
            }
            for t in by_turnover
        ]
    except Exception as e:
        print(f"  Error fetching tickers: {e}")
        return []


def load_previous_snapshot():
    """Load last_snapshot.json. Returns dict keyed by symbol, or empty dict."""
    if not SNAPSHOT_FILE.exists():
        return {}
    try:
        data = json.loads(SNAPSHOT_FILE.read_text(encoding="utf-8"))
        return data.get("tickers", {})
    except (json.JSONDecodeError, KeyError) as e:
        print(f"  Warning: could not load previous snapshot: {e}")
        return {}


def save_snapshot(tickers):
    """Save current ticker data as the comparison baseline for next pulse."""
    SNAPSHOT_FILE.parent.mkdir(parents=True, exist_ok=True)
    snapshot = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "tickers": {t["symbol"]: t for t in tickers},
    }
    SNAPSHOT_FILE.write_text(
        json.dumps(snapshot, separators=(",", ":")),
        encoding="utf-8",
    )


def load_hot_list():
    """Load existing hot_list.json, remove expired entries. Returns list of coin dicts."""
    if not HOT_LIST_FILE.exists():
        return []
    try:
        data = json.loads(HOT_LIST_FILE.read_text(encoding="utf-8"))
        now = datetime.now(timezone.utc)
        active = []
        for coin in data.get("coins", []):
            expires = datetime.fromisoformat(coin["expires_utc"])
            if expires > now:
                active.append(coin)
        return active
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"  Warning: could not load hot list: {e}")
        return []


def save_hot_list(coins):
    """Save hot_list.json with compact JSON."""
    HOT_LIST_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "coins": coins,
    }
    HOT_LIST_FILE.write_text(
        json.dumps(data, indent=2),
        encoding="utf-8",
    )


def detect_momentum(tickers, previous):
    """Compare current tickers against previous snapshot. Return list of flagged coins."""
    flagged = []
    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=config.MOMENTUM_PULSE_EXPIRY_HOURS)

    for t in tickers:
        symbol = t["symbol"]
        pct = abs(t["price_change_24h_pct"])
        turnover = t["turnover_24h_usd"]
        funding = abs(t["funding_rate_pct"])

        triggers = []

        # Criterion 1: Big move + high turnover
        if pct > config.MOMENTUM_BIG_MOVE_PCT and turnover > config.MOMENTUM_BIG_MOVE_TURNOVER:
            triggers.append("big_move")

        # Criterion 2: Volume acceleration vs previous pulse
        prev = previous.get(symbol)
        vol_accel = None
        price_accel = None
        if prev and prev.get("turnover_24h_usd", 0) > 0:
            vol_accel = turnover / prev["turnover_24h_usd"]
            price_accel = pct - abs(prev.get("price_change_24h_pct", 0))
            if vol_accel > config.MOMENTUM_VOLUME_ACCEL_THRESHOLD:
                triggers.append("volume_acceleration")

        # Criterion 3: Extreme funding + price starting to move
        if funding > config.MOMENTUM_FUNDING_EXTREME_PCT and pct > config.MOMENTUM_FUNDING_MOVE_PCT:
            triggers.append("funding_squeeze")

        if triggers:
            flagged.append({
                "symbol": symbol,
                "flagged_utc": now.isoformat(),
                "expires_utc": expires.isoformat(),
                "trigger": triggers[0],
                "all_triggers": triggers,
                "last_price": t["last_price"],
                "price_change_24h_pct": t["price_change_24h_pct"],
                "turnover_24h_usd": t["turnover_24h_usd"],
                "funding_rate_pct": t["funding_rate_pct"],
                "open_interest": t["open_interest"],
                "volume_acceleration": float(vol_accel) if vol_accel is not None else None,
                "price_acceleration_pct": float(price_accel) if price_accel is not None else None,
            })

    return flagged


def merge_hot_list(existing, newly_flagged):
    """Merge new flags into existing hot list. Newer data wins for same symbol."""
    by_symbol = {c["symbol"]: c for c in existing}
    for coin in newly_flagged:
        by_symbol[coin["symbol"]] = coin
    return list(by_symbol.values())


def send_telegram_alert(flagged_coins):
    """Send a quick Telegram alert for newly flagged coins."""
    if not flagged_coins or not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        return

    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"

    lines = ["<b>Momentum Pulse Alert</b>\n"]
    for coin in sorted(flagged_coins, key=lambda c: abs(c["price_change_24h_pct"]), reverse=True):
        direction = "+" if coin["price_change_24h_pct"] > 0 else ""
        accel = f" | Vol {coin['volume_acceleration']:.1f}x" if coin["volume_acceleration"] else ""
        lines.append(
            f"<b>{coin['symbol']}</b>: "
            f"{direction}{coin['price_change_24h_pct']:.1f}% | "
            f"${coin['turnover_24h_usd'] / 1e6:.0f}M vol{accel} | "
            f"{coin['trigger']}"
        )

    lines.append(f"\n<i>{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC</i>")
    text = "\n".join(lines)

    for attempt in range(1, 4):
        try:
            r = requests.post(url, json={
                "chat_id": config.TELEGRAM_CHAT_ID,
                "text": text,
                "parse_mode": "HTML",
            }, timeout=30)
            if r.status_code == 200:
                print("  Telegram alert sent")
                return
            print(f"  Telegram alert failed: {r.text}")
            return
        except (ConnectionError, Timeout) as e:
            if attempt < 3:
                print(f"  Telegram retry {attempt}/3...")
                time.sleep(attempt * 2)
            else:
                print(f"  Telegram alert failed after 3 attempts: {e}")


def run_pulse():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Running momentum pulse...")

    # 1. Fetch current tickers
    tickers = fetch_tickers()
    if not tickers:
        print("  No tickers fetched — aborting pulse")
        return
    print(f"  Fetched {len(tickers)} tickers")

    # 2. Load previous snapshot for comparison
    previous = load_previous_snapshot()
    if previous:
        print(f"  Previous snapshot: {len(previous)} symbols")
    else:
        print("  No previous snapshot (first run)")

    # 3. Detect momentum
    flagged = detect_momentum(tickers, previous)
    for coin in flagged:
        accel = f", vol_accel={coin['volume_acceleration']:.1f}x" if coin["volume_acceleration"] else ""
        print(f"    Flagged: {coin['symbol']} ({coin['trigger']}, "
              f"{coin['price_change_24h_pct']:+.1f}%{accel})")

    # 4. Save current as new snapshot
    save_snapshot(tickers)

    # 5. Merge into hot list
    existing = load_hot_list()
    merged = merge_hot_list(existing, flagged)
    save_hot_list(merged)
    print(f"  Hot list: {len(merged)} total coins ({len(flagged)} newly flagged)")

    # 6. Send Telegram alert for newly flagged only
    if flagged:
        send_telegram_alert(flagged)
    else:
        print("  No new momentum flags — no alert sent")

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Pulse complete.\n")


if __name__ == "__main__":
    run_pulse()
