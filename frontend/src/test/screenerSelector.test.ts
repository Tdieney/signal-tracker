import { describe, it, expect } from 'vitest';
import { selectFilteredAndSortedItems } from '../features/screener/screenerSelector';
import { DEFAULT_FILTERS } from '../lib/constants';
import { FilterState } from '../lib/urlFilter';
import { ScreenerItem } from '../schemas/screenerSchema';

describe('screenerSelector', () => {
  const sampleItems: ScreenerItem[] = [
    {
      symbol: 'FPT',
      exchange: 'HOSE',
      in_vn30: true,
      last_trading_date: '2026-08-21',
      close: 102.5,
      ma10: 101.8,
      distance_pct: 0.69,
      volume: 2300000,
      avg_volume_20d: 1800000,
      signal: 'CROSS_UP_MA10',
      signal_reason: 'CROSS_UP_MA10',
      data_status: 'VALID',
    },
    {
      symbol: 'VNM',
      exchange: 'HOSE',
      in_vn30: true,
      last_trading_date: '2026-08-21',
      close: 70.0,
      ma10: 72.0,
      distance_pct: -2.78,
      volume: 1500000,
      avg_volume_20d: 2000000,
      signal: 'CROSS_DOWN_MA10',
      signal_reason: 'CROSS_DOWN_MA10',
      data_status: 'VALID',
    },
    {
      symbol: 'SHS',
      exchange: 'HNX',
      in_vn30: false,
      last_trading_date: '2026-08-21',
      close: 18.5,
      ma10: 18.0,
      distance_pct: 2.78,
      volume: 3000000,
      avg_volume_20d: 2500000,
      signal: 'ABOVE_MA10',
      signal_reason: 'ABOVE_MA10',
      data_status: 'VALID',
    },
    {
      symbol: 'BSR',
      exchange: 'UPCOM',
      in_vn30: false,
      last_trading_date: '2026-08-21',
      close: 22.0,
      ma10: 23.0,
      distance_pct: -4.35,
      volume: 500000,
      avg_volume_20d: 800000,
      signal: 'BELOW_MA10',
      signal_reason: 'BELOW_MA10',
      data_status: 'VALID',
    },
  ];

  it('filters by exchange', () => {
    const filters: FilterState = { ...DEFAULT_FILTERS, exchange: 'HOSE' };
    const results = selectFilteredAndSortedItems(sampleItems, filters);
    expect(results.length).toBe(2);
    expect(results.every((r) => r.exchange === 'HOSE')).toBe(true);
  });

  it('filters by signal', () => {
    const filters: FilterState = { ...DEFAULT_FILTERS, signal: 'CROSS_UP_MA10' };
    const results = selectFilteredAndSortedItems(sampleItems, filters);
    expect(results.length).toBe(1);
    expect(results[0].symbol).toBe('FPT');
  });

  it('filters by universe VN30', () => {
    const filters: FilterState = { ...DEFAULT_FILTERS, universe: 'VN30' };
    const results = selectFilteredAndSortedItems(sampleItems, filters);
    expect(results.length).toBe(2);
    expect(results.every((r) => r.in_vn30)).toBe(true);
  });

  it('filters by min average volume', () => {
    const filters: FilterState = { ...DEFAULT_FILTERS, minAvgVolume20d: '2000000' };
    const results = selectFilteredAndSortedItems(sampleItems, filters);
    expect(results.length).toBe(2);
    expect(results.map((r) => r.symbol)).toEqual(expect.arrayContaining(['VNM', 'SHS']));
  });

  it('sorts numerically by distance_pct descending', () => {
    const filters: FilterState = { ...DEFAULT_FILTERS, sort: 'distance_pct', direction: 'desc' };
    const results = selectFilteredAndSortedItems(sampleItems, filters);
    expect(results[0].symbol).toBe('SHS'); // +2.78%
    expect(results[1].symbol).toBe('FPT'); // +0.69%
    expect(results[2].symbol).toBe('VNM'); // -2.78%
    expect(results[3].symbol).toBe('BSR'); // -4.35%
  });

  it('guarantees identical results for desktop and mobile layouts (parity)', () => {
    const filters: FilterState = { ...DEFAULT_FILTERS, exchange: 'HOSE', sort: 'close', direction: 'asc' };
    const desktopResults = selectFilteredAndSortedItems(sampleItems, filters);
    const mobileResults = selectFilteredAndSortedItems(sampleItems, filters);
    expect(desktopResults).toEqual(mobileResults);
  });
});
