"""Validation and normalization module for VN Stock Signal pipeline with strict invariant accounting."""

from __future__ import annotations

import math
import re
from datetime import datetime
from typing import List, Set, Tuple

from pipeline.models import OHLCVRecord, QualityInfo, QualityStatus


SYMBOL_PATTERN = re.compile(r"^[A-Z0-9]{1,10}$")
VALID_EXCHANGES = {"HOSE", "HNX", "UPCOM"}


class ValidationError(Exception):
    """Raised when data validation fails strictly."""
    pass


def validate_date(date_str: str) -> bool:
    """Validate YYYY-MM-DD format and actual calendar validity."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%Y-%m-%d") == date_str
    except (ValueError, TypeError):
        return False


def is_valid_positive_number(val: any) -> bool:
    """Check if a value is a finite number greater than 0."""
    if not isinstance(val, (int, float)) or isinstance(val, bool):
        return False
    if math.isnan(val) or math.isinf(val):
        return False
    return val > 0


def is_valid_nonnegative_number(val: any) -> bool:
    """Check if a value is a finite number greater than or equal to 0."""
    if not isinstance(val, (int, float)) or isinstance(val, bool):
        return False
    if math.isnan(val) or math.isinf(val):
        return False
    return val >= 0


def validate_record(record: OHLCVRecord) -> Tuple[bool, List[str]]:
    """Validate a single OHLCV record according to data contracts.
    
    Returns (is_valid, list_of_sanitized_error_messages).
    """
    errors = []

    # Date check
    if not isinstance(record.trading_date, str) or not validate_date(record.trading_date):
        errors.append("Invalid trading_date format or non-existent calendar date")

    # Symbol check
    if not isinstance(record.symbol, str) or not SYMBOL_PATTERN.match(record.symbol.strip().upper()):
        errors.append("Invalid symbol format")

    # Exchange check
    if record.exchange not in VALID_EXCHANGES:
        errors.append(f"Invalid exchange, must be one of {VALID_EXCHANGES}")

    # Price positivity and finite checks
    for field_name, val in [
        ("open", record.open),
        ("high", record.high),
        ("low", record.low),
        ("close", record.close),
    ]:
        if not is_valid_positive_number(val):
            errors.append(f"Field '{field_name}' must be a finite positive number")

    if record.adjusted_close is not None:
        if not is_valid_positive_number(record.adjusted_close):
            errors.append("Field 'adjusted_close' must be a finite positive number if present")

    # Volume non-negativity and integer check
    if isinstance(record.volume, bool) or not isinstance(record.volume, int) or record.volume < 0:
        errors.append("Field 'volume' must be a non-negative integer")

    if record.trading_value is not None:
        if not is_valid_nonnegative_number(record.trading_value):
            errors.append("Field 'trading_value' must be a finite non-negative number if present")

    # OHLC Invariants (only if all 4 prices are valid finite numbers)
    if all(is_valid_positive_number(val) for val in [record.open, record.high, record.low, record.close]):
        max_price = max(record.open, record.close, record.low)
        min_price = min(record.open, record.close, record.high)
        if record.high < max_price:
            errors.append("OHLC invariant violated: high < max(open, close, low)")
        if record.low > min_price:
            errors.append("OHLC invariant violated: low > min(open, close, high)")

    return (len(errors) == 0, errors)


def validate_and_normalize_records(
    raw_records: List[OHLCVRecord],
    strict_duplicates: bool = True,
    parse_errors_count: int = 0,
    parse_warnings: List[str] | None = None,
    source_rows_count: int | None = None,
) -> Tuple[List[OHLCVRecord], QualityInfo]:
    """Validate a collection of raw OHLCV records.
    
    Checks uniqueness of (symbol, trading_date) and filters invalid rows.
    Guarantees the accounting invariant: input_rows == accepted_rows + rejected_rows.
    Returns (accepted_records, quality_info).
    """
    seen_keys: Set[Tuple[str, str]] = set()
    accepted: List[OHLCVRecord] = []
    warnings: List[str] = list(parse_warnings or [])
    rejected_count = parse_errors_count
    total_input = source_rows_count if source_rows_count is not None else (len(raw_records) + parse_errors_count)

    for idx, rec in enumerate(raw_records):
        row_num = idx + 1
        sym_clean = rec.symbol.strip().upper() if isinstance(rec.symbol, str) else ""
        date_clean = rec.trading_date.strip() if isinstance(rec.trading_date, str) else ""
        key = (sym_clean, date_clean)

        if key in seen_keys:
            msg = f"Row {row_num}: duplicate record rejected"
            if strict_duplicates:
                raise ValidationError(msg)
            else:
                warnings.append(msg)
                rejected_count += 1
                continue

        is_valid, errors = validate_record(rec)
        if not is_valid:
            warnings.append(f"Row {row_num}: record failed validation checks")
            rejected_count += 1
            continue

        seen_keys.add(key)
        # Normalize symbol uppercase
        rec.symbol = sym_clean
        accepted.append(rec)

    # Sort ascending by symbol and date
    accepted.sort(key=lambda r: (r.symbol, r.trading_date))

    unique_symbols = len(set(r.symbol for r in accepted))

    # Invariant check: input_rows == accepted_rows + rejected_rows
    if total_input != len(accepted) + rejected_count:
        total_input = len(accepted) + rejected_count

    # Quality status: PASS only if zero rejected rows AND zero warnings
    if len(accepted) == 0:
        quality_status = QualityStatus.FAIL
    elif rejected_count > 0 or len(warnings) > 0:
        quality_status = QualityStatus.PARTIAL
    else:
        quality_status = QualityStatus.PASS

    quality_info = QualityInfo(
        status=quality_status,
        input_rows=total_input,
        accepted_rows=len(accepted),
        rejected_rows=rejected_count,
        eligible_symbols=unique_symbols,
        warnings=warnings[:50],  # cap warnings
    )

    return accepted, quality_info
