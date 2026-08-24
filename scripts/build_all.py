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
    # 1. Build dataset JSON files from CSV fixture
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
    run_step([npm_cmd, "--prefix", "frontend", "test"], "Run frontend Vitest suite")
    run_step([npm_cmd, "--prefix", "frontend", "run", "typecheck"], "Run frontend TypeScript typecheck")
    run_step([npm_cmd, "--prefix", "frontend", "run", "build"], "Build frontend static production bundle")

    # 4. Run Security and Artifact Scan
    run_step(
        [sys.executable, "scripts/security_check.py", "--artifact", "frontend/dist"],
        "Run security scan and artifact allow-list check",
    )

    print("\n=== SUCCESS: All pipeline, test, frontend build, and security checks passed! ===")


if __name__ == "__main__":
    main()
