"""Tests for JSON serialization, transactional directory replacement, safety targets, and deterministic reproducibility."""

from __future__ import annotations

import json
import math
import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

from pipeline.build_dataset import build_dataset_from_records
from pipeline.providers.csv_provider import CsvDataProvider
from pipeline.serialization import (
    DataIntegrityError,
    FilesystemSafetyError,
    sanitize_value,
    serialize_dataset,
    validate_no_directory_overlap,
    validate_target_directory,
)


class TestSerialization(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_serialization_")
        self.workspace_root = os.path.join(self.temp_dir, "workspace")
        self.output_dir = os.path.join(self.workspace_root, "frontend", "public", "data")
        self.staging_dir = os.path.join(self.workspace_root, ".staging_data")
        os.makedirs(self.workspace_root, exist_ok=True)

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _snapshot_directory_tree(self, dir_path: str) -> dict[str, bytes]:
        """Snapshot all file relative paths and their exact byte contents."""
        tree = {}
        for root, _, files in os.walk(dir_path):
            for f in files:
                full_p = os.path.join(root, f)
                rel_p = os.path.relpath(full_p, dir_path).replace("\\", "/")
                with open(full_p, "rb") as fp:
                    tree[rel_p] = fp.read()
        return tree

    def test_build_and_serialize_deterministic_dataset(self):
        provider = CsvDataProvider("tests/fixtures/sample_ohlcv.csv")
        records = provider.fetch_ohlcv()
        dataset_id = build_dataset_from_records(
            records=records,
            output_dir=self.output_dir,
            staging_dir=self.staging_dir,
            as_of_date="2026-08-21",
            fixed_generated_at="2026-08-21T10:00:00Z",
            workspace_root=self.workspace_root,
        )

        manifest_path = os.path.join(self.output_dir, "manifest.json")
        overview_path = os.path.join(self.output_dir, "overview.json")
        screener_path = os.path.join(self.output_dir, "screener.json")
        symbols_dir = os.path.join(self.output_dir, "symbols")

        self.assertTrue(os.path.exists(manifest_path))
        self.assertTrue(os.path.exists(overview_path))
        self.assertTrue(os.path.exists(screener_path))
        self.assertTrue(os.path.exists(symbols_dir))

        # Check manifest content & demo truthfulness semantics (safe default UNKNOWN)
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_json = json.load(f)
            self.assertEqual(manifest_json["schema_version"], "1.0.0")
            self.assertEqual(manifest_json["as_of_date"], "2026-08-21")
            self.assertEqual(manifest_json["quality"]["status"], "PASS")
            self.assertEqual(manifest_json["freshness"]["status"], "UNKNOWN")
            self.assertEqual(manifest_json["market_session_status"], "UNKNOWN")
            self.assertIn("fixture", manifest_json["freshness"]["reason"].lower())

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

        fpt_path = os.path.join(symbols_dir, "FPT.json")
        self.assertTrue(os.path.exists(fpt_path))
        with open(fpt_path, "r", encoding="utf-8") as f:
            fpt_json = json.load(f)
            self.assertEqual(fpt_json["dataset_id"], dataset_id)
            self.assertEqual(fpt_json["symbol"], "FPT")
            self.assertIn("series", fpt_json)
            self.assertIn("explanation", fpt_json)

    def test_dangerous_target_directory_rejected(self):
        with self.assertRaises(FilesystemSafetyError):
            validate_target_directory("/", workspace_root=self.workspace_root)
        with self.assertRaises(FilesystemSafetyError):
            validate_target_directory("C:\\", workspace_root=self.workspace_root)

        with self.assertRaises(FilesystemSafetyError):
            validate_target_directory(os.path.expanduser("~"), workspace_root=self.workspace_root)

        with self.assertRaises(FilesystemSafetyError):
            validate_target_directory("", workspace_root=self.workspace_root)

        with self.assertRaises(FilesystemSafetyError):
            validate_target_directory(self.workspace_root, workspace_root=self.workspace_root)

        parent_dir = os.path.abspath(os.path.join(self.workspace_root, "..", "other_dir"))
        with self.assertRaises(FilesystemSafetyError):
            validate_target_directory(parent_dir, workspace_root=self.workspace_root, allow_temp=False)

        with self.assertRaises(FilesystemSafetyError):
            validate_target_directory("/etc", workspace_root=self.workspace_root)

    def test_staging_and_output_overlap_rejected(self):
        with self.assertRaises(FilesystemSafetyError):
            validate_no_directory_overlap(self.output_dir, self.output_dir)

        nested_staging = os.path.join(self.output_dir, "nested_staging")
        with self.assertRaises(FilesystemSafetyError):
            validate_no_directory_overlap(nested_staging, self.output_dir)

        nested_output = os.path.join(self.staging_dir, "nested_output")
        with self.assertRaises(FilesystemSafetyError):
            validate_no_directory_overlap(self.staging_dir, nested_output)

    def test_symlink_escape_rejected(self):
        """Test that symlinks pointing outside the workspace are rejected."""
        external_target = os.path.join(self.temp_dir, "external_target")
        os.makedirs(external_target, exist_ok=True)
        symlink_path = os.path.join(self.workspace_root, "link_to_external")

        try:
            os.symlink(external_target, symlink_path, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks/junctions creation not permitted in this OS/user environment")

        with self.assertRaises(FilesystemSafetyError):
            validate_target_directory(symlink_path, workspace_root=self.workspace_root, allow_temp=False)

    def test_transactional_rollback_on_swap_failure(self):
        """Test that transactional directory replacement executes a true rollback on injected move failure."""
        provider = CsvDataProvider("tests/fixtures/sample_ohlcv.csv")
        records = provider.fetch_ohlcv()
        build_dataset_from_records(
            records=records,
            output_dir=self.output_dir,
            staging_dir=self.staging_dir,
            as_of_date="2026-08-21",
            fixed_generated_at="2026-08-21T10:00:00Z",
            workspace_root=self.workspace_root,
        )

        # Snapshot entire tree before injected failure
        original_tree = self._snapshot_directory_tree(self.output_dir)
        self.assertGreater(len(original_tree), 0)

        real_rename = os.rename
        call_count = [0]

        def selective_rename(src, dst):
            call_count[0] += 1
            if call_count[0] == 1:
                return real_rename(src, dst)
            elif call_count[0] == 2:
                raise OSError("Injected disk failure during staging -> output replacement")
            else:
                return real_rename(src, dst)

        with patch("os.rename", side_effect=selective_rename):
            with self.assertRaises(IOError):
                build_dataset_from_records(
                    records=records,
                    output_dir=self.output_dir,
                    staging_dir=self.staging_dir,
                    as_of_date="2026-08-21",
                    fixed_generated_at="2026-08-21T11:00:00Z",
                    workspace_root=self.workspace_root,
                )

        # 1. Output directory tree must be restored byte-for-byte
        restored_tree = self._snapshot_directory_tree(self.output_dir)
        self.assertEqual(restored_tree, original_tree)

        # 2. Assert zero orphan backup or staging directories left behind
        parent_dir = os.path.dirname(self.output_dir)
        remaining_dirs = os.listdir(parent_dir)
        for item in remaining_dirs:
            self.assertFalse(item.startswith(".backup_"), f"Orphan backup directory left behind: {item}")
            self.assertFalse(item.startswith(".staging_"), f"Orphan staging directory left behind: {item}")

    def test_stale_symbols_cleaned_up(self):
        os.makedirs(os.path.join(self.output_dir, "symbols"), exist_ok=True)
        stale_file = os.path.join(self.output_dir, "symbols", "DELISTED_OLD_SYMBOL.json")
        with open(stale_file, "w", encoding="utf-8") as f:
            f.write('{"symbol": "OLD"}')

        self.assertTrue(os.path.exists(stale_file))

        provider = CsvDataProvider("tests/fixtures/sample_ohlcv.csv")
        records = provider.fetch_ohlcv()
        build_dataset_from_records(
            records=records,
            output_dir=self.output_dir,
            staging_dir=self.staging_dir,
            as_of_date="2026-08-21",
            fixed_generated_at="2026-08-21T10:00:00Z",
            workspace_root=self.workspace_root,
        )

        self.assertFalse(os.path.exists(stale_file))

    def test_non_finite_rejection(self):
        with self.assertRaises(ValueError):
            sanitize_value({"price": float("nan")})
        with self.assertRaises(ValueError):
            sanitize_value({"price": float("inf")})
        with self.assertRaises(ValueError):
            sanitize_value({"price": float("-inf")})

    def test_two_run_reproducibility(self):
        """Test that two runs with fixed generated_at produce byte-for-byte identical output trees."""
        provider = CsvDataProvider("tests/fixtures/sample_ohlcv.csv")
        records = provider.fetch_ohlcv()

        id1 = build_dataset_from_records(
            records=records,
            output_dir=self.output_dir,
            staging_dir=self.staging_dir,
            as_of_date="2026-08-21",
            fixed_generated_at="2026-08-21T10:00:00Z",
            workspace_root=self.workspace_root,
        )
        tree1 = self._snapshot_directory_tree(self.output_dir)

        id2 = build_dataset_from_records(
            records=records,
            output_dir=self.output_dir,
            staging_dir=self.staging_dir,
            as_of_date="2026-08-21",
            fixed_generated_at="2026-08-21T10:00:00Z",
            workspace_root=self.workspace_root,
        )
        tree2 = self._snapshot_directory_tree(self.output_dir)

        self.assertEqual(id1, id2)
        self.assertEqual(tree1, tree2)


if __name__ == "__main__":
    unittest.main()
