import React, { useEffect, useState } from 'react';
import { ArrowLeft } from 'lucide-react';
import { FreshnessBadge } from '../../components/FreshnessBadge';
import { LightweightChart } from '../../components/LightweightChart';
import { SignalBadge } from '../../components/SignalBadge';
import { Skeleton } from '../../components/Skeleton';
import { StatusBanner } from '../../components/StatusBanner';
import { getSymbolDetail } from '../../lib/api';
import { formatDistance, formatPrice } from '../../lib/formatters';
import { Manifest } from '../../schemas/manifestSchema';
import { SymbolDetail } from '../../schemas/symbolSchema';
import { SignalExplanationCard } from './SignalExplanationCard';

interface SymbolDetailPageProps {
  symbol: string;
  manifest: Manifest;
}

export const SymbolDetailPage: React.FC<SymbolDetailPageProps> = ({
  symbol,
  manifest,
}) => {
  const [detail, setDetail] = useState<SymbolDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSymbol = async (signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    setNotFound(false);
    try {
      const data = await getSymbolDetail(symbol, manifest.dataset_id, signal);
      setDetail(data);
    } catch (err: any) {
      if (err?.name === 'AbortError' || signal?.aborted) return;
      if (
        err?.statusCode === 404 ||
        err?.message?.includes('404') ||
        err?.message?.includes('không tồn tại') ||
        err?.message?.includes('không hợp lệ')
      ) {
        setNotFound(true);
      } else {
        setError(err?.message || 'Không thể tải chi tiết cổ phiếu.');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const controller = new AbortController();
    fetchSymbol(controller.signal);
    return () => controller.abort();
  }, [symbol, manifest.dataset_id]);

  if (loading) {
    return (
      <div>
        <Skeleton className="sk-title mb-4" />
        <Skeleton className="sk-detail-header" />
        <Skeleton className="sk-detail-chart" />
      </div>
    );
  }

  if (notFound) {
    return (
      <div className="card text-center p-6" data-testid="symbol-not-found-card">
        <h1 className="text-h1 mb-2">Không tìm thấy mã {symbol}</h1>
        <p className="text-small text-muted mb-4">
          Mã cổ phiếu này không nằm trong danh mục theo dõi hoặc chưa có dữ liệu giao dịch cho phiên hiện tại.
        </p>
        <a href="#/screener" className="btn-primary">
          <ArrowLeft size={16} aria-hidden="true" />
          <span>Quay lại bộ lọc</span>
        </a>
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div className="mb-6" data-testid="symbol-error-card">
        <StatusBanner
          variant="error"
          title="Lỗi tải dữ liệu chi tiết cổ phiếu"
          message={error || 'Không thể tải thông tin chi tiết.'}
          onRetry={() => fetchSymbol()}
        />
        <div className="mt-4">
          <a href="#/screener" className="btn-secondary">
            <ArrowLeft size={16} aria-hidden="true" />
            <span>Quay lại bộ lọc</span>
          </a>
        </div>
      </div>
    );
  }

  const { latest, series, explanation, as_of_date, exchange } = detail;
  const distanceColorClass =
    latest.distance_pct !== null && latest.distance_pct !== undefined
      ? latest.distance_pct > 0
        ? 'text-positive'
        : latest.distance_pct < 0
        ? 'text-negative'
        : ''
      : '';

  return (
    <div>
      {/* Back to Screener Link */}
      <div className="mb-4">
        <a
          href="#/screener"
          className="btn-secondary"
          aria-label="Quay lại danh sách bộ lọc cổ phiếu"
        >
          <ArrowLeft size={16} aria-hidden="true" />
          <span>Quay lại bộ lọc</span>
        </a>
      </div>

      {/* Symbol Header Card */}
      <div className="card symbol-header-card">
        <div className="flex flex-wrap justify-between items-center gap-3 mb-4">
          <div className="flex items-center gap-3">
            <h1 className="text-h1">{detail.symbol}</h1>
            <span className="symbol-header-exchange-tag">{exchange}</span>
            <SignalBadge signal={latest.signal} />
          </div>

          <FreshnessBadge
            status={manifest.freshness.status}
            asOfDate={as_of_date}
            reason={manifest.freshness.reason}
            marketSessionStatus={manifest.market_session_status}
            provider={manifest.provider}
          />
        </div>

        {/* Quick Metrics */}
        <div className="symbol-quick-metrics">
          <div>
            <span className="text-xs text-muted block mb-1">Giá đóng cửa (Close)</span>
            <strong className="text-display symbol-metric-item-value">{formatPrice(latest.close)}</strong>
          </div>
          <div>
            <span className="text-xs text-muted block mb-1">Đường trung bình MA10</span>
            <strong className="text-display symbol-metric-item-value">{formatPrice(latest.ma10)}</strong>
          </div>
          <div>
            <span className="text-xs text-muted block mb-1">Khoảng cách tới MA10</span>
            <strong className={`text-display symbol-metric-item-value ${distanceColorClass}`}>
              {formatDistance(latest.distance_pct)}
            </strong>
          </div>
        </div>
      </div>

      {/* Concrete Signal Explanation */}
      <SignalExplanationCard
        symbol={detail.symbol}
        asOfDate={as_of_date}
        explanation={explanation}
        signal={latest.signal}
      />

      {/* Lightweight Chart & Historical Table Alternative */}
      <div className="mb-6">
        <LightweightChart series={series} symbol={detail.symbol} />
      </div>
    </div>
  );
};
