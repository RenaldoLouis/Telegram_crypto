"""
liquidation_collector.py — persistent forward-collector for Bybit liquidation
events (FORK A, 2026-08-09). True historical liquidation data is not free
(Bybit's feed is a real-time WS stream, no historical REST endpoint), so we
accumulate it going forward and backtest the liquidation-CLUSTER hypothesis
(distance to a liq magnet) once ~2-4 weeks of data exist.

This is a DATA COLLECTOR ONLY — it makes ZERO trading decisions and touches no
order API (Phase A / CORE PRINCIPLE: edge lives in our Python, never in a live
feed reaction). It appends raw liquidation prints to logs/liquidations/.

Runs as a launchd KeepAlive daemon (see com.user.liqcollector.plist). Honest
caveat: it only collects while the Mac is awake AND the VPN is up (Bybit is
ISP-blocked here) — expect gaps; that is fine, clusters are what we backtest.

Run manually:  source venv/bin/activate && python liquidation_collector.py
"""
import os, json, time, signal, sys
from datetime import datetime, timezone

from pybit.unified_trading import WebSocket

# Broad, liquid perp set — superset of the 15-symbol validation universe + majors
# so collected clusters cover whatever the scan trades. Edit freely.
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "SUIUSDT",
    "XLMUSDT", "ENAUSDT", "HBARUSDT", "TRXUSDT", "NEARUSDT", "OPUSDT", "ARBUSDT",
    "INJUSDT", "LINKUSDT", "AVAXUSDT", "LTCUSDT", "TONUSDT", "WLDUSDT",
]

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "liquidations")
os.makedirs(LOG_DIR, exist_ok=True)

_count = 0


def _log_path():
    # rotate monthly so files stay manageable
    return os.path.join(LOG_DIR, f"liq_{datetime.now(timezone.utc):%Y-%m}.jsonl")


def _handle(msg):
    """Append every liquidation print as one JSON line. Bybit allLiquidation
    payload: data[] items have T (ms), s (symbol), S (side), v (qty), p (price)."""
    global _count
    try:
        rows = msg.get("data") or []
        if isinstance(rows, dict):
            rows = [rows]
        recv_ms = int(msg.get("ts") or 0)
        lines = []
        for r in rows:
            try:
                price = float(r.get("p") or 0)
                qty = float(r.get("v") or 0)
            except (TypeError, ValueError):
                price, qty = 0.0, 0.0
            lines.append(json.dumps({
                "t": int(r.get("T") or recv_ms),   # event time (ms)
                "sym": r.get("s"),
                "side": r.get("S"),                  # Buy/Sell (close direction)
                "price": price,
                "qty": qty,
                "notional": round(price * qty, 2),
            }, separators=(",", ":")))
        if lines:
            with open(_log_path(), "a") as f:
                f.write("\n".join(lines) + "\n")
            _count += len(lines)
    except Exception as e:  # never let a bad message kill the collector
        print(f"[liq] handler error: {type(e).__name__}: {e}", flush=True)


def main():
    print(f"[liq] starting collector for {len(SYMBOLS)} symbols -> {LOG_DIR}", flush=True)
    try:
        ws = WebSocket(testnet=False, channel_type="linear")
    except Exception as e:
        print(f"[liq] WS connect failed (VPN down?): {type(e).__name__}: {e}", flush=True)
        sys.exit(1)  # launchd KeepAlive will retry after ThrottleInterval

    # subscribe per symbol (topic: allLiquidation.<symbol>)
    for sym in SYMBOLS:
        try:
            ws.all_liquidation_stream(symbol=sym, callback=_handle)
        except Exception as e:
            print(f"[liq] subscribe {sym} failed: {type(e).__name__}: {e}", flush=True)

    def _bye(*_):
        print(f"[liq] shutting down (collected {_count} events this run)", flush=True)
        sys.exit(0)
    signal.signal(signal.SIGTERM, _bye)
    signal.signal(signal.SIGINT, _bye)

    # Optional self-limit for ephemeral CI runners (GitHub Actions job cap is 6h):
    # exit cleanly after LIQ_MAX_SECONDS so the artifact-upload step still runs.
    # 0/unset = run forever (the launchd daemon case).
    try:
        max_s = int(os.environ.get("LIQ_MAX_SECONDS", "0") or "0")
    except ValueError:
        max_s = 0
    start = time.time()

    # keep the main thread alive; pybit runs the socket on its own thread and
    # auto-reconnects. Heartbeat every 15 min so logs show liveness.
    last = 0
    while True:
        time.sleep(60)
        if max_s and time.time() - start >= max_s:
            print(f"[liq] max_seconds={max_s} reached — clean exit "
                  f"({_count} events collected this run)", flush=True)
            sys.exit(0)
        if time.time() - last >= 900:
            print(f"[liq] alive @ {datetime.now(timezone.utc):%Y-%m-%d %H:%M}Z — "
                  f"{_count} events collected this run", flush=True)
            last = time.time()


if __name__ == "__main__":
    main()
