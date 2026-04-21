from pybit.unified_trading import HTTP
from datetime import datetime, timezone
import pandas as pd
import time
import config


class BybitFetcher:
    def __init__(self):
        self.client = HTTP(
            testnet=False,
            api_key=config.BYBIT_API_KEY,
            api_secret=config.BYBIT_API_SECRET,
        )

    def get_top_movers(self, limit=50):
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

    def _compute_indicators(self, candles):
        """Compute RSI, volume spike, breakout from raw candle data."""
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

        # --- EMA 20 & 50 for trend ---
        df["ema_20"] = df["close"].ewm(span=20, adjust=False).mean()
        df["ema_50"] = df["close"].ewm(span=50, adjust=False).mean()

        latest = df.iloc[-1]

        return {
            "current_price": float(latest["close"]),
            "rsi_14": round(float(latest["rsi_14"]), 2) if pd.notna(latest["rsi_14"]) else None,
            "volume_spike_ratio": round(float(latest["vol_spike_ratio"]), 2) if pd.notna(latest["vol_spike_ratio"]) else None,
            "breaking_20_high": bool(latest["close"] >= latest["high_20"]) if pd.notna(latest["high_20"]) else None,
            "breaking_20_low": bool(latest["close"] <= latest["low_20"]) if pd.notna(latest["low_20"]) else None,
            "ema_20": round(float(latest["ema_20"]), 6) if pd.notna(latest["ema_20"]) else None,
            "ema_50": round(float(latest["ema_50"]), 6) if pd.notna(latest["ema_50"]) else None,
            "trend": "bullish" if pd.notna(latest["ema_20"]) and pd.notna(latest["ema_50"]) and latest["ema_20"] > latest["ema_50"] else "bearish",
            "last_3_candles_pct": [
                round(float((df.iloc[-i]["close"] - df.iloc[-i]["open"]) / df.iloc[-i]["open"] * 100), 2)
                for i in [3, 2, 1]
            ],
        }

    def get_klines_with_indicators(self, symbol):
        """Fetches 1h candles and calculates basic indicators (legacy single-TF)."""
        res = self.client.get_kline(
            category=config.BYBIT_CATEGORY,
            symbol=symbol,
            interval=config.KLINE_INTERVAL,
            limit=config.KLINE_LIMIT,
        )
        candles = res["result"]["list"]
        candles.reverse()

        indicators = self._compute_indicators(candles)
        indicators["symbol"] = symbol
        return indicators

    def get_multi_tf_indicators(self, symbol):
        """Fetches candles across all configured timeframes and computes indicators for each."""
        result = {"symbol": symbol, "timeframes": {}}

        tf_labels = {"15": "15m", "60": "1h", "240": "4h", "D": "1D"}

        for interval, limit in config.KLINE_INTERVALS.items():
            try:
                res = self.client.get_kline(
                    category=config.BYBIT_CATEGORY,
                    symbol=symbol,
                    interval=interval,
                    limit=limit,
                )
                candles = res["result"]["list"]
                candles.reverse()

                indicators = self._compute_indicators(candles)
                label = tf_labels.get(interval, interval)
                result["timeframes"][label] = indicators
            except Exception as e:
                print(f"  Warning: {symbol} {interval} kline failed: {e}")

            # Small delay to avoid rate limits with 50 symbols x 4 timeframes
            time.sleep(0.05)

        return result

    def get_full_market_snapshot(self):
        """Main entry — returns everything Claude needs with multi-TF data."""
        top_movers = self.get_top_movers(config.TOP_MOVERS_LIMIT)

        # Build symbols to analyze: top movers + your watchlist
        symbols_to_analyze = list({m["symbol"] for m in top_movers} | set(config.WATCHLIST))

        technicals = []
        total = len(symbols_to_analyze)
        for i, sym in enumerate(symbols_to_analyze):
            try:
                print(f"  [{i+1}/{total}] Fetching {sym}...")
                technicals.append(self.get_multi_tf_indicators(sym))
            except Exception as e:
                print(f"  Error fetching {sym}: {e}")

        return {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "top_movers": top_movers,
            "technicals": technicals,
        }
