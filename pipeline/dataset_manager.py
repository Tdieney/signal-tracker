"""Dataset Manager: Transactional staging, deep contract verification, and Last-Known-Good (LKG) rollback engine."""

from __future__ import annotations

import logging
import os
import shutil
from typing import List, Optional, Tuple
from scripts.security_check import validate_data_directory

logger = logging.getLogger("vn_stock_signal.dataset_manager")


def is_path_safe_and_within(child_path: str, parent_path: str) -> bool:
    """Validate that child_path resolves strictly within parent_path without symlink/junction escape."""
    abs_parent = os.path.abspath(os.path.realpath(parent_path))
    abs_child = os.path.abspath(os.path.realpath(child_path))

    # Reject if child is identical to parent or parent's parent
    if abs_child == abs_parent:
        return False

    try:
        common = os.path.commonpath([abs_parent, abs_child])
        return common == abs_parent
    except ValueError:
        return False


def are_paths_disjoint(path_a: str, path_b: str) -> bool:
    """Verify that neither path contains the other."""
    abs_a = os.path.abspath(os.path.realpath(path_a))
    abs_b = os.path.abspath(os.path.realpath(path_b))

    if abs_a == abs_b:
        return False

    try:
        common = os.path.commonpath([abs_a, abs_b])
        return common != abs_a and common != abs_b
    except ValueError:
        return True


class DatasetManager:
    """Manages transactional dataset publishing, deep validation, and Last-Known-Good rollback."""

    def __init__(
        self,
        workspace_root: str,
        target_dir: str,
        staging_dir: Optional[str] = None,
        lkg_dir: Optional[str] = None,
    ):
        self.workspace_root = os.path.abspath(workspace_root)
        self.target_dir = os.path.abspath(target_dir)
        self.staging_dir = os.path.abspath(staging_dir or os.path.join(self.workspace_root, ".staging_data"))
        self.lkg_dir = os.path.abspath(lkg_dir or os.path.join(self.workspace_root, ".lkg_data"))
        self.swap_dir = os.path.abspath(os.path.join(self.workspace_root, ".swap_tmp"))

        self._validate_path_boundaries()

    def _validate_path_boundaries(self) -> None:
        """Ensure all managed paths are within workspace_root and mutually disjoint."""
        managed_paths = [
            ("target_dir", self.target_dir),
            ("staging_dir", self.staging_dir),
            ("lkg_dir", self.lkg_dir),
            ("swap_dir", self.swap_dir),
        ]

        for name, p in managed_paths:
            # Check within workspace
            abs_p = os.path.abspath(p)
            abs_ws = os.path.abspath(self.workspace_root)

            # Do not allow targeting root or parent
            if abs_p == abs_ws or not abs_p.startswith(abs_ws):
                raise ValueError(f"Managed directory {name} ({p}) must be strictly inside workspace_root ({self.workspace_root})")

        # Check mutual disjointness
        for i in range(len(managed_paths)):
            for j in range(i + 1, len(managed_paths)):
                name_i, path_i = managed_paths[i]
                name_j, path_j = managed_paths[j]
                if not are_paths_disjoint(path_i, path_j):
                    raise ValueError(f"Managed paths {name_i} ({path_i}) and {name_j} ({path_j}) must be mutually disjoint")

    def prepare_staging(self) -> str:
        """Create a clean empty staging directory."""
        if os.path.exists(self.staging_dir):
            if os.path.islink(self.staging_dir):
                os.unlink(self.staging_dir)
            else:
                shutil.rmtree(self.staging_dir)
        os.makedirs(self.staging_dir, exist_ok=True)
        return self.staging_dir

    def _verify_directory(self, dir_path: str) -> Tuple[bool, List[str]]:
        """Deep validate a data directory using the shared schema and security validator."""
        try:
            errors = validate_data_directory(dir_path)
            return (len(errors) == 0), errors
        except Exception as e:
            return False, [f"Validation exception on {dir_path}: {e}"]

    def verify_staging(self) -> Tuple[bool, List[str]]:
        """Deep validate staging directory against security rules and data contracts."""
        return self._verify_directory(self.staging_dir)

    def publish_from_staging(self) -> Tuple[bool, List[str]]:
        """Atomically promote verified staging dataset to target with zero-orphan transactional rollback."""
        is_valid, errors = self.verify_staging()
        if not is_valid:
            return False, errors

        had_target = os.path.exists(self.target_dir)

        # 1. Clean swap directory
        if os.path.exists(self.swap_dir):
            shutil.rmtree(self.swap_dir)

        try:
            # 2. Back up existing target to swap_dir
            if had_target:
                shutil.move(self.target_dir, self.swap_dir)

            # 3. Move staging to target
            shutil.move(self.staging_dir, self.target_dir)

            # 4. Deep verify target directory after move
            target_valid, target_errors = self._verify_directory(self.target_dir)
            if not target_valid:
                # Rollback step 3
                if os.path.exists(self.target_dir):
                    shutil.rmtree(self.target_dir)
                if had_target and os.path.exists(self.swap_dir):
                    shutil.move(self.swap_dir, self.target_dir)
                return False, [f"Target verification failed after move: {e}" for e in target_errors]

            # 5. Update LKG backup safely
            lkg_tmp = self.lkg_dir + ".tmp"
            if os.path.exists(lkg_tmp):
                shutil.rmtree(lkg_tmp)
            shutil.copytree(self.target_dir, lkg_tmp)

            if os.path.exists(self.lkg_dir):
                shutil.rmtree(self.lkg_dir)
            shutil.move(lkg_tmp, self.lkg_dir)

            # 6. Clean swap backup
            if os.path.exists(self.swap_dir):
                shutil.rmtree(self.swap_dir)

            return True, []
        except Exception as e:
            # Rollback on unhandled exception
            if not os.path.exists(self.target_dir) and had_target and os.path.exists(self.swap_dir):
                shutil.move(self.swap_dir, self.target_dir)
            if os.path.exists(self.swap_dir):
                shutil.rmtree(self.swap_dir, ignore_errors=True)
            return False, [f"Transactional publish failed: {e}"]

    def rollback_to_last_known_good(self) -> Tuple[bool, str]:
        """Restore target directory from LKG backup."""
        if not os.path.exists(self.lkg_dir):
            return False, "No Last-Known-Good dataset available for rollback."

        is_lkg_valid, lkg_errors = self._verify_directory(self.lkg_dir)
        if not is_lkg_valid:
            return False, f"LKG dataset corrupted: {lkg_errors}"

        if os.path.exists(self.swap_dir):
            shutil.rmtree(self.swap_dir)

        had_target = os.path.exists(self.target_dir)
        try:
            if had_target:
                shutil.move(self.target_dir, self.swap_dir)
            shutil.copytree(self.lkg_dir, self.target_dir)
            if os.path.exists(self.swap_dir):
                shutil.rmtree(self.swap_dir)
            return True, "Successfully rolled back target directory to Last-Known-Good dataset."
        except Exception as e:
            if had_target and os.path.exists(self.swap_dir) and not os.path.exists(self.target_dir):
                shutil.move(self.swap_dir, self.target_dir)
            return False, f"Failed to restore from LKG: {e}"
