import React, { useEffect, useState } from 'react';
import { BreadthChart } from '../../components/BreadthChart';
import { MetricCard } from '../../components/MetricCard';
import { SignalBadge } from '../../components/SignalBadge';
import { Skeleton } from '../../components/Skeleton';
import { StatusBanner } from '../../components/StatusBanner';
import { getOverview, getScreener } from '../../lib/api';
import { formatDateVi, formatPrice, formatDistance } from '../../lib/formatters';
import { Manifest } from '../../schemas/manifestSchema';
import { Overview } from '../../schemas/overviewSchema';
import { ScreenerItem } from '../../schemas/screenerSchema';

interface OverviewPageProps {
  manifest: Manifest | null;
}

export const OverviewPage: React.FC<OverviewPageProps> = ({ manifest }) => {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [screenerItems, setScreenerItems] = useState<ScreenerItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const datasetId = manifest?.dataset_id;
      const [ovData, scData] = await Promise.all([
        getOverview(datasetId),
        getScreener(datasetId),
      ]);
      setOverview(ovData);
      setScreenerItems(scData.items);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Không thể tải dữ liệu trang Tổng quan.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [manifest?.dataset_id]);

  const crossUpItems = screenerItems.filter((it) => it.signal === 'CROSS_UP_MA10');
  const crossDownItems = screenerItems.filter((it) => it.signal === 'CROSS_DOWN_MA10');

  return (
    <div>
      {/* Title & Market Session Status */}
      <div style={{ marginBottom: 'var(--space-5)' }}>
        <div style={{ display: 'flex', alignItems: 'baseline', flexWrap: 'wrap', gap: 'var(--space-3)' }}>
          <h1>Tổng quan thị trường</h1>
          {manifest && (
            <span className="text-small" style={{ color: 'var(--color-positive)', fontWeight: 600 }}>
              • Đã xác nhận sau đóng cửa phiên {formatDateVi(manifest.as_of_date)}
            </span>
          )}
        </div>
        <p className="text-body" style={{ color: 'var(--color-text-muted)', marginTop: 'var(--space-1)' }}>
          Đo lường độ rộng thị trường và thống kê vị thế giá đóng cửa so với đường trung bình 10 phiên (MA10).
        </p>
      </div>

      {error && (
        <StatusBanner
          variant="error"
          title="Lỗi tải dữ liệu Tổng quan"
          message={error}
          onRetry={fetchData}
        />
      )}

      {/* KPI Cards Grid */}
      <section aria-labelledby="kpi-heading" style={{ marginBottom: 'var(--space-6)' }}>
        <h2 id="kpi-heading" className="sr-only" style={{ display: 'none' }}>
          Chỉ số thị trường chính
        </h2>

        {loading ? (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
              gap: 'var(--space-4)',
            }}
          >
            {[...Array(5)].map((_, i) => (
              <div key={i} className="card" style={{ height: '110px' }}>
                <Skeleton width="60%" height="1rem" style={{ marginBottom: 'var(--space-3)' }} />
                <Skeleton width="40%" height="2rem" />
              </div>
            ))}
          </div>
        ) : overview ? (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
              gap: 'var(--space-4)',
            }}
          >
            <MetricCard
              label="Mã đủ dữ liệu MA10"
              value={overview.metrics.eligible_count}
              iconType="total"
              contextText="Cổ phiếu có tối thiểu 10 phiên giao dịch hợp lệ"
              linkHref="#/screener?universe=ALL"
            />
            <MetricCard
              label="Trên MA10"
              value={overview.metrics.above_count}
              percentage={overview.metrics.above_pct}
              tone="positive"
              iconType="above"
              contextText="Giá đóng cửa lớn hơn MA10"
              linkHref="#/screener?signal=ABOVE_MA10"
            />
            <MetricCard
              label="Dưới MA10"
              value={overview.metrics.below_count}
              percentage={overview.metrics.below_pct}
              tone="negative"
              iconType="below"
              contextText="Giá đóng cửa nhỏ hơn MA10"
              linkHref="#/screener?signal=BELOW_MA10"
            />
            <MetricCard
              label="Vừa cắt lên MA10"
              value={overview.metrics.cross_up_count}
              tone="positive"
              iconType="cross_up"
              contextText="Hôm nay trên MA10, phiên trước không ở trên"
              linkHref="#/screener?signal=CROSS_UP_MA10"
            />
            <MetricCard
              label="Vừa cắt xuống MA10"
              value={overview.metrics.cross_down_count}
              tone="negative"
              iconType="cross_down"
              contextText="Hôm nay dưới MA10, phiên trước không ở dưới"
              linkHref="#/screener?signal=CROSS_DOWN_MA10"
            />
          </div>
        ) : null}
      </section>

      {/* Breadth Chart */}
      <section style={{ marginBottom: 'var(--space-6)' }}>
        {loading ? (
          <div className="card" style={{ height: '300px' }}>
            <Skeleton width="40%" height="1.5rem" style={{ marginBottom: 'var(--space-4)' }} />
            <Skeleton width="100%" height="200px" />
          </div>
        ) : overview ? (
          <BreadthChart history={overview.breadth_history} />
        ) : null}
      </section>

      {/* Cross Up / Cross Down Previews */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 340px), 1fr))',
          gap: 'var(--space-5)',
          marginBottom: 'var(--space-6)',
        }}
      >
        {/* Cross Up Preview */}
        <div className="card" style={{ padding: 'var(--space-4)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-3)' }}>
            <h3 className="text-h3" style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              <span>Vừa cắt lên MA10</span>
              <span
                style={{
                  backgroundColor: 'var(--color-positive-bg)',
                  color: 'var(--color-positive)',
                  fontSize: '0.75rem',
                  padding: '2px 8px',
                  borderRadius: 'var(--radius-full)',
                  fontWeight: 600,
                }}
              >
                {crossUpItems.length}
              </span>
            </h3>
            <a href="#/screener?signal=CROSS_UP_MA10" className="text-small" style={{ fontWeight: 600 }}>
              Xem tất cả →
            </a>
          </div>

          {crossUpItems.length === 0 ? (
            <p className="text-small" style={{ color: 'var(--color-text-muted)', padding: 'var(--space-3) 0' }}>
              Không có mã nào vừa cắt lên MA10 trong phiên này.
            </p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
              {crossUpItems.slice(0, 5).map((item) => (
                <div
                  key={item.symbol}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: 'var(--space-2) var(--space-3)',
                    backgroundColor: 'var(--color-surface-subtle)',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--color-border-subtle)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                    <a
                      href={`#/symbols/${item.symbol}`}
                      style={{ fontWeight: 700, fontSize: '1rem', color: 'var(--color-primary)' }}
                    >
                      {item.symbol}
                    </a>
                    <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                      {item.exchange}
                    </span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
                    <span style={{ fontWeight: 600, fontSize: '0.9375rem' }}>{formatPrice(item.close)}</span>
                    <span style={{ color: 'var(--color-positive)', fontSize: '0.875rem', fontWeight: 600 }}>
                      {formatDistance(item.distance_pct)}
                    </span>
                    <SignalBadge signal={item.signal} compact />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Cross Down Preview */}
        <div className="card" style={{ padding: 'var(--space-4)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-3)' }}>
            <h3 className="text-h3" style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              <span>Vừa cắt xuống MA10</span>
              <span
                style={{
                  backgroundColor: 'var(--color-negative-bg)',
                  color: 'var(--color-negative)',
                  fontSize: '0.75rem',
                  padding: '2px 8px',
                  borderRadius: 'var(--radius-full)',
                  fontWeight: 600,
                }}
              >
                {crossDownItems.length}
              </span>
            </h3>
            <a href="#/screener?signal=CROSS_DOWN_MA10" className="text-small" style={{ fontWeight: 600 }}>
              Xem tất cả →
            </a>
          </div>

          {crossDownItems.length === 0 ? (
            <p className="text-small" style={{ color: 'var(--color-text-muted)', padding: 'var(--space-3) 0' }}>
              Không có mã nào vừa cắt xuống MA10 trong phiên này.
            </p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
              {crossDownItems.slice(0, 5).map((item) => (
                <div
                  key={item.symbol}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: 'var(--space-2) var(--space-3)',
                    backgroundColor: 'var(--color-surface-subtle)',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--color-border-subtle)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                    <a
                      href={`#/symbols/${item.symbol}`}
                      style={{ fontWeight: 700, fontSize: '1rem', color: 'var(--color-primary)' }}
                    >
                      {item.symbol}
                    </a>
                    <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                      {item.exchange}
                    </span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
                    <span style={{ fontWeight: 600, fontSize: '0.9375rem' }}>{formatPrice(item.close)}</span>
                    <span style={{ color: 'var(--color-negative)', fontSize: '0.875rem', fontWeight: 600 }}>
                      {formatDistance(item.distance_pct)}
                    </span>
                    <SignalBadge signal={item.signal} compact />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Data Quality Summary */}
      {manifest && (
        <section className="card" style={{ padding: 'var(--space-4)' }}>
          <h3 className="text-h3" style={{ marginBottom: 'var(--space-2)' }}>
            Chất lượng dữ liệu dataset
          </h3>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
              gap: 'var(--space-3)',
              marginTop: 'var(--space-3)',
            }}
          >
            <div>
              <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Trạng thái kiểm tra</span>
              <div style={{ fontWeight: 600, color: manifest.quality.status === 'PASS' ? 'var(--color-positive)' : 'var(--color-warning)' }}>
                {manifest.quality.status === 'PASS' ? 'Đạt chuẩn (PASS)' : 'Cảnh báo (PARTIAL)'}
              </div>
            </div>
            <div>
              <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Số dòng dữ liệu nạp</span>
              <div style={{ fontWeight: 600 }}>{manifest.quality.input_rows.toLocaleString('vi-VN')} dòng</div>
            </div>
            <div>
              <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Số dòng hợp lệ</span>
              <div style={{ fontWeight: 600 }}>{manifest.quality.accepted_rows.toLocaleString('vi-VN')} dòng</div>
            </div>
            <div>
              <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Số mã theo dõi</span>
              <div style={{ fontWeight: 600 }}>{manifest.quality.eligible_symbols} mã</div>
            </div>
          </div>
        </section>
      )}
    </div>
  );
};
