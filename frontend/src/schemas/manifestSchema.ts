import { z } from 'zod';

export const FreshnessStatusSchema = z.enum(['FRESH', 'STALE', 'UNKNOWN']);
export const QualityStatusSchema = z.enum(['PASS', 'PARTIAL', 'FAIL']);

export const ManifestSchema = z.object({
  schema_version: z.string(),
  dataset_id: z.string(),
  as_of_date: z.string(),
  generated_at: z.string(),
  market_timezone: z.string(),
  market_session_status: z.string(),
  freshness: z.object({
    status: FreshnessStatusSchema,
    expected_as_of_date: z.string(),
    reason: z.string(),
  }),
  provider: z.string(),
  universe: z.string(),
  files: z.object({
    overview: z.string(),
    screener: z.string(),
    symbols_base: z.string(),
  }),
  quality: z.object({
    status: QualityStatusSchema,
    input_rows: z.number().int().nonnegative(),
    accepted_rows: z.number().int().nonnegative(),
    rejected_rows: z.number().int().nonnegative(),
    eligible_symbols: z.number().int().nonnegative(),
    warnings: z.array(z.string()),
  }),
});

export type Manifest = z.infer<typeof ManifestSchema>;
