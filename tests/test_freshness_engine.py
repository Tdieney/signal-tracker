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
    """Test suite verifying Vietnam stock market calendar and freshness semantics."""

    def setUp(self):
        self.tz = timezone(timedelta(hours=7))
        self.cal = VietnamTradingCalendar(holidays={"2026-04-30", "2026-05-01", "2026-09-02"})

    def test_trading_calendar_weekdays_and_holidays(self):
        # 2026-08-21 is Friday (weekday) -> True
        self.assertTrue(self.cal.is_trading_day("2026-08-21"))
        # 2026-08-22 is Saturday -> False
        self.assertFalse(self.cal.is_trading_day("2026-08-22"))
        # 2026-08-23 is Sunday -> False
        self.assertFalse(self.cal.is_trading_day("2026-08-23"))
        # 2026-04-30 is a holiday -> False
        self.assertFalse(self.cal.is_trading_day("2026-04-30"))

    def test_latest_completed_trading_day_resolution(self):
        # On Friday 2026-08-21 at 16:00 (after 15:30 close) -> latest is 2026-08-21
        dt_friday_evening = datetime(2026, 8, 21, 16, 0, tzinfo=self.tz)
        self.assertEqual(self.cal.get_latest_completed_trading_day(dt_friday_evening), "2026-08-21")

        # On Friday 2026-08-21 at 10:00 (during session) -> latest completed is Thursday 2026-08-20
        dt_friday_morning = datetime(2026, 8, 21, 10, 0, tzinfo=self.tz)
        self.assertEqual(self.cal.get_latest_completed_trading_day(dt_friday_morning), "2026-08-20")

        # On Sunday 2026-08-23 -> latest completed is Friday 2026-08-21
        dt_sunday = datetime(2026, 8, 23, 12, 0, tzinfo=self.tz)
        self.assertEqual(self.cal.get_latest_completed_trading_day(dt_sunday), "2026-08-21")

    def test_evaluate_market_session_status(self):
        dt_friday_closed = datetime(2026, 8, 21, 16, 0, tzinfo=self.tz)

        # Demo/fixture provider always yields UNKNOWN (safe default)
        session_demo = evaluate_market_session_status(dt_friday_closed, "2026-08-21", is_live_provider=False, calendar=self.cal)
        self.assertEqual(session_demo, MarketSessionStatus.UNKNOWN)

        # Live provider after close on valid trading day yields CLOSED_CONFIRMED
        session_live = evaluate_market_session_status(dt_friday_closed, "2026-08-21", is_live_provider=True, calendar=self.cal)
        self.assertEqual(session_live, MarketSessionStatus.CLOSED_CONFIRMED)

    def test_evaluate_dataset_freshness(self):
        dt_now = datetime(2026, 8, 21, 16, 0, tzinfo=self.tz)

        # Demo fixture -> UNKNOWN
        freshness_demo = evaluate_dataset_freshness(dt_now, "2026-08-21", is_live_provider=False, calendar=self.cal)
        self.assertEqual(freshness_demo.status, FreshnessStatus.UNKNOWN)

        # Live fresh -> FRESH
        freshness_live_fresh = evaluate_dataset_freshness(dt_now, "2026-08-21", is_live_provider=True, calendar=self.cal)
        self.assertEqual(freshness_live_fresh.status, FreshnessStatus.FRESH)

        # Live stale -> STALE
        freshness_live_stale = evaluate_dataset_freshness(dt_now, "2026-08-15", is_live_provider=True, calendar=self.cal)
        self.assertEqual(freshness_live_stale.status, FreshnessStatus.STALE)


if __name__ == "__main__":
    unittest.main()
