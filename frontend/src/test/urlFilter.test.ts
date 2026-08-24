import { describe, it, expect } from 'vitest';
import { parseFilterFromQuery, serializeFilterToQuery } from '../lib/urlFilter';

describe('urlFilter', () => {
  it('parses valid query parameters', () => {
    const query = 'exchange=HOSE&signal=CROSS_UP_MA10&universe=VN30&distanceMin=1.5&minAvgVolume20d=500000&sort=close&direction=asc&page=2';
    const state = parseFilterFromQuery(query);

    expect(state.exchange).toBe('HOSE');
    expect(state.signal).toBe('CROSS_UP_MA10');
    expect(state.universe).toBe('VN30');
    expect(state.distanceMin).toBe('1.5');
    expect(state.minAvgVolume20d).toBe('500000');
    expect(state.sort).toBe('close');
    expect(state.direction).toBe('asc');
    expect(state.page).toBe(2);
  });

  it('normalizes invalid/malicious query parameters safely without crashing', () => {
    const malicious = 'exchange=<script>&signal=HACKED&universe=DROP_TABLE&sort=evil_field&page=-5&minAvgVolume20d=invalid';
    const state = parseFilterFromQuery(malicious);

    expect(state.exchange).toBe('ALL');
    expect(state.signal).toBe('ALL');
    expect(state.universe).toBe('ALL');
    expect(state.sort).toBe('distance_pct');
    expect(state.page).toBe(1);
    expect(state.minAvgVolume20d).toBe('');
  });

  it('serializes state to query string omitting default values', () => {
    const state = {
      exchange: 'HOSE',
      signal: 'CROSS_UP_MA10',
      universe: 'ALL',
      query: 'FPT',
      distanceMin: '2',
      distanceMax: '',
      minAvgVolume20d: '',
      sort: 'distance_pct', // default sort
      direction: 'desc' as const, // default direction
      page: 1, // default page
      pageSize: 20,
    };

    const query = serializeFilterToQuery(state);
    expect(query).toContain('exchange=HOSE');
    expect(query).toContain('signal=CROSS_UP_MA10');
    expect(query).toContain('query=FPT');
    expect(query).toContain('distanceMin=2');
    expect(query).not.toContain('universe');
    expect(query).not.toContain('sort');
    expect(query).not.toContain('page');
  });
});
