"""Behavior tests for the crypto-only universe (2026-10-25): tokenized stock / ETF /
commodity / forex perps never reach the scan or the unified backtest's auto universe.

Run: venv/bin/python test_crypto_universe.py
"""

import json
import tempfile
from pathlib import Path

import config
import unified_backtest as ub
from fetchers.bybit_data import BybitFetcher


def _fetcher(api):
    f = BybitFetcher.__new__(BybitFetcher)   # no HTTP client: _api is stubbed
    f._api = api
    return f


def test_non_crypto_symbols_pages_flags_and_fallback():
    pages = {"": {"list": [{"symbol": "BTCUSDT", "symbolType": ""},
                           {"symbol": "SKHYNIXUSDT", "symbolType": "stock"},
                           {"symbol": "AKEUSDT", "symbolType": "innovation"}],
                  "nextPageCursor": "p2"},
             "p2": {"list": [{"symbol": "KORUUSDT", "symbolType": "ETF"},
                             {"symbol": "CLUSDT", "symbolType": "commodity"},
                             {"symbol": "EURUSDUSDT", "symbolType": "forex"}],
                    "nextPageCursor": ""}}
    calls = []

    def api(method, **kw):
        calls.append((method, kw.get("cursor", "")))
        return {"result": pages[kw.get("cursor", "")]}

    got = _fetcher(api).get_non_crypto_symbols()
    assert {"SKHYNIXUSDT", "KORUUSDT", "CLUSDT", "EURUSDUSDT"} <= got, got
    assert "BTCUSDT" not in got and "AKEUSDT" not in got          # blank / innovation = crypto
    assert set(config.SCAN_EXCLUDE_SYMBOLS) <= got                # pegged tokens Bybit leaves blank
    assert calls == [("get_instruments_info", ""), ("get_instruments_info", "p2")], calls

    def down(method, **kw):
        raise RuntimeError("timeout")

    # a failed call never stops the scan: only the static pegged list is applied
    assert _fetcher(down).get_non_crypto_symbols() == set(config.SCAN_EXCLUDE_SYMBOLS)
    print("  ✓ test_non_crypto_symbols_pages_flags_and_fallback")


def test_drop_non_crypto_cuts_pool_and_hot_list():
    pool = [{"symbol": "BTCUSDT"}, {"symbol": "SKHYNIXUSDT"}, {"symbol": "SUIUSDT"}]
    hot = [{"symbol": "KORUUSDT"}, {"symbol": "PEPEUSDT"}]
    pool2, hot2, dropped = BybitFetcher._drop_non_crypto(pool, hot, {"SKHYNIXUSDT", "KORUUSDT", "XAUTUSDT"})
    assert [t["symbol"] for t in pool2] == ["BTCUSDT", "SUIUSDT"]
    assert [c["symbol"] for c in hot2] == ["PEPEUSDT"]            # hot-list coins skip the liquidity filter
    assert dropped == ["KORUUSDT", "SKHYNIXUSDT"]
    print("  ✓ test_drop_non_crypto_cuts_pool_and_hot_list")


def test_auto_universe_skips_excluded_symbols():
    prev = ub.SETUPS_DIR
    with tempfile.TemporaryDirectory() as d:
        ub.SETUPS_DIR = Path(d)
        try:
            setups = [{"symbol": "SKHYNIXUSDT"}] * 5 + [{"symbol": "PEPEUSDT"}] * 3 + [{"symbol": "WLDUSDT"}]
            (Path(d) / "setups_a.json").write_text(json.dumps({"setups": setups}))
            base = ub.auto_universe(4)
            assert "SKHYNIXUSDT" in base                          # most frequent live symbol
            cut = ub.auto_universe(4, exclude={"SKHYNIXUSDT"})
            assert "SKHYNIXUSDT" not in cut and "PEPEUSDT" in cut and "BTCUSDT" in cut, cut
        finally:
            ub.SETUPS_DIR = prev
    print("  ✓ test_auto_universe_skips_excluded_symbols")


if __name__ == "__main__":
    test_non_crypto_symbols_pages_flags_and_fallback()
    test_drop_non_crypto_cuts_pool_and_hot_list()
    test_auto_universe_skips_excluded_symbols()
    print("All 3 crypto-universe tests passed.")
