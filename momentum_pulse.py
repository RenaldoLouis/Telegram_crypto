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
import statistics
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
        client = HTTP(testnet=False, domain="bytick")
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
    """Load last_snapshot.json. Returns (tickers_dict, previous_regime)."""
    if not SNAPSHOT_FILE.exists():
        return {}, "neutral"
    try:
        data = json.loads(SNAPSHOT_FILE.read_text(encoding="utf-8"))
        return data.get("tickers", {}), data.get("regime", "neutral")
    except (json.JSONDecodeError, KeyError) as e:
        print(f"  Warning: could not load previous snapshot: {e}")
        return {}, "neutral"


def save_snapshot(tickers, regime="neutral"):
    """Save current ticker data as the comparison baseline for next pulse."""
    SNAPSHOT_FILE.parent.mkdir(parents=True, exist_ok=True)
    snapshot = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "tickers": {t["symbol"]: t for t in tickers},
        "regime": regime,
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


def save_hot_list(coins, market_regime=None):
    """Save hot_list.json with compact JSON."""
    HOT_LIST_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "market_regime": market_regime,
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


def detect_market_regime(tickers, previous_regime="neutral"):
    """Classify overall market as risk_off, neutral, or risk_on from 50-ticker data.

    Uses aggregate metrics (breadth, BTC, median change, funding) — zero extra API calls.
    """
    changes = [t["price_change_24h_pct"] for t in tickers]
    declining = sum(1 for c in changes if c < 0)
    pct_declining = (declining / len(tickers)) * 100 if tickers else 50

    median_change = statistics.median(changes) if changes else 0.0
    avg_funding = statistics.mean(t["funding_rate_pct"] for t in tickers) if tickers else 0.0
    large_decline_count = sum(1 for c in changes if c < -5)

    # Find BTC specifically (market leader)
    btc_change = 0.0
    for t in tickers:
        if t["symbol"] == "BTCUSDT":
            btc_change = t["price_change_24h_pct"]
            break

    # Classification (thresholds from config)
    regime = "neutral"

    # Risk off: broad sell-off
    if (pct_declining >= config.REGIME_BEARISH_DECLINE_PCT
            and median_change <= config.REGIME_BEARISH_MEDIAN_CHANGE):
        regime = "risk_off"
    elif btc_change <= config.REGIME_BEARISH_BTC_CHANGE:
        regime = "risk_off"
    elif (pct_declining >= config.REGIME_BEARISH_COMBO_DECLINE
            and btc_change <= config.REGIME_BEARISH_COMBO_BTC):
        regime = "risk_off"

    # Risk on: broad rally (only if not already risk_off)
    if regime == "neutral":
        if (pct_declining <= config.REGIME_BULLISH_DECLINE_PCT
                and median_change >= config.REGIME_BULLISH_MEDIAN_CHANGE):
            regime = "risk_on"
        elif btc_change >= config.REGIME_BULLISH_BTC_CHANGE:
            regime = "risk_on"
        elif (pct_declining <= config.REGIME_BULLISH_COMBO_DECLINE
                and btc_change >= config.REGIME_BULLISH_COMBO_BTC):
            regime = "risk_on"

    return {
        "regime": regime,
        "metrics": {
            "pct_declining": round(pct_declining, 1),
            "median_change_pct": round(median_change, 2),
            "btc_change_pct": round(btc_change, 2),
            "avg_funding_pct": round(avg_funding, 4),
            "large_decline_count": large_decline_count,
        },
        "detected_utc": datetime.now(timezone.utc).isoformat(),
        "previous_regime": previous_regime,
    }


def send_regime_alert(regime):
    """Send Telegram alert when market regime changes."""
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        return

    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    m = regime["metrics"]
    label = regime["regime"].upper().replace("_", " ")
    prev_label = regime["previous_regime"].upper().replace("_", " ")

    lines = [
        f"<b>MARKET REGIME: {prev_label} \u2192 {label}</b>\n",
        f"{m['pct_declining']}% of top 50 coins declining",
        f"BTC: {m['btc_change_pct']:+.1f}% | Median: {m['median_change_pct']:+.1f}%",
        f"Avg funding: {m['avg_funding_pct']:+.4f}%",
        f"Coins >5% decline: {m['large_decline_count']}",
    ]

    if regime["regime"] == "risk_off":
        lines.append("\n\u26a0\ufe0f Next scan will prioritize shorts / reduce long setups")
    elif regime["regime"] == "risk_on":
        lines.append("\n\u2705 Next scan will favor trend-following longs")

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
                print("  Regime alert sent to Telegram")
                return
            print(f"  Regime alert failed with status {r.status_code}")
            return
        except (ConnectionError, Timeout) as e:
            if attempt < 3:
                print(f"  Telegram retry {attempt}/3...")
                time.sleep(attempt * 2)
            else:
                print(f"  Regime alert failed after 3 attempts: {e}")


def merge_hot_list(existing, newly_flagged):
    """Merge new flags into existing hot list. Newer data wins for same symbol."""
    by_symbol = {c["symbol"]: c for c in existing}
    for coin in newly_flagged:
        by_symbol[coin["symbol"]] = coin
    return list(by_symbol.values())


def send_telegram_alert(flagged_coins, regime=None):
    """Send a quick Telegram alert for newly flagged coins."""
    if not flagged_coins or not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        return

    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"

    lines = ["<b>Momentum Pulse Alert</b>"]
    if regime and regime.get("regime") != "neutral":
        label = regime["regime"].upper().replace("_", " ")
        lines.append(f"<i>Market: {label}</i>")
    lines.append("")
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
            print(f"  Telegram alert failed with status {r.status_code}")
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
    previous, previous_regime = load_previous_snapshot()
    if previous:
        print(f"  Previous snapshot: {len(previous)} symbols (regime: {previous_regime})")
    else:
        print("  No previous snapshot (first run)")

    # 3. Detect per-coin momentum
    flagged = detect_momentum(tickers, previous)
    for coin in flagged:
        accel = f", vol_accel={coin['volume_acceleration']:.1f}x" if coin["volume_acceleration"] else ""
        print(f"    Flagged: {coin['symbol']} ({coin['trigger']}, "
              f"{coin['price_change_24h_pct']:+.1f}%{accel})")

    # 4. Detect market-wide regime
    regime = detect_market_regime(tickers, previous_regime)
    m = regime["metrics"]
    print(f"  Market regime: {regime['regime'].upper()} "
          f"(BTC {m['btc_change_pct']:+.1f}%, "
          f"{m['pct_declining']}% declining, "
          f"median {m['median_change_pct']:+.1f}%)")

    # 5. Save current as new snapshot (includes regime for next pulse comparison)
    save_snapshot(tickers, regime["regime"])

    # 6. Merge into hot list (includes regime for main scan)
    existing = load_hot_list()
    merged = merge_hot_list(existing, flagged)
    save_hot_list(merged, market_regime=regime)
    print(f"  Hot list: {len(merged)} total coins ({len(flagged)} newly flagged)")

    # 7. Send regime change alert (fires even if no individual coins flagged)
    if regime["regime"] != regime["previous_regime"]:
        print(f"  Regime changed: {regime['previous_regime']} → {regime['regime']}")
        send_regime_alert(regime)

    # 8. Send Telegram alert for newly flagged coins
    if flagged:
        send_telegram_alert(flagged, regime=regime)
    else:
        print("  No new momentum flags — no alert sent")

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Pulse complete.\n")


if __name__ == "__main__":
    run_pulse()
