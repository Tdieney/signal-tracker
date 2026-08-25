"""Unit and adversarial tests for VnstockMarketClient, universe metadata, and raw accounting."""

import io
import json
import unittest
import urllib.error
import urllib.request
from unittest.mock import MagicMock

from pipeline.models import VN30_SYMBOLS, VN30_UNIVERSE_CONFIG
from pipeline.providers.vnstock_client import VnstockMarketClient
from pipeline.providers.vnstock_provider import VnstockDataProvider


class DummyHTTPResponse(io.BytesIO):
    """Mock urllib response object."""
    def __init__(self, data: bytes, code: int = 200):
        super().__init__(data)
        self.code = code
        self.status = code

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class TestVnstockMarketClient(unittest.TestCase):
    """Test suite verifying VnstockMarketClient behavior, raw accounting, retries, and quarantine guards."""

    def setUp(self):
        self.mock_opener = MagicMock(spec=urllib.request.OpenerDirector)
        self.client = VnstockMarketClient(
            rate_limit_delay_seconds=0.0,
            max_retries=3,
            timeout_seconds=5.0,
            opener=self.mock_opener,
        )

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

    def test_fetch_daily_bars_successful_response(self):
        """Verify parsing of standard OHLCV payload format."""
        mock_payload = {
            "t": [1787277600, 1787536800, 1787623200],
            "o": [70.0, 71.0, 71.5],
            "h": [72.0, 72.5, 72.0],
            "l": [69.5, 70.8, 70.7],
            "c": [71.5, 72.0, 70.7],
            "v": [5000000, 4500000, 4690000],
        }
        mock_resp = DummyHTTPResponse(json.dumps(mock_payload).encode("utf-8"))
        self.mock_opener.open.return_value = mock_resp

        bars = self.client.fetch_daily_bars("FPT", lookback_days=30)
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
        mock_resp = DummyHTTPResponse(json.dumps(mock_payload).encode("utf-8"))
        self.mock_opener.open.return_value = mock_resp

        provider = VnstockDataProvider(client=self.client)
        result = provider.fetch_ohlcv(symbols=["FPT"])

        self.assertEqual(result.input_rows, 2)
        self.assertEqual(result.accepted_rows, 1)
        self.assertEqual(result.rejected_rows, 1)
        self.assertTrue(len(result.warnings) > 0)
        self.assertEqual(result.input_rows, result.accepted_rows + result.rejected_rows)

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
        mock_resp = DummyHTTPResponse(json.dumps(mock_payload).encode("utf-8"))
        self.mock_opener.open.return_value = mock_resp

        provider = VnstockDataProvider(client=self.client)
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

    def test_fetch_daily_bars_retries_on_transient_failure(self):
        """Verify automatic retry with backoff on transient HTTP 500 error."""
        error_resp = urllib.error.HTTPError("https://services.entrade.com.vn", 500, "Server Error", {}, None)
        valid_payload = {
            "t": [1787623200],
            "o": [71.5],
            "h": [72.0],
            "l": [70.7],
            "c": [70.7],
            "v": [4690000],
        }
        success_resp = DummyHTTPResponse(json.dumps(valid_payload).encode("utf-8"))

        self.mock_opener.open.side_effect = [error_resp, error_resp, success_resp]

        bars = self.client.fetch_daily_bars("FPT")
        self.assertEqual(len(bars), 1)
        self.assertEqual(self.mock_opener.open.call_count, 3)

    def test_fetch_daily_bars_fails_gracefully_on_persistent_error(self):
        """Verify persistent HTTP error returns empty list without crashing."""
        error_resp = urllib.error.HTTPError("https://services.entrade.com.vn", 503, "Service Unavailable", {}, None)
        self.mock_opener.open.side_effect = error_resp

        bars = self.client.fetch_daily_bars("FPT")
        self.assertEqual(bars, [])
        self.assertEqual(self.mock_opener.open.call_count, 3)

    def test_probe_success_and_failure(self):
        """Verify probe returns correct health tuple."""
        mock_payload = {
            "t": [1787623200],
            "o": [71.5],
            "h": [72.0],
            "l": [70.7],
            "c": [70.7],
            "v": [4690000],
        }
        self.mock_opener.open.return_value = DummyHTTPResponse(json.dumps(mock_payload).encode("utf-8"))
        is_ok, msg, lat = self.client.probe("FPT")
        self.assertTrue(is_ok)
        self.assertIn("succeeded", msg)

        self.mock_opener.open.side_effect = urllib.error.URLError("Connection refused")
        is_ok_fail, msg_fail, lat_fail = self.client.probe("FPT")
        self.assertFalse(is_ok_fail)


if __name__ == "__main__":
    unittest.main()
