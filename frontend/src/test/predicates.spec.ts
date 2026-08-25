import { describe, it, expect } from 'vitest';
import {
  isStandardBrowser404Console,
  isManifest404AllowedConsole,
  createExactRequestFailedPredicate,
  createInvalidSymbolAllowedConsole,
  isMalformedManifestAllowedConsole,
  isUnsupportedSchemaAllowedConsole,
  isMissingKeysAllowedConsole,
  createDatasetIdMismatchAllowedConsole,
} from '../../e2e/predicates';

describe('Pure E2E Predicate Functions Unit Tests', () => {
  it('isStandardBrowser404Console matches exact browser 404 formats', () => {
    const chromiumMsg = 'Failed to load resource: the server responded with a status of 404 (Not Found)';
    const webkitMsg = 'Failed to load resource: the server responded with a status of 404 ()';
    const shortMsg = 'Failed to load resource: the server responded with a status of 404';

    expect(isStandardBrowser404Console(chromiumMsg, 'http://localhost/data/manifest.json', '/data/manifest.json')).toBe(true);
    expect(isStandardBrowser404Console(webkitMsg, 'http://localhost/data/manifest.json', '/data/manifest.json')).toBe(true);
    expect(isStandardBrowser404Console(shortMsg, 'http://localhost/data/manifest.json', '/data/manifest.json')).toBe(true);
  });

  it('isStandardBrowser404Console rejects unexpected errors containing 404 keywords or wrong URL', () => {
    const unexpectedMsg = 'UNEXPECTED: Failed to load resource 404 in manifest.json';
    const crashMsg = 'RuntimeError: 404 occurred while fetching manifest.json';
    const valid404 = 'Failed to load resource: the server responded with a status of 404 (Not Found)';

    expect(isStandardBrowser404Console(unexpectedMsg, 'http://localhost/data/manifest.json', '/data/manifest.json')).toBe(false);
    expect(isStandardBrowser404Console(crashMsg, 'http://localhost/data/manifest.json', '/data/manifest.json')).toBe(false);
    expect(isStandardBrowser404Console(valid404, 'http://localhost/data/overview.json', '/data/manifest.json')).toBe(false);
    expect(isStandardBrowser404Console(valid404, 'https://evil.example/assets/crash.js', '/data/manifest.json')).toBe(false);
  });

  it('isManifest404AllowedConsole returns false for non-matching url or unexpected prefix', () => {
    expect(isManifest404AllowedConsole('UNEXPECTED: Failed to load resource 404 in manifest.json', 'http://localhost/data/manifest.json')).toBe(false);
    expect(isManifest404AllowedConsole('Failed to load resource: the server responded with a status of 404 (Not Found)', 'http://localhost/data/overview.json')).toBe(false);
    expect(isManifest404AllowedConsole('Failed to load resource: the server responded with a status of 404 (Not Found)', 'https://evil.example/assets/crash.js')).toBe(false);
  });

  it('createExactRequestFailedPredicate matches exact url suffix', () => {
    const pred = createExactRequestFailedPredicate('/data/manifest.json');
    expect(pred('http://localhost:4173/signal-tracker/data/manifest.json')).toBe(true);
    expect(pred('http://localhost:4173/signal-tracker/data/overview.json')).toBe(false);
    expect(pred('http://localhost:4173/signal-tracker/data/manifest.json.bak')).toBe(false);
    expect(pred('https://evil.example/assets/crash.js')).toBe(false);
  });

  it('createInvalidSymbolAllowedConsole strictly matches browser 404 on symbol endpoint and rejects all other errors', () => {
    const symbolPred = createInvalidSymbolAllowedConsole('UNKNOWNXYZ');
    const valid404 = 'Failed to load resource: the server responded with a status of 404 (Not Found)';
    const crashMsg = 'Không thể tải dữ liệu chi tiết mã UNKNOWNXYZ: expected 404; UNEXPECTED RUNTIME CRASH';

    expect(symbolPred(valid404, 'http://localhost:4173/signal-tracker/data/symbols/UNKNOWNXYZ.json')).toBe(true);

    // Negative controls
    expect(symbolPred(crashMsg, 'https://evil.example/assets/crash.js')).toBe(false);
    expect(symbolPred(crashMsg, 'http://localhost:4173/signal-tracker/data/symbols/UNKNOWNXYZ.json')).toBe(false);
    expect(symbolPred(valid404, 'http://localhost:4173/signal-tracker/data/symbols/FPT.json')).toBe(false);
    expect(symbolPred(valid404, 'https://evil.example/assets/crash.js')).toBe(false);
  });

  it('isMalformedManifestAllowedConsole matches exact engine syntax errors and rejects unrelated payloads or wrong URL', () => {
    const jsonError = 'SyntaxError: JSON.parse: unexpected character at line 1 column 1 of the JSON data';
    const tokenError = 'SyntaxError: Unexpected token < in JSON at position 0';
    const crashMsg = 'SyntaxError: Unexpected token < while parsing unrelated payload';

    expect(isMalformedManifestAllowedConsole(jsonError, 'http://localhost:4173/signal-tracker/assets/api.js')).toBe(true);
    expect(isMalformedManifestAllowedConsole(tokenError, 'http://localhost:4173/signal-tracker/assets/api.js')).toBe(true);

    // Negative controls
    expect(isMalformedManifestAllowedConsole(crashMsg, 'https://evil.example/assets/crash.js')).toBe(false);
    expect(isMalformedManifestAllowedConsole(jsonError, 'https://evil.example/assets/crash.js')).toBe(false);
  });

  it('isUnsupportedSchemaAllowedConsole and isMissingKeysAllowedConsole match anchored errors', () => {
    const schemaError = 'Schema validation failed for manifest.json: JSHandle@object';
    const schemaErrorObj = 'Schema validation failed for manifest.json: {_errors: [], schema_version: []}';
    const crashMsg = 'UNEXPECTED Schema validation error in custom module';

    expect(isUnsupportedSchemaAllowedConsole(schemaError, 'http://localhost:4173/signal-tracker/assets/api.js')).toBe(true);
    expect(isUnsupportedSchemaAllowedConsole(schemaErrorObj, 'http://localhost:4173/signal-tracker/assets/api.js')).toBe(true);
    expect(isMissingKeysAllowedConsole(schemaError, 'http://localhost:4173/signal-tracker/assets/api.js')).toBe(true);

    // Negative controls
    expect(isUnsupportedSchemaAllowedConsole(crashMsg, 'https://evil.example/assets/crash.js')).toBe(false);
    expect(isMissingKeysAllowedConsole(crashMsg, 'https://evil.example/assets/crash.js')).toBe(false);
    expect(isUnsupportedSchemaAllowedConsole(schemaError, 'https://evil.example/assets/crash.js')).toBe(false);
  });

  it('createDatasetIdMismatchAllowedConsole strictly matches exact equality and location', () => {
    const predOverview = createDatasetIdMismatchAllowedConsole('/data/overview.json');
    const validMsg = 'Lỗi xác thực dataset_id cho /data/overview.json: dataset_id mismatch';
    const crashMsg = 'Lỗi xác thực dataset_id cho /data/overview.json: dataset_id mismatch UNEXPECTED RUNTIME CRASH';

    expect(predOverview(validMsg, 'http://localhost:4173/signal-tracker/data/overview.json')).toBe(true);

    // Negative controls
    expect(predOverview(crashMsg, 'https://evil.example/assets/crash.js')).toBe(false);
    expect(predOverview(validMsg, 'https://evil.example/assets/crash.js')).toBe(false);
    expect(predOverview(validMsg, 'http://localhost:4173/signal-tracker/data/screener.json')).toBe(false);
  });
});
