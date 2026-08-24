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

  let toneColor = 'var(--color-text)';
  if (tone === 'positive') toneColor = 'var(--color-positive)';
  else if (tone === 'negative') toneColor = 'var(--color-negative)';
  else if (tone === 'info') toneColor = 'var(--color-primary)';

  const content = (
    <div
      className="card"
      style={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        height: '100%',
        padding: 'var(--space-4)',
        transition: 'transform 150ms ease, box-shadow 150ms ease, border-color 150ms ease',
        borderColor: linkHref ? 'var(--color-border)' : 'var(--color-border-subtle)',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-2)' }}>
        <span className="text-small" style={{ fontWeight: 500 }}>{label}</span>
        {icon && <span style={{ color: toneColor }}>{icon}</span>}
      </div>

      <div style={{ display: 'flex', alignItems: 'baseline', gap: 'var(--space-2)', marginTop: 'var(--space-1)' }}>
        <span className="text-display" style={{ color: toneColor }}>
          {value !== null && value !== undefined ? value : '—'}
        </span>
        {percentage !== undefined && percentage !== null && (
          <span className="text-small" style={{ fontWeight: 600, color: toneColor }}>
            ({percentage}%)
          </span>
        )}
      </div>

      {contextText && (
        <div className="text-xs" style={{ marginTop: 'var(--space-2)' }}>
          {contextText}
        </div>
      )}
    </div>
  );

  if (linkHref) {
    return (
      <a
        href={linkHref}
        style={{ textDecoration: 'none', color: 'inherit', display: 'block', height: '100%' }}
        aria-label={`${label}: ${value} ${percentage !== undefined && percentage !== null ? `(${percentage}%)` : ''}. Bấm để xem trong bộ lọc.`}
      >
        {content}
      </a>
    );
  }

  return content;
};
