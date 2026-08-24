import React from 'react';

export const SkipLink: React.FC = () => {
  return (
    <a
      href="#main-content"
      className="skip-link"
      style={{
        position: 'absolute',
        top: '-100px',
        left: '1rem',
        background: 'var(--color-primary-strong)',
        color: '#ffffff',
        padding: 'var(--space-2) var(--space-4)',
        zIndex: 9999,
        borderRadius: 'var(--radius-sm)',
        fontWeight: 600,
        textDecoration: 'none',
        transition: 'top 0.15s ease-in-out',
      }}
      onFocus={(e) => {
        e.currentTarget.style.top = '1rem';
      }}
      onBlur={(e) => {
        e.currentTarget.style.top = '-100px';
      }}
    >
      Bỏ qua đến nội dung chính
    </a>
  );
};
