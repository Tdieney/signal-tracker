import { z } from 'zod';
import { Manifest, ManifestSchema } from '../schemas/manifestSchema';
import { Overview, OverviewSchema } from '../schemas/overviewSchema';
import { Screener, ScreenerSchema } from '../schemas/screenerSchema';
import { SymbolDetail, SymbolDetailSchema } from '../schemas/symbolSchema';
import { SUPPORTED_SCHEMA_VERSION } from './constants';

export class ApiError extends Error {
  constructor(message: string, public statusCode?: number, public isFatal = false) {
    super(message);
    this.name = 'ApiError';
  }
}

// Memory cache for fetched JSON
const cache = new Map<string, unknown>();

export function clearApiCache(): void {
  cache.clear();
}

function getBaseDataUrl(): string {
  const base = import.meta.env.BASE_URL || './';
  const cleanBase = base.endsWith('/') ? base : `${base}/`;
  return `${cleanBase}data/`;
}

export async function fetchJson<T>(
  relativePath: string,
  schema: z.ZodSchema<T>,
  signal?: AbortSignal,
  timeoutMs = 15000
): Promise<T> {
  const url = `${getBaseDataUrl()}${relativePath}`;

  if (cache.has(url)) {
    return cache.get(url) as T;
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const combinedSignal = signal
    ? createCombinedSignal(signal, controller.signal)
    : controller.signal;

  try {
    const response = await fetch(url, {
      signal: combinedSignal,
      headers: { 'Accept': 'application/json' },
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      throw new ApiError(
        `Không thể tải dữ liệu từ ${relativePath} (${response.status}: ${response.statusText})`,
        response.status
      );
    }

    const rawData = await response.json();
    const parseResult = schema.safeParse(rawData);

    if (!parseResult.success) {
      console.error(`Schema validation failed for ${relativePath}:`, parseResult.error.format());
      throw new ApiError(
        `Dữ liệu từ ${relativePath} không đúng định dạng chuẩn (schema validation failure).`,
        500,
        true
      );
    }

    cache.set(url, parseResult.data);
    return parseResult.data;
  } catch (err: unknown) {
    clearTimeout(timeoutId);
    if (err instanceof ApiError) throw err;
    if (err instanceof Error && err.name === 'AbortError') {
      throw new ApiError('Yêu cầu dữ liệu bị quá thời gian hoặc đã bị hủy.');
    }
    throw new ApiError(`Lỗi kết nối khi tải ${relativePath}. Vui lòng thử lại.`);
  }
}

function createCombinedSignal(s1: AbortSignal, s2: AbortSignal): AbortSignal {
  const controller = new AbortController();
  const onAbort = () => controller.abort();
  if (s1.aborted || s2.aborted) {
    controller.abort();
    return controller.signal;
  }
  s1.addEventListener('abort', onAbort, { once: true });
  s2.addEventListener('abort', onAbort, { once: true });
  return controller.signal;
}

// Typed API methods with strict dataset_id verification
export async function getManifest(signal?: AbortSignal): Promise<Manifest> {
  const manifest = await fetchJson<Manifest>('manifest.json', ManifestSchema, signal);
  const manifestMajor = manifest.schema_version.split('.')[0];
  const supportedMajor = SUPPORTED_SCHEMA_VERSION.split('.')[0];

  if (manifestMajor !== supportedMajor) {
    throw new ApiError(
      `Phiên bản dữ liệu không tương thích (yêu cầu major ${supportedMajor}.x.x, nhận được ${manifest.schema_version}).`,
      500,
      true
    );
  }
  return manifest;
}

export async function getOverview(manifestDatasetId: string, signal?: AbortSignal): Promise<Overview> {
  if (!manifestDatasetId) {
    throw new ApiError('Không thể tải Overview mà không có Manifest dataset_id hợp lệ.', 400, true);
  }
  const overview = await fetchJson<Overview>('overview.json', OverviewSchema, signal);
  if (overview.dataset_id !== manifestDatasetId) {
    throw new ApiError(
      `Dữ liệu Tổng quan không khớp phiên bản với Manifest (dataset_id mismatch: ${overview.dataset_id} != ${manifestDatasetId}).`,
      500,
      true
    );
  }
  return overview;
}

export async function getScreener(manifestDatasetId: string, signal?: AbortSignal): Promise<Screener> {
  if (!manifestDatasetId) {
    throw new ApiError('Không thể tải Screener mà không có Manifest dataset_id hợp lệ.', 400, true);
  }
  const screener = await fetchJson<Screener>('screener.json', ScreenerSchema, signal);
  if (screener.dataset_id !== manifestDatasetId) {
    throw new ApiError(
      `Dữ liệu Bộ lọc không khớp phiên bản với Manifest (dataset_id mismatch: ${screener.dataset_id} != ${manifestDatasetId}).`,
      500,
      true
    );
  }
  return screener;
}

export async function getSymbolDetail(
  symbol: string,
  manifestDatasetId: string,
  signal?: AbortSignal
): Promise<SymbolDetail> {
  if (!manifestDatasetId) {
    throw new ApiError(`Không thể tải Symbol ${symbol} mà không có Manifest dataset_id hợp lệ.`, 400, true);
  }
  const cleanSymbol = symbol.trim().toUpperCase();
  if (!/^[A-Z0-9]{1,10}$/.test(cleanSymbol)) {
    throw new ApiError(`Mã cổ phiếu '${symbol}' không hợp lệ.`, 400);
  }
  const detail = await fetchJson<SymbolDetail>(`symbols/${cleanSymbol}.json`, SymbolDetailSchema, signal);
  if (detail.dataset_id !== manifestDatasetId) {
    throw new ApiError(
      `Dữ liệu mã ${symbol} không khớp phiên bản với Manifest (dataset_id mismatch: ${detail.dataset_id} != ${manifestDatasetId}).`,
      500,
      true
    );
  }
  return detail;
}
