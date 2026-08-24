import { z } from 'zod';
import { DataStatusSchema, SignalTypeSchema } from './screenerSchema';

export const SymbolSeriesPointSchema = z.object({
  trading_date: z.string(),
  open: z.number(),
  high: z.number(),
  low: z.number(),
  close: z.number(),
  ma10: z.number().nullable(),
  volume: z.number().int(),
  signal: SignalTypeSchema.nullable(),
});

export const SymbolExplanationSchema = z.object({
  current_close: z.number().nullable(),
  current_ma10: z.number().nullable(),
  previous_close: z.number().nullable(),
  previous_ma10: z.number().nullable(),
  rule: z.string().nullable(),
});

export const SymbolLatestSchema = z.object({
  close: z.number().nullable(),
  ma10: z.number().nullable(),
  distance_pct: z.number().nullable(),
  signal: SignalTypeSchema.nullable(),
  data_status: DataStatusSchema,
});

export const SymbolDetailSchema = z.object({
  schema_version: z.string(),
  dataset_id: z.string(),
  symbol: z.string(),
  exchange: z.string(),
  as_of_date: z.string(),
  latest: SymbolLatestSchema,
  series: z.array(SymbolSeriesPointSchema),
  explanation: SymbolExplanationSchema,
});

export type SymbolDetail = z.infer<typeof SymbolDetailSchema>;
export type SymbolSeriesPoint = z.infer<typeof SymbolSeriesPointSchema>;
export type SymbolExplanation = z.infer<typeof SymbolExplanationSchema>;
