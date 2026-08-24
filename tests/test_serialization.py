"""Tests for JSON serialization and dataset building."""

import json
import os
import shutil
import unittest
from pipeline.build_dataset import build_dataset_from_records
from pipeline.providers.csv_provider import CsvDataProvider


class TestSerialization(unittest.TestCase):

    def setUp(self):
        self.output_dir = "tests/temp_data"
        self.staging_dir = "tests/temp_staging"

    def tearDown(self):
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)
        if os.path.exists(self.staging_dir):
            shutil.rmtree(self.staging_dir)

    def test_build_and_serialize_deterministic_dataset(self):
        provider = CsvDataProvider("tests/fixtures/sample_ohlcv.csv")
        records = provider.fetch_ohlcv()
        dataset_id = build_dataset_from_records(
            records=records,
            output_dir=self.output_dir,
            staging_dir=self.staging_dir,
            as_of_date="2026-08-21",
        )

        manifest_path = os.path.join(self.output_dir, "manifest.json")
        overview_path = os.path.join(self.output_dir, "overview.json")
        screener_path = os.path.join(self.output_dir, "screener.json")
        symbols_dir = os.path.join(self.output_dir, "symbols")

        self.assertTrue(os.path.exists(manifest_path))
        self.assertTrue(os.path.exists(overview_path))
        self.assertTrue(os.path.exists(screener_path))
        self.assertTrue(os.path.exists(symbols_dir))

        # Check manifest content
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_json = json.load(f)
            self.assertEqual(manifest_json["schema_version"], "1.0.0")
            self.assertEqual(manifest_json["as_of_date"], "2026-08-21")
            self.assertEqual(manifest_json["quality"]["status"], "PASS")

        # Check cross-file dataset_id consistency
        with open(overview_path, "r", encoding="utf-8") as f:
            overview_json = json.load(f)
            self.assertEqual(overview_json["dataset_id"], dataset_id)
            self.assertEqual(overview_json["as_of_date"], "2026-08-21")

        with open(screener_path, "r", encoding="utf-8") as f:
            screener_json = json.load(f)
            self.assertEqual(screener_json["dataset_id"], dataset_id)
            self.assertEqual(screener_json["as_of_date"], "2026-08-21")
            self.assertGreater(len(screener_json["items"]), 0)

        # Check FPT symbol file
        fpt_path = os.path.join(symbols_dir, "FPT.json")
        self.assertTrue(os.path.exists(fpt_path))
        with open(fpt_path, "r", encoding="utf-8") as f:
            fpt_json = json.load(f)
            self.assertEqual(fpt_json["dataset_id"], dataset_id)
            self.assertEqual(fpt_json["symbol"], "FPT")
            self.assertIn("series", fpt_json)
            self.assertIn("explanation", fpt_json)


if __name__ == "__main__":
    unittest.main()
