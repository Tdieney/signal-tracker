import React, { useEffect, useState, useCallback } from 'react';
import { OverviewPage } from '../features/overview/OverviewPage';
import { ScreenerPage } from '../features/screener/ScreenerPage';
import { SymbolDetailPage } from '../features/symbol-detail/SymbolDetailPage';
import { Skeleton } from '../components/Skeleton';
import { StatusBanner } from '../components/StatusBanner';
import { getManifest, clearApiCache } from '../lib/api';
import { Manifest } from '../schemas/manifestSchema';
import { AppShell } from './AppShell';
import { parseHashRoute, RouteType } from './routes';

export const App: React.FC = () => {
  const [currentRoute, setCurrentRoute] = useState<RouteType>(() =>
    parseHashRoute(window.location.hash)
  );
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [manifestLoading, setManifestLoading] = useState(true);
  const [manifestError, setManifestError] = useState<string | null>(null);

  // Load manifest at root startup with fail-closed guarantee
  const loadManifest = useCallback(async () => {
    setManifestLoading(true);
    setManifestError(null);
    clearApiCache();
    try {
      const data = await getManifest();
      setManifest(data);
    } catch (err: any) {
      setManifest(null);
      setManifestError(
        err?.message || 'Không thể tải tệp thông tin Manifest của thị trường. Không thể hiển thị tín hiệu.'
      );
    } finally {
      setManifestLoading(false);
    }
  }, []);

  useEffect(() => {
    loadManifest();
  }, [loadManifest]);

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

  // Get current active route name for navigation tab highlight
  const currentTab = currentRoute.name === 'screener' ? 'screener' : 'overview';

  return (
    <AppShell
      currentRoute={currentTab}
      manifest={manifest}
    >
      {/* 1. Manifest Loading State */}
      {manifestLoading && (
        <div data-testid="manifest-loading">
          <Skeleton className="sk-title mb-3" />
          <Skeleton className="sk-row mb-4" />
          <div className="grid-kpi mb-6">
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="sk-kpi" />
            ))}
          </div>
        </div>
      )}

      {/* 2. Manifest Fail-Closed Error State */}
      {!manifestLoading && manifestError && (
        <div data-testid="manifest-error" className="card p-6">
          <StatusBanner
            variant="error"
            title="Lỗi xác thực dữ liệu Manifest (Fail-Closed Mode)"
            message={`${manifestError} Vì lý do an toàn tài chính, toàn bộ bảng tín hiệu và bộ lọc bị tạm khóa cho đến khi dữ liệu được xác thực.`}
            onRetry={loadManifest}
          />
        </div>
      )}

      {/* 3. Valid Manifest Loaded: Render Safe Child Views */}
      {!manifestLoading && !manifestError && manifest && (
        <>
          {currentRoute.name === 'overview' && <OverviewPage manifest={manifest} />}
          {currentRoute.name === 'screener' && (
            <ScreenerPage initialSearch={currentRoute.search} manifest={manifest} />
          )}
          {currentRoute.name === 'symbol' && (
            <SymbolDetailPage symbol={currentRoute.symbol} manifest={manifest} />
          )}
          {currentRoute.name === 'not_found' && (
            <div className="card text-center p-6" data-testid="not-found-card">
              <h1 className="text-h1 mb-2">
                404 — Không tìm thấy trang
              </h1>
              <p className="text-body text-muted mb-4">
                Đường dẫn <code>{currentRoute.path}</code> không tồn tại hoặc đã được di chuyển.
              </p>
              <div className="flex justify-center gap-3">
                <a
                  href="#/"
                  className="btn-primary"
                >
                  Về Trang chủ Tổng quan
                </a>
                <a
                  href="#/screener"
                  className="btn-secondary"
                >
                  Xem Bộ lọc cổ phiếu
                </a>
              </div>
            </div>
          )}
        </>
      )}
    </AppShell>
  );
};
