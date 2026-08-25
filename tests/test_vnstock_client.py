"""Unit and adversarial tests for offline VnstockMarketClient parser, universe metadata, and raw accounting."""

import unittest
from datetime import datetime, timezone

from pipeline.models import VN30_SYMBOLS, VN30_UNIVERSE_CONFIG
from pipeline.providers.vnstock_client import VnstockMarketClient
from pipeline.providers.vnstock_provider import VnstockDataProvider


class TestVnstockMarketClient(unittest.TestCase):
    """Test suite verifying VnstockMarketClient offline parsing, raw accounting, date filtering, and quarantine guards."""

    def test_vn30_canonical_universe_metadata_and_constituents(self):
        """Verify VN30 canonical universe metadata: effective date 2026-08-03, MCH/TCX included, PLX/TPB excluded."""
        self.assertEqual(VN30_UNIVERSE_CONFIG.name, "VN30")
        self.assertEqual(VN30_UNIVERSE_CONFIG.version, "2026-08-03")
        self.assertEqual(VN30_UNIVERSE_CONFIG.effective_date, "2026-08-03")
        self.assertIn("HOSE", VN30_UNIVERSE_CONFIG.source)

        constituents = VN30_UNIVERSE_CONFIG.constituents
        self.assertEqual(len(constituents), 30)
        self.assertEqual(len(set(constituents)), 30)
        self.assertEqual(VN30_SYMBOLS, constituents)

        # August 2026 Index Review: MCH and TCX added
        self.assertIn("MCH", constituents)
        self.assertIn("TCX", constituents)

        # Removed constituents: PLX and TPB excluded
        self.assertNotIn("PLX", constituents)
        self.assertNotIn("TPB", constituents)

        for sym in constituents:
            self.assertTrue(sym.isalnum() and sym.isupper(), f"Invalid symbol: {sym}")

    def test_parse_raw_payload_success(self):
        """Verify offline parsing of standard OHLCV payload format."""
        mock_payload = {
            "t": [1787277600, 1787536800, 1787623200],
            "o": [70.0, 71.0, 71.5],
            "h": [72.0, 72.5, 72.0],
            "l": [69.5, 70.8, 70.7],
            "c": [71.5, 72.0, 70.7],
            "v": [5000000, 4500000, 4690000],
        }

        bars = VnstockMarketClient.parse_raw_payload(mock_payload, "FPT")
        self.assertEqual(len(bars), 3)

        latest = bars[-1]
        self.assertEqual(latest["symbol"], "FPT")
        self.assertEqual(latest["close"], 70.7)
        self.assertEqual(latest["open"], 71.5)
        self.assertEqual(latest["high"], 72.0)
        self.assertEqual(latest["low"], 70.7)
        self.assertEqual(latest["volume"], 4690000)
        self.assertEqual(latest["exchange"], "HOSE")
        self.assertTrue(latest["in_vn30"])

    def test_raw_row_accounting_with_malformed_and_nonpositive_prices(self):
        """Verify raw rows (including invalid prices) are preserved for provider input/accepted/rejected accounting."""
        mock_payload = {
            "t": [1787277600, 1787536800],
            "o": [70.0, 71.0],
            "h": [72.0, 72.5],
            "l": [69.5, 70.8],
            "c": [71.5, -5.0],  # Negative close
            "v": [5000000, 4500000],
        }

        client = VnstockMarketClient(fixture_fetcher=lambda sym: mock_payload)
        provider = VnstockDataProvider(client=client)
        result = provider.fetch_ohlcv(symbols=["FPT"])

        self.assertEqual(result.input_rows, 2)
        self.assertEqual(result.accepted_rows, 1)
        self.assertEqual(result.rejected_rows, 1)
        self.assertTrue(len(result.warnings) > 0)
        self.assertEqual(result.input_rows, result.accepted_rows + result.rejected_rows)

    def test_raw_row_accounting_with_date_range_filtering(self):
        """Regression test: Rows outside start_date/end_date are strictly accounted as rejected_rows.

        Demonstrates that input_rows == accepted_rows + rejected_rows invariant holds exactly
        when date filtering is applied.
        """
        # Timestamps for dates:
        # 2026-08-01, 2026-08-05, 2026-08-10, 2026-08-15, 2026-08-20
        d1 = int(datetime(2026, 8, 1, tzinfo=timezone.utc).timestamp())
        d2 = int(datetime(2026, 8, 5, tzinfo=timezone.utc).timestamp())
        d3 = int(datetime(2026, 8, 10, tzinfo=timezone.utc).timestamp())
        d4 = int(datetime(2026, 8, 15, tzinfo=timezone.utc).timestamp())
        d5 = int(datetime(2026, 8, 20, tzinfo=timezone.utc).timestamp())

        mock_payload = {
            "t": [d1, d2, d3, d4, d5],
            "o": [70.0, 71.0, 72.0, 73.0, 74.0],
            "h": [71.0, 72.0, 73.0, 74.0, 75.0],
            "l": [69.0, 70.0, 71.0, 72.0, 73.0],
            "c": [70.5, 71.5, 72.5, 73.5, 74.5],
            "v": [1000, 1000, 1000, 1000, 1000],
        }

        client = VnstockMarketClient(fixture_fetcher=lambda sym: mock_payload)
        provider = VnstockDataProvider(client=client)

        # Filter to 2026-08-08 .. 2026-08-18 (should accept d3, d4 = 2 rows; reject d1, d2, d5 = 3 rows)
        result = provider.fetch_ohlcv(
            symbols=["FPT"],
            start_date="2026-08-08",
            end_date="2026-08-18",
        )

        self.assertEqual(result.input_rows, 5)
        self.assertEqual(result.accepted_rows, 2)
        self.assertEqual(result.rejected_rows, 3)
        self.assertEqual(result.input_rows, result.accepted_rows + result.rejected_rows)
        self.assertTrue(any("outside requested date range" in w for w in result.warnings))

    def test_array_length_mismatch_strict_accounting(self):
        """Verify array length mismatch is accounted as rejected rows with sanitized warnings."""
        mock_payload = {
            "t": [1787277600, 1787536800, 1787623200],
            "o": [70.0, 71.0],  # Only 2 items, t has 3 items
            "h": [72.0, 72.5, 72.0],
            "l": [69.5, 70.8, 70.7],
            "c": [71.5, 72.0, 70.7],
            "v": [5000000, 4500000, 4690000],
        }

        client = VnstockMarketClient(fixture_fetcher=lambda sym: mock_payload)
        provider = VnstockDataProvider(client=client)
        result = provider.fetch_ohlcv(symbols=["FPT"])

        self.assertEqual(result.input_rows, 3)
        self.assertEqual(result.accepted_rows, 2)
        self.assertEqual(result.rejected_rows, 1)
        self.assertEqual(result.input_rows, result.accepted_rows + result.rejected_rows)

    def test_quarantine_live_provider_fail_closed_guard(self):
        """Verify VnstockDataProvider raises RuntimeError when is_live=True without verified licence."""
        with self.assertRaises(RuntimeError) as ctx:
            VnstockDataProvider(is_live=True)
        self.assertIn("disabled", str(ctx.exception).lower())

        unconfigured = VnstockDataProvider()
        health = unconfigured.health_check()
        self.assertFalse(health.is_healthy)
        self.assertIn("quarantined", health.message.lower())

    def test_network_transport_disabled_and_quarantined(self):
        """Verify VnstockMarketClient has zero network transport and raises RuntimeError if live fetch attempted."""
        client_no_fixture = VnstockMarketClient()
        with self.assertRaises(RuntimeError) as ctx:
            client_no_fixture.fetch_daily_bars("FPT")
        self.assertIn("disabled", str(ctx.exception).lower())

        is_ok, msg, lat = client_no_fixture.probe("FPT")
        self.assertFalse(is_ok)
        self.assertIn("disabled", msg.lower())


if __name__ == "__main__":
    unittest.main()
