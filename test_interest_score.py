"""Offline tests for the pre-filter's open-interest rules (fix 2026-11-02).

Bybit's ticker `openInterest` is in COINS; `openInterestValue` is in USD. The pre-filter's thresholds
($50M disqualifier, $200M bonus) are dollar amounts, so they must read the USD value. Before the fix
BTC (≈68k coins ≈ $5.4B) failed the $50M test and cheap high-supply coins with < $50M passed it.
"""

import unittest
from unittest import mock

from fetchers.bybit_data import BybitFetcher

score = BybitFetcher._ticker_interest_score


def ticker(oi_coins, oi_usd, pct=0.0, turnover=200e6, funding=0.0):
    return {"symbol": "XUSDT", "price_change_24h_pct": pct, "turnover_24h_usd": turnover,
            "volume_24h": 1.0, "funding_rate_pct": funding,
            "open_interest": oi_coins, "open_interest_value": oi_usd}


class OpenInterestInDollars(unittest.TestCase):
    def test_expensive_coin_with_large_oi_passes(self):
        _, disq = score(ticker(oi_coins=68_000, oi_usd=5.4e9))
        self.assertFalse(disq)

    def test_cheap_coin_with_small_dollar_oi_is_disqualified(self):
        _, disq = score(ticker(oi_coins=2e9, oi_usd=20e6))
        self.assertTrue(disq)

    def test_big_move_bonus_uses_dollars(self):
        # same move; only the dollar OI crosses $200M → +2
        low, _ = score(ticker(oi_coins=5e9, oi_usd=150e6, pct=6.0))
        high, _ = score(ticker(oi_coins=1_000, oi_usd=250e6, pct=6.0))
        self.assertEqual(high - low, 2)

    def test_missing_oi_value_does_not_disqualify(self):
        _, disq = score(ticker(oi_coins=0, oi_usd=0))
        self.assertFalse(disq)

    def test_turnover_floor_unchanged(self):
        _, disq = score(ticker(oi_coins=1e9, oi_usd=1e9, turnover=9e6))
        self.assertTrue(disq)


class TopMoversCarriesDollarOi(unittest.TestCase):
    def test_open_interest_value_mapped(self):
        f = BybitFetcher.__new__(BybitFetcher)
        row = {"symbol": "BTCUSDT", "lastPrice": "78000", "price24hPcnt": "0.01", "turnover24h": "9e9",
               "volume24h": "1", "fundingRate": "0.0001", "openInterest": "68218.975",
               "openInterestValue": "5358825608.87"}
        with mock.patch.object(BybitFetcher, "_api", return_value={"result": {"list": [row]}}, create=True):
            out = f.get_top_movers(1)
        self.assertAlmostEqual(out[0]["open_interest_value"], 5358825608.87)
        self.assertAlmostEqual(out[0]["open_interest"], 68218.975)


if __name__ == "__main__":
    unittest.main()
