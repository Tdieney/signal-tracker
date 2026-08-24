import { z } from 'zod';

export const BreadthMetricSchema = z.object({
  eligible_count: z.number().int().nonnegative(),
  above_count: z.number().int().nonnegative(),
  above_pct: z.number().nullable(),
  below_count: z.number().int().nonnegative(),
  below_pct: z.number().nullable(),
  on_ma10_count: z.number().int().nonnegative(),
  cross_up_count: z.number().int().nonnegative(),
  cross_down_count: z.number().int().nonnegative(),
});

export const BreadthHistoryPointSchema = z.object({
  trading_date: z.string(),
  eligible_count: z.number().int().nonnegative(),
  above_count: z.number().int().nonnegative(),
  above_pct: z.number().nullable(),
});

export const OverviewSchema = z.object({
  schema_version: z.string(),
  dataset_id: z.string(),
  as_of_date: z.string(),
  metrics: BreadthMetricSchema,
  breadth_history: z.array(BreadthHistoryPointSchema),
});

export type Overview = z.infer<typeof OverviewSchema>;
export type BreadthMetric = z.infer<typeof BreadthMetricSchema>;
export type BreadthHistoryPoint = z.infer<typeof BreadthHistoryPointSchema>;
