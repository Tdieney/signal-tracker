"""CLI entrypoint to execute the VN Stock Signal pipeline and generate static JSON."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from typing import Optional, Sequence

# Ensure repo root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pipeline.freshness import evaluate_dataset_freshness, evaluate_market_session_status
from pipeline.indicators import calculate_all_indicators
from pipeline.models import (
    MARKET_TIMEZONE,
    SCHEMA_VERSION,
    FreshnessInfo,
    FreshnessStatus,
    ManifestData,
    MarketSessionStatus,
    OverviewData,
    ScreenerData,
)
from pipeline.providers.base import ProviderFetchResult
from pipeline.providers.company_api_provider import CompanyApiDataProvider
from pipeline.providers.csv_provider import CsvDataProvider
from pipeline.providers.vnstock_provider import VnstockDataProvider
from pipeline.serialization import (
    build_screener_item,
    build_symbol_detail,
    serialize_dataset,
)
from pipeline.signals import calculate_market_breadth, classify_signals_for_symbol
from pipeline.validation import validate_and_normalize_records


def compute_deterministic_dataset_id(
    as_of_date: str,
    records: list,
    provider: str = "csv",
    universe: str = "ALL",
    quality_status: str = "PASS",
    eligible_count: int = 0,
    quality_metadata: dict | None = None,
    market_session_status: str = "UNKNOWN",
    freshness_status: str = "UNKNOWN",
) -> str:
    """Derive deterministic 16-hex dataset ID hash from canonical sorted representation of all pipeline inputs & public metrics."""
    canonical_data = {
        "as_of_date": as_of_date,
        "provider": provider,
        "universe": universe,
        "quality_status": quality_status,
        "eligible_count": eligible_count,
        "quality_metadata": quality_metadata or {},
        "market_session_status": market_session_status,
        "freshness_status": freshness_status,
        "records": [
            [
                r.symbol,
                r.trading_date,
                r.exchange,
                r.in_vn30,
                r.open,
                r.high,
                r.low,
                r.close,
                r.adjusted_close,
                r.volume,
                r.trading_value,
            ]
            for r in sorted(records, key=lambda x: (x.symbol, x.trading_date))
        ],
    }
    canonical_json = json.dumps(canonical_data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()[:16]


def build_dataset_from_records(
    records: list | ProviderFetchResult,
    output_dir: str = "frontend/public/data",
    staging_dir: str | None = None,
    as_of_date: str | None = None,
    provider_name: str = "csv",
    universe_name: str = "ALL",
    parse_errors_count: int = 0,
    parse_warnings: list | None = None,
    fixed_generated_at: str | None = None,
    reference_time: datetime | None = None,
    workspace_root: str | None = None,
    source_rows_count: int | None = None,
    is_live_provider: bool = False,
) -> str:
    """Build and serialize full dataset from normalized OHLCV records with injected reference time."""
    if isinstance(records, ProviderFetchResult):
        raw_records = records.records
        parse_errors_count = parse_errors_count or records.rejected_rows
        parse_warnings = parse_warnings or records.warnings
        source_rows_count = source_rows_count or records.input_rows
        provider_name = records.provider_name or provider_name
    else:
        raw_records = list(records)

    # 1. Normalize and validate with strict accounting
    accepted_records, quality_info = validate_and_normalize_records(
        raw_records,
        strict_duplicates=True,
        parse_errors_count=parse_errors_count,
        parse_warnings=parse_warnings,
        source_rows_count=source_rows_count,
    )
    if not accepted_records:
        raise ValueError("No valid records found in data source")

    # 2. Determine as_of_date
    all_dates = sorted(set(r.trading_date for r in accepted_records))
    latest_date = all_dates[-1]
    target_as_of = as_of_date if as_of_date else latest_date

    # 3. Calculate indicators and classify signals per symbol
    indicators_by_symbol = calculate_all_indicators(accepted_records)
    for sym, sym_recs in indicators_by_symbol.items():
        classify_signals_for_symbol(sym_recs)

    # 4. Calculate Market Breadth
    as_of_metric, breadth_history = calculate_market_breadth(indicators_by_symbol, target_as_of)

    # 5. Fix quality eligible_symbols to exact breadth-eligible count
    quality_info.eligible_symbols = as_of_metric.eligible_count

    # 6. Resolve deterministic reference time
    ref_dt = reference_time
    if ref_dt is None and fixed_generated_at:
        try:
            # Parse fixed ISO timestamp
            clean_iso = fixed_generated_at.replace("Z", "+00:00")
            ref_dt = datetime.fromisoformat(clean_iso)
        except Exception:
            ref_dt = None
    if ref_dt is None:
        ref_dt = datetime.now(timezone.utc)

    generated_at_str = fixed_generated_at or ref_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    # 7. Evaluate Session Status and Freshness with reference time injection
    has_complete = (quality_info.status.value in ("PASS", "PARTIAL")) and len(accepted_records) > 0
    session_status = evaluate_market_session_status(
        as_of_date=target_as_of,
        reference_time=ref_dt,
        is_live_provider=is_live_provider,
        has_complete_data=has_complete,
    )
    freshness_info = evaluate_dataset_freshness(
        as_of_date=target_as_of,
        reference_time=ref_dt,
        is_live_provider=is_live_provider,
        has_complete_data=has_complete,
    )

    # 8. Compute Canonical Dataset ID
    dataset_id = compute_deterministic_dataset_id(
        as_of_date=target_as_of,
        records=accepted_records,
        provider=provider_name,
        universe=universe_name,
        quality_status=quality_info.status.value,
        eligible_count=as_of_metric.eligible_count,
        quality_metadata={
            "input_rows": quality_info.input_rows,
            "accepted_rows": quality_info.accepted_rows,
            "rejected_rows": quality_info.rejected_rows,
            "warnings": quality_info.warnings,
        },
        market_session_status=session_status.value,
        freshness_status=freshness_info.status.value,
    )

    overview_data = OverviewData(
        schema_version=SCHEMA_VERSION,
        dataset_id=dataset_id,
        as_of_date=target_as_of,
        metrics=as_of_metric,
        breadth_history=breadth_history,
    )

    all_symbols = sorted(indicators_by_symbol.keys())
    screener_items = [
        build_screener_item(sym, indicators_by_symbol[sym], target_as_of)
        for sym in all_symbols
    ]
    screener_data = ScreenerData(
        schema_version=SCHEMA_VERSION,
        dataset_id=dataset_id,
        as_of_date=target_as_of,
        items=screener_items,
    )

    # 9. Build Symbol Details
    symbol_details = {
        sym: build_symbol_detail(sym, indicators_by_symbol[sym], dataset_id, target_as_of)
        for sym in all_symbols
    }

    # 10. Build Manifest Data
    manifest_data = ManifestData(
        schema_version=SCHEMA_VERSION,
        dataset_id=dataset_id,
        as_of_date=target_as_of,
        generated_at=generated_at_str,
        market_timezone=MARKET_TIMEZONE,
        market_session_status=session_status,
        freshness=freshness_info,
        provider=provider_name,
        universe=universe_name,
        files={
            "overview": "overview.json",
            "screener": "screener.json",
            "symbols_base": "symbols/",
        },
        quality=quality_info,
    )

    # 11. Serialize & validate cross-file consistency atomically
    serialize_dataset(
        manifest=manifest_data,
        overview=overview_data,
        screener=screener_data,
        symbol_details=symbol_details,
        staging_dir=staging_dir,
        output_dir=output_dir,
        workspace_root=workspace_root,
    )

    return dataset_id


def main() -> None:
    parser = argparse.ArgumentParser(description="VN Stock Signal Data Pipeline")
    parser.add_argument("--provider", default="csv", choices=["csv", "vnstock", "company_api"], help="Data provider")
    parser.add_argument("--input", default="tests/fixtures/sample_ohlcv.csv", help="Input CSV file path (for csv provider)")
    parser.add_argument("--output", default="frontend/public/data", help="Output directory for JSON")
    parser.add_argument("--staging", default=None, help="Optional staging temporary directory")
    parser.add_argument("--as-of", default=None, help="Target as-of date (YYYY-MM-DD)")
    parser.add_argument("--universe", default="ALL", choices=["ALL", "VN30"], help="Universe name")
    parser.add_argument("--generated-at", default=None, help="Fixed ISO timestamp for deterministic test builds")
    parser.add_argument("--reference-time", default=None, help="Fixed ISO reference time for freshness evaluation")

    args = parser.parse_args()

    if args.provider.lower() == "csv":
        provider = CsvDataProvider(args.input)
        raw_result = provider.fetch_ohlcv()
    elif args.provider.lower() == "vnstock":
        provider = VnstockDataProvider()
        raw_result = provider.fetch_ohlcv()
    else:
        provider = CompanyApiDataProvider()
        raw_result = provider.fetch_ohlcv()

    print(f"Processing {len(raw_result.records)} records from {args.provider} (input_rows={raw_result.input_rows})...")

    ref_dt = None
    if args.reference_time:
        try:
            ref_dt = datetime.fromisoformat(args.reference_time.replace("Z", "+00:00"))
        except Exception:
            ref_dt = None

    try:
        ds_id = build_dataset_from_records(
            records=raw_result.records,
            output_dir=args.output,
            staging_dir=args.staging,
            as_of_date=args.as_of,
            provider_name=args.provider,
            universe_name=args.universe,
            parse_errors_count=raw_result.rejected_rows,
            parse_warnings=raw_result.warnings,
            fixed_generated_at=args.generated_at,
            reference_time=ref_dt,
            source_rows_count=raw_result.input_rows,
            is_live_provider=(args.provider.lower() != "csv"),
        )
        print(f"Successfully generated dataset {ds_id} into {args.output}")
    except Exception as ex:
        print(f"ERROR: Pipeline generation failed: {ex}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
