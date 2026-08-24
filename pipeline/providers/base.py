"""Base DataProvider interface definition for VN Stock Signal pipeline."""

from __future__ import annotations

from typing import List, Protocol, Sequence
from pipeline.models import OHLCVRecord


class DataProvider(Protocol):
    """Protocol for fetching normalized stock OHLCV records."""

    def fetch_ohlcv(
        self,
        symbols: Sequence[str],
        start_date: str,
        end_date: str,
    ) -> List[OHLCVRecord]:
        """Fetch and return normalized OHLCV records for given symbols and date range."""
        ...
