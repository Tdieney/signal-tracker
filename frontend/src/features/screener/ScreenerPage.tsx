import React, { useEffect, useState } from 'react';
import { Filter, RotateCcw, Search } from 'lucide-react';
import { DataTable } from '../../components/DataTable';
import { FilterDrawer } from '../../components/FilterDrawer';
import { Skeleton } from '../../components/Skeleton';
import { StatusBanner } from '../../components/StatusBanner';
import { StockCardList } from '../../components/StockCardList';
import { getScreener } from '../../lib/api';
import { DEFAULT_FILTERS, EXCHANGES, SIGNALS, SIGNAL_LABELS, UNIVERSES } from '../../lib/constants';
import { FilterState, parseFilterFromQuery, serializeFilterToQuery } from '../../lib/urlFilter';
import { Manifest } from '../../schemas/manifestSchema';
import { ScreenerItem } from '../../schemas/screenerSchema';
import { selectFilteredAndSortedItems } from './screenerSelector';

interface ScreenerPageProps {
  manifest: Manifest | null;
  searchQueryString: string;
}

export const ScreenerPage: React.FC<ScreenerPageProps> = ({
  manifest,
  searchQueryString,
}) => {
  const [items, setItems] = useState<ScreenerItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  // Initialize filters from current URL query
  const [filters, setFilters] = useState<FilterState>(() =>
    parseFilterFromQuery(searchQueryString)
  );

  // Temporary filters state for mobile drawer
  const [tempDrawerFilters, setTempDrawerFilters] = useState<FilterState>(filters);

  // Synchronize when URL search changes externally
  useEffect(() => {
    const parsed = parseFilterFromQuery(searchQueryString);
    setFilters(parsed);
    setTempDrawerFilters(parsed);
  }, [searchQueryString]);

  // Update URL hash when filters change
  const updateFilters = (newFilters: FilterState) => {
    setFilters(newFilters);
    const queryString = serializeFilterToQuery(newFilters);
    window.location.hash = queryString ? `#/screener?${queryString}` : '#/screener';
  };

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getScreener(manifest?.dataset_id);
      setItems(data.items);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Không thể tải dữ liệu bộ lọc.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [manifest?.dataset_id]);

  // Compute filtered & sorted items via shared selector
  const filteredAndSortedItems = selectFilteredAndSortedItems(items, filters);

  const handleSortChange = (field: string) => {
    let nextDir: 'asc' | 'desc' = 'desc';
    if (filters.sort === field) {
      nextDir = filters.direction === 'asc' ? 'desc' : 'asc';
    } else if (field === 'symbol' || field === 'exchange' || field === 'signal') {
      nextDir = 'asc';
    }
    updateFilters({ ...filters, sort: field, direction: nextDir });
  };

  const resetFilters = () => {
    updateFilters({ ...DEFAULT_FILTERS });
  };

  return (
    <div>
      {/* Header & Title */}
      <div style={{ marginBottom: 'var(--space-5)' }}>
        <h1>Bộ lọc cổ phiếu MA10</h1>
        <p className="text-body" style={{ color: 'var(--color-text-muted)', marginTop: 'var(--space-1)' }}>
          Lọc và sắp xếp danh sách cổ phiếu theo sàn, rổ chỉ số, tín hiệu MA10 và thanh khoản trung bình.
        </p>
      </div>

      {error && (
        <StatusBanner
          variant="error"
          title="Lỗi tải dữ liệu Bộ lọc"
          message={error}
          onRetry={fetchData}
        />
      )}

      {/* Desktop Filter Toolbar (visible on >= 768px) */}
      <div
        className="card filter-toolbar-desktop"
        style={{
          marginBottom: 'var(--space-4)',
          padding: 'var(--space-4)',
          display: 'flex',
          flexWrap: 'wrap',
          gap: 'var(--space-3)',
          alignItems: 'center',
        }}
      >
        {/* Search Query */}
        <div style={{ position: 'relative', flex: '1 1 180px', minWidth: '160px' }}>
          <Search
            size={16}
            aria-hidden="true"
            style={{
              position: 'absolute',
              left: '10px',
              top: '50%',
              transform: 'translateY(-50%)',
              color: 'var(--color-text-muted)',
            }}
          />
          <input
            type="text"
            placeholder="Tìm mã cổ phiếu..."
            value={filters.query}
            onChange={(e) => updateFilters({ ...filters, query: e.target.value })}
            style={{
              width: '100%',
              padding: 'var(--space-2) var(--space-3) var(--space-2) 32px',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--color-border)',
              fontSize: '0.875rem',
            }}
            aria-label="Tìm kiếm mã cổ phiếu"
          />
        </div>

        {/* Exchange Filter */}
        <div style={{ minWidth: '130px' }}>
          <label htmlFor="filter-exchange" className="sr-only" style={{ display: 'none' }}>
            Sàn
          </label>
          <select
            id="filter-exchange"
            value={filters.exchange}
            onChange={(e) => updateFilters({ ...filters, exchange: e.target.value })}
            style={{
              width: '100%',
              padding: 'var(--space-2) var(--space-3)',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--color-border)',
              backgroundColor: 'var(--color-surface)',
              fontSize: '0.875rem',
            }}
            aria-label="Lọc theo sàn giao dịch"
          >
            {EXCHANGES.map((ex) => (
              <option key={ex} value={ex}>
                {ex === 'ALL' ? 'Tất cả sàn' : ex}
              </option>
            ))}
          </select>
        </div>

        {/* Universe Filter */}
        <div style={{ minWidth: '130px' }}>
          <label htmlFor="filter-universe" className="sr-only" style={{ display: 'none' }}>
            Rổ cổ phiếu
          </label>
          <select
            id="filter-universe"
            value={filters.universe}
            onChange={(e) => updateFilters({ ...filters, universe: e.target.value })}
            style={{
              width: '100%',
              padding: 'var(--space-2) var(--space-3)',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--color-border)',
              backgroundColor: 'var(--color-surface)',
              fontSize: '0.875rem',
            }}
            aria-label="Lọc theo rổ cổ phiếu"
          >
            {UNIVERSES.map((u) => (
              <option key={u} value={u}>
                {u === 'ALL' ? 'Toàn thị trường' : 'VN30'}
              </option>
            ))}
          </select>
        </div>

        {/* Signal Filter */}
        <div style={{ minWidth: '180px' }}>
          <label htmlFor="filter-signal" className="sr-only" style={{ display: 'none' }}>
            Tín hiệu MA10
          </label>
          <select
            id="filter-signal"
            value={filters.signal}
            onChange={(e) => updateFilters({ ...filters, signal: e.target.value })}
            style={{
              width: '100%',
              padding: 'var(--space-2) var(--space-3)',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--color-border)',
              backgroundColor: 'var(--color-surface)',
              fontSize: '0.875rem',
            }}
            aria-label="Lọc theo tín hiệu MA10"
          >
            {SIGNALS.map((sig) => (
              <option key={sig} value={sig}>
                {sig === 'ALL' ? 'Tất cả tín hiệu' : SIGNAL_LABELS[sig] || sig}
              </option>
            ))}
          </select>
        </div>

        {/* Reset Filter Button */}
        <button
          type="button"
          onClick={resetFilters}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 'var(--space-1)',
            padding: 'var(--space-2) var(--space-3)',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--color-border)',
            backgroundColor: 'var(--color-surface)',
            fontSize: '0.875rem',
            fontWeight: 500,
            color: 'var(--color-text)',
            cursor: 'pointer',
          }}
          aria-label="Đặt lại toàn bộ bộ lọc"
        >
          <RotateCcw size={14} aria-hidden="true" />
          <span>Đặt lại</span>
        </button>
      </div>

      {/* Mobile Filter Summary Bar (visible on < 768px) */}
      <div
        className="filter-summary-mobile"
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 'var(--space-3)',
          gap: 'var(--space-2)',
        }}
      >
        <span className="text-small" style={{ fontWeight: 600 }}>
          {filteredAndSortedItems.length} kết quả
        </span>

        <button
          type="button"
          onClick={() => {
            setTempDrawerFilters(filters);
            setIsDrawerOpen(true);
          }}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 'var(--space-1)',
            padding: 'var(--space-2) var(--space-3)',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--color-border)',
            backgroundColor: 'var(--color-surface)',
            fontSize: '0.875rem',
            fontWeight: 600,
            color: 'var(--color-primary-strong)',
            cursor: 'pointer',
          }}
        >
          <Filter size={16} aria-hidden="true" />
          <span>Bộ lọc & Sắp xếp</span>
        </button>
      </div>

      {/* Results Header Info */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-3)' }}>
        <span className="text-small" style={{ color: 'var(--color-text-muted)' }}>
          Hiển thị <strong>{filteredAndSortedItems.length}</strong> / {items.length} mã cổ phiếu
        </span>
      </div>

      {/* Loading state */}
      {loading && (
        <div className="card" style={{ padding: 'var(--space-5)' }}>
          {[...Array(6)].map((_, i) => (
            <Skeleton key={i} height="2.5rem" style={{ marginBottom: 'var(--space-2)' }} />
          ))}
        </div>
      )}

      {/* Empty State: No Match */}
      {!loading && filteredAndSortedItems.length === 0 && (
        <div
          className="card"
          style={{
            padding: 'var(--space-7) var(--space-4)',
            textAlign: 'center',
            backgroundColor: 'var(--color-surface)',
          }}
        >
          <h3 className="text-h3" style={{ marginBottom: 'var(--space-2)' }}>
            Không tìm thấy mã nào phù hợp
          </h3>
          <p className="text-small" style={{ color: 'var(--color-text-muted)', marginBottom: 'var(--space-4)' }}>
            Hãy thử điều chỉnh hoặc xóa bớt các điều kiện lọc để hiển thị nhiều kết quả hơn.
          </p>
          <button
            type="button"
            onClick={resetFilters}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 'var(--space-2)',
              padding: 'var(--space-2) var(--space-4)',
              borderRadius: 'var(--radius-md)',
              border: 'none',
              backgroundColor: 'var(--color-primary)',
              color: '#ffffff',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            <RotateCcw size={16} aria-hidden="true" />
            <span>Xóa bộ lọc</span>
          </button>
        </div>
      )}

      {/* Content Rendering: Responsive Table (Desktop) vs Card List (Mobile) */}
      {!loading && filteredAndSortedItems.length > 0 && (
        <>
          {/* Desktop Table View */}
          <div className="screener-table-view">
            <DataTable
              items={filteredAndSortedItems}
              sortField={filters.sort}
              sortDirection={filters.direction}
              onSortChange={handleSortChange}
            />
          </div>

          {/* Mobile Card List View */}
          <div className="screener-cards-view">
            <StockCardList items={filteredAndSortedItems} />
          </div>
        </>
      )}

      {/* Mobile Filter Drawer */}
      <FilterDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        tempFilters={tempDrawerFilters}
        onFilterChange={(key, val) =>
          setTempDrawerFilters((prev) => ({ ...prev, [key]: val }))
        }
        onApply={() => {
          updateFilters(tempDrawerFilters);
          setIsDrawerOpen(false);
        }}
        onReset={() => {
          setTempDrawerFilters({ ...DEFAULT_FILTERS });
          updateFilters({ ...DEFAULT_FILTERS });
          setIsDrawerOpen(false);
        }}
      />
    </div>
  );
};
