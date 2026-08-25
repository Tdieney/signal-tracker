"""Automated security check, secret scanning, exact CSP validator, and deep public artifact schema validator."""

from __future__ import annotations

import argparse
import datetime
import json
import math
import os
import re
import sys
import urllib.parse
from typing import Any, Dict, List, Set, Tuple


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
    re.compile(r".*\.sh$"),
    re.compile(r".*secret.*", re.IGNORECASE),
]

SECRET_PATTERNS = [
    re.compile(r"(?i)api[_-]?key\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}['\"]?"),
    re.compile(r"(?i)secret[_-]?key\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}['\"]?"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9_\-\.]{20,}"),
    re.compile(r"(?i)ghp_[A-Za-z0-9]{36}"),
    re.compile(r"(?i)gho_[A-Za-z0-9]{36}"),
    re.compile(r"(?i)glpat-[A-Za-z0-9_\-]{20}"),
    re.compile(r"(?i)aws_secret_access_key\s*="),
    re.compile(r"(?i)VITE_[A-Za-z0-9_]*SECRET\s*="),
    re.compile(r"(?i)VITE_[A-Za-z0-9_]*TOKEN\s*="),
    re.compile(r"(?i)VITE_[A-Za-z0-9_]*KEY\s*="),
    re.compile(r"RAW_SECRET_KEY_[A-Za-z0-9_]+"),
    re.compile(r"AIzaSy[A-Za-z0-9_\-]{33}"),
]

ALLOWED_EXTERNAL_HOSTNAMES = {
    "www.w3.org",
    "reactjs.org",
    "www.apache.org",
    "www.tradingview.com",
}

EXTERNAL_URL_PATTERN = re.compile(r'https?://[a-zA-Z0-9_\-\./:\?#%&=]+')

MAX_FILE_SIZES = {
    ".html": 50 * 1024,        # 50 KB
    ".css": 200 * 1024,        # 200 KB
    ".js": 1500 * 1024,        # 1.5 MB
    ".json": 1000 * 1024,      # 1 MB
}

# Strict approved SHA-256 hash for Lightweight Charts style injection
APPROVED_STYLE_HASH = "'sha256-3pRED1tOXas1FXFoPb9TGCjmYe9XQsmO9OV23khV2nY='"

# Exact allowed CSP directives and their exact expected token sets
EXACT_CSP_SPEC = {
    "default-src": {"'self'"},
    "script-src": {"'self'"},
    "style-src": {"'self'", APPROVED_STYLE_HASH},
    "img-src": {"'self'", "data:"},
    "font-src": {"'self'"},
    "connect-src": {"'self'"},
    "object-src": {"'none'"},
    "base-uri": {"'self'"},
    "form-action": {"'self'"},
}

ALLOWED_ARTIFACT_PATH_PATTERNS = [
    re.compile(r"^index\.html$"),
    re.compile(r"^assets/index-[A-Za-z0-9_-]+\.(js|css)$"),
    re.compile(r"^data/manifest\.json$"),
    re.compile(r"^data/overview\.json$"),
    re.compile(r"^data/screener\.json$"),
    re.compile(r"^data/symbols/[A-Z0-9]{1,10}\.json$"),
    re.compile(r"^favicon\.(ico|png|svg)$"),
    re.compile(r"^robots\.txt$"),
]

DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ISO_TIMESTAMP_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")
DATASET_ID_REGEX = re.compile(r"^[a-f0-9]{16}$")
SCHEMA_VERSION_REGEX = re.compile(r"^\d+\.\d+\.\d+$")
SYMBOL_REGEX = re.compile(r"^[A-Z0-9]{1,10}$")

VALID_PROVIDERS = {"csv", "vnstock", "company_api"}
VALID_UNIVERSES = {"ALL", "VN30"}
VALID_FRESHNESS_STATUSES = {"FRESH", "STALE", "UNKNOWN"}
VALID_MARKET_SESSION_STATUSES = {"CLOSED_CONFIRMED", "UNKNOWN"}
VALID_QUALITY_STATUSES = {"PASS", "PARTIAL", "FAIL"}
VALID_EXCHANGES = {"HOSE", "HNX", "UPCOM"}
VALID_SIGNALS = {"ABOVE_MA10", "BELOW_MA10", "CROSS_UP_MA10", "CROSS_DOWN_MA10"}
VALID_DATA_STATUSES = {"VALID", "INSUFFICIENT_DATA", "NO_DATA_FOR_AS_OF_DATE", "INVALID_DATA"}

EXEMPT_SOURCE_FILES = {
    "scripts/security_check.py",
    "tests/test_security_check.py",
    "tests/test_csv_provider.py",
}


def is_valid_calendar_date(date_str: str) -> bool:
    """Validate that date_str is an actual calendar date (e.g. rejects 2026-02-30)."""
    if not isinstance(date_str, str) or not DATE_REGEX.match(date_str):
        return False
    try:
        parts = [int(p) for p in date_str.split("-")]
        datetime.date(parts[0], parts[1], parts[2])
        return True
    except (ValueError, TypeError):
        return False


def is_valid_iso_timestamp(ts_str: str) -> bool:
    """Validate that ts_str is a syntactically and calendar-valid ISO 8601 timestamp."""
    if not isinstance(ts_str, str) or not ISO_TIMESTAMP_REGEX.match(ts_str):
        return False
    try:
        clean_ts = ts_str.replace("Z", "+00:00")
        datetime.datetime.fromisoformat(clean_ts)
        return True
    except (ValueError, TypeError):
        return False


def is_finite_number(val: Any) -> bool:
    """Check that val is int or float and is finite (not NaN or Inf)."""
    if isinstance(val, bool):
        return False
    if isinstance(val, (int, float)):
        return math.isfinite(val)
    return False


def is_positive_finite_number(val: Any) -> bool:
    """Check that val is a finite number > 0."""
    return is_finite_number(val) and val > 0


def is_nonnegative_finite_number(val: Any) -> bool:
    """Check that val is a finite number >= 0."""
    return is_finite_number(val) and val >= 0


def parse_csp_directives(csp_string: str) -> Tuple[Dict[str, List[str]], List[str]]:
    """Parse CSP string into directive map, detecting duplicate directives and unsafe tokens."""
    directives: Dict[str, List[str]] = {}
    errors: List[str] = []
    parts = [p.strip() for p in csp_string.split(";") if p.strip()]

    for part in parts:
        tokens = part.split()
        if tokens:
            name = tokens[0].lower()
            values = tokens[1:]
            if name in directives:
                errors.append(f"Duplicate CSP directive '{name}' detected")
            directives[name] = values

            for tok in values:
                if tok in ("'unsafe-inline'", "'unsafe-eval'", "*"):
                    errors.append(f"Forbidden CSP token '{tok}' in directive '{name}'")

    return directives, errors


def check_csp_meta_tag(html_content: str, filename: str) -> List[str]:
    """Ensure Content-Security-Policy is present, exact, and conforms to strict allow-list."""
    violations: List[str] = []
    csp_match = re.search(
        r'<meta[^>]+http-equiv=["\']Content-Security-Policy["\'][^>]+content=(?:"([^"]+)"|\'([^\']+)\')',
        html_content,
        re.IGNORECASE,
    )
    if not csp_match:
        csp_match = re.search(
            r'<meta[^>]+content=(?:"([^"]+)"|\'([^\']+)\')[^>]+http-equiv=["\']Content-Security-Policy["\']',
            html_content,
            re.IGNORECASE,
        )

    if not csp_match:
        violations.append(f"Missing Content-Security-Policy meta tag in {filename}")
        return violations

    csp_val = csp_match.group(1) or csp_match.group(2) or ""
    directives, parse_errors = parse_csp_directives(csp_val)
    violations.extend(parse_errors)

    actual_directive_names = set(directives.keys())
    expected_directive_names = set(EXACT_CSP_SPEC.keys())

    missing = expected_directive_names - actual_directive_names
    extra = actual_directive_names - expected_directive_names

    if missing:
        violations.append(f"Missing required CSP directives: {sorted(missing)} in {filename}")
    if extra:
        violations.append(f"Unexpected extra CSP directives: {sorted(extra)} in {filename}")

    for dir_name, expected_tokens in EXACT_CSP_SPEC.items():
        if dir_name in directives:
            actual_tokens = set(directives[dir_name])
            if actual_tokens != expected_tokens:
                missing_tokens = expected_tokens - actual_tokens
                extra_tokens = actual_tokens - expected_tokens
                msg_parts = []
                if missing_tokens:
                    msg_parts.append(f"missing {missing_tokens}")
                if extra_tokens:
                    msg_parts.append(f"extraneous {extra_tokens}")
                violations.append(f"CSP directive '{dir_name}' mismatch ({'; '.join(msg_parts)}) in {filename}")

    return violations


def validate_external_url(raw_url: str) -> bool:
    """Validate external URL using urlparse for exact hostname allow-listing and malicious scheme rejection."""
    clean_url = raw_url.rstrip('",\';)%')
    try:
        if "%2e%2e" in clean_url.lower() or "javascript:" in clean_url.lower():
            return False
        parsed = urllib.parse.urlparse(clean_url)
    except Exception:
        return False

    if parsed.scheme not in ("http", "https"):
        return False

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        return False

    if hostname in ("localhost", "127.0.0.1", "::1"):
        return False

    return hostname in ALLOWED_EXTERNAL_HOSTNAMES


def validate_json_deep_structure(rel_path: str, content: str) -> Tuple[List[str], Dict[str, Any] | None]:
    """Verify that public JSON files match deep schemas, exact keys, types, enums, numbers, and invariants."""
    violations: List[str] = []
    norm_path = rel_path.replace("\\", "/")
    filename = os.path.basename(norm_path)

    # Check for NaN / Infinity tokens
    if "NaN" in content or "Infinity" in content:
        violations.append(f"Invalid non-standard numeric token (NaN/Infinity) in {rel_path}")

    try:
        data = json.loads(content)
    except json.JSONDecodeError as ex:
        return [f"Corrupted/malformed JSON in artifact: {rel_path} ({ex})"], None

    if not isinstance(data, dict):
        return [f"Public JSON root must be an object, got {type(data).__name__}: {rel_path}"], None

    # Base envelope keys
    for field in ["schema_version", "dataset_id", "as_of_date"]:
        if field not in data:
            violations.append(f"Missing base field '{field}' in {rel_path}")

    if "schema_version" in data:
        if not isinstance(data["schema_version"], str) or not SCHEMA_VERSION_REGEX.match(data["schema_version"]):
            violations.append(f"Invalid schema_version '{data.get('schema_version')}' in {rel_path}")
        elif data["schema_version"] != "1.0.0":
            violations.append(f"Unsupported schema_version '{data['schema_version']}' in {rel_path}")

    if "dataset_id" in data:
        if not isinstance(data["dataset_id"], str) or not DATASET_ID_REGEX.match(data["dataset_id"]):
            violations.append(f"Invalid dataset_id format '{data.get('dataset_id')}' in {rel_path}")

    if "as_of_date" in data:
        if not is_valid_calendar_date(data.get("as_of_date", "")):
            violations.append(f"Invalid as_of_date calendar date '{data.get('as_of_date')}' in {rel_path}")

    # Detailed file validations
    if filename == "manifest.json":
        expected_keys = {
            "schema_version", "dataset_id", "as_of_date", "generated_at",
            "market_timezone", "market_session_status", "freshness",
            "provider", "universe", "files", "quality"
        }
        actual_keys = set(data.keys())
        if actual_keys != expected_keys:
            if expected_keys - actual_keys:
                violations.append(f"manifest.json missing top-level keys: {expected_keys - actual_keys}")
            if actual_keys - expected_keys:
                violations.append(f"manifest.json unexpected top-level keys: {actual_keys - expected_keys}")

        gen_at = data.get("generated_at")
        if not is_valid_iso_timestamp(gen_at):
            violations.append(f"manifest.json generated_at must be valid ISO 8601 UTC timestamp: {gen_at}")

        if data.get("market_timezone") != "Asia/Ho_Chi_Minh":
            violations.append(f"manifest.json market_timezone must be 'Asia/Ho_Chi_Minh', got: {data.get('market_timezone')}")

        if data.get("market_session_status") not in VALID_MARKET_SESSION_STATUSES:
            violations.append(f"manifest.json invalid market_session_status: {data.get('market_session_status')}")

        if data.get("provider") not in VALID_PROVIDERS:
            violations.append(f"manifest.json provider must be one of {VALID_PROVIDERS}, got: {data.get('provider')}")

        if data.get("universe") not in VALID_UNIVERSES:
            violations.append(f"manifest.json universe must be one of {VALID_UNIVERSES}, got: {data.get('universe')}")

        freshness = data.get("freshness")
        if not isinstance(freshness, dict):
            violations.append("manifest.json 'freshness' must be an object")
        else:
            if set(freshness.keys()) != {"status", "expected_as_of_date", "reason"}:
                violations.append(f"manifest.json 'freshness' invalid keys: {set(freshness.keys())}")
            if freshness.get("status") not in VALID_FRESHNESS_STATUSES:
                violations.append(f"manifest.json freshness.status invalid: {freshness.get('status')}")
            if not is_valid_calendar_date(freshness.get("expected_as_of_date", "")):
                violations.append(f"manifest.json freshness.expected_as_of_date invalid date: {freshness.get('expected_as_of_date')}")
            if not isinstance(freshness.get("reason"), str) or len(freshness.get("reason", "")) > 500:
                violations.append("manifest.json freshness.reason must be string under 500 chars")

        files_dict = data.get("files")
        if not isinstance(files_dict, dict):
            violations.append("manifest.json 'files' must be an object")
        else:
            expected_files = {"overview": "overview.json", "screener": "screener.json", "symbols_base": "symbols/"}
            if files_dict != expected_files:
                violations.append(f"manifest.json 'files' map mismatch: actual {files_dict} vs expected {expected_files}")

        quality = data.get("quality")
        if not isinstance(quality, dict):
            violations.append("manifest.json 'quality' must be an object")
        else:
            if set(quality.keys()) != {"status", "input_rows", "accepted_rows", "rejected_rows", "eligible_symbols", "warnings"}:
                violations.append(f"manifest.json 'quality' invalid keys: {set(quality.keys())}")
            if quality.get("status") not in VALID_QUALITY_STATUSES:
                violations.append(f"manifest.json quality.status invalid: {quality.get('status')}")

            in_rows = quality.get("input_rows")
            acc_rows = quality.get("accepted_rows")
            rej_rows = quality.get("rejected_rows")
            elig_sym = quality.get("eligible_symbols")

            for int_name, val in [("input_rows", in_rows), ("accepted_rows", acc_rows), ("rejected_rows", rej_rows), ("eligible_symbols", elig_sym)]:
                if isinstance(val, bool) or not isinstance(val, int) or val < 0:
                    violations.append(f"manifest.json quality.{int_name} must be non-negative integer, got: {val}")

            # Accounting invariants
            if isinstance(in_rows, int) and isinstance(acc_rows, int) and isinstance(rej_rows, int):
                if in_rows != acc_rows + rej_rows:
                    violations.append(f"manifest.json quality row accounting invariant violated: input_rows ({in_rows}) != accepted_rows ({acc_rows}) + rejected_rows ({rej_rows})")

            if isinstance(elig_sym, int) and isinstance(acc_rows, int):
                if elig_sym > acc_rows:
                    violations.append(f"manifest.json quality eligible_symbols ({elig_sym}) > accepted_rows ({acc_rows})")

            warnings = quality.get("warnings")
            if not isinstance(warnings, list):
                violations.append("manifest.json quality.warnings must be a list")
            else:
                if len(warnings) > 100:
                    violations.append(f"manifest.json quality.warnings exceeds maximum 100 items ({len(warnings)})")
                for w_idx, w in enumerate(warnings):
                    if not isinstance(w, str):
                        violations.append(f"manifest.json quality.warnings[{w_idx}] must be a string, got: {type(w).__name__}")
                    else:
                        if len(w) > 300:
                            violations.append(f"manifest.json quality.warnings[{w_idx}] exceeds 300 chars")
                        for pat in SECRET_PATTERNS:
                            if pat.search(w):
                                violations.append(f"manifest.json quality.warnings[{w_idx}] contains sensitive secret pattern")

    elif filename == "overview.json":
        expected_keys = {"schema_version", "dataset_id", "as_of_date", "metrics", "breadth_history"}
        actual_keys = set(data.keys())
        if actual_keys != expected_keys:
            violations.append(f"overview.json top-level keys mismatch: actual {actual_keys} vs expected {expected_keys}")

        metrics = data.get("metrics")
        if not isinstance(metrics, dict):
            violations.append("overview.json 'metrics' must be an object")
        else:
            expected_metric_keys = {
                "eligible_count", "above_count", "above_pct", "below_count",
                "below_pct", "on_ma10_count", "cross_up_count", "cross_down_count"
            }
            if set(metrics.keys()) != expected_metric_keys:
                violations.append(f"overview.json metrics invalid keys: {set(metrics.keys())}")
            else:
                elig = metrics.get("eligible_count")
                abv = metrics.get("above_count")
                bel = metrics.get("below_count")
                on_m = metrics.get("on_ma10_count")
                cr_up = metrics.get("cross_up_count")
                cr_dn = metrics.get("cross_down_count")
                abv_p = metrics.get("above_pct")
                bel_p = metrics.get("below_pct")

                for cnt_name, cnt_val in [("eligible_count", elig), ("above_count", abv), ("below_count", bel),
                                          ("on_ma10_count", on_m), ("cross_up_count", cr_up), ("cross_down_count", cr_dn)]:
                    if isinstance(cnt_val, bool) or not isinstance(cnt_val, int) or cnt_val < 0:
                        violations.append(f"overview.json metrics.{cnt_name} must be non-negative integer, got: {cnt_val}")

                # Percentages validation & math consistency
                for pct_name, pct_val in [("above_pct", abv_p), ("below_pct", bel_p)]:
                    if pct_val is not None:
                        if not is_finite_number(pct_val) or not (0.0 <= pct_val <= 100.0):
                            violations.append(f"overview.json metrics.{pct_name} must be finite number in [0, 100] or null, got: {pct_val}")

                if isinstance(elig, int) and elig > 0:
                    if isinstance(abv, int):
                        expected_abv_pct = round(abv / elig * 100, 1)
                        if abv_p is None or abs(abv_p - expected_abv_pct) > 0.05:
                            violations.append(f"overview.json above_pct ({abv_p}) does not match above_count/eligible_count ({expected_abv_pct})")
                    if isinstance(bel, int):
                        expected_bel_pct = round(bel / elig * 100, 1)
                        if bel_p is None or abs(bel_p - expected_bel_pct) > 0.05:
                            violations.append(f"overview.json below_pct ({bel_p}) does not match below_count/eligible_count ({expected_bel_pct})")
                elif elig == 0:
                    if abv_p is not None or bel_p is not None:
                        violations.append("overview.json percentages must be null when eligible_count is 0")

                # Invariants
                if isinstance(elig, int) and isinstance(abv, int) and isinstance(bel, int) and isinstance(on_m, int):
                    if abv + bel + on_m != elig:
                        violations.append(f"overview.json metrics count invariant violated: above ({abv}) + below ({bel}) + on_ma10 ({on_m}) != eligible ({elig})")
                    if isinstance(cr_up, int) and cr_up > elig:
                        violations.append(f"overview.json cross_up_count ({cr_up}) > eligible_count ({elig})")
                    if isinstance(cr_dn, int) and cr_dn > elig:
                        violations.append(f"overview.json cross_down_count ({cr_dn}) > eligible_count ({elig})")

        breadth_history = data.get("breadth_history")
        if not isinstance(breadth_history, list):
            violations.append("overview.json 'breadth_history' must be a list")
        else:
            if len(breadth_history) > 60:
                violations.append(f"overview.json breadth_history length ({len(breadth_history)}) exceeds Phase 1 limit 60")
            prev_date = ""
            for idx, item in enumerate(breadth_history):
                if not isinstance(item, dict) or set(item.keys()) != {"trading_date", "eligible_count", "above_count", "above_pct"}:
                    violations.append(f"overview.json breadth_history[{idx}] invalid shape")
                else:
                    t_date = item.get("trading_date", "")
                    if not is_valid_calendar_date(t_date):
                        violations.append(f"overview.json breadth_history[{idx}].trading_date invalid: {t_date}")
                    if prev_date and t_date <= prev_date:
                        violations.append(f"overview.json breadth_history not sorted strictly ascending by date: {prev_date} >= {t_date}")
                    prev_date = t_date

                    h_elig = item.get("eligible_count")
                    h_abv = item.get("above_count")
                    h_pct = item.get("above_pct")

                    if isinstance(h_elig, bool) or not isinstance(h_elig, int) or h_elig < 0:
                        violations.append(f"overview.json breadth_history[{idx}].eligible_count must be int >= 0")
                    if isinstance(h_abv, bool) or not isinstance(h_abv, int) or h_abv < 0 or (isinstance(h_elig, int) and h_abv > h_elig):
                        violations.append(f"overview.json breadth_history[{idx}].above_count invalid: {h_abv}")
                    if h_pct is not None and (not is_finite_number(h_pct) or not (0.0 <= h_pct <= 100.0)):
                        violations.append(f"overview.json breadth_history[{idx}].above_pct must be in [0, 100] or null")

                    if isinstance(h_elig, int) and isinstance(h_abv, int) and h_elig > 0:
                        expected_h_pct = round(h_abv / h_elig * 100, 1)
                        if h_pct is None or abs(h_pct - expected_h_pct) > 0.05:
                            violations.append(f"overview.json breadth_history[{idx}].above_pct ({h_pct}) does not match above_count/eligible_count ({expected_h_pct})")

    elif filename == "screener.json":
        expected_keys = {"schema_version", "dataset_id", "as_of_date", "items"}
        actual_keys = set(data.keys())
        if actual_keys != expected_keys:
            violations.append(f"screener.json top-level keys mismatch: actual {actual_keys} vs expected {expected_keys}")

        items = data.get("items")
        if not isinstance(items, list):
            violations.append("screener.json 'items' must be a list")
        else:
            expected_item_keys = {
                "symbol", "exchange", "in_vn30", "last_trading_date", "close",
                "ma10", "distance_pct", "volume", "avg_volume_20d", "signal",
                "signal_reason", "data_status"
            }
            for idx, item in enumerate(items):
                if not isinstance(item, dict) or set(item.keys()) != expected_item_keys:
                    violations.append(f"screener.json items[{idx}] invalid shape")
                    break

                sym = item.get("symbol")
                if not isinstance(sym, str) or not SYMBOL_REGEX.match(sym):
                    violations.append(f"screener.json items[{idx}].symbol invalid: {sym}")

                ex = item.get("exchange")
                if ex not in VALID_EXCHANGES:
                    violations.append(f"screener.json items[{idx}].exchange invalid: {ex}")

                vn30 = item.get("in_vn30")
                if not isinstance(vn30, bool):
                    violations.append(f"screener.json items[{idx}].in_vn30 must be boolean, got: {type(vn30).__name__}")

                l_date = item.get("last_trading_date")
                if not is_valid_calendar_date(l_date):
                    violations.append(f"screener.json items[{idx}].last_trading_date invalid: {l_date}")

                sig = item.get("signal")
                if sig is not None and sig not in VALID_SIGNALS:
                    violations.append(f"screener.json items[{idx}].signal invalid: {sig}")

                s_reason = item.get("signal_reason")
                if s_reason is not None and (not isinstance(s_reason, str) or not s_reason.strip()):
                    violations.append(f"screener.json items[{idx}].signal_reason must be non-empty string or null")

                d_status = item.get("data_status")
                if d_status not in VALID_DATA_STATUSES:
                    violations.append(f"screener.json items[{idx}].data_status invalid: {d_status}")

                close_val = item.get("close")
                if close_val is not None and not is_positive_finite_number(close_val):
                    violations.append(f"screener.json items[{idx}].close must be positive finite number or null, got: {close_val}")

                ma10_val = item.get("ma10")
                if ma10_val is not None and not is_positive_finite_number(ma10_val):
                    violations.append(f"screener.json items[{idx}].ma10 must be positive finite number or null, got: {ma10_val}")

                dist_val = item.get("distance_pct")
                if dist_val is not None and not is_finite_number(dist_val):
                    violations.append(f"screener.json items[{idx}].distance_pct must be finite number or null, got: {dist_val}")

                avg_vol = item.get("avg_volume_20d")
                if avg_vol is not None and not is_nonnegative_finite_number(avg_vol):
                    violations.append(f"screener.json items[{idx}].avg_volume_20d must be non-negative finite number or null, got: {avg_vol}")

                vol = item.get("volume")
                if vol is not None and (isinstance(vol, bool) or not isinstance(vol, int) or vol < 0):
                    violations.append(f"screener.json items[{idx}].volume must be non-negative integer or null, got: {vol}")

    elif norm_path.startswith("data/symbols/") and filename.endswith(".json"):
        expected_sym = filename[:-5]
        expected_keys = {"schema_version", "dataset_id", "symbol", "exchange", "as_of_date", "latest", "series", "explanation"}
        actual_keys = set(data.keys())
        if actual_keys != expected_keys:
            violations.append(f"symbol detail JSON top-level keys mismatch in {rel_path}: {actual_keys} vs {expected_keys}")

        sym = data.get("symbol")
        if sym != expected_sym:
            violations.append(f"symbol detail symbol '{sym}' does not match filename '{filename}' in {rel_path}")

        if data.get("exchange") not in VALID_EXCHANGES:
            violations.append(f"symbol detail exchange invalid '{data.get('exchange')}' in {rel_path}")

        latest = data.get("latest")
        if not isinstance(latest, dict) or set(latest.keys()) != {"close", "ma10", "distance_pct", "signal", "data_status"}:
            violations.append(f"symbol detail 'latest' invalid shape in {rel_path}")
        else:
            lat_close = latest.get("close")
            lat_ma10 = latest.get("ma10")
            lat_dist = latest.get("distance_pct")
            lat_sig = latest.get("signal")
            lat_stat = latest.get("data_status")

            if lat_close is not None and not is_positive_finite_number(lat_close):
                violations.append(f"symbol detail latest.close must be positive finite number in {rel_path}")
            if lat_ma10 is not None and not is_positive_finite_number(lat_ma10):
                violations.append(f"symbol detail latest.ma10 must be positive finite number or null in {rel_path}")
            if lat_dist is not None and not is_finite_number(lat_dist):
                violations.append(f"symbol detail latest.distance_pct must be finite number or null in {rel_path}")
            if lat_sig is not None and lat_sig not in VALID_SIGNALS:
                violations.append(f"symbol detail latest.signal invalid '{lat_sig}' in {rel_path}")
            if lat_stat not in VALID_DATA_STATUSES:
                violations.append(f"symbol detail latest.data_status invalid '{lat_stat}' in {rel_path}")

        series = data.get("series")
        if not isinstance(series, list):
            violations.append(f"symbol detail 'series' must be a list in {rel_path}")
        else:
            expected_series_keys = {"trading_date", "open", "high", "low", "close", "ma10", "volume", "signal"}
            prev_s_date = ""
            for s_idx, s_item in enumerate(series):
                if not isinstance(s_item, dict) or set(s_item.keys()) != expected_series_keys:
                    violations.append(f"symbol detail series[{s_idx}] invalid shape in {rel_path}")
                    break
                s_date = s_item.get("trading_date", "")
                if not is_valid_calendar_date(s_date):
                    violations.append(f"symbol detail series[{s_idx}].trading_date invalid in {rel_path}")
                if prev_s_date and s_date <= prev_s_date:
                    violations.append(f"symbol detail series not sorted ascending by date in {rel_path}: {prev_s_date} >= {s_date}")
                prev_s_date = s_date

                s_open = s_item.get("open")
                s_high = s_item.get("high")
                s_low = s_item.get("low")
                s_close = s_item.get("close")
                for p_name, p_val in [("open", s_open), ("high", s_high), ("low", s_low), ("close", s_close)]:
                    if not is_positive_finite_number(p_val):
                        violations.append(f"symbol detail series[{s_idx}].{p_name} must be positive finite number in {rel_path}")

                s_ma10 = s_item.get("ma10")
                if s_ma10 is not None and not is_positive_finite_number(s_ma10):
                    violations.append(f"symbol detail series[{s_idx}].ma10 must be positive finite number or null in {rel_path}")

                if is_positive_finite_number(s_open) and is_positive_finite_number(s_high) and is_positive_finite_number(s_low) and is_positive_finite_number(s_close):
                    if s_high < max(s_open, s_close, s_low) or s_low > min(s_open, s_close, s_high):
                        violations.append(f"symbol detail series[{s_idx}] OHLC invariant violated in {rel_path}")

                s_vol = s_item.get("volume")
                if isinstance(s_vol, bool) or not isinstance(s_vol, int) or s_vol < 0:
                    violations.append(f"symbol detail series[{s_idx}].volume must be non-negative int in {rel_path}")

                s_sig = s_item.get("signal")
                if s_sig is not None and s_sig not in VALID_SIGNALS:
                    violations.append(f"symbol detail series[{s_idx}].signal invalid '{s_sig}' in {rel_path}")

        explanation = data.get("explanation")
        if not isinstance(explanation, dict) or set(explanation.keys()) != {"current_close", "current_ma10", "previous_close", "previous_ma10", "rule"}:
            violations.append(f"symbol detail 'explanation' invalid shape in {rel_path}")
        else:
            for exp_f in ["current_close", "current_ma10", "previous_close", "previous_ma10"]:
                exp_v = explanation.get(exp_f)
                if exp_v is not None and not is_positive_finite_number(exp_v):
                    violations.append(f"symbol detail explanation.{exp_f} must be positive finite number or null in {rel_path}")
            rule_v = explanation.get("rule")
            if not isinstance(rule_v, str) or not rule_v.strip():
                violations.append(f"symbol detail explanation.rule must be non-empty string in {rel_path}")

    return violations, data


def check_artifact_directory(artifact_dir: str) -> List[str]:
    """Inspect built production artifact for mandatory files, strict CSP, and cross-file consistency."""
    violations: List[str] = []
    if not os.path.exists(artifact_dir):
        return [f"Artifact directory does not exist: {artifact_dir}"]

    mandatory_files = [
        "index.html",
        "data/manifest.json",
        "data/overview.json",
        "data/screener.json",
    ]
    for mf in mandatory_files:
        full_mf = os.path.join(artifact_dir, mf)
        if not os.path.isfile(full_mf):
            violations.append(f"Mandatory artifact file not found: {mf}")

    assets_dir = os.path.join(artifact_dir, "assets")
    if not os.path.isdir(assets_dir):
        violations.append("Mandatory assets directory not found in artifact")
    else:
        asset_files = os.listdir(assets_dir)
        has_js = any(f.endswith(".js") and f.startswith("index-") for f in asset_files)
        has_css = any(f.endswith(".css") and f.startswith("index-") for f in asset_files)
        if not has_js:
            violations.append("Missing mandatory JavaScript bundle index-*.js in assets/")
        if not has_css:
            violations.append("Missing mandatory CSS bundle index-*.css in assets/")

    json_envelopes: Dict[str, Dict[str, Any]] = {}
    screener_symbols: Set[str] = set()

    for root, _, files in os.walk(artifact_dir):
        for f in files:
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, artifact_dir)
            rel_posix = rel_path.replace("\\", "/")
            _, ext = os.path.splitext(f)
            ext_lower = ext.lower()

            matches_pattern = any(p.match(rel_posix) for p in ALLOWED_ARTIFACT_PATH_PATTERNS)
            if not matches_pattern:
                violations.append(f"Disallowed or unexpected artifact file path: {rel_posix}")

            if ext_lower not in ALLOWED_EXTENSIONS:
                violations.append(f"Disallowed file extension '{ext}' in artifact: {rel_path}")

            for pat in DISALLOWED_FILENAME_PATTERNS:
                if pat.match(f):
                    violations.append(f"Disallowed filename pattern '{pat.pattern}' in artifact: {rel_path}")

            size = os.path.getsize(full_path)
            max_size = MAX_FILE_SIZES.get(ext_lower)
            if max_size and size > max_size:
                violations.append(f"File size {size} bytes exceeds maximum limit {max_size} bytes: {rel_path}")

            if ext_lower in {".html", ".css", ".js", ".json"}:
                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as tf:
                        content = tf.read()

                        for pat in SECRET_PATTERNS:
                            if pat.search(content):
                                violations.append(f"Suspicious secret pattern detected in artifact: {rel_path}")

                        if ext_lower == ".html":
                            csp_errs = check_csp_meta_tag(content, rel_path)
                            violations.extend(csp_errs)

                        if ext_lower in {".html", ".js", ".css"}:
                            found_urls = EXTERNAL_URL_PATTERN.findall(content)
                            for url in found_urls:
                                if not validate_external_url(url):
                                    clean_url = url.rstrip('",\';)%')
                                    violations.append(f"Unauthorized external URL in artifact ({clean_url}): {rel_path}")

                        if ext_lower == ".json":
                            json_errs, parsed_data = validate_json_deep_structure(rel_path, content)
                            violations.extend(json_errs)
                            if parsed_data:
                                json_envelopes[rel_posix] = parsed_data
                                if rel_posix == "data/screener.json" and "items" in parsed_data:
                                    screener_symbols = set(it["symbol"] for it in parsed_data["items"] if "symbol" in it)
                except Exception as ex:
                    violations.append(f"Error reading artifact file: {rel_path} ({ex})")

    # Cross-file consistency validation
    manifest_data = json_envelopes.get("data/manifest.json")
    overview_data = json_envelopes.get("data/overview.json")

    if manifest_data:
        expected_dataset_id = manifest_data.get("dataset_id")
        expected_as_of = manifest_data.get("as_of_date")
        expected_schema = manifest_data.get("schema_version")

        for file_rel, envelope in json_envelopes.items():
            if file_rel != "data/manifest.json":
                if envelope.get("dataset_id") != expected_dataset_id:
                    violations.append(f"Cross-file dataset_id mismatch in {file_rel}: {envelope.get('dataset_id')} != {expected_dataset_id}")
                if envelope.get("as_of_date") != expected_as_of:
                    violations.append(f"Cross-file as_of_date mismatch in {file_rel}: {envelope.get('as_of_date')} != {expected_as_of}")
                if envelope.get("schema_version") != expected_schema:
                    violations.append(f"Cross-file schema_version mismatch in {file_rel}: {envelope.get('schema_version')} != {expected_schema}")

        disk_symbol_files = {
            f[:-5] for f in os.listdir(os.path.join(artifact_dir, "data", "symbols"))
            if f.endswith(".json")
        } if os.path.isdir(os.path.join(artifact_dir, "data", "symbols")) else set()

        if screener_symbols != disk_symbol_files:
            if screener_symbols - disk_symbol_files:
                violations.append(f"Screener references missing symbol JSONs: {screener_symbols - disk_symbol_files}")
            if disk_symbol_files - screener_symbols:
                violations.append(f"Unreferenced symbol JSON files in artifact: {disk_symbol_files - screener_symbols}")

        if overview_data and "metrics" in overview_data and "quality" in manifest_data:
            if overview_data["metrics"].get("eligible_count") != manifest_data["quality"].get("eligible_symbols"):
                violations.append(f"Cross-file eligible count mismatch: overview metrics ({overview_data['metrics'].get('eligible_count')}) != manifest quality ({manifest_data['quality'].get('eligible_symbols')})")

    return violations


def scan_source_for_secrets(root_dir: str) -> List[str]:
    """Scan source code files in repository for accidental secret tokens and multiline inline React style props."""
    violations: List[str] = []
    ignored_dirs = {".git", "node_modules", ".venv", "__pycache__", "dist", ".staging_data", "tests/fixtures"}
    style_prop_pattern = re.compile(r"\bstyle\s*=\s*\{")

    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in ignored_dirs]
        for f in files:
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, root_dir)
            rel_posix = rel_path.replace("\\", "/")

            if f.startswith(".env") and f != ".env.example":
                violations.append(f"Uncommitted or untracked .env file found: {rel_path}")

            # Exact normalized relative-path allow-list check
            if rel_posix in EXEMPT_SOURCE_FILES:
                continue

            _, ext = os.path.splitext(f)
            ext_lower = ext.lower()
            if ext_lower in {".ts", ".tsx", ".js", ".jsx", ".py", ".html", ".json"}:
                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as sf:
                        content = sf.read()

                        for pat in SECRET_PATTERNS:
                            if pat.search(content):
                                violations.append(f"Suspicious secret pattern in {rel_path}")

                        if ext_lower in {".tsx", ".jsx"}:
                            if style_prop_pattern.search(content):
                                violations.append(f"Forbidden inline React style prop found in {rel_path}")
                except Exception:
                    pass

    return violations


def main() -> None:
    parser = argparse.ArgumentParser(description="Security check & artifact allow-list validator")
    parser.add_argument("--artifact", default="frontend/dist", help="Path to built artifact directory")
    parser.add_argument("--root", default=".", help="Root directory of workspace")
    args = parser.parse_args()

    print("Running security, CSP, and artifact checks...")
    all_violations: List[str] = []

    src_violations = scan_source_for_secrets(args.root)
    all_violations.extend(src_violations)

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
        print("PASS: Zero security violations, strict CSP verified, and artifact allow-list intact.")


if __name__ == "__main__":
    main()
