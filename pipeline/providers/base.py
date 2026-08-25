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
        """Fetch and return validated OHLCV records with full quality accounting."""
        ...

    @abstractmethod
    def health_check(self) -> ProviderHealth:
        """Perform a liveness and health probe without mutating state."""
        ...


# Protocol alias for backward compatibility
DataProvider = BaseMarketDataProvider
