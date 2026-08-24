/**
 * Formatters according to docs/03-design-system.md
 * Uses Intl.NumberFormat('vi-VN') and standard date formats.
 */

const numberFormat = new Intl.NumberFormat('vi-VN', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const integerFormat = new Intl.NumberFormat('vi-VN', {
  maximumFractionDigits: 0,
});

const percentFormat = new Intl.NumberFormat('vi-VN', {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

export function formatPrice(val: number | null | undefined): string {
  if (val === null || val === undefined || isNaN(val)) return '—';
  return numberFormat.format(val);
}

export function formatDistance(val: number | null | undefined): string {
  if (val === null || val === undefined || isNaN(val)) return '—';
  const prefix = val > 0 ? '+' : '';
  return `${prefix}${numberFormat.format(val)}%`;
}

export function formatPercent(val: number | null | undefined): string {
  if (val === null || val === undefined || isNaN(val)) return '—';
  return `${percentFormat.format(val)}%`;
}

export function formatVolume(val: number | null | undefined): string {
  if (val === null || val === undefined || isNaN(val)) return '—';
  return integerFormat.format(val);
}

export function formatVolumeCompact(val: number | null | undefined): string {
  if (val === null || val === undefined || isNaN(val)) return '—';
  if (val >= 1_000_000) {
    return `${(val / 1_000_000).toLocaleString('vi-VN', { maximumFractionDigits: 2 })} Tr`;
  }
  if (val >= 1_000) {
    return `${(val / 1_000).toLocaleString('vi-VN', { maximumFractionDigits: 1 })} K`;
  }
  return integerFormat.format(val);
}

export function formatDateVi(dateStr: string | null | undefined): string {
  if (!dateStr) return '—';
  // dateStr format: YYYY-MM-DD
  const parts = dateStr.split('-');
  if (parts.length === 3) {
    return `${parts[2]}/${parts[1]}/${parts[0]}`;
  }
  return dateStr;
}

export function formatDateTimeVi(isoStr: string | null | undefined): string {
  if (!isoStr) return '—';
  try {
    const dt = new Date(isoStr);
    return dt.toLocaleString('vi-VN', {
      timeZone: 'Asia/Ho_Chi_Minh',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return isoStr;
  }
}
