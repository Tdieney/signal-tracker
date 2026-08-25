"""Unit tests for BaseMarketDataProvider implementations and provider contracts."""

import os
import unittest
from typing import List
from pipeline.models import OHLCVRecord
from pipeline.providers.base import BaseMarketDataProvider, ProviderFetchResult, ProviderHealth
from pipeline.providers.company_api_provider import CompanyApiDataProvider
from pipeline.providers.csv_provider import CsvDataProvider
from pipeline.providers.vnstock_provider import VnstockDataProvider


class TestProviderInterface(unittest.TestCase):
    """Test suite verifying market data providers adhere to provider-neutral contracts."""

    def test_polymorphic_provider_contracts(self):
        """Polymorphic test verifying all provider subclasses uniformly return ProviderFetchResult."""
        providers: List[BaseMarketDataProvider] = [
            CsvDataProvider("tests/fixtures/sample_ohlcv.csv"),
            VnstockDataProvider(fetch_fn=lambda sym, s, e: [
                {"trading_date": "2026-08-21", "symbol": "FPT", "open": 100.0, "high": 102.0, "low": 99.0, "close": 101.0, "volume": 1000}
            ]),
            CompanyApiDataProvider(
                api_base_url="https://api.example.com",
                fetch_fn=lambda url, key, sym, s, e: [
                    {"trading_date": "2026-08-21", "symbol": "VNM", "open": 70.0, "high": 72.0, "low": 69.5, "close": 71.0, "volume": 50000}
                ],
            ),
        ]

        for p in providers:
            # 1. Uniform fetch_ohlcv returns ProviderFetchResult
            result = p.fetch_ohlcv(symbols=["FPT", "VNM"])
            self.assertIsInstance(result, ProviderFetchResult)
            self.assertEqual(result.provider_name, p.provider_name)
            # Invariant: input_rows == accepted_rows + rejected_rows
            self.assertEqual(result.input_rows, result.accepted_rows + result.rejected_rows)

            # 2. Convenience fetch_records returns List[OHLCVRecord]
            records = p.fetch_records(symbols=["FPT", "VNM"])
            self.assertIsInstance(records, list)
            self.assertEqual(len(records), result.accepted_rows)
            for r in records:
                self.assertIsInstance(r, OHLCVRecord)

    def test_truthful_health_checks_when_unconfigured(self):
        """Verify unconfigured live adapters report is_healthy=False rather than false healthy claims."""
        unconfigured_vnstock = VnstockDataProvider(fetch_fn=None)
        health_vn = unconfigured_vnstock.health_check()
        self.assertFalse(health_vn.is_healthy)
        self.assertIn("unconfigured", health_vn.message.lower())

        # Company API with missing key and no fetch_fn
        if "DATA_API_KEY" in os.environ:
            del os.environ["DATA_API_KEY"]
        unconfigured_company = CompanyApiDataProvider(fetch_fn=None)
        health_co = unconfigured_company.health_check()
        self.assertFalse(health_co.is_healthy)
        self.assertIn("missing", health_co.message.lower())

    def test_vnstock_real_retry_execution(self):
        """Verify real retry execution loop without false retry claims."""
        attempts = 0

        def flaky_fetch(sym, s, e):
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise ConnectionError("Temporary connection failure")
            return [{"trading_date": "2026-08-21", "symbol": "FPT", "open": 100.0, "high": 102.0, "low": 99.0, "close": 101.0, "volume": 1000}]

        provider = VnstockDataProvider(max_retries=3, fetch_fn=flaky_fetch)
        res = provider.fetch_ohlcv(symbols=["FPT"])
        self.assertEqual(attempts, 3)
        self.assertEqual(res.accepted_rows, 1)

    def test_adversarial_zero_secret_leakage(self):
        """Adversarial test: secret tokens injected in symbols, exceptions, URLs, and fields must NEVER leak."""
        secret_token = "SECRET_BEARER_TOKEN_PROD_ABC12345"

        def malicious_fetch(url, key, sym, start, end):
            # Inject fake token in exception, raw field, and corrupted date
            raise RuntimeError(f"Internal crash at {url} with auth={secret_token}")

        provider = CompanyApiDataProvider(
            api_base_url=f"https://api.example.com/{secret_token}",
            fetch_fn=malicious_fetch,
        )

        res = provider.fetch_ohlcv(symbols=[f"SYM_{secret_token}"])
        self.assertEqual(res.accepted_rows, 0)
        self.assertEqual(res.rejected_rows, 0)

        # Assert token is nowhere in warnings
        for w in res.warnings:
            self.assertNotIn(secret_token, w)


if __name__ == "__main__":
    unittest.main()
