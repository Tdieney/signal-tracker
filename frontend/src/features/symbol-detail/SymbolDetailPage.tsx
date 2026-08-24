import React, { useEffect, useState } from 'react';
import { ArrowLeft } from 'lucide-react';
import { FreshnessBadge } from '../../components/FreshnessBadge';
import { LightweightChart } from '../../components/LightweightChart';
import { SignalBadge } from '../../components/SignalBadge';
import { Skeleton } from '../../components/Skeleton';
import { getSymbolDetail } from '../../lib/api';
import { formatDateVi, formatDistance, formatPrice } from '../../lib/formatters';
import { Manifest } from '../../schemas/manifestSchema';
import { SymbolDetail } from '../../schemas/symbolSchema';
import { SignalExplanationCard } from './SignalExplanationCard';

interface SymbolDetailPageProps {
  symbol: string;
  manifest: Manifest | null;
}

export const SymbolDetailPage: React.FC<SymbolDetailPageProps> = ({
  symbol,
  manifest,
}) => {
  const [detail, setDetail] = useState<SymbolDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const cleanSymbol = symbol.trim().toUpperCase();

  const fetchDetail = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getSymbolDetail(cleanSymbol, manifest?.dataset_id);
      setDetail(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : `Không thể tải dữ liệu chi tiết mã ${cleanSymbol}.`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetail();
  }, [cleanSymbol, manifest?.dataset_id]);

  if (loading) {
    return (
      <div>
        <div style={{ marginBottom: 'var(--space-4)' }}>
          <Skeleton width="120px" height="1.5rem" />
        </div>
        <div className="card" style={{ height: '140px', marginBottom: 'var(--space-5)' }}>
          <Skeleton width="40%" height="2rem" style={{ marginBottom: 'var(--space-3)' }} />
          <Skeleton width="60%" height="1.5rem" />
        </div>
        <div className="card" style={{ height: '380px' }}>
          <Skeleton width="100%" height="100%" />
        </div>
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div>
        <div style={{ marginBottom: 'var(--space-4)' }}>
          <a
            href="#/screener"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 'var(--space-1)',
              fontWeight: 600,
              fontSize: '0.9375rem',
            }}
          >
            <ArrowLeft size={16} aria-hidden="true" />
            <span>Quay lại bộ lọc</span>
          </a>
        </div>

        <div className="card" style={{ padding: 'var(--space-6)', textAlign: 'center' }}>
          <h2 className="text-h2" style={{ marginBottom: 'var(--space-2)' }}>
            Không tìm thấy thông tin mã {cleanSymbol}
          </h2>
          <p className="text-body" style={{ color: 'var(--color-text-muted)', marginBottom: 'var(--space-4)' }}>
            Mã cổ phiếu không tồn tại trong dataset hiện tại hoặc dữ liệu chưa được cập nhật.
          </p>
          <a
            href="#/screener"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 'var(--space-2)',
              padding: 'var(--space-2) var(--space-4)',
              borderRadius: 'var(--radius-md)',
              backgroundColor: 'var(--color-primary)',
              color: '#ffffff',
              fontWeight: 600,
              textDecoration: 'none',
            }}
          >
            Quay về danh sách bộ lọc
          </a>
        </div>
      </div>
    );
  }

  const { latest, explanation, series } = detail;
  const distanceColor =
    latest.distance_pct !== null && latest.distance_pct !== undefined
      ? latest.distance_pct > 0
        ? 'var(--color-positive)'
        : latest.distance_pct < 0
        ? 'var(--color-negative)'
        : 'inherit'
      : 'inherit';

  return (
    <div>
      {/* Breadcrumb Back Link */}
      <div style={{ marginBottom: 'var(--space-4)' }}>
        <a
          href="#/screener"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 'var(--space-1)',
            fontWeight: 600,
            fontSize: '0.9375rem',
            color: 'var(--color-primary)',
          }}
        >
          <ArrowLeft size={16} aria-hidden="true" />
          <span>Quay lại bộ lọc</span>
        </a>
      </div>

      {/* Symbol Detail Header Card */}
      <section
        className="card"
        style={{
          padding: 'var(--space-5)',
          marginBottom: 'var(--space-5)',
          backgroundColor: 'var(--color-surface)',
        }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
            flexWrap: 'wrap',
            gap: 'var(--space-4)',
          }}
        >
          {/* Symbol Title & Exchange */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              <h1>{detail.symbol}</h1>
              <span
                style={{
                  fontSize: '0.875rem',
                  backgroundColor: 'var(--color-surface-muted)',
                  color: 'var(--color-text-muted)',
                  padding: '2px 8px',
                  borderRadius: 'var(--radius-sm)',
                  fontWeight: 600,
                }}
              >
                {detail.exchange}
              </span>
              <SignalBadge signal={latest.signal} />
            </div>

            <div style={{ marginTop: 'var(--space-2)' }}>
              {manifest && (
                <FreshnessBadge
                  status={manifest.freshness.status}
                  asOfDate={detail.as_of_date}
                  reason={manifest.freshness.reason}
                />
              )}
            </div>
          </div>

          {/* Quick Metrics Grid */}
          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: 'var(--space-5)',
              alignItems: 'baseline',
            }}
          >
            <div>
              <span className="text-xs" style={{ color: 'var(--color-text-muted)', display: 'block' }}>Close</span>
              <span className="text-display" style={{ fontSize: '1.75rem' }}>{formatPrice(latest.close)}</span>
            </div>
            <div>
              <span className="text-xs" style={{ color: 'var(--color-text-muted)', display: 'block' }}>MA10</span>
              <span className="text-display" style={{ fontSize: '1.75rem' }}>{formatPrice(latest.ma10)}</span>
            </div>
            <div>
              <span className="text-xs" style={{ color: 'var(--color-text-muted)', display: 'block' }}>Distance %</span>
              <span className="text-display" style={{ fontSize: '1.75rem', color: distanceColor }}>
                {formatDistance(latest.distance_pct)}
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* Structured Explanation Card */}
      <SignalExplanationCard
        symbol={detail.symbol}
        asOfDate={detail.as_of_date}
        explanation={explanation}
        signal={latest.signal}
      />

      {/* Candlestick + MA10 + Volume Chart */}
      <LightweightChart series={series} symbol={detail.symbol} />

      {/* Signal History Table */}
      <section className="card" style={{ padding: 'var(--space-4)', marginBottom: 'var(--space-5)' }}>
        <h3 className="text-h3" style={{ marginBottom: 'var(--space-3)' }}>
          Lịch sử tín hiệu {detail.symbol} các phiên gần nhất
        </h3>
        <div className="scrollable-region" style={{ maxHeight: '280px' }} tabIndex={0}>
          <table
            style={{
              width: '100%',
              borderCollapse: 'collapse',
              fontSize: '0.875rem',
              textAlign: 'left',
            }}
          >
            <thead>
              <tr style={{ backgroundColor: 'var(--color-surface-muted)', borderBottom: '1px solid var(--color-border)' }}>
                <th style={{ padding: 'var(--space-2) var(--space-3)' }}>Phiên</th>
                <th style={{ padding: 'var(--space-2) var(--space-3)', textAlign: 'right' }}>Close</th>
                <th style={{ padding: 'var(--space-2) var(--space-3)', textAlign: 'right' }}>MA10</th>
                <th style={{ padding: 'var(--space-2) var(--space-3)', textAlign: 'right' }}>Distance %</th>
                <th style={{ padding: 'var(--space-2) var(--space-3)' }}>Tín hiệu</th>
              </tr>
            </thead>
            <tbody>
              {[...series].reverse().map((pt) => {
                const dist =
                  pt.ma10 !== null && pt.ma10 !== undefined
                    ? ((pt.close - pt.ma10) / pt.ma10) * 100
                    : null;
                const dColor = dist !== null ? (dist > 0 ? 'var(--color-positive)' : dist < 0 ? 'var(--color-negative)' : 'inherit') : 'inherit';

                return (
                  <tr key={pt.trading_date} style={{ borderBottom: '1px solid var(--color-border-subtle)' }}>
                    <td style={{ padding: 'var(--space-2) var(--space-3)' }}>{formatDateVi(pt.trading_date)}</td>
                    <td style={{ padding: 'var(--space-2) var(--space-3)', textAlign: 'right', fontWeight: 600 }}>{formatPrice(pt.close)}</td>
                    <td style={{ padding: 'var(--space-2) var(--space-3)', textAlign: 'right' }}>{formatPrice(pt.ma10)}</td>
                    <td style={{ padding: 'var(--space-2) var(--space-3)', textAlign: 'right', fontWeight: 600, color: dColor }}>{formatDistance(dist)}</td>
                    <td style={{ padding: 'var(--space-2) var(--space-3)' }}>
                      <SignalBadge signal={pt.signal} compact />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
};
