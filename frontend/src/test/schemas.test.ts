import { describe, it, expect } from 'vitest';
import { ManifestSchema } from '../schemas/manifestSchema';
import { OverviewSchema } from '../schemas/overviewSchema';
import { ScreenerSchema } from '../schemas/screenerSchema';
import { SymbolDetailSchema } from '../schemas/symbolSchema';

const VALID_DATASET_ID = 'a31f530fd5738909';

describe('Zod runtime schemas validation', () => {
  const validManifest = {
    schema_version: '1.0.0',
    dataset_id: VALID_DATASET_ID,
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

  it('validates a correct manifest schema', () => {
    const result = ManifestSchema.safeParse(validManifest);
    expect(result.success).toBe(true);
  });

  it('rejects invalid non-16-hex dataset_id in manifest', () => {
    const invalidIds = [
      '2026-08-21T11:30:00Z', // ISO string instead of 16-hex
      'a31f530fd573890',      // 15 chars
      'a31f530fd5738909a',     // 17 chars
      'A31F530FD5738909',     // Uppercase
      'g31f530fd5738909',     // Non-hex character
    ];
    for (const id of invalidIds) {
      const result = ManifestSchema.safeParse({ ...validManifest, dataset_id: id });
      expect(result.success).toBe(false);
    }
  });

  it('rejects unsupported schema versions', () => {
    const invalidVersions = ['2.0.0', '1.1.0', '0.9.0', 'beta-1'];
    for (const v of invalidVersions) {
      const result = ManifestSchema.safeParse({ ...validManifest, schema_version: v });
      expect(result.success).toBe(false);
    }
  });

  it('rejects invalid Gregorian calendar dates (e.g. Feb 30th or Month 13)', () => {
    const invalidDates = ['2026-02-30', '2026-13-01', '2026-00-10', '2026-04-31', '2026-02-29']; // 2026 is not a leap year
    for (const d of invalidDates) {
      const result = ManifestSchema.safeParse({ ...validManifest, as_of_date: d });
      expect(result.success).toBe(false);
    }
  });

  it('rejects strict object undeclared keys in manifest', () => {
    const result = ManifestSchema.safeParse({
      ...validManifest,
      extra_unknown_key: 'malicious_payload',
    });
    expect(result.success).toBe(false);
  });

  it('rejects manifest quality accounting invariant violations', () => {
    // 1. input != accepted + rejected
    const badMath = {
      ...validManifest,
      quality: {
        ...validManifest.quality,
        input_rows: 1000,
        accepted_rows: 900,
        rejected_rows: 50, // 900 + 50 != 1000
      },
    };
    expect(ManifestSchema.safeParse(badMath).success).toBe(false);

    // 2. eligible_symbols > accepted_rows
    const badEligible = {
      ...validManifest,
      quality: {
        ...validManifest.quality,
        input_rows: 10,
        accepted_rows: 10,
        rejected_rows: 0,
        eligible_symbols: 15, // 15 > 10
      },
    };
    expect(ManifestSchema.safeParse(badEligible).success).toBe(false);
  });

  it('validates an overview schema with correct math consistency', () => {
    const validOverview = {
      schema_version: '1.0.0',
      dataset_id: VALID_DATASET_ID,
      as_of_date: '2026-08-21',
      metrics: {
        eligible_count: 10,
        above_count: 6,
        above_pct: 60.0,
        below_count: 3,
        below_pct: 30.0,
        on_ma10_count: 1,
        cross_up_count: 2,
        cross_down_count: 1,
      },
      breadth_history: [
        {
          trading_date: '2026-08-21',
          eligible_count: 10,
          above_count: 6,
          above_pct: 60.0,
        },
      ],
    };

    const result = OverviewSchema.safeParse(validOverview);
    expect(result.success).toBe(true);
  });

  it('rejects overview schema when percentage math does not match symbol counts', () => {
    const badOverview = {
      schema_version: '1.0.0',
      dataset_id: VALID_DATASET_ID,
      as_of_date: '2026-08-21',
      metrics: {
        eligible_count: 10,
        above_count: 6,
        above_pct: 75.0, // 6/10 is 60.0, not 75.0!
        below_count: 4,
        below_pct: 40.0,
        on_ma10_count: 0,
        cross_up_count: 0,
        cross_down_count: 0,
      },
      breadth_history: [],
    };

    const result = OverviewSchema.safeParse(badOverview);
    expect(result.success).toBe(false);
  });

  it('rejects overview schema when eligible_count != above + below + on_ma10', () => {
    const badSumOverview = {
      schema_version: '1.0.0',
      dataset_id: VALID_DATASET_ID,
      as_of_date: '2026-08-21',
      metrics: {
        eligible_count: 10,
        above_count: 5,
        above_pct: 50.0,
        below_count: 4,
        below_pct: 40.0,
        on_ma10_count: 0, // 5 + 4 + 0 = 9 != 10
        cross_up_count: 0,
        cross_down_count: 0,
      },
      breadth_history: [],
    };

    const result = OverviewSchema.safeParse(badSumOverview);
    expect(result.success).toBe(false);
  });

  it('validates a screener schema item with typed SignalReason', () => {
    const validScreener = {
      schema_version: '1.0.0',
      dataset_id: VALID_DATASET_ID,
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
          symbol: 'VNM',
          exchange: 'HOSE',
          in_vn30: true,
          last_trading_date: '2026-08-21',
          close: 75.0,
          ma10: 75.0,
          distance_pct: 0.0,
          volume: 1200000,
          avg_volume_20d: 1500000,
          signal: null,
          signal_reason: 'ON_MA10',
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

  it('rejects screener items with arbitrary non-enum signal_reason', () => {
    const badScreener = {
      schema_version: '1.0.0',
      dataset_id: VALID_DATASET_ID,
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
          signal_reason: 'ARBITRARY_CUSTOM_STRING', // invalid enum!
          data_status: 'VALID',
        },
      ],
    };

    const result = ScreenerSchema.safeParse(badScreener);
    expect(result.success).toBe(false);
  });

  it('validates symbol detail schema and enforces OHLC bounds', () => {
    const validDetail = {
      schema_version: '1.0.0',
      dataset_id: VALID_DATASET_ID,
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

  it('rejects symbol detail series when high < low or high < close', () => {
    const badDetail = {
      schema_version: '1.0.0',
      dataset_id: VALID_DATASET_ID,
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
          high: 99.0, // High < Open/Close!
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

    const result = SymbolDetailSchema.safeParse(badDetail);
    expect(result.success).toBe(false);
  });

  it('rejects symbol detail explanation with arbitrary non-enum rule', () => {
    const badDetail = {
      schema_version: '1.0.0',
      dataset_id: VALID_DATASET_ID,
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
        rule: 'UNAPPROVED_CUSTOM_RULE', // Invalid enum!
      },
    };

    const result = SymbolDetailSchema.safeParse(badDetail);
    expect(result.success).toBe(false);
  });
});
