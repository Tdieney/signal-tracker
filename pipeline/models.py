"""Data models and type definitions for VN Stock Signal Phase 1 pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


SCHEMA_VERSION = "1.0.0"
MARKET_TIMEZONE = "Asia/Ho_Chi_Minh"


class SignalType(str, Enum):
    ABOVE_MA10 = "ABOVE_MA10"
    BELOW_MA10 = "BELOW_MA10"
    CROSS_UP_MA10 = "CROSS_UP_MA10"
    CROSS_DOWN_MA10 = "CROSS_DOWN_MA10"


class SignalReason(str, Enum):
    ABOVE_MA10 = "ABOVE_MA10"
    BELOW_MA10 = "BELOW_MA10"
    CROSS_UP_MA10 = "CROSS_UP_MA10"
    CROSS_DOWN_MA10 = "CROSS_DOWN_MA10"
    ON_MA10 = "ON_MA10"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class DataStatus(str, Enum):
    VALID = "VALID"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    NO_DATA_FOR_AS_OF_DATE = "NO_DATA_FOR_AS_OF_DATE"
    INVALID_DATA = "INVALID_DATA"


class MarketSessionStatus(str, Enum):
    CLOSED_CONFIRMED = "CLOSED_CONFIRMED"
    UNKNOWN = "UNKNOWN"


class FreshnessStatus(str, Enum):
    FRESH = "FRESH"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


class QualityStatus(str, Enum):
    PASS = "PASS"
    PARTIAL = "PARTIAL"
    FAIL = "FAIL"


class Exchange(str, Enum):
    HOSE = "HOSE"
    HNX = "HNX"
    UPCOM = "UPCOM"


@dataclass
class OHLCVRecord:
    trading_date: str  # YYYY-MM-DD
    symbol: str
    exchange: str
    open: float
    high: float
    low: float
    close: float
    adjusted_close: Optional[float] = None
    volume: int = 0
    trading_value: Optional[float] = None
    in_vn30: bool = False


@dataclass
class IndicatorRecord:
    trading_date: str
    symbol: str
    exchange: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    in_vn30: bool = False
    ma10: Optional[float] = None
    distance_pct: Optional[float] = None
    avg_volume_20d: Optional[float] = None
    signal: Optional[SignalType] = None
    signal_reason: Optional[str] = None
    data_status: DataStatus = DataStatus.VALID
    previous_close: Optional[float] = None
    previous_ma10: Optional[float] = None


@dataclass
class FreshnessInfo:
    status: FreshnessStatus
    expected_as_of_date: str
    reason: str


@dataclass
class QualityInfo:
    status: QualityStatus
    input_rows: int
    accepted_rows: int
    rejected_rows: int
    eligible_symbols: int
    warnings: List[str] = field(default_factory=list)


@dataclass
class ManifestData:
    schema_version: str
    dataset_id: str
    as_of_date: str
    generated_at: str
    market_timezone: str
    market_session_status: str
    freshness: FreshnessInfo
    provider: str
    universe: str
    files: Dict[str, str]
    quality: QualityInfo


@dataclass
class BreadthMetric:
    eligible_count: int
    above_count: int
    above_pct: Optional[float]
    below_count: int
    below_pct: Optional[float]
    on_ma10_count: int
    cross_up_count: int
    cross_down_count: int


@dataclass
class BreadthHistoryPoint:
    trading_date: str
    eligible_count: int
    above_count: int
    above_pct: Optional[float]


@dataclass
class OverviewData:
    schema_version: str
    dataset_id: str
    as_of_date: str
    metrics: BreadthMetric
    breadth_history: List[BreadthHistoryPoint]


@dataclass
class ScreenerItem:
    symbol: str
    exchange: str
    in_vn30: bool
    last_trading_date: Optional[str]
    close: Optional[float]
    ma10: Optional[float]
    distance_pct: Optional[float]
    volume: Optional[int]
    avg_volume_20d: Optional[float]
    signal: Optional[SignalType]
    signal_reason: Optional[str]
    data_status: DataStatus


@dataclass
class ScreenerData:
    schema_version: str
    dataset_id: str
    as_of_date: str
    items: List[ScreenerItem]


@dataclass
class SymbolSeriesPoint:
    trading_date: str
    open: float
    high: float
    low: float
    close: float
    ma10: Optional[float]
    volume: int
    signal: Optional[SignalType]


@dataclass
class SymbolExplanation:
    current_close: Optional[float]
    current_ma10: Optional[float]
    previous_close: Optional[float]
    previous_ma10: Optional[float]
    rule: Optional[str]


@dataclass
class SymbolLatest:
    close: Optional[float]
    ma10: Optional[float]
    distance_pct: Optional[float]
    signal: Optional[SignalType]
    data_status: DataStatus


@dataclass
class SymbolDetailData:
    schema_version: str
    dataset_id: str
    symbol: str
    exchange: str
    as_of_date: str
    latest: SymbolLatest
    series: List[SymbolSeriesPoint]
    explanation: SymbolExplanation
