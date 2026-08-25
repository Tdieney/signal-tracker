import React from 'react';
import { Calendar, AlertTriangle, FileText } from 'lucide-react';
import { formatDateVi } from '../lib/formatters';

interface FreshnessBadgeProps {
  status: 'FRESH' | 'STALE' | 'UNKNOWN';
  asOfDate: string;
  generatedAt?: string;
  reason?: string;
  marketSessionStatus?: string;
  provider?: string;
}

export const FreshnessBadge: React.FC<FreshnessBadgeProps> = ({
  status,
  asOfDate,
  reason,
  marketSessionStatus,
  provider,
}) => {
  const formattedDate = formatDateVi(asOfDate);
  const isDemo =
    provider === 'csv' ||
    marketSessionStatus === 'UNKNOWN' ||
    status === 'UNKNOWN' ||
    reason?.toLowerCase().includes('demo') ||
    reason?.toLowerCase().includes('mẫu');

  let icon = <Calendar size={16} aria-hidden="true" />;
  let text = `Dữ liệu phiên ${formattedDate}`;
  let variantClass = 'freshness-badge-unknown';

  if (isDemo) {
    icon = <FileText size={16} aria-hidden="true" />;
    text = `Dữ liệu mẫu — phiên ${formattedDate}`;
    variantClass = 'freshness-badge-unknown';
  } else if (status === 'FRESH') {
    icon = <Calendar size={16} aria-hidden="true" />;
    text = `Dữ liệu phiên ${formattedDate}`;
    variantClass = 'freshness-badge-fresh';
  } else if (status === 'STALE') {
    icon = <AlertTriangle size={16} aria-hidden="true" />;
    text = `Dữ liệu có thể đã cũ — phiên ${formattedDate}`;
    variantClass = 'freshness-badge-stale';
  }

  return (
    <div
      title={reason || text}
      className={`freshness-badge ${variantClass}`}
      data-testid="freshness-badge"
    >
      {icon}
      <span>{text}</span>
    </div>
  );
};
