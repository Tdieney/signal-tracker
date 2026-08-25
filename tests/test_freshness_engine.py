"""Unit tests for VietnamTradingCalendar, market session detection, and freshness evaluation."""

from datetime import datetime, timedelta, timezone
import unittest

from pipeline.freshness import (
    VietnamTradingCalendar,
    evaluate_dataset_freshness,
    evaluate_market_session_status,
)
from pipeline.models import FreshnessStatus, MarketSessionStatus


class TestFreshnessEngine(unittest.TestCase):
    """Test suite verifying Vietnam stock market calendar, supported ranges, and freshness semantics."""

    def setUp(self):
        self.tz = timezone(timedelta(hours=7))
        self.cal = VietnamTradingCalendar(holidays={"2026-04-30", "2026-05-01", "2026-09-02"})

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
        # 2026-08-21 is Friday (weekday) -> True
        self.assertTrue(self.cal.is_trading_day("2026-08-21"))
        # 2026-08-22 is Saturday -> False
        self.assertFalse(self.cal.is_trading_day("2026-08-22"))
        # 2026-08-23 is Sunday -> False
        self.assertFalse(self.cal.is_trading_day("2026-08-23"))
        # 2026-04-30 is a holiday -> False
        self.assertFalse(self.cal.is_trading_day("2026-04-30"))

    def test_pre_and_post_1530_market_session_boundary(self):
        """Regression test simulating before and after 15:30 on the exact same trading day."""
        # Friday 2026-08-21 at 14:45 (market still trading)
        dt_trading = datetime(2026, 8, 21, 14, 45, tzinfo=self.tz)
        status_trading = evaluate_market_session_status(
            as_of_date="2026-08-21",
            reference_time=dt_trading,
            is_live_provider=True,
            has_complete_data=True,
            calendar=self.cal,
        )
        self.assertEqual(status_trading, MarketSessionStatus.UNKNOWN)

        # Friday 2026-08-21 at 15:35 (after 15:30 settlement)
        dt_closed = datetime(2026, 8, 21, 15, 35, tzinfo=self.tz)
        status_closed = evaluate_market_session_status(
            as_of_date="2026-08-21",
            reference_time=dt_closed,
            is_live_provider=True,
            has_complete_data=True,
            calendar=self.cal,
        )
        self.assertEqual(status_closed, MarketSessionStatus.CLOSED_CONFIRMED)

    def test_session_status_requires_data_completeness(self):
        """Even post 15:30, if has_complete_data=False or demo mode, status MUST be UNKNOWN."""
        dt_closed = datetime(2026, 8, 21, 16, 0, tzinfo=self.tz)

        # Demo mode -> UNKNOWN
        status_demo = evaluate_market_session_status(
            as_of_date="2026-08-21",
            reference_time=dt_closed,
            is_live_provider=False,
            has_complete_data=True,
            calendar=self.cal,
        )
        self.assertEqual(status_demo, MarketSessionStatus.UNKNOWN)

        # Incomplete data -> UNKNOWN
        status_incomplete = evaluate_market_session_status(
            as_of_date="2026-08-21",
            reference_time=dt_closed,
            is_live_provider=True,
            has_complete_data=False,
            calendar=self.cal,
        )
        self.assertEqual(status_incomplete, MarketSessionStatus.UNKNOWN)

    def test_evaluate_dataset_freshness(self):
        dt_now = datetime(2026, 8, 21, 16, 0, tzinfo=self.tz)

        # Demo fixture -> UNKNOWN
        freshness_demo = evaluate_dataset_freshness(
            as_of_date="2026-08-21",
            reference_time=dt_now,
            is_live_provider=False,
            calendar=self.cal,
        )
        self.assertEqual(freshness_demo.status, FreshnessStatus.UNKNOWN)

        # Live fresh -> FRESH
        freshness_live_fresh = evaluate_dataset_freshness(
            as_of_date="2026-08-21",
            reference_time=dt_now,
            is_live_provider=True,
            calendar=self.cal,
        )
        self.assertEqual(freshness_live_fresh.status, FreshnessStatus.FRESH)

        # Live stale -> STALE
        freshness_live_stale = evaluate_dataset_freshness(
            as_of_date="2026-08-15",
            reference_time=dt_now,
            is_live_provider=True,
            calendar=self.cal,
        )
        self.assertEqual(freshness_live_stale.status, FreshnessStatus.STALE)


if __name__ == "__main__":
    unittest.main()
