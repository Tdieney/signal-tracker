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
    <div className="stock-card-list" role="list" aria-label="Danh sách cổ phiếu">
      {items.map((item) => {
        const isExpanded = expandedSymbols.has(item.symbol);
        const distanceColorClass =
          item.distance_pct !== null && item.distance_pct !== undefined
            ? item.distance_pct > 0
              ? 'text-positive'
              : item.distance_pct < 0
              ? 'text-negative'
              : ''
            : '';

        return (
          <div
            key={item.symbol}
            role="listitem"
            className="card stock-card"
          >
            {/* Header row: Symbol + Exchange + Signal */}
            <div className="flex justify-between items-center mb-2">
              <div className="flex items-center gap-2">
                <a
                  href={`#/symbols/${item.symbol}`}
                  className="font-bold text-h3"
                >
                  {item.symbol}
                </a>
                <span className="text-xs text-muted">
                  {item.exchange}
                </span>
                {item.in_vn30 && (
                  <span className="badge-vn30">VN30</span>
                )}
              </div>
              <SignalBadge signal={item.signal} compact />
            </div>

            {/* Price & Metric row */}
            <div className="stock-card-grid">
              <div>
                <span className="text-xs text-muted block mb-1">Đóng cửa:</span>
                <span className="font-semibold text-body">{formatPrice(item.close)}</span>
              </div>
              <div>
                <span className="text-xs text-muted block mb-1">MA10:</span>
                <span className="font-medium text-body">{formatPrice(item.ma10)}</span>
              </div>
              <div>
                <span className="text-xs text-muted block mb-1">Khoảng cách:</span>
                <span className={`font-semibold ${distanceColorClass}`}>{formatDistance(item.distance_pct)}</span>
              </div>
            </div>

            {/* Bottom row: Avg Vol + Expand Button */}
            <div className="flex justify-between items-center mt-2 text-small">
              <span className="text-muted">
                Avg Vol 20D: <strong className="text-body">{formatVolumeCompact(item.avg_volume_20d)}</strong>
              </span>

              <button
                type="button"
                onClick={() => toggleExpand(item.symbol)}
                className="stock-card-expand-btn"
                aria-expanded={isExpanded}
                aria-label={isExpanded ? `Thu gọn thông tin mã ${item.symbol}` : `Xem thêm chi tiết mã ${item.symbol}`}
              >
                <span>{isExpanded ? 'Thu gọn' : 'Xem thêm'}</span>
                {isExpanded ? <ChevronUp size={14} aria-hidden="true" /> : <ChevronDown size={14} aria-hidden="true" />}
              </button>
            </div>

            {/* Expanded section */}
            {isExpanded && (
              <div className="stock-card-expanded-section">
                <div>
                  <span className="text-xs text-muted block">Volume phiên:</span>
                  <span>{formatVolume(item.volume)}</span>
                </div>
                <div>
                  <span className="text-xs text-muted block">Trạng thái:</span>
                  <span>{DATA_STATUS_LABELS[item.data_status] || item.data_status}</span>
                </div>
                {item.last_trading_date && (
                  <div>
                    <span className="text-xs text-muted block">Phiên gần nhất:</span>
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
