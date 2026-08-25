"""End-to-end integration and adversarial regression tests for VN30 dataset generation and completeness rules."""

import json
import os
import shutil
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock

from pipeline.build_dataset import build_dataset_from_records
from pipeline.models import VN30_SYMBOLS, get_universe_symbols
from pipeline.providers.vnstock_client import VnstockMarketClient
from pipeline.providers.vnstock_provider import VnstockDataProvider
from scripts.security_check import validate_data_directory


class TestLiveDatasetPipeline(unittest.TestCase):
    """Test suite verifying VN30 dataset generation, completeness enforcement, and fail-closed aborts."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.output_dir = os.path.join(self.test_dir, "data")
        self.mock_client = MagicMock(spec=VnstockMarketClient)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _generate_mock_symbol_bars(
        self,
        symbol: str,
        num_bars: int = 30,
        end_date_str: str = "2026-08-25",
    ):
        bars = []
        base_price = 50.0 + (hash(symbol) % 50)
        parts = [int(p) for p in end_date_str.split("-")]
        cur_d = date(parts[0], parts[1], parts[2])
        dates = []
        while len(dates) < num_bars:
            if cur_d.weekday() < 5:
                dates.append(cur_d.strftime("%Y-%m-%d"))
            cur_d -= timedelta(days=1)
        dates.reverse()

        for i, dt_str in enumerate(dates):
            p = round(base_price + (i * 0.2), 2)
            bars.append({
                "trading_date": dt_str,
                "symbol": symbol,
                "exchange": "HOSE",
                "open": round(p - 0.5, 2),
                "high": round(p + 1.0, 2),
                "low": round(p - 1.0, 2),
                "close": p,
                "volume": 1000000 + (i * 10000),
                "in_vn30": symbol in VN30_SYMBOLS,
            })
        return bars

    def test_complete_vn30_mock_pipeline_generation(self):
        """Verify building complete 30-symbol VN30 dataset generates all symbol files and passes validation."""
        def mock_fetch(symbol, lookback_days=180, start_date=None, end_date=None):
            return self._generate_mock_symbol_bars(symbol, num_bars=30, end_date_str="2026-08-25")

        self.mock_client.fetch_daily_bars.side_effect = mock_fetch

        provider = VnstockDataProvider(client=self.mock_client)
        result = provider.fetch_ohlcv(symbols=get_universe_symbols("VN30"))

        self.assertEqual(result.provider_name, "vnstock")
        self.assertTrue(result.is_complete)
        self.assertEqual(result.input_rows, 30 * 30)
        self.assertEqual(result.accepted_rows, 30 * 30)
        self.assertEqual(result.rejected_rows, 0)

        dataset_id = build_dataset_from_records(
            records=result,
            output_dir=self.output_dir,
            provider_name="vnstock",
            universe_name="VN30",
            as_of_date="2026-08-25",
            fixed_generated_at="2026-08-25T14:30:00Z",
            reference_time=datetime(2026, 8, 25, 16, 0, 0, tzinfo=timezone.utc),
            is_live_provider=True,
            is_complete=True,
        )

        self.assertTrue(os.path.exists(os.path.join(self.output_dir, "manifest.json")))
        self.assertTrue(os.path.exists(os.path.join(self.output_dir, "overview.json")))
        self.assertTrue(os.path.exists(os.path.join(self.output_dir, "screener.json")))

        # Check all 30 symbols exist on disk
        for sym in VN30_SYMBOLS:
            sym_file = os.path.join(self.output_dir, "symbols", f"{sym}.json")
            self.assertTrue(os.path.exists(sym_file), f"Missing symbol file: {sym_file}")

        with open(os.path.join(self.output_dir, "manifest.json"), "r", encoding="utf-8") as f:
            manifest = json.load(f)

        self.assertEqual(manifest["dataset_id"], dataset_id)
        self.assertEqual(manifest["quality"]["status"], "PASS")
        self.assertEqual(manifest["quality"]["eligible_symbols"], 30)
        self.assertEqual(manifest["freshness"]["status"], "FRESH")
        self.assertEqual(manifest["market_session_status"], "CLOSED_CONFIRMED")

        errors = validate_data_directory(self.output_dir)
        self.assertEqual(errors, [], f"Data directory security violations: {errors}")

    def test_incomplete_as_of_date_coverage_yields_unknown_session_and_non_fresh(self):
        """Adversarial test: If 29/30 symbols are missing latest session (only 1 eligible on as_of_date),
        manifest must NOT announce FRESH or CLOSED_CONFIRMED."""
        def mock_fetch_skewed(symbol, lookback_days=180, start_date=None, end_date=None):
            # Only FPT has data up to 2026-08-25; all other 29 symbols ended on 2026-08-24
            if symbol == "FPT":
                return self._generate_mock_symbol_bars(symbol, num_bars=30, end_date_str="2026-08-25")
            else:
                return self._generate_mock_symbol_bars(symbol, num_bars=30, end_date_str="2026-08-24")

        self.mock_client.fetch_daily_bars.side_effect = mock_fetch_skewed

        provider = VnstockDataProvider(client=self.mock_client)
        result = provider.fetch_ohlcv(symbols=get_universe_symbols("VN30"))

        dataset_id = build_dataset_from_records(
            records=result,
            output_dir=self.output_dir,
            provider_name="vnstock",
            universe_name="VN30",
            as_of_date="2026-08-25",
            fixed_generated_at="2026-08-25T14:30:00Z",
            reference_time=datetime(2026, 8, 25, 16, 0, 0, tzinfo=timezone.utc),
            is_live_provider=True,
            is_complete=False,
        )

        with open(os.path.join(self.output_dir, "manifest.json"), "r", encoding="utf-8") as f:
            manifest = json.load(f)

        # Only 1 symbol (FPT) is eligible on 2026-08-25
        self.assertEqual(manifest["quality"]["eligible_symbols"], 1)
        self.assertNotEqual(manifest["freshness"]["status"], "FRESH")
        self.assertNotEqual(manifest["market_session_status"], "CLOSED_CONFIRMED")
        self.assertEqual(manifest["market_session_status"], "UNKNOWN")

    def test_missing_constituent_aborts_live_build_fail_closed(self):
        """Adversarial test: If any constituent is missing entirely (e.g. only 29/30 symbols fetched),
        live production build must raise ValueError (fail closed) without promoting partial dataset."""
        # Omit 'VNM' entirely from the universe
        symbols_29 = [s for s in get_universe_symbols("VN30") if s != "VNM"]

        def mock_fetch_29(symbol, lookback_days=180, start_date=None, end_date=None):
            return self._generate_mock_symbol_bars(symbol, num_bars=30, end_date_str="2026-08-25")

        self.mock_client.fetch_daily_bars.side_effect = mock_fetch_29

        provider = VnstockDataProvider(client=self.mock_client)
        result = provider.fetch_ohlcv(symbols=symbols_29)

        with self.assertRaises(ValueError) as ctx:
            build_dataset_from_records(
                records=result,
                output_dir=self.output_dir,
                provider_name="vnstock",
                universe_name="VN30",
                as_of_date="2026-08-25",
                is_live_provider=True,
            )
        self.assertIn("missing", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()
