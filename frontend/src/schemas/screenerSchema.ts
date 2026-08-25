import { z } from 'zod';
import {
  DatasetIdSchema,
  GregorianDateSchema,
  NonNegativeFiniteNumber,
  PositiveFiniteNumber,
} from './validationUtils';

export const SignalTypeSchema = z.enum([
  'ABOVE_MA10',
  'BELOW_MA10',
  'CROSS_UP_MA10',
  'CROSS_DOWN_MA10',
]);

export const SignalReasonSchema = z.enum([
  'ABOVE_MA10',
  'BELOW_MA10',
  'CROSS_UP_MA10',
  'CROSS_DOWN_MA10',
  'ON_MA10',
  'INSUFFICIENT_DATA',
]);

export const DataStatusSchema = z.enum([
  'VALID',
  'INSUFFICIENT_DATA',
  'NO_DATA_FOR_AS_OF_DATE',
  'INVALID_DATA',
]);

export const ScreenerItemSchema = z
  .object({
    symbol: z.string().regex(/^[A-Z0-9]{1,10}$/, 'Mã cổ phiếu phải gồm 1-10 ký tự in hoa/số'),
    exchange: z.enum(['HOSE', 'HNX', 'UPCOM']),
    in_vn30: z.boolean(),
    last_trading_date: GregorianDateSchema.nullable(),
    close: PositiveFiniteNumber.nullable(),
    ma10: PositiveFiniteNumber.nullable(),
    distance_pct: z.number().finite().nullable(),
    volume: z.number().int().nonnegative().nullable(),
    avg_volume_20d: NonNegativeFiniteNumber.nullable(),
    signal: SignalTypeSchema.nullable(),
    signal_reason: SignalReasonSchema.nullable(),
    data_status: DataStatusSchema,
  })
  .strict();

export const ScreenerSchema = z
  .object({
    schema_version: z.literal('1.0.0'),
    dataset_id: DatasetIdSchema,
    as_of_date: GregorianDateSchema,
    items: z.array(ScreenerItemSchema),
  })
  .strict();

export type Screener = z.infer<typeof ScreenerSchema>;
export type ScreenerItem = z.infer<typeof ScreenerItemSchema>;
export type SignalType = z.infer<typeof SignalTypeSchema>;
export type SignalReason = z.infer<typeof SignalReasonSchema>;
export type DataStatus = z.infer<typeof DataStatusSchema>;
