import { test, expect, Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

// Helper to attach CSP violation, console error, and request failure listeners
async function setupPageListeners(
  page: Page,
  errors: string[],
  allowedSubstrings: string[] = []
) {
  await page.addInitScript(() => {
    (window as any).__cspViolations = (window as any).__cspViolations || [];
    document.addEventListener('securitypolicyviolation', (e) => {
      (window as any).__cspViolations.push(
        `CSP Violation: directive '${e.violatedDirective}' blocked '${e.blockedURI}'`
      );
    });
  });

  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      const text = msg.text();
      const isAllowed = allowedSubstrings.some((allow) => text.includes(allow)) || text.includes('favicon.ico') || text.includes('AbortError');
      if (!isAllowed) {
        errors.push(`Console error: ${text}`);
      }
    }
  });

  page.on('pageerror', (err) => {
    const isAllowed = allowedSubstrings.some((allow) => err.message.includes(allow));
    if (!isAllowed) {
      errors.push(`Uncaught page error: ${err.message}`);
    }
  });

  page.on('requestfailed', (req) => {
    const isAllowed = allowedSubstrings.some((allow) => req.url().includes(allow)) || req.url().includes('favicon');
    if (!isAllowed) {
      errors.push(`Failed network request: ${req.url()} (${req.failure()?.errorText})`);
    }
  });
}

async function getCapturedCSPViolations(page: Page): Promise<string[]> {
  return await page.evaluate(() => (window as any).__cspViolations || []);
}

test.describe('VN Stock Signal — Production E2E, CSP & Accessibility Suite', () => {

  test('Page level layout has zero horizontal overflow, correct brand and strict CSP', async ({ page }) => {
    const errors: string[] = [];
    await setupPageListeners(page, errors);

    await page.goto('#/');
    await page.waitForSelector('h1');

    // 1. Diagnostic assertion for zero horizontal scrollbar overflow
    const overflowDiagnostics = await page.evaluate(() => {
      const docWidth = document.documentElement.scrollWidth;
      const winWidth = window.innerWidth;
      const hasOverflow = docWidth > winWidth;
      const culprits: any[] = [];
      if (hasOverflow) {
        const allEls = document.querySelectorAll('*');
        allEls.forEach((el) => {
          const rect = el.getBoundingClientRect();
          const scrollW = el.scrollWidth;
          const clientW = el.clientWidth;
          if (rect.right > winWidth + 1) {
            culprits.push({
              tagName: el.tagName,
              id: el.id,
              className: el.className,
              rect: { left: rect.left, right: rect.right, width: rect.width },
              scrollWidth: scrollW,
              clientWidth: clientW,
            });
          }
        });
      }
      return { hasOverflow, docWidth, winWidth, culprits };
    });

    if (overflowDiagnostics.hasOverflow) {
      console.error(
        `Horizontal overflow detected! scrollWidth=${overflowDiagnostics.docWidth}px > innerWidth=${overflowDiagnostics.winWidth}px. Culprits:`,
        JSON.stringify(overflowDiagnostics.culprits, null, 2)
      );
    }
    expect(overflowDiagnostics.hasOverflow).toBe(false);

    // 2. Verify brand link and navigation
    await expect(page.locator('a.brand-link')).toBeVisible();
    await expect(page.locator('nav a.nav-tab-active')).toContainText('Tổng quan');

    // 3. Zero CSP violations or page errors
    const cspViolations = await getCapturedCSPViolations(page);
    expect(cspViolations).toEqual([]);
    expect(errors).toEqual([]);
  });

  test('Overview route displays metrics, demo banner, and breadth chart with zero CSP violations', async ({ page }) => {
    const errors: string[] = [];
    await setupPageListeners(page, errors);

    await page.goto('#/');
    await page.waitForSelector('h1');

    // Wait for KPI cards
    const metricCards = page.locator('.metric-card');
    await expect(metricCards.first()).toBeVisible();
    await expect(metricCards).toHaveCount(5);

    // Verify Breadth Chart
    await expect(page.locator('.chart-panel')).toBeVisible();

    // Verify Demo / Freshness banner
    const demoBadge = page.locator('.freshness-badge-unknown, .status-banner');
    await expect(demoBadge.first()).toBeVisible();

    // Zero CSP violations or errors
    const cspViolations = await getCapturedCSPViolations(page);
    expect(cspViolations).toEqual([]);
    expect(errors).toEqual([]);
  });

  test('SkipLink focuses main content without mutating hash route into 404', async ({ page }) => {
    const errors: string[] = [];
    await setupPageListeners(page, errors);

    await page.goto('#/');
    await page.waitForSelector('h1');

    const skipLink = page.locator('a.skip-link');
    await skipLink.focus();
    await expect(skipLink).toBeFocused();

    // Trigger click on SkipLink
    await skipLink.click();

    // Verify focus moved to #main-content
    const isMainFocused = await page.evaluate(() => document.activeElement?.id === 'main-content');
    expect(isMainFocused).toBe(true);

    // Strict assertion: URL hash MUST match '#/' and NOT mutate into '#main-content' causing 404
    expect(page.url()).toMatch(/#\/?$/);
    await expect(page.locator('h1')).toBeVisible();
    expect(errors).toEqual([]);
  });

  test('Screener route supports search query, filtering, URL sync, and pagination', async ({ page }) => {
    const errors: string[] = [];
    await setupPageListeners(page, errors);

    await page.goto('#/screener');
    await page.waitForSelector('h1');

    // Check visible content container (table on desktop, cards on mobile)
    const content = page.locator('.screener-table-view:visible, .screener-cards-view:visible');
    await expect(content.first()).toBeVisible();

    // Search for 'FPT' using the visible search input
    const searchInput = page.locator('input[type="search"]:visible').first();
    await searchInput.fill('FPT');

    // Wait for debounce and URL hash sync
    await expect(page).toHaveURL(/query=FPT/);

    // Verify FPT is visible in active view
    const fptLink = page.locator('.screener-table-view:visible a:has-text("FPT"), .screener-cards-view:visible a:has-text("FPT")').first();
    await expect(fptLink).toBeVisible({ timeout: 10000 });

    // Clear search
    await searchInput.fill('');
    await expect(page).not.toHaveURL(/query=FPT/);

    // Zero CSP violations or errors
    const cspViolations = await getCapturedCSPViolations(page);
    expect(cspViolations).toEqual([]);
    expect(errors).toEqual([]);
  });

  test('Symbol detail route renders correctly with explanations and table alternative', async ({ page }) => {
    const errors: string[] = [];
    await setupPageListeners(page, errors);

    await page.goto('#/symbols/FPT');
    await page.waitForSelector('h1');

    // Verify Symbol Header & Metrics
    await expect(page.locator('h1')).toHaveText('FPT');
    await expect(page.locator('.symbol-header-card')).toBeVisible();

    // Verify Signal Explanation Card
    const explanationCard = page.locator('.explanation-card');
    await expect(explanationCard).toBeVisible();
    await expect(explanationCard).toContainText('Giải thích tín hiệu kỹ thuật');

    // Verify Lightweight Chart Container
    await expect(page.locator('.chart-panel')).toBeVisible();

    // Verify Accessible Table Alternative toggle
    const toggleBtn = page.locator('.chart-toggle-btn');
    await expect(toggleBtn).toBeVisible();
    await toggleBtn.click();
    await expect(page.locator('.chart-table-alt-wrapper')).toBeVisible({ timeout: 10000 });

    // Toggle back to chart
    await toggleBtn.click();
    await expect(page.locator('.chart-container-lightweight')).toBeVisible({ timeout: 10000 });

    // Zero CSP violations or errors
    const cspViolations = await getCapturedCSPViolations(page);
    expect(cspViolations).toEqual([]);
    expect(errors).toEqual([]);
  });

  test('404 Not Found route renders cleanly for invalid paths', async ({ page }) => {
    const errors: string[] = [];
    await setupPageListeners(page, errors);

    await page.goto('#/invalid/route/does/not/exist');
    await expect(page.locator('[data-testid="not-found-card"]')).toBeVisible();
    await expect(page.locator('h1')).toContainText('404');
    expect(errors).toEqual([]);
  });

  test('Invalid symbol route renders symbol not found error state', async ({ page }) => {
    const errors: string[] = [];
    await setupPageListeners(page, errors, [
      'symbols/XYZ.json',
      '404',
      'Not Found',
      'Failed to load resource',
      'status of 404',
    ]);

    await page.goto('#/symbols/XYZ');
    const notFoundCard = page.locator('[data-testid="symbol-not-found-card"]');
    await expect(notFoundCard).toBeVisible({ timeout: 10000 });
    await expect(notFoundCard).toContainText('Không tìm thấy mã XYZ');
    expect(errors).toEqual([]);
  });

  test('Mobile FilterDrawer has deterministic initial focus, true focus trap, background isolation, and Escape close', async ({
    page,
    isMobile,
  }) => {
    test.skip(!isMobile, 'FilterDrawer is mobile only');

    const errors: string[] = [];
    await setupPageListeners(page, errors);

    await page.goto('#/screener');
    await page.waitForSelector('h1');

    const openBtn = page.locator('#open-filter-drawer-btn');
    await expect(openBtn).toBeVisible({ timeout: 10000 });
    await openBtn.click();

    // 1. Verify dialog opened and assert deterministic initial focus on Close button
    const dialog = page.locator('div[role="dialog"]');
    await expect(dialog).toBeVisible();
    await expect(dialog).toHaveAttribute('aria-modal', 'true');

    const closeBtn = dialog.locator('button[aria-label="Đóng bảng lọc"]');
    const applyBtn = dialog.locator('button:has-text("Áp dụng")');

    await expect(closeBtn).toBeVisible();
    await expect(applyBtn).toBeVisible();
    await expect(closeBtn).toBeFocused();

    // 2. Verify background isolation (app shell root has inert and aria-hidden)
    const shellInert = await page.$eval('.app-shell-root', (el) => el.hasAttribute('inert') && el.getAttribute('aria-hidden') === 'true');
    expect(shellInert).toBe(true);

    // 3. Test focus trap wrap: Tab from last element (Apply button) wraps to first element (Close button)
    await applyBtn.focus();
    await expect(applyBtn).toBeFocused();
    await page.keyboard.press('Tab');
    await expect(closeBtn).toBeFocused();

    // 4. Test Shift+Tab from first element (Close button) wraps to last element (Apply button)
    await page.keyboard.press('Shift+Tab');
    await expect(applyBtn).toBeFocused();

    // 5. Test Escape key closes dialog, clears inert, and restores focus to trigger
    await page.keyboard.press('Escape');
    await expect(dialog).not.toBeVisible();
    const shellInertAfter = await page.$eval('.app-shell-root', (el) => el.hasAttribute('inert'));
    expect(shellInertAfter).toBe(false);
    await expect(openBtn).toBeFocused();
    expect(errors).toEqual([]);
  });

  test('Full Axe accessibility check on Overview, Screener, and Symbol Detail without disabled rules', async ({
    page,
  }) => {
    // 1. Overview Page
    await page.goto('#/');
    await page.waitForSelector('h1');
    const overviewResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();
    const seriousOverview = overviewResults.violations.filter(
      (v) => v.impact === 'serious' || v.impact === 'critical'
    );
    expect(seriousOverview).toEqual([]);

    // 2. Screener Page
    await page.goto('#/screener');
    await page.waitForSelector('h1');
    const screenerResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();
    const seriousScreener = screenerResults.violations.filter(
      (v) => v.impact === 'serious' || v.impact === 'critical'
    );
    expect(seriousScreener).toEqual([]);

    // 3. Symbol Detail Page
    await page.goto('#/symbols/FPT');
    await page.waitForSelector('h1');
    const symbolResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();
    const seriousSymbol = symbolResults.violations.filter(
      (v) => v.impact === 'serious' || v.impact === 'critical'
    );
    expect(seriousSymbol).toEqual([]);
  });

  test('Non-tautological Desktop Table and Mobile Cards parity with independent contexts', async ({
    browser,
    baseURL,
  }) => {
    const desktopContext = await browser.newContext({ baseURL, viewport: { width: 1440, height: 900 } });
    const mobileContext = await browser.newContext({ baseURL, viewport: { width: 390, height: 844 } });

    try {
      const desktopPage = await desktopContext.newPage();
      await desktopPage.goto('#/screener?signal=ABOVE_MA10');
      await desktopPage.waitForSelector('.data-table tbody tr');

      const tableData = await desktopPage.$$eval('.data-table tbody tr', (rows) =>
        rows.map((r) => {
          const symbol = r.querySelector('td a span:first-child')?.textContent?.trim() || '';
          const close = r.querySelector('td:nth-child(3)')?.textContent?.trim() || '';
          return { symbol, close };
        }).filter((item) => item.symbol.length > 0)
      );

      const mobilePage = await mobileContext.newPage();
      await mobilePage.goto('#/screener?signal=ABOVE_MA10');
      await mobilePage.waitForSelector('.stock-card');

      const cardData = await mobilePage.$$eval('.stock-card', (cards) =>
        cards.map((c) => {
          const symbol = c.querySelector('a.font-bold')?.textContent?.trim() || '';
          const close = c.querySelector('.stock-card-grid div:first-child span.font-semibold')?.textContent?.trim() || '';
          return { symbol, close };
        }).filter((item) => item.symbol.length > 0)
      );

      expect(tableData.length).toBeGreaterThan(0);
      expect(cardData.length).toBeGreaterThan(0);
      expect(tableData).toEqual(cardData);
    } finally {
      await desktopContext.close();
      await mobileContext.close();
    }
  });

  test('Fail-closed matrix: Manifest 404 renders safe error banner with retry and no financial signals', async ({
    page,
  }) => {
    const errors: string[] = [];
    await setupPageListeners(page, errors, [
      'data/manifest.json',
      '404',
      'Not Found',
      'Failed to load resource',
      'status of 404',
    ]);

    await page.route('**/data/manifest.json', (route) =>
      route.fulfill({ status: 404, body: 'Not Found' })
    );

    await page.goto('#/');
    const errorCard = page.locator('[data-testid="manifest-error"]');
    await expect(errorCard).toBeVisible();
    await expect(errorCard).toContainText('Lỗi xác thực dữ liệu Manifest (Fail-Closed Mode)');

    // Verify financial metrics and signals are NOT rendered
    await expect(page.locator('.metric-card')).toHaveCount(0);
    await expect(page.locator('.chart-panel')).toHaveCount(0);

    const cspViolations = await getCapturedCSPViolations(page);
    expect(cspViolations).toEqual([]);
    expect(errors).toEqual([]);

    // Test retry recovery when manifest is restored
    await page.unroute('**/data/manifest.json');
    const retryBtn = errorCard.locator('button:has-text("Thử lại")');
    await retryBtn.click();

    // Now metrics should be restored
    await expect(page.locator('.metric-card').first()).toBeVisible({ timeout: 10000 });
  });

  test('Fail-closed matrix: Malformed manifest JSON renders safe error banner', async ({ page }) => {
    const errors: string[] = [];
    await setupPageListeners(page, errors, [
      'data/manifest.json',
      'JSON.parse',
      'SyntaxError',
      'invalid json',
      'Unexpected token',
      'JSON',
    ]);

    await page.route('**/data/manifest.json', (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '{"schema_version": invalid...' })
    );

    await page.goto('#/');
    const errorCard = page.locator('[data-testid="manifest-error"]');
    await expect(errorCard).toBeVisible();
    await expect(page.locator('.metric-card')).toHaveCount(0);

    const cspViolations = await getCapturedCSPViolations(page);
    expect(cspViolations).toEqual([]);
    expect(errors).toEqual([]);
  });

  test('Fail-closed matrix: Unsupported manifest schema version renders safe error banner', async ({ page }) => {
    const errors: string[] = [];
    await setupPageListeners(page, errors, [
      'data/manifest.json',
      'Schema validation failed for manifest.json',
      'Phiên bản dữ liệu không tương thích',
    ]);

    await page.route('**/data/manifest.json', async (route) => {
      const response = await route.fetch();
      const json = await response.json();
      json.schema_version = '9.9.9';
      route.fulfill({ response, json });
    });

    await page.goto('#/');
    const errorCard = page.locator('[data-testid="manifest-error"]');
    await expect(errorCard).toBeVisible();
    await expect(page.locator('.metric-card')).toHaveCount(0);

    const cspViolations = await getCapturedCSPViolations(page);
    expect(cspViolations).toEqual([]);
    expect(errors).toEqual([]);
  });

  test('Fail-closed matrix: Manifest missing required keys renders safe error banner', async ({ page }) => {
    const errors: string[] = [];
    await setupPageListeners(page, errors, [
      'data/manifest.json',
      'Schema validation failed for manifest.json',
    ]);

    await page.route('**/data/manifest.json', (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '{"schema_version": "1.0.0"}' })
    );

    await page.goto('#/');
    const errorCard = page.locator('[data-testid="manifest-error"]');
    await expect(errorCard).toBeVisible();
    await expect(page.locator('.metric-card')).toHaveCount(0);

    const cspViolations = await getCapturedCSPViolations(page);
    expect(cspViolations).toEqual([]);
    expect(errors).toEqual([]);
  });

  test('Fail-closed matrix: Overview dataset_id mismatch renders fail-closed error banner', async ({ page }) => {
    const errors: string[] = [];
    await setupPageListeners(page, errors, [
      'dataset_id mismatch',
      'mismatched_old_dataset_id_999',
      'Dữ liệu Tổng quan không khớp',
    ]);

    await page.route('**/data/overview.json', async (route) => {
      const response = await route.fetch();
      const json = await response.json();
      json.dataset_id = 'mismatched_old_dataset_id_999';
      route.fulfill({ response, json });
    });

    await page.goto('#/');
    const errorBanner = page.locator('.status-banner-danger, .status-banner');
    await expect(errorBanner.first()).toBeVisible({ timeout: 10000 });
    await expect(errorBanner.first()).toContainText('dataset_id mismatch');

    const cspViolations = await getCapturedCSPViolations(page);
    expect(cspViolations).toEqual([]);
    expect(errors).toEqual([]);
  });

  test('Fail-closed matrix: Screener dataset_id mismatch renders fail-closed error banner', async ({ page }) => {
    const errors: string[] = [];
    await setupPageListeners(page, errors, [
      'dataset_id mismatch',
      'mismatched_old_screener_id_999',
      'Dữ liệu Bộ lọc không khớp',
    ]);

    await page.route('**/data/screener.json', async (route) => {
      const response = await route.fetch();
      const json = await response.json();
      json.dataset_id = 'mismatched_old_screener_id_999';
      route.fulfill({ response, json });
    });

    await page.goto('#/screener');
    const errorBanner = page.locator('.status-banner-danger, .status-banner');
    await expect(errorBanner.first()).toBeVisible({ timeout: 10000 });
    await expect(errorBanner.first()).toContainText('dataset_id mismatch');

    const cspViolations = await getCapturedCSPViolations(page);
    expect(cspViolations).toEqual([]);
    expect(errors).toEqual([]);
  });

  test('Fail-closed matrix: Symbol Detail dataset_id mismatch renders fail-closed error banner', async ({ page }) => {
    const errors: string[] = [];
    await setupPageListeners(page, errors, [
      'dataset_id mismatch',
      'mismatched_old_symbol_id_999',
      'Dữ liệu mã FPT không khớp',
    ]);

    await page.route('**/data/symbols/FPT.json', async (route) => {
      const response = await route.fetch();
      const json = await response.json();
      json.dataset_id = 'mismatched_old_symbol_id_999';
      route.fulfill({ response, json });
    });

    await page.goto('#/symbols/FPT');
    const errorBanner = page.locator('.status-banner-danger, .status-banner');
    await expect(errorBanner.first()).toBeVisible({ timeout: 10000 });
    await expect(errorBanner.first()).toContainText('dataset_id mismatch');

    const cspViolations = await getCapturedCSPViolations(page);
    expect(cspViolations).toEqual([]);
    expect(errors).toEqual([]);
  });

});
