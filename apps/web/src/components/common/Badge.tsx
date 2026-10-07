import React from 'react';
import clsx from 'clsx';
import { ContentStatus } from '../../types/api';

export interface BadgeProps {
  status?: ContentStatus | 'DEGRADED' | string;
  variant?: 'success' | 'warning' | 'danger' | 'info' | 'neutral' | string;
  label?: string;
  children?: React.ReactNode;
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  status,
  variant,
  label,
  children,
  className,
}) => {
  const normStatus = (status || '').toUpperCase();

  const getBadgeStyle = () => {
    if (variant) {
      switch (variant) {
        case 'success':
          return 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40';
        case 'warning':
          return 'bg-amber-500/15 text-amber-300 border-amber-500/40';
        case 'danger':
          return 'bg-rose-500/15 text-rose-300 border-rose-500/40';
        case 'info':
          return 'bg-cyan-500/15 text-cyan-300 border-cyan-500/40';
        case 'neutral':
        default:
          return 'bg-slate-800 text-slate-300 border-slate-700';
      }
    }

    switch (normStatus) {
      case 'DRAFT':
        return 'bg-slate-800 text-slate-300 border-slate-700';
      case 'PENDING_REVIEW':
        return 'bg-amber-500/15 text-amber-300 border-amber-500/40 animate-pulse';
      case 'APPROVED':
        return 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40';
      case 'SCHEDULED':
        return 'bg-sky-500/15 text-sky-300 border-sky-500/40';
      case 'PUBLISHING':
        return 'bg-cyan-500/15 text-cyan-300 border-cyan-500/40 animate-pulse';
      case 'PUBLISHED':
        return 'bg-emerald-600/20 text-emerald-400 border-emerald-600/50';
      case 'FAILED':
        return 'bg-rose-500/15 text-rose-300 border-rose-500/40';
      case 'PUBLISH_UNKNOWN':
        return 'bg-purple-500/15 text-purple-300 border-purple-500/40';
      case 'DEGRADED':
        return 'bg-orange-500/20 text-orange-300 border-orange-500/40';
      default:
        return 'bg-slate-800 text-slate-300 border-slate-700';
    }
  };

  const getDisplayContent = () => {
    if (children) return children;
    if (label) return label;
    switch (normStatus) {
      case 'DRAFT':
        return 'Brouillon';
      case 'PENDING_REVIEW':
        return 'À Revoir (HITL)';
      case 'APPROVED':
        return 'Approuvé';
      case 'SCHEDULED':
        return 'Planifié';
      case 'PUBLISHING':
        return 'Publication en cours';
      case 'PUBLISHED':
        return 'Publié';
      case 'FAILED':
        return 'Échec';
      case 'PUBLISH_UNKNOWN':
        return 'Statut Incertain';
      case 'DEGRADED':
        return 'Mode Dégradé';
      default:
        return status || '';
    }
  };

  return (
    <span
      className={clsx(
        'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-mono font-medium border select-none',
        getBadgeStyle(),
        className
      )}
    >
      {getDisplayContent()}
    </span>
  );
};

export const StatusBadge: React.FC<BadgeProps> = Badge;
