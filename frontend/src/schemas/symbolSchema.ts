import { z } from 'zod';
import {
  DataStatusSchema,
  SignalReasonSchema,
  SignalTypeSchema,
} from './screenerSchema';
import {
  DatasetIdSchema,
  GregorianDateSchema,
  PositiveFiniteNumber,
} from './validationUtils';

export const SymbolSeriesPointSchema = z
  .object({
    trading_date: GregorianDateSchema,
    open: PositiveFiniteNumber,
    high: PositiveFiniteNumber,
    low: PositiveFiniteNumber,
    close: PositiveFiniteNumber,
    ma10: PositiveFiniteNumber.nullable(),
    volume: z.number().int().nonnegative(),
    signal: SignalTypeSchema.nullable(),
  })
  .strict()
  .refine(
    (p) =>
      p.high >= p.low &&
      p.high >= p.open &&
      p.high >= p.close &&
      p.low <= p.open &&
      p.low <= p.close,
    {
      message: 'OHLC bounds violated: high must be >= open/close/low and low must be <= open/close/high',
      path: ['high'],
    }
  );

export const SymbolExplanationSchema = z
  .object({
    current_close: PositiveFiniteNumber.nullable(),
    current_ma10: PositiveFiniteNumber.nullable(),
    previous_close: PositiveFiniteNumber.nullable(),
    previous_ma10: PositiveFiniteNumber.nullable(),
    rule: SignalReasonSchema.nullable(),
  })
  .strict();

export const SymbolLatestSchema = z
  .object({
    close: PositiveFiniteNumber.nullable(),
    ma10: PositiveFiniteNumber.nullable(),
    distance_pct: z.number().finite().nullable(),
    signal: SignalTypeSchema.nullable(),
    data_status: DataStatusSchema,
  })
  .strict();

export const SymbolDetailSchema = z
  .object({
    schema_version: z.literal('1.0.0'),
    dataset_id: DatasetIdSchema,
    symbol: z.string().regex(/^[A-Z0-9]{1,10}$/, 'Mã cổ phiếu phải gồm 1-10 ký tự in hoa/số'),
    exchange: z.enum(['HOSE', 'HNX', 'UPCOM']),
    as_of_date: GregorianDateSchema,
    latest: SymbolLatestSchema,
    series: z.array(SymbolSeriesPointSchema),
    explanation: SymbolExplanationSchema,
  })
  .strict();

export type SymbolDetail = z.infer<typeof SymbolDetailSchema>;
export type SymbolSeriesPoint = z.infer<typeof SymbolSeriesPointSchema>;
export type SymbolExplanation = z.infer<typeof SymbolExplanationSchema>;
export type SymbolLatest = z.infer<typeof SymbolLatestSchema>;
