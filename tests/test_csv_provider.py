"""Tests for CSV data provider."""

import os
import unittest
from pipeline.providers.csv_provider import CsvDataProvider


class TestCsvProvider(unittest.TestCase):

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


if __name__ == "__main__":
    unittest.main()
