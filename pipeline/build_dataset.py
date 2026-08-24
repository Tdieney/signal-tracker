"""CLI entrypoint to execute the VN Stock Signal pipeline and generate static JSON."""

from __future__ import annotations

import argparse
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


def build_dataset_from_records(
    records: list,
    output_dir: str,
    staging_dir: str,
    as_of_date: str | None = None,
    provider_name: str = "csv",
    universe_name: str = "ALL",
) -> str:
    """Build and serialize full dataset from normalized OHLCV records."""
    # 1. Normalize and validate
    accepted_records, quality_info = validate_and_normalize_records(records, strict_duplicates=True)
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

    # 5. Build Overview Data
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    dataset_id = now_utc

    overview_data = OverviewData(
        schema_version=SCHEMA_VERSION,
        dataset_id=dataset_id,
        as_of_date=target_as_of,
        metrics=as_of_metric,
        breadth_history=breadth_history,
    )

    # 6. Build Screener Items
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

    # 8. Build Manifest
    manifest_data = ManifestData(
        schema_version=SCHEMA_VERSION,
        dataset_id=dataset_id,
        as_of_date=target_as_of,
        generated_at=now_utc,
        market_timezone=MARKET_TIMEZONE,
        market_session_status=MarketSessionStatus.CLOSED_CONFIRMED.value,
        freshness=FreshnessInfo(
            status=FreshnessStatus.FRESH,
            expected_as_of_date=target_as_of,
            reason="Latest expected completed trading session",
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

    # 9. Serialize & validate cross-file consistency
    serialize_dataset(
        manifest=manifest_data,
        overview=overview_data,
        screener=screener_data,
        symbol_details=symbol_details,
        staging_dir=staging_dir,
        output_dir=output_dir,
    )

    return dataset_id


def main() -> None:
    parser = argparse.ArgumentParser(description="VN Stock Signal Dataset Builder")
    parser.add_argument("--provider", default="csv", choices=["csv", "vnstock"], help="Data provider")
    parser.add_argument("--input", default="tests/fixtures/sample_ohlcv.csv", help="Input CSV fixture path")
    parser.add_argument("--output", default="frontend/public/data", help="Output directory for static JSON")
    parser.add_argument("--staging", default=".staging_data", help="Temporary staging directory")
    parser.add_argument("--as-of-date", default=None, help="Target as-of trading date (YYYY-MM-DD)")
    parser.add_argument("--universe", default="ALL", help="Universe name")

    args = parser.parse_args()

    if args.provider == "csv":
        if not os.path.exists(args.input):
            print(f"Error: Input file not found: {args.input}", file=sys.stderr)
            sys.exit(1)
        provider = CsvDataProvider(args.input)
        records = provider.fetch_ohlcv()
    elif args.provider == "vnstock":
        try:
            from pipeline.providers.vnstock_provider import VnstockDataProvider
            provider = VnstockDataProvider()
            records = provider.fetch_ohlcv()
        except ImportError as e:
            print(f"Error loading vnstock provider: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"Unknown provider: {args.provider}", file=sys.stderr)
        sys.exit(1)

    print(f"Processing {len(records)} records from {args.provider}...")
    dataset_id = build_dataset_from_records(
        records=records,
        output_dir=args.output,
        staging_dir=args.staging,
        as_of_date=args.as_of_date,
        provider_name=args.provider,
        universe_name=args.universe,
    )
    print(f"Successfully generated dataset {dataset_id} into {args.output}")


if __name__ == "__main__":
    main()
