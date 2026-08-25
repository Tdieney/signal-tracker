"""Dataset Manager: Transactional staging, deep contract verification, and Last-Known-Good (LKG) rollback engine."""

from __future__ import annotations

import logging
import os
import shutil
from typing import List, Optional, Tuple
from scripts.security_check import is_reparse_point_or_symlink, validate_data_directory

logger = logging.getLogger("vn_stock_signal.dataset_manager")


def is_path_safe_and_within(child_path: str, parent_workspace: str) -> bool:
    """Validate that child_path resolves strictly inside parent_workspace without escaping via traversal or symlinks."""
    norm_parent = os.path.normcase(os.path.abspath(os.path.realpath(parent_workspace)))
    norm_child = os.path.normcase(os.path.abspath(os.path.realpath(child_path)))

    # Reject if child is identical to parent or parent's filesystem root
    if norm_child == norm_parent:
        return False

    # Check for symlink/junction/reparse point in child_path or any existing ancestor component up to workspace
    check_p = os.path.abspath(child_path)
    abs_parent = os.path.abspath(parent_workspace)
    while len(check_p) >= len(abs_parent):
        if is_reparse_point_or_symlink(check_p):
            return False
        parent_p = os.path.dirname(check_p)
        if parent_p == check_p:
            break
        check_p = parent_p

    try:
        common = os.path.commonpath([norm_parent, norm_child])
        return common == norm_parent
    except ValueError:
        # Different drives on Windows
        return False


def are_paths_disjoint(path_a: str, path_b: str) -> bool:
    """Verify that neither path is identical to or contains the other."""
    norm_a = os.path.normcase(os.path.abspath(os.path.realpath(path_a)))
    norm_b = os.path.normcase(os.path.abspath(os.path.realpath(path_b)))

    if norm_a == norm_b:
        return False

    try:
        common = os.path.commonpath([norm_a, norm_b])
        return common != norm_a and common != norm_b
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
        self.lkg_tmp = os.path.abspath(os.path.join(self.workspace_root, ".lkg_tmp"))
        self.lkg_swap = os.path.abspath(os.path.join(self.workspace_root, ".lkg_swap_tmp"))

        self._validate_path_boundaries()

    def _validate_path_boundaries(self) -> None:
        """Ensure all managed paths are strictly inside workspace_root and mutually disjoint."""
        managed_paths = [
            ("target_dir", self.target_dir),
            ("staging_dir", self.staging_dir),
            ("lkg_dir", self.lkg_dir),
            ("swap_dir", self.swap_dir),
            ("lkg_tmp", self.lkg_tmp),
            ("lkg_swap", self.lkg_swap),
        ]

        for name, p in managed_paths:
            if not is_path_safe_and_within(p, self.workspace_root):
                raise ValueError(
                    f"Managed directory {name} ({p}) must resolve strictly inside workspace_root ({self.workspace_root})"
                )

        # Check mutual disjointness across all managed paths
        for i in range(len(managed_paths)):
            for j in range(i + 1, len(managed_paths)):
                name_i, path_i = managed_paths[i]
                name_j, path_j = managed_paths[j]
                if not are_paths_disjoint(path_i, path_j):
                    raise ValueError(f"Managed paths {name_i} ({path_i}) and {name_j} ({path_j}) must be mutually disjoint")

    def _assert_safe_destructive_target(self, path: str) -> None:
        """Ensure path is strictly within workspace_root before performing destructive operations."""
        if not is_path_safe_and_within(path, self.workspace_root):
            raise ValueError(f"Destructive target path {path} is outside workspace {self.workspace_root}")

    def prepare_staging(self) -> str:
        """Create a clean empty staging directory."""
        self._assert_safe_destructive_target(self.staging_dir)
        if os.path.exists(self.staging_dir):
            if is_reparse_point_or_symlink(self.staging_dir):
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

    def _clean_stale_recovery_directories(self) -> Tuple[bool, List[str]]:
        """Clean stale temporary recovery directories and verify they are completely gone."""
        recovery_dirs = [self.swap_dir, self.lkg_tmp, self.lkg_swap]
        for d in recovery_dirs:
            self._assert_safe_destructive_target(d)
            if os.path.exists(d):
                try:
                    if is_reparse_point_or_symlink(d):
                        os.unlink(d)
                    else:
                        shutil.rmtree(d)
                except Exception as ex:
                    logger.warning(f"Failed to remove recovery directory: {ex}")
                if os.path.exists(d):
                    return False, ["Persistent stale recovery directory could not be cleaned"]
        return True, []

    def verify_staging(self) -> Tuple[bool, List[str]]:
        """Deep validate staging directory against security rules and data contracts."""
        return self._verify_directory(self.staging_dir)

    def publish_from_staging(self) -> Tuple[bool, List[str]]:
        """Promote verified staging dataset to target with transactional failure rollback and explicit commit point."""
        is_valid, errors = self.verify_staging()
        if not is_valid:
            return False, errors

        # 1. Clean and verify stale recovery directories before transaction starts
        clean_ok, clean_errs = self._clean_stale_recovery_directories()
        if not clean_ok:
            return False, clean_errs

        had_target = os.path.exists(self.target_dir)
        had_lkg = os.path.exists(self.lkg_dir)
        committed = False

        try:
            # 2. Back up existing target to swap_dir
            if had_target:
                self._assert_safe_destructive_target(self.target_dir)
                shutil.move(self.target_dir, self.swap_dir)

            # 3. Move staging to target
            self._assert_safe_destructive_target(self.staging_dir)
            self._assert_safe_destructive_target(self.target_dir)
            shutil.move(self.staging_dir, self.target_dir)

            # 4. Deep verify target directory after move
            target_valid, target_errors = self._verify_directory(self.target_dir)
            if not target_valid:
                # Pre-commit rollback: restore target from swap_dir
                if os.path.exists(self.target_dir):
                    shutil.rmtree(self.target_dir, ignore_errors=True)
                if had_target and os.path.exists(self.swap_dir):
                    shutil.move(self.swap_dir, self.target_dir)
                return False, [f"Target verification failed after move: {e}" for e in target_errors]

            # 5. Create and verify LKG candidate in lkg_tmp
            shutil.copytree(self.target_dir, self.lkg_tmp)
            lkg_valid, lkg_errors = self._verify_directory(self.lkg_tmp)
            if not lkg_valid:
                # Pre-commit rollback: restore target from swap_dir
                if os.path.exists(self.lkg_tmp):
                    shutil.rmtree(self.lkg_tmp, ignore_errors=True)
                if os.path.exists(self.target_dir):
                    shutil.rmtree(self.target_dir, ignore_errors=True)
                if had_target and os.path.exists(self.swap_dir):
                    shutil.move(self.swap_dir, self.target_dir)
                return False, [f"LKG candidate verification failed: {e}" for e in lkg_errors]

            # 6. Back up existing LKG to lkg_swap
            if had_lkg:
                shutil.move(self.lkg_dir, self.lkg_swap)

            # 7. Promote lkg_tmp to lkg_dir
            shutil.move(self.lkg_tmp, self.lkg_dir)

            # 8. Final deep verification of promoted LKG
            lkg_promoted_valid, lkg_promoted_errors = self._verify_directory(self.lkg_dir)
            if not lkg_promoted_valid:
                # Pre-commit rollback: restore both target and LKG
                if os.path.exists(self.lkg_dir):
                    shutil.rmtree(self.lkg_dir, ignore_errors=True)
                if had_lkg and os.path.exists(self.lkg_swap):
                    shutil.move(self.lkg_swap, self.lkg_dir)
                if os.path.exists(self.target_dir):
                    shutil.rmtree(self.target_dir, ignore_errors=True)
                if had_target and os.path.exists(self.swap_dir):
                    shutil.move(self.swap_dir, self.target_dir)
                return False, [f"Promoted LKG verification failed: {e}" for e in lkg_promoted_errors]

            # =========================================================================
            # COMMIT POINT: Both target_dir and lkg_dir are validated and promoted to V2.
            # From this point forward, the transaction is COMMITTED.
            # Failures in subsequent cleanup MUST NOT cause split-brain or revert target.
            # =========================================================================
            committed = True
            warnings: List[str] = []

            # 9. Post-commit cleanup of temporary recovery directories
            try:
                if had_lkg and os.path.exists(self.lkg_swap):
                    shutil.rmtree(self.lkg_swap)
            except Exception as ex_clean_lkg:
                logger.warning(f"Post-commit cleanup of lkg_swap failed (non-fatal): {ex_clean_lkg}")

            try:
                if os.path.exists(self.swap_dir):
                    shutil.rmtree(self.swap_dir)
            except Exception as ex_clean_swap:
                logger.warning(f"Post-commit cleanup of swap_dir failed (non-fatal): {ex_clean_swap}")

            # Check if any recovery directory remains
            if (had_lkg and os.path.exists(self.lkg_swap)) or os.path.exists(self.swap_dir) or os.path.exists(self.lkg_tmp):
                warnings.append("Post-commit warning: temporary recovery directory cleanup incomplete")

            return True, warnings

        except Exception as e:
            if committed:
                # Post-commit exception: target and LKG are already valid V2. Do NOT roll back to V1!
                logger.error(f"Post-commit error during final cleanup: {e}")
                return True, ["Post-commit warning: temporary recovery directory cleanup incomplete"]

            # Pre-commit full recovery: restore both target and LKG to V1 byte-for-byte
            if os.path.exists(self.lkg_tmp):
                shutil.rmtree(self.lkg_tmp, ignore_errors=True)

            if had_lkg and os.path.exists(self.lkg_swap) and not os.path.exists(self.lkg_dir):
                shutil.move(self.lkg_swap, self.lkg_dir)
            elif os.path.exists(self.lkg_swap):
                shutil.rmtree(self.lkg_swap, ignore_errors=True)

            # If swap_dir exists, target was backed up to swap_dir and new target was placed/attempted.
            # In this case, delete partial/new target and restore old target from swap_dir.
            if had_target and os.path.exists(self.swap_dir):
                if os.path.exists(self.target_dir):
                    shutil.rmtree(self.target_dir, ignore_errors=True)
                shutil.move(self.swap_dir, self.target_dir)
            elif not had_target and os.path.exists(self.target_dir):
                # Target was newly created from staging; remove it
                shutil.rmtree(self.target_dir, ignore_errors=True)

            if os.path.exists(self.swap_dir):
                shutil.rmtree(self.swap_dir, ignore_errors=True)

            return False, [f"Transactional publish failed: {e}"]

    def rollback_to_last_known_good(self) -> Tuple[bool, str]:
        """Restore target directory from LKG backup with transactional safety."""
        if not os.path.exists(self.lkg_dir):
            return False, "No Last-Known-Good dataset available for rollback."

        is_lkg_valid, lkg_errors = self._verify_directory(self.lkg_dir)
        if not is_lkg_valid:
            return False, f"LKG dataset corrupted: {lkg_errors}"

        # Clean and verify stale recovery directories before rollback starts
        clean_ok, clean_errs = self._clean_stale_recovery_directories()
        if not clean_ok or os.path.exists(self.swap_dir):
            return False, "Persistent stale recovery directory could not be cleaned"

        had_target = os.path.exists(self.target_dir)
        try:
            if had_target:
                self._assert_safe_destructive_target(self.target_dir)
                if os.path.exists(self.swap_dir):
                    return False, "Persistent stale recovery directory could not be cleaned"
                shutil.move(self.target_dir, self.swap_dir)

            self._assert_safe_destructive_target(self.target_dir)
            shutil.copytree(self.lkg_dir, self.target_dir)

            target_valid, target_errors = self._verify_directory(self.target_dir)
            if not target_valid:
                # Rollback restoration
                if os.path.exists(self.target_dir):
                    try:
                        if is_reparse_point_or_symlink(self.target_dir):
                            os.unlink(self.target_dir)
                        else:
                            shutil.rmtree(self.target_dir)
                    except Exception:
                        pass

                if os.path.exists(self.target_dir):
                    logger.error("Partial target directory could not be removed; keeping swap recovery intact without moving.")
                    return False, "LKG rollback failed: partial target directory could not be removed for recovery"

                if had_target and os.path.exists(self.swap_dir):
                    try:
                        shutil.move(self.swap_dir, self.target_dir)
                    except Exception as restore_ex:
                        logger.error(f"Failed to restore original target from swap during rollback failure: {restore_ex}")
                        return False, "LKG rollback failed and target restoration failed"
                return False, f"Target verification failed after LKG restoration: {target_errors}"

            if os.path.exists(self.swap_dir):
                try:
                    if is_reparse_point_or_symlink(self.swap_dir):
                        os.unlink(self.swap_dir)
                    else:
                        shutil.rmtree(self.swap_dir)
                except Exception as ex_clean:
                    logger.warning(f"Post-rollback cleanup of swap_dir failed (non-fatal): {ex_clean}")

            return True, "Successfully rolled back target directory to Last-Known-Good dataset."
        except Exception as e:
            if os.path.exists(self.target_dir):
                try:
                    if is_reparse_point_or_symlink(self.target_dir):
                        os.unlink(self.target_dir)
                    else:
                        shutil.rmtree(self.target_dir)
                except Exception as ex_rm:
                    logger.warning(f"Failed to remove partial target during rollback recovery: {ex_rm}")

            if os.path.exists(self.target_dir):
                logger.error("Partial target directory could not be removed; keeping swap recovery intact without moving.")
                return False, "LKG rollback failed: partial target directory could not be removed for recovery"

            if had_target and os.path.exists(self.swap_dir):
                try:
                    shutil.move(self.swap_dir, self.target_dir)
                except Exception as restore_ex:
                    logger.error(f"Failed to restore original target from swap during rollback failure: {restore_ex}")
                    return False, "LKG rollback failed and target restoration failed"

            if os.path.exists(self.swap_dir):
                try:
                    if is_reparse_point_or_symlink(self.swap_dir):
                        os.unlink(self.swap_dir)
                    else:
                        shutil.rmtree(self.swap_dir)
                except Exception:
                    pass

            return False, "LKG rollback failed"
