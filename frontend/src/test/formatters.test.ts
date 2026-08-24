import { describe, it, expect } from 'vitest';
import {
  formatDateVi,
  formatDistance,
  formatPercent,
  formatPrice,
  formatVolume,
  formatVolumeCompact,
} from '../lib/formatters';

describe('formatters', () => {
  it('formats prices with 2 decimals in Vietnamese locale', () => {
    expect(formatPrice(102.5)).toMatch(/102[,.]50/);
    expect(formatPrice(null)).toBe('—');
    expect(formatPrice(undefined)).toBe('—');
    expect(formatPrice(NaN)).toBe('—');
  });

  it('formats distance percentage with positive sign prefix', () => {
    expect(formatDistance(2.45)).toMatch(/\+2[,.]45%/);
    expect(formatDistance(-1.3)).toMatch(/-1[,.]30%/);
    expect(formatDistance(0)).toMatch(/0[,.]00%/);
    expect(formatDistance(null)).toBe('—');
  });

  it('formats breadth percentage with 1 decimal', () => {
    expect(formatPercent(59.1)).toMatch(/59[,.]1%/);
    expect(formatPercent(null)).toBe('—');
  });

  it('formats volumes and compact representations', () => {
    expect(formatVolume(2300000)).toMatch(/2[.,]300[.,]000/);
    expect(formatVolumeCompact(2300000)).toMatch(/2[,.]3\s*Tr/);
    expect(formatVolumeCompact(50000)).toMatch(/50\s*K/);
    expect(formatVolumeCompact(null)).toBe('—');
  });

  it('formats YYYY-MM-DD date strings into DD/MM/YYYY', () => {
    expect(formatDateVi('2026-08-21')).toBe('21/08/2026');
    expect(formatDateVi(null)).toBe('—');
  });
});
