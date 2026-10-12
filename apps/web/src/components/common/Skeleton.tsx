import React from 'react';
import clsx from 'clsx';

export const Skeleton: React.FC<{ className?: string }> = ({ className }) => {
  return (
    <div
      className={clsx(
        'animate-pulse bg-surface-subtle border border-border-subtle rounded-md',
        className
      )}
      aria-hidden="true"
    />
  );
};
