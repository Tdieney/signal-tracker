import React from 'react';
import { Activity, Filter, Home } from 'lucide-react';
import { FreshnessBadge } from '../components/FreshnessBadge';
import { SkipLink } from '../components/SkipLink';
import { StatusBanner } from '../components/StatusBanner';
import { FINANCIAL_DISCLAIMER, APP_VERSION } from '../lib/constants';
import { Manifest } from '../schemas/manifestSchema';

interface AppShellProps {
  children: React.ReactNode;
  currentRoute: string;
  manifest: Manifest | null;
  globalError: string | null;
  onRetry?: () => void;
}

export const AppShell: React.FC<AppShellProps> = ({
  children,
  currentRoute,
  manifest,
  globalError,
  onRetry,
}) => {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <SkipLink />

      {/* Header */}
      <header
        style={{
          backgroundColor: 'var(--color-surface)',
          borderBottom: '1px solid var(--color-border)',
          position: 'sticky',
          top: 0,
          zIndex: 100,
        }}
      >
        <div
          className="page-container"
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            height: 'var(--header-height)',
            gap: 'var(--space-4)',
          }}
        >
          {/* Brand */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)' }}>
            <a
              href="#/"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--space-2)',
                color: 'var(--color-text)',
                textDecoration: 'none',
                fontWeight: 700,
                fontSize: '1.125rem',
              }}
              aria-label="VN Stock Signal - Trang chủ Tổng quan"
            >
              <div
                style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: 'var(--radius-md)',
                  backgroundColor: 'var(--color-primary)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#ffffff',
                }}
              >
                <Activity size={20} aria-hidden="true" />
              </div>
              <span>VN Stock Signal</span>
            </a>

            {/* Navigation tabs */}
            <nav aria-label="Điều hướng chính" style={{ display: 'flex', gap: 'var(--space-1)' }}>
              <a
                href="#/"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 'var(--space-1)',
                  padding: 'var(--space-2) var(--space-3)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.9375rem',
                  fontWeight: currentRoute === '/' ? 600 : 500,
                  color: currentRoute === '/' ? 'var(--color-primary-strong)' : 'var(--color-text-muted)',
                  backgroundColor: currentRoute === '/' ? 'var(--color-primary-light)' : 'transparent',
                  textDecoration: 'none',
                }}
                aria-current={currentRoute === '/' ? 'page' : undefined}
              >
                <Home size={16} aria-hidden="true" />
                <span>Tổng quan</span>
              </a>

              <a
                href="#/screener"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 'var(--space-1)',
                  padding: 'var(--space-2) var(--space-3)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.9375rem',
                  fontWeight: currentRoute.startsWith('/screener') ? 600 : 500,
                  color: currentRoute.startsWith('/screener') ? 'var(--color-primary-strong)' : 'var(--color-text-muted)',
                  backgroundColor: currentRoute.startsWith('/screener') ? 'var(--color-primary-light)' : 'transparent',
                  textDecoration: 'none',
                }}
                aria-current={currentRoute.startsWith('/screener') ? 'page' : undefined}
              >
                <Filter size={16} aria-hidden="true" />
                <span>Bộ lọc</span>
              </a>
            </nav>
          </div>

          {/* Freshness indicator in header */}
          {manifest && (
            <div className="header-freshness" style={{ display: 'flex', alignItems: 'center' }}>
              <FreshnessBadge
                status={manifest.freshness.status}
                asOfDate={manifest.as_of_date}
                reason={manifest.freshness.reason}
              />
            </div>
          )}
        </div>
      </header>

      {/* Main Content Area */}
      <main id="main-content" tabIndex={-1} style={{ flex: 1, padding: 'var(--space-5) 0', outline: 'none' }}>
        <div className="page-container">
          {/* Global error banner */}
          {globalError && (
            <StatusBanner
              variant="error"
              title="Lỗi tải dữ liệu"
              message={globalError}
              onRetry={onRetry}
            />
          )}

          {/* Stale data warning banner */}
          {manifest && manifest.freshness.status === 'STALE' && (
            <StatusBanner
              variant="warning"
              title="Dữ liệu có thể đã cũ"
              message={`Dataset hiện tại là phiên ${manifest.as_of_date}, chưa có dữ liệu của phiên mới nhất. Các tín hiệu kỹ thuật vẫn có thể quan sát nhưng không phản ánh phiên hiện tại.`}
            />
          )}

          {/* Partial quality warning banner */}
          {manifest && manifest.quality.status === 'PARTIAL' && (
            <StatusBanner
              variant="warning"
              title="Dữ liệu không đầy đủ"
              message={`Có ${manifest.quality.rejected_rows} dòng dữ liệu bị loại do không hợp lệ. Đã xử lý ${manifest.quality.accepted_rows} dòng hợp lệ.`}
            />
          )}

          {children}
        </div>
      </main>

      {/* Footer */}
      <footer
        style={{
          backgroundColor: 'var(--color-surface)',
          borderTop: '1px solid var(--color-border)',
          padding: 'var(--space-6) 0',
          marginTop: 'auto',
        }}
      >
        <div className="page-container">
          <div style={{ maxWidth: '800px', marginBottom: 'var(--space-4)' }}>
            <p className="text-small" style={{ color: 'var(--color-text-muted)', lineHeight: 1.6 }}>
              <strong>Tuyên bố miễn trừ trách nhiệm:</strong> {FINANCIAL_DISCLAIMER}
            </p>
          </div>

          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              justifyContent: 'space-between',
              alignItems: 'center',
              gap: 'var(--space-2)',
              paddingTop: 'var(--space-4)',
              borderTop: '1px solid var(--color-border-subtle)',
            }}
          >
            <div className="text-xs" style={{ color: 'var(--color-text-subtle)' }}>
              VN Stock Signal v{APP_VERSION} {manifest ? `• Schema ${manifest.schema_version} • Nguồn: ${manifest.provider}` : ''}
            </div>
            <div className="text-xs" style={{ color: 'var(--color-text-subtle)' }}>
              Múi giờ: Asia/Ho_Chi_Minh • Cập nhật cuối ngày
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};
