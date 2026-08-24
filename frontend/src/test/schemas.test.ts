import { describe, it, expect } from 'vitest';
import { ManifestSchema } from '../schemas/manifestSchema';
import { OverviewSchema } from '../schemas/overviewSchema';
import { ScreenerSchema } from '../schemas/screenerSchema';
import { SymbolDetailSchema } from '../schemas/symbolSchema';

describe('Zod runtime schemas validation', () => {
  it('validates a correct manifest schema', () => {
    const validManifest = {
      schema_version: '1.0.0',
      dataset_id: '2026-08-21T11:30:00Z',
      as_of_date: '2026-08-21',
      generated_at: '2026-08-21T11:30:00Z',
      market_timezone: 'Asia/Ho_Chi_Minh',
      market_session_status: 'CLOSED_CONFIRMED',
      freshness: {
        status: 'FRESH',
        expected_as_of_date: '2026-08-21',
        reason: 'Latest session',
      },
      provider: 'csv',
      universe: 'ALL',
      files: {
        overview: 'overview.json',
        screener: 'screener.json',
        symbols_base: 'symbols/',
      },
      quality: {
        status: 'PASS',
        input_rows: 1000,
        accepted_rows: 1000,
        rejected_rows: 0,
        eligible_symbols: 100,
        warnings: [],
      },
    };

    const result = ManifestSchema.safeParse(validManifest);
    expect(result.success).toBe(true);
  });

  it('rejects invalid freshness enum values in manifest', () => {
    const invalidManifest = {
      schema_version: '1.0.0',
      dataset_id: '2026-08-21T11:30:00Z',
      as_of_date: '2026-08-21',
      generated_at: '2026-08-21T11:30:00Z',
      market_timezone: 'Asia/Ho_Chi_Minh',
      market_session_status: 'CLOSED_CONFIRMED',
      freshness: {
        status: 'INVALID_FRESHNESS',
        expected_as_of_date: '2026-08-21',
        reason: 'Latest session',
      },
      provider: 'csv',
      universe: 'ALL',
      files: { overview: 'o', screener: 's', symbols_base: 'sym/' },
      quality: { status: 'PASS', input_rows: 1, accepted_rows: 1, rejected_rows: 0, eligible_symbols: 1, warnings: [] },
    };

    const result = ManifestSchema.safeParse(invalidManifest);
    expect(result.success).toBe(false);
  });

  it('validates an overview schema with null breadth percentages', () => {
    const validOverview = {
      schema_version: '1.0.0',
      dataset_id: '2026-08-21T11:30:00Z',
      as_of_date: '2026-08-21',
      metrics: {
        eligible_count: 0,
        above_count: 0,
        above_pct: null,
        below_count: 0,
        below_pct: null,
        on_ma10_count: 0,
        cross_up_count: 0,
        cross_down_count: 0,
      },
      breadth_history: [
        {
          trading_date: '2026-08-21',
          eligible_count: 0,
          above_count: 0,
          above_pct: null,
        },
      ],
    };

    const result = OverviewSchema.safeParse(validOverview);
    expect(result.success).toBe(true);
  });

  it('validates a screener schema item with nullable fields', () => {
    const validScreener = {
      schema_version: '1.0.0',
      dataset_id: '2026-08-21T11:30:00Z',
      as_of_date: '2026-08-21',
      items: [
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
          symbol: 'NEW',
          exchange: 'HOSE',
          in_vn30: false,
          last_trading_date: null,
          close: null,
          ma10: null,
          distance_pct: null,
          volume: null,
          avg_volume_20d: null,
          signal: null,
          signal_reason: null,
          data_status: 'INSUFFICIENT_DATA',
        },
      ],
    };

    const result = ScreenerSchema.safeParse(validScreener);
    expect(result.success).toBe(true);
  });

  it('validates symbol detail schema', () => {
    const validDetail = {
      schema_version: '1.0.0',
      dataset_id: '2026-08-21T11:30:00Z',
      symbol: 'FPT',
      exchange: 'HOSE',
      as_of_date: '2026-08-21',
      latest: {
        close: 102.5,
        ma10: 101.8,
        distance_pct: 0.69,
        signal: 'CROSS_UP_MA10',
        data_status: 'VALID',
      },
      series: [
        {
          trading_date: '2026-08-21',
          open: 101.0,
          high: 103.0,
          low: 100.5,
          close: 102.5,
          ma10: 101.8,
          volume: 2300000,
          signal: 'CROSS_UP_MA10',
        },
      ],
      explanation: {
        current_close: 102.5,
        current_ma10: 101.8,
        previous_close: 100.4,
        previous_ma10: 100.8,
        rule: 'CROSS_UP_MA10',
      },
    };

    const result = SymbolDetailSchema.safeParse(validDetail);
    expect(result.success).toBe(true);
  });
});
