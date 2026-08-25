"""Base Market Data Provider interface and result abstractions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Sequence
from pipeline.models import OHLCVRecord


@dataclass
class ProviderFetchResult:
    """Standardized result returned by all market data providers."""
    records: List[OHLCVRecord]
    provider_name: str
    input_rows: int
    accepted_rows: int
    rejected_rows: int
    warnings: List[str] = field(default_factory=list)
    payload_sha256: Optional[str] = None

    def __post_init__(self):
        if self.input_rows != self.accepted_rows + self.rejected_rows:
            raise ValueError(
                f"Provider row accounting invariant violated: "
                f"input_rows ({self.input_rows}) != accepted_rows ({self.accepted_rows}) + rejected_rows ({self.rejected_rows})"
            )


@dataclass
class ProviderHealth:
    """Health check outcome for a market data provider."""
    is_healthy: bool
    provider_name: str
    message: str
    latency_ms: Optional[float] = None


class BaseMarketDataProvider(ABC):
    """Abstract base class for all market data provider adapters."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique provider identifier (e.g. 'csv', 'vnstock', 'company_api')."""
        ...

    @abstractmethod
    def fetch_ohlcv(
        self,
        symbols: Optional[Sequence[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> ProviderFetchResult:
        """Fetch and return validated OHLCV records with full quality accounting in ProviderFetchResult."""
        ...

    def fetch_records(
        self,
        symbols: Optional[Sequence[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[OHLCVRecord]:
        """Convenience method returning the raw list of validated OHLCVRecord objects."""
        return self.fetch_ohlcv(symbols=symbols, start_date=start_date, end_date=end_date).records

    @abstractmethod
    def health_check(self) -> ProviderHealth:
        """Perform a liveness and health probe without mutating state."""
        ...


# Protocol alias for backward compatibility
DataProvider = BaseMarketDataProvider
