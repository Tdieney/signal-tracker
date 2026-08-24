import React from 'react';

interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  borderRadius?: string;
  style?: React.CSSProperties;
}

export const Skeleton: React.FC<SkeletonProps> = ({
  width = '100%',
  height = '1.25rem',
  borderRadius = 'var(--radius-sm)',
  style,
}) => {
  return (
    <div
      aria-hidden="true"
      style={{
        width,
        height,
        borderRadius,
        backgroundColor: 'var(--color-skeleton)',
        opacity: 0.7,
        animation: 'skeleton-pulse 1.5s ease-in-out infinite',
        ...style,
      }}
    />
  );
};
