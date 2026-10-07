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
    <div className="glass-panel p-12 rounded-2xl text-center max-w-lg mx-auto space-y-4 border border-slate-800 bg-slate-900/40">
      <div className="w-16 h-16 rounded-full bg-slate-800/80 border border-slate-700 text-cyan-400 flex items-center justify-center mx-auto">
        <Icon className="w-8 h-8" />
      </div>
      <h3 className="text-lg font-bold text-white tracking-tight">{title}</h3>
      <p className="text-xs text-slate-400 leading-relaxed max-w-sm mx-auto">{description}</p>
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
