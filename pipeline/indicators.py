"""Indicator calculations module for VN Stock Signal pipeline."""

from __future__ import annotations

from typing import Dict, List
from pipeline.models import IndicatorRecord, OHLCVRecord


def calculate_symbol_indicators(records: List[OHLCVRecord]) -> List[IndicatorRecord]:
    """Calculate rolling MA10, Distance %, and Avg Volume 20D for a single symbol's records.
    
    Records must be pre-sorted in ascending chronological order of trading_date.
    No forward-filling is applied.
    """
    results: List[IndicatorRecord] = []
    close_window: List[float] = []
    volume_window: List[int] = []

    for i, rec in enumerate(records):
        close_window.append(rec.close)
        volume_window.append(rec.volume)

        # MA10 is computed over the last 10 valid sessions
        ma10: float | None = None
        distance_pct: float | None = None
        if len(close_window) >= 10:
            window_10 = close_window[-10:]
            ma10 = sum(window_10) / 10.0
            distance_pct = ((rec.close - ma10) / ma10) * 100.0

        # Avg Volume 20D is computed over the last 20 valid sessions
        avg_vol_20d: float | None = None
        if len(volume_window) >= 20:
            window_20 = volume_window[-20:]
            avg_vol_20d = sum(window_20) / 20.0

        # Previous session references
        prev_close: float | None = records[i - 1].close if i > 0 else None
        prev_ma10: float | None = results[i - 1].ma10 if i > 0 else None

        indicator_rec = IndicatorRecord(
            trading_date=rec.trading_date,
            symbol=rec.symbol,
            exchange=rec.exchange,
            open=rec.open,
            high=rec.high,
            low=rec.low,
            close=rec.close,
            volume=rec.volume,
            in_vn30=rec.in_vn30,
            ma10=ma10,
            distance_pct=distance_pct,
            avg_volume_20d=avg_vol_20d,
            previous_close=prev_close,
            previous_ma10=prev_ma10,
        )
        results.append(indicator_rec)

    return results


def calculate_all_indicators(
    records: List[OHLCVRecord]
) -> Dict[str, List[IndicatorRecord]]:
    """Group OHLCV records by symbol and calculate indicators for each symbol."""
    by_symbol: Dict[str, List[OHLCVRecord]] = {}
    for rec in records:
        by_symbol.setdefault(rec.symbol, []).append(rec)

    indicators_by_symbol: Dict[str, List[IndicatorRecord]] = {}
    for symbol, sym_records in by_symbol.items():
        # Ensure chronological ordering
        sym_records.sort(key=lambda r: r.trading_date)
        indicators_by_symbol[symbol] = calculate_symbol_indicators(sym_records)

    return indicators_by_symbol
