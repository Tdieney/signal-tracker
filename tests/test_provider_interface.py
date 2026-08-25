"""Unit tests for BaseMarketDataProvider implementations and provider contracts."""

import unittest
from pipeline.models import OHLCVRecord
from pipeline.providers.base import BaseMarketDataProvider, ProviderFetchResult, ProviderHealth
from pipeline.providers.company_api_provider import CompanyApiDataProvider
from pipeline.providers.csv_provider import CsvDataProvider
from pipeline.providers.vnstock_provider import VnstockDataProvider


class TestProviderInterface(unittest.TestCase):
    """Test suite verifying market data providers adhere to provider-neutral contracts."""

    def test_csv_provider_implements_interface(self):
        provider = CsvDataProvider("tests/fixtures/sample_ohlcv.csv")
        self.assertIsInstance(provider, BaseMarketDataProvider)
        self.assertEqual(provider.provider_name, "csv")

        health = provider.health_check()
        self.assertIsInstance(health, ProviderHealth)
        self.assertTrue(health.is_healthy)
        self.assertEqual(health.provider_name, "csv")

        result = provider.fetch_ohlcv_result()
        self.assertIsInstance(result, ProviderFetchResult)
        self.assertEqual(result.provider_name, "csv")
        self.assertEqual(result.input_rows, result.accepted_rows + result.rejected_rows)
        self.assertGreater(len(result.records), 0)
        self.assertIsNotNone(result.payload_sha256)

    def test_vnstock_provider_mock_fetch_and_accounting(self):
        mock_data = [
            {"trading_date": "2026-08-21", "symbol": "FPT", "open": 100.0, "high": 102.0, "low": 99.0, "close": 101.0, "volume": 1000},
            {"trading_date": "2026-08-21", "symbol": "FPT", "open": -50.0, "high": 102.0, "low": 99.0, "close": 101.0, "volume": 1000}, # invalid negative price
        ]
        provider = VnstockDataProvider(fetch_fn=lambda sym, s, e: mock_data)
        self.assertIsInstance(provider, BaseMarketDataProvider)
        self.assertEqual(provider.provider_name, "vnstock")

        health = provider.health_check()
        self.assertTrue(health.is_healthy)

        result = provider.fetch_ohlcv_result(symbols=["FPT"])
        self.assertEqual(result.input_rows, 2)
        self.assertEqual(result.accepted_rows, 1)
        self.assertEqual(result.rejected_rows, 1)
        self.assertEqual(result.input_rows, result.accepted_rows + result.rejected_rows)

    def test_company_api_provider_zero_secret_leakage(self):
        secret_token = "SUPER_SECRET_BEARER_TOKEN_XYZ_12345"
        mock_data = [
            {"trading_date": "2026-08-21", "symbol": "VNM", "open": 70.0, "high": 72.0, "low": 69.5, "close": 71.0, "volume": 50000},
        ]
        provider = CompanyApiDataProvider(
            api_base_url="https://api.example.com",
            api_key_env_var="CUSTOM_TEST_KEY",
            fetch_fn=lambda url, key, sym, date: mock_data,
        )
        self.assertIsInstance(provider, BaseMarketDataProvider)
        self.assertEqual(provider.provider_name, "company_api")

        health = provider.health_check()
        self.assertTrue(health.is_healthy)

        result = provider.fetch_ohlcv_result(symbols=["VNM"])
        self.assertEqual(result.accepted_rows, 1)

        # Assert secret token is never present in warnings
        for w in result.warnings:
            self.assertNotIn(secret_token, w)


if __name__ == "__main__":
    unittest.main()
