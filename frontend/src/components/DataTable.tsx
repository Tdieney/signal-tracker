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
      className="scrollable-region card"
      style={{ padding: 0, overflowX: 'auto', border: '1px solid var(--color-border)' }}
      tabIndex={0}
      role="region"
      aria-label="Bảng kết quả lọc cổ phiếu"
    >
      <table
        style={{
          width: '100%',
          borderCollapse: 'collapse',
          fontSize: '0.875rem',
          textAlign: 'left',
        }}
      >
        <thead>
          <tr
            style={{
              backgroundColor: 'var(--color-surface-muted)',
              borderBottom: '1px solid var(--color-border)',
              position: 'sticky',
              top: 0,
              zIndex: 10,
            }}
          >
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
                  style={{
                    padding: 'var(--space-3) var(--space-4)',
                    fontWeight: 600,
                    color: 'var(--color-text)',
                    textAlign: col.align || 'left',
                    whiteSpace: 'nowrap',
                  }}
                >
                  <button
                    type="button"
                    onClick={() => onSortChange(col.key)}
                    style={{
                      background: 'none',
                      border: 'none',
                      padding: 0,
                      font: 'inherit',
                      fontWeight: 600,
                      color: isCurrentSort ? 'var(--color-primary-strong)' : 'inherit',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px',
                      cursor: 'pointer',
                      textAlign: col.align || 'left',
                    }}
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
                      <ArrowUpDown size={14} aria-hidden="true" style={{ opacity: 0.4 }} />
                    )}
                  </button>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {items.map((item, idx) => {
            const isEven = idx % 2 === 0;
            const distanceColor =
              item.distance_pct !== null && item.distance_pct !== undefined
                ? item.distance_pct > 0
                  ? 'var(--color-positive)'
                  : item.distance_pct < 0
                  ? 'var(--color-negative)'
                  : 'inherit'
                : 'inherit';

            return (
              <tr
                key={item.symbol}
                style={{
                  backgroundColor: isEven ? 'var(--color-surface)' : 'var(--color-surface-subtle)',
                  borderBottom: '1px solid var(--color-border-subtle)',
                  transition: 'background-color 100ms ease',
                }}
              >
                {/* Symbol Link */}
                <td style={{ padding: 'var(--space-3) var(--space-4)', fontWeight: 700 }}>
                  <a
                    href={`#/symbols/${item.symbol}`}
                    style={{
                      color: 'var(--color-primary)',
                      textDecoration: 'none',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 'var(--space-1)',
                    }}
                  >
                    {item.symbol}
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
                  </a>
                </td>

                {/* Exchange */}
                <td style={{ padding: 'var(--space-3) var(--space-4)', color: 'var(--color-text-muted)' }}>
                  {item.exchange}
                </td>

                {/* Close */}
                <td style={{ padding: 'var(--space-3) var(--space-4)', textAlign: 'right', fontWeight: 600 }}>
                  {formatPrice(item.close)}
                </td>

                {/* MA10 */}
                <td style={{ padding: 'var(--space-3) var(--space-4)', textAlign: 'right' }}>
                  {formatPrice(item.ma10)}
                </td>

                {/* Distance % */}
                <td
                  style={{
                    padding: 'var(--space-3) var(--space-4)',
                    textAlign: 'right',
                    fontWeight: 600,
                    color: distanceColor,
                  }}
                >
                  {formatDistance(item.distance_pct)}
                </td>

                {/* Volume */}
                <td
                  style={{ padding: 'var(--space-3) var(--space-4)', textAlign: 'right' }}
                  title={formatVolume(item.volume)}
                >
                  {formatVolumeCompact(item.volume)}
                </td>

                {/* Avg Volume 20D */}
                <td
                  style={{ padding: 'var(--space-3) var(--space-4)', textAlign: 'right' }}
                  title={formatVolume(item.avg_volume_20d)}
                >
                  {formatVolumeCompact(item.avg_volume_20d)}
                </td>

                {/* Signal */}
                <td style={{ padding: 'var(--space-3) var(--space-4)' }}>
                  <SignalBadge signal={item.signal} />
                </td>

                {/* Data status */}
                <td style={{ padding: 'var(--space-3) var(--space-4)', color: 'var(--color-text-muted)', fontSize: '0.8125rem' }}>
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
