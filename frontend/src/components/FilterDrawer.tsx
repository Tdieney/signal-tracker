import React, { useEffect, useRef } from 'react';
import { X, RotateCcw, Check } from 'lucide-react';
import { EXCHANGES, SIGNALS, SIGNAL_LABELS, UNIVERSES } from '../lib/constants';
import { FilterState } from '../lib/urlFilter';

interface FilterDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  tempFilters: FilterState;
  onFilterChange: (key: keyof FilterState, value: any) => void;
  onApply: () => void;
  onReset: () => void;
}

export const FilterDrawer: React.FC<FilterDrawerProps> = ({
  isOpen,
  onClose,
  tempFilters,
  onFilterChange,
  onApply,
  onReset,
}) => {
  const dialogRef = useRef<HTMLDivElement>(null);
  const firstInputRef = useRef<HTMLSelectElement>(null);

  // Focus management and Escape key handling
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    // Focus first input on open
    setTimeout(() => {
      firstInputRef.current?.focus();
    }, 50);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="drawer-title"
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
        zIndex: 200,
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'flex-end',
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={dialogRef}
        className="card"
        style={{
          width: '100%',
          maxWidth: '500px',
          maxHeight: '90vh',
          backgroundColor: 'var(--color-surface)',
          borderTopLeftRadius: 'var(--radius-lg)',
          borderTopRightRadius: 'var(--radius-lg)',
          borderBottomLeftRadius: 0,
          borderBottomRightRadius: 0,
          padding: 'var(--space-5)',
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: 'var(--shadow-modal)',
        }}
      >
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-4)' }}>
          <h2 id="drawer-title" className="text-h2">Bộ lọc cổ phiếu</h2>
          <button
            type="button"
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: 'var(--color-text-muted)',
              padding: 'var(--space-1)',
              borderRadius: 'var(--radius-sm)',
            }}
            aria-label="Đóng bảng lọc"
          >
            <X size={20} aria-hidden="true" />
          </button>
        </div>

        {/* Filter Form Controls */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)', flex: 1 }}>
          {/* Exchange */}
          <div>
            <label htmlFor="drawer-exchange" style={{ display: 'block', fontWeight: 600, fontSize: '0.875rem', marginBottom: 'var(--space-1)' }}>
              Sàn giao dịch
            </label>
            <select
              id="drawer-exchange"
              ref={firstInputRef}
              value={tempFilters.exchange}
              onChange={(e) => onFilterChange('exchange', e.target.value)}
              style={{
                width: '100%',
                padding: 'var(--space-2) var(--space-3)',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--color-border)',
                backgroundColor: 'var(--color-surface)',
                fontSize: '0.9375rem',
              }}
            >
              {EXCHANGES.map((ex) => (
                <option key={ex} value={ex}>
                  {ex === 'ALL' ? 'Tất cả sàn' : ex}
                </option>
              ))}
            </select>
          </div>

          {/* Universe */}
          <div>
            <label htmlFor="drawer-universe" style={{ display: 'block', fontWeight: 600, fontSize: '0.875rem', marginBottom: 'var(--space-1)' }}>
              Nhóm rổ cổ phiếu
            </label>
            <select
              id="drawer-universe"
              value={tempFilters.universe}
              onChange={(e) => onFilterChange('universe', e.target.value)}
              style={{
                width: '100%',
                padding: 'var(--space-2) var(--space-3)',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--color-border)',
                backgroundColor: 'var(--color-surface)',
                fontSize: '0.9375rem',
              }}
            >
              {UNIVERSES.map((u) => (
                <option key={u} value={u}>
                  {u === 'ALL' ? 'Toàn thị trường' : 'VN30'}
                </option>
              ))}
            </select>
          </div>

          {/* Signal */}
          <div>
            <label htmlFor="drawer-signal" style={{ display: 'block', fontWeight: 600, fontSize: '0.875rem', marginBottom: 'var(--space-1)' }}>
              Tín hiệu MA10
            </label>
            <select
              id="drawer-signal"
              value={tempFilters.signal}
              onChange={(e) => onFilterChange('signal', e.target.value)}
              style={{
                width: '100%',
                padding: 'var(--space-2) var(--space-3)',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--color-border)',
                backgroundColor: 'var(--color-surface)',
                fontSize: '0.9375rem',
              }}
            >
              {SIGNALS.map((sig) => (
                <option key={sig} value={sig}>
                  {sig === 'ALL' ? 'Tất cả tín hiệu' : SIGNAL_LABELS[sig] || sig}
                </option>
              ))}
            </select>
          </div>

          {/* Distance range */}
          <div>
            <span style={{ display: 'block', fontWeight: 600, fontSize: '0.875rem', marginBottom: 'var(--space-1)' }}>
              Khoảng cách tới MA10 (%)
            </span>
            <div style={{ display: 'flex', gap: 'var(--space-2)', alignItems: 'center' }}>
              <input
                type="number"
                placeholder="Tối thiểu"
                value={tempFilters.distanceMin}
                onChange={(e) => onFilterChange('distanceMin', e.target.value)}
                style={{
                  flex: 1,
                  padding: 'var(--space-2) var(--space-3)',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--color-border)',
                  fontSize: '0.9375rem',
                }}
                aria-label="Khoảng cách tới MA10 tối thiểu"
              />
              <span style={{ color: 'var(--color-text-muted)' }}>-</span>
              <input
                type="number"
                placeholder="Tối đa"
                value={tempFilters.distanceMax}
                onChange={(e) => onFilterChange('distanceMax', e.target.value)}
                style={{
                  flex: 1,
                  padding: 'var(--space-2) var(--space-3)',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--color-border)',
                  fontSize: '0.9375rem',
                }}
                aria-label="Khoảng cách tới MA10 tối đa"
              />
            </div>
          </div>

          {/* Min Avg Volume 20D */}
          <div>
            <label htmlFor="drawer-volume" style={{ display: 'block', fontWeight: 600, fontSize: '0.875rem', marginBottom: 'var(--space-1)' }}>
              Thanh khoản trung bình 20 phiên tối thiểu
            </label>
            <input
              id="drawer-volume"
              type="number"
              min="0"
              placeholder="Ví dụ: 100000"
              value={tempFilters.minAvgVolume20d}
              onChange={(e) => onFilterChange('minAvgVolume20d', e.target.value)}
              style={{
                width: '100%',
                padding: 'var(--space-2) var(--space-3)',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--color-border)',
                fontSize: '0.9375rem',
              }}
            />
          </div>
        </div>

        {/* Action buttons */}
        <div
          style={{
            display: 'flex',
            gap: 'var(--space-3)',
            marginTop: 'var(--space-6)',
            paddingTop: 'var(--space-4)',
            borderTop: '1px solid var(--color-border)',
          }}
        >
          <button
            type="button"
            onClick={onReset}
            style={{
              flex: 1,
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 'var(--space-1)',
              padding: 'var(--space-3)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--color-border)',
              backgroundColor: 'var(--color-surface)',
              fontWeight: 600,
              fontSize: '0.9375rem',
              color: 'var(--color-text)',
              cursor: 'pointer',
            }}
          >
            <RotateCcw size={16} aria-hidden="true" />
            <span>Xóa lọc</span>
          </button>
          <button
            type="button"
            onClick={onApply}
            style={{
              flex: 1,
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 'var(--space-1)',
              padding: 'var(--space-3)',
              borderRadius: 'var(--radius-md)',
              border: 'none',
              backgroundColor: 'var(--color-primary)',
              fontWeight: 600,
              fontSize: '0.9375rem',
              color: '#ffffff',
              cursor: 'pointer',
            }}
          >
            <Check size={16} aria-hidden="true" />
            <span>Áp dụng</span>
          </button>
        </div>
      </div>
    </div>
  );
};
