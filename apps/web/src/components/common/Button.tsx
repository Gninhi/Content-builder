import React from 'react';
import clsx from 'clsx';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' | 'vault' | 'brass';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  loadingLabel?: string;
  iconOnly?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  className,
  type = 'button',
  variant = 'primary',
  size = 'md',
  isLoading = false,
  loadingLabel = 'Chargement...',
  iconOnly = false,
  disabled,
  ...props
}) => {
  const baseStyles =
    'inline-flex items-center justify-center font-medium rounded-md select-none transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-app disabled:opacity-50 disabled:cursor-not-allowed';

  const variants = {
    // Primary: Accent plein avec contraste élevé (Texte inverse)
    primary:
      'bg-accent hover:bg-accent-hover active:bg-accent-active text-txt-inverse font-semibold shadow-sm focus-visible:ring-border-focus',
    brass:
      'bg-accent hover:bg-accent-hover active:bg-accent-active text-txt-inverse font-semibold shadow-sm focus-visible:ring-border-focus',
    // Secondary: Surface surélevée avec bordure sobre
    secondary:
      'bg-surface hover:bg-surface-hover active:bg-surface-active text-txt-primary border border-border hover:border-border-hover focus-visible:ring-border-focus shadow-sm',
    vault:
      'bg-surface hover:bg-surface-hover active:bg-surface-active text-txt-primary border border-border hover:border-border-hover focus-visible:ring-border-focus shadow-sm',
    // Outline: Transparent avec bordure standard
    outline:
      'bg-transparent hover:bg-surface text-txt-secondary hover:text-txt-primary border border-border hover:border-border-hover focus-visible:ring-border-focus',
    // Ghost: Léger sans bordure
    ghost:
      'bg-transparent hover:bg-surface text-txt-secondary hover:text-txt-primary focus-visible:ring-border-focus',
    // Danger: Découplé avec bordure et contraste strict
    danger:
      'bg-status-danger-bg text-status-danger-text border border-status-danger-border hover:opacity-90 active:opacity-100 focus-visible:ring-status-danger-border font-medium shadow-sm',
  };

  const sizes = {
    sm: iconOnly ? 'h-9 w-9 p-0' : 'text-xs px-3 py-1.5 min-h-[36px]',
    md: iconOnly ? 'h-11 w-11 p-0' : 'text-sm px-4 py-2 min-h-[44px] min-w-[44px]',
    lg: iconOnly ? 'h-12 w-12 p-0' : 'text-base px-5 py-2.5 min-h-[48px] min-w-[48px]',
  };

  return (
    <button
      type={type}
      className={clsx(baseStyles, variants[variant], sizes[size], className)}
      disabled={disabled || isLoading}
      aria-busy={isLoading}
      {...props}
    >
      {isLoading ? (
        <span className="flex items-center gap-2">
          <svg
            className="animate-spin h-4 w-4 shrink-0"
            viewBox="0 0 24 24"
            fill="none"
            aria-hidden="true"
          >
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
          </svg>
          {loadingLabel && <span>{loadingLabel}</span>}
        </span>
      ) : (
        children
      )}
    </button>
  );
};
