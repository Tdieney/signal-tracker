"""Tests for pipeline validation and normalization."""

import unittest
from pipeline.models import OHLCVRecord, QualityStatus
from pipeline.validation import (
    ValidationError,
    validate_and_normalize_records,
    validate_date,
    validate_record,
)


class TestValidation(unittest.TestCase):

    def test_validate_date(self):
        self.assertTrue(validate_date("2026-08-21"))
        self.assertFalse(validate_date("2026-8-21"))
        self.assertFalse(validate_date("21-08-2026"))
        self.assertFalse(validate_date("2026-02-30"))
        self.assertFalse(validate_date(""))

    def test_validate_valid_record(self):
        rec = OHLCVRecord(
            trading_date="2026-08-21",
            symbol="FPT",
            exchange="HOSE",
            open=100.0,
            high=105.0,
            low=98.0,
            close=102.5,
            volume=1500000,
        )
        is_valid, errors = validate_record(rec)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_invalid_ohlc_invariants(self):
        # High lower than close
        rec1 = OHLCVRecord(
            trading_date="2026-08-21",
            symbol="FPT",
            exchange="HOSE",
            open=100.0,
            high=101.0,
            low=98.0,
            close=102.5,
            volume=1000,
        )
        is_valid1, errors1 = validate_record(rec1)
        self.assertFalse(is_valid1)
        self.assertTrue(any("high" in e for e in errors1))

        # Low higher than open
        rec2 = OHLCVRecord(
            trading_date="2026-08-21",
            symbol="FPT",
            exchange="HOSE",
            open=100.0,
            high=105.0,
            low=101.0,
            close=102.5,
            volume=1000,
        )
        is_valid2, errors2 = validate_record(rec2)
        self.assertFalse(is_valid2)
        self.assertTrue(any("low" in e for e in errors2))

    def test_validate_invalid_symbol_and_exchange(self):
        rec = OHLCVRecord(
            trading_date="2026-08-21",
            symbol="fpt-invalid!",
            exchange="NASDAQ",
            open=10.0,
            high=12.0,
            low=9.0,
            close=11.0,
            volume=100,
        )
        is_valid, errors = validate_record(rec)
        self.assertFalse(is_valid)
        self.assertTrue(any("symbol" in e for e in errors))
        self.assertTrue(any("exchange" in e for e in errors))

    def test_strict_duplicate_rejection(self):
        rec1 = OHLCVRecord(
            trading_date="2026-08-21",
            symbol="FPT",
            exchange="HOSE",
            open=100.0,
            high=105.0,
            low=98.0,
            close=102.5,
            volume=1000,
        )
        rec2 = OHLCVRecord(
            trading_date="2026-08-21",
            symbol="FPT",
            exchange="HOSE",
            open=101.0,
            high=106.0,
            low=99.0,
            close=103.0,
            volume=2000,
        )
        with self.assertRaises(ValidationError):
            validate_and_normalize_records([rec1, rec2], strict_duplicates=True)


if __name__ == "__main__":
    unittest.main()
