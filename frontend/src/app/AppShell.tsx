import React from 'react';
import { Activity, BarChart2, Filter } from 'lucide-react';
import { DISCLAIMER_FOOTER } from '../lib/constants';
import { FreshnessBadge } from '../components/FreshnessBadge';
import { SkipLink } from '../components/SkipLink';
import { Manifest } from '../schemas/manifestSchema';

interface AppShellProps {
  currentRoute: string;
  manifest: Manifest | null;
  children: React.ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({
  currentRoute,
  manifest,
  children,
}) => {
  return (
    <div className="app-shell-root">
      <SkipLink />

      {/* Header */}
      <header className="app-header">
        <div className="page-container app-header-inner">
          {/* Logo & Brand */}
          <a
            href="#/"
            className="brand-link"
            aria-label="VN Stock Signal - Về trang chủ tổng quan"
          >
            <div className="brand-logo-icon" aria-hidden="true">
              <Activity size={20} />
            </div>
            <span className="brand-title-text">VN Stock Signal</span>
          </a>

          {/* Navigation */}
          <nav aria-label="Điều hướng chính" className="nav-tabs">
            <a
              href="#/"
              className={`nav-tab ${currentRoute === 'overview' ? 'nav-tab-active' : ''}`}
              aria-current={currentRoute === 'overview' ? 'page' : undefined}
            >
              <BarChart2 size={16} aria-hidden="true" />
              <span>Tổng quan</span>
            </a>
            <a
              href="#/screener"
              className={`nav-tab ${currentRoute === 'screener' ? 'nav-tab-active' : ''}`}
              aria-current={currentRoute === 'screener' ? 'page' : undefined}
            >
              <Filter size={16} aria-hidden="true" />
              <span>Bộ lọc</span>
            </a>
          </nav>
        </div>
      </header>

      {/* Main Content Area */}
      <main id="main-content" tabIndex={-1} className="main-content-wrapper">
        <div className="page-container">
          {children}
        </div>
      </main>

      {/* Footer */}
      <footer className="app-footer">
        <div className="page-container">
          {/* Regulatory & Risk Disclaimer */}
          <div className="footer-disclaimer">
            <h3 className="text-small font-semibold mb-1">
              Tuyên bố miễn trừ trách nhiệm
            </h3>
            <p className="text-xs text-muted">
              {DISCLAIMER_FOOTER}
            </p>
          </div>

          {/* Metadata & Freshness */}
          <div className="footer-meta">
            <div className="text-xs text-subtle">
              Dữ liệu cuối ngày (EOD) • Phân tích kỹ thuật MA10 • Tự động build tĩnh
            </div>

            {manifest && (
              <FreshnessBadge
                status={manifest.freshness.status}
                asOfDate={manifest.as_of_date}
                generatedAt={manifest.generated_at}
                reason={manifest.freshness.reason}
                marketSessionStatus={manifest.market_session_status}
                provider={manifest.provider}
              />
            )}
          </div>
        </div>
      </footer>
    </div>
  );
};
