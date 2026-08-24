import React, { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { DATA_STATUS_LABELS } from '../lib/constants';
import { formatDateVi, formatDistance, formatPrice, formatVolume, formatVolumeCompact } from '../lib/formatters';
import { ScreenerItem } from '../schemas/screenerSchema';
import { SignalBadge } from './SignalBadge';

interface StockCardListProps {
  items: ScreenerItem[];
}

export const StockCardList: React.FC<StockCardListProps> = ({ items }) => {
  const [expandedSymbols, setExpandedSymbols] = useState<Set<string>>(new Set());

  const toggleExpand = (sym: string) => {
    setExpandedSymbols((prev) => {
      const next = new Set(prev);
      if (next.has(sym)) next.delete(sym);
      else next.add(sym);
      return next;
    });
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }} role="list" aria-label="Danh sách cổ phiếu">
      {items.map((item) => {
        const isExpanded = expandedSymbols.has(item.symbol);
        const distanceColor =
          item.distance_pct !== null && item.distance_pct !== undefined
            ? item.distance_pct > 0
              ? 'var(--color-positive)'
              : item.distance_pct < 0
              ? 'var(--color-negative)'
              : 'inherit'
            : 'inherit';

        return (
          <div
            key={item.symbol}
            role="listitem"
            className="card"
            style={{ padding: 'var(--space-3) var(--space-4)' }}
          >
            {/* Header row: Symbol + Exchange + Signal */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-2)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                <a
                  href={`#/symbols/${item.symbol}`}
                  style={{ fontWeight: 700, fontSize: '1.125rem', color: 'var(--color-primary)' }}
                >
                  {item.symbol}
                </a>
                <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                  {item.exchange}
                </span>
                {item.in_vn30 && (
                  <span
                    style={{
                      fontSize: '0.6875rem',
                      backgroundColor: 'var(--color-primary-light)',
                      color: 'var(--color-primary-strong)',
                      padding: '1px 4px',
                      borderRadius: 'var(--radius-sm)',
                      fontWeight: 600,
                    }}
                  >
                    VN30
                  </span>
                )}
              </div>
              <SignalBadge signal={item.signal} compact />
            </div>

            {/* Price & Metric row */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(3, 1fr)',
                gap: 'var(--space-2)',
                padding: 'var(--space-2) 0',
                borderTop: '1px solid var(--color-border-subtle)',
                borderBottom: '1px solid var(--color-border-subtle)',
                fontSize: '0.875rem',
              }}
            >
              <div>
                <span className="text-xs" style={{ color: 'var(--color-text-muted)', display: 'block' }}>Close</span>
                <span style={{ fontWeight: 600 }}>{formatPrice(item.close)}</span>
              </div>
              <div>
                <span className="text-xs" style={{ color: 'var(--color-text-muted)', display: 'block' }}>MA10</span>
                <span>{formatPrice(item.ma10)}</span>
              </div>
              <div>
                <span className="text-xs" style={{ color: 'var(--color-text-muted)', display: 'block' }}>Distance</span>
                <span style={{ fontWeight: 600, color: distanceColor }}>{formatDistance(item.distance_pct)}</span>
              </div>
            </div>

            {/* Bottom row: Avg Vol + Expand Button */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginTop: 'var(--space-2)',
                fontSize: '0.8125rem',
              }}
            >
              <span style={{ color: 'var(--color-text-muted)' }}>
                Avg Vol 20D: <strong>{formatVolumeCompact(item.avg_volume_20d)}</strong>
              </span>

              <button
                type="button"
                onClick={() => toggleExpand(item.symbol)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--color-primary)',
                  fontSize: '0.8125rem',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '2px',
                  cursor: 'pointer',
                  padding: '4px',
                }}
                aria-expanded={isExpanded}
                aria-label={isExpanded ? `Thu gọn thông tin mã ${item.symbol}` : `Xem thêm chi tiết mã ${item.symbol}`}
              >
                <span>{isExpanded ? 'Thu gọn' : 'Xem thêm'}</span>
                {isExpanded ? <ChevronUp size={14} aria-hidden="true" /> : <ChevronDown size={14} aria-hidden="true" />}
              </button>
            </div>

            {/* Expanded section */}
            {isExpanded && (
              <div
                style={{
                  marginTop: 'var(--space-2)',
                  paddingTop: 'var(--space-2)',
                  borderTop: '1px dashed var(--color-border-subtle)',
                  display: 'grid',
                  gridTemplateColumns: 'repeat(2, 1fr)',
                  gap: 'var(--space-2)',
                  fontSize: '0.8125rem',
                }}
              >
                <div>
                  <span className="text-xs" style={{ color: 'var(--color-text-muted)', display: 'block' }}>Volume phiên:</span>
                  <span>{formatVolume(item.volume)}</span>
                </div>
                <div>
                  <span className="text-xs" style={{ color: 'var(--color-text-muted)', display: 'block' }}>Trạng thái:</span>
                  <span>{DATA_STATUS_LABELS[item.data_status] || item.data_status}</span>
                </div>
                {item.last_trading_date && (
                  <div>
                    <span className="text-xs" style={{ color: 'var(--color-text-muted)', display: 'block' }}>Phiên gần nhất:</span>
                    <span>{formatDateVi(item.last_trading_date)}</span>
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};
