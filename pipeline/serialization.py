"""Serialization and staging output builder for VN Stock Signal pipeline."""

from __future__ import annotations

import json
import math
import os
import shutil
from typing import Any, Dict, List, Optional
from pipeline.models import (
    MARKET_TIMEZONE,
    SCHEMA_VERSION,
    DataStatus,
    FreshnessInfo,
    FreshnessStatus,
    IndicatorRecord,
    ManifestData,
    MarketSessionStatus,
    OverviewData,
    QualityInfo,
    ScreenerData,
    ScreenerItem,
    SignalReason,
    SymbolDetailData,
    SymbolExplanation,
    SymbolLatest,
    SymbolSeriesPoint,
)


def sanitize_value(val: Any) -> Any:
    """Ensure no NaN or Infinity enters serialized JSON."""
    if val is None:
        return None
    if isinstance(val, float):
        if math.isnan(val) or math.isinf(val):
            return None
        return round(val, 4)
    if isinstance(val, list):
        return [sanitize_value(v) for v in val]
    if isinstance(val, dict):
        return {k: sanitize_value(v) for k, v in val.items()}
    return val


def round_float(val: Optional[float], decimals: int = 2) -> Optional[float]:
    """Round float cleanly, returning None if val is None or invalid."""
    if val is None or math.isnan(val) or math.isinf(val):
        return None
    return round(val, decimals)


def build_screener_item(
    symbol: str,
    records: List[IndicatorRecord],
    as_of_date: str,
    exchange_fallback: str = "HOSE",
    in_vn30_fallback: bool = False
) -> ScreenerItem:
    """Build a ScreenerItem for a symbol as of as_of_date."""
    # Find record matching as_of_date, or latest available record prior to as_of_date
    matching = [r for r in records if r.trading_date == as_of_date]
    prior = [r for r in records if r.trading_date <= as_of_date]
    
    if matching:
        rec = matching[0]
        return ScreenerItem(
            symbol=rec.symbol,
            exchange=rec.exchange,
            in_vn30=rec.in_vn30,
            last_trading_date=rec.trading_date,
            close=round_float(rec.close, 2),
            ma10=round_float(rec.ma10, 2),
            distance_pct=round_float(rec.distance_pct, 2),
            volume=rec.volume,
            avg_volume_20d=round_float(rec.avg_volume_20d, 0),
            signal=rec.signal,
            signal_reason=rec.signal_reason,
            data_status=rec.data_status,
        )
    elif prior:
        latest_prior = prior[-1]
        return ScreenerItem(
            symbol=symbol,
            exchange=latest_prior.exchange,
            in_vn30=latest_prior.in_vn30,
            last_trading_date=latest_prior.trading_date,
            close=None,
            ma10=None,
            distance_pct=None,
            volume=None,
            avg_volume_20d=None,
            signal=None,
            signal_reason=None,
            data_status=DataStatus.NO_DATA_FOR_AS_OF_DATE,
        )
    else:
        return ScreenerItem(
            symbol=symbol,
            exchange=exchange_fallback,
            in_vn30=in_vn30_fallback,
            last_trading_date=None,
            close=None,
            ma10=None,
            distance_pct=None,
            volume=None,
            avg_volume_20d=None,
            signal=None,
            signal_reason=None,
            data_status=DataStatus.NO_DATA_FOR_AS_OF_DATE,
        )


def build_symbol_detail(
    symbol: str,
    records: List[IndicatorRecord],
    dataset_id: str,
    as_of_date: str,
    max_series_points: int = 120
) -> SymbolDetailData:
    """Build SymbolDetailData for a symbol up to as_of_date."""
    relevant_records = [r for r in records if r.trading_date <= as_of_date]
    relevant_records.sort(key=lambda r: r.trading_date)

    if not relevant_records:
        return SymbolDetailData(
            schema_version=SCHEMA_VERSION,
            dataset_id=dataset_id,
            symbol=symbol,
            exchange="HOSE",
            as_of_date=as_of_date,
            latest=SymbolLatest(
                close=None,
                ma10=None,
                distance_pct=None,
                signal=None,
                data_status=DataStatus.NO_DATA_FOR_AS_OF_DATE,
            ),
            series=[],
            explanation=SymbolExplanation(
                current_close=None,
                current_ma10=None,
                previous_close=None,
                previous_ma10=None,
                rule=None,
            ),
        )

    last_rec = relevant_records[-1]
    prev_rec = relevant_records[-2] if len(relevant_records) > 1 else None

    # Series points for chart
    series_points: List[SymbolSeriesPoint] = []
    window = relevant_records[-max_series_points:] if len(relevant_records) > max_series_points else relevant_records
    for r in window:
        series_points.append(
            SymbolSeriesPoint(
                trading_date=r.trading_date,
                open=round_float(r.open, 2) or 0.0,
                high=round_float(r.high, 2) or 0.0,
                low=round_float(r.low, 2) or 0.0,
                close=round_float(r.close, 2) or 0.0,
                ma10=round_float(r.ma10, 2),
                volume=r.volume,
                signal=r.signal,
            )
        )

    # Explanation
    explanation = SymbolExplanation(
        current_close=round_float(last_rec.close, 2) if last_rec.trading_date == as_of_date else None,
        current_ma10=round_float(last_rec.ma10, 2) if last_rec.trading_date == as_of_date else None,
        previous_close=round_float(prev_rec.close, 2) if prev_rec and last_rec.trading_date == as_of_date else None,
        previous_ma10=round_float(prev_rec.ma10, 2) if prev_rec and last_rec.trading_date == as_of_date else None,
        rule=last_rec.signal_reason if last_rec.trading_date == as_of_date else None,
    )

    latest_status = last_rec.data_status if last_rec.trading_date == as_of_date else DataStatus.NO_DATA_FOR_AS_OF_DATE

    return SymbolDetailData(
        schema_version=SCHEMA_VERSION,
        dataset_id=dataset_id,
        symbol=symbol,
        exchange=last_rec.exchange,
        as_of_date=as_of_date,
        latest=SymbolLatest(
            close=round_float(last_rec.close, 2) if last_rec.trading_date == as_of_date else None,
            ma10=round_float(last_rec.ma10, 2) if last_rec.trading_date == as_of_date else None,
            distance_pct=round_float(last_rec.distance_pct, 2) if last_rec.trading_date == as_of_date else None,
            signal=last_rec.signal if last_rec.trading_date == as_of_date else None,
            data_status=latest_status,
        ),
        series=series_points,
        explanation=explanation,
    )


def serialize_dataset(
    manifest: ManifestData,
    overview: OverviewData,
    screener: ScreenerData,
    symbol_details: Dict[str, SymbolDetailData],
    staging_dir: str,
    output_dir: str
) -> None:
    """Write all JSON files to staging_dir, validate cross-file consistency, and copy to output_dir."""
    # Ensure staging directory exists and is clean
    if os.path.exists(staging_dir):
        shutil.rmtree(staging_dir)
    os.makedirs(staging_dir, exist_ok=True)
    symbols_dir = os.path.join(staging_dir, "symbols")
    os.makedirs(symbols_dir, exist_ok=True)

    # 1. Write overview.json
    overview_dict = {
        "schema_version": overview.schema_version,
        "dataset_id": overview.dataset_id,
        "as_of_date": overview.as_of_date,
        "metrics": {
            "eligible_count": overview.metrics.eligible_count,
            "above_count": overview.metrics.above_count,
            "above_pct": overview.metrics.above_pct,
            "below_count": overview.metrics.below_count,
            "below_pct": overview.metrics.below_pct,
            "on_ma10_count": overview.metrics.on_ma10_count,
            "cross_up_count": overview.metrics.cross_up_count,
            "cross_down_count": overview.metrics.cross_down_count,
        },
        "breadth_history": [
            {
                "trading_date": pt.trading_date,
                "eligible_count": pt.eligible_count,
                "above_count": pt.above_count,
                "above_pct": pt.above_pct,
            }
            for pt in overview.breadth_history
        ],
    }
    with open(os.path.join(staging_dir, "overview.json"), "w", encoding="utf-8") as f:
        json.dump(sanitize_value(overview_dict), f, indent=2)

    # 2. Write screener.json
    screener_dict = {
        "schema_version": screener.schema_version,
        "dataset_id": screener.dataset_id,
        "as_of_date": screener.as_of_date,
        "items": [
            {
                "symbol": item.symbol,
                "exchange": item.exchange,
                "in_vn30": item.in_vn30,
                "last_trading_date": item.last_trading_date,
                "close": item.close,
                "ma10": item.ma10,
                "distance_pct": item.distance_pct,
                "volume": item.volume,
                "avg_volume_20d": item.avg_volume_20d,
                "signal": item.signal.value if item.signal else None,
                "signal_reason": item.signal_reason,
                "data_status": item.data_status.value,
            }
            for item in screener.items
        ],
    }
    with open(os.path.join(staging_dir, "screener.json"), "w", encoding="utf-8") as f:
        json.dump(sanitize_value(screener_dict), f, indent=2)

    # 3. Write symbols/*.json
    for sym, detail in symbol_details.items():
        detail_dict = {
            "schema_version": detail.schema_version,
            "dataset_id": detail.dataset_id,
            "symbol": detail.symbol,
            "exchange": detail.exchange,
            "as_of_date": detail.as_of_date,
            "latest": {
                "close": detail.latest.close,
                "ma10": detail.latest.ma10,
                "distance_pct": detail.latest.distance_pct,
                "signal": detail.latest.signal.value if detail.latest.signal else None,
                "data_status": detail.latest.data_status.value,
            },
            "series": [
                {
                    "trading_date": s.trading_date,
                    "open": s.open,
                    "high": s.high,
                    "low": s.low,
                    "close": s.close,
                    "ma10": s.ma10,
                    "volume": s.volume,
                    "signal": s.signal.value if s.signal else None,
                }
                for s in detail.series
            ],
            "explanation": {
                "current_close": detail.explanation.current_close,
                "current_ma10": detail.explanation.current_ma10,
                "previous_close": detail.explanation.previous_close,
                "previous_ma10": detail.explanation.previous_ma10,
                "rule": detail.explanation.rule,
            },
        }
        with open(os.path.join(symbols_dir, f"{sym}.json"), "w", encoding="utf-8") as f:
            json.dump(sanitize_value(detail_dict), f, indent=2)

    # 4. Write manifest.json last
    manifest_dict = {
        "schema_version": manifest.schema_version,
        "dataset_id": manifest.dataset_id,
        "as_of_date": manifest.as_of_date,
        "generated_at": manifest.generated_at,
        "market_timezone": manifest.market_timezone,
        "market_session_status": manifest.market_session_status,
        "freshness": {
            "status": manifest.freshness.status.value,
            "expected_as_of_date": manifest.freshness.expected_as_of_date,
            "reason": manifest.freshness.reason,
        },
        "provider": manifest.provider,
        "universe": manifest.universe,
        "files": manifest.files,
        "quality": {
            "status": manifest.quality.status.value,
            "input_rows": manifest.quality.input_rows,
            "accepted_rows": manifest.quality.accepted_rows,
            "rejected_rows": manifest.quality.rejected_rows,
            "eligible_symbols": manifest.quality.eligible_symbols,
            "warnings": manifest.quality.warnings,
        },
    }
    with open(os.path.join(staging_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(sanitize_value(manifest_dict), f, indent=2)

    # Verify cross-file consistency in staging
    dataset_id = manifest.dataset_id
    schema_ver = manifest.schema_version
    as_of = manifest.as_of_date

    assert overview.dataset_id == dataset_id, "overview.json dataset_id mismatch"
    assert overview.schema_version == schema_ver, "overview.json schema_version mismatch"
    assert overview.as_of_date == as_of, "overview.json as_of_date mismatch"

    assert screener.dataset_id == dataset_id, "screener.json dataset_id mismatch"
    assert screener.schema_version == schema_ver, "screener.json schema_version mismatch"
    assert screener.as_of_date == as_of, "screener.json as_of_date mismatch"

    for sym, detail in symbol_details.items():
        assert detail.dataset_id == dataset_id, f"symbols/{sym}.json dataset_id mismatch"
        assert detail.schema_version == schema_ver, f"symbols/{sym}.json schema_version mismatch"
        assert detail.as_of_date == as_of, f"symbols/{sym}.json as_of_date mismatch"

    # Publish staging to output_dir
    os.makedirs(output_dir, exist_ok=True)
    target_symbols_dir = os.path.join(output_dir, "symbols")
    os.makedirs(target_symbols_dir, exist_ok=True)

    # Copy files
    shutil.copyfile(os.path.join(staging_dir, "overview.json"), os.path.join(output_dir, "overview.json"))
    shutil.copyfile(os.path.join(staging_dir, "screener.json"), os.path.join(output_dir, "screener.json"))
    for filename in os.listdir(symbols_dir):
        shutil.copyfile(os.path.join(symbols_dir, filename), os.path.join(target_symbols_dir, filename))
    shutil.copyfile(os.path.join(staging_dir, "manifest.json"), os.path.join(output_dir, "manifest.json"))
