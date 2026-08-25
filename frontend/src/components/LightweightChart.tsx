import React, { useEffect, useRef, useState } from 'react';
import { Table, BarChart2 } from 'lucide-react';
import {
  ColorType,
  CrosshairMode,
  createChart,
  IChartApi,
} from 'lightweight-charts';
import { SymbolSeriesPoint } from '../schemas/symbolSchema';
import { formatDateVi, formatPrice, formatVolume } from '../lib/formatters';

interface LightweightChartProps {
  series: SymbolSeriesPoint[];
  symbol: string;
}

export const LightweightChart: React.FC<LightweightChartProps> = ({
  series,
  symbol,
}) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const [showTable, setShowTable] = useState(false);

  useEffect(() => {
    if (showTable || !chartContainerRef.current || series.length === 0) return;

    // Initialize Chart
    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#ffffff' },
        textColor: '#1f242f',
        fontSize: 12,
        fontFamily: 'Inter, sans-serif',
      },
      grid: {
        vertLines: { color: '#f1f3f7' },
        horzLines: { color: '#f1f3f7' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
      },
      rightPriceScale: {
        borderColor: '#e1e5ee',
        scaleMargins: {
          top: 0.1,
          bottom: 0.25,
        },
      },
      timeScale: {
        borderColor: '#e1e5ee',
        timeVisible: false,
      },
      handleScale: true,
      handleScroll: true,
    });

    chartRef.current = chart;

    // 1. Candlestick Series
    const candleSeries = chart.addCandlestickSeries({
      upColor: '#087a55',
      downColor: '#b42318',
      borderUpColor: '#087a55',
      borderDownColor: '#b42318',
      wickUpColor: '#087a55',
      wickDownColor: '#b42318',
    });

    const candleData = series.map((s) => ({
      time: s.trading_date,
      open: s.open,
      high: s.high,
      low: s.low,
      close: s.close,
    }));
    candleSeries.setData(candleData);

    // 2. MA10 Line Series
    const ma10Series = chart.addLineSeries({
      color: '#2457d6',
      lineWidth: 2,
      priceLineVisible: false,
    });

    const ma10Data = series
      .filter((s) => s.ma10 !== null && s.ma10 !== undefined)
      .map((s) => ({
        time: s.trading_date,
        value: s.ma10 as number,
      }));
    ma10Series.setData(ma10Data);

    // 3. Volume Histogram Series
    const volumeSeries = chart.addHistogramSeries({
      color: '#9ba4b5',
      priceFormat: {
        type: 'volume',
      },
      priceScaleId: '', // Overlay scale
    });

    volumeSeries.priceScale().applyOptions({
      scaleMargins: {
        top: 0.8,
        bottom: 0,
      },
    });

    const volumeData = series.map((s) => ({
      time: s.trading_date,
      value: s.volume,
      color: s.close >= s.open ? 'rgba(8, 122, 85, 0.4)' : 'rgba(180, 35, 24, 0.4)',
    }));
    volumeSeries.setData(volumeData);

    chart.timeScale().fitContent();

    // Responsive Resize Observer
    const resizeObserver = new ResizeObserver((entries) => {
      if (entries.length === 0 || !entries[0].contentRect) return;
      const { width, height } = entries[0].contentRect;
      chart.applyOptions({ width, height });
    });

    resizeObserver.observe(chartContainerRef.current);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
      chartRef.current = null;
    };
  }, [series, showTable]);

  return (
    <div className="card chart-panel">
      <div className="chart-header">
        <div>
          <h2 className="text-h2">
            Biểu đồ giá &amp; MA10 — {symbol}
          </h2>
          <div className="chart-legend mt-1">
            <span className="chart-legend-item">
              <span className="legend-swatch-up" aria-hidden="true" />
              <span>Tăng</span>
            </span>
            <span className="chart-legend-item">
              <span className="legend-swatch-down" aria-hidden="true" />
              <span>Giảm</span>
            </span>
            <span className="chart-legend-item">
              <span className="legend-swatch-ma10" aria-hidden="true" />
              <span>MA10</span>
            </span>
          </div>
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
          ref={chartContainerRef}
          role="region"
          aria-label={`Biểu đồ nến kỹ thuật và đường trung bình MA10 của mã ${symbol}`}
          tabIndex={0}
          className="chart-container-lightweight"
        />
      ) : (
        <div
          className="chart-table-alt-wrapper"
          tabIndex={0}
          role="region"
          aria-label={`Bảng dữ liệu lịch sử giá và MA10 của mã ${symbol}`}
        >
          <div className="scrollable-region chart-table-scroll">
            <table className="data-table">
              <thead>
                <tr className="data-table-header-row">
                  <th className="data-table-th">Ngày</th>
                  <th className="data-table-th data-table-th-right">Open</th>
                  <th className="data-table-th data-table-th-right">High</th>
                  <th className="data-table-th data-table-th-right">Low</th>
                  <th className="data-table-th data-table-th-right">Close</th>
                  <th className="data-table-th data-table-th-right">MA10</th>
                  <th className="data-table-th data-table-th-right">Volume</th>
                </tr>
              </thead>
              <tbody>
                {series.slice().reverse().map((s, idx) => (
                  <tr
                    key={s.trading_date}
                    className={`data-table-row ${idx % 2 !== 0 ? 'data-table-row-alt' : ''}`}
                  >
                    <td className="data-table-td font-semibold">{formatDateVi(s.trading_date)}</td>
                    <td className="data-table-td-right">{formatPrice(s.open)}</td>
                    <td className="data-table-td-right">{formatPrice(s.high)}</td>
                    <td className="data-table-td-right">{formatPrice(s.low)}</td>
                    <td className="data-table-td-right font-bold">{formatPrice(s.close)}</td>
                    <td className="data-table-td-right">{formatPrice(s.ma10)}</td>
                    <td className="data-table-td-right">{formatVolume(s.volume)}</td>
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
