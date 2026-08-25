import React, { useEffect, useMemo, useState } from 'react';
import { Filter, Search, RotateCcw, ChevronLeft, ChevronRight } from 'lucide-react';
import { DataTable } from '../../components/DataTable';
import { FilterDrawer } from '../../components/FilterDrawer';
import { FreshnessBadge } from '../../components/FreshnessBadge';
import { Skeleton } from '../../components/Skeleton';
import { StatusBanner } from '../../components/StatusBanner';
import { StockCardList } from '../../components/StockCardList';
import { getScreener } from '../../lib/api';
import {
  DEFAULT_FILTERS,
  EXCHANGES,
  SIGNALS,
  UNIVERSES,
  SIGNAL_LABELS,
} from '../../lib/constants';
import {
  FilterState,
  parseFilterFromQuery,
  serializeFilterToQuery,
} from '../../lib/urlFilter';
import { Manifest } from '../../schemas/manifestSchema';
import { ScreenerItem } from '../../schemas/screenerSchema';
import { selectFilteredAndSortedItems } from './screenerSelector';

interface ScreenerPageProps {
  initialSearch?: string;
  manifest: Manifest;
}

export const ScreenerPage: React.FC<ScreenerPageProps> = ({
  initialSearch = '',
  manifest,
}) => {
  const [items, setItems] = useState<ScreenerItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Initialize filters from URL query
  const [filters, setFilters] = useState<FilterState>(() =>
    parseFilterFromQuery(initialSearch)
  );

  // Mobile Filter Drawer state
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [tempDrawerFilters, setTempDrawerFilters] = useState<FilterState>(filters);

  // Sync state when URL query prop changes
  useEffect(() => {
    setFilters(parseFilterFromQuery(initialSearch));
  }, [initialSearch]);

  // Fetch screener data with AbortController and dataset_id check
  const fetchData = async (signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    try {
      const data = await getScreener(manifest.dataset_id, signal);
      setItems(data.items);
    } catch (err: any) {
      if (err?.name === 'AbortError' || signal?.aborted) return;
      setError(err?.message || 'Không thể tải danh sách cổ phiếu.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const controller = new AbortController();
    fetchData(controller.signal);
    return () => controller.abort();
  }, [manifest.dataset_id]);

  // Update URL query when filters change
  const updateFilters = (newFilters: FilterState) => {
    setFilters(newFilters);
    const query = serializeFilterToQuery(newFilters);
    window.location.hash = query ? `#/screener?${query}` : '#/screener';
  };

  // Sort handler for data table
  const handleSortChange = (field: string) => {
    let nextDir: 'asc' | 'desc' = 'desc';
    if (filters.sort === field) {
      nextDir = filters.direction === 'asc' ? 'desc' : 'asc';
    } else if (field === 'symbol' || field === 'exchange' || field === 'signal') {
      nextDir = 'asc';
    }
    updateFilters({ ...filters, sort: field, direction: nextDir, page: 1 });
  };

  // Pure filtered and sorted items (Parity across desktop and mobile)
  const filteredItems = useMemo(() => {
    return selectFilteredAndSortedItems(items, filters);
  }, [items, filters]);

  // Pagination calculation
  const totalCount = filteredItems.length;
  const totalPages = Math.max(1, Math.ceil(totalCount / filters.pageSize));
  const currentPage = Math.min(filters.page, totalPages);

  const paginatedItems = useMemo(() => {
    const startIdx = (currentPage - 1) * filters.pageSize;
    return filteredItems.slice(startIdx, startIdx + filters.pageSize);
  }, [filteredItems, currentPage, filters.pageSize]);

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      updateFilters({ ...filters, page: newPage });
    }
  };

  const handleResetFilters = () => {
    updateFilters({ ...DEFAULT_FILTERS });
  };

  if (loading) {
    return (
      <div>
        <div className="mb-5">
          <Skeleton className="sk-title mb-2" />
          <Skeleton className="sk-row" />
        </div>
        <div className="card mb-4 p-4">
          <Skeleton className="sk-row" />
        </div>
        <div className="card p-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Skeleton key={i} className="sk-row" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <StatusBanner
        variant="error"
        title="Lỗi tải bộ lọc"
        message={error}
        onRetry={() => fetchData()}
      />
    );
  }

  return (
    <div>
      {/* Page Header with Freshness Badge */}
      <div className="mb-5">
        <div className="flex flex-wrap justify-between items-center gap-3 mb-2">
          <h1 className="text-h1">Bộ lọc cổ phiếu</h1>
          <FreshnessBadge
            status={manifest.freshness.status}
            asOfDate={manifest.as_of_date}
            reason={manifest.freshness.reason}
            marketSessionStatus={manifest.market_session_status}
            provider={manifest.provider}
          />
        </div>
        <p className="text-small text-muted">
          Lọc và sắp xếp toàn bộ cổ phiếu theo sàn, tín hiệu MA10, rổ chỉ số, khoảng cách tới MA10 và thanh khoản.
        </p>
      </div>

      {/* Desktop Filter Toolbar */}
      <div className="card filter-toolbar-desktop">
        {/* Search by Symbol */}
        <div className="filter-search-box">
          <Search size={16} className="filter-search-icon" aria-hidden="true" />
          <input
            type="search"
            placeholder="Tìm theo mã..."
            value={filters.query}
            onChange={(e) =>
              updateFilters({ ...filters, query: e.target.value.toUpperCase(), page: 1 })
            }
            aria-label="Tìm kiếm theo mã cổ phiếu"
            className="filter-search-input"
          />
        </div>

        {/* Exchange Filter */}
        <div className="filter-select-group">
          <select
            value={filters.exchange}
            onChange={(e) =>
              updateFilters({ ...filters, exchange: e.target.value, page: 1 })
            }
            aria-label="Lọc theo sàn giao dịch"
            className="filter-select"
          >
            {EXCHANGES.map((ex) => (
              <option key={ex} value={ex}>
                {ex === 'ALL' ? 'Tất cả sàn' : ex}
              </option>
            ))}
          </select>
        </div>

        {/* Universe Filter */}
        <div className="filter-select-group">
          <select
            value={filters.universe}
            onChange={(e) =>
              updateFilters({ ...filters, universe: e.target.value, page: 1 })
            }
            aria-label="Lọc theo rổ chỉ số"
            className="filter-select"
          >
            {UNIVERSES.map((u) => (
              <option key={u} value={u}>
                {u === 'ALL' ? 'Toàn thị trường' : 'Chỉ rổ VN30'}
              </option>
            ))}
          </select>
        </div>

        {/* Signal Filter */}
        <div className="filter-select-signal">
          <select
            value={filters.signal}
            onChange={(e) =>
              updateFilters({ ...filters, signal: e.target.value, page: 1 })
            }
            aria-label="Lọc theo tín hiệu kỹ thuật"
            className="filter-select"
          >
            {SIGNALS.map((s) => (
              <option key={s} value={s}>
                {SIGNAL_LABELS[s] || s}
              </option>
            ))}
          </select>
        </div>

        {/* Min Avg Volume 20D */}
        <div className="filter-select-group">
          <input
            type="number"
            min="0"
            step="100000"
            placeholder="Min Vol 20D"
            value={filters.minAvgVolume20d}
            onChange={(e) =>
              updateFilters({ ...filters, minAvgVolume20d: e.target.value, page: 1 })
            }
            aria-label="Khối lượng trung bình 20 phiên tối thiểu"
            className="filter-search-input"
          />
        </div>

        {/* Reset Filters Button */}
        <button
          type="button"
          onClick={handleResetFilters}
          className="btn-secondary"
          title="Đặt lại toàn bộ bộ lọc về mặc định"
        >
          <RotateCcw size={14} aria-hidden="true" />
          <span>Đặt lại</span>
        </button>
      </div>

      {/* Mobile Filter Summary Bar */}
      <div className="filter-summary-mobile">
        <div className="filter-search-box">
          <Search size={16} className="filter-search-icon" aria-hidden="true" />
          <input
            type="search"
            placeholder="Tìm mã..."
            value={filters.query}
            onChange={(e) =>
              updateFilters({ ...filters, query: e.target.value.toUpperCase(), page: 1 })
            }
            aria-label="Tìm theo mã cổ phiếu"
            className="filter-search-input"
          />
        </div>

        <button
          type="button"
          id="open-filter-drawer-btn"
          onClick={() => {
            setTempDrawerFilters(filters);
            setIsDrawerOpen(true);
          }}
          className="btn-secondary flex items-center gap-1"
          aria-haspopup="dialog"
          aria-expanded={isDrawerOpen}
        >
          <Filter size={16} aria-hidden="true" />
          <span>Bộ lọc</span>
        </button>
      </div>

      {/* Result Count and Summary */}
      <div className="flex justify-between items-center mb-3">
        <span className="text-small text-muted">
          Tìm thấy <strong className="text-body font-bold">{totalCount}</strong> cổ phiếu phù hợp
        </span>
        <span className="text-small text-muted">
          Trang {currentPage} / {totalPages}
        </span>
      </div>

      {/* Results View: Desktop Table vs Mobile Cards */}
      {paginatedItems.length > 0 ? (
        <>
          {/* Desktop Table View */}
          <div className="screener-table-view">
            <DataTable
              items={paginatedItems}
              sortField={filters.sort}
              sortDirection={filters.direction}
              onSortChange={handleSortChange}
            />
          </div>

          {/* Mobile Card List View */}
          <div className="screener-cards-view">
            <StockCardList items={paginatedItems} />
          </div>

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="flex justify-center items-center gap-2 mt-5">
              <button
                type="button"
                onClick={() => handlePageChange(currentPage - 1)}
                disabled={currentPage === 1}
                className="btn-secondary"
                aria-label="Trang trước"
              >
                <ChevronLeft size={16} aria-hidden="true" />
                <span>Trước</span>
              </button>

              <span className="text-small font-semibold">
                {currentPage} / {totalPages}
              </span>

              <button
                type="button"
                onClick={() => handlePageChange(currentPage + 1)}
                disabled={currentPage === totalPages}
                className="btn-secondary"
                aria-label="Trang tiếp theo"
              >
                <span>Sau</span>
                <ChevronRight size={16} aria-hidden="true" />
              </button>
            </div>
          )}
        </>
      ) : (
        /* Empty State */
        <div className="card text-center p-6" data-testid="empty-results-card">
          <h2 className="text-h2 mb-2">Không tìm thấy cổ phiếu phù hợp</h2>
          <p className="text-small text-muted mb-4">
            Không có mã nào thỏa mãn toàn bộ tiêu chí lọc hiện tại. Hãy thử nới lỏng điều kiện hoặc đặt lại bộ lọc.
          </p>
          <button
            type="button"
            onClick={handleResetFilters}
            className="btn-primary"
          >
            <RotateCcw size={16} aria-hidden="true" />
            <span>Đặt lại bộ lọc</span>
          </button>
        </div>
      )}

      {/* Accessible Mobile Filter Drawer */}
      <FilterDrawer
        isOpen={isDrawerOpen}
        onClose={() => {
          setIsDrawerOpen(false);
          requestAnimationFrame(() => {
            document.getElementById('open-filter-drawer-btn')?.focus();
          });
        }}
        tempFilters={tempDrawerFilters}
        onFilterChange={(key, val) =>
          setTempDrawerFilters((prev) => ({ ...prev, [key]: val }))
        }
        onApply={() => {
          updateFilters(tempDrawerFilters);
          setIsDrawerOpen(false);
          requestAnimationFrame(() => {
            document.getElementById('open-filter-drawer-btn')?.focus();
          });
        }}
        onReset={() => {
          setTempDrawerFilters({ ...DEFAULT_FILTERS });
          updateFilters({ ...DEFAULT_FILTERS });
          setIsDrawerOpen(false);
          requestAnimationFrame(() => {
            document.getElementById('open-filter-drawer-btn')?.focus();
          });
        }}
      />
    </div>
  );
};
