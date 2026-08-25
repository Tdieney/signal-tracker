import React, { useState } from 'react';
import { Table, BarChart2 } from 'lucide-react';
import { formatDateVi } from '../lib/formatters';
import { BreadthHistoryPoint } from '../schemas/overviewSchema';

interface BreadthChartProps {
  history: BreadthHistoryPoint[];
}

export const BreadthChart: React.FC<BreadthChartProps> = ({ history }) => {
  const [showTable, setShowTable] = useState(false);

  if (!history || history.length === 0) {
    return (
      <div className="card chart-panel text-center text-muted">
        Chưa có dữ liệu lịch sử độ rộng thị trường.
      </div>
    );
  }

  // SVG Chart Dimensions
  const height = 220;
  const width = 800;
  const paddingLeft = 45;
  const paddingRight = 20;
  const paddingTop = 20;
  const paddingBottom = 30;

  const chartWidth = width - paddingLeft - paddingRight;
  const chartHeight = height - paddingTop - paddingBottom;

  const points = history.slice(-60); // Maximum 60 sessions
  const n = points.length;
  const xStep = n > 1 ? chartWidth / (n - 1) : 0;

  const svgPoints = points
    .map((p, idx) => {
      const pct = p.above_pct ?? 0;
      const x = paddingLeft + idx * xStep;
      const y = paddingTop + (1 - pct / 100) * chartHeight;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');

  const areaPath =
    points.length > 1
      ? `M ${paddingLeft},${paddingTop + chartHeight} L ${svgPoints.split(' ')[0]} ${points
          .map((p, idx) => {
            const pct = p.above_pct ?? 0;
            const x = paddingLeft + idx * xStep;
            const y = paddingTop + (1 - pct / 100) * chartHeight;
            return `L ${x.toFixed(1)},${y.toFixed(1)}`;
          })
          .join(' ')} L ${(paddingLeft + (n - 1) * xStep).toFixed(1)},${paddingTop + chartHeight} Z`
      : '';

  return (
    <div className="card chart-panel">
      <div className="chart-header">
        <div>
          <h2 className="text-h2">
            Tỷ lệ cổ phiếu trên MA10 (60 phiên gần nhất)
          </h2>
          <span className="text-small">
            Đường đo lường sức mạnh lan tỏa của thị trường (% mã Close &gt; MA10 trên tổng số mã đủ điều kiện)
          </span>
        </div>

        <button
          type="button"
          onClick={() => setShowTable(!showTable)}
          className="chart-toggle-btn"
          aria-expanded={showTable}
          aria-label={showTable ? 'Chuyển sang xem biểu đồ' : 'Chuyển sang xem bảng dữ liệu'}
        >
          {showTable ? (
            <span className="flex items-center gap-1">
              <BarChart2 size={14} aria-hidden="true" />
              <span>Xem biểu đồ</span>
            </span>
          ) : (
            <span className="flex items-center gap-1">
              <Table size={14} aria-hidden="true" />
              <span>Xem dạng bảng</span>
            </span>
          )}
        </button>
      </div>

      {!showTable ? (
        <div
          className="chart-container-svg"
          role="img"
          aria-label="Biểu đồ độ rộng thị trường thể hiện tỷ lệ phần trăm cổ phiếu nằm trên đường MA10 trong 60 phiên gần nhất"
        >
          <svg
            viewBox={`0 0 ${width} ${height}`}
            width="100%"
            height="100%"
            preserveAspectRatio="none"
          >
            <defs>
              <linearGradient id="breadthAreaGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#2457d6" stopOpacity="0.35" />
                <stop offset="100%" stopColor="#2457d6" stopOpacity="0.0" />
              </linearGradient>
            </defs>

            {/* Grid horizontal lines */}
            {[0, 25, 50, 75, 100].map((level) => {
              const y = paddingTop + (1 - level / 100) * chartHeight;
              return (
                <g key={level}>
                  <line
                    x1={paddingLeft}
                    y1={y}
                    x2={width - paddingRight}
                    y2={y}
                    stroke="var(--color-border-subtle)"
                    strokeDasharray={level === 50 ? '4,4' : undefined}
                    strokeWidth={level === 50 ? '1.5' : '1'}
                  />
                  <text
                    x={paddingLeft - 8}
                    y={y + 4}
                    textAnchor="end"
                    fontSize="11"
                    fill="var(--color-text-subtle)"
                    fontFamily="inherit"
                  >
                    {level}%
                  </text>
                </g>
              );
            })}

            {/* Area Fill */}
            {areaPath && <path d={areaPath} fill="url(#breadthAreaGradient)" />}

            {/* Line Plot */}
            <polyline
              fill="none"
              stroke="var(--color-primary)"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              points={svgPoints}
            />

            {/* First and Last Date Labels */}
            {points.length > 0 && (
              <>
                <text
                  x={paddingLeft}
                  y={height - 8}
                  textAnchor="start"
                  fontSize="11"
                  fill="var(--color-text-subtle)"
                  fontFamily="inherit"
                >
                  {formatDateVi(points[0].trading_date)}
                </text>
                <text
                  x={width - paddingRight}
                  y={height - 8}
                  textAnchor="end"
                  fontSize="11"
                  fill="var(--color-text-subtle)"
                  fontFamily="inherit"
                >
                  {formatDateVi(points[points.length - 1].trading_date)}
                </text>
              </>
            )}
          </svg>
        </div>
      ) : (
        <div
          className="chart-table-alt-wrapper"
          tabIndex={0}
          role="region"
          aria-label="Bảng dữ liệu tỷ lệ cổ phiếu trên MA10 theo phiên"
        >
          <div className="scrollable-region chart-table-scroll">
            <table className="data-table">
              <thead>
                <tr className="data-table-header-row">
                  <th className="data-table-th">Ngày giao dịch</th>
                  <th className="data-table-th data-table-th-right">Mã trên MA10</th>
                  <th className="data-table-th data-table-th-right">Tổng mã đủ điều kiện</th>
                  <th className="data-table-th data-table-th-right">Tỷ lệ (%)</th>
                </tr>
              </thead>
              <tbody>
                {points.slice().reverse().map((p, idx) => (
                  <tr
                    key={p.trading_date}
                    className={`data-table-row ${idx % 2 !== 0 ? 'data-table-row-alt' : ''}`}
                  >
                    <td className="data-table-td font-semibold">{formatDateVi(p.trading_date)}</td>
                    <td className="data-table-td-right text-positive">{p.above_count}</td>
                    <td className="data-table-td-right">{p.eligible_count}</td>
                    <td className="data-table-td-right font-bold">
                      {p.above_pct !== null && p.above_pct !== undefined ? `${p.above_pct}%` : '—'}
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
