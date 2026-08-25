import { z } from 'zod';

export const FreshnessStatusSchema = z.enum(['FRESH', 'STALE', 'UNKNOWN']);
export const QualityStatusSchema = z.enum(['PASS', 'PARTIAL', 'FAIL']);
export const MarketSessionStatusSchema = z.enum(['CLOSED_CONFIRMED', 'UNKNOWN']);
export const ProviderSchema = z.enum(['csv', 'vnstock', 'company_api']);
export const UniverseSchema = z.enum(['ALL', 'VN30', 'ALL_PLUS_VN30']);

export const ManifestSchema = z.object({
  schema_version: z.string().regex(/^1\.\d+\.\d+$/, 'Chỉ hỗ trợ schema phiên bản 1.x.x'),
  dataset_id: z.string().min(1, 'dataset_id không được để trống'),
  as_of_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'as_of_date phải có định dạng YYYY-MM-DD'),
  generated_at: z.string().min(1),
  market_timezone: z.literal('Asia/Ho_Chi_Minh'),
  market_session_status: MarketSessionStatusSchema,
  freshness: z.object({
    status: FreshnessStatusSchema,
    expected_as_of_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
    reason: z.string().min(1),
  }),
  provider: ProviderSchema,
  universe: UniverseSchema,
  files: z.object({
    overview: z.literal('overview.json'),
    screener: z.literal('screener.json'),
    symbols_base: z.literal('symbols/'),
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
