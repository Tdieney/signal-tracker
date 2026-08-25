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
      <span className="flex items-center gap-1 signal-badge-empty">
        <Minus size={14} aria-hidden="true" />
        <span>—</span>
      </span>
    );
  }

  const label = SIGNAL_LABELS[signal] || signal;
  let variantClass = 'signal-badge-below';
  let icon = <Minus size={14} aria-hidden="true" />;

  switch (signal) {
    case 'CROSS_UP_MA10':
      variantClass = 'signal-badge-cross-up';
      icon = <ArrowUpRight size={15} aria-hidden="true" />;
      break;
    case 'ABOVE_MA10':
      variantClass = 'signal-badge-above';
      icon = <TrendingUp size={15} aria-hidden="true" />;
      break;
    case 'CROSS_DOWN_MA10':
      variantClass = 'signal-badge-cross-down';
      icon = <ArrowDownRight size={15} aria-hidden="true" />;
      break;
    case 'BELOW_MA10':
      variantClass = 'signal-badge-below';
      icon = <TrendingDown size={15} aria-hidden="true" />;
      break;
  }

  return (
    <span
      className={`signal-badge ${variantClass} ${compact ? 'signal-badge-compact' : ''}`}
      title={label}
    >
      {icon}
      <span>{label}</span>
    </span>
  );
};
