import React from 'react';
import clsx from 'clsx';

export const Skeleton: React.FC<{ className?: string }> = ({ className }) => {
  return (
    <div
      className={clsx('animate-pulse bg-slate-800/80 rounded-lg', className)}
      aria-hidden="true"
    />
  );
};
