import { z } from 'zod';

export const DATASET_ID_REGEX = /^[0-9a-f]{16}$/;
export const DATE_REGEX = /^\d{4}-\d{2}-\d{2}$/;
export const ISO_TIMESTAMP_REGEX = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/;

/**
 * Validates that a string is a real calendar Gregorian date (YYYY-MM-DD),
 * correctly handling month boundaries (28-31) and leap years.
 */
export function isValidGregorianDate(dateStr: string): boolean {
  if (!DATE_REGEX.test(dateStr)) return false;
  const parts = dateStr.split('-');
  const y = parseInt(parts[0], 10);
  const m = parseInt(parts[1], 10);
  const d = parseInt(parts[2], 10);
  if (m < 1 || m > 12 || d < 1 || d > 31 || y < 1970 || y > 2100) return false;

  const date = new Date(Date.UTC(y, m - 1, d));
  return (
    date.getUTCFullYear() === y &&
    date.getUTCMonth() === m - 1 &&
    date.getUTCDate() === d
  );
}

/**
 * Validates that a string is a strict ISO 8601 calendar timestamp.
 */
export function isValidIsoDateTime(timestampStr: string): boolean {
  if (!ISO_TIMESTAMP_REGEX.test(timestampStr)) return false;
  const date = new Date(timestampStr);
  return !isNaN(date.getTime());
}

/**
 * Standard rounding to 1 decimal place matching Python round(val, 1) and data contracts.
 */
export function roundTo1Decimal(val: number): number {
  return Math.round(val * 10) / 10;
}

export const DatasetIdSchema = z
  .string()
  .regex(DATASET_ID_REGEX, 'dataset_id phải đúng 16 ký tự hexadecimal (0-9, a-f)');

export const GregorianDateSchema = z
  .string()
  .regex(DATE_REGEX, 'Ngày phải có định dạng YYYY-MM-DD')
  .refine(isValidGregorianDate, 'Ngày lịch Gregorian không hợp lệ');

export const IsoTimestampSchema = z
  .string()
  .regex(ISO_TIMESTAMP_REGEX, 'Thời gian phải theo định dạng ISO 8601')
  .refine(isValidIsoDateTime, 'Thời gian ISO 8601 không hợp lệ');

export const PositiveFiniteNumber = z.number().finite().positive();
export const NonNegativeFiniteNumber = z.number().finite().nonnegative();
export const PercentageNumber = z.number().finite().min(0).max(100);
