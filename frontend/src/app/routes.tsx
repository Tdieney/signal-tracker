export type RouteType =
  | { name: 'overview' }
  | { name: 'screener'; search: string }
  | { name: 'symbol'; symbol: string }
  | { name: 'not_found'; path: string };

export function parseHashRoute(hash: string): RouteType {
  const cleanHash = hash.startsWith('#') ? hash.slice(1) : hash;
  const [pathPart, queryPart] = cleanHash.split('?');
  const path = pathPart || '/';

  if (path === '/' || path === '' || path === '/main-content' || path === 'main-content') {
    return { name: 'overview' };
  }

  if (path === '/screener') {
    return { name: 'screener', search: queryPart || '' };
  }

  const symbolMatch = path.match(/^\/symbols\/([A-Z0-9]{1,10})$/i);
  if (symbolMatch) {
    return { name: 'symbol', symbol: symbolMatch[1].toUpperCase() };
  }

  return { name: 'not_found', path };
}
