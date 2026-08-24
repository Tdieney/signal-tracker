"""Validation and normalization module for VN Stock Signal pipeline."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Dict, List, Set, Tuple

from pipeline.models import OHLCVRecord, QualityInfo, QualityStatus


SYMBOL_PATTERN = re.compile(r"^[A-Z0-9]{1,10}$")
VALID_EXCHANGES = {"HOSE", "HNX", "UPCOM"}


class ValidationError(Exception):
    """Raised when data validation fails strictly."""
    pass


def validate_date(date_str: str) -> bool:
    """Validate YYYY-MM-DD format."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%Y-%m-%d") == date_str
    except (ValueError, TypeError):
        return False


def validate_record(record: OHLCVRecord) -> Tuple[bool, List[str]]:
    """Validate a single OHLCV record according to data contracts.
    
    Returns (is_valid, list_of_error_messages).
    """
    errors = []

    # Date check
    if not validate_date(record.trading_date):
        errors.append(f"Invalid trading_date format '{record.trading_date}', expected YYYY-MM-DD")

    # Symbol check
    if not isinstance(record.symbol, str) or not SYMBOL_PATTERN.match(record.symbol):
        errors.append(f"Invalid symbol '{record.symbol}', must match ^[A-Z0-9]{{1,10}}$")

    # Exchange check
    if record.exchange not in VALID_EXCHANGES:
        errors.append(f"Invalid exchange '{record.exchange}', must be one of {VALID_EXCHANGES}")

    # Price positivity checks
    for field_name, val in [
        ("open", record.open),
        ("high", record.high),
        ("low", record.low),
        ("close", record.close),
    ]:
        if not isinstance(val, (int, float)) or val <= 0:
            errors.append(f"Field '{field_name}' must be a positive number, got {val}")

    if record.adjusted_close is not None:
        if not isinstance(record.adjusted_close, (int, float)) or record.adjusted_close <= 0:
            errors.append(f"Field 'adjusted_close' must be positive if present, got {record.adjusted_close}")

    # Volume non-negativity
    if not isinstance(record.volume, int) or record.volume < 0:
        errors.append(f"Field 'volume' must be a non-negative integer, got {record.volume}")

    if record.trading_value is not None:
        if not isinstance(record.trading_value, (int, float)) or record.trading_value < 0:
            errors.append(f"Field 'trading_value' must be non-negative if present, got {record.trading_value}")

    # OHLC Invariants (only if prices are numbers)
    if all(isinstance(val, (int, float)) and val > 0 for val in [record.open, record.high, record.low, record.close]):
        max_price = max(record.open, record.close, record.low)
        min_price = min(record.open, record.close, record.high)
        if record.high < max_price:
            errors.append(f"OHLC invariant violated: high ({record.high}) < max(open, close, low) ({max_price})")
        if record.low > min_price:
            errors.append(f"OHLC invariant violated: low ({record.low}) > min(open, close, high) ({min_price})")

    return (len(errors) == 0, errors)


def validate_and_normalize_records(
    raw_records: List[OHLCVRecord],
    strict_duplicates: bool = True
) -> Tuple[List[OHLCVRecord], QualityInfo]:
    """Validate a collection of raw OHLCV records.
    
    Checks uniqueness of (symbol, trading_date) and filters invalid rows.
    Returns (accepted_records, quality_info).
    """
    seen_keys: Set[Tuple[str, str]] = set()
    accepted: List[OHLCVRecord] = []
    warnings: List[str] = []
    rejected_count = 0

    for idx, rec in enumerate(raw_records):
        key = (rec.symbol.upper(), rec.trading_date)
        if key in seen_keys:
            msg = f"Duplicate record for (symbol={key[0]}, date={key[1]}) at index {idx}"
            if strict_duplicates:
                raise ValidationError(msg)
            else:
                warnings.append(msg)
                rejected_count += 1
                continue

        is_valid, errors = validate_record(rec)
        if not is_valid:
            warnings.append(f"Rejected record (symbol={rec.symbol}, date={rec.trading_date}): {'; '.join(errors)}")
            rejected_count += 1
            continue

        seen_keys.add(key)
        # Normalize symbol uppercase
        rec.symbol = rec.symbol.upper()
        accepted.append(rec)

    # Sort ascending by symbol and date
    accepted.sort(key=lambda r: (r.symbol, r.trading_date))

    unique_symbols = len(set(r.symbol for r in accepted))
    quality_status = QualityStatus.PASS if rejected_count == 0 else (
        QualityStatus.PARTIAL if len(accepted) > 0 else QualityStatus.FAIL
    )

    quality_info = QualityInfo(
        status=quality_status,
        input_rows=len(raw_records),
        accepted_rows=len(accepted),
        rejected_rows=rejected_count,
        eligible_symbols=unique_symbols,
        warnings=warnings[:50],  # cap warnings
    )

    return accepted, quality_info
