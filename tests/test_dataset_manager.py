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
from scripts.security_check import is_reparse_point_or_symlink, validate_data_directory


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

    # -------------------------------------------------------------------------
    # Comprehensive 11-point Failure Injection Test Suite
    # -------------------------------------------------------------------------

    def test_failure_injection_1_target_to_swap_move(self):
        """1. Injected failure moving target -> swap; verify target V1 restored byte-for-byte with 0 orphans."""
        self.mgr.prepare_staging()
        self._create_mock_valid_dataset(self.staging_dir, dataset_id="1111111111111111")
        self.mgr.publish_from_staging()
        v1_target_snap = self._snapshot_directory(self.target_dir)
        v1_lkg_snap = self._snapshot_directory(self.lkg_dir)

        self.mgr.prepare_staging()
        self._create_mock_valid_dataset(self.staging_dir, dataset_id="2222222222222222")

        original_move = shutil.move

        def mock_move(src, dst):
            if src == self.target_dir and dst == self.mgr.swap_dir:
                raise OSError("Injected IO failure moving target to swap")
            return original_move(src, dst)

        with patch("shutil.move", side_effect=mock_move):
            success, errors = self.mgr.publish_from_staging()
            self.assertFalse(success)

        self.assertEqual(v1_target_snap, self._snapshot_directory(self.target_dir))
        self.assertEqual(v1_lkg_snap, self._snapshot_directory(self.lkg_dir))
        self.assertFalse(os.path.exists(self.mgr.swap_dir))
        self.assertFalse(os.path.exists(self.mgr.lkg_tmp))

    def test_failure_injection_2_staging_to_target_move(self):
        """2. Injected failure moving staging -> target; verify target V1 restored byte-for-byte with 0 orphans."""
        self.mgr.prepare_staging()
        self._create_mock_valid_dataset(self.staging_dir, dataset_id="1111111111111111")
        self.mgr.publish_from_staging()
        v1_target_snap = self._snapshot_directory(self.target_dir)
        v1_lkg_snap = self._snapshot_directory(self.lkg_dir)

        self.mgr.prepare_staging()
        self._create_mock_valid_dataset(self.staging_dir, dataset_id="2222222222222222")

        original_move = shutil.move

        def mock_move(src, dst):
            if src == self.staging_dir and dst == self.target_dir:
                raise OSError("Injected IO failure moving staging to target")
            return original_move(src, dst)

        with patch("shutil.move", side_effect=mock_move):
            success, errors = self.mgr.publish_from_staging()
            self.assertFalse(success)

        self.assertEqual(v1_target_snap, self._snapshot_directory(self.target_dir))
        self.assertEqual(v1_lkg_snap, self._snapshot_directory(self.lkg_dir))
        self.assertFalse(os.path.exists(self.mgr.swap_dir))
        self.assertFalse(os.path.exists(self.mgr.lkg_tmp))

    def test_failure_injection_3_target_post_validation(self):
        """3. Injected failure during post-move target deep validation; verify target V1 restored byte-for-byte."""
        self.mgr.prepare_staging()
        self._create_mock_valid_dataset(self.staging_dir, dataset_id="1111111111111111")
        self.mgr.publish_from_staging()
        v1_target_snap = self._snapshot_directory(self.target_dir)
        v1_lkg_snap = self._snapshot_directory(self.lkg_dir)

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

        self.assertEqual(v1_target_snap, self._snapshot_directory(self.target_dir))
        self.assertEqual(v1_lkg_snap, self._snapshot_directory(self.lkg_dir))
        self.assertFalse(os.path.exists(self.mgr.swap_dir))

    def test_failure_injection_4_target_to_lkg_tmp_copy(self):
        """4. Injected failure copying target -> lkg_tmp; verify target V1 restored byte-for-byte with 0 orphans."""
        self.mgr.prepare_staging()
        self._create_mock_valid_dataset(self.staging_dir, dataset_id="1111111111111111")
        self.mgr.publish_from_staging()
        v1_target_snap = self._snapshot_directory(self.target_dir)
        v1_lkg_snap = self._snapshot_directory(self.lkg_dir)

        self.mgr.prepare_staging()
        self._create_mock_valid_dataset(self.staging_dir, dataset_id="2222222222222222")

        with patch("shutil.copytree", side_effect=IOError("Injected failure copying target to lkg_tmp")):
            success, errors = self.mgr.publish_from_staging()
            self.assertFalse(success)

        self.assertEqual(v1_target_snap, self._snapshot_directory(self.target_dir))
        self.assertEqual(v1_lkg_snap, self._snapshot_directory(self.lkg_dir))
        self.assertFalse(os.path.exists(self.mgr.swap_dir))
        self.assertFalse(os.path.exists(self.mgr.lkg_tmp))

    def test_failure_injection_5_lkg_tmp_validation(self):
        """5. Injected validation failure on lkg_tmp candidate; verify target V1 and LKG V1 restored byte-for-byte."""
        self.mgr.prepare_staging()
        self._create_mock_valid_dataset(self.staging_dir, dataset_id="1111111111111111")
        self.mgr.publish_from_staging()
        v1_target_snap = self._snapshot_directory(self.target_dir)
        v1_lkg_snap = self._snapshot_directory(self.lkg_dir)

        self.mgr.prepare_staging()
        self._create_mock_valid_dataset(self.staging_dir, dataset_id="2222222222222222")

        original_verify = self.mgr._verify_directory

        def mock_verify(dir_path):
            if os.path.abspath(dir_path) == os.path.abspath(self.mgr.lkg_tmp):
                return False, ["Injected lkg_tmp candidate validation failure"]
            return original_verify(dir_path)

        with patch.object(self.mgr, "_verify_directory", side_effect=mock_verify):
            success, errors = self.mgr.publish_from_staging()
            self.assertFalse(success)
            self.assertTrue(any("Injected lkg_tmp candidate validation failure" in e for e in errors))

        self.assertEqual(v1_target_snap, self._snapshot_directory(self.target_dir))
        self.assertEqual(v1_lkg_snap, self._snapshot_directory(self.lkg_dir))
        self.assertFalse(os.path.exists(self.mgr.swap_dir))
        self.assertFalse(os.path.exists(self.mgr.lkg_tmp))

    def test_failure_injection_6_lkg_to_lkg_swap_move(self):
        """6. Injected failure moving old LKG -> lkg_swap; verify target V1 and LKG V1 restored byte-for-byte."""
        self.mgr.prepare_staging()
        self._create_mock_valid_dataset(self.staging_dir, dataset_id="1111111111111111")
        self.mgr.publish_from_staging()
        v1_target_snap = self._snapshot_directory(self.target_dir)
        v1_lkg_snap = self._snapshot_directory(self.lkg_dir)

        self.mgr.prepare_staging()
        self._create_mock_valid_dataset(self.staging_dir, dataset_id="2222222222222222")

        original_move = shutil.move

        def mock_move(src, dst):
            if src == self.lkg_dir and dst == self.mgr.lkg_swap:
                raise OSError("Injected IO failure moving old LKG to lkg_swap")
            return original_move(src, dst)

        with patch("shutil.move", side_effect=mock_move):
            success, errors = self.mgr.publish_from_staging()
            self.assertFalse(success)

        self.assertEqual(v1_target_snap, self._snapshot_directory(self.target_dir))
        self.assertEqual(v1_lkg_snap, self._snapshot_directory(self.lkg_dir))
        self.assertFalse(os.path.exists(self.mgr.swap_dir))
        self.assertFalse(os.path.exists(self.mgr.lkg_tmp))

    def test_failure_injection_7_lkg_tmp_to_lkg_promotion(self):
        """7. Injected failure moving lkg_tmp -> lkg_dir; verify target V1 and LKG V1 restored byte-for-byte."""
        self.mgr.prepare_staging()
        self._create_mock_valid_dataset(self.staging_dir, dataset_id="1111111111111111")
        self.mgr.publish_from_staging()
        v1_target_snap = self._snapshot_directory(self.target_dir)
        v1_lkg_snap = self._snapshot_directory(self.lkg_dir)

        self.mgr.prepare_staging()
        self._create_mock_valid_dataset(self.staging_dir, dataset_id="2222222222222222")

        original_move = shutil.move

        def mock_move(src, dst):
            if src == self.mgr.lkg_tmp and dst == self.lkg_dir:
                raise OSError("Injected IO failure promoting lkg_tmp to lkg_dir")
            return original_move(src, dst)

        with patch("shutil.move", side_effect=mock_move):
            success, errors = self.mgr.publish_from_staging()
            self.assertFalse(success)

        self.assertEqual(v1_target_snap, self._snapshot_directory(self.target_dir))
        self.assertEqual(v1_lkg_snap, self._snapshot_directory(self.lkg_dir))
        self.assertFalse(os.path.exists(self.mgr.swap_dir))
        self.assertFalse(os.path.exists(self.mgr.lkg_tmp))

    def test_failure_injection_8_lkg_swap_cleanup_no_split_brain(self):
        """8. Reproduction test: Injected failure cleaning lkg_swap post-commit must NOT cause split-brain (Target=V2, LKG=V2), reports warning, and recovers next run."""
        self.mgr.prepare_staging()
        self._create_mock_valid_dataset(self.staging_dir, dataset_id="1111111111111111")
        self.mgr.publish_from_staging()

        self.mgr.prepare_staging()
        self._create_mock_valid_dataset(self.staging_dir, dataset_id="2222222222222222")
        v2_staging_snap = self._snapshot_directory(self.staging_dir)

        original_rmtree = shutil.rmtree

        def mock_rmtree(path, ignore_errors=False):
            if os.path.abspath(path) == os.path.abspath(self.mgr.lkg_swap):
                raise OSError("Injected permission error during post-commit lkg_swap cleanup")
            return original_rmtree(path, ignore_errors=ignore_errors)

        with patch("shutil.rmtree", side_effect=mock_rmtree):
            success, warnings = self.mgr.publish_from_staging()
            # Must succeed because commit point was already reached
            self.assertTrue(success)
            self.assertEqual(warnings, ["Post-commit warning: temporary recovery directory cleanup incomplete"])

        # Assert BOTH target and LKG are on V2 (ZERO SPLIT-BRAIN)
        target_snap = self._snapshot_directory(self.target_dir)
        lkg_snap = self._snapshot_directory(self.lkg_dir)
        self.assertEqual(target_snap, lkg_snap, "Target and LKG must have identical byte snapshot on V2")
        self.assertEqual(v2_staging_snap, target_snap, "Target must be V2")
        # Assert orphan directory exists
        self.assertTrue(os.path.exists(self.mgr.lkg_swap))

        # Subsequent transaction: Once failure condition is cleared, next publish cleans stale recovery dir and succeeds cleanly
        self.mgr.prepare_staging()
        self._create_mock_valid_dataset(self.staging_dir, dataset_id="3333333333333333")
        success_v3, warnings_v3 = self.mgr.publish_from_staging()
        self.assertTrue(success_v3)
        self.assertEqual(warnings_v3, [])
        self.assertFalse(os.path.exists(self.mgr.lkg_swap))

    def test_failure_injection_9_target_swap_cleanup_no_split_brain(self):
        """9. Injected failure cleaning swap_dir post-commit must NOT cause split-brain (Target=V2, LKG=V2), reports warning, and recovers next run."""
        self.mgr.prepare_staging()
        self._create_mock_valid_dataset(self.staging_dir, dataset_id="1111111111111111")
        self.mgr.publish_from_staging()

        self.mgr.prepare_staging()
        self._create_mock_valid_dataset(self.staging_dir, dataset_id="2222222222222222")
        v2_staging_snap = self._snapshot_directory(self.staging_dir)

        original_rmtree = shutil.rmtree

        def mock_rmtree(path, ignore_errors=False):
            if os.path.abspath(path) == os.path.abspath(self.mgr.swap_dir):
                raise OSError("Injected permission error during post-commit swap_dir cleanup")
            return original_rmtree(path, ignore_errors=ignore_errors)

        with patch("shutil.rmtree", side_effect=mock_rmtree):
            success, warnings = self.mgr.publish_from_staging()
            self.assertTrue(success)
            self.assertEqual(warnings, ["Post-commit warning: temporary recovery directory cleanup incomplete"])

        target_snap = self._snapshot_directory(self.target_dir)
        lkg_snap = self._snapshot_directory(self.lkg_dir)
        self.assertEqual(target_snap, lkg_snap)
        self.assertEqual(v2_staging_snap, target_snap)
        self.assertTrue(os.path.exists(self.mgr.swap_dir))

        # Subsequent transaction recovers
        self.mgr.prepare_staging()
        self._create_mock_valid_dataset(self.staging_dir, dataset_id="3333333333333333")
        success_v3, warnings_v3 = self.mgr.publish_from_staging()
        self.assertTrue(success_v3)
        self.assertEqual(warnings_v3, [])
        self.assertFalse(os.path.exists(self.mgr.swap_dir))

    def test_persistent_cleanup_failure_causes_fail_closed_transaction(self):
        """Persistent failure to clean stale recovery directory aborts new transaction before modifying target."""
        self.mgr.prepare_staging()
        self._create_mock_valid_dataset(self.staging_dir, dataset_id="1111111111111111")
        self.mgr.publish_from_staging()
        v1_target_snap = self._snapshot_directory(self.target_dir)

        # Create un-deletable stale recovery directory
        os.makedirs(self.mgr.swap_dir, exist_ok=True)

        original_rmtree = shutil.rmtree

        def unremovable_rmtree(path, ignore_errors=False):
            if os.path.abspath(path) == os.path.abspath(self.mgr.swap_dir):
                pass  # Cannot delete
            else:
                original_rmtree(path, ignore_errors=ignore_errors)

        self.mgr.prepare_staging()
        self._create_mock_valid_dataset(self.staging_dir, dataset_id="2222222222222222")

        with patch("shutil.rmtree", side_effect=unremovable_rmtree):
            success, errors = self.mgr.publish_from_staging()
            self.assertFalse(success)
            self.assertEqual(errors, ["Persistent stale recovery directory could not be cleaned"])

        # Target was never touched or corrupted
        self.assertEqual(v1_target_snap, self._snapshot_directory(self.target_dir))

    def test_rollback_persistent_stale_swap_aborts_fail_closed(self):
        """A. Persistent stale swap directory causes rollback to abort fail-closed before touching target or calling copytree."""
        self.mgr.prepare_staging()
        self._create_mock_valid_dataset(self.staging_dir, dataset_id="1111111111111111")
        self.mgr.publish_from_staging()
        v1_target_snap = self._snapshot_directory(self.target_dir)

        # Create un-deletable stale swap directory with a dummy file
        os.makedirs(self.mgr.swap_dir, exist_ok=True)
        stale_file = os.path.join(self.mgr.swap_dir, "stale.txt")
        with open(stale_file, "w", encoding="utf-8") as f:
            f.write("stale swap content")

        original_rmtree = shutil.rmtree

        def unremovable_rmtree(path, ignore_errors=False):
            if os.path.abspath(path) == os.path.abspath(self.mgr.swap_dir):
                pass  # Cannot delete
            else:
                original_rmtree(path, ignore_errors=ignore_errors)

        copytree_called = False
        original_copytree = shutil.copytree

        def track_copytree(src, dst):
            nonlocal copytree_called
            copytree_called = True
            return original_copytree(src, dst)

        with patch("shutil.rmtree", side_effect=unremovable_rmtree), patch("shutil.copytree", side_effect=track_copytree):
            success, msg = self.mgr.rollback_to_last_known_good()
            self.assertFalse(success)
            self.assertEqual(msg, "Persistent stale recovery directory could not be cleaned")
            self.assertFalse(copytree_called, "copytree must NEVER be called if swap is stale and un-deletable")

        # Target snapshot is byte-for-byte unchanged
        self.assertEqual(v1_target_snap, self._snapshot_directory(self.target_dir))
        # Ensure no nested target directory inside swap
        self.assertFalse(os.path.exists(os.path.join(self.mgr.swap_dir, os.path.basename(self.target_dir))))

    def test_rollback_transient_stale_swap_cleans_and_succeeds(self):
        """B. Transient stale swap directory is cleaned up by rollback before restoring LKG."""
        self.mgr.prepare_staging()
        self._create_mock_valid_dataset(self.staging_dir, dataset_id="1111111111111111")
        self.mgr.publish_from_staging()

        # Update target with V2
        self.mgr.prepare_staging()
        self._create_mock_valid_dataset(self.staging_dir, dataset_id="2222222222222222")
        self.mgr.publish_from_staging()
        v2_lkg_snap = self._snapshot_directory(self.lkg_dir)

        # Create transient deletable swap directory
        os.makedirs(self.mgr.swap_dir, exist_ok=True)
        with open(os.path.join(self.mgr.swap_dir, "transient.txt"), "w", encoding="utf-8") as f:
            f.write("transient stale swap")

        success, msg = self.mgr.rollback_to_last_known_good()
        self.assertTrue(success)
        self.assertEqual(self._snapshot_directory(self.target_dir), v2_lkg_snap)
        self.assertFalse(os.path.exists(self.mgr.swap_dir))

    def test_failure_injection_10_rollback_copy_failure(self):
        """10. Injected failure during LKG rollback copy restores original target byte-for-byte with no nested path corruption."""
        self.mgr.prepare_staging()
        self._create_mock_valid_dataset(self.staging_dir, dataset_id="aaaaaaaaaaaaaaaa")
        self.mgr.publish_from_staging()
        target_v1_snap = self._snapshot_directory(self.target_dir)

        with patch("shutil.copytree", side_effect=IOError("Injected failure during rollback copytree")):
            success, msg = self.mgr.rollback_to_last_known_good()
            self.assertFalse(success)

        # Target restored to previous state byte-for-byte
        self.assertEqual(target_v1_snap, self._snapshot_directory(self.target_dir))
        self.assertFalse(os.path.exists(self.mgr.swap_dir))
        self.assertFalse(os.path.exists(os.path.join(self.target_dir, os.path.basename(self.target_dir))))

    def test_failure_injection_11_rollback_post_validation_failure(self):
        """11. Injected validation failure during LKG restoration restores previous target byte-for-byte."""
        self.mgr.prepare_staging()
        self._create_mock_valid_dataset(self.staging_dir, dataset_id="aaaaaaaaaaaaaaaa")
        self.mgr.publish_from_staging()
        target_v1_snap = self._snapshot_directory(self.target_dir)

        original_verify = self.mgr._verify_directory

        def mock_verify(dir_path):
            if os.path.abspath(dir_path) == os.path.abspath(self.target_dir):
                return False, ["Injected post-restoration target validation failure"]
            return original_verify(dir_path)

    def test_rollback_partial_copytree_cleanup_failure_preserves_swap_byte_for_byte(self):
        """A. Injected copytree failure creating partial target where cleanup raises preserves swap_dir byte-for-byte without nesting."""
        self.mgr.prepare_staging()
        self._create_mock_valid_dataset(self.staging_dir, dataset_id="1111111111111111")
        self.mgr.publish_from_staging()
        v1_target_snap = self._snapshot_directory(self.target_dir)

        # Update target with V2
        self.mgr.prepare_staging()
        self._create_mock_valid_dataset(self.staging_dir, dataset_id="2222222222222222")
        self.mgr.publish_from_staging()
        v2_target_snap = self._snapshot_directory(self.target_dir)

        def failing_copytree(src, dst):
            os.makedirs(dst, exist_ok=True)
            with open(os.path.join(dst, "partial.txt"), "w", encoding="utf-8") as f:
                f.write("partial content")
            raise IOError("Injected copytree failure after writing partial target")

        original_rmtree = shutil.rmtree

        def failing_rmtree(path, ignore_errors=False):
            if os.path.abspath(path) == os.path.abspath(self.target_dir):
                raise IOError("Injected rmtree failure on partial target")
            return original_rmtree(path, ignore_errors=ignore_errors)

        with patch("shutil.copytree", side_effect=failing_copytree), patch("shutil.rmtree", side_effect=failing_rmtree):
            success, msg = self.mgr.rollback_to_last_known_good()
            self.assertFalse(success)
            self.assertEqual(msg, "LKG rollback failed: partial target directory could not be removed for recovery")

        # swap_dir still exists and contains the exact V2 target snapshot byte-for-byte
        self.assertTrue(os.path.exists(self.mgr.swap_dir))
        self.assertEqual(self._snapshot_directory(self.mgr.swap_dir), v2_target_snap)
        # swap_dir is NOT nested under target_dir
        self.assertFalse(os.path.exists(os.path.join(self.target_dir, os.path.basename(self.mgr.swap_dir))))

    def test_rollback_partial_cleanup_noop_preserves_swap_byte_for_byte(self):
        """B. Injected copytree failure where partial target cleanup is a no-op preserves swap_dir without nesting."""
        self.mgr.prepare_staging()
        self._create_mock_valid_dataset(self.staging_dir, dataset_id="1111111111111111")
        self.mgr.publish_from_staging()

        self.mgr.prepare_staging()
        self._create_mock_valid_dataset(self.staging_dir, dataset_id="2222222222222222")
        self.mgr.publish_from_staging()
        v2_target_snap = self._snapshot_directory(self.target_dir)

        def failing_copytree(src, dst):
            os.makedirs(dst, exist_ok=True)
            with open(os.path.join(dst, "partial.txt"), "w", encoding="utf-8") as f:
                f.write("partial content")
            raise IOError("Injected copytree failure after writing partial target")

        original_rmtree = shutil.rmtree

        def noop_rmtree(path, ignore_errors=False):
            if os.path.abspath(path) == os.path.abspath(self.target_dir):
                pass  # No-op, leaves target_dir intact
            else:
                original_rmtree(path, ignore_errors=ignore_errors)

        with patch("shutil.copytree", side_effect=failing_copytree), patch("shutil.rmtree", side_effect=noop_rmtree):
            success, msg = self.mgr.rollback_to_last_known_good()
            self.assertFalse(success)
            self.assertEqual(msg, "LKG rollback failed: partial target directory could not be removed for recovery")

        self.assertTrue(os.path.exists(self.mgr.swap_dir))
        self.assertEqual(self._snapshot_directory(self.mgr.swap_dir), v2_target_snap)
        self.assertFalse(os.path.exists(os.path.join(self.target_dir, os.path.basename(self.mgr.swap_dir))))

    def test_rollback_restore_move_failure_preserves_swap(self):
        """D. Injected failure during restore move leaves swap_dir intact with original target for retry/manual recovery."""
        self.mgr.prepare_staging()
        self._create_mock_valid_dataset(self.staging_dir, dataset_id="1111111111111111")
        self.mgr.publish_from_staging()

        self.mgr.prepare_staging()
        self._create_mock_valid_dataset(self.staging_dir, dataset_id="2222222222222222")
        self.mgr.publish_from_staging()
        v2_target_snap = self._snapshot_directory(self.target_dir)

        original_move = shutil.move

        def failing_restore_move(src, dst):
            if os.path.abspath(src) == os.path.abspath(self.mgr.swap_dir) and os.path.abspath(dst) == os.path.abspath(self.target_dir):
                raise IOError("Injected move failure during target restore")
            return original_move(src, dst)

        with patch("shutil.copytree", side_effect=IOError("Injected copytree failure")), patch("shutil.move", side_effect=failing_restore_move):
            success, msg = self.mgr.rollback_to_last_known_good()
            self.assertFalse(success)
            self.assertEqual(msg, "LKG rollback failed and target restoration failed")

        # Recovery swap remains intact with original V2 target snapshot
        self.assertTrue(os.path.exists(self.mgr.swap_dir))
        self.assertEqual(self._snapshot_directory(self.mgr.swap_dir), v2_target_snap)


if __name__ == "__main__":
    unittest.main()
