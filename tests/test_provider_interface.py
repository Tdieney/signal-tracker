"""Unit tests for BaseMarketDataProvider implementations, provider contracts, and adversarial secret containment."""

import os
import unittest
from typing import List
from pipeline.models import OHLCVRecord
from pipeline.providers.base import (
    BaseMarketDataProvider,
    ProviderFetchResult,
    ProviderHealth,
    safe_date_label,
    safe_symbol_label,
)
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
            result = p.fetch_ohlcv(symbols=["FPT", "VNM"])
            self.assertIsInstance(result, ProviderFetchResult)
            self.assertEqual(result.provider_name, p.provider_name)
            self.assertEqual(result.input_rows, result.accepted_rows + result.rejected_rows)

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

    def test_adversarial_zero_secret_leakage_exact_tokens(self):
        """Adversarial test: exact tokens (1234-56-78, ABC12345, ghp_FAKE_TOKEN_123456789) injected across fields NEVER leak."""
        test_tokens = [
            "1234-56-78",
            "ABC12345",
            "ghp_FAKE_TOKEN_123456789",
        ]

        for token in test_tokens:
            # 1. Company API injection in URL, Key, Exception, Response
            def malicious_fetch(url, key, sym, start, end):
                raise RuntimeError(f"Crashing with token {token} at {url}")

            provider_co = CompanyApiDataProvider(
                api_base_url=f"https://api.example.com/{token}",
                fetch_fn=malicious_fetch,
            )
            res_co = provider_co.fetch_ohlcv(symbols=[f"MAL_{token}"])
            for w in res_co.warnings:
                self.assertNotIn(token, w, f"Token '{token}' leaked in CompanyApi warning: {w}")

            # 2. Vnstock injection in response payload and invalid date
            def bad_response_fetch(sym, start, end):
                return [
                    {
                        "trading_date": f"DATE_{token}",
                        "symbol": f"SYM_{token}",
                        "open": -1.0,
                        "high": 100.0,
                        "low": 90.0,
                        "close": 95.0,
                        "volume": -100,
                    }
                ]

            provider_vn = VnstockDataProvider(fetch_fn=bad_response_fetch)
            res_vn = provider_vn.fetch_ohlcv(symbols=["FPT"])
            for w in res_vn.warnings:
                self.assertNotIn(token, w, f"Token '{token}' leaked in Vnstock warning: {w}")

            # 3. Label sanitizers
            self.assertEqual(safe_symbol_label(f"SYM_{token}"), "[INVALID_SYMBOL]")
            self.assertEqual(safe_date_label(f"2026_{token}"), "[INVALID_DATE]")


if __name__ == "__main__":
    unittest.main()
