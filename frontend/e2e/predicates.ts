/**
 * Pure, modular, and unit-tested predicate functions for Playwright E2E and console error filtering.
 * All predicates use exact equality or strictly anchored regex patterns (^ and $), and validate trusted origins via URL parser.
 */

export interface PageListenerFilter {
  isAllowedConsole?: (msgText: string, locationUrl?: string) => boolean;
  isAllowedPageError?: (errMessage: string) => boolean;
  isAllowedRequestFailed?: (url: string, errorText?: string) => boolean;
}

const TRUSTED_HOSTNAMES = new Set(['localhost', '127.0.0.1', '::1', '[::1]', 'tdieney.github.io']);

/**
 * Validates whether a given URL has a trusted protocol, hostname, and origin structure.
 * Rejects credentials spoofing (user:pass@), subdomain/suffix spoofing, non-http/https protocols, and malformed URLs.
 */
export const isTrustedOrigin = (rawUrl?: string): boolean => {
  if (!rawUrl) return true;
  try {
    const parsed = new URL(rawUrl);
    // Protocol must strictly be http: or https:
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
      return false;
    }
    // Reject credentials in URL
    if (parsed.username || parsed.password) {
      return false;
    }
    // Exact hostname match
    if (!TRUSTED_HOSTNAMES.has(parsed.hostname)) {
      return false;
    }
    return true;
  } catch {
    // Malformed URLs are rejected
    return false;
  }
};

/**
 * Exact predicate for network request failure on a specific resource URL suffix.
 */
export const createExactRequestFailedPredicate = (expectedUrlSuffix: string) => {
  return (url: string, _errorText?: string): boolean => {
    if (!url.endsWith(expectedUrlSuffix)) {
      return false;
    }
    return isTrustedOrigin(url);
  };
};

/**
 * Exact predicate for standard browser console 404 message tied to an exact resource URL.
 */
export const isStandardBrowser404Console = (
  text: string,
  locationUrl?: string,
  resourceSuffix?: string
): boolean => {
  const isExactBrowser404 = /^Failed to load resource: the server responded with a status of 404(\s*\([^)]*\))?$/.test(
    text.trim()
  );
  if (!isExactBrowser404) {
    return false;
  }
  if (resourceSuffix) {
    if (!locationUrl || !locationUrl.endsWith(resourceSuffix)) {
      return false;
    }
    return isTrustedOrigin(locationUrl);
  }
  return true;
};

/**
 * Predicate for Manifest 404 error scenario.
 */
export const isManifest404AllowedConsole = (text: string, locationUrl?: string): boolean => {
  return isStandardBrowser404Console(text, locationUrl, '/data/manifest.json');
};

/**
 * Predicate for invalid symbol route 404 scenario.
 * Strictly requires standard browser 404 on the exact symbol endpoint.
 */
export const createInvalidSymbolAllowedConsole = (symbol: string) => {
  const expectedSuffix = `/data/symbols/${symbol}.json`;
  return (text: string, locationUrl?: string): boolean => {
    return isStandardBrowser404Console(text, locationUrl, expectedSuffix);
  };
};

/**
 * Predicate for malformed manifest JSON syntax error.
 * Strictly matches standard engine JSON syntax errors, anchored from ^ to $.
 */
export const isMalformedManifestAllowedConsole = (text: string, locationUrl?: string): boolean => {
  const isExactSyntaxError =
    /^SyntaxError: (JSON\.parse: unexpected character at line \d+ column \d+ of the JSON data|Unexpected token ['"<][^]*is not valid JSON|Unexpected token [A-Za-z0-9_<]+ in JSON at position \d+|JSON Parse error: Unexpected identifier "[^"]*"|Unexpected end of JSON input)$/.test(
      text.trim()
    );
  if (!isExactSyntaxError) {
    return false;
  }
  return isTrustedOrigin(locationUrl);
};

/**
 * Predicate for unsupported manifest schema version.
 * Strictly matches exact application schema validation console format.
 */
export const isUnsupportedSchemaAllowedConsole = (text: string, locationUrl?: string): boolean => {
  const isExactSchema = /^Schema validation failed for manifest\.json: (\{.*\}|JSHandle@object)$/.test(text.trim());
  if (!isExactSchema) {
    return false;
  }
  return isTrustedOrigin(locationUrl);
};

/**
 * Predicate for manifest missing required keys.
 * Strictly matches exact application schema validation console format.
 */
export const isMissingKeysAllowedConsole = (text: string, locationUrl?: string): boolean => {
  const isExactMissing = /^Schema validation failed for manifest\.json: (\{.*\}|JSHandle@object)$/.test(text.trim());
  if (!isExactMissing) {
    return false;
  }
  return isTrustedOrigin(locationUrl);
};

/**
 * Predicate for cross-file dataset_id mismatch error on a specific resource.
 * Strictly matches exact equality and exact resource location.
 */
export const createDatasetIdMismatchAllowedConsole = (resourceSuffix: string) => {
  return (text: string, locationUrl?: string): boolean => {
    const isExactMismatch = text === `Lỗi xác thực dataset_id cho ${resourceSuffix}: dataset_id mismatch`;
    if (!isExactMismatch) {
      return false;
    }
    if (!locationUrl || !locationUrl.endsWith(resourceSuffix)) {
      return false;
    }
    return isTrustedOrigin(locationUrl);
  };
};
