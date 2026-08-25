import { describe, it, expect } from 'vitest';
import {
  isStandardBrowser404Console,
  isManifest404AllowedConsole,
  createExactRequestFailedPredicate,
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
});
