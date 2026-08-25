import React, { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';
import { EXCHANGES, SIGNALS, UNIVERSES, SIGNAL_LABELS } from '../lib/constants';
import { FilterState } from '../lib/urlFilter';

interface FilterDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  tempFilters: FilterState;
  onFilterChange: (key: keyof FilterState, value: string | number) => void;
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
  const drawerRef = useRef<HTMLDivElement>(null);
  const closeBtnRef = useRef<HTMLButtonElement>(null);
  const triggerElementRef = useRef<HTMLElement | null>(null);

  const returnFocusToTrigger = () => {
    const btn = document.getElementById('open-filter-drawer-btn');
    const target = triggerElementRef.current || btn;
    if (target && typeof target.focus === 'function') {
      target.focus();
    }
  };

  const handleClose = () => {
    returnFocusToTrigger();
    onClose();
  };

  // Deterministic initial focus & true background isolation lifecycle
  useEffect(() => {
    if (!isOpen) return;

    triggerElementRef.current = document.activeElement as HTMLElement;

    // Isolate entire app shell background with inert and aria-hidden
    const appShell = document.querySelector('.app-shell-root') as HTMLElement | null;
    if (appShell) {
      appShell.setAttribute('aria-hidden', 'true');
      appShell.setAttribute('inert', '');
    }

    // Deterministically focus close button
    if (closeBtnRef.current) {
      closeBtnRef.current.focus();
    }

    return () => {
      if (appShell) {
        appShell.removeAttribute('aria-hidden');
        appShell.removeAttribute('inert');
      }
    };
  }, [isOpen]);

  // Focus trap & Escape key handling
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        handleClose();
        return;
      }

      if (e.key === 'Tab' && drawerRef.current) {
        const focusable = Array.from(
          drawerRef.current.querySelectorAll<HTMLElement>(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
          )
        ).filter((el) => !el.hasAttribute('disabled') && el.offsetParent !== null);

        if (focusable.length === 0) return;

        const firstElement = focusable[0];
        const lastElement = focusable[focusable.length - 1];

        if (e.shiftKey) {
          if (document.activeElement === firstElement) {
            e.preventDefault();
            lastElement.focus();
          }
        } else {
          if (document.activeElement === lastElement) {
            e.preventDefault();
            firstElement.focus();
          }
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const modalContent = (
    <div
      className="filter-drawer-overlay"
      onClick={(e) => {
        if (e.target === e.currentTarget) handleClose();
      }}
    >
      <div
        ref={drawerRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="drawer-title"
        className="filter-drawer-container"
      >
        {/* Header */}
        <div className="flex justify-between items-center mb-4">
          <h2 id="drawer-title" className="text-h2">
            Bộ lọc cổ phiếu
          </h2>
          <button
            ref={closeBtnRef}
            type="button"
            onClick={handleClose}
            aria-label="Đóng bảng lọc"
            className="filter-drawer-close-btn"
          >
            <X size={20} aria-hidden="true" />
          </button>
        </div>

        {/* Form fields */}
        <div className="flex flex-col gap-4">
          {/* Exchange */}
          <div>
            <label htmlFor="drawer-exchange" className="text-small font-semibold block mb-1">
              Sàn giao dịch
            </label>
            <select
              id="drawer-exchange"
              value={tempFilters.exchange}
              onChange={(e) => onFilterChange('exchange', e.target.value)}
              className="filter-select"
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
            <label htmlFor="drawer-universe" className="text-small font-semibold block mb-1">
              Nhóm chỉ số
            </label>
            <select
              id="drawer-universe"
              value={tempFilters.universe}
              onChange={(e) => onFilterChange('universe', e.target.value)}
              className="filter-select"
            >
              {UNIVERSES.map((u) => (
                <option key={u} value={u}>
                  {u === 'ALL' ? 'Toàn thị trường' : 'Chỉ rổ VN30'}
                </option>
              ))}
            </select>
          </div>

          {/* Signal */}
          <div>
            <label htmlFor="drawer-signal" className="text-small font-semibold block mb-1">
              Tín hiệu kỹ thuật
            </label>
            <select
              id="drawer-signal"
              value={tempFilters.signal}
              onChange={(e) => onFilterChange('signal', e.target.value)}
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
          <div>
            <label htmlFor="drawer-min-vol" className="text-small font-semibold block mb-1">
              Khối lượng TB 20 phiên tối thiểu
            </label>
            <input
              id="drawer-min-vol"
              type="number"
              min="0"
              step="100000"
              placeholder="VD: 100000"
              value={tempFilters.minAvgVolume20d}
              onChange={(e) => onFilterChange('minAvgVolume20d', e.target.value)}
              className="filter-search-input"
            />
          </div>

          {/* Distance Min / Max */}
          <div>
            <label className="text-small font-semibold block mb-1">
              Khoảng cách tới MA10 (%)
            </label>
            <div className="flex gap-2">
              <input
                type="number"
                step="0.5"
                placeholder="Tối thiểu"
                value={tempFilters.distanceMin}
                onChange={(e) => onFilterChange('distanceMin', e.target.value)}
                aria-label="Khoảng cách tới MA10 tối thiểu"
                className="filter-search-input flex-1"
              />
              <input
                type="number"
                step="0.5"
                placeholder="Tối đa"
                value={tempFilters.distanceMax}
                onChange={(e) => onFilterChange('distanceMax', e.target.value)}
                aria-label="Khoảng cách tới MA10 tối đa"
                className="filter-search-input flex-1"
              />
            </div>
          </div>
        </div>

        {/* Action buttons */}
        <div className="filter-drawer-actions">
          <button
            type="button"
            onClick={() => {
              returnFocusToTrigger();
              onReset();
            }}
            className="btn-secondary flex-1 justify-center"
          >
            Đặt lại
          </button>
          <button
            type="button"
            onClick={() => {
              returnFocusToTrigger();
              onApply();
            }}
            className="btn-primary flex-1 justify-center"
          >
            Áp dụng
          </button>
        </div>
      </div>
    </div>
  );

  return createPortal(modalContent, document.body);
};
