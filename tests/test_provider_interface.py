"""Unit tests for BaseMarketDataProvider implementations, provider contracts, and adversarial secret containment."""

import json
import logging
import os
import shutil
import tempfile
import unittest
from typing import List

from pipeline.build_dataset import build_dataset_from_records
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
from pipeline.validation import validate_and_normalize_records


class LogCaptureHandler(logging.Handler):
    """Handler to reliably capture all log records for assertions."""
    def __init__(self):
        super().__init__()
        self.records: List[logging.LogRecord] = []

    def emit(self, record):
        self.records.append(record)


class TestProviderInterface(unittest.TestCase):
    """Test suite verifying market data providers adhere to provider-neutral contracts."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.log_handler = LogCaptureHandler()
        logging.getLogger().addHandler(self.log_handler)
        logging.getLogger("vn_stock_signal").setLevel(logging.DEBUG)

    def tearDown(self):
        logging.getLogger().removeHandler(self.log_handler)
        shutil.rmtree(self.test_dir, ignore_errors=True)

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
        """Adversarial test: exact raw tokens (1234-56-78, ABC12345, ghp_FAKE_TOKEN_123456789) injected verbatim NEVER leak."""
        test_tokens = [
            "1234-56-78",
            "ABC12345",
            "ghp_FAKE_TOKEN_123456789",
        ]

        for token in test_tokens:
            self.log_handler.records.clear()

            # 1. Test CSV Provider injection
            csv_path = os.path.join(self.test_dir, f"test_{token.replace('-', '_')}.csv")
            with open(csv_path, "w", encoding="utf-8") as f:
                f.write("trading_date,symbol,exchange,open,high,low,close,volume\n")
                f.write(f"{token},{token},HOSE,100,102,99,-1,1000\n")
                f.write(f"2026-08-21,FPT,HOSE,100,102,99,101,1000\n")

            csv_provider = CsvDataProvider(csv_path)
            res_csv = csv_provider.fetch_ohlcv()

            for w in res_csv.warnings:
                self.assertNotIn(token, w, f"Exact token '{token}' leaked in CSV warning: {w}")

            # 2. Test Company API Provider injection
            def malicious_company_fetch(url, key, sym, start, end):
                raise RuntimeError(f"Crashing with token {token} at {url}")

            provider_co = CompanyApiDataProvider(
                api_base_url=f"https://api.example.com/{token}",
                fetch_fn=malicious_company_fetch,
            )
            res_co = provider_co.fetch_ohlcv(symbols=[token])
            for w in res_co.warnings:
                self.assertNotIn(token, w, f"Exact token '{token}' leaked in CompanyApi warning: {w}")

            # 3. Test Vnstock Provider injection
            def bad_vnstock_fetch(sym, start, end):
                return [
                    {
                        "trading_date": token,
                        "symbol": token,
                        "open": -10.0,
                        "high": 100.0,
                        "low": 90.0,
                        "close": 95.0,
                        "volume": -100,
                    }
                ]

            provider_vn = VnstockDataProvider(fetch_fn=bad_vnstock_fetch)
            res_vn = provider_vn.fetch_ohlcv(symbols=[token])
            for w in res_vn.warnings:
                self.assertNotIn(token, w, f"Exact token '{token}' leaked in Vnstock warning: {w}")

            # 4. Direct pipeline validation and dataset build check:
            # Pass 1 valid FPT record, 1 invalid record with raw token in trading_date, and 1 duplicate record
            valid_rec = OHLCVRecord("2026-08-21", "FPT", "HOSE", 100.0, 102.0, 99.0, 101.0, volume=1000)
            bad_rec = OHLCVRecord(token, "FPT", "HOSE", 100.0, 102.0, 99.0, 101.0, volume=1000)
            dup_rec = OHLCVRecord("2026-08-21", "FPT", "HOSE", 100.0, 102.0, 99.0, 101.0, volume=1000)

            accepted_recs, quality_info = validate_and_normalize_records(
                [valid_rec, bad_rec, dup_rec],
                strict_duplicates=False,
            )
            self.assertEqual(len(accepted_recs), 1)
            for w in quality_info.warnings:
                self.assertNotIn(token, w, f"Exact token '{token}' leaked in QualityInfo warnings: {w}")

            # 5. Build Dataset serialization check: Assert adversarial token rejected and not in JSON bytes
            out_dataset_dir = os.path.join(self.test_dir, f"dataset_{token.replace('-', '_')}")
            build_dataset_from_records(
                records=accepted_recs,
                output_dir=out_dataset_dir,
                fixed_generated_at="2026-08-21T10:00:00Z",
                workspace_root=self.test_dir,
                parse_warnings=quality_info.warnings,
                parse_errors_count=quality_info.rejected_rows,
            )

            # Inspect captured log messages
            for log_rec in self.log_handler.records:
                msg = log_rec.getMessage()
                self.assertNotIn(token, msg, f"Exact token '{token}' leaked in captured log message: {msg}")

            # Inspect all output JSON files on disk
            for root, _, files in os.walk(out_dataset_dir):
                for fn in files:
                    full_fn = os.path.join(root, fn)
                    with open(full_fn, "rb") as fp:
                        json_bytes = fp.read()
                        self.assertNotIn(
                            token.encode("utf-8"),
                            json_bytes,
                            f"Exact token '{token}' leaked in serialized JSON artifact: {fn}",
                        )


if __name__ == "__main__":
    unittest.main()
