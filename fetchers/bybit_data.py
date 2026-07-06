from pybit.unified_trading import HTTP
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import json
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

        # --- ATR (14) for volatility-aware stop/target placement ---
        tr = pd.concat([
            df["high"] - df["low"],
            (df["high"] - df["close"].shift()).abs(),
            (df["low"] - df["close"].shift()).abs(),
        ], axis=1).max(axis=1)
        df["atr_14"] = tr.rolling(14).mean()

        # --- MACD (12, 26, 9) for momentum direction + acceleration ---
        ema_12 = df["close"].ewm(span=12, adjust=False).mean()
        ema_26 = df["close"].ewm(span=26, adjust=False).mean()
        df["macd"] = ema_12 - ema_26
        df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
        df["macd_hist"] = df["macd"] - df["macd_signal"]

        # --- SMA 200 (meaningful on 1D with 200+ candles, NaN otherwise) ---
        df["sma_200"] = df["close"].rolling(200).mean()

        # --- ADX (14) for trend strength (ranging vs trending) ---
        plus_dm = df["high"].diff()
        minus_dm = -df["low"].diff()
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
        atr_wilder = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
        plus_di = 100 * plus_dm.ewm(alpha=1/14, min_periods=14, adjust=False).mean() / atr_wilder
        minus_di = 100 * minus_dm.ewm(alpha=1/14, min_periods=14, adjust=False).mean() / atr_wilder
        di_sum = plus_di + minus_di
        di_sum = di_sum.replace(0, float('nan'))
        dx = 100 * (plus_di - minus_di).abs() / di_sum
        df["adx_14"] = dx.ewm(alpha=1/14, min_periods=14, adjust=False).mean()

        latest = df.iloc[-1]

        result = {
            "current_price": float(latest["close"]),
            "rsi_14": round(float(latest["rsi_14"]), 2) if pd.notna(latest["rsi_14"]) else None,
            "volume_spike_ratio": round(float(latest["vol_spike_ratio"]), 2) if pd.notna(latest["vol_spike_ratio"]) else None,
            "breaking_20_high": bool(latest["close"] >= latest["high_20"]) if pd.notna(latest["high_20"]) else None,
            "breaking_20_low": bool(latest["close"] <= latest["low_20"]) if pd.notna(latest["low_20"]) else None,
            "ema_20": round(float(latest["ema_20"]), 6) if pd.notna(latest["ema_20"]) else None,
            "ema_50": round(float(latest["ema_50"]), 6) if pd.notna(latest["ema_50"]) else None,
            "atr_14": round(float(latest["atr_14"]), 6) if pd.notna(latest["atr_14"]) else None,
            "atr_pct": round(float(latest["atr_14"] / latest["close"] * 100), 2) if pd.notna(latest["atr_14"]) and latest["close"] > 0 else None,
            "trend": "bullish" if pd.notna(latest["ema_20"]) and pd.notna(latest["ema_50"]) and latest["ema_20"] > latest["ema_50"] else "bearish",
            "adx_14": round(float(latest["adx_14"]), 2) if pd.notna(latest["adx_14"]) else None,
            "macd": round(float(latest["macd"]), 6) if pd.notna(latest["macd"]) else None,
            "macd_hist": round(float(latest["macd_hist"]), 6) if pd.notna(latest["macd_hist"]) else None,
            "range_pct": round(float((latest["high_20"] - latest["low_20"]) / latest["close"] * 100), 2) if pd.notna(latest["high_20"]) and pd.notna(latest["low_20"]) and latest["close"] > 0 else None,
            "last_3_candles_pct": [
                round(float((df.iloc[-i]["close"] - df.iloc[-i]["open"]) / df.iloc[-i]["open"] * 100), 2)
                for i in [3, 2, 1]
            ],
        }

        # SMA 200 only included when enough candles (1D with 210 candles). Saves tokens on shorter TFs.
        if pd.notna(latest["sma_200"]):
            result["sma_200"] = round(float(latest["sma_200"]), 6)

        # Divergence detection (RSI + MACD swing point analysis)
        divergences = BybitFetcher._detect_divergences(df)
        if divergences:
            result["divergences"] = divergences

        return result

    @staticmethod
    def _check_validated_signals(candles, tf_label):
        """Check validated signal formulas against candle data.

        Passed out-of-sample train/test validation on 15 symbols (Jul 2026 re-run):
          - rsi_rejection_short : confirmed both 1h + 4h
          - macd_momentum_long  : confirmed both 1h + 4h
          - trend_pullback_short: 4h ONLY (1h rejected as overfit)
        macd_momentum_short removed — degraded to overfit on both TFs.
        Only called for 1h and 4h.

        Returns list of signal dicts (empty if none fire).
        """
        if len(candles) < 55:
            return []

        df = pd.DataFrame(
            candles,
            columns=["timestamp", "open", "high", "low", "close", "volume", "turnover"]
        )
        df[["open", "high", "low", "close", "volume"]] = df[
            ["open", "high", "low", "close", "volume"]
        ].astype(float)

        # Compute needed indicators
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0).rolling(14).mean()
        rs = gain / loss
        df["rsi"] = 100 - (100 / (1 + rs))
        df["ema20"] = df["close"].ewm(span=20, adjust=False).mean()
        df["ema50"] = df["close"].ewm(span=50, adjust=False).mean()
        tr = pd.concat([
            df["high"] - df["low"],
            (df["high"] - df["close"].shift()).abs(),
            (df["low"] - df["close"].shift()).abs(),
        ], axis=1).max(axis=1)
        df["atr"] = tr.rolling(14).mean()
        ema12 = df["close"].ewm(span=12, adjust=False).mean()
        ema26 = df["close"].ewm(span=26, adjust=False).mean()
        df["macd"] = ema12 - ema26
        df["macd_sig"] = df["macd"].ewm(span=9, adjust=False).mean()
        df["macd_hist"] = df["macd"] - df["macd_sig"]
        plus_dm = df["high"].diff()
        minus_dm = -df["low"].diff()
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
        atr_w = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
        plus_di = 100 * plus_dm.ewm(alpha=1/14, min_periods=14, adjust=False).mean() / atr_w
        minus_di = 100 * minus_dm.ewm(alpha=1/14, min_periods=14, adjust=False).mean() / atr_w
        di_sum = (plus_di + minus_di).replace(0, float('nan'))
        dx = 100 * (plus_di - minus_di).abs() / di_sum
        df["adx"] = dx.ewm(alpha=1/14, min_periods=14, adjust=False).mean()

        c = df.iloc[-1]  # current
        p = df.iloc[-2]  # previous
        p2 = df.iloc[-3] # 2 candles ago

        signals = []

        # Guard: need valid indicators
        if not all(pd.notna(c[col]) for col in ["rsi", "ema20", "ema50", "atr", "adx", "macd_hist"]):
            return []
        if c["atr"] <= 0:
            return []

        # --- Signal 1: RSI Rejection Short ---
        # RSI was >75 (overbought), now crossing back down. Exhaustion reversal.
        # Validated (Jul 2026 re-run): ★ STRONG both TFs — 4h test +0.438, 1h test +0.809
        if (pd.notna(p["rsi"]) and pd.notna(p2["rsi"]) and
            p2["rsi"] > 75 and p["rsi"] > 70 and
            c["rsi"] < 72 and c["rsi"] > 50 and c["rsi"] < p["rsi"]):
            risk = 2.0 * float(c["atr"])
            signals.append({
                "signal": "rsi_rejection_short",
                "tf": tf_label,
                "direction": "short",
                "target_r": 2.0,
                "stop_atr": 2.0,
                "indicators": f"RSI {c['rsi']:.1f} (was {p2['rsi']:.1f}), ADX {c['adx']:.1f}",
                "historical": "+0.44 expect (4h test), +0.81 (1h test)",
            })

        # --- Signal 2: MACD Momentum Long ---
        # MACD histogram flips positive in uptrend. Trend continuation.
        # Validated (Jul 2026 re-run): confirmed both TFs — 4h test +0.250, 1h test +0.591
        if (pd.notna(p["macd_hist"]) and
            p["macd_hist"] <= 0 and c["macd_hist"] > 0 and
            c["ema20"] > c["ema50"] and
            c["adx"] > 20 and
            35 <= c["rsi"] <= 65):
            signals.append({
                "signal": "macd_momentum_long",
                "tf": tf_label,
                "direction": "long",
                "target_r": 1.5,
                "stop_atr": 1.5,
                "indicators": f"MACD hist flipped +, RSI {c['rsi']:.1f}, ADX {c['adx']:.1f}",
                "historical": "+0.25 expect (4h test), +0.59 (1h test)",
            })

        # --- Signal 3: Trend Pullback Short (4h ONLY) ---
        # Downtrend + price pulled back to EMA20 + MACD confirms.
        # Validated (Jul 2026 re-run): 4h test +0.280, N=111, 100% robust.
        # 1h REJECTED as overfit (all variants negative test exp) — gated to 4h only.
        if (tf_label == "4h" and
            c["ema20"] < c["ema50"] and
            c["adx"] > 15 and
            50 <= c["rsi"] <= 70 and
            float(c["close"]) < float(c["ema50"]) and
            abs(float(c["close"]) - float(c["ema20"])) < 0.7 * float(c["atr"]) and
            c["macd"] < 0):
            signals.append({
                "signal": "trend_pullback_short",
                "tf": tf_label,
                "direction": "short",
                "target_r": 2.0,
                "stop_atr": 1.5,
                "indicators": f"EMA20<EMA50, RSI {c['rsi']:.1f}, ADX {c['adx']:.1f}, near EMA20",
                "historical": "+0.28 expect (4h test, N=111, 100% robust)",
            })

        return signals

    @staticmethod
    def _detect_divergences(df, lookback=40, order=3):
        """Detect RSI and MACD divergences from swing highs/lows.

        Returns list of short labels: rsi_bull, rsi_bear, rsi_h_bull, rsi_h_bear,
        macd_bull, macd_bear, macd_h_bull, macd_h_bear. Empty if none found.
        """
        n = len(df)
        if n < 2 * order + 2:
            return []

        window_start = max(0, n - lookback)
        divergences = []

        # Find swing highs (local maxima in high prices)
        swing_highs = []
        for i in range(order, n - order):
            is_peak = True
            for j in range(-order, order + 1):
                if j != 0 and df["high"].iat[i] <= df["high"].iat[i + j]:
                    is_peak = False
                    break
            if is_peak:
                swing_highs.append(i)

        # Find swing lows (local minima in low prices)
        swing_lows = []
        for i in range(order, n - order):
            is_trough = True
            for j in range(-order, order + 1):
                if j != 0 and df["low"].iat[i] >= df["low"].iat[i + j]:
                    is_trough = False
                    break
            if is_trough:
                swing_lows.append(i)

        # Keep only swing points in lookback window
        recent_highs = [i for i in swing_highs if i >= window_start]
        recent_lows = [i for i in swing_lows if i >= window_start]

        for ind_name, ind_col in [("rsi", "rsi_14"), ("macd", "macd")]:
            ind = df[ind_col]

            # Bearish divergences (from swing highs)
            if len(recent_highs) >= 2:
                h1, h2 = recent_highs[-2], recent_highs[-1]
                iv1, iv2 = ind.iat[h1], ind.iat[h2]
                if pd.notna(iv1) and pd.notna(iv2):
                    ph1, ph2 = df["high"].iat[h1], df["high"].iat[h2]
                    # Regular bearish: price higher high + indicator lower high
                    if ph2 > ph1 and iv2 < iv1:
                        divergences.append(f"{ind_name}_bear")
                    # Hidden bearish: price lower high + indicator higher high
                    elif ph2 < ph1 and iv2 > iv1:
                        divergences.append(f"{ind_name}_h_bear")

            # Bullish divergences (from swing lows)
            if len(recent_lows) >= 2:
                l1, l2 = recent_lows[-2], recent_lows[-1]
                iv1, iv2 = ind.iat[l1], ind.iat[l2]
                if pd.notna(iv1) and pd.notna(iv2):
                    pl1, pl2 = df["low"].iat[l1], df["low"].iat[l2]
                    # Regular bullish: price lower low + indicator higher low
                    if pl2 < pl1 and iv2 > iv1:
                        divergences.append(f"{ind_name}_bull")
                    # Hidden bullish: price higher low + indicator lower low
                    elif pl2 > pl1 and iv2 < iv1:
                        divergences.append(f"{ind_name}_h_bull")

        return divergences

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
        validated_signals = []

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

                # Check validated signals on 1h and 4h only
                if label in ("1h", "4h"):
                    sigs = BybitFetcher._check_validated_signals(candles, label)
                    for sig in sigs:
                        sig["symbol"] = symbol
                    validated_signals.extend(sigs)
            except Exception as e:
                print(f"  Warning: {symbol} {interval} kline failed: {e}")

            # Small delay to avoid rate limits with 50 symbols x 4 timeframes
            time.sleep(0.05)

        if validated_signals:
            result["validated_signals"] = validated_signals

        return result

    @staticmethod
    def _ticker_interest_score(ticker, hot_map=None):
        """Score a ticker using knowledge-based rules. Uses only ticker-level data (free).

        Scoring is derived from the knowledge files:
        - 02_risk_management.md: liquidity minimums ($10M volume, $50M OI)
        - 04_volume_analysis.md: funding rate thresholds (±0.03%, ±0.05%)
        - 05_crypto_specifics.md: BTC correlation, extreme moves
        - 06_setup_playbook.md: setup triggers (funding squeeze, liquidation cascade)

        Args:
            ticker: dict with symbol, price_change_24h_pct, turnover_24h_usd, etc.
            hot_map: optional dict {symbol: hot_list_entry} from momentum pulse.

        Returns (score, disqualified). Disqualified coins are dropped entirely.
        """
        score = 0
        pct_change = ticker.get("price_change_24h_pct", 0)
        abs_pct = abs(pct_change)
        funding = ticker.get("funding_rate_pct", 0)
        abs_funding = abs(funding)
        turnover = ticker.get("turnover_24h_usd", 0)
        volume = ticker.get("volume_24h", 0)
        oi = ticker.get("open_interest", 0)

        # ===== HARD DISQUALIFIERS (from 02_risk_management, 07_watchlist) =====
        # "Any perp below $50M OI or $10M daily volume should be avoided" — 02_risk_management
        if turnover < 10_000_000:
            return 0, True
        # Low OI = illiquid, unreliable signals
        if oi > 0 and oi < 50_000_000:
            return 0, True

        # ===== LIQUIDITY (higher = more reliable signals) =====
        # "High volume = institutional interest = higher probability moves" — system prompt
        if turnover > 1_000_000_000:
            score += 4  # top-tier liquid
        elif turnover > 500_000_000:
            score += 3
        elif turnover > 100_000_000:
            score += 2
        elif turnover > 50_000_000:
            score += 1

        # ===== PRICE ACTION (from 01_trading_philosophy, 05_crypto_specifics) =====
        # "Unusual 24h % change combined with high turnover suggests attention" — system prompt
        # "Normal daily volatility (crypto): 3-10%" — 05_crypto_specifics
        if abs_pct > 15:
            score += 5  # exceptional event, possible liquidation cascade / climactic move
        elif abs_pct > 10:
            score += 4  # strong move, likely setup forming
        elif abs_pct > 5:
            score += 3  # "FOMO extended move" territory but also breakout candidate
        elif abs_pct > 3:
            score += 2  # above normal crypto vol, worth checking
        elif abs_pct > 1.5:
            score += 1  # mild activity

        # ===== FUNDING RATE (from 04_volume_analysis, 06_setup_playbook) =====
        # ">0.05%/8h = longs crowded (squeeze risk). <-0.05%/8h = shorts crowded" — 04_volume_analysis
        # "Funding rate has been extreme for 24+ hours → squeeze setup" — 06_setup_playbook
        if abs_funding > 0.05:
            score += 5  # extreme crowding = Setup 5 (Funding Squeeze) candidate
        elif abs_funding > 0.03:
            score += 3  # moderate crowding, worth monitoring
        elif abs_funding > 0.01:
            score += 1  # mild bias

        # ===== OI-PRICE DIVERGENCE (from 04_volume_analysis) =====
        # "Price ↑ + OI ↓ = shorts covering (squeeze, near tops)"
        # "Price ↓ + OI ↓ = longs closing (capitulation, near bottoms)"
        # We can't see OI *change* from a single ticker snapshot, but high OI
        # + big move = lots of positions getting tested
        if oi > 200_000_000 and abs_pct > 5:
            score += 2  # high OI + big move = liquidation cluster likely

        # ===== COMBINED SIGNALS (from 06_setup_playbook) =====
        # Setup 5 (Funding Squeeze): extreme funding + price stalling
        if abs_funding > 0.05 and abs_pct < 3:
            score += 3  # crowded BUT price not moving = squeeze building

        # Setup 6 (Post-Liquidation): big move + high volume
        if abs_pct > 10 and turnover > 200_000_000:
            score += 2  # post-liquidation reversal candidate

        # ===== VOLUME ACCELERATION BONUS (from momentum pulse hot list) =====
        if hot_map and ticker.get("symbol") in hot_map:
            hot_entry = hot_map[ticker["symbol"]]
            vol_accel = hot_entry.get("volume_acceleration")
            if vol_accel is not None:
                if vol_accel > 5:
                    score += 4  # extreme volume ramp-up
                elif vol_accel > 2:
                    score += 2  # significant volume ramp-up

        return score, False

    @staticmethod
    def _load_hot_list():
        """Load momentum pulse hot list, removing expired entries.

        Returns (active_coins, market_regime_dict_or_None).
        """
        hot_list_path = Path(config.MOMENTUM_HOT_LIST_PATH)
        if not hot_list_path.exists():
            return [], None
        try:
            data = json.loads(hot_list_path.read_text(encoding="utf-8"))
            regime = data.get("market_regime")
            now = datetime.now(timezone.utc)
            active = []
            for coin in data.get("coins", []):
                expires = datetime.fromisoformat(coin["expires_utc"])
                if expires > now:
                    active.append(coin)
            return active, regime
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"  Warning: could not load hot list: {e}")
            return [], None

    def get_full_market_snapshot(self):
        """Main entry — returns everything Claude needs with multi-TF data.

        Flow:
          1. Fetch top 50 tickers by turnover (single API call, free)
          2. Load momentum pulse hot list (dynamic watchlist)
          3. Disqualify illiquid coins ($10M volume, $50M OI minimums)
          4. Score remaining by knowledge-based rules (free), with hot list bonus
          5. Keep top 25 by score + watchlist + hot list
          6. Fetch multi-TF klines only for those ~25
          7. Send all with full detail to Claude
        """
        # Step 1: Get broad pool of 50 tickers
        broad_pool = self.get_top_movers(50)
        print(f"  Fetched {len(broad_pool)} tickers from Bybit")

        # Step 2: Load momentum pulse hot list (dynamic watchlist) + market regime
        hot_coins, market_regime = self._load_hot_list()
        hot_syms = {coin["symbol"] for coin in hot_coins}
        hot_map = {coin["symbol"]: coin for coin in hot_coins}
        if hot_coins:
            print(f"  Hot list: {len(hot_coins)} active coins "
                  f"({', '.join(sorted(hot_syms))})")

        # Step 3: Score, disqualify illiquid, and rank
        watchlist_syms = set(config.WATCHLIST) | hot_syms
        scored = []
        disqualified = 0
        for t in broad_pool:
            score, disq = self._ticker_interest_score(t, hot_map=hot_map)
            if disq and t["symbol"] not in watchlist_syms:
                disqualified += 1
                continue
            scored.append((t, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        print(f"  Disqualified {disqualified} illiquid coins (< $10M vol or < $50M OI)")

        # Step 4: Keep top 25 + watchlist + hot list (dedup)
        selected_symbols = set()
        selected_movers = []

        # Always include watchlist first
        for t, s in scored:
            if t["symbol"] in watchlist_syms:
                selected_symbols.add(t["symbol"])
                selected_movers.append(t)

        # Fill up to limit from ranked list
        for t, s in scored:
            if len(selected_symbols) >= config.TOP_MOVERS_LIMIT:
                break
            if t["symbol"] not in selected_symbols:
                selected_symbols.add(t["symbol"])
                selected_movers.append(t)

        # Add watchlist symbols that weren't in the top 50 at all
        for sym in watchlist_syms:
            if sym not in selected_symbols:
                selected_symbols.add(sym)

        # Log top scores for debugging
        top_5 = scored[:5]
        print(f"  Top 5 scores: {', '.join(f'{t['symbol']}={s}' for t, s in top_5)}")
        print(f"  Selected {len(selected_symbols)} symbols for multi-TF analysis")

        # Step 5: Fetch multi-TF klines only for selected symbols
        technicals = []
        symbols_list = sorted(selected_symbols)
        total = len(symbols_list)
        for i, sym in enumerate(symbols_list):
            try:
                print(f"  [{i+1}/{total}] Fetching {sym}...")
                technicals.append(self.get_multi_tf_indicators(sym))
            except Exception as e:
                print(f"  Error fetching {sym}: {e}")

        return {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "top_movers": selected_movers,
            "technicals": technicals,
            "market_regime": market_regime,
        }
