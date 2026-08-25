"""Comprehensive adversarial and regression unit tests for security_check.py."""

import json
import os
import shutil
import tempfile
import unittest

from scripts.security_check import (
    check_artifact_directory,
    check_csp_meta_tag,
    is_valid_calendar_date,
    scan_source_for_secrets,
    validate_external_url,
    validate_json_deep_structure,
)


class TestSecurityCheck(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_sec_check_")
        self.artifact_dir = os.path.join(self.temp_dir, "dist")
        os.makedirs(self.artifact_dir, exist_ok=True)

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_valid_artifact(self):
        """Helper to create a fully valid production artifact directory."""
        index_html = (
            '<!DOCTYPE html><html><head>'
            '<meta http-equiv="Content-Security-Policy" content="'
            "default-src 'self'; script-src 'self'; style-src 'self' 'sha256-3pRED1tOXas1FXFoPb9TGCjmYe9XQsmO9OV23khV2nY='; "
            "img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self';"
            '"></head><body><div id="root"></div></body></html>'
        )
        with open(os.path.join(self.artifact_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(index_html)

        assets_dir = os.path.join(self.artifact_dir, "assets")
        os.makedirs(assets_dir, exist_ok=True)
        with open(os.path.join(assets_dir, "index-ABC12345.js"), "w", encoding="utf-8") as f:
            f.write('console.log("valid bundle");')
        with open(os.path.join(assets_dir, "index-ABC12345.css"), "w", encoding="utf-8") as f:
            f.write('.card { color: #000; }')

        data_dir = os.path.join(self.artifact_dir, "data")
        os.makedirs(data_dir, exist_ok=True)

        manifest = {
            "schema_version": "1.0.0",
            "dataset_id": "0123456789abcdef",
            "as_of_date": "2026-08-21",
            "generated_at": "2026-08-21T10:00:00Z",
            "market_timezone": "Asia/Ho_Chi_Minh",
            "market_session_status": "UNKNOWN",
            "freshness": {"status": "UNKNOWN", "expected_as_of_date": "2026-08-21", "reason": "Test"},
            "provider": "csv",
            "universe": "ALL",
            "files": {"overview": "overview.json", "screener": "screener.json", "symbols_base": "symbols/"},
            "quality": {"status": "PASS", "input_rows": 10, "accepted_rows": 10, "rejected_rows": 0, "eligible_symbols": 1, "warnings": []},
        }
        with open(os.path.join(data_dir, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f)

        overview = {
            "schema_version": "1.0.0",
            "dataset_id": "0123456789abcdef",
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
            "breadth_history": [{"trading_date": "2026-08-21", "eligible_count": 1, "above_count": 1, "above_pct": 100.0}],
        }
        with open(os.path.join(data_dir, "overview.json"), "w", encoding="utf-8") as f:
            json.dump(overview, f)

        screener = {
            "schema_version": "1.0.0",
            "dataset_id": "0123456789abcdef",
            "as_of_date": "2026-08-21",
            "items": [{
                "symbol": "FPT",
                "exchange": "HOSE",
                "in_vn30": True,
                "last_trading_date": "2026-08-21",
                "close": 100.0,
                "ma10": 98.0,
                "distance_pct": 2.04,
                "volume": 1000,
                "avg_volume_20d": 1000.0,
                "signal": "ABOVE_MA10",
                "signal_reason": "Price above MA10",
                "data_status": "VALID",
            }],
        }
        with open(os.path.join(data_dir, "screener.json"), "w", encoding="utf-8") as f:
            json.dump(screener, f)

        symbols_dir = os.path.join(data_dir, "symbols")
        os.makedirs(symbols_dir, exist_ok=True)
        fpt = {
            "schema_version": "1.0.0",
            "dataset_id": "0123456789abcdef",
            "symbol": "FPT",
            "exchange": "HOSE",
            "as_of_date": "2026-08-21",
            "latest": {"close": 100.0, "ma10": 98.0, "distance_pct": 2.04, "signal": "ABOVE_MA10", "data_status": "VALID"},
            "series": [{"trading_date": "2026-08-21", "open": 99.0, "high": 101.0, "low": 98.0, "close": 100.0, "ma10": 98.0, "volume": 1000, "signal": "ABOVE_MA10"}],
            "explanation": {"current_close": 100.0, "current_ma10": 98.0, "previous_close": 98.0, "previous_ma10": 97.0, "rule": "Rule"},
        }
        with open(os.path.join(symbols_dir, "FPT.json"), "w", encoding="utf-8") as f:
            json.dump(fpt, f)

    def test_artifact_directory_valid(self):
        self._create_valid_artifact()
        violations = check_artifact_directory(self.artifact_dir)
        self.assertEqual(violations, [])

    def test_csp_meta_tag_valid(self):
        valid_csp = (
            '<meta http-equiv="Content-Security-Policy" content="'
            "default-src 'self'; script-src 'self'; style-src 'self' 'sha256-3pRED1tOXas1FXFoPb9TGCjmYe9XQsmO9OV23khV2nY='; "
            "img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self';"
            '">'
        )
        violations = check_csp_meta_tag(valid_csp, "index.html")
        self.assertEqual(violations, [])

    def test_csp_rejects_missing_meta_tag(self):
        html_without_csp = "<html><head><title>No CSP</title></head><body></body></html>"
        violations = check_csp_meta_tag(html_without_csp, "index.html")
        self.assertTrue(any("Missing Content-Security-Policy" in v for v in violations))

    def test_csp_rejects_unsafe_inline(self):
        csp = '<meta http-equiv="Content-Security-Policy" content="script-src \'unsafe-inline\' \'self\'; style-src \'self\';">'
        violations = check_csp_meta_tag(csp, "index.html")
        self.assertTrue(any("Forbidden CSP token ''unsafe-inline''" in v for v in violations))

    def test_csp_rejects_unsafe_eval(self):
        csp = '<meta http-equiv="Content-Security-Policy" content="script-src \'unsafe-eval\' \'self\'; style-src \'self\';">'
        violations = check_csp_meta_tag(csp, "index.html")
        self.assertTrue(any("Forbidden CSP token ''unsafe-eval''" in v for v in violations))

    def test_csp_rejects_wildcard(self):
        csp = '<meta http-equiv="Content-Security-Policy" content="default-src *; script-src \'self\';">'
        violations = check_csp_meta_tag(csp, "index.html")
        self.assertTrue(any("Forbidden CSP token '*'" in v for v in violations))

    def test_csp_fails_on_missing_style_hash(self):
        missing_hash_csp = (
            '<meta http-equiv="Content-Security-Policy" content="'
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self';"
            '">'
        )
        violations = check_csp_meta_tag(missing_hash_csp, "index.html")
        self.assertTrue(any("style-src" in v and "missing" in v for v in violations))

    def test_csp_fails_on_extraneous_data_scheme(self):
        bad_csp = (
            '<meta http-equiv="Content-Security-Policy" content="'
            "default-src 'self'; script-src 'self'; style-src 'self' 'sha256-3pRED1tOXas1FXFoPb9TGCjmYe9XQsmO9OV23khV2nY='; "
            "img-src 'self' data:; font-src 'self'; connect-src 'self' data:; object-src 'none'; base-uri 'self'; form-action 'self';"
            '">'
        )
        violations = check_csp_meta_tag(bad_csp, "index.html")
        self.assertTrue(any("extraneous" in v and "connect-src" in v for v in violations))

    def test_csp_fails_on_duplicate_directive(self):
        duplicate_csp = (
            '<meta http-equiv="Content-Security-Policy" content="'
            "default-src 'self'; script-src 'self'; script-src 'self'; style-src 'self' 'sha256-3pRED1tOXas1FXFoPb9TGCjmYe9XQsmO9OV23khV2nY='; "
            "img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self';"
            '">'
        )
        violations = check_csp_meta_tag(duplicate_csp, "index.html")
        self.assertTrue(any("Duplicate CSP directive 'script-src'" in v for v in violations))

    def test_artifact_fails_on_disallowed_extensions_and_patterns(self):
        self._create_valid_artifact()
        # Add disallowed files
        with open(os.path.join(self.artifact_dir, ".env"), "w") as f:
            f.write("SECRET=123")
        with open(os.path.join(self.artifact_dir, "raw_data.csv"), "w") as f:
            f.write("a,b,c")
        with open(os.path.join(self.artifact_dir, "build.log"), "w") as f:
            f.write("log")
        with open(os.path.join(self.artifact_dir, "bundle.js.map"), "w") as f:
            f.write("{}")

        violations = check_artifact_directory(self.artifact_dir)
        self.assertTrue(any(".env" in v for v in violations))
        self.assertTrue(any("raw_data.csv" in v for v in violations))
        self.assertTrue(any("build.log" in v for v in violations))
        self.assertTrue(any("bundle.js.map" in v for v in violations))

    def test_deep_json_schema_rejections_and_adversarial_cases(self):
        # 1. Invalid calendar date (e.g. 2026-02-30)
        self.assertFalse(is_valid_calendar_date("2026-02-30"))
        self.assertTrue(is_valid_calendar_date("2026-08-21"))

        # 2. NaN / Infinity in JSON
        violations, _ = validate_json_deep_structure("data/overview.json", '{"schema_version": "1.0.0", "above_pct": NaN}')
        self.assertTrue(any("NaN" in v for v in violations))

        # 3. Overview metrics has string "WRONG"
        bad_overview = {
            "schema_version": "1.0.0",
            "dataset_id": "0123456789abcdef",
            "as_of_date": "2026-08-21",
            "metrics": {
                "eligible_count": "WRONG",
                "above_count": 1,
                "above_pct": 100.0,
                "below_count": 0,
                "below_pct": 0.0,
                "on_ma10_count": 0,
                "cross_up_count": 0,
                "cross_down_count": 0,
            },
            "breadth_history": [],
        }
        violations, _ = validate_json_deep_structure("data/overview.json", json.dumps(bad_overview))
        self.assertTrue(any("eligible_count" in v for v in violations))

        # 4. Overview metrics count invariant broken (above + below + on_ma10 != eligible)
        bad_overview["metrics"]["eligible_count"] = 10
        bad_overview["metrics"]["above_count"] = 5
        bad_overview["metrics"]["below_count"] = 2
        bad_overview["metrics"]["on_ma10_count"] = 1  # 5 + 2 + 1 = 8 != 10
        violations, _ = validate_json_deep_structure("data/overview.json", json.dumps(bad_overview))
        self.assertTrue(any("metrics count invariant violated" in v for v in violations))

        # 5. Screener item wrong types (in_vn30 is string, invalid exchange, invalid signal)
        bad_screener = {
            "schema_version": "1.0.0",
            "dataset_id": "0123456789abcdef",
            "as_of_date": "2026-08-21",
            "items": [{
                "symbol": "FPT",
                "exchange": "INVALID_EXCHANGE",
                "in_vn30": "not-a-bool",
                "last_trading_date": "2026-08-21",
                "close": 100.0,
                "ma10": 98.0,
                "distance_pct": 2.04,
                "volume": 1000,
                "avg_volume_20d": 1000.0,
                "signal": "BUY_NOW_INVALID",
                "signal_reason": "test",
                "data_status": "VALID",
            }],
        }
        violations, _ = validate_json_deep_structure("data/screener.json", json.dumps(bad_screener))
        self.assertTrue(any("in_vn30 must be boolean" in v for v in violations))
        self.assertTrue(any("exchange invalid" in v for v in violations))
        self.assertTrue(any("signal invalid" in v for v in violations))

        # 6. Symbol detail: symbol does not match filename
        bad_symbol = {
            "schema_version": "1.0.0",
            "dataset_id": "0123456789abcdef",
            "symbol": "VIC",
            "exchange": "HOSE",
            "as_of_date": "2026-08-21",
            "latest": {"close": 100.0, "ma10": 98.0, "distance_pct": 2.04, "signal": "ABOVE_MA10", "data_status": "VALID"},
            "series": [{"trading_date": "2026-08-21", "open": 99.0, "high": 101.0, "low": 98.0, "close": 100.0, "ma10": 98.0, "volume": 1000, "signal": "ABOVE_MA10"}],
            "explanation": {"current_close": 100.0, "current_ma10": 98.0, "previous_close": 98.0, "previous_ma10": 97.0, "rule": "Rule"},
        }
        violations, _ = validate_json_deep_structure("data/symbols/FPT.json", json.dumps(bad_symbol))
        self.assertTrue(any("does not match filename" in v for v in violations))

        # 7. Symbol detail: OHLC invariant violation in series
        bad_symbol["symbol"] = "FPT"
        bad_symbol["series"][0]["high"] = 50.0  # high < open (99) and close (100)
        violations, _ = validate_json_deep_structure("data/symbols/FPT.json", json.dumps(bad_symbol))
        self.assertTrue(any("OHLC invariant violated" in v for v in violations))

        # 8. Manifest path traversal in files map
        bad_manifest = {
            "schema_version": "1.0.0",
            "dataset_id": "0123456789abcdef",
            "as_of_date": "2026-08-21",
            "generated_at": "2026-08-21T10:00:00Z",
            "market_timezone": "Asia/Ho_Chi_Minh",
            "market_session_status": "UNKNOWN",
            "freshness": {"status": "UNKNOWN", "expected_as_of_date": "2026-08-21", "reason": "T"},
            "provider": "csv",
            "universe": "ALL",
            "files": {"overview": "../overview.json", "screener": "screener.json", "symbols_base": "symbols/"},
            "quality": {"status": "PASS", "input_rows": 1, "accepted_rows": 1, "rejected_rows": 0, "eligible_symbols": 1, "warnings": []},
        }
        violations, _ = validate_json_deep_structure("data/manifest.json", json.dumps(bad_manifest))
        self.assertTrue(any("files' map mismatch" in v for v in violations))

        # 9. Warnings containing non-strings or raw secrets
        bad_manifest["files"]["overview"] = "overview.json"
        bad_manifest["quality"]["warnings"] = [123, True, {"bad": "object"}, "RAW_SECRET_KEY_AIzaSyD12345678"]
        violations, _ = validate_json_deep_structure("data/manifest.json", json.dumps(bad_manifest))
        self.assertTrue(any("must be a string" in v for v in violations))
        self.assertTrue(any("contains sensitive secret pattern" in v for v in violations))

        # 10. Quality row accounting invariant violated
        bad_manifest["quality"]["warnings"] = []
        bad_manifest["quality"]["input_rows"] = 10
        bad_manifest["quality"]["accepted_rows"] = 5
        bad_manifest["quality"]["rejected_rows"] = 3  # 5 + 3 = 8 != 10
        violations, _ = validate_json_deep_structure("data/manifest.json", json.dumps(bad_manifest))
        self.assertTrue(any("row accounting invariant violated" in v for v in violations))

    def test_url_parser_rejects_subdomain_spoofing_and_localhost(self):
        self.assertTrue(validate_external_url("https://www.w3.org/2000/svg"))
        self.assertTrue(validate_external_url("https://reactjs.org/docs/error-decoder.html?invariant=123"))
        self.assertFalse(validate_external_url("https://www.w3.org.evil.com/malicious.js"))
        self.assertFalse(validate_external_url("http://localhost:5000/secret"))
        self.assertFalse(validate_external_url("javascript:alert(1)"))
        self.assertFalse(validate_external_url("https://www.w3.org/%2e%2e/admin"))

    def test_source_scan_detects_secrets_and_inline_style(self):
        source_dir = os.path.join(self.temp_dir, "source")
        os.makedirs(source_dir, exist_ok=True)
        bad_tsx = os.path.join(source_dir, "BadComponent.tsx")
        with open(bad_tsx, "w", encoding="utf-8") as f:
            f.write("export const C = () => <div style={{\n  color: 'red',\n}}>Hello</div>;")

        violations = scan_source_for_secrets(source_dir)
        self.assertTrue(any("Forbidden inline React style prop found" in v for v in violations))


if __name__ == "__main__":
    unittest.main()
