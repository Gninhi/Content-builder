import React from 'react';
import clsx from 'clsx';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost' | 'outline';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  className,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  disabled,
  ...props
}) => {
  const baseStyles =
    'inline-flex items-center justify-center font-medium rounded-lg transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 focus-visible:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed min-h-[44px] min-w-[44px] px-4 py-2 select-none';

  const variants = {
    primary: 'bg-sky-700 hover:bg-sky-600 active:bg-sky-800 text-white shadow-sm shadow-sky-950/30',
    secondary: 'bg-slate-800 hover:bg-slate-700 text-slate-100 border border-slate-700',
    danger: 'bg-rose-700 hover:bg-rose-600 active:bg-rose-800 text-white shadow-sm shadow-rose-950/30',
    ghost: 'hover:bg-slate-800 text-slate-300 hover:text-white',
    outline: 'border border-slate-700 text-slate-300 hover:bg-slate-800 hover:text-white',
  };

  const sizes = {
    sm: 'text-xs px-3 py-1.5 min-h-[38px]',
    md: 'text-sm px-4 py-2 min-h-[44px]',
    lg: 'text-base px-6 py-3 min-h-[48px]',
  };

  return (
    <button
      className={clsx(baseStyles, variants[variant], sizes[size], className)}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? (
        <span className="flex items-center gap-2">
          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
          </svg>
          <span>Chargement...</span>
        </span>
      ) : (
        children
      )}
    </button>
  );
};
