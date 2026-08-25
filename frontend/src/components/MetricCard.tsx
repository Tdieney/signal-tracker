import React from 'react';
import { ArrowUpRight, TrendingUp, TrendingDown, ArrowDownRight, Activity } from 'lucide-react';

interface MetricCardProps {
  label: string;
  value: number | string | null | undefined;
  percentage?: number | null;
  contextText?: string;
  linkHref?: string;
  tone?: 'default' | 'positive' | 'negative' | 'info';
  iconType?: 'cross_up' | 'cross_down' | 'above' | 'below' | 'total';
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  percentage,
  contextText,
  linkHref,
  tone = 'default',
  iconType,
}) => {
  let icon = null;
  if (iconType === 'total') icon = <Activity size={18} aria-hidden="true" />;
  else if (iconType === 'above') icon = <TrendingUp size={18} aria-hidden="true" />;
  else if (iconType === 'below') icon = <TrendingDown size={18} aria-hidden="true" />;
  else if (iconType === 'cross_up') icon = <ArrowUpRight size={18} aria-hidden="true" />;
  else if (iconType === 'cross_down') icon = <ArrowDownRight size={18} aria-hidden="true" />;

  let toneClass = '';
  if (tone === 'positive') toneClass = 'metric-card-positive';
  else if (tone === 'negative') toneClass = 'metric-card-negative';
  else if (tone === 'info') toneClass = 'metric-card-info';

  const content = (
    <div className={`card metric-card ${toneClass}`}>
      <div className="metric-card-header">
        <span className="text-small font-semibold">{label}</span>
        {icon && <span>{icon}</span>}
      </div>

      <div className="metric-card-body">
        <span className="metric-card-value">
          {value !== null && value !== undefined ? value : '—'}
        </span>
        {percentage !== undefined && percentage !== null && (
          <span className="metric-card-pct">
            ({percentage}%)
          </span>
        )}
      </div>

      {contextText && (
        <div className="text-xs text-muted mt-2">
          {contextText}
        </div>
      )}
    </div>
  );

  if (linkHref) {
    return (
      <a
        href={linkHref}
        className="metric-card-wrapper"
        aria-label={`${label}: ${value} ${percentage !== undefined && percentage !== null ? `(${percentage}%)` : ''}. Bấm để xem trong bộ lọc.`}
      >
        {content}
      </a>
    );
  }

  return content;
};
