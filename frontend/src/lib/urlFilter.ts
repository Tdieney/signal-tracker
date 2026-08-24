import { DEFAULT_FILTERS, EXCHANGES, SIGNALS, UNIVERSES } from './constants';

export interface FilterState {
  exchange: string;
  signal: string;
  universe: string;
  query: string;
  distanceMin: string;
  distanceMax: string;
  minAvgVolume20d: string;
  sort: string;
  direction: 'asc' | 'desc';
  page: number;
  pageSize: number;
}

const ALLOWED_SORT_FIELDS = new Set([
  'symbol',
  'exchange',
  'close',
  'ma10',
  'distance_pct',
  'volume',
  'avg_volume_20d',
  'signal',
  'data_status',
]);

export function parseFilterFromQuery(queryString: string): FilterState {
  const params = new URLSearchParams(queryString);
  const state: FilterState = {
    ...DEFAULT_FILTERS,
    direction: DEFAULT_FILTERS.direction,
  };

  // Exchange allow-list
  const rawExchange = (params.get('exchange') || '').toUpperCase();
  if (EXCHANGES.includes(rawExchange as any)) {
    state.exchange = rawExchange;
  }

  // Signal allow-list
  const rawSignal = params.get('signal') || '';
  if (SIGNALS.includes(rawSignal as any)) {
    state.signal = rawSignal;
  }

  // Universe allow-list
  const rawUniverse = (params.get('universe') || '').toUpperCase();
  if (UNIVERSES.includes(rawUniverse as any)) {
    state.universe = rawUniverse;
  }

  // Query search
  const rawQuery = params.get('query') || '';
  state.query = rawQuery.trim().slice(0, 10);

  // Numeric bounds
  const rawDistMin = params.get('distanceMin');
  if (rawDistMin !== null && !isNaN(Number(rawDistMin))) {
    state.distanceMin = rawDistMin;
  }

  const rawDistMax = params.get('distanceMax');
  if (rawDistMax !== null && !isNaN(Number(rawDistMax))) {
    state.distanceMax = rawDistMax;
  }

  const rawMinVol = params.get('minAvgVolume20d');
  if (rawMinVol !== null && !isNaN(Number(rawMinVol)) && Number(rawMinVol) >= 0) {
    state.minAvgVolume20d = rawMinVol;
  }

  // Sort
  const rawSort = params.get('sort') || '';
  if (ALLOWED_SORT_FIELDS.has(rawSort)) {
    state.sort = rawSort;
  }

  const rawDir = (params.get('direction') || '').toLowerCase();
  if (rawDir === 'asc' || rawDir === 'desc') {
    state.direction = rawDir;
  }

  // Page
  const rawPage = parseInt(params.get('page') || '1', 10);
  if (!isNaN(rawPage) && rawPage >= 1) {
    state.page = rawPage;
  }

  return state;
}

export function serializeFilterToQuery(state: FilterState): string {
  const params = new URLSearchParams();

  if (state.exchange && state.exchange !== 'ALL') {
    params.set('exchange', state.exchange);
  }
  if (state.signal && state.signal !== 'ALL') {
    params.set('signal', state.signal);
  }
  if (state.universe && state.universe !== 'ALL') {
    params.set('universe', state.universe);
  }
  if (state.query) {
    params.set('query', state.query);
  }
  if (state.distanceMin !== '') {
    params.set('distanceMin', state.distanceMin);
  }
  if (state.distanceMax !== '') {
    params.set('distanceMax', state.distanceMax);
  }
  if (state.minAvgVolume20d !== '') {
    params.set('minAvgVolume20d', state.minAvgVolume20d);
  }
  if (state.sort && state.sort !== DEFAULT_FILTERS.sort) {
    params.set('sort', state.sort);
  }
  if (state.direction && state.direction !== DEFAULT_FILTERS.direction) {
    params.set('direction', state.direction);
  }
  if (state.page > 1) {
    params.set('page', state.page.toString());
  }

  return params.toString();
}
