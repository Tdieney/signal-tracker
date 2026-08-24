"""Optional Vnstock data provider adapter for prototype data retrieval."""

from __future__ import annotations

import logging
import time
from typing import List, Optional, Sequence
from pipeline.models import OHLCVRecord
from pipeline.providers.base import DataProvider


logger = logging.getLogger("vn_stock_signal.vnstock_provider")


class VnstockDataProvider(DataProvider):
    """Adapter for vnstock python package to fetch OHLCV records.
    
    NOTE: For personal research/prototype use only. Not for redistribution or commercial use.
    """

    def __init__(self, rate_limit_delay_seconds: float = 0.5, max_retries: int = 2):
        self.rate_limit_delay_seconds = rate_limit_delay_seconds
        self.max_retries = max_retries
        self._check_package()

    def _check_package(self) -> None:
        try:
            import vnstock  # noqa: F401
        except ImportError:
            logger.warning(
                "vnstock package is not installed. VnstockDataProvider will only work if vnstock is available."
            )

    def fetch_ohlcv(
        self,
        symbols: Optional[Sequence[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[OHLCVRecord]:
        """Fetch OHLCV dataframe from vnstock and map to normalized OHLCVRecord list."""
        try:
            from vnstock import stock_historical_data
        except ImportError as e:
            raise RuntimeError(
                "vnstock package is required to use VnstockDataProvider. Install via `pip install vnstock`."
            ) from e

        records: List[OHLCVRecord] = []
        target_symbols = symbols if symbols else ["FPT", "VNM", "HPG", "VCB", "SSI", "MWG", "VIC", "TCB"]

        for sym in target_symbols:
            clean_sym = sym.upper()
            attempts = 0
            success = False

            while attempts < self.max_retries and not success:
                attempts += 1
                try:
                    time.sleep(self.rate_limit_delay_seconds)
                    # Fetch from vnstock
                    df = stock_historical_data(
                        clean_sym,
                        start_date=start_date or "2026-01-01",
                        end_date=end_date or "2026-08-21",
                        resolution="1D",
                        type="stock",
                        beautify=True,
                    )

                    if df is not None and not df.empty:
                        for _, row in df.iterrows():
                            # Extract normalized fields safely
                            date_str = str(row.get("time") or row.get("trading_date") or "")[:10]
                            open_p = float(row.get("open", 0))
                            high_p = float(row.get("high", 0))
                            low_p = float(row.get("low", 0))
                            close_p = float(row.get("close", 0))
                            vol = int(float(row.get("volume", 0)))

                            rec = OHLCVRecord(
                                trading_date=date_str,
                                symbol=clean_sym,
                                exchange="HOSE",  # Fallback
                                open=open_p,
                                high=high_p,
                                low=low_p,
                                close=close_p,
                                adjusted_close=close_p,
                                volume=vol,
                            )
                            records.append(rec)
                        success = True
                except Exception as ex:
                    # Sanitize log output to avoid sensitive dumps
                    logger.warning(f"Error fetching data for symbol {clean_sym} on attempt {attempts}: {type(ex).__name__}")
                    if attempts >= self.max_retries:
                        logger.error(f"Failed to fetch data for symbol {clean_sym} after {self.max_retries} attempts.")

        return records
