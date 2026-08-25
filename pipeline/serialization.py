"""Serialization and staging output builder for VN Stock Signal pipeline."""

from __future__ import annotations

import json
import math
import os
import shutil
import tempfile
import uuid
from typing import Any, Dict, List, Optional, Set
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


class DataIntegrityError(Exception):
    """Raised when cross-file dataset integrity or validation fails."""
    pass


class FilesystemSafetyError(ValueError):
    """Raised when a directory path fails safety checks (root, home, escape, overlap)."""
    pass


def validate_target_directory(
    path: str,
    workspace_root: Optional[str] = None,
    allow_temp: bool = True
) -> str:
    """Validate that a target path is safe and not a root, home, workspace root, or dangerous directory.

    Rejects:
    - empty or non-string paths
    - filesystem roots ('/', 'C:\\', drive roots)
    - user home root ('~')
    - system directories ('/etc', '/var', 'C:\\Windows', etc.)
    - repository root ('.' or repo path)
    - repository parent or paths escaping workspace via '..' or symlinks (unless inside tempdir)
    """
    if not path or not isinstance(path, str):
        raise FilesystemSafetyError("Target directory path cannot be empty or non-string")

    norm_path = os.path.abspath(os.path.normpath(path))
    real_path = os.path.realpath(norm_path)
    home_dir = os.path.realpath(os.path.abspath(os.path.expanduser("~")))

    # Default workspace root is repo root (parent of pipeline dir)
    if workspace_root is None:
        workspace_root = os.path.realpath(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    else:
        workspace_root = os.path.realpath(os.path.abspath(workspace_root))

    # Reject filesystem roots (e.g. '/' on Linux, 'C:\' on Windows)
    drive, rest = os.path.splitdrive(norm_path)
    if norm_path in ("/", "\\", drive + "\\", drive + "/", drive) or real_path in ("/", "\\", drive + "\\", drive + "/", drive):
        raise FilesystemSafetyError(f"Dangerous target path rejected (filesystem root): {path}")

    # Reject user home root exactly
    if norm_path == home_dir or real_path == home_dir:
        raise FilesystemSafetyError(f"Dangerous target path rejected (user home root): {path}")

    # Reject system directories
    for sys_dir in ["/etc", "/var", "/bin", "/usr", "/lib", "/boot", "/sys", "/proc", "C:\\Windows", "C:\\Program Files", "C:\\Program Files (x86)"]:
        if norm_path.lower() == os.path.abspath(sys_dir).lower() or real_path.lower() == os.path.realpath(sys_dir).lower():
            raise FilesystemSafetyError(f"Dangerous target path rejected (system directory): {path}")

    # Reject repository root exactly
    if norm_path == workspace_root or real_path == workspace_root:
        raise FilesystemSafetyError(f"Dangerous target path rejected (repository root directory): {path}")

    # Check if path is within workspace or allowed temporary directory
    temp_dir = os.path.normcase(os.path.realpath(tempfile.gettempdir()))
    norm_ws = os.path.normcase(workspace_root)
    norm_real = os.path.normcase(real_path)

    is_in_workspace = False
    try:
        if os.path.commonpath([norm_ws, norm_real]) == norm_ws and norm_real != norm_ws:
            is_in_workspace = True
    except ValueError:
        pass

    is_in_temp = False
    if allow_temp:
        try:
            if os.path.commonpath([temp_dir, norm_real]) == temp_dir and norm_real != temp_dir:
                is_in_temp = True
        except ValueError:
            pass

    if not is_in_workspace and not is_in_temp:
        raise FilesystemSafetyError(
            f"Dangerous target path rejected (outside workspace and temp directory): {path}"
        )

    return norm_path


def validate_no_directory_overlap(staging_path: str, output_path: str) -> None:
    """Ensure staging and output directories do not overlap or equal each other."""
    s_real = os.path.normcase(os.path.realpath(os.path.abspath(staging_path)))
    o_real = os.path.normcase(os.path.realpath(os.path.abspath(output_path)))

    if s_real == o_real:
        raise FilesystemSafetyError(f"Staging directory cannot be identical to output directory: {staging_path}")

    try:
        common = os.path.commonpath([s_real, o_real])
    except ValueError:
        # Different drives on Windows (disjoint by definition)
        return

    if common == o_real or common == s_real:
        raise FilesystemSafetyError(f"Staging directory and output directory cannot overlap: {staging_path} and {output_path}")


def sanitize_value(val: Any) -> Any:
    """Ensure no NaN or Infinity enters serialized JSON, rejecting non-finite numbers."""
    if val is None:
        return None
    if isinstance(val, float):
        if math.isnan(val) or math.isinf(val):
            raise ValueError(f"Non-finite float value detected in JSON serialization: {val}")
        return round(val, 4)
    if isinstance(val, list):
        return [sanitize_value(v) for v in val]
    if isinstance(val, dict):
        return {k: sanitize_value(v) for k, v in val.items()}
    return val


def round_float(val: Optional[float], decimals: int = 2) -> Optional[float]:
    """Round float cleanly, returning None if val is None or invalid."""
    if val is None:
        return None
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
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
    staging_dir: Optional[str] = None,
    output_dir: str = "frontend/public/data",
    workspace_root: Optional[str] = None,
) -> None:
    """Write all JSON files to an isolated staging directory, validate cross-file consistency,
    and atomically publish to output_dir with backup and rollback.
    """
    # 0. Safety validation on target directories
    safe_output = validate_target_directory(output_dir, workspace_root=workspace_root)
    output_parent = os.path.dirname(safe_output)
    os.makedirs(output_parent, exist_ok=True)

    # Use an isolated sibling temporary staging directory
    if staging_dir is not None:
        safe_staging = validate_target_directory(staging_dir, workspace_root=workspace_root)
        validate_no_directory_overlap(safe_staging, safe_output)
        # Never rmtree caller-supplied staging dir without creating a dedicated isolated subfolder
        staging_root = os.path.join(safe_staging, f".dataset_build_{uuid.uuid4().hex[:8]}")
    else:
        staging_root = os.path.join(output_parent, f".staging_{uuid.uuid4().hex[:8]}")

    os.makedirs(staging_root, exist_ok=True)
    symbols_staging_dir = os.path.join(staging_root, "symbols")
    os.makedirs(symbols_staging_dir, exist_ok=True)

    try:
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
        with open(os.path.join(staging_root, "overview.json"), "w", encoding="utf-8") as f:
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
        with open(os.path.join(staging_root, "screener.json"), "w", encoding="utf-8") as f:
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
            with open(os.path.join(symbols_staging_dir, f"{sym}.json"), "w", encoding="utf-8") as f:
                json.dump(sanitize_value(detail_dict), f, indent=2)

        # 4. Write manifest.json strictly last in staging
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
        with open(os.path.join(staging_root, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(sanitize_value(manifest_dict), f, indent=2)

        # 5. Verify cross-file consistency in staging with explicit exceptions
        dataset_id = manifest.dataset_id
        schema_ver = manifest.schema_version
        as_of = manifest.as_of_date

        if overview.dataset_id != dataset_id:
            raise DataIntegrityError(f"overview.json dataset_id mismatch: {overview.dataset_id} != {dataset_id}")
        if overview.schema_version != schema_ver:
            raise DataIntegrityError(f"overview.json schema_version mismatch: {overview.schema_version} != {schema_ver}")
        if overview.as_of_date != as_of:
            raise DataIntegrityError(f"overview.json as_of_date mismatch: {overview.as_of_date} != {as_of}")

        if screener.dataset_id != dataset_id:
            raise DataIntegrityError(f"screener.json dataset_id mismatch: {screener.dataset_id} != {dataset_id}")
        if screener.schema_version != schema_ver:
            raise DataIntegrityError(f"screener.json schema_version mismatch: {screener.schema_version} != {schema_ver}")
        if screener.as_of_date != as_of:
            raise DataIntegrityError(f"screener.json as_of_date mismatch: {screener.as_of_date} != {as_of}")

        for sym, detail in symbol_details.items():
            if detail.dataset_id != dataset_id:
                raise DataIntegrityError(f"symbols/{sym}.json dataset_id mismatch: {detail.dataset_id} != {dataset_id}")
            if detail.schema_version != schema_ver:
                raise DataIntegrityError(f"symbols/{sym}.json schema_version mismatch: {detail.schema_version} != {schema_ver}")
            if detail.as_of_date != as_of:
                raise DataIntegrityError(f"symbols/{sym}.json as_of_date mismatch: {detail.as_of_date} != {as_of}")

        # 6. Atomic directory publish with backup and rollback
        backup_dir = os.path.join(output_parent, f".backup_{uuid.uuid4().hex[:8]}")
        has_existing_output = os.path.exists(safe_output)

        if has_existing_output:
            try:
                # Rename current output to backup
                os.rename(safe_output, backup_dir)
            except OSError as ex:
                raise IOError(f"Failed to create backup of existing output directory: {ex}") from ex

        try:
            # Move staging to output
            os.rename(staging_root, safe_output)
            # Swap succeeded: remove backup directory
            if has_existing_output and os.path.exists(backup_dir):
                shutil.rmtree(backup_dir, ignore_errors=True)
        except Exception as swap_err:
            # Rollback: restore backup if available
            if has_existing_output and os.path.exists(backup_dir):
                try:
                    if os.path.exists(safe_output):
                        shutil.rmtree(safe_output, ignore_errors=True)
                    os.rename(backup_dir, safe_output)
                except Exception as rb_err:
                    raise IOError(f"Critical swap failure and rollback failed: {swap_err}; rollback error: {rb_err}") from swap_err
            raise IOError(f"Atomic directory swap failed: {swap_err}") from swap_err

    finally:
        # Clean up temporary staging directory if it still exists
        if os.path.exists(staging_root):
            shutil.rmtree(staging_root, ignore_errors=True)
