"""Deterministic CSV data provider implementation with sanitized warning messages and precise row accounting."""

from __future__ import annotations

import csv
import hashlib
import os
from typing import List, Optional, Sequence
from pipeline.models import OHLCVRecord
from pipeline.providers.base import (
    BaseMarketDataProvider,
    ProviderFetchResult,
    ProviderHealth,
    safe_date_label,
    safe_symbol_label,
)
from pipeline.validation import validate_record


class CsvDataProvider(BaseMarketDataProvider):
    """Loads OHLCV records from a local CSV file deterministically without leaking raw payloads into warnings."""

    def __init__(self, csv_filepath: str):
        self.csv_filepath = csv_filepath
        self.source_rows_count = 0
        self.rejected_rows_count = 0
        self.parse_warnings: List[str] = []
        if not os.path.exists(csv_filepath):
            raise FileNotFoundError(f"CSV fixture file not found: {csv_filepath}")

    @property
    def provider_name(self) -> str:
        return "csv"

    def health_check(self) -> ProviderHealth:
        """Verify that the CSV fixture file exists and is readable."""
        if os.path.isfile(self.csv_filepath) and os.access(self.csv_filepath, os.R_OK):
            size_kb = os.path.getsize(self.csv_filepath) / 1024.0
            return ProviderHealth(
                is_healthy=True,
                provider_name=self.provider_name,
                message=f"CSV fixture file is readable ({size_kb:.1f} KB)",
                latency_ms=0.1,
            )
        return ProviderHealth(
            is_healthy=False,
            provider_name=self.provider_name,
            message="CSV fixture file is missing or not readable",
        )

    def fetch_ohlcv(
        self,
        symbols: Optional[Sequence[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> ProviderFetchResult:
        """Parse CSV file and return full ProviderFetchResult with quality accounting."""
        records: List[OHLCVRecord] = []
        symbol_set = set(s.upper() for s in symbols) if symbols else None
        self.source_rows_count = 0
        self.rejected_rows_count = 0
        self.parse_warnings = []
        sha = hashlib.sha256()

        with open(self.csv_filepath, mode="r", encoding="utf-8-sig") as f:
            content = f.read()
            sha.update(content.encode("utf-8"))
            f.seek(0)
            reader = csv.DictReader(f)
            for row_idx, row in enumerate(reader, start=2):
                if not row or not any(row.values()):
                    continue

                self.source_rows_count += 1

                # Normalize field names by lowercasing and stripping
                cleaned_row = {
                    k.strip().lower(): (v.strip() if v is not None else "")
                    for k, v in row.items()
                    if k is not None
                }

                raw_date = cleaned_row.get("trading_date") or cleaned_row.get("date") or ""
                raw_sym = cleaned_row.get("symbol") or cleaned_row.get("ticker") or ""
                ex = (cleaned_row.get("exchange") or "HOSE").upper()

                date_label = safe_date_label(raw_date)
                sym_label = safe_symbol_label(raw_sym)

                if symbol_set and sym_label not in symbol_set:
                    # Filtered out by caller symbol set
                    self.source_rows_count -= 1
                    continue
                if start_date and raw_date < start_date:
                    self.source_rows_count -= 1
                    continue
                if end_date and raw_date > end_date:
                    self.source_rows_count -= 1
                    continue

                try:
                    open_str = cleaned_row.get("open", "")
                    high_str = cleaned_row.get("high", "")
                    low_str = cleaned_row.get("low", "")
                    close_str = cleaned_row.get("close", "")
                    vol_str = cleaned_row.get("volume", "0")

                    if not (open_str and high_str and low_str and close_str):
                        self.rejected_rows_count += 1
                        self.parse_warnings.append(f"Row {row_idx}: Missing required OHLC price values")
                        continue

                    open_val = float(open_str)
                    high_val = float(high_str)
                    low_val = float(low_str)
                    close_val = float(close_str)
                    volume_val = int(float(vol_str)) if vol_str else 0
                except (ValueError, TypeError):
                    self.rejected_rows_count += 1
                    self.parse_warnings.append(f"Row {row_idx}: Non-numeric OHLC price or volume field")
                    continue

                adj_close_str = cleaned_row.get("adjusted_close") or cleaned_row.get("adj_close")
                adj_close = None
                if adj_close_str:
                    try:
                        adj_close = float(adj_close_str)
                    except (ValueError, TypeError):
                        self.parse_warnings.append(f"Row {row_idx}: Invalid optional adjusted_close field")

                val_str = cleaned_row.get("trading_value") or cleaned_row.get("value")
                trading_val = None
                if val_str:
                    try:
                        trading_val = float(val_str)
                    except (ValueError, TypeError):
                        self.parse_warnings.append(f"Row {row_idx}: Invalid optional trading_value field")

                vn30_str = cleaned_row.get("in_vn30", "").lower()
                in_vn30 = vn30_str in ("true", "1", "yes", "t")

                rec = OHLCVRecord(
                    trading_date=raw_date,
                    symbol=raw_sym.upper(),
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

                is_valid, val_errs = validate_record(rec)
                if not is_valid:
                    self.rejected_rows_count += 1
                    self.parse_warnings.append(f"Row {row_idx}: Record failed data validation checks")
                    continue

                records.append(rec)

        accepted_count = len(records)
        return ProviderFetchResult(
            records=records,
            provider_name=self.provider_name,
            input_rows=self.source_rows_count,
            accepted_rows=accepted_count,
            rejected_rows=self.rejected_rows_count,
            warnings=list(self.parse_warnings),
            payload_sha256=sha.hexdigest(),
            is_complete=False,
            provenance="fixture",
        )
