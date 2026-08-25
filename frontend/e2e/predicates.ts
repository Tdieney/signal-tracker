/**
 * Pure, modular, and unit-tested predicate functions for Playwright E2E and console error filtering.
 */

export interface PageListenerFilter {
  isAllowedConsole?: (msgText: string, locationUrl?: string) => boolean;
  isAllowedPageError?: (errMessage: string) => boolean;
  isAllowedRequestFailed?: (url: string, errorText?: string) => boolean;
}

/**
 * Exact predicate for network request failure on a specific resource URL suffix.
 */
export const createExactRequestFailedPredicate = (expectedUrlSuffix: string) => {
  return (url: string, _errorText?: string): boolean => {
    return url.endsWith(expectedUrlSuffix);
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
    if (!locationUrl) {
      return false;
    }
    return locationUrl.endsWith(resourceSuffix);
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
 */
export const createInvalidSymbolAllowedConsole = (symbol: string) => {
  const expectedSuffix = `/data/symbols/${symbol}.json`;
  return (text: string, locationUrl?: string): boolean => {
    if (isStandardBrowser404Console(text, locationUrl, expectedSuffix)) {
      return true;
    }
    const isAnchoredAppMsg =
      text === `Không tìm thấy dữ liệu cho mã ${symbol}` ||
      text.startsWith(`Không thể tải dữ liệu chi tiết mã ${symbol}:`);
    if (!isAnchoredAppMsg) {
      return false;
    }
    if (locationUrl && locationUrl.includes('/data/') && !locationUrl.endsWith(expectedSuffix)) {
      return false;
    }
    return true;
  };
};

/**
 * Predicate for malformed manifest JSON syntax error.
 */
export const isMalformedManifestAllowedConsole = (text: string, locationUrl?: string): boolean => {
  const isExactSyntaxError =
    /^SyntaxError: (JSON\.parse: unexpected character|Unexpected token ['"<]|Unexpected identifier|JSON Parse error|Unexpected end of JSON input)/.test(text.trim()) ||
    text.startsWith("Lỗi kết nối khi tải manifest.json:");
  if (!isExactSyntaxError) {
    return false;
  }
  if (locationUrl && locationUrl.includes('/data/') && !locationUrl.endsWith("/data/manifest.json")) {
    return false;
  }
  return true;
};

/**
 * Predicate for unsupported manifest schema version.
 */
export const isUnsupportedSchemaAllowedConsole = (text: string, locationUrl?: string): boolean => {
  const isAnchoredSchema =
    text.startsWith("Schema validation failed for manifest.json:") ||
    text.startsWith("Schema validation failed for /data/manifest.json:") ||
    text === "Phiên bản dữ liệu không tương thích";
  if (!isAnchoredSchema) {
    return false;
  }
  if (locationUrl && locationUrl.includes('/data/') && !locationUrl.endsWith("/data/manifest.json")) {
    return false;
  }
  return true;
};

/**
 * Predicate for manifest missing required keys.
 */
export const isMissingKeysAllowedConsole = (text: string, locationUrl?: string): boolean => {
  const isAnchoredMissing =
    text.startsWith("Schema validation failed for manifest.json:") ||
    text.startsWith("Schema validation failed for /data/manifest.json:");
  if (!isAnchoredMissing) {
    return false;
  }
  if (locationUrl && locationUrl.includes('/data/') && !locationUrl.endsWith("/data/manifest.json")) {
    return false;
  }
  return true;
};

/**
 * Predicate for cross-file dataset_id mismatch error on a specific resource.
 */
export const createDatasetIdMismatchAllowedConsole = (resourceSuffix: string) => {
  return (text: string, locationUrl?: string): boolean => {
    const isAnchoredMismatch =
      text.startsWith(`Lỗi xác thực dataset_id cho ${resourceSuffix}: dataset_id mismatch`) ||
      text === `dataset_id mismatch (${resourceSuffix})`;
    if (!isAnchoredMismatch) {
      return false;
    }
    if (locationUrl && locationUrl.includes('/data/') && !locationUrl.endsWith(resourceSuffix)) {
      return false;
    }
    return true;
  };
};
