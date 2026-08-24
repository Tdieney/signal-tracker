"""Deterministic CSV data provider implementation."""

from __future__ import annotations

import csv
import os
from typing import List, Optional, Sequence
from pipeline.models import OHLCVRecord
from pipeline.providers.base import DataProvider


class CsvDataProvider(DataProvider):
    """Loads OHLCV records from a local CSV file deterministically."""

    def __init__(self, csv_filepath: str):
        self.csv_filepath = csv_filepath
        if not os.path.exists(csv_filepath):
            raise FileNotFoundError(f"CSV fixture file not found: {csv_filepath}")

    def fetch_ohlcv(
        self,
        symbols: Optional[Sequence[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[OHLCVRecord]:
        """Parse CSV file and return OHLCVRecord list filtered by symbols and date range."""
        records: List[OHLCVRecord] = []
        symbol_set = set(s.upper() for s in symbols) if symbols else None

        with open(self.csv_filepath, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Normalize field names by lowercasing and stripping
                cleaned_row = {k.strip().lower(): (v.strip() if v is not None else "") for k, v in row.items() if k}

                date_str = cleaned_row.get("trading_date") or cleaned_row.get("date") or ""
                sym = (cleaned_row.get("symbol") or cleaned_row.get("ticker") or "").upper()
                ex = (cleaned_row.get("exchange") or "HOSE").upper()

                if symbol_set and sym not in symbol_set:
                    continue
                if start_date and date_str < start_date:
                    continue
                if end_date and date_str > end_date:
                    continue

                try:
                    open_val = float(cleaned_row.get("open", 0))
                    high_val = float(cleaned_row.get("high", 0))
                    low_val = float(cleaned_row.get("low", 0))
                    close_val = float(cleaned_row.get("close", 0))
                    vol_str = cleaned_row.get("volume", "0")
                    volume_val = int(float(vol_str)) if vol_str else 0
                except (ValueError, TypeError):
                    continue

                adj_close_str = cleaned_row.get("adjusted_close") or cleaned_row.get("adj_close")
                adj_close = float(adj_close_str) if adj_close_str else None

                val_str = cleaned_row.get("trading_value") or cleaned_row.get("value")
                trading_val = float(val_str) if val_str else None

                vn30_str = cleaned_row.get("in_vn30", "").lower()
                in_vn30 = vn30_str in ("true", "1", "yes", "t")

                rec = OHLCVRecord(
                    trading_date=date_str,
                    symbol=sym,
                    exchange=ex,
                    open=open_val,
                    high=high_val,
                    low=low_val,
                    close=close_val,
                    adjusted_close=adj_close,
                    volume=volume_val,
                    trading_value=trading_val,
                    in_vn30=in_vn30,
                )
                records.append(rec)

        return records
