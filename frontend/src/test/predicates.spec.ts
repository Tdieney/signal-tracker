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

  it('isStandardBrowser404Console rejects unexpected errors containing 404 keywords', () => {
    const unexpectedMsg = 'UNEXPECTED: Failed to load resource 404 in manifest.json';
    const crashMsg = 'RuntimeError: 404 occurred while fetching manifest.json';

    expect(isStandardBrowser404Console(unexpectedMsg, 'http://localhost/data/manifest.json', '/data/manifest.json')).toBe(false);
    expect(isStandardBrowser404Console(crashMsg, 'http://localhost/data/manifest.json', '/data/manifest.json')).toBe(false);
  });

  it('isManifest404AllowedConsole returns false for non-matching url or unexpected prefix', () => {
    expect(isManifest404AllowedConsole('UNEXPECTED: Failed to load resource 404 in manifest.json', 'http://localhost/data/manifest.json')).toBe(false);
    expect(isManifest404AllowedConsole('Failed to load resource: the server responded with a status of 404 (Not Found)', 'http://localhost/data/overview.json')).toBe(false);
  });

  it('createExactRequestFailedPredicate matches exact url suffix', () => {
    const pred = createExactRequestFailedPredicate('/data/manifest.json');
    expect(pred('http://localhost:4173/signal-tracker/data/manifest.json')).toBe(true);
    expect(pred('http://localhost:4173/signal-tracker/data/overview.json')).toBe(false);
    expect(pred('http://localhost:4173/signal-tracker/data/manifest.json.bak')).toBe(false);
  });

  it('createInvalidSymbolAllowedConsole matches only symbol 404 and rejects random errors', () => {
    const symbolPred = createInvalidSymbolAllowedConsole('UNKNOWNXYZ');
    const valid404 = 'Failed to load resource: the server responded with a status of 404';
    expect(symbolPred(valid404, 'http://localhost/data/symbols/UNKNOWNXYZ.json')).toBe(true);
    expect(symbolPred(valid404, 'http://localhost/data/symbols/FPT.json')).toBe(false);
    expect(symbolPred('UNEXPECTED ERROR in UNKNOWNXYZ', 'http://localhost/data/symbols/UNKNOWNXYZ.json')).toBe(false);
  });

  it('isMalformedManifestAllowedConsole matches JSON syntax errors and rejects unrelated errors', () => {
    const jsonError = 'SyntaxError: JSON.parse: unexpected character at line 1';
    expect(isMalformedManifestAllowedConsole(jsonError)).toBe(true);
    expect(isMalformedManifestAllowedConsole('UNEXPECTED: SyntaxError elsewhere')).toBe(false);
  });

  it('isUnsupportedSchemaAllowedConsole and isMissingKeysAllowedConsole match schema errors', () => {
    const schemaError = 'Schema validation failed for manifest.json: invalid version';
    expect(isUnsupportedSchemaAllowedConsole(schemaError)).toBe(true);
    expect(isMissingKeysAllowedConsole(schemaError)).toBe(true);
    expect(isUnsupportedSchemaAllowedConsole('UNEXPECTED: Schema error')).toBe(false);
  });

  it('createDatasetIdMismatchAllowedConsole matches dataset_id mismatch for target file only', () => {
    const predOverview = createDatasetIdMismatchAllowedConsole('/data/overview.json');
    const msg = 'Lỗi xác thực dataset_id cho /data/overview.json: dataset_id mismatch';
    expect(predOverview(msg)).toBe(true);
    expect(predOverview('Lỗi xác thực dataset_id cho /data/screener.json: dataset_id mismatch')).toBe(false);
    expect(predOverview('UNEXPECTED: dataset_id mismatch random')).toBe(false);
  });
});
