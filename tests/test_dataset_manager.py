"""Unit tests for DatasetManager atomic staging, deep validation, and transactional rollback."""

import json
import os
import shutil
import tempfile
import unittest

from pipeline.dataset_manager import DatasetManager


class TestDatasetManager(unittest.TestCase):
    """Test suite verifying transactional staging and LKG rollback mechanism."""

    def setUp(self):
        self.workspace_root = tempfile.mkdtemp()
        self.target_dir = os.path.join(self.workspace_root, "public", "data")
        self.staging_dir = os.path.join(self.workspace_root, ".staging_data")
        self.lkg_dir = os.path.join(self.workspace_root, ".lkg_data")
        self.mgr = DatasetManager(
            workspace_root=self.workspace_root,
            target_dir=self.target_dir,
            staging_dir=self.staging_dir,
            lkg_dir=self.lkg_dir,
        )

    def tearDown(self):
        shutil.rmtree(self.workspace_root, ignore_errors=True)

    def _create_mock_valid_dataset(self, directory: str, dataset_id: str = "1234567890abcdef"):
        os.makedirs(os.path.join(directory, "symbols"), exist_ok=True)
        manifest = {
            "schema_version": "1.0.0",
            "dataset_id": dataset_id,
            "as_of_date": "2026-08-21",
            "generated_at": "2026-08-21T10:00:00Z",
            "market_timezone": "Asia/Ho_Chi_Minh",
            "market_session_status": "UNKNOWN",
            "freshness": {
                "status": "UNKNOWN",
                "expected_as_of_date": "2026-08-21",
                "reason": "Dữ liệu mẫu thử nghiệm (fixture/demo), không phải dữ liệu thị trường trực tiếp.",
            },
            "provider": "csv",
            "universe": "ALL",
            "files": {
                "overview": "overview.json",
                "screener": "screener.json",
                "symbols_base": "symbols/",
            },
            "quality": {
                "status": "PASS",
                "input_rows": 10,
                "accepted_rows": 10,
                "rejected_rows": 0,
                "eligible_symbols": 1,
                "warnings": [],
            },
        }
        overview = {
            "schema_version": "1.0.0",
            "dataset_id": dataset_id,
            "as_of_date": "2026-08-21",
            "metrics": {
                "eligible_count": 1,
                "above_count": 1,
                "above_pct": 100.0,
                "below_count": 0,
                "below_pct": 0.0,
                "on_ma10_count": 0,
                "cross_up_count": 0,
                "cross_down_count": 0,
            },
            "breadth_history": [
                {
                    "trading_date": "2026-08-21",
                    "eligible_count": 1,
                    "above_count": 1,
                    "above_pct": 100.0,
                }
            ],
        }
        screener = {
            "schema_version": "1.0.0",
            "dataset_id": dataset_id,
            "as_of_date": "2026-08-21",
            "items": [
                {
                    "symbol": "FPT",
                    "exchange": "HOSE",
                    "in_vn30": True,
                    "last_trading_date": "2026-08-21",
                    "close": 100.0,
                    "ma10": 98.0,
                    "distance_pct": 2.04,
                    "volume": 10000,
                    "avg_volume_20d": 15000,
                    "signal": "ABOVE_MA10",
                    "signal_reason": "ABOVE_MA10",
                    "data_status": "VALID",
                }
            ],
        }
        symbol_fpt = {
            "schema_version": "1.0.0",
            "dataset_id": dataset_id,
            "symbol": "FPT",
            "exchange": "HOSE",
            "in_vn30": True,
            "as_of_date": "2026-08-21",
            "latest_close": 100.0,
            "ma10": 98.0,
            "distance_pct": 2.04,
            "signal": "ABOVE_MA10",
            "signal_reason": "ABOVE_MA10",
            "avg_volume_20d": 15000,
            "is_volume_breakout": False,
            "explanation": {
                "rule": "ABOVE_MA10",
                "summary": "Giá đóng cửa nằm trên đường MA10.",
                "details": [],
            },
            "series": [
                {
                    "trading_date": "2026-08-21",
                    "open": 99.0,
                    "high": 101.0,
                    "low": 98.5,
                    "close": 100.0,
                    "volume": 10000,
                    "adjusted_close": None,
                    "trading_value": None,
                    "ma10": 98.0,
                    "distance_pct": 2.04,
                    "signal": "ABOVE_MA10",
                }
            ],
        }

        with open(os.path.join(directory, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f)
        with open(os.path.join(directory, "overview.json"), "w", encoding="utf-8") as f:
            json.dump(overview, f)
        with open(os.path.join(directory, "screener.json"), "w", encoding="utf-8") as f:
            json.dump(screener, f)
        with open(os.path.join(directory, "symbols", "FPT.json"), "w", encoding="utf-8") as f:
            json.dump(symbol_fpt, f)

    def test_workspace_boundary_and_disjoint_path_validation(self):
        """Reject paths outside workspace or overlapping directory trees."""
        # Outside workspace
        with self.assertRaises(ValueError):
            DatasetManager(
                workspace_root=self.workspace_root,
                target_dir="/tmp/outside_workspace",
            )

        # Overlapping target and staging
        with self.assertRaises(ValueError):
            DatasetManager(
                workspace_root=self.workspace_root,
                target_dir=os.path.join(self.workspace_root, "data"),
                staging_dir=os.path.join(self.workspace_root, "data", "nested_staging"),
            )

    def test_verify_staging_rejects_incomplete_dataset(self):
        self.mgr.prepare_staging()
        # Missing overview and screener
        with open(os.path.join(self.staging_dir, "manifest.json"), "w") as f:
            json.dump({"schema_version": "1.0.0"}, f)
        is_valid, errors = self.mgr.verify_staging()
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)

    def test_publish_promotes_to_target_and_creates_lkg_backup(self):
        self.mgr.prepare_staging()
        self._create_mock_valid_dataset(self.staging_dir, dataset_id="1111222233334444")

        success, errors = self.mgr.publish_from_staging()
        self.assertTrue(success, f"Publish failed with errors: {errors}")
        self.assertTrue(os.path.isfile(os.path.join(self.target_dir, "manifest.json")))
        self.assertTrue(os.path.isfile(os.path.join(self.lkg_dir, "manifest.json")))

    def test_step_by_step_rollback_recovery_with_zero_orphans(self):
        """Inject failure during step 4 (target post-validation failure) and verify perfect rollback."""
        # 1. Publish Initial Good V1
        self.mgr.prepare_staging()
        self._create_mock_valid_dataset(self.staging_dir, dataset_id="1111111111111111")
        success_v1, errors_v1 = self.mgr.publish_from_staging()
        self.assertTrue(success_v1, f"Initial publish failed: {errors_v1}")

        with open(os.path.join(self.target_dir, "manifest.json"), "r") as f:
            self.assertEqual(json.load(f)["dataset_id"], "1111111111111111")

        # 2. Stage corrupted V2 (mismatched overview dataset_id)
        self.mgr.prepare_staging()
        self._create_mock_valid_dataset(self.staging_dir, dataset_id="2222222222222222")
        with open(os.path.join(self.staging_dir, "overview.json"), "w") as f:
            json.dump({"schema_version": "1.0.0", "dataset_id": "BAD_OVERVIEW_ID"}, f)

        # 3. Publish must fail and leave Target V1 completely intact
        success, errors = self.mgr.publish_from_staging()
        self.assertFalse(success)
        self.assertGreater(len(errors), 0)

        # Target V1 is preserved
        with open(os.path.join(self.target_dir, "manifest.json"), "r") as f:
            self.assertEqual(json.load(f)["dataset_id"], "1111111111111111")

        # Zero swap orphans
        self.assertFalse(os.path.exists(self.mgr.swap_dir))

    def test_rollback_to_last_known_good(self):
        # 1. Publish V1
        self.mgr.prepare_staging()
        self._create_mock_valid_dataset(self.staging_dir, dataset_id="aaaaaaaaaaaaaaaa")
        success_v1, errors_v1 = self.mgr.publish_from_staging()
        self.assertTrue(success_v1, f"V1 publish failed: {errors_v1}")

        # 2. Corrupt target directory
        shutil.rmtree(self.target_dir)

        # 3. Rollback recovers from LKG
        success, msg = self.mgr.rollback_to_last_known_good()
        self.assertTrue(success, f"Rollback failed: {msg}")
        with open(os.path.join(self.target_dir, "manifest.json"), "r") as f:
            self.assertEqual(json.load(f)["dataset_id"], "aaaaaaaaaaaaaaaa")


if __name__ == "__main__":
    unittest.main()
