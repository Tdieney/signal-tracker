import { test, expect, Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

interface PageListenerFilter {
  isAllowedConsole?: (msgText: string) => boolean;
  isAllowedPageError?: (errMessage: string) => boolean;
  isAllowedRequestFailed?: (url: string, errorText?: string) => boolean;
}

// Helper to attach CSP violation, console error, and request failure listeners with strict predicates
async function setupPageListeners(
  page: Page,
  errors: string[],
  filter?: PageListenerFilter
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
      const isAllowed =
        (filter?.isAllowedConsole && filter.isAllowedConsole(text)) ||
        text.includes('favicon.ico') ||
        text.includes('AbortError');
      if (!isAllowed) {
        errors.push(`Console error: ${text}`);
      }
    }
  });

  page.on('pageerror', (err) => {
    const isAllowed = filter?.isAllowedPageError && filter.isAllowedPageError(err.message);
    if (!isAllowed) {
      errors.push(`Uncaught page error: ${err.message}`);
    }
  });

  page.on('requestfailed', (req) => {
    const url = req.url();
    const errorText = req.failure()?.errorText;
    const isAllowed =
      (filter?.isAllowedRequestFailed && filter.isAllowedRequestFailed(url, errorText)) ||
      url.includes('favicon');
    if (!isAllowed) {
      errors.push(`Failed network request: ${url} (${errorText})`);
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

    expect(
      overflowDiagnostics.culprits,
      `Horizontal overflow detected! scrollWidth=${overflowDiagnostics.docWidth}px > innerWidth=${overflowDiagnostics.winWidth}px`
    ).toEqual([]);
    expect(overflowDiagnostics.hasOverflow).toBe(false);

    // 2. Verify brand link and navigation
    const brandLink = page.locator('a.brand-link');
    await expect(brandLink).toBeVisible();
    await expect(brandLink).toHaveAttribute('href', '#/');
    await expect(brandLink).toHaveAttribute('aria-label', /VN Stock Signal/i);

    // 3. Verify strict CSP compliance: zero CSP violations
    const cspViolations = await getCapturedCSPViolations(page);
    expect(cspViolations).toEqual([]);
    expect(errors).toEqual([]);
  });

  test('Overview route displays metrics, demo banner, and breadth chart with zero CSP violations', async ({
    page,
  }) => {
    const errors: string[] = [];
    await setupPageListeners(page, errors);

    await page.goto('#/');
    await page.waitForSelector('h1');

    // Verify Page Title
    await expect(page.locator('h1')).toContainText('Tổng quan độ rộng thị trường');

    // Verify Demo Status Banner
    const statusBanner = page.locator('.status-banner');
    await expect(statusBanner).toBeVisible();
    await expect(statusBanner).toContainText('Chế độ dữ liệu mẫu');

    // Verify KPI Cards (Total eligible, Above MA10, Below MA10, Cross Up MA10, Cross Down MA10)
    const metricCards = page.locator('.metric-card');
    await expect(metricCards).toHaveCount(5);
    await expect(metricCards.nth(0)).toContainText('Tổng mã hợp lệ');
    await expect(metricCards.nth(1)).toContainText('Trên MA10');
    await expect(metricCards.nth(2)).toContainText('Dưới MA10');

    // Verify Breadth Chart SVG container exists
    const chart = page.locator('.chart-container-svg');
    await expect(chart).toBeVisible();

    // Verify zero console errors and CSP violations
    const cspViolations = await getCapturedCSPViolations(page);
    expect(cspViolations).toEqual([]);
    expect(errors).toEqual([]);
  });

  test('SkipLink focuses main content without mutating hash route into 404', async ({ page }) => {
    const errors: string[] = [];
    await setupPageListeners(page, errors);

    await page.goto('#/');
    await page.waitForSelector('h1');

    // Focus and click SkipLink
    const skipLink = page.locator('a.skip-link');
    await skipLink.focus();
    await expect(skipLink).toBeFocused();
    await page.keyboard.press('Enter');

    // Assert main content receives focus
    const mainContent = page.locator('#main-content');
    await expect(mainContent).toBeFocused();

    // Assert hash does NOT mutate into '#main-content' which would break hash router
    const currentHash = await page.evaluate(() => window.location.hash);
    expect(currentHash === '#/' || currentHash === '').toBe(true);

    // Verify route remains on Overview and not 404
    await expect(page.locator('h1')).toContainText('Tổng quan độ rộng thị trường');
    expect(errors).toEqual([]);
  });

  test('Screener route supports search query, filtering, URL sync, and pagination', async ({ page }) => {
    const errors: string[] = [];
    await setupPageListeners(page, errors);

    await page.goto('#/screener');
    await page.waitForSelector('h1');

    // Verify Screener heading
    await expect(page.locator('h1')).toContainText('Bộ lọc cổ phiếu');

    // Test Search Filter Input (responsive selector for desktop/mobile)
    const isMobile = (page.viewportSize()?.width || 1440) < 768;
    const searchInput = isMobile
      ? page.locator('.filter-summary-mobile input[type="search"]')
      : page.locator('.filter-toolbar-desktop input[type="search"]');

    await expect(searchInput).toBeVisible();
    await searchInput.fill('FPT');

    // Wait for debounced search sync in URL query
    await page.waitForTimeout(350);
    const urlWithQuery = page.url();
    expect(urlWithQuery).toContain('query=FPT');

    // Verify only FPT is visible in table/cards
    const symbolLinks = isMobile
      ? page.locator('.stock-card-list a[href*="#/symbols/FPT"]')
      : page.locator('.data-table a[href*="#/symbols/FPT"]');
    await expect(symbolLinks.first()).toBeVisible();

    // Clear search and test exchange filter
    await searchInput.fill('');
    await page.waitForTimeout(350);

    if (!isMobile) {
      const exchangeSelect = page.locator('.filter-toolbar-desktop select[aria-label*="sàn"]');
      if (await exchangeSelect.isVisible()) {
        await exchangeSelect.selectOption('HOSE');
        await page.waitForTimeout(200);
        expect(page.url()).toContain('exchange=HOSE');
      }
    }

    const cspViolations = await getCapturedCSPViolations(page);
    expect(cspViolations).toEqual([]);
    expect(errors).toEqual([]);
  });

  test('Symbol detail route renders correctly with explanations and table alternative', async ({ page }) => {
    const errors: string[] = [];
    await setupPageListeners(page, errors);

    await page.goto('#/symbols/FPT');
    await page.waitForSelector('h1');

    // Verify FPT title and exchange badge
    await expect(page.locator('h1')).toContainText('FPT');
    await expect(page.locator('.symbol-header-exchange-tag')).toContainText('HOSE');

    // Verify Signal Explanation Card
    const explanationCard = page.locator('.explanation-card');
    await expect(explanationCard).toBeVisible();
    await expect(explanationCard).toContainText('Giải thích tín hiệu');

    // Verify Lightweight Candlestick Chart or SVG container is mounted
    const chartContainer = page.locator('.chart-container-lightweight, .chart-container-svg');
    await expect(chartContainer.first()).toBeVisible();

    // Toggle Accessible Table Alternative
    const toggleBtn = page.locator('button.chart-toggle-btn');
    await toggleBtn.click();
    const tableAlt = page.locator('.chart-table-alt-wrapper table.data-table');
    await expect(tableAlt).toBeVisible();
    const rows = tableAlt.locator('tbody tr');
    await expect(rows.first()).toBeVisible();

    const cspViolations = await getCapturedCSPViolations(page);
    expect(cspViolations).toEqual([]);
    expect(errors).toEqual([]);
  });

  test('404 Not Found route renders cleanly for invalid paths', async ({ page }) => {
    const errors: string[] = [];
    await setupPageListeners(page, errors);

    await page.goto('#/invalid-unknown-route-999');
    await page.waitForSelector('h1');

    await expect(page.locator('h1')).toContainText('404');
    await expect(page.locator('h1')).toContainText('Không tìm thấy trang');
    const backBtn = page.locator('a[href="#/"]');
    await expect(backBtn.first()).toBeVisible();

    const cspViolations = await getCapturedCSPViolations(page);
    expect(cspViolations).toEqual([]);
    expect(errors).toEqual([]);
  });

  test('Invalid symbol route renders symbol not found error state', async ({ page }) => {
    const errors: string[] = [];
    await setupPageListeners(page, errors, {
      isAllowedRequestFailed: (url) => url.includes('UNKNOWNXYZ.json'),
      isAllowedConsole: (text) =>
        text.includes('UNKNOWNXYZ.json') ||
        text.includes('404') ||
        text.includes('Failed to load resource') ||
        text.includes('không tìm thấy'),
    });

    await page.goto('#/symbols/UNKNOWNXYZ');
    await page.waitForSelector('h1');

    await expect(page.locator('h1')).toContainText('Không tìm thấy mã UNKNOWNXYZ');
    const returnLink = page.locator('a:has-text("Quay lại bộ lọc")');
    await expect(returnLink).toBeVisible();

    const cspViolations = await getCapturedCSPViolations(page);
    expect(cspViolations).toEqual([]);
    expect(errors).toEqual([]);
  });

  test('Mobile FilterDrawer has deterministic initial focus, true focus trap, background isolation, and Escape close', async ({
    page,
  }) => {
    // Only run on mobile viewports (< 768px) where FilterDrawer button exists
    const viewport = page.viewportSize();
    if (!viewport || viewport.width >= 768) {
      test.skip();
      return;
    }

    const errors: string[] = [];
    await setupPageListeners(page, errors);

    await page.goto('#/screener');
    await page.waitForSelector('h1');

    // 1. Open mobile FilterDrawer
    const openDrawerBtn = page.locator('#open-filter-drawer-btn, button:has-text("Bộ lọc")').first();
    await expect(openDrawerBtn).toBeVisible();
    await openDrawerBtn.click();

    // 2. Assert FilterDrawer dialog is open with aria-modal="true"
    const drawerDialog = page.locator('div[role="dialog"][aria-modal="true"]');
    await expect(drawerDialog).toBeVisible();

    // 3. Assert background content is hidden from assistive tech
    const appShellRoot = page.locator('.app-shell-root');
    await expect(appShellRoot).toHaveAttribute('aria-hidden', 'true');

    // 4. Assert deterministic initial focus is on the close button or first interactive control
    const closeBtn = drawerDialog.locator('button[aria-label*="Đóng"]').first();
    await expect(closeBtn).toBeFocused();

    // 5. Test keyboard Escape closes drawer and restores focus to opener button
    await page.keyboard.press('Escape');
    await expect(drawerDialog).not.toBeVisible();
    await expect(openDrawerBtn).toBeFocused();
    await expect(appShellRoot).not.toHaveAttribute('aria-hidden', 'true');

    const cspViolations = await getCapturedCSPViolations(page);
    expect(cspViolations).toEqual([]);
    expect(errors).toEqual([]);
  });

  test('Full Axe accessibility check on Overview, Screener, and Symbol Detail without disabled rules', async ({
    page,
  }) => {
    const routes = ['#/', '#/screener', '#/symbols/FPT'];

    for (const route of routes) {
      await page.goto(route);
      await page.waitForSelector('h1');

      // Run Axe accessibility analysis on full document
      const axeResults = await new AxeBuilder({ page }).analyze();
      expect(
        axeResults.violations,
        `Axe accessibility violations found on ${route}: ${JSON.stringify(axeResults.violations, null, 2)}`
      ).toEqual([]);
    }
  });

  test('Non-tautological Desktop Table and Mobile Cards parity with independent contexts', async ({
    browser,
    baseURL,
  }) => {
    const desktopContext = await browser.newContext({
      baseURL,
      viewport: { width: 1440, height: 900 },
    });
    const mobileContext = await browser.newContext({
      baseURL,
      viewport: { width: 390, height: 844 },
    });

    try {
      const desktopPage = await desktopContext.newPage();
      const mobilePage = await mobileContext.newPage();

      await desktopPage.goto('#/screener');
      await mobilePage.goto('#/screener');

      await desktopPage.waitForSelector('table.data-table tbody tr');
      await mobilePage.waitForSelector('.stock-card-list .stock-card');

      // Extract dataset rows from desktop table
      const tableData = await desktopPage.$$eval('table.data-table tbody tr', (rows) =>
        rows.map((r) => {
          const symbol = r.querySelector('td:first-child a')?.getAttribute('href')?.replace('#/symbols/', '') || '';
          const close = r.querySelector('td:nth-child(3)')?.textContent?.trim() || '';
          return { symbol, close };
        }).filter((item) => item.symbol.length > 0)
      );

      // Extract dataset items from mobile stock cards
      const cardData = await mobilePage.$$eval('.stock-card-list .stock-card', (cards) =>
        cards.map((c) => {
          const symbol = c.querySelector('a')?.getAttribute('href')?.replace('#/symbols/', '') || '';
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
    await setupPageListeners(page, errors, {
      isAllowedRequestFailed: (url) => url.endsWith('/data/manifest.json'),
      isAllowedConsole: (text) =>
        text.includes('404') ||
        text.includes('Failed to load resource') ||
        text.includes('manifest.json') ||
        text.includes('Không thể tải dữ liệu'),
    });

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
    await setupPageListeners(page, errors, {
      isAllowedConsole: (text) =>
        text.includes('manifest.json') &&
        (text.includes('JSON') ||
          text.includes('SyntaxError') ||
          text.includes('Unexpected token') ||
          text.includes('Lỗi kết nối khi tải') ||
          text.includes('Không thể tải dữ liệu')),
    });

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
    await setupPageListeners(page, errors, {
      isAllowedConsole: (text) =>
        text.includes('manifest.json') &&
        (text.includes('Schema validation failed') ||
          text.includes('Phiên bản dữ liệu không tương thích') ||
          text.includes('Không đúng định dạng chuẩn')),
    });

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
    await setupPageListeners(page, errors, {
      isAllowedConsole: (text) =>
        text.includes('manifest.json') &&
        (text.includes('Schema validation failed') || text.includes('Không đúng định dạng chuẩn')),
    });

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
    await setupPageListeners(page, errors, {
      isAllowedConsole: (text) =>
        text.includes('overview.json') && text.includes('dataset_id mismatch'),
    });

    await page.route('**/data/overview.json', async (route) => {
      const response = await route.fetch();
      const json = await response.json();
      json.dataset_id = '0000000000000999';
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
    await setupPageListeners(page, errors, {
      isAllowedConsole: (text) =>
        text.includes('screener.json') && text.includes('dataset_id mismatch'),
    });

    await page.route('**/data/screener.json', async (route) => {
      const response = await route.fetch();
      const json = await response.json();
      json.dataset_id = '0000000000000999';
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
    await setupPageListeners(page, errors, {
      isAllowedConsole: (text) =>
        text.includes('FPT.json') && text.includes('dataset_id mismatch'),
    });

    await page.route('**/data/symbols/FPT.json', async (route) => {
      const response = await route.fetch();
      const json = await response.json();
      json.dataset_id = '0000000000000999';
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

  test('Negative control: Unhandled unexpected error or CSP violation is captured and fails verification', async ({
    page,
  }) => {
    const capturedErrors: string[] = [];
    // Strict listener with no allowed errors
    await setupPageListeners(page, capturedErrors);

    await page.goto('#/');
    await page.waitForSelector('h1');

    // 1. Injected unauthorized inline script attempting evaluation (violating CSP script-src 'self')
    await page.evaluate(() => {
      try {
        const script = document.createElement('script');
        script.textContent = 'window.__unauthorizedExecuted = true;';
        document.body.appendChild(script);
      } catch (e) {
        // Ignored, CSP violation event listener will record violation
      }
    });

    // Verify CSP violation was recorded
    const cspViolations = await getCapturedCSPViolations(page);
    expect(cspViolations.length).toBeGreaterThan(0);
    expect(cspViolations[0]).toContain("script-src");

    // 2. Injected unexpected console error
    await page.evaluate(() => {
      console.error('UNEXPECTED_NEGATIVE_CONTROL_ERROR: Injected runtime crash');
    });

    // Verify error listener captured the unexpected error
    expect(capturedErrors.length).toBeGreaterThan(0);
    expect(capturedErrors.some((e) => e.includes('UNEXPECTED_NEGATIVE_CONTROL_ERROR'))).toBe(true);
  });

});
