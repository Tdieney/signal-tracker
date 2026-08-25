"""Unit tests for VietnamTradingCalendar, market session detection, freshness evaluation, and dataset identity."""

from datetime import datetime, timedelta, timezone
import json
import os
import shutil
import tempfile
import unittest

from pipeline.build_dataset import (
    build_dataset_from_records,
    compute_deterministic_dataset_id,
)
from pipeline.freshness import (
    CALENDAR_VERSION,
    VietnamTradingCalendar,
    evaluate_dataset_freshness,
    evaluate_market_session_status,
)
from pipeline.models import FreshnessStatus, MarketSessionStatus, OHLCVRecord


class TestFreshnessEngine(unittest.TestCase):
    """Test suite verifying Vietnam stock market calendar, supported ranges, freshness semantics, and dataset identity."""

    def setUp(self):
        self.tz = timezone(timedelta(hours=7))
        self.cal = VietnamTradingCalendar(holidays={"2026-04-30", "2026-05-01", "2026-09-02"})
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_trading_calendar_supported_year_bounds(self):
        """Calendar strictly bounds to supported years 2025-2027 and fails closed outside."""
        # Supported range
        self.assertTrue(self.cal.is_within_supported_range("2025-01-02"))
        self.assertTrue(self.cal.is_within_supported_range("2026-06-15"))
        self.assertTrue(self.cal.is_within_supported_range("2027-12-31"))

        # Unsupported range (fail closed)
        self.assertFalse(self.cal.is_within_supported_range("2024-12-31"))
        self.assertFalse(self.cal.is_within_supported_range("2028-01-01"))
        self.assertFalse(self.cal.is_trading_day("2024-12-30"))
        self.assertFalse(self.cal.is_trading_day("2028-01-03"))

    def test_trading_calendar_weekdays_and_holidays(self):
        self.assertTrue(self.cal.is_trading_day("2026-08-21"))
        self.assertFalse(self.cal.is_trading_day("2026-08-22"))
        self.assertFalse(self.cal.is_trading_day("2026-08-23"))
        self.assertFalse(self.cal.is_trading_day("2026-04-30"))

    def test_pre_and_post_1530_market_session_boundary(self):
        """Regression test simulating before and after 15:30 on the exact same trading day."""
        dt_trading = datetime(2026, 8, 21, 14, 45, tzinfo=self.tz)
        status_trading = evaluate_market_session_status(
            as_of_date="2026-08-21",
            reference_time=dt_trading,
            is_live_provider=True,
            is_complete=True,
            calendar=self.cal,
        )
        self.assertEqual(status_trading, MarketSessionStatus.UNKNOWN)

        dt_closed = datetime(2026, 8, 21, 15, 35, tzinfo=self.tz)
        status_closed = evaluate_market_session_status(
            as_of_date="2026-08-21",
            reference_time=dt_closed,
            is_live_provider=True,
            is_complete=True,
            calendar=self.cal,
        )
        self.assertEqual(status_closed, MarketSessionStatus.CLOSED_CONFIRMED)

    def test_session_status_and_single_record_fpt_regression(self):
        """Regression test: Single FPT record or incomplete fixture yields UNKNOWN session and UNKNOWN freshness."""
        dt_closed = datetime(2026, 8, 21, 16, 0, tzinfo=self.tz)

        # Demo mode / single fixture -> UNKNOWN session & UNKNOWN freshness
        status_demo = evaluate_market_session_status(
            as_of_date="2026-08-21",
            reference_time=dt_closed,
            is_live_provider=False,
            is_complete=False,
            calendar=self.cal,
        )
        freshness_demo = evaluate_dataset_freshness(
            as_of_date="2026-08-21",
            reference_time=dt_closed,
            is_live_provider=False,
            is_complete=False,
            calendar=self.cal,
        )
        self.assertEqual(status_demo, MarketSessionStatus.UNKNOWN)
        self.assertEqual(freshness_demo.status, FreshnessStatus.UNKNOWN)

        # Live provider without full completeness confirmation -> UNKNOWN
        status_incomplete = evaluate_market_session_status(
            as_of_date="2026-08-21",
            reference_time=dt_closed,
            is_live_provider=True,
            is_complete=False,
            calendar=self.cal,
        )
        self.assertEqual(status_incomplete, MarketSessionStatus.UNKNOWN)

    def test_dataset_identity_sensitivity_to_expected_dates(self):
        """Two builds with different expected dates (e.g. 2026-08-25 vs 2026-08-26) MUST have different dataset_id."""
        records = [
            OHLCVRecord("2026-08-21", "FPT", "HOSE", 100.0, 102.0, 99.0, 101.0, None, 1000, None, True)
        ]

        id_day1 = compute_deterministic_dataset_id(
            as_of_date="2026-08-21",
            records=records,
            freshness_status="STALE",
            freshness_expected_as_of_date="2026-08-25",
        )
        id_day2 = compute_deterministic_dataset_id(
            as_of_date="2026-08-21",
            records=records,
            freshness_status="STALE",
            freshness_expected_as_of_date="2026-08-26",
        )

        self.assertNotEqual(id_day1, id_day2, "Dataset ID must differ when expected_as_of_date changes")

    def test_deterministic_build_reproducibility(self):
        """Fixed reference time build produces identical dataset_id across independent executions."""
        records = [
            OHLCVRecord("2026-08-21", "FPT", "HOSE", 100.0, 102.0, 99.0, 101.0, None, 1000, None, True)
        ]
        fixed_time = datetime(2026, 8, 25, 10, 0, 0, tzinfo=timezone.utc)

        out_dir_1 = os.path.join(self.test_dir, "out1")
        out_dir_2 = os.path.join(self.test_dir, "out2")

        id1 = build_dataset_from_records(
            records=records,
            output_dir=out_dir_1,
            fixed_generated_at="2026-08-25T10:00:00Z",
            reference_time=fixed_time,
            workspace_root=self.test_dir,
        )
        id2 = build_dataset_from_records(
            records=records,
            output_dir=out_dir_2,
            fixed_generated_at="2026-08-25T10:00:00Z",
            reference_time=fixed_time,
            workspace_root=self.test_dir,
        )

        self.assertEqual(id1, id2)

        # Byte-for-byte comparison of manifest.json
        with open(os.path.join(out_dir_1, "manifest.json"), "rb") as f1, open(os.path.join(out_dir_2, "manifest.json"), "rb") as f2:
            self.assertEqual(f1.read(), f2.read())


if __name__ == "__main__":
    unittest.main()
