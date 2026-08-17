"""cvd_collector.py — persistent forward-collector for Bybit taker ORDER FLOW
(CVD), Phase 2 of roadmap #4 (2026-08-17).

WHY: `cvd_backtest.py` found — on free Binance history — that a CVD-slope
(flow-momentum) CONFIRMATION filter on `rsi_rejection_short` carries a robust,
OOS-stable, monotonic net-of-cost edge (+0.11..+0.13R on 4h). That result is a
BINANCE proxy; Bybit has NO free historical trade/CVD feed (recent-trade REST
caps at ~1000 trades), so to confirm the effect ON-VENUE we must accumulate
Bybit's own taker flow going forward and re-test in ~3-4 weeks.

This is a DATA COLLECTOR ONLY — it makes ZERO trading decisions and touches no
order API (Phase A / CORE PRINCIPLE: the edge lives in our Python, never in a
live feed reaction).

STORAGE: raw trade tape is huge, so we DON'T store it. Trades are aggregated in
memory into PER-MINUTE taker buckets (buy/sell base + quote volume, trade count)
and only completed minutes are flushed to logs/cvd/cvd_YYYY-MM.jsonl. From those
per-minute deltas any bar's CVD / CVD-slope is reconstructable at backtest time.

Mirrors liquidation_collector.py: chained ~5.5h CI jobs (CVD_MAX_SECONDS self-
exit) uploading dated artifacts, reusing the WireGuard VPN. Also runnable locally.

Run manually:  source venv/bin/activate && python cvd_collector.py
"""
import os, json, time, signal, sys, threading
from datetime import datetime, timezone

from pybit.unified_trading import WebSocket

# Same liquid perp set as the liquidation collector so the two datasets align.
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "SUIUSDT",
    "XLMUSDT", "ENAUSDT", "HBARUSDT", "TRXUSDT", "NEARUSDT", "OPUSDT", "ARBUSDT",
    "INJUSDT", "LINKUSDT", "AVAXUSDT", "LTCUSDT", "TONUSDT", "WLDUSDT",
]

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "cvd")
os.makedirs(LOG_DIR, exist_ok=True)

_lock = threading.Lock()
_buckets = {}   # (symbol, minute_start_ms) -> aggregate dict
_written = 0


def _log_path():
    return os.path.join(LOG_DIR, f"cvd_{datetime.now(timezone.utc):%Y-%m}.jsonl")


def _handle(msg):
    """Aggregate each publicTrade into its per-minute bucket. Bybit publicTrade
    item: T (ms), s (symbol), S (taker side Buy/Sell), v (size, base), p (price)."""
    try:
        rows = msg.get("data") or []
        if isinstance(rows, dict):
            rows = [rows]
        with _lock:
            for r in rows:
                sym = r.get("s")
                t = int(r.get("T") or 0)
                if not sym or not t:
                    continue
                try:
                    p = float(r.get("p") or 0)
                    v = float(r.get("v") or 0)
                except (TypeError, ValueError):
                    continue
                mb = (t // 60000) * 60000          # minute bucket (ms)
                b = _buckets.get((sym, mb))
                if b is None:
                    b = {"buy_v": 0.0, "sell_v": 0.0,
                         "buy_q": 0.0, "sell_q": 0.0, "n": 0}
                    _buckets[(sym, mb)] = b
                quote = p * v
                if r.get("S") == "Buy":            # taker BUY (aggressor lifted ask)
                    b["buy_v"] += v
                    b["buy_q"] += quote
                else:                              # taker SELL (aggressor hit bid)
                    b["sell_v"] += v
                    b["sell_q"] += quote
                b["n"] += 1
    except Exception as e:  # never let a bad message kill the collector
        print(f"[cvd] handler error: {type(e).__name__}: {e}", flush=True)


def _flush(final=False):
    """Write out minutes older than the current one (or everything on `final`)."""
    global _written
    now_mb = (int(time.time() * 1000) // 60000) * 60000
    lines = []
    with _lock:
        keys = [k for k in list(_buckets) if final or k[1] < now_mb]
        for k in keys:
            sym, mb = k
            b = _buckets.pop(k)
            lines.append(json.dumps({
                "t": mb, "sym": sym,
                "buy_v": round(b["buy_v"], 4), "sell_v": round(b["sell_v"], 4),
                "buy_q": round(b["buy_q"], 2), "sell_q": round(b["sell_q"], 2),
                "n": b["n"],
            }, separators=(",", ":")))
    if lines:
        with open(_log_path(), "a") as f:
            f.write("\n".join(lines) + "\n")
        _written += len(lines)
    return len(lines)


def main():
    print(f"[cvd] starting collector for {len(SYMBOLS)} symbols -> {LOG_DIR}",
          flush=True)
    try:
        ws = WebSocket(testnet=False, channel_type="linear")
    except Exception as e:
        print(f"[cvd] WS connect failed (VPN down?): {type(e).__name__}: {e}",
              flush=True)
        sys.exit(1)  # launchd/CI will retry

    for sym in SYMBOLS:
        try:
            ws.trade_stream(symbol=sym, callback=_handle)
        except Exception as e:
            print(f"[cvd] subscribe {sym} failed: {type(e).__name__}: {e}",
                  flush=True)

    def _bye(*_):
        n = _flush(final=True)
        print(f"[cvd] shutting down — flushed final {n} buckets "
              f"({_written} minute-buckets written this run)", flush=True)
        sys.exit(0)
    signal.signal(signal.SIGTERM, _bye)
    signal.signal(signal.SIGINT, _bye)

    try:
        max_s = int(os.environ.get("CVD_MAX_SECONDS", "0") or "0")
    except ValueError:
        max_s = 0
    start = time.time()
    last_hb = 0

    # pybit runs the socket on its own thread + auto-reconnects. This thread
    # flushes completed minutes every 30s and heartbeats every 15min.
    while True:
        time.sleep(30)
        _flush()
        if max_s and time.time() - start >= max_s:
            n = _flush(final=True)
            print(f"[cvd] max_seconds={max_s} reached — clean exit "
                  f"(final {n}, {_written} minute-buckets this run)", flush=True)
            sys.exit(0)
        if time.time() - last_hb >= 900:
            print(f"[cvd] alive @ {datetime.now(timezone.utc):%Y-%m-%d %H:%M}Z — "
                  f"{_written} minute-buckets written, {len(_buckets)} open",
                  flush=True)
            last_hb = time.time()


if __name__ == "__main__":
    main()
