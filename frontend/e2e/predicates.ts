/**
 * Pure, testable predicate functions for Playwright E2E and console error filtering.
 */

export interface PageListenerFilter {
  isAllowedConsole?: (msgText: string, locationUrl?: string) => boolean;
  isAllowedPageError?: (errMessage: string) => boolean;
  isAllowedRequestFailed?: (url: string, errorText?: string) => boolean;
}

export const createExactRequestFailedPredicate = (expectedUrlSuffix: string) => {
  return (url: string, _errorText?: string): boolean => {
    return url.endsWith(expectedUrlSuffix);
  };
};

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
  if (resourceSuffix && locationUrl) {
    return locationUrl.endsWith(resourceSuffix);
  }
  return true;
};

export const isManifest404AllowedConsole = (text: string, locationUrl?: string): boolean => {
  return isStandardBrowser404Console(text, locationUrl, '/data/manifest.json');
};
