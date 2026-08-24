import { FilterState } from '../../lib/urlFilter';
import { ScreenerItem } from '../../schemas/screenerSchema';

export function selectFilteredAndSortedItems(
  items: ScreenerItem[],
  filters: FilterState
): ScreenerItem[] {
  // 1. Filtering
  const filtered = items.filter((item) => {
    // Exchange
    if (filters.exchange !== 'ALL' && item.exchange !== filters.exchange) {
      return false;
    }

    // Signal
    if (filters.signal !== 'ALL') {
      if (item.signal !== filters.signal) {
        return false;
      }
    }

    // Universe
    if (filters.universe === 'VN30' && !item.in_vn30) {
      return false;
    }

    // Symbol query search
    if (filters.query) {
      const q = filters.query.trim().toUpperCase();
      if (!item.symbol.toUpperCase().includes(q)) {
        return false;
      }
    }

    // Distance Min
    if (filters.distanceMin !== '') {
      const minVal = parseFloat(filters.distanceMin);
      if (!isNaN(minVal)) {
        if (item.distance_pct === null || item.distance_pct === undefined || item.distance_pct < minVal) {
          return false;
        }
      }
    }

    // Distance Max
    if (filters.distanceMax !== '') {
      const maxVal = parseFloat(filters.distanceMax);
      if (!isNaN(maxVal)) {
        if (item.distance_pct === null || item.distance_pct === undefined || item.distance_pct > maxVal) {
          return false;
        }
      }
    }

    // Min Avg Volume 20D
    if (filters.minAvgVolume20d !== '') {
      const minVol = parseFloat(filters.minAvgVolume20d);
      if (!isNaN(minVol)) {
        if (item.avg_volume_20d === null || item.avg_volume_20d === undefined || item.avg_volume_20d < minVol) {
          return false;
        }
      }
    }

    return true;
  });

  // 2. Sorting
  const sorted = [...filtered].sort((a, b) => {
    const field = filters.sort;
    const dir = filters.direction === 'asc' ? 1 : -1;

    let valA: any = (a as any)[field];
    let valB: any = (b as any)[field];

    // Nulls placed at the end regardless of direction
    if (valA === null || valA === undefined) return 1;
    if (valB === null || valB === undefined) return -1;

    if (typeof valA === 'number' && typeof valB === 'number') {
      return (valA - valB) * dir;
    }

    const strA = String(valA);
    const strB = String(valB);
    return strA.localeCompare(strB) * dir;
  });

  return sorted;
}
