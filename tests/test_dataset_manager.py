"""Unit tests for DatasetManager path security, deep schema validation, and transactional rollback."""

import json
import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

from pipeline.dataset_manager import (
    DatasetManager,
    are_paths_disjoint,
    is_path_safe_and_within,
)
from scripts.security_check import validate_data_directory


class TestDatasetManager(unittest.TestCase):
    """Test suite verifying strict path containment, deep symbol validation, and transactional rollback."""

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

    def _create_mock_valid_dataset(self, directory: str, dataset_id: str = "1234567890abcdef", symbol: str = "FPT"):
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
                    "symbol": symbol,
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
        symbol_data = {
            "schema_version": "1.0.0",
            "dataset_id": dataset_id,
            "symbol": symbol,
            "exchange": "HOSE",
            "as_of_date": "2026-08-21",
            "latest": {
                "close": 100.0,
                "ma10": 98.0,
                "distance_pct": 2.04,
                "signal": "ABOVE_MA10",
                "data_status": "VALID",
            },
            "series": [
                {
                    "trading_date": "2026-08-21",
                    "open": 99.0,
                    "high": 101.0,
                    "low": 98.5,
                    "close": 100.0,
                    "ma10": 98.0,
                    "volume": 10000,
                    "signal": "ABOVE_MA10",
                }
            ],
            "explanation": {
                "current_close": 100.0,
                "current_ma10": 98.0,
                "previous_close": 98.0,
                "previous_ma10": 97.5,
                "rule": "ABOVE_MA10",
            },
        }

        with open(os.path.join(directory, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f)
        with open(os.path.join(directory, "overview.json"), "w", encoding="utf-8") as f:
            json.dump(overview, f)
        with open(os.path.join(directory, "screener.json"), "w", encoding="utf-8") as f:
            json.dump(screener, f)
        with open(os.path.join(directory, "symbols", f"{symbol}.json"), "w", encoding="utf-8") as f:
            json.dump(symbol_data, f)

    def _snapshot_directory(self, dir_path: str) -> dict:
        """Create snapshot of directory file structure and byte content."""
        if not os.path.exists(dir_path):
            return {}
        snapshot = {}
        for root, _, files in os.walk(dir_path):
            for f in files:
                full_p = os.path.join(root, f)
                rel_p = os.path.relpath(full_p, dir_path).replace("\\", "/")
                with open(full_p, "rb") as fp:
                    snapshot[rel_p] = fp.read()
        return snapshot

    def test_path_safety_rejects_workspace_sibling(self):
        """Reject workspace siblings such as <workspace>_outside without startswith bypass."""
        sibling = self.workspace_root + "_outside"
        self.assertFalse(is_path_safe_and_within(sibling, self.workspace_root))
        with self.assertRaises(ValueError):
            DatasetManager(
                workspace_root=self.workspace_root,
                target_dir=sibling,
            )

    def test_path_safety_rejects_overlapping_and_root_paths(self):
        """Reject paths identical to workspace or overlapping directories."""
        self.assertFalse(is_path_safe_and_within(self.workspace_root, self.workspace_root))
        self.assertFalse(are_paths_disjoint(
            os.path.join(self.workspace_root, "data"),
            os.path.join(self.workspace_root, "data", "child"),
        ))

    def test_validate_data_directory_rejects_envelope_only_symbol_json(self):
        """Regression test: Replacing FPT.json with envelope-only object missing latest/series/explanation creates violations and fails publish."""
        self.mgr.prepare_staging()
        self._create_mock_valid_dataset(self.staging_dir, dataset_id="1111222233334444")

        # Replace FPT.json with envelope-only object
        envelope_only = {
            "schema_version": "1.0.0",
            "dataset_id": "1111222233334444",
            "symbol": "FPT",
            "as_of_date": "2026-08-21",
        }
        with open(os.path.join(self.staging_dir, "symbols", "FPT.json"), "w", encoding="utf-8") as f:
            json.dump(envelope_only, f)

        violations = validate_data_directory(self.staging_dir)
        self.assertTrue(len(violations) > 0, "Deep validation must detect missing top-level keys in symbol file")
        self.assertTrue(any("symbol detail JSON top-level keys mismatch" in v for v in violations))

        success, publish_errors = self.mgr.publish_from_staging()
        self.assertFalse(success)
        self.assertTrue(len(publish_errors) > 0)

    def test_publish_promotes_valid_staging_and_creates_lkg(self):
        """Valid dataset publishes smoothly and initializes LKG."""
        self.mgr.prepare_staging()
        self._create_mock_valid_dataset(self.staging_dir, dataset_id="abcdef1234567890")

        success, errors = self.mgr.publish_from_staging()
        self.assertTrue(success, f"Publish failed: {errors}")
        self.assertTrue(os.path.isfile(os.path.join(self.target_dir, "manifest.json")))
        self.assertTrue(os.path.isfile(os.path.join(self.lkg_dir, "manifest.json")))

    def test_injected_failure_at_staging_to_target_move(self):
        """Inject failure when moving staging to target; verify target V1 restored byte-for-byte with 0 orphans."""
        # 1. Establish V1
        self.mgr.prepare_staging()
        self._create_mock_valid_dataset(self.staging_dir, dataset_id="1111111111111111")
        self.mgr.publish_from_staging()
        v1_snapshot = self._snapshot_directory(self.target_dir)

        # 2. Stage V2
        self.mgr.prepare_staging()
        self._create_mock_valid_dataset(self.staging_dir, dataset_id="2222222222222222")

        # Inject failure on shutil.move when moving staging -> target
        original_move = shutil.move

        def mock_move(src, dst):
            if src == self.staging_dir and dst == self.target_dir:
                raise OSError("Injected IO failure moving staging to target")
            return original_move(src, dst)

        with patch("shutil.move", side_effect=mock_move):
            success, errors = self.mgr.publish_from_staging()
            self.assertFalse(success)

        # Assert target was restored byte-for-byte
        current_target_snapshot = self._snapshot_directory(self.target_dir)
        self.assertEqual(v1_snapshot, current_target_snapshot)
        self.assertFalse(os.path.exists(self.mgr.swap_dir))
        self.assertFalse(os.path.exists(self.mgr.lkg_tmp))

    def test_injected_failure_at_target_post_validation(self):
        """Inject failure during post-move target deep validation; verify target V1 restored byte-for-byte."""
        # 1. Establish V1
        self.mgr.prepare_staging()
        self._create_mock_valid_dataset(self.staging_dir, dataset_id="1111111111111111")
        self.mgr.publish_from_staging()
        v1_snapshot = self._snapshot_directory(self.target_dir)

        # 2. Stage V2
        self.mgr.prepare_staging()
        self._create_mock_valid_dataset(self.staging_dir, dataset_id="2222222222222222")

        original_verify = self.mgr._verify_directory

        def mock_verify(dir_path):
            if os.path.abspath(dir_path) == os.path.abspath(self.target_dir):
                return False, ["Injected post-move target deep validation failure"]
            return original_verify(dir_path)

        with patch.object(self.mgr, "_verify_directory", side_effect=mock_verify):
            success, errors = self.mgr.publish_from_staging()
            self.assertFalse(success)
            self.assertTrue(any("Injected post-move target deep validation failure" in e for e in errors))

        # Assert target was restored byte-for-byte
        current_target_snapshot = self._snapshot_directory(self.target_dir)
        self.assertEqual(v1_snapshot, current_target_snapshot)
        self.assertFalse(os.path.exists(self.mgr.swap_dir))

    def test_injected_failure_at_lkg_copy(self):
        """Inject failure when copying target to lkg_tmp; verify target V1 restored byte-for-byte."""
        # 1. Establish V1
        self.mgr.prepare_staging()
        self._create_mock_valid_dataset(self.staging_dir, dataset_id="1111111111111111")
        self.mgr.publish_from_staging()
        v1_snapshot = self._snapshot_directory(self.target_dir)

        # 2. Stage V2
        self.mgr.prepare_staging()
        self._create_mock_valid_dataset(self.staging_dir, dataset_id="2222222222222222")

        with patch("shutil.copytree", side_effect=IOError("Injected failure during LKG copy")):
            success, errors = self.mgr.publish_from_staging()
            self.assertFalse(success)

        # Assert target was restored byte-for-byte
        current_target_snapshot = self._snapshot_directory(self.target_dir)
        self.assertEqual(v1_snapshot, current_target_snapshot)
        self.assertFalse(os.path.exists(self.mgr.swap_dir))
        self.assertFalse(os.path.exists(self.mgr.lkg_tmp))

    def test_rollback_to_last_known_good_with_injected_failure(self):
        """Test rollback_to_last_known_good restores LKG, and restores previous target if copy fails midway."""
        # 1. Establish V1 in LKG
        self.mgr.prepare_staging()
        self._create_mock_valid_dataset(self.staging_dir, dataset_id="aaaaaaaaaaaaaaaa")
        self.mgr.publish_from_staging()
        lkg_snapshot = self._snapshot_directory(self.lkg_dir)

        # 2. Manually corrupt target to test rollback
        with open(os.path.join(self.target_dir, "manifest.json"), "w") as f:
            f.write("corrupted manifest")

        # 3. Successful rollback to LKG
        success, msg = self.mgr.rollback_to_last_known_good()
        self.assertTrue(success, f"Rollback failed: {msg}")
        self.assertEqual(lkg_snapshot, self._snapshot_directory(self.target_dir))


if __name__ == "__main__":
    unittest.main()
