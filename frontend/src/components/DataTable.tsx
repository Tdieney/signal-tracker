import React from 'react';
import { ArrowDown, ArrowUp, ArrowUpDown } from 'lucide-react';
import { DATA_STATUS_LABELS } from '../lib/constants';
import { formatDistance, formatPrice, formatVolume, formatVolumeCompact } from '../lib/formatters';
import { ScreenerItem } from '../schemas/screenerSchema';
import { SignalBadge } from './SignalBadge';

interface DataTableProps {
  items: ScreenerItem[];
  sortField: string;
  sortDirection: 'asc' | 'desc';
  onSortChange: (field: string) => void;
}

export const DataTable: React.FC<DataTableProps> = ({
  items,
  sortField,
  sortDirection,
  onSortChange,
}) => {
  const columns = [
    { key: 'symbol', label: 'Mã' },
    { key: 'exchange', label: 'Sàn' },
    { key: 'close', label: 'Close', align: 'right' as const },
    { key: 'ma10', label: 'MA10', align: 'right' as const },
    { key: 'distance_pct', label: 'Distance %', align: 'right' as const },
    { key: 'volume', label: 'Volume', align: 'right' as const },
    { key: 'avg_volume_20d', label: 'Avg Vol 20D', align: 'right' as const },
    { key: 'signal', label: 'Tín hiệu' },
    { key: 'data_status', label: 'Trạng thái' },
  ];

  return (
    <div
      className="scrollable-region card data-table-wrapper"
      tabIndex={0}
      role="region"
      aria-label="Bảng kết quả lọc cổ phiếu"
    >
      <table className="data-table">
        <thead>
          <tr className="data-table-header-row">
            {columns.map((col) => {
              const isCurrentSort = sortField === col.key;
              const ariaSort = isCurrentSort
                ? sortDirection === 'asc'
                  ? 'ascending'
                  : 'descending'
                : 'none';

              return (
                <th
                  key={col.key}
                  aria-sort={ariaSort}
                  className={`data-table-th ${col.align === 'right' ? 'data-table-th-right' : ''}`}
                >
                  <button
                    type="button"
                    onClick={() => onSortChange(col.key)}
                    className={`data-table-sort-btn ${isCurrentSort ? 'data-table-sort-btn-active' : ''}`}
                    aria-label={`Sắp xếp theo ${col.label}, hiện tại ${
                      isCurrentSort ? (sortDirection === 'asc' ? 'tăng dần' : 'giảm dần') : 'không sắp xếp'
                    }`}
                  >
                    <span>{col.label}</span>
                    {isCurrentSort ? (
                      sortDirection === 'asc' ? (
                        <ArrowUp size={14} aria-hidden="true" />
                      ) : (
                        <ArrowDown size={14} aria-hidden="true" />
                      )
                    ) : (
                      <ArrowUpDown size={14} aria-hidden="true" className="opacity-40" />
                    )}
                  </button>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {items.map((item, idx) => {
            const isAlt = idx % 2 !== 0;
            const distanceColorClass =
              item.distance_pct !== null && item.distance_pct !== undefined
                ? item.distance_pct > 0
                  ? 'text-positive'
                  : item.distance_pct < 0
                  ? 'text-negative'
                  : ''
                : '';

            return (
              <tr
                key={item.symbol}
                className={`data-table-row ${isAlt ? 'data-table-row-alt' : ''}`}
              >
                {/* Symbol Link */}
                <td className="data-table-td-bold">
                  <a
                    href={`#/symbols/${item.symbol}`}
                    className="flex items-center"
                  >
                    <span>{item.symbol}</span>
                    {item.in_vn30 && (
                      <span className="badge-vn30">VN30</span>
                    )}
                  </a>
                </td>

                {/* Exchange */}
                <td className="data-table-td text-muted">
                  {item.exchange}
                </td>

                {/* Close */}
                <td className="data-table-td-right font-semibold">
                  {formatPrice(item.close)}
                </td>

                {/* MA10 */}
                <td className="data-table-td-right">
                  {formatPrice(item.ma10)}
                </td>

                {/* Distance % */}
                <td className={`data-table-td-right font-semibold ${distanceColorClass}`}>
                  {formatDistance(item.distance_pct)}
                </td>

                {/* Volume */}
                <td
                  className="data-table-td-right"
                  title={formatVolume(item.volume)}
                >
                  {formatVolumeCompact(item.volume)}
                </td>

                {/* Avg Volume 20D */}
                <td
                  className="data-table-td-right"
                  title={formatVolume(item.avg_volume_20d)}
                >
                  {formatVolumeCompact(item.avg_volume_20d)}
                </td>

                {/* Signal */}
                <td className="data-table-td">
                  <SignalBadge signal={item.signal} />
                </td>

                {/* Data status */}
                <td className="data-table-td text-muted text-small">
                  {DATA_STATUS_LABELS[item.data_status] || item.data_status}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};
