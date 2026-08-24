import React, { useState } from 'react';
import { BreadthHistoryPoint } from '../schemas/overviewSchema';
import { formatDateVi, formatPercent } from '../lib/formatters';

interface BreadthChartProps {
  history: BreadthHistoryPoint[];
}

export const BreadthChart: React.FC<BreadthChartProps> = ({ history }) => {
  const [showTableAlt, setShowTableAlt] = useState(false);

  if (!history || history.length === 0) {
    return (
      <div className="card" style={{ padding: 'var(--space-5)', textAlign: 'center' }}>
        <p className="text-small" style={{ color: 'var(--color-text-muted)' }}>
          Chưa có dữ liệu lịch sử độ rộng thị trường.
        </p>
      </div>
    );
  }

  // Find max and min for SVG scaling
  const validPoints = history.filter((pt) => pt.above_pct !== null && pt.above_pct !== undefined);
  const width = 800;
  const height = 220;
  const padding = { top: 20, right: 30, bottom: 30, left: 40 };

  const chartW = width - padding.left - padding.right;
  const chartH = height - padding.top - padding.bottom;

  // Build SVG path
  const points = validPoints.map((pt, i) => {
    const x = padding.left + (i / Math.max(validPoints.length - 1, 1)) * chartW;
    const y = padding.top + chartH - ((pt.above_pct ?? 0) / 100) * chartH;
    return { x, y, pt };
  });

  const pathD = points.reduce((acc, p, i) => {
    return i === 0 ? `M ${p.x} ${p.y}` : `${acc} L ${p.x} ${p.y}`;
  }, '');

  const areaD = points.length > 0
    ? `${pathD} L ${points[points.length - 1].x} ${padding.top + chartH} L ${points[0].x} ${padding.top + chartH} Z`
    : '';

  return (
    <div className="card" style={{ padding: 'var(--space-4)' }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 'var(--space-2)',
          marginBottom: 'var(--space-3)',
        }}
      >
        <div>
          <h2 className="text-h2">Độ rộng thị trường MA10 ({validPoints.length} phiên)</h2>
          <p className="text-xs" style={{ color: 'var(--color-text-muted)', marginTop: '2px' }}>
            Tỷ lệ cổ phiếu có giá đóng cửa trên MA10 theo thời gian
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowTableAlt(!showTableAlt)}
          style={{
            background: 'none',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-sm)',
            padding: 'var(--space-1) var(--space-3)',
            fontSize: '0.8125rem',
            color: 'var(--color-primary)',
            cursor: 'pointer',
          }}
          aria-expanded={showTableAlt}
        >
          {showTableAlt ? 'Ẩn bảng số liệu' : 'Xem bảng số liệu chi tiết'}
        </button>
      </div>

      {/* Responsive SVG Chart */}
      <div
        className="scrollable-region"
        style={{ position: 'relative', width: '100%', minHeight: '220px' }}
        tabIndex={0}
        role="region"
        aria-label="Biểu đồ tỷ lệ cổ phiếu trên MA10 theo các phiên gần nhất"
      >
        <svg
          viewBox={`0 0 ${width} ${height}`}
          style={{ width: '100%', height: 'auto', display: 'block', overflow: 'visible' }}
          role="img"
          aria-hidden="true"
        >
          {/* Background grid lines */}
          <line
            x1={padding.left}
            y1={padding.top}
            x2={width - padding.right}
            y2={padding.top}
            stroke="var(--color-border-subtle)"
            strokeDasharray="4 4"
          />
          <text x={padding.left - 8} y={padding.top + 4} textAnchor="end" fontSize="11" fill="var(--color-text-muted)">
            100%
          </text>

          <line
            x1={padding.left}
            y1={padding.top + chartH * 0.5}
            x2={width - padding.right}
            y2={padding.top + chartH * 0.5}
            stroke="var(--color-border-subtle)"
            strokeDasharray="4 4"
          />
          <text x={padding.left - 8} y={padding.top + chartH * 0.5 + 4} textAnchor="end" fontSize="11" fill="var(--color-text-muted)">
            50%
          </text>

          <line
            x1={padding.left}
            y1={padding.top + chartH}
            x2={width - padding.right}
            y2={padding.top + chartH}
            stroke="var(--color-border)"
          />
          <text x={padding.left - 8} y={padding.top + chartH + 4} textAnchor="end" fontSize="11" fill="var(--color-text-muted)">
            0%
          </text>

          {/* Area fill */}
          {areaD && <path d={areaD} fill="rgba(36, 87, 214, 0.08)" />}

          {/* Line */}
          {pathD && (
            <path
              d={pathD}
              fill="none"
              stroke="var(--color-primary)"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          )}

          {/* Points */}
          {points.map((p, i) => (
            <g key={i}>
              <circle
                cx={p.x}
                cy={p.y}
                r="4"
                fill="var(--color-surface)"
                stroke="var(--color-primary)"
                strokeWidth="2"
              />
            </g>
          ))}

          {/* X axis dates */}
          {points.length > 0 && (
            <>
              <text x={points[0].x} y={height - 8} textAnchor="start" fontSize="11" fill="var(--color-text-muted)">
                {formatDateVi(points[0].pt.trading_date)}
              </text>
              <text
                x={points[points.length - 1].x}
                y={height - 8}
                textAnchor="end"
                fontSize="11"
                fill="var(--color-text-muted)"
              >
                {formatDateVi(points[points.length - 1].pt.trading_date)}
              </text>
            </>
          )}
        </svg>
      </div>

      {/* Accessible Table Alternative */}
      {showTableAlt && (
        <div style={{ marginTop: 'var(--space-4)', borderTop: '1px solid var(--color-border-subtle)', paddingTop: 'var(--space-3)' }}>
          <div className="scrollable-region" style={{ maxHeight: '240px' }} tabIndex={0}>
            <table
              style={{
                width: '100%',
                borderCollapse: 'collapse',
                fontSize: '0.875rem',
                textAlign: 'left',
              }}
            >
              <caption className="text-small" style={{ textAlign: 'left', paddingBottom: 'var(--space-2)', fontWeight: 600 }}>
                Bảng dữ liệu lịch sử độ rộng MA10
              </caption>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--color-border)', backgroundColor: 'var(--color-surface-muted)' }}>
                  <th style={{ padding: 'var(--space-2) var(--space-3)' }}>Phiên</th>
                  <th style={{ padding: 'var(--space-2) var(--space-3)' }}>Số mã đủ dữ liệu</th>
                  <th style={{ padding: 'var(--space-2) var(--space-3)' }}>Số mã trên MA10</th>
                  <th style={{ padding: 'var(--space-2) var(--space-3)' }}>Tỷ lệ trên MA10</th>
                </tr>
              </thead>
              <tbody>
                {[...validPoints].reverse().map((pt) => (
                  <tr key={pt.trading_date} style={{ borderBottom: '1px solid var(--color-border-subtle)' }}>
                    <td style={{ padding: 'var(--space-2) var(--space-3)' }}>{formatDateVi(pt.trading_date)}</td>
                    <td style={{ padding: 'var(--space-2) var(--space-3)' }}>{pt.eligible_count}</td>
                    <td style={{ padding: 'var(--space-2) var(--space-3)' }}>{pt.above_count}</td>
                    <td style={{ padding: 'var(--space-2) var(--space-3)', fontWeight: 600 }}>
                      {formatPercent(pt.above_pct)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
