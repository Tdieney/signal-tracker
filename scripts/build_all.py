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
    # 1. Build dataset JSON files from CSV fixture with fixed deterministic generated-at
    run_step(
        [
            sys.executable,
            "pipeline/build_dataset.py",
            "--provider",
            "csv",
            "--input",
            "tests/fixtures/sample_ohlcv.csv",
            "--output",
            "frontend/public/data",
            "--generated-at",
            "2026-08-21T10:00:00Z",
        ],
        "Build static JSON dataset from CSV fixture",
    )

    # 2. Run Python tests
    run_step(
        [sys.executable, "-m", "unittest", "discover", "tests"],
        "Run Python pipeline test suite",
    )

    # 3. Run frontend tests and production build
    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
    run_step([npm_cmd, "--prefix", "frontend", "test", "--", "--run"], "Run frontend Vitest suite")
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
