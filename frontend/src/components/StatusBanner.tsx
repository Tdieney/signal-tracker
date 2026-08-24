import React from 'react';
import { AlertCircle, AlertTriangle, Info, RefreshCw } from 'lucide-react';

interface StatusBannerProps {
  variant: 'info' | 'warning' | 'error';
  title?: string;
  message: string;
  onRetry?: () => void;
}

export const StatusBanner: React.FC<StatusBannerProps> = ({
  variant,
  title,
  message,
  onRetry,
}) => {
  let bg = 'var(--color-info-bg)';
  let border = 'var(--color-info-border)';
  let color = 'var(--color-info)';
  let icon = <Info size={20} aria-hidden="true" />;
  const role = variant === 'error' ? 'alert' : 'status';

  if (variant === 'warning') {
    bg = 'var(--color-warning-bg)';
    border = 'var(--color-warning-border)';
    color = 'var(--color-warning)';
    icon = <AlertTriangle size={20} aria-hidden="true" />;
  } else if (variant === 'error') {
    bg = 'var(--color-negative-bg)';
    border = 'var(--color-negative-border)';
    color = 'var(--color-negative)';
    icon = <AlertCircle size={20} aria-hidden="true" />;
  }

  return (
    <div
      role={role}
      className="status-banner"
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: 'var(--space-3)',
        padding: 'var(--space-3) var(--space-4)',
        backgroundColor: bg,
        border: `1px solid ${border}`,
        borderRadius: 'var(--radius-md)',
        color: 'var(--color-text)',
        marginBottom: 'var(--space-4)',
      }}
    >
      <div style={{ color, flexShrink: 0, marginTop: '2px' }}>{icon}</div>
      <div style={{ flex: 1, fontSize: '0.875rem' }}>
        {title && <strong style={{ display: 'block', marginBottom: '2px', color }}>{title}</strong>}
        <div>{message}</div>
      </div>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 'var(--space-1)',
            padding: 'var(--space-1) var(--space-3)',
            backgroundColor: 'var(--color-surface)',
            border: `1px solid ${border}`,
            borderRadius: 'var(--radius-sm)',
            fontSize: '0.8125rem',
            fontWeight: 600,
            color: 'var(--color-text)',
            cursor: 'pointer',
            flexShrink: 0,
          }}
        >
          <RefreshCw size={14} aria-hidden="true" />
          <span>Thử lại</span>
        </button>
      )}
    </div>
  );
};
