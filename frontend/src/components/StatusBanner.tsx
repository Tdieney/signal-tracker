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
  let icon = <Info size={20} aria-hidden="true" />;
  let variantClass = 'status-banner-info';
  let iconColorClass = 'text-muted';
  const role = variant === 'error' ? 'alert' : 'status';

  if (variant === 'warning') {
    variantClass = 'status-banner-warning';
    iconColorClass = 'text-negative';
    icon = <AlertTriangle size={20} aria-hidden="true" />;
  } else if (variant === 'error') {
    variantClass = 'status-banner-error';
    iconColorClass = 'text-negative';
    icon = <AlertCircle size={20} aria-hidden="true" />;
  }

  return (
    <div
      role={role}
      className={`status-banner ${variantClass}`}
    >
      <div className={`status-banner-icon ${iconColorClass}`}>{icon}</div>
      <div className="flex-1">
        {title && <strong className={`status-banner-title ${iconColorClass}`}>{title}</strong>}
        <div>{message}</div>
      </div>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="status-banner-retry"
        >
          <RefreshCw size={14} aria-hidden="true" />
          <span>Thử lại</span>
        </button>
      )}
    </div>
  );
};
