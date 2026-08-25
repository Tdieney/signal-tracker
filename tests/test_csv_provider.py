"""Tests for CSV data provider, strict quality row accounting, and sanitized warnings."""

import os
import shutil
import tempfile
import unittest

from pipeline.models import QualityStatus
from pipeline.providers.csv_provider import CsvDataProvider
from pipeline.validation import validate_and_normalize_records


class TestCsvProvider(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_csv_prov_")

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_fetch_sample_fixture(self):
        fixture_path = "tests/fixtures/sample_ohlcv.csv"
        self.assertTrue(os.path.exists(fixture_path))

        provider = CsvDataProvider(fixture_path)
        records = provider.fetch_ohlcv()
        self.assertGreater(len(records), 0)

        # Filter by symbol
        fpt_records = provider.fetch_ohlcv(symbols=["FPT"])
        self.assertTrue(all(r.symbol == "FPT" for r in fpt_records))
        self.assertGreater(len(fpt_records), 0)

        # Filter by date range
        date_records = provider.fetch_ohlcv(start_date="2026-08-01", end_date="2026-08-15")
        self.assertTrue(all("2026-08-01" <= r.trading_date <= "2026-08-15" for r in date_records))

    def test_optional_field_warnings_accounting_and_partial_status(self):
        """Test: 1 physical row with 2 optional-field warnings results in input_rows=1, accepted_rows=1, rejected_rows=0, status=PARTIAL."""
        csv_content = (
            "trading_date,symbol,exchange,open,high,low,close,volume,adjusted_close,trading_value,in_vn30\n"
            "2026-08-21,FPT,HOSE,100.0,105.0,98.0,102.5,1000,INVALID_ADJ,INVALID_VAL,true\n"
        )
        csv_file = os.path.join(self.temp_dir, "test_optional_warns.csv")
        with open(csv_file, "w", encoding="utf-8") as f:
            f.write(csv_content)

        provider = CsvDataProvider(csv_file)
        records = provider.fetch_ohlcv()

        self.assertEqual(provider.source_rows_count, 1)
        self.assertEqual(provider.rejected_rows_count, 0)
        self.assertEqual(len(records), 1)
        self.assertEqual(len(provider.parse_warnings), 2)

        accepted, quality = validate_and_normalize_records(
            records,
            strict_duplicates=False,
            parse_errors_count=provider.rejected_rows_count,
            parse_warnings=provider.parse_warnings,
            source_rows_count=provider.source_rows_count,
        )

        self.assertEqual(quality.input_rows, 1)
        self.assertEqual(quality.accepted_rows, 1)
        self.assertEqual(quality.rejected_rows, 0)
        self.assertEqual(quality.input_rows, quality.accepted_rows + quality.rejected_rows)
        self.assertEqual(quality.status, QualityStatus.PARTIAL)

    def test_required_field_invalid_accounting_and_invariants(self):
        """Test: 1 required-field-invalid row increments rejected_rows by 1 and preserves invariant."""
        csv_content = (
            "trading_date,symbol,exchange,open,high,low,close,volume,adjusted_close,trading_value,in_vn30\n"
            "2026-08-21,FPT,HOSE,100.0,105.0,98.0,102.5,1000,102.5,100000,true\n"
            "2026-08-21,VIC,HOSE,NOT_A_PRICE,55.0,48.0,50.0,2000,50.0,100000,true\n"
        )
        csv_file = os.path.join(self.temp_dir, "test_required_invalid.csv")
        with open(csv_file, "w", encoding="utf-8") as f:
            f.write(csv_content)

        provider = CsvDataProvider(csv_file)
        records = provider.fetch_ohlcv()

        self.assertEqual(provider.source_rows_count, 2)
        self.assertEqual(provider.rejected_rows_count, 1)
        self.assertEqual(len(records), 1)

        accepted, quality = validate_and_normalize_records(
            records,
            strict_duplicates=False,
            parse_errors_count=provider.rejected_rows_count,
            parse_warnings=provider.parse_warnings,
            source_rows_count=provider.source_rows_count,
        )

        self.assertEqual(quality.input_rows, 2)
        self.assertEqual(quality.accepted_rows, 1)
        self.assertEqual(quality.rejected_rows, 1)
        self.assertEqual(quality.input_rows, quality.accepted_rows + quality.rejected_rows)
        self.assertEqual(quality.status, QualityStatus.PARTIAL)

    def test_csv_parser_sanitizes_raw_secrets_and_bad_values(self):
        """Test that raw secret tokens or unparsed values never leak into public parse warnings."""
        raw_secret = "RAW_SECRET_KEY_AIzaSyD12345678"
        bad_value = "BAD_RAW_INJECTED_VALUE_999"

        csv_content = (
            "trading_date,symbol,exchange,open,high,low,close,volume,adjusted_close,trading_value,in_vn30\n"
            f"2026-08-21,FPT,HOSE,100.0,102.0,99.0,101.0,1000,101.0,100000,true\n"
            f"2026-08-21,VIC,HOSE,50.0,{raw_secret},49.0,51.0,2000,51.0,100000,true\n"
            f"2026-08-21,VNM,HOSE,80.0,82.0,79.0,81.0,1500,{bad_value},120000,true\n"
        )
        csv_file = os.path.join(self.temp_dir, "test_secret_leak.csv")
        with open(csv_file, "w", encoding="utf-8") as f:
            f.write(csv_content)

        provider = CsvDataProvider(csv_file)
        records = provider.fetch_ohlcv()

        self.assertEqual(provider.rejected_rows_count, 1)
        self.assertEqual(len(provider.parse_warnings), 2)

        for w in provider.parse_warnings:
            self.assertNotIn(raw_secret, w)
            self.assertNotIn(bad_value, w)

        accepted, quality_info = validate_and_normalize_records(
            records,
            strict_duplicates=False,
            parse_errors_count=provider.rejected_rows_count,
            parse_warnings=provider.parse_warnings,
            source_rows_count=provider.source_rows_count,
        )
        self.assertEqual(quality_info.status, QualityStatus.PARTIAL)
        self.assertEqual(quality_info.rejected_rows, 1)
        self.assertEqual(quality_info.accepted_rows, 2)
        self.assertEqual(quality_info.input_rows, 3)


if __name__ == "__main__":
    unittest.main()
