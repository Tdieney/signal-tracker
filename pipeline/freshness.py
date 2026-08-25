"""Vietnam stock exchange trading calendar, market session detection, and freshness evaluation."""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from typing import Optional, Set

from pipeline.models import (
    FreshnessInfo,
    FreshnessStatus,
    MarketSessionStatus,
    MARKET_TIMEZONE,
)

# Standard VN timezone (Asia/Ho_Chi_Minh is UTC+7)
VN_TZ = timezone(timedelta(hours=7))

# Supported calendar boundaries and metadata
SUPPORTED_CALENDAR_YEAR_MIN = 2025
SUPPORTED_CALENDAR_YEAR_MAX = 2027
CALENDAR_VERSION = "2026.1-provisional"
CALENDAR_SOURCE = (
    "Provisional calendar definition (2025–2027) based on HOSE/HNX trading rules "
    "& Vietnam Labor Code statutory holidays; requires annual live regulatory synchronization"
)

# Standard VN public holidays (YYYY-MM-DD) for supported years (2025–2027)
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
    """Trading calendar engine for HOSE / HNX / UPCOM exchanges within supported year range."""

    def __init__(self, holidays: Optional[Set[str]] = None):
        self.holidays = holidays if holidays is not None else set(KNOWN_VIETNAM_HOLIDAYS)
        self.min_year = SUPPORTED_CALENDAR_YEAR_MIN
        self.max_year = SUPPORTED_CALENDAR_YEAR_MAX
        self.version = CALENDAR_VERSION
        self.source = CALENDAR_SOURCE

    def is_within_supported_range(self, date_str: str) -> bool:
        """Check if date_str falls within supported calendar years (2025-2027)."""
        try:
            year = int(date_str.split("-")[0])
            return self.min_year <= year <= self.max_year
        except (ValueError, IndexError):
            return False

    def is_trading_day(self, date_str: str) -> bool:
        """Return True if date_str (YYYY-MM-DD) is a Monday-Friday non-holiday trading day within supported years."""
        if not self.is_within_supported_range(date_str):
            # Fail closed outside supported range
            return False

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

    def get_latest_completed_trading_day(self, reference_dt: datetime) -> Optional[str]:
        """Return the date (YYYY-MM-DD) of the most recent completed trading session, or None if outside supported range."""
        local_dt = reference_dt.astimezone(VN_TZ) if reference_dt.tzinfo else reference_dt.replace(tzinfo=VN_TZ)

        cur_date = local_dt.date()
        cur_date_str = cur_date.strftime("%Y-%m-%d")

        if not self.is_within_supported_range(cur_date_str):
            return None

        # If today is a trading day and reference time >= 15:30, today's session is completed
        if self.is_trading_day(cur_date_str) and local_dt.time() >= SESSION_SETTLED_CONFIRMED_TIME:
            return cur_date_str

        # Otherwise look back day by day within supported range
        check_date = cur_date - timedelta(days=1)
        while check_date.year >= self.min_year:
            check_str = check_date.strftime("%Y-%m-%d")
            if self.is_trading_day(check_str):
                return check_str
            check_date -= timedelta(days=1)

        return None


def evaluate_market_session_status(
    as_of_date: str,
    reference_time: Optional[datetime] = None,
    is_live_provider: bool = False,
    is_complete: bool = False,
    calendar: Optional[VietnamTradingCalendar] = None,
) -> MarketSessionStatus:
    """Determine market session status according to strict completeness and provenance contracts."""
    if not is_live_provider or not is_complete:
        # Safe default for fixtures, demo builds, or incomplete data
        return MarketSessionStatus.UNKNOWN

    cal = calendar or VietnamTradingCalendar()
    if not cal.is_within_supported_range(as_of_date):
        return MarketSessionStatus.UNKNOWN

    ref_dt = reference_time or datetime.now(timezone.utc)
    local_now = ref_dt.astimezone(VN_TZ) if ref_dt.tzinfo else ref_dt.replace(tzinfo=VN_TZ)

    today_str = local_now.strftime("%Y-%m-%d")

    # If dataset as_of_date matches today, today is a trading day, and time is past 15:30
    if (
        as_of_date == today_str
        and cal.is_trading_day(today_str)
        and local_now.time() >= SESSION_SETTLED_CONFIRMED_TIME
    ):
        return MarketSessionStatus.CLOSED_CONFIRMED

    # If dataset matches the latest completed trading day
    latest_completed = cal.get_latest_completed_trading_day(local_now)
    if latest_completed and as_of_date == latest_completed:
        return MarketSessionStatus.CLOSED_CONFIRMED

    return MarketSessionStatus.UNKNOWN


def evaluate_dataset_freshness(
    as_of_date: str,
    reference_time: Optional[datetime] = None,
    is_live_provider: bool = False,
    is_complete: bool = False,
    calendar: Optional[VietnamTradingCalendar] = None,
) -> FreshnessInfo:
    """Evaluate whether the dataset is FRESH, STALE, or UNKNOWN with reference_time injection."""
    cal = calendar or VietnamTradingCalendar()
    ref_dt = reference_time or datetime.now(timezone.utc)
    expected_as_of = cal.get_latest_completed_trading_day(ref_dt) or as_of_date

    if not is_live_provider or not is_complete:
        return FreshnessInfo(
            status=FreshnessStatus.UNKNOWN,
            expected_as_of_date=expected_as_of,
            reason="Dữ liệu mẫu thử nghiệm (fixture/demo), không phải dữ liệu thị trường trực tiếp.",
        )

    if not cal.is_within_supported_range(as_of_date):
        return FreshnessInfo(
            status=FreshnessStatus.UNKNOWN,
            expected_as_of_date=expected_as_of,
            reason=f"Ngày dữ liệu {as_of_date} nằm ngoài phạm vi lịch giao dịch hỗ trợ ({cal.min_year}–{cal.max_year})",
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
