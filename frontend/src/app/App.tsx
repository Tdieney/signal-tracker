import React, { useEffect, useState } from 'react';
import { OverviewPage } from '../features/overview/OverviewPage';
import { ScreenerPage } from '../features/screener/ScreenerPage';
import { SymbolDetailPage } from '../features/symbol-detail/SymbolDetailPage';
import { getManifest } from '../lib/api';
import { Manifest } from '../schemas/manifestSchema';
import { AppShell } from './AppShell';
import { parseHashRoute, RouteType } from './routes';

export const App: React.FC = () => {
  const [currentRoute, setCurrentRoute] = useState<RouteType>(() =>
    parseHashRoute(window.location.hash)
  );
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [globalError, setGlobalError] = useState<string | null>(null);

  // Load manifest at root startup
  const loadManifest = async () => {
    setGlobalError(null);
    try {
      const data = await getManifest();
      setManifest(data);
    } catch (err: unknown) {
      setGlobalError(
        err instanceof Error
          ? err.message
          : 'Không thể kết nối đến nguồn dữ liệu Manifest. Vui lòng thử lại.'
      );
    }
  };

  useEffect(() => {
    loadManifest();
  }, []);

  // Listen to hash route changes
  useEffect(() => {
    const handleHashChange = () => {
      const route = parseHashRoute(window.location.hash);
      setCurrentRoute(route);

      // Manage document title
      if (route.name === 'overview') {
        document.title = 'VN Stock Signal — Tổng quan thị trường';
      } else if (route.name === 'screener') {
        document.title = 'VN Stock Signal — Bộ lọc cổ phiếu MA10';
      } else if (route.name === 'symbol') {
        document.title = `VN Stock Signal — Chi tiết ${route.symbol}`;
      } else {
        document.title = 'VN Stock Signal — Không tìm thấy trang';
      }

      // Accessible focus management: focus main content on route navigation without layout jump
      const mainContent = document.getElementById('main-content');
      if (mainContent) {
        mainContent.focus({ preventScroll: true });
      }
    };

    window.addEventListener('hashchange', handleHashChange);
    handleHashChange(); // Run once for initial title

    return () => {
      window.removeEventListener('hashchange', handleHashChange);
    };
  }, []);

  // Get current active route path string for navigation tab highlight
  const currentPath =
    currentRoute.name === 'overview'
      ? '/'
      : currentRoute.name === 'screener'
      ? '/screener'
      : currentRoute.name === 'symbol'
      ? `/symbols/${currentRoute.symbol}`
      : '/404';

  return (
    <AppShell
      currentRoute={currentPath}
      manifest={manifest}
      globalError={globalError}
      onRetry={loadManifest}
    >
      {currentRoute.name === 'overview' && <OverviewPage manifest={manifest} />}
      {currentRoute.name === 'screener' && (
        <ScreenerPage manifest={manifest} searchQueryString={currentRoute.search} />
      )}
      {currentRoute.name === 'symbol' && (
        <SymbolDetailPage symbol={currentRoute.symbol} manifest={manifest} />
      )}
      {currentRoute.name === 'not_found' && (
        <div className="card" style={{ padding: 'var(--space-7)', textAlign: 'center' }}>
          <h1 className="text-h1" style={{ marginBottom: 'var(--space-2)' }}>
            404 — Không tìm thấy trang
          </h1>
          <p className="text-body" style={{ color: 'var(--color-text-muted)', marginBottom: 'var(--space-5)' }}>
            Đường dẫn <code>{currentRoute.path}</code> không tồn tại.
          </p>
          <div style={{ display: 'flex', justifyContent: 'center', gap: 'var(--space-3)' }}>
            <a
              href="#/"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                padding: 'var(--space-2) var(--space-4)',
                borderRadius: 'var(--radius-md)',
                backgroundColor: 'var(--color-primary)',
                color: '#ffffff',
                fontWeight: 600,
                textDecoration: 'none',
              }}
            >
              Về Trang chủ Tổng quan
            </a>
            <a
              href="#/screener"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                padding: 'var(--space-2) var(--space-4)',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--color-border)',
                backgroundColor: 'var(--color-surface)',
                color: 'var(--color-text)',
                fontWeight: 600,
                textDecoration: 'none',
              }}
            >
              Xem Bộ lọc cổ phiếu
            </a>
          </div>
        </div>
      )}
    </AppShell>
  );
};
