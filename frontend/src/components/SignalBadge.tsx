import React from 'react';
import { ArrowUpRight, ArrowDownRight, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { SIGNAL_LABELS } from '../lib/constants';
import { SignalType } from '../schemas/screenerSchema';

interface SignalBadgeProps {
  signal: SignalType | null | undefined;
  compact?: boolean;
}

const COMPACT_SIGNAL_LABELS: Record<string, string> = {
  ABOVE_MA10: 'Trên MA10',
  BELOW_MA10: 'Dưới MA10',
  CROSS_UP_MA10: 'Cắt lên',
  CROSS_DOWN_MA10: 'Cắt xuống',
};

export const SignalBadge: React.FC<SignalBadgeProps> = ({ signal, compact = false }) => {
  if (!signal) {
    return (
      <span className="flex items-center gap-1 signal-badge-empty">
        <Minus size={14} aria-hidden="true" />
        <span>—</span>
      </span>
    );
  }

  const label = compact
    ? COMPACT_SIGNAL_LABELS[signal] || SIGNAL_LABELS[signal] || signal
    : SIGNAL_LABELS[signal] || signal;

  let variantClass = 'signal-badge-below';
  let icon = <Minus size={14} aria-hidden="true" />;

  switch (signal) {
    case 'CROSS_UP_MA10':
      variantClass = 'signal-badge-cross-up';
      icon = <ArrowUpRight size={14} aria-hidden="true" />;
      break;
    case 'ABOVE_MA10':
      variantClass = 'signal-badge-above';
      icon = <TrendingUp size={14} aria-hidden="true" />;
      break;
    case 'CROSS_DOWN_MA10':
      variantClass = 'signal-badge-cross-down';
      icon = <ArrowDownRight size={14} aria-hidden="true" />;
      break;
    case 'BELOW_MA10':
      variantClass = 'signal-badge-below';
      icon = <TrendingDown size={14} aria-hidden="true" />;
      break;
  }

  return (
    <span
      className={`signal-badge ${variantClass} ${compact ? 'signal-badge-compact' : ''}`}
      title={SIGNAL_LABELS[signal] || label}
    >
      {icon}
      <span>{label}</span>
    </span>
  );
};
