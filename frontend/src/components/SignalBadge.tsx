import React from 'react';
import { ArrowUpRight, ArrowDownRight, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { SIGNAL_LABELS } from '../lib/constants';
import { SignalType } from '../schemas/screenerSchema';

interface SignalBadgeProps {
  signal: SignalType | null | undefined;
  compact?: boolean;
}

export const SignalBadge: React.FC<SignalBadgeProps> = ({ signal, compact = false }) => {
  if (!signal) {
    return (
      <span
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 'var(--space-1)',
          color: 'var(--color-text-muted)',
          fontSize: '0.875rem',
        }}
      >
        <Minus size={14} aria-hidden="true" />
        <span>—</span>
      </span>
    );
  }

  const label = SIGNAL_LABELS[signal] || signal;

  let bg = 'var(--color-surface-muted)';
  let color = 'var(--color-text)';
  let border = 'var(--color-border)';
  let icon = <Minus size={14} aria-hidden="true" />;

  switch (signal) {
    case 'CROSS_UP_MA10':
      bg = 'var(--color-positive-bg)';
      color = 'var(--color-positive)';
      border = 'var(--color-positive-border)';
      icon = <ArrowUpRight size={15} aria-hidden="true" />;
      break;
    case 'ABOVE_MA10':
      bg = 'var(--color-info-bg)';
      color = 'var(--color-info)';
      border = 'var(--color-info-border)';
      icon = <TrendingUp size={15} aria-hidden="true" />;
      break;
    case 'CROSS_DOWN_MA10':
      bg = 'var(--color-negative-bg)';
      color = 'var(--color-negative)';
      border = 'var(--color-negative-border)';
      icon = <ArrowDownRight size={15} aria-hidden="true" />;
      break;
    case 'BELOW_MA10':
      bg = 'var(--color-surface-muted)';
      color = 'var(--color-text-muted)';
      border = 'var(--color-border)';
      icon = <TrendingDown size={15} aria-hidden="true" />;
      break;
  }

  return (
    <span
      className="signal-badge"
      title={label}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '4px',
        padding: compact ? '2px 8px' : '4px 10px',
        borderRadius: 'var(--radius-sm)',
        backgroundColor: bg,
        color: color,
        border: `1px solid ${border}`,
        fontSize: compact ? '0.75rem' : '0.875rem',
        fontWeight: 600,
        whiteSpace: 'nowrap',
      }}
    >
      {icon}
      <span>{label}</span>
    </span>
  );
};
