import React, { useEffect, useState } from 'react';
import { ArrowUpRight, ArrowDownRight, Info } from 'lucide-react';
import { BreadthChart } from '../../components/BreadthChart';
import { MetricCard } from '../../components/MetricCard';
import { SignalBadge } from '../../components/SignalBadge';
import { Skeleton } from '../../components/Skeleton';
import { StatusBanner } from '../../components/StatusBanner';
import { getOverview, getScreener } from '../../lib/api';
import { formatDateVi } from '../../lib/formatters';
import { Manifest } from '../../schemas/manifestSchema';
import { Overview } from '../../schemas/overviewSchema';
import { ScreenerItem } from '../../schemas/screenerSchema';

interface OverviewPageProps {
  manifest: Manifest;
}

export const OverviewPage: React.FC<OverviewPageProps> = ({ manifest }) => {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [screenerItems, setScreenerItems] = useState<ScreenerItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async (signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    try {
      const [ovData, scData] = await Promise.all([
        getOverview(manifest.dataset_id, signal),
        getScreener(manifest.dataset_id, signal),
      ]);
      setOverview(ovData);
      setScreenerItems(scData.items);
    } catch (err: any) {
      if (err?.name === 'AbortError' || signal?.aborted) return;
      setError(err?.message || 'Không thể tải dữ liệu trang tổng quan.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const controller = new AbortController();
    fetchData(controller.signal);
    return () => controller.abort();
  }, [manifest.dataset_id]);

  if (loading) {
    return (
      <div>
        <div className="mb-5">
          <Skeleton className="sk-title mb-2" />
          <Skeleton className="sk-row" />
        </div>
        <div className="grid-kpi mb-6">
          {[1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} className="sk-kpi" />
          ))}
        </div>
        <Skeleton className="sk-chart mb-6" />
      </div>
    );
  }

  if (error || !overview) {
    return (
      <StatusBanner
        variant="error"
        title="Lỗi tải dữ liệu tổng quan"
        message={error || 'Không thể hiển thị dữ liệu thị trường.'}
        onRetry={() => fetchData()}
      />
    );
  }

  const { metrics, breadth_history } = overview;
  const asOfFormatted = formatDateVi(overview.as_of_date);

  // Financial safety / demo truthfulness check
  const isDemo =
    manifest.provider === 'csv' ||
    manifest.market_session_status === 'UNKNOWN' ||
    manifest.freshness.status === 'UNKNOWN' ||
    manifest.freshness.reason?.toLowerCase().includes('demo');

  const sessionStatusText =
    manifest.market_session_status === 'CLOSED_CONFIRMED'
      ? `Đã xác nhận sau đóng cửa phiên ${asOfFormatted}`
      : `Dữ liệu mẫu thử nghiệm (phiên ${asOfFormatted}) — Chưa xác nhận giao dịch thực tế`;

  // Filter latest preview lists
  const crossUpItems = screenerItems
    .filter((item) => item.signal === 'CROSS_UP_MA10')
    .slice(0, 5);

  const crossDownItems = screenerItems
    .filter((item) => item.signal === 'CROSS_DOWN_MA10')
    .slice(0, 5);

  return (
    <div>
      {/* Demo Banner */}
      {isDemo && (
        <StatusBanner
          variant="info"
          title="Chế độ dữ liệu mẫu (Demo / Test Mode)"
          message="Dashboard đang hiển thị dữ liệu mô phỏng từ fixture CSV để kiểm thử giao diện và công thức kỹ thuật. Dữ liệu không phản ánh giao dịch trực tiếp ngoài thị trường."
        />
      )}

      {/* Page Header */}
      <div className="mb-5">
        <div className="flex flex-wrap items-baseline gap-2 mb-1">
          <h1 className="text-h1">Tổng quan độ rộng thị trường</h1>
          <span className="text-small font-semibold text-muted">
            • {sessionStatusText}
          </span>
        </div>
        <p className="text-small text-muted">
          Theo dõi tỷ lệ cổ phiếu nằm trên hoặc dưới đường trung bình MA10 và các tín hiệu giao cắt mới nhất.
        </p>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid-kpi mb-6">
        <MetricCard
          label="Tổng mã hợp lệ"
          value={metrics.eligible_count}
          contextText="Đủ dữ liệu giá & MA10"
          linkHref="#/screener"
          iconType="total"
        />

        <MetricCard
          label="Trên MA10"
          value={metrics.above_count}
          percentage={metrics.above_pct}
          contextText="Duy trì xu hướng ngắn hạn"
          tone="positive"
          linkHref="#/screener?signal=ABOVE_MA10"
          iconType="above"
        />

        <MetricCard
          label="Dưới MA10"
          value={metrics.below_count}
          percentage={metrics.below_pct}
          contextText="Dưới đường trung bình ngắn hạn"
          tone="default"
          linkHref="#/screener?signal=BELOW_MA10"
          iconType="below"
        />

        <MetricCard
          label="Vừa vượt MA10"
          value={metrics.cross_up_count}
          contextText="Cross Up trong phiên"
          tone="positive"
          linkHref="#/screener?signal=CROSS_UP_MA10"
          iconType="cross_up"
        />

        <MetricCard
          label="Vừa cắt xuống MA10"
          value={metrics.cross_down_count}
          contextText="Cross Down trong phiên"
          tone="negative"
          linkHref="#/screener?signal=CROSS_DOWN_MA10"
          iconType="cross_down"
        />
      </div>

      {/* Market Breadth 60-session Chart */}
      <div className="mb-6">
        <BreadthChart history={breadth_history} />
      </div>

      {/* Cross Up / Down Preview Grid */}
      <div className="grid-previews">
        {/* Cross Up Preview */}
        <div className="card preview-card">
          <div className="preview-header">
            <div className="flex items-center gap-2">
              <ArrowUpRight size={18} className="text-positive" aria-hidden="true" />
              <h3 className="text-h3">Mã vừa vượt MA10</h3>
            </div>
            <span className="preview-badge preview-badge-positive">
              {metrics.cross_up_count} mã
            </span>
          </div>

          {crossUpItems.length > 0 ? (
            <div className="flex flex-col gap-2 mb-4">
              {crossUpItems.map((item) => (
                <div key={item.symbol} className="preview-item-row">
                  <div className="flex items-center gap-2">
                    <a href={`#/symbols/${item.symbol}`} className="preview-symbol-link">
                      {item.symbol}
                    </a>
                    <span className="text-xs text-muted">{item.exchange}</span>
                    {item.in_vn30 && <span className="badge-vn30">VN30</span>}
                  </div>
                  <SignalBadge signal={item.signal} compact />
                </div>
              ))}
            </div>
          ) : (
            <div className="text-small text-muted mb-4">
              Không có mã nào vừa vượt lên MA10 trong phiên này.
            </div>
          )}

          <a href="#/screener?signal=CROSS_UP_MA10" className="text-small font-semibold flex items-center gap-1">
            <span>Xem tất cả mã Cross Up trong bộ lọc</span>
            <ArrowUpRight size={14} aria-hidden="true" />
          </a>
        </div>

        {/* Cross Down Preview */}
        <div className="card preview-card">
          <div className="preview-header">
            <div className="flex items-center gap-2">
              <ArrowDownRight size={18} className="text-negative" aria-hidden="true" />
              <h3 className="text-h3">Mã vừa cắt xuống MA10</h3>
            </div>
            <span className="preview-badge preview-badge-negative">
              {metrics.cross_down_count} mã
            </span>
          </div>

          {crossDownItems.length > 0 ? (
            <div className="flex flex-col gap-2 mb-4">
              {crossDownItems.map((item) => (
                <div key={item.symbol} className="preview-item-row">
                  <div className="flex items-center gap-2">
                    <a href={`#/symbols/${item.symbol}`} className="preview-symbol-link">
                      {item.symbol}
                    </a>
                    <span className="text-xs text-muted">{item.exchange}</span>
                    {item.in_vn30 && <span className="badge-vn30">VN30</span>}
                  </div>
                  <SignalBadge signal={item.signal} compact />
                </div>
              ))}
            </div>
          ) : (
            <div className="text-small text-muted mb-4">
              Không có mã nào vừa cắt xuống MA10 trong phiên này.
            </div>
          )}

          <a href="#/screener?signal=CROSS_DOWN_MA10" className="text-small font-semibold flex items-center gap-1">
            <span>Xem tất cả mã Cross Down trong bộ lọc</span>
            <ArrowDownRight size={14} aria-hidden="true" />
          </a>
        </div>
      </div>

      {/* Data Quality Card */}
      <div className="card">
        <div className="flex items-center gap-2 mb-2">
          <Info size={18} className="text-muted" aria-hidden="true" />
          <h3 className="text-h3">Chất lượng dữ liệu phiên</h3>
        </div>
        <p className="text-small text-muted mb-3">
          Tất cả bản ghi dữ liệu được kiểm tra hợp lệ trước khi phân loại tín hiệu và tính toán độ rộng.
        </p>

        <div className="grid-quality">
          <div className="card bg-surface-subtle">
            <span className="text-xs text-muted block mb-1">Dòng dữ liệu nạp:</span>
            <strong className="text-body font-bold">{manifest.quality.input_rows}</strong>
          </div>
          <div className="card bg-surface-subtle">
            <span className="text-xs text-muted block mb-1">Dòng hợp lệ:</span>
            <strong className="text-body font-bold text-positive">{manifest.quality.accepted_rows}</strong>
          </div>
          <div className="card bg-surface-subtle">
            <span className="text-xs text-muted block mb-1">Dòng loại bỏ:</span>
            <strong className="text-body font-bold text-negative">{manifest.quality.rejected_rows}</strong>
          </div>
          <div className="card bg-surface-subtle">
            <span className="text-xs text-muted block mb-1">Số mã đủ điều kiện:</span>
            <strong className="text-body font-bold">{manifest.quality.eligible_symbols}</strong>
          </div>
        </div>
      </div>
    </div>
  );
};
