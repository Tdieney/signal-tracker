"""Master build script to run pipeline dataset generation, frontend build, and security verification."""

from __future__ import annotations

import os
import subprocess
import sys


def run_step(cmd: list[str], description: str) -> None:
    print(f"=== [STEP] {description} ===")
    res = subprocess.run(cmd, shell=False)
    if res.returncode != 0:
        print(f"ERROR: Step '{description}' failed with code {res.returncode}", file=sys.stderr)
        sys.exit(res.returncode)


def main() -> None:
    # 0. Check for whitespace errors in working-tree and committed HEAD
    run_step(["git", "diff", "--check"], "Check for uncommitted trailing whitespace errors in working tree")
    run_step(["git", "show", "--check", "--format=", "HEAD"], "Check for committed trailing whitespace errors in HEAD")

    # 1. Build live dataset JSON files from Vnstock provider for VN30 universe
    run_step(
        [
            sys.executable,
            "pipeline/build_dataset.py",
            "--provider",
            "vnstock",
            "--universe",
            "VN30",
            "--output",
            "frontend/public/data",
        ],
        "Build live JSON dataset from Vnstock provider (VN30)",
    )

    # 2. Run Python tests
    run_step(
        [sys.executable, "-m", "unittest", "discover", "tests"],
        "Run Python pipeline test suite",
    )

    # 3. Run frontend tests, audit, and production build
    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
    run_step([npm_cmd, "--prefix", "frontend", "test", "--", "--run"], "Run frontend Vitest suite")
    run_step([npm_cmd, "--prefix", "frontend", "audit", "--audit-level=high"], "Run frontend npm security audit")
    run_step([npm_cmd, "--prefix", "frontend", "run", "typecheck"], "Run frontend TypeScript typecheck")
    run_step([npm_cmd, "--prefix", "frontend", "run", "build:pages"], "Build frontend static production bundle with base path")

    # 4. Run Security and Artifact Scan
    run_step(
        [sys.executable, "scripts/security_check.py", "--artifact", "frontend/dist"],
        "Run security scan and artifact allow-list check",
    )

    # 5. Run Playwright E2E and Accessibility Suite
    run_step(
        [npm_cmd, "--prefix", "frontend", "run", "test:e2e"],
        "Run Playwright E2E and Axe accessibility suite across viewports",
    )

    print("\n=== SUCCESS: All pipeline, test, frontend build, security, and E2E checks passed! ===")


if __name__ == "__main__":
    main()
