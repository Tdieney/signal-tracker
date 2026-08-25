"""CLI entrypoint to execute the VN Stock Signal pipeline and generate static JSON."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

# Ensure repo root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

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
from pipeline.providers.csv_provider import CsvDataProvider
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
) -> str:
    """Derive deterministic 16-hex dataset ID hash from canonical sorted representation of all pipeline inputs & public metrics.

    Excludes volatile `generated_at` build timestamp so identical data inputs yield identical dataset_id.
    """
    canonical_data = {
        "as_of_date": as_of_date,
        "provider": provider,
        "universe": universe,
        "quality_status": quality_status,
        "eligible_count": eligible_count,
        "quality_metadata": quality_metadata or {},
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
    records: list,
    output_dir: str = "frontend/public/data",
    staging_dir: str | None = None,
    as_of_date: str | None = None,
    provider_name: str = "csv",
    universe_name: str = "ALL",
    parse_errors_count: int = 0,
    parse_warnings: list | None = None,
    fixed_generated_at: str | None = None,
    workspace_root: str | None = None,
    source_rows_count: int | None = None,
) -> str:
    """Build and serialize full dataset from normalized OHLCV records."""
    # 1. Normalize and validate with strict accounting
    accepted_records, quality_info = validate_and_normalize_records(
        records,
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

    # 6. Build Overview & Screener Data with canonical hash
    generated_at_str = fixed_generated_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
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

    # 7. Build Symbol Details
    symbol_details = {
        sym: build_symbol_detail(sym, indicators_by_symbol[sym], dataset_id, target_as_of)
        for sym in all_symbols
    }

    # 8. Build Manifest with Truthful Semantics (safe default is UNKNOWN)
    is_csv_fixture = (provider_name.lower() == "csv")
    session_status = MarketSessionStatus.UNKNOWN.value
    freshness_status = FreshnessStatus.UNKNOWN
    freshness_reason = (
        "Dữ liệu mẫu thử nghiệm (fixture/demo), không phải dữ liệu thị trường trực tiếp."
        if is_csv_fixture
        else "Offline dataset"
    )

    manifest_data = ManifestData(
        schema_version=SCHEMA_VERSION,
        dataset_id=dataset_id,
        as_of_date=target_as_of,
        generated_at=generated_at_str,
        market_timezone=MARKET_TIMEZONE,
        market_session_status=session_status,
        freshness=FreshnessInfo(
            status=freshness_status,
            expected_as_of_date=target_as_of,
            reason=freshness_reason,
        ),
        provider=provider_name,
        universe=universe_name,
        files={
            "overview": "overview.json",
            "screener": "screener.json",
            "symbols_base": "symbols/",
        },
        quality=quality_info,
    )

    # 9. Serialize & validate cross-file consistency atomically
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
    parser.add_argument("--provider", default="csv", choices=["csv", "vnstock"], help="Data provider")
    parser.add_argument("--input", default="tests/fixtures/sample_ohlcv.csv", help="Input CSV file path")
    parser.add_argument("--output", default="frontend/public/data", help="Output directory for JSON")
    parser.add_argument("--staging", default=None, help="Optional staging temporary directory")
    parser.add_argument("--as-of", default=None, help="Target as-of date (YYYY-MM-DD)")
    parser.add_argument("--universe", default="ALL", choices=["ALL", "VN30"], help="Universe name")
    parser.add_argument("--generated-at", default=None, help="Fixed ISO timestamp for deterministic test builds")

    args = parser.parse_args()

    if args.provider.lower() != "csv":
        print(
            f"ERROR: Provider '{args.provider}' is experimental and unsupported for production in Phase 1. Use --provider csv.",
            file=sys.stderr,
        )
        sys.exit(1)

    provider = CsvDataProvider(args.input)
    raw_records = provider.fetch_ohlcv()
    print(f"Processing {len(raw_records)} records from {args.provider}...")

    try:
        ds_id = build_dataset_from_records(
            records=raw_records,
            output_dir=args.output,
            staging_dir=args.staging,
            as_of_date=args.as_of,
            provider_name=args.provider,
            universe_name=args.universe,
            parse_errors_count=provider.rejected_rows_count,
            parse_warnings=provider.parse_warnings,
            fixed_generated_at=args.generated_at,
            source_rows_count=provider.source_rows_count,
        )
        print(f"Successfully generated dataset {ds_id} into {args.output}")
    except Exception as ex:
        print(f"ERROR: Pipeline generation failed: {ex}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
