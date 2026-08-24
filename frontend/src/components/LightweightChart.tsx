import React, { useEffect, useRef, useState } from 'react';
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

export const LightweightChart: React.FC<LightweightChartProps> = ({ series, symbol }) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const [showDataAlternative, setShowDataAlternative] = useState(false);

  useEffect(() => {
    if (!chartContainerRef.current || series.length === 0) return;

    // Create TradingView Lightweight Chart instance
    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#ffffff' },
        textColor: '#566176',
        fontSize: 12,
        fontFamily: 'Inter, system-ui, sans-serif',
      },
      grid: {
        vertLines: { color: '#eef2f7' },
        horzLines: { color: '#eef2f7' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
      },
      rightPriceScale: {
        borderColor: '#d7deea',
        scaleMargins: {
          top: 0.1,
          bottom: 0.25, // Leave bottom space for volume histogram
        },
      },
      timeScale: {
        borderColor: '#d7deea',
        timeVisible: false,
      },
      width: chartContainerRef.current.clientWidth,
      height: 380,
    });

    chartRef.current = chart;

    // 1. Candlestick Series
    const candleSeries = chart.addCandlestickSeries({
      upColor: '#087a55',
      downColor: '#b42318',
      borderVisible: false,
      wickUpColor: '#087a55',
      wickDownColor: '#b42318',
    });

    // 2. MA10 Line Series
    const ma10Series = chart.addLineSeries({
      color: '#2457d6',
      lineWidth: 2,
      priceLineVisible: false,
      title: 'MA10',
    });

    // 3. Volume Histogram Series (scaled at bottom)
    const volumeSeries = chart.addHistogramSeries({
      color: '#a0aec0',
      priceFormat: {
        type: 'volume',
      },
      priceScaleId: 'volume',
    });

    chart.priceScale('volume').applyOptions({
      scaleMargins: {
        top: 0.8,
        bottom: 0,
      },
    });

    // Prepare data arrays
    const candleData = series.map((s) => ({
      time: s.trading_date,
      open: s.open,
      high: s.high,
      low: s.low,
      close: s.close,
    }));

    const ma10Data = series
      .filter((s) => s.ma10 !== null && s.ma10 !== undefined)
      .map((s) => ({
        time: s.trading_date,
        value: s.ma10 as number,
      }));

    const volumeData = series.map((s) => ({
      time: s.trading_date,
      value: s.volume,
      color: s.close >= s.open ? 'rgba(8, 122, 85, 0.35)' : 'rgba(180, 35, 24, 0.35)',
    }));

    candleSeries.setData(candleData);
    ma10Series.setData(ma10Data);
    volumeSeries.setData(volumeData);

    // Fit content
    chart.timeScale().fitContent();

    // Resize Observer for container responsiveness
    const resizeObserver = new ResizeObserver((entries) => {
      if (entries.length === 0 || !entries[0].contentRect) return;
      const { width } = entries[0].contentRect;
      chart.applyOptions({ width });
    });

    resizeObserver.observe(chartContainerRef.current);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
      chartRef.current = null;
    };
  }, [series]);

  return (
    <div className="card" style={{ padding: 'var(--space-4)', marginBottom: 'var(--space-5)' }}>
      {/* Header and Controls */}
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
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
          <h2 className="text-h2">Biểu đồ giá & MA10</h2>
          {/* Legend */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', fontSize: '0.8125rem' }}>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
              <span style={{ width: '12px', height: '12px', backgroundColor: '#087a55', borderRadius: '2px' }} />
              Tăng
            </span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
              <span style={{ width: '12px', height: '12px', backgroundColor: '#b42318', borderRadius: '2px' }} />
              Giảm
            </span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
              <span style={{ width: '14px', height: '3px', backgroundColor: '#2457d6', borderRadius: '2px' }} />
              MA10
            </span>
          </div>
        </div>

        <button
          type="button"
          onClick={() => setShowDataAlternative(!showDataAlternative)}
          style={{
            background: 'none',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-sm)',
            padding: 'var(--space-1) var(--space-3)',
            fontSize: '0.8125rem',
            color: 'var(--color-primary)',
            cursor: 'pointer',
          }}
          aria-expanded={showDataAlternative}
        >
          {showDataAlternative ? 'Ẩn bảng số liệu' : 'Xem dạng bảng dữ liệu'}
        </button>
      </div>

      {/* Lightweight Chart Container */}
      <div
        ref={chartContainerRef}
        style={{ width: '100%', height: '380px', position: 'relative' }}
        role="region"
        aria-label={`Biểu đồ nến và đường MA10 cho mã ${symbol}`}
      />

      {/* Accessible Table Alternative */}
      {showDataAlternative && (
        <div style={{ marginTop: 'var(--space-4)', borderTop: '1px solid var(--color-border-subtle)', paddingTop: 'var(--space-3)' }}>
          <div className="scrollable-region" style={{ maxHeight: '260px' }} tabIndex={0}>
            <table
              style={{
                width: '100%',
                borderCollapse: 'collapse',
                fontSize: '0.875rem',
                textAlign: 'left',
              }}
            >
              <caption className="text-small" style={{ textAlign: 'left', paddingBottom: 'var(--space-2)', fontWeight: 600 }}>
                Lịch sử phiên giao dịch gần nhất của {symbol}
              </caption>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--color-border)', backgroundColor: 'var(--color-surface-muted)' }}>
                  <th style={{ padding: 'var(--space-2) var(--space-3)' }}>Phiên</th>
                  <th style={{ padding: 'var(--space-2) var(--space-3)', textAlign: 'right' }}>Open</th>
                  <th style={{ padding: 'var(--space-2) var(--space-3)', textAlign: 'right' }}>High</th>
                  <th style={{ padding: 'var(--space-2) var(--space-3)', textAlign: 'right' }}>Low</th>
                  <th style={{ padding: 'var(--space-2) var(--space-3)', textAlign: 'right' }}>Close</th>
                  <th style={{ padding: 'var(--space-2) var(--space-3)', textAlign: 'right' }}>MA10</th>
                  <th style={{ padding: 'var(--space-2) var(--space-3)', textAlign: 'right' }}>Volume</th>
                </tr>
              </thead>
              <tbody>
                {[...series].reverse().map((pt) => (
                  <tr key={pt.trading_date} style={{ borderBottom: '1px solid var(--color-border-subtle)' }}>
                    <td style={{ padding: 'var(--space-2) var(--space-3)' }}>{formatDateVi(pt.trading_date)}</td>
                    <td style={{ padding: 'var(--space-2) var(--space-3)', textAlign: 'right' }}>{formatPrice(pt.open)}</td>
                    <td style={{ padding: 'var(--space-2) var(--space-3)', textAlign: 'right' }}>{formatPrice(pt.high)}</td>
                    <td style={{ padding: 'var(--space-2) var(--space-3)', textAlign: 'right' }}>{formatPrice(pt.low)}</td>
                    <td style={{ padding: 'var(--space-2) var(--space-3)', textAlign: 'right', fontWeight: 600 }}>{formatPrice(pt.close)}</td>
                    <td style={{ padding: 'var(--space-2) var(--space-3)', textAlign: 'right' }}>{formatPrice(pt.ma10)}</td>
                    <td style={{ padding: 'var(--space-2) var(--space-3)', textAlign: 'right' }}>{formatVolume(pt.volume)}</td>
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
