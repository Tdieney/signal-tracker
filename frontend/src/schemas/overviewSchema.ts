import { z } from 'zod';
import {
  DatasetIdSchema,
  GregorianDateSchema,
  PercentageNumber,
  roundTo1Decimal,
} from './validationUtils';

export const BreadthMetricSchema = z
  .object({
    eligible_count: z.number().int().nonnegative(),
    above_count: z.number().int().nonnegative(),
    above_pct: PercentageNumber.nullable(),
    below_count: z.number().int().nonnegative(),
    below_pct: PercentageNumber.nullable(),
    on_ma10_count: z.number().int().nonnegative(),
    cross_up_count: z.number().int().nonnegative(),
    cross_down_count: z.number().int().nonnegative(),
  })
  .strict()
  .refine(
    (m) => m.eligible_count === m.above_count + m.below_count + m.on_ma10_count,
    {
      message: 'Breadth metric sum invariant violated: eligible_count must equal above_count + below_count + on_ma10_count',
      path: ['eligible_count'],
    }
  )
  .refine(
    (m) => m.cross_up_count <= m.eligible_count,
    {
      message: 'Breadth metric invariant violated: cross_up_count cannot exceed eligible_count',
      path: ['cross_up_count'],
    }
  )
  .refine(
    (m) => m.cross_down_count <= m.eligible_count,
    {
      message: 'Breadth metric invariant violated: cross_down_count cannot exceed eligible_count',
      path: ['cross_down_count'],
    }
  )
  .refine(
    (m) => {
      if (m.eligible_count === 0) {
        return m.above_pct === null && m.below_pct === null;
      }
      const expectedAbove = roundTo1Decimal((m.above_count / m.eligible_count) * 100);
      const expectedBelow = roundTo1Decimal((m.below_count / m.eligible_count) * 100);
      return m.above_pct === expectedAbove && m.below_pct === expectedBelow;
    },
    {
      message: 'Breadth percentage math mismatch with symbol counts',
      path: ['above_pct'],
    }
  );

export const BreadthHistoryPointSchema = z
  .object({
    trading_date: GregorianDateSchema,
    eligible_count: z.number().int().nonnegative(),
    above_count: z.number().int().nonnegative(),
    above_pct: PercentageNumber.nullable(),
  })
  .strict()
  .refine(
    (h) => {
      if (h.eligible_count === 0) {
        return h.above_pct === null;
      }
      if (h.above_count > h.eligible_count) return false;
      const expectedAbove = roundTo1Decimal((h.above_count / h.eligible_count) * 100);
      return h.above_pct === expectedAbove;
    },
    {
      message: 'Breadth history point percentage math mismatch with symbol counts',
      path: ['above_pct'],
    }
  );

export const OverviewSchema = z
  .object({
    schema_version: z.literal('1.0.0'),
    dataset_id: DatasetIdSchema,
    as_of_date: GregorianDateSchema,
    metrics: BreadthMetricSchema,
    breadth_history: z.array(BreadthHistoryPointSchema),
  })
  .strict();

export type Overview = z.infer<typeof OverviewSchema>;
export type BreadthMetric = z.infer<typeof BreadthMetricSchema>;
export type BreadthHistoryPoint = z.infer<typeof BreadthHistoryPointSchema>;
