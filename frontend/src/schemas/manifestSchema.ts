import { z } from 'zod';
import {
  DatasetIdSchema,
  GregorianDateSchema,
  IsoTimestampSchema,
} from './validationUtils';

export const FreshnessStatusSchema = z.enum(['FRESH', 'STALE', 'UNKNOWN']);
export const QualityStatusSchema = z.enum(['PASS', 'PARTIAL', 'FAIL']);
export const MarketSessionStatusSchema = z.enum(['CLOSED_CONFIRMED', 'UNKNOWN']);
export const ProviderSchema = z.enum(['csv', 'vnstock', 'company_api']);
export const UniverseSchema = z.enum(['ALL', 'VN30']);

export const ManifestFreshnessSchema = z
  .object({
    status: FreshnessStatusSchema,
    expected_as_of_date: GregorianDateSchema,
    reason: z.string().min(1, 'Lý do độ mới không được để trống'),
  })
  .strict();

export const ManifestFilesSchema = z
  .object({
    overview: z.literal('overview.json'),
    screener: z.literal('screener.json'),
    symbols_base: z.literal('symbols/'),
  })
  .strict();

export const ManifestQualitySchema = z
  .object({
    status: QualityStatusSchema,
    input_rows: z.number().int().nonnegative(),
    accepted_rows: z.number().int().nonnegative(),
    rejected_rows: z.number().int().nonnegative(),
    eligible_symbols: z.number().int().nonnegative(),
    warnings: z.array(z.string()),
  })
  .strict()
  .refine(
    (q) => q.input_rows === q.accepted_rows + q.rejected_rows,
    {
      message: 'Quality accounting invariant violated: input_rows must equal accepted_rows + rejected_rows',
      path: ['input_rows'],
    }
  )
  .refine(
    (q) => q.eligible_symbols <= q.accepted_rows,
    {
      message: 'Quality accounting invariant violated: eligible_symbols cannot exceed accepted_rows',
      path: ['eligible_symbols'],
    }
  );

export const ManifestSchema = z
  .object({
    schema_version: z.literal('1.0.0'),
    dataset_id: DatasetIdSchema,
    as_of_date: GregorianDateSchema,
    generated_at: IsoTimestampSchema,
    market_timezone: z.literal('Asia/Ho_Chi_Minh'),
    market_session_status: MarketSessionStatusSchema,
    freshness: ManifestFreshnessSchema,
    provider: ProviderSchema,
    universe: UniverseSchema,
    files: ManifestFilesSchema,
    quality: ManifestQualitySchema,
  })
  .strict();

export type Manifest = z.infer<typeof ManifestSchema>;
export type FreshnessStatus = z.infer<typeof FreshnessStatusSchema>;
export type QualityStatus = z.infer<typeof QualityStatusSchema>;
export type MarketSessionStatus = z.infer<typeof MarketSessionStatusSchema>;
