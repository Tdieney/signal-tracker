import React from 'react';
import { Calendar, AlertTriangle, HelpCircle } from 'lucide-react';
import { formatDateVi } from '../lib/formatters';

interface FreshnessBadgeProps {
  status: 'FRESH' | 'STALE' | 'UNKNOWN';
  asOfDate: string;
  generatedAt?: string;
  reason?: string;
}

export const FreshnessBadge: React.FC<FreshnessBadgeProps> = ({
  status,
  asOfDate,
  reason,
}) => {
  const formattedDate = formatDateVi(asOfDate);

  let icon = <Calendar size={16} aria-hidden="true" />;
  let text = `Dữ liệu phiên ${formattedDate}`;
  let bg = 'var(--color-surface-muted)';
  let color = 'var(--color-text)';
  let border = 'var(--color-border)';

  if (status === 'FRESH') {
    icon = <Calendar size={16} aria-hidden="true" />;
    text = `Dữ liệu phiên ${formattedDate}`;
    bg = 'var(--color-positive-bg)';
    color = 'var(--color-positive)';
    border = 'var(--color-positive-border)';
  } else if (status === 'STALE') {
    icon = <AlertTriangle size={16} aria-hidden="true" />;
    text = `Dữ liệu có thể đã cũ — phiên ${formattedDate}`;
    bg = 'var(--color-warning-bg)';
    color = 'var(--color-warning)';
    border = 'var(--color-warning-border)';
  } else if (status === 'UNKNOWN') {
    icon = <HelpCircle size={16} aria-hidden="true" />;
    text = `Dữ liệu gần nhất là phiên ${formattedDate} — chưa xác định độ mới`;
    bg = 'var(--color-surface-muted)';
    color = 'var(--color-text-muted)';
    border = 'var(--color-border)';
  }

  return (
    <div
      title={reason || text}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 'var(--space-2)',
        padding: 'var(--space-1) var(--space-3)',
        borderRadius: 'var(--radius-full)',
        backgroundColor: bg,
        color: color,
        border: `1px solid ${border}`,
        fontSize: '0.875rem',
        fontWeight: 500,
        lineHeight: 1.4,
      }}
    >
      {icon}
      <span>{text}</span>
    </div>
  );
};
