"""Automated security check, secret scanning, and public artifact allow-list validator."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import List, Set


ALLOWED_EXTENSIONS = {
    ".html",
    ".js",
    ".css",
    ".json",
    ".svg",
    ".png",
    ".ico",
    ".txt",
    ".webmanifest",
    ".woff",
    ".woff2",
}

DISALLOWED_FILENAME_PATTERNS = [
    re.compile(r"^\.env"),
    re.compile(r".*\.pem$"),
    re.compile(r".*\.key$"),
    re.compile(r".*\.log$"),
    re.compile(r".*\.map$"),
    re.compile(r".*\.csv$"),
    re.compile(r".*\.pkl$"),
    re.compile(r".*\.py$"),
    re.compile(r".*secret.*", re.IGNORECASE),
]

SUSPICIOUS_CONTENT_PATTERNS = [
    re.compile(r"(?i)api[_-]?key\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]"),
    re.compile(r"(?i)secret[_-]?key\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9_\-\.]{20,}"),
    re.compile(r"(?i)ghp_[A-Za-z0-9]{36}"),
    re.compile(r"(?i)VITE_[A-Za-z0-9_]*SECRET"),
    re.compile(r"(?i)VITE_[A-Za-z0-9_]*TOKEN"),
    re.compile(r"(?i)VITE_[A-Za-z0-9_]*KEY"),
]


def check_artifact_directory(artifact_dir: str) -> List[str]:
    """Verify that only allowed file types exist in public artifact."""
    violations: List[str] = []
    if not os.path.exists(artifact_dir):
        return [f"Artifact directory does not exist: {artifact_dir}"]

    for root, _, files in os.walk(artifact_dir):
        for f in files:
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, artifact_dir)
            _, ext = os.path.splitext(f)
            ext_lower = ext.lower()

            if ext_lower not in ALLOWED_EXTENSIONS:
                violations.append(f"Disallowed file extension '{ext}' in artifact: {rel_path}")

            for pat in DISALLOWED_FILENAME_PATTERNS:
                if pat.match(f):
                    violations.append(f"Disallowed filename pattern matched in artifact: {rel_path}")

            # Check file contents for NaN / Infinity in JSON or secrets
            if ext_lower == ".json":
                try:
                    with open(full_path, "r", encoding="utf-8") as jf:
                        content = jf.read()
                        if "NaN" in content or "Infinity" in content:
                            violations.append(f"Invalid numeric token (NaN/Infinity) in JSON: {rel_path}")
                        json.loads(content)
                except Exception as ex:
                    violations.append(f"Corrupted JSON in artifact: {rel_path} ({ex})")

    return violations


def scan_source_for_secrets(root_dir: str) -> List[str]:
    """Scan source code files for accidental secret tokens."""
    violations: List[str] = []
    ignored_dirs = {".git", "node_modules", ".venv", "__pycache__", "dist", ".staging_data"}

    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in ignored_dirs]
        for f in files:
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, root_dir)

            if f.startswith(".env") and f != ".env.example":
                violations.append(f"Uncommitted or untracked .env file found: {rel_path}")

            # Scan text content
            _, ext = os.path.splitext(f)
            ext_lower = ext.lower()
            if ext_lower in {".ts", ".tsx", ".js", ".jsx", ".py", ".html", ".json"}:
                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as sf:
                        for line_idx, line in enumerate(sf, start=1):
                            for pat in SUSPICIOUS_CONTENT_PATTERNS:
                                if pat.search(line):
                                    if "SUSPICIOUS_CONTENT_PATTERNS" not in line and "security_check.py" not in rel_path:
                                        violations.append(f"Suspicious secret pattern at {rel_path}:{line_idx}")
                except Exception:
                    pass

    return violations


def main() -> None:
    parser = argparse.ArgumentParser(description="Security check & artifact allow-list validator")
    parser.add_argument("--artifact", default="frontend/dist", help="Path to built artifact directory")
    parser.add_argument("--root", default=".", help="Root directory of workspace")
    args = parser.parse_args()

    print("Running security and artifact checks...")
    all_violations: List[str] = []

    # 1. Source secret scan
    src_violations = scan_source_for_secrets(args.root)
    all_violations.extend(src_violations)

    # 2. Artifact inspection (if artifact exists)
    if os.path.exists(args.artifact):
        art_violations = check_artifact_directory(args.artifact)
        all_violations.extend(art_violations)
    else:
        print(f"Note: Artifact directory '{args.artifact}' not yet built; skipping artifact check.")

    if all_violations:
        print(f"FAIL: Found {len(all_violations)} security/allow-list violations:", file=sys.stderr)
        for v in all_violations:
            print(f"  - {v}", file=sys.stderr)
        sys.exit(1)
    else:
        print("PASS: Zero security violations or disallowed artifact files detected.")


if __name__ == "__main__":
    main()
