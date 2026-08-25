"""Optional Vnstock data provider adapter for prototype research only."""

from __future__ import annotations

import logging
from typing import List, Optional, Sequence
from pipeline.models import OHLCVRecord
from pipeline.providers.base import DataProvider

logger = logging.getLogger("vn_stock_signal.vnstock_provider")


class VnstockDataProvider(DataProvider):
    """Adapter for vnstock python package to fetch OHLCV records.
    
    IMPORTANT: Experimental research stub only. Not supported for production dataset generation in Phase 1.
    """

    def __init__(self, rate_limit_delay_seconds: float = 0.5, max_retries: int = 2):
        self.rate_limit_delay_seconds = rate_limit_delay_seconds
        self.max_retries = max_retries

    def fetch_ohlcv(
        self,
        symbols: Optional[Sequence[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[OHLCVRecord]:
        """Fail closed for Phase 1 as live providers require validated calendar/session policies."""
        raise NotImplementedError(
            "VnstockDataProvider is an experimental research stub and is not supported for dataset generation in Phase 1. "
            "Use CsvDataProvider with validated fixture data."
        )
