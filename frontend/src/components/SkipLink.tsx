import React from 'react';

export const SkipLink: React.FC = () => {
  const handleSkip = (e: React.MouseEvent<HTMLAnchorElement>) => {
    e.preventDefault();
    const mainContent = document.getElementById('main-content');
    if (mainContent) {
      mainContent.focus({ preventScroll: false });
      mainContent.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <a
      href="#main-content"
      className="skip-link"
      onClick={handleSkip}
    >
      Bỏ qua đến nội dung chính
    </a>
  );
};
