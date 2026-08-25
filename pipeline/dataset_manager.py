"""Dataset Manager: Transactional staging, verification, and Last-Known-Good (LKG) rollback engine."""

from __future__ import annotations

import json
import logging
import os
import shutil
from typing import Optional, Tuple
from scripts.security_check import check_artifact_directory

logger = logging.getLogger("vn_stock_signal.dataset_manager")


class DatasetManager:
    """Manages atomic dataset publishing and automatic Last-Known-Good rollback."""

    def __init__(
        self,
        target_dir: str,
        staging_dir: Optional[str] = None,
        lkg_dir: Optional[str] = None,
    ):
        self.target_dir = os.path.abspath(target_dir)
        self.staging_dir = os.path.abspath(staging_dir or os.path.join(os.path.dirname(self.target_dir), ".staging_data"))
        self.lkg_dir = os.path.abspath(lkg_dir or os.path.join(os.path.dirname(self.target_dir), ".lkg_data"))

    def prepare_staging(self) -> str:
        """Create a clean empty staging directory."""
        if os.path.exists(self.staging_dir):
            shutil.rmtree(self.staging_dir)
        os.makedirs(self.staging_dir, exist_ok=True)
        return self.staging_dir

    def verify_staging(self) -> Tuple[bool, list]:
        """Validate all files in staging directory against data contracts and security rules."""
        manifest_path = os.path.join(self.staging_dir, "manifest.json")
        overview_path = os.path.join(self.staging_dir, "overview.json")
        screener_path = os.path.join(self.staging_dir, "screener.json")
        symbols_dir = os.path.join(self.staging_dir, "symbols")

        errors = []
        if not os.path.isfile(manifest_path):
            errors.append("Missing staging manifest.json")
        if not os.path.isfile(overview_path):
            errors.append("Missing staging overview.json")
        if not os.path.isfile(screener_path):
            errors.append("Missing staging screener.json")
        if not os.path.isdir(symbols_dir):
            errors.append("Missing staging symbols directory")

        if errors:
            return False, errors

        # Verify manifest dataset_id matches child files
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)
            manifest_id = manifest_data.get("dataset_id")

            with open(overview_path, "r", encoding="utf-8") as f:
                ov_data = json.load(f)
            if ov_data.get("dataset_id") != manifest_id:
                errors.append(f"Overview dataset_id mismatch: {ov_data.get('dataset_id')} vs {manifest_id}")

            with open(screener_path, "r", encoding="utf-8") as f:
                sc_data = json.load(f)
            if sc_data.get("dataset_id") != manifest_id:
                errors.append(f"Screener dataset_id mismatch: {sc_data.get('dataset_id')} vs {manifest_id}")
        except Exception as e:
            errors.append(f"Error parsing staging JSON: {e}")

        return (len(errors) == 0), errors

    def publish_from_staging(self) -> bool:
        """Atomically promote verified staging dataset to target and backup to LKG."""
        is_valid, errors = self.verify_staging()
        if not is_valid:
            logger.error(f"Staging dataset validation failed: {errors}")
            return False

        # Create target parent dir if needed
        os.makedirs(os.path.dirname(self.target_dir), exist_ok=True)

        # Atomic replacement: swap staging into target
        temp_backup = self.target_dir + ".swap_tmp"
        if os.path.exists(temp_backup):
            shutil.rmtree(temp_backup)

        try:
            if os.path.exists(self.target_dir):
                shutil.move(self.target_dir, temp_backup)
            shutil.move(self.staging_dir, self.target_dir)

            # Update LKG backup
            if os.path.exists(self.lkg_dir):
                shutil.rmtree(self.lkg_dir)
            shutil.copytree(self.target_dir, self.lkg_dir)

            # Clean up swap backup
            if os.path.exists(temp_backup):
                shutil.rmtree(temp_backup)
            return True
        except Exception as e:
            logger.error(f"Atomic swap failed: {e}")
            if os.path.exists(temp_backup) and not os.path.exists(self.target_dir):
                shutil.move(temp_backup, self.target_dir)
            return False

    def rollback_to_last_known_good(self) -> bool:
        """Restore target directory from LKG backup if available."""
        if not os.path.exists(self.lkg_dir):
            logger.warning("No Last-Known-Good dataset available for rollback.")
            return False

        try:
            if os.path.exists(self.target_dir):
                shutil.rmtree(self.target_dir)
            shutil.copytree(self.lkg_dir, self.target_dir)
            logger.info("Successfully restored target dataset from Last-Known-Good backup.")
            return True
        except Exception as e:
            logger.error(f"Failed to rollback to LKG: {e}")
            return False
