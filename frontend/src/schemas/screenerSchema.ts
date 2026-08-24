import { z } from 'zod';

export const SignalTypeSchema = z.enum([
  'ABOVE_MA10',
  'BELOW_MA10',
  'CROSS_UP_MA10',
  'CROSS_DOWN_MA10',
]);

export const DataStatusSchema = z.enum([
  'VALID',
  'INSUFFICIENT_DATA',
  'NO_DATA_FOR_AS_OF_DATE',
  'INVALID_DATA',
]);

export const ScreenerItemSchema = z.object({
  symbol: z.string(),
  exchange: z.string(),
  in_vn30: z.boolean(),
  last_trading_date: z.string().nullable(),
  close: z.number().nullable(),
  ma10: z.number().nullable(),
  distance_pct: z.number().nullable(),
  volume: z.number().int().nullable(),
  avg_volume_20d: z.number().nullable(),
  signal: SignalTypeSchema.nullable(),
  signal_reason: z.string().nullable(),
  data_status: DataStatusSchema,
});

export const ScreenerSchema = z.object({
  schema_version: z.string(),
  dataset_id: z.string(),
  as_of_date: z.string(),
  items: z.array(ScreenerItemSchema),
});

export type Screener = z.infer<typeof ScreenerSchema>;
export type ScreenerItem = z.infer<typeof ScreenerItemSchema>;
export type SignalType = z.infer<typeof SignalTypeSchema>;
export type DataStatus = z.infer<typeof DataStatusSchema>;
