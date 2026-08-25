"""Tests for pipeline validation, normalization, and dataset_id sensitivity."""

import unittest
from pipeline.build_dataset import compute_deterministic_dataset_id
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
        self.assertTrue(any("OHLC invariant" in e for e in errors1))

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
        self.assertTrue(any("OHLC invariant" in e for e in errors2))

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

    def test_dataset_id_sensitivity_to_all_public_fields(self):
        """Comprehensive parameterized test verifying dataset_id changes when ANY public-affecting field changes."""
        base_rec = OHLCVRecord(
            trading_date="2026-08-21",
            symbol="FPT",
            exchange="HOSE",
            open=100.0,
            high=105.0,
            low=98.0,
            close=102.5,
            adjusted_close=102.5,
            volume=1000,
            trading_value=102500.0,
            in_vn30=True,
        )
        base_id = compute_deterministic_dataset_id(
            as_of_date="2026-08-21",
            records=[base_rec],
            provider="csv",
            universe="ALL",
            quality_status="PASS",
            eligible_count=1,
            quality_metadata={"input_rows": 1, "accepted_rows": 1, "rejected_rows": 0, "warnings": []},
        )

        # 1. Record field mutations
        record_modifications = [
            ("symbol", OHLCVRecord("2026-08-21", "VIC", "HOSE", 100.0, 105.0, 98.0, 102.5, 102.5, 1000, 102500.0, True)),
            ("trading_date", OHLCVRecord("2026-08-20", "FPT", "HOSE", 100.0, 105.0, 98.0, 102.5, 102.5, 1000, 102500.0, True)),
            ("open", OHLCVRecord("2026-08-21", "FPT", "HOSE", 101.0, 105.0, 98.0, 102.5, 102.5, 1000, 102500.0, True)),
            ("high", OHLCVRecord("2026-08-21", "FPT", "HOSE", 100.0, 106.0, 98.0, 102.5, 102.5, 1000, 102500.0, True)),
            ("low", OHLCVRecord("2026-08-21", "FPT", "HOSE", 100.0, 105.0, 97.0, 102.5, 102.5, 1000, 102500.0, True)),
            ("close", OHLCVRecord("2026-08-21", "FPT", "HOSE", 100.0, 105.0, 98.0, 103.0, 102.5, 1000, 102500.0, True)),
            ("adjusted_close", OHLCVRecord("2026-08-21", "FPT", "HOSE", 100.0, 105.0, 98.0, 102.5, 100.0, 1000, 102500.0, True)),
            ("volume", OHLCVRecord("2026-08-21", "FPT", "HOSE", 100.0, 105.0, 98.0, 102.5, 102.5, 2000, 102500.0, True)),
            ("trading_value", OHLCVRecord("2026-08-21", "FPT", "HOSE", 100.0, 105.0, 98.0, 102.5, 102.5, 1000, 200000.0, True)),
            ("exchange", OHLCVRecord("2026-08-21", "FPT", "HNX", 100.0, 105.0, 98.0, 102.5, 102.5, 1000, 102500.0, True)),
            ("in_vn30", OHLCVRecord("2026-08-21", "FPT", "HOSE", 100.0, 105.0, 98.0, 102.5, 102.5, 1000, 102500.0, False)),
        ]

        for field_name, mod_rec in record_modifications:
            mod_id = compute_deterministic_dataset_id(
                as_of_date="2026-08-21",
                records=[mod_rec],
                provider="csv",
                universe="ALL",
                quality_status="PASS",
                eligible_count=1,
                quality_metadata={"input_rows": 1, "accepted_rows": 1, "rejected_rows": 0, "warnings": []},
            )
            self.assertNotEqual(base_id, mod_id, f"dataset_id failed to change when modifying record field '{field_name}'")

        # 2. Context parameter mutations
        self.assertNotEqual(base_id, compute_deterministic_dataset_id("2026-08-20", [base_rec], "csv", "ALL", "PASS", 1, {"input_rows": 1, "accepted_rows": 1, "rejected_rows": 0, "warnings": []}), "as_of_date")
        self.assertNotEqual(base_id, compute_deterministic_dataset_id("2026-08-21", [base_rec], "vnstock", "ALL", "PASS", 1, {"input_rows": 1, "accepted_rows": 1, "rejected_rows": 0, "warnings": []}), "provider")
        self.assertNotEqual(base_id, compute_deterministic_dataset_id("2026-08-21", [base_rec], "csv", "VN30", "PASS", 1, {"input_rows": 1, "accepted_rows": 1, "rejected_rows": 0, "warnings": []}), "universe")
        self.assertNotEqual(base_id, compute_deterministic_dataset_id("2026-08-21", [base_rec], "csv", "ALL", "PARTIAL", 1, {"input_rows": 1, "accepted_rows": 1, "rejected_rows": 0, "warnings": []}), "quality_status")
        self.assertNotEqual(base_id, compute_deterministic_dataset_id("2026-08-21", [base_rec], "csv", "ALL", "PASS", 2, {"input_rows": 1, "accepted_rows": 1, "rejected_rows": 0, "warnings": []}), "eligible_count")

        # 3. Quality metadata mutations (counters and warnings)
        self.assertNotEqual(base_id, compute_deterministic_dataset_id("2026-08-21", [base_rec], "csv", "ALL", "PASS", 1, {"input_rows": 2, "accepted_rows": 1, "rejected_rows": 1, "warnings": []}), "input_rows")
        self.assertNotEqual(base_id, compute_deterministic_dataset_id("2026-08-21", [base_rec], "csv", "ALL", "PASS", 1, {"input_rows": 1, "accepted_rows": 1, "rejected_rows": 0, "warnings": ["Sanitized warning"]}), "warnings")

    def test_symbol_contract_validity_and_normalization(self):
        """Test symbol contract: FPT, A1, VN30 valid, lowercase normalized, invalid chars rejected."""
        valid_symbols = ["FPT", "A1", "VN30", "fpt", "a1", "vn30", "ABC12345", "VIC"]
        for sym in valid_symbols:
            rec = OHLCVRecord("2026-08-21", sym, "HOSE", 100.0, 105.0, 98.0, 102.5, volume=1000)
            is_valid, errs = validate_record(rec)
            self.assertTrue(is_valid, f"Expected symbol '{sym}' to be valid, but got: {errs}")

        accepted, quality = validate_and_normalize_records([
            OHLCVRecord("2026-08-21", "fpt", "HOSE", 100.0, 105.0, 98.0, 102.5, volume=1000),
            OHLCVRecord("2026-08-21", "a1", "HOSE", 50.0, 52.0, 49.0, 51.0, volume=500),
            OHLCVRecord("2026-08-21", "vn30", "HOSE", 1200.0, 1210.0, 1195.0, 1205.0, volume=2000),
        ])
        self.assertEqual([r.symbol for r in accepted], ["A1", "FPT", "VN30"])

        invalid_symbols = ["FPT-VN", "ABC!", "@#$", "", "TOOLONGSYMBOL1234"]
        for sym in invalid_symbols:
            rec = OHLCVRecord("2026-08-21", sym, "HOSE", 100.0, 105.0, 98.0, 102.5, volume=1000)
            is_valid, errs = validate_record(rec)
            self.assertFalse(is_valid, f"Expected symbol '{sym}' to be invalid")

    def test_zero_leakage_in_validation_and_errors(self):
        """Test that validation warnings and ValidationError never contain raw symbols, dates, or record payloads."""
        adversarial_token = "SECRET_TOKEN_ABC12345"
        bad_rec = OHLCVRecord(
            trading_date=adversarial_token,
            symbol=adversarial_token,
            exchange="INVALID_EXCHANGE",
            open=-10.0,
            high=100.0,
            low=90.0,
            close=95.0,
            volume=-1,
        )

        accepted, quality = validate_and_normalize_records([bad_rec], strict_duplicates=False)
        self.assertEqual(len(accepted), 0)
        self.assertEqual(quality.rejected_rows, 1)
        for w in quality.warnings:
            self.assertNotIn(adversarial_token, w)
            self.assertIn("Row 1: record failed validation checks", w)

        # Duplicate rejection test
        rec1 = OHLCVRecord("2026-08-21", "FPT", "HOSE", 100.0, 105.0, 98.0, 102.5, volume=1000)
        rec2 = OHLCVRecord("2026-08-21", "FPT", "HOSE", 101.0, 106.0, 99.0, 103.0, volume=2000)
        try:
            validate_and_normalize_records([rec1, rec2], strict_duplicates=True)
            self.fail("Expected ValidationError on duplicate record")
        except ValidationError as ex:
            self.assertNotIn("FPT", str(ex))
            self.assertNotIn("2026-08-21", str(ex))
            self.assertEqual(str(ex), "Row 2: duplicate record rejected")


if __name__ == "__main__":
    unittest.main()
