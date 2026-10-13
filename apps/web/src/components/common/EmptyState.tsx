import React from 'react';
import { Button } from './Button';
import { LucideIcon, Inbox } from 'lucide-react';

export interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon: Icon = Inbox,
  title,
  description,
  actionLabel,
  onAction,
}) => {
  return (
    <div className="panel-surface p-8 sm:p-12 rounded-xl text-center max-w-lg mx-auto space-y-4">
      <div className="w-12 h-12 rounded-lg bg-surface-subtle border border-border text-txt-secondary flex items-center justify-center mx-auto shadow-sm">
        <Icon className="w-6 h-6 text-txt-secondary" />
      </div>
      <div>
        <h3 className="text-base sm:text-lg font-bold text-txt-primary tracking-tight">{title}</h3>
        <p className="text-xs text-txt-secondary leading-relaxed max-w-sm mx-auto mt-1">{description}</p>
      </div>
      {actionLabel && onAction && (
        <div className="pt-2">
          <Button variant="primary" size="sm" onClick={onAction}>
            {actionLabel}
          </Button>
        </div>
      )}
    </div>
  );
};
