from pybit.unified_trading import HTTP
from datetime import datetime, timezone
import pandas as pd
import config


class BybitFetcher:
    def __init__(self):
        self.client = HTTP(
            testnet=False,
            api_key=config.BYBIT_API_KEY,
            api_secret=config.BYBIT_API_SECRET,
        )

    def get_top_movers(self, limit=20):
        """Returns top N USDT perpetuals by 24h turnover + price change."""
        res = self.client.get_tickers(category=config.BYBIT_CATEGORY)
        tickers = res["result"]["list"]

        # Filter to USDT perps only
        usdt_perps = [t for t in tickers if t["symbol"].endswith("USDT")]

        # Sort by 24h turnover
        by_turnover = sorted(
            usdt_perps,
            key=lambda t: float(t.get("turnover24h", 0)),
            reverse=True
        )[:limit]

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

    def get_klines_with_indicators(self, symbol):
        """Fetches 1h candles and calculates basic indicators."""
        res = self.client.get_kline(
            category=config.BYBIT_CATEGORY,
            symbol=symbol,
            interval=config.KLINE_INTERVAL,
            limit=config.KLINE_LIMIT,
        )
        candles = res["result"]["list"]
        # Bybit returns newest first, reverse for chronological
        candles.reverse()

        df = pd.DataFrame(
            candles,
            columns=["timestamp", "open", "high", "low", "close", "volume", "turnover"]
        )
        df[["open", "high", "low", "close", "volume"]] = df[
            ["open", "high", "low", "close", "volume"]
        ].astype(float)

        # --- RSI (14) ---
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0).rolling(14).mean()
        rs = gain / loss
        df["rsi_14"] = 100 - (100 / (1 + rs))

        # --- Volume spike detection ---
        df["vol_avg_20"] = df["volume"].rolling(20).mean()
        df["vol_spike_ratio"] = df["volume"] / df["vol_avg_20"]

        # --- Price vs 20-candle high/low (breakout detection) ---
        df["high_20"] = df["high"].rolling(20).max()
        df["low_20"] = df["low"].rolling(20).min()

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        return {
                "symbol": symbol,
                "current_price": float(latest["close"]),
                "rsi_14": round(float(latest["rsi_14"]), 2) if pd.notna(latest["rsi_14"]) else None,
                "volume_spike_ratio": round(float(latest["vol_spike_ratio"]), 2) if pd.notna(latest["vol_spike_ratio"]) else None,
                "breaking_20h_high": bool(latest["close"] >= latest["high_20"]),
                "breaking_20h_low": bool(latest["close"] <= latest["low_20"]),
                "last_3_candles_pct": [
                    round(float((df.iloc[-i]["close"] - df.iloc[-i]["open"]) / df.iloc[-i]["open"] * 100), 2)
                    for i in [3, 2, 1]
                ],
            }

    def get_full_market_snapshot(self):
        """Main entry — returns everything Claude needs."""
        top_movers = self.get_top_movers(config.TOP_MOVERS_LIMIT)

        # Build symbols to analyze: top movers + your watchlist
        symbols_to_analyze = list({m["symbol"] for m in top_movers} | set(config.WATCHLIST))

        technicals = []
        for sym in symbols_to_analyze:
            try:
                technicals.append(self.get_klines_with_indicators(sym))
            except Exception as e:
                print(f"Error fetching {sym}: {e}")

        return {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "top_movers": top_movers,
            "technicals": technicals,
        }