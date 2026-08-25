"""Unit tests for DatasetManager atomic staging, validation, and Last-Known-Good rollback."""

import json
import os
import shutil
import tempfile
import unittest

from pipeline.dataset_manager import DatasetManager


class TestDatasetManager(unittest.TestCase):
    """Test suite verifying transactional staging and LKG rollback mechanism."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.target_dir = os.path.join(self.test_dir, "data")
        self.staging_dir = os.path.join(self.test_dir, ".staging_data")
        self.lkg_dir = os.path.join(self.test_dir, ".lkg_data")
        self.mgr = DatasetManager(
            target_dir=self.target_dir,
            staging_dir=self.staging_dir,
            lkg_dir=self.lkg_dir,
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _create_mock_dataset(self, directory: str, dataset_id: str = "1234567890abcdef"):
        os.makedirs(os.path.join(directory, "symbols"), exist_ok=True)
        manifest = {"schema_version": "1.0.0", "dataset_id": dataset_id}
        overview = {"schema_version": "1.0.0", "dataset_id": dataset_id}
        screener = {"schema_version": "1.0.0", "dataset_id": dataset_id, "items": []}
        symbol_fpt = {"schema_version": "1.0.0", "dataset_id": dataset_id, "symbol": "FPT"}

        with open(os.path.join(directory, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f)
        with open(os.path.join(directory, "overview.json"), "w", encoding="utf-8") as f:
            json.dump(overview, f)
        with open(os.path.join(directory, "screener.json"), "w", encoding="utf-8") as f:
            json.dump(screener, f)
        with open(os.path.join(directory, "symbols", "FPT.json"), "w", encoding="utf-8") as f:
            json.dump(symbol_fpt, f)

    def test_prepare_staging_creates_clean_dir(self):
        stg = self.mgr.prepare_staging()
        self.assertTrue(os.path.isdir(stg))
        self.assertEqual(len(os.listdir(stg)), 0)

    def test_verify_staging_valid_and_invalid(self):
        self.mgr.prepare_staging()
        # Empty staging -> invalid
        is_valid, errors = self.mgr.verify_staging()
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)

        # Complete valid staging -> valid
        self._create_mock_dataset(self.staging_dir, dataset_id="1111222233334444")
        is_valid, errors = self.mgr.verify_staging()
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_publish_promotes_to_target_and_creates_lkg_backup(self):
        self.mgr.prepare_staging()
        self._create_mock_dataset(self.staging_dir, dataset_id="aaaabbbbccccdddd")

        published = self.mgr.publish_from_staging()
        self.assertTrue(published)
        self.assertTrue(os.path.isfile(os.path.join(self.target_dir, "manifest.json")))
        self.assertTrue(os.path.isfile(os.path.join(self.lkg_dir, "manifest.json")))

    def test_rollback_to_last_known_good(self):
        # 1. Publish valid dataset V1
        self.mgr.prepare_staging()
        self._create_mock_dataset(self.staging_dir, dataset_id="1111111111111111")
        self.mgr.publish_from_staging()

        with open(os.path.join(self.target_dir, "manifest.json"), "r") as f:
            self.assertEqual(json.load(f)["dataset_id"], "1111111111111111")

        # 2. Corrupt or delete target directory to simulate failure
        shutil.rmtree(self.target_dir)

        # 3. Rollback recovers V1 from LKG
        rolled_back = self.mgr.rollback_to_last_known_good()
        self.assertTrue(rolled_back)
        with open(os.path.join(self.target_dir, "manifest.json"), "r") as f:
            self.assertEqual(json.load(f)["dataset_id"], "1111111111111111")


if __name__ == "__main__":
    unittest.main()
