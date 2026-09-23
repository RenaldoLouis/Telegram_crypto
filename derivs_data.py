"""Bybit PUBLIC derivatives data: funding-rate history and open-interest history.

Free, keyless, deep (200+ days). Used by `unified_backtest.py` (per-trade positioning
features + the funding-squeeze candidate rules) and — if a rule is ever promoted — by
the live fetcher. Pure data access; zero trading decisions.

Semantics (no look-ahead): every lookup takes a time `t_ms` and answers ONLY from records
whose own timestamp is <= t_ms. Funding settles every 8h at 00/08/16 UTC and the record's
timestamp IS the settlement time; open interest snapshots are stamped at the START of
their interval, so a snapshot at ts covers [ts, ts+interval) and is treated as known at
ts + interval.
"""

import bisect
import json
import time
from datetime import datetime, timezone
from pathlib import Path

CACHE_DIR = Path(__file__).parent / "logs" / "backtest_cache" / "unified"
OI_INTERVAL_MS = {"5min": 300_000, "15min": 900_000, "30min": 1_800_000,
                  "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000}
SETTLEMENT_HOURS = (0, 8, 16)   # UTC funding settlement hours on Bybit USDT perps
FUNDING_MS = 8 * 3_600_000


def _cache_path(kind, symbol, days, extra=""):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    now = int(time.time() * 1000)
    end_day = datetime.now(timezone.utc).strftime("%Y%m%d")
    start_day = datetime.fromtimestamp((now - days * 86_400_000) / 1000, tz=timezone.utc).strftime("%Y%m%d")
    return CACHE_DIR / f"{symbol}_{kind}{extra}_{start_day}_{end_day}.json"


def fetch_funding(client, symbol, days, skip_fetch=False):
    """[(settlement_ts_ms, rate_fraction), ...] oldest first. rate 0.0001 = 0.01%."""
    cp = _cache_path("funding", symbol, days)
    if cp.exists():
        return [tuple(x) for x in json.loads(cp.read_text())]
    if skip_fetch:
        return []
    now = int(time.time() * 1000)
    start = now - days * 86_400_000
    out = {}
    end = now
    for _ in range(40):
        try:
            res = client.get_funding_rate_history(category="linear", symbol=symbol,
                                                  startTime=start, endTime=end, limit=200)
        except Exception as e:
            print(f"    ! {symbol} funding fetch error: {e}")
            break
        rows = res.get("result", {}).get("list", []) or []
        if not rows:
            break
        for r in rows:
            out[int(r["fundingRateTimestamp"])] = float(r["fundingRate"])
        oldest = min(int(r["fundingRateTimestamp"]) for r in rows)
        if oldest <= start or len(rows) < 200:
            break
        end = oldest - 1
        time.sleep(0.1)
    data = sorted(out.items())
    cp.write_text(json.dumps(data))
    return data


def fetch_open_interest(client, symbol, days, interval="1h", skip_fetch=False):
    """[(snapshot_ts_ms, open_interest_contracts), ...] oldest first."""
    cp = _cache_path("oi", symbol, days, extra=f"_{interval}")
    if cp.exists():
        return [tuple(x) for x in json.loads(cp.read_text())]
    if skip_fetch:
        return []
    now = int(time.time() * 1000)
    start = now - days * 86_400_000
    out = {}
    end = now
    for _ in range(80):
        try:
            res = client.get_open_interest(category="linear", symbol=symbol, intervalTime=interval,
                                           startTime=start, endTime=end, limit=200)
        except Exception as e:
            print(f"    ! {symbol} OI fetch error: {e}")
            break
        rows = res.get("result", {}).get("list", []) or []
        if not rows:
            break
        for r in rows:
            out[int(r["timestamp"])] = float(r["openInterest"])
        oldest = min(int(r["timestamp"]) for r in rows)
        if oldest <= start or len(rows) < 200:
            break
        end = oldest - 1
        time.sleep(0.1)
    data = sorted(out.items())
    cp.write_text(json.dumps(data))
    return data


class DerivIndex:
    """Time-indexed, look-ahead-safe access to funding + OI for one symbol."""

    def __init__(self, funding, oi, oi_interval="1h", z_window=30):
        self.f_ts = [t for t, _ in funding]
        self.f_val = [v for _, v in funding]
        step = OI_INTERVAL_MS.get(oi_interval, 3_600_000)
        # OI snapshot at ts is known once its interval has elapsed.
        self.o_ts = [t + step for t, _ in oi]
        self.o_val = [v for _, v in oi]
        self.z_window = z_window

    # ---- funding ----
    def funding_at(self, t_ms):
        """Last SETTLED funding rate (fraction) at or before t_ms, or None."""
        j = bisect.bisect_right(self.f_ts, t_ms) - 1
        return self.f_val[j] if j >= 0 else None

    def funding_z(self, t_ms):
        """z-score of the latest settled rate vs the trailing `z_window` settlements."""
        j = bisect.bisect_right(self.f_ts, t_ms) - 1
        if j < self.z_window:
            return None
        w = self.f_val[j - self.z_window:j]
        mu = sum(w) / len(w)
        var = sum((x - mu) ** 2 for x in w) / len(w)
        sd = var ** 0.5
        return (self.f_val[j] - mu) / sd if sd > 0 else None

    def funding_mean(self, t_ms, n=3):
        """Mean of the last n settled rates (24h at n=3) — smooths one-off prints."""
        j = bisect.bisect_right(self.f_ts, t_ms) - 1
        if j < 0:
            return None
        w = self.f_val[max(0, j - n + 1):j + 1]
        return sum(w) / len(w) if w else None

    # ---- open interest ----
    def oi_at(self, t_ms):
        j = bisect.bisect_right(self.o_ts, t_ms) - 1
        return self.o_val[j] if j >= 0 else None

    def oi_change_pct(self, t_ms, hours):
        now = self.oi_at(t_ms)
        then = self.oi_at(t_ms - hours * 3_600_000)
        if now is None or then is None or then <= 0:
            return None
        return (now / then - 1) * 100

    def has_data(self):
        return bool(self.f_ts) and bool(self.o_ts)


def is_settlement_close(close_ms):
    """True if a bar CLOSING at close_ms coincides with a funding settlement (00/08/16 UTC)."""
    dt = datetime.fromtimestamp(close_ms / 1000, tz=timezone.utc)
    return dt.minute == 0 and dt.hour in SETTLEMENT_HOURS


def hours_to_settlement(t_ms):
    dt = datetime.fromtimestamp(t_ms / 1000, tz=timezone.utc)
    h = dt.hour + dt.minute / 60.0
    nxt = next(x for x in (8, 16, 24) if x > h)
    return round(nxt - h, 2)


def oi_divergence(price_chg_pct, oi_chg_pct, eps_price=0.5, eps_oi=0.5):
    """Classify positioning from price vs OI change over the same window.
      up_up     : new longs opening into the rally (fragile if crowded)
      up_down   : short covering — finite fuel
      down_up   : new shorts pressing — squeeze fuel if price holds
      down_down : longs closing / liquidating — capitulation
      flat      : neither moved enough
    """
    if price_chg_pct is None or oi_chg_pct is None:
        return "na"
    p = "up" if price_chg_pct > eps_price else ("down" if price_chg_pct < -eps_price else "flat")
    o = "up" if oi_chg_pct > eps_oi else ("down" if oi_chg_pct < -eps_oi else "flat")
    if p == "flat" or o == "flat":
        return "flat"
    return f"{p}_{o}"


def attach_to_df(df, deriv, interval_ms, price_lookback_bars):
    """Add per-bar positioning columns to an indicator DataFrame, each computed as of the
    bar's CLOSE time from data available then: funding_rate, funding_mean24h, funding_z,
    oi_chg_24h_pct, price_chg_24h_pct, settlement_close. Missing data → NaN."""
    import math
    n = len(df)
    ts = df["timestamp"].astype("int64").tolist()
    closes = df["close"].astype(float).tolist()
    fr, fm, fz, oc, pc, sc = [], [], [], [], [], []
    for i in range(n):
        close_t = ts[i] + interval_ms
        fr.append(deriv.funding_at(close_t) if deriv else None)
        fm.append(deriv.funding_mean(close_t, 3) if deriv else None)
        fz.append(deriv.funding_z(close_t) if deriv else None)
        oc.append(deriv.oi_change_pct(close_t, 24) if deriv else None)
        k = i - price_lookback_bars
        pc.append((closes[i] / closes[k] - 1) * 100 if k >= 0 and closes[k] else None)
        sc.append(is_settlement_close(close_t))
    nan = float("nan")
    df["funding_rate"] = [x if x is not None else nan for x in fr]
    df["funding_mean24h"] = [x if x is not None else nan for x in fm]
    df["funding_z"] = [x if x is not None else nan for x in fz]
    df["oi_chg_24h_pct"] = [x if x is not None else nan for x in oc]
    df["price_chg_24h_pct"] = [x if x is not None else nan for x in pc]
    df["settlement_close"] = sc
    return df
