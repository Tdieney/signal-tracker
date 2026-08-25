"""Vietnam stock exchange trading calendar, market session detection, and freshness evaluation."""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from typing import List, Optional, Set

from pipeline.models import (
    FreshnessInfo,
    FreshnessStatus,
    MarketSessionStatus,
    MARKET_TIMEZONE,
)

# Standard VN timezone (Asia/Ho_Chi_Minh is UTC+7)
VN_TZ = timezone(timedelta(hours=7))

# Standard VN public holidays (YYYY-MM-DD) for current and adjacent years
KNOWN_VIETNAM_HOLIDAYS: Set[str] = {
    # 2025
    "2025-01-01", "2025-01-27", "2025-01-28", "2025-01-29", "2025-01-30", "2025-01-31",
    "2025-04-07", "2025-04-30", "2025-05-01", "2025-09-01", "2025-09-02",
    # 2026
    "2026-01-01", "2026-02-16", "2026-02-17", "2026-02-18", "2026-02-19", "2026-02-20",
    "2026-04-26", "2026-04-30", "2026-05-01", "2026-09-01", "2026-09-02",
    # 2027
    "2027-01-01", "2027-02-05", "2027-02-08", "2027-02-09", "2027-02-10", "2027-02-11",
    "2027-04-16", "2027-04-30", "2027-05-03", "2027-09-01", "2027-09-02",
}

# Market session time boundaries in Asia/Ho_Chi_Minh
SESSION_OPEN_TIME = time(9, 0)
SESSION_CLOSE_TIME = time(15, 0)
SESSION_SETTLED_CONFIRMED_TIME = time(15, 30)


class VietnamTradingCalendar:
    """Accurate trading calendar engine for HOSE / HNX / UPCOM exchanges."""

    def __init__(self, holidays: Optional[Set[str]] = None):
        self.holidays = holidays if holidays is not None else set(KNOWN_VIETNAM_HOLIDAYS)

    def is_trading_day(self, date_str: str) -> bool:
        """Return True if date_str (YYYY-MM-DD) is a Monday-Friday non-holiday trading day."""
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return False

        # 0 = Monday, 4 = Friday, 5 = Saturday, 6 = Sunday
        if dt.weekday() >= 5:
            return False

        if date_str in self.holidays:
            return False

        return True

    def get_latest_completed_trading_day(self, reference_dt: datetime) -> str:
        """Return the date (YYYY-MM-DD) of the most recent completed trading session."""
        local_dt = reference_dt.astimezone(VN_TZ) if reference_dt.tzinfo else reference_dt.replace(tzinfo=VN_TZ)

        cur_date = local_dt.date()
        cur_date_str = cur_date.strftime("%Y-%m-%d")

        # If today is a trading day and current time >= 15:30, today's session is completed
        if self.is_trading_day(cur_date_str) and local_dt.time() >= SESSION_SETTLED_CONFIRMED_TIME:
            return cur_date_str

        # Otherwise look back day by day
        check_date = cur_date - timedelta(days=1)
        while True:
            check_str = check_date.strftime("%Y-%m-%d")
            if self.is_trading_day(check_str):
                return check_str
            check_date -= timedelta(days=1)


def evaluate_market_session_status(
    now: datetime,
    as_of_date: str,
    is_live_provider: bool = False,
    calendar: Optional[VietnamTradingCalendar] = None,
) -> MarketSessionStatus:
    """Determine market session status according to strict data contract rules."""
    if not is_live_provider:
        # Safe default for fixtures/demo/offline builds
        return MarketSessionStatus.UNKNOWN

    cal = calendar or VietnamTradingCalendar()
    local_now = now.astimezone(VN_TZ) if now.tzinfo else now.replace(tzinfo=VN_TZ)

    today_str = local_now.strftime("%Y-%m-%d")

    # If dataset as_of_date matches today, and today is a trading day, and time is past 15:30
    if (
        as_of_date == today_str
        and cal.is_trading_day(today_str)
        and local_now.time() >= SESSION_SETTLED_CONFIRMED_TIME
    ):
        return MarketSessionStatus.CLOSED_CONFIRMED

    # If dataset matches the latest completed trading day
    latest_completed = cal.get_latest_completed_trading_day(local_now)
    if as_of_date == latest_completed:
        return MarketSessionStatus.CLOSED_CONFIRMED

    return MarketSessionStatus.UNKNOWN


def evaluate_dataset_freshness(
    now: datetime,
    as_of_date: str,
    is_live_provider: bool = False,
    calendar: Optional[VietnamTradingCalendar] = None,
) -> FreshnessInfo:
    """Evaluate whether the dataset is FRESH, STALE, or UNKNOWN."""
    cal = calendar or VietnamTradingCalendar()
    expected_as_of = cal.get_latest_completed_trading_day(now)

    if not is_live_provider:
        return FreshnessInfo(
            status=FreshnessStatus.UNKNOWN,
            expected_as_of_date=expected_as_of,
            reason="Dữ liệu mẫu thử nghiệm (fixture/demo), không phải dữ liệu thị trường trực tiếp.",
        )

    if as_of_date == expected_as_of:
        return FreshnessInfo(
            status=FreshnessStatus.FRESH,
            expected_as_of_date=expected_as_of,
            reason=f"Dữ liệu đã cập nhật đầy đủ cho phiên giao dịch gần nhất ({as_of_date})",
        )
    elif as_of_date < expected_as_of:
        return FreshnessInfo(
            status=FreshnessStatus.STALE,
            expected_as_of_date=expected_as_of,
            reason=f"Dữ liệu mới nhất hiện có là phiên {as_of_date}, chưa có dữ liệu phiên kỳ vọng {expected_as_of}",
        )
    else:
        # as_of_date > expected_as_of (future date or mock)
        return FreshnessInfo(
            status=FreshnessStatus.UNKNOWN,
            expected_as_of_date=expected_as_of,
            reason=f"Ngày dữ liệu {as_of_date} vượt quá phiên giao dịch chuẩn {expected_as_of}",
        )
