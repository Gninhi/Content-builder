import React from 'react';
import clsx from 'clsx';
import { useLanguage } from '../../context/LanguageContext';
import { ContentStatus } from '../../types/api';

export interface BadgeProps {
  status?: ContentStatus | 'DEGRADED' | string;
  variant?: 'success' | 'warning' | 'danger' | 'info' | 'neutral' | 'accent' | 'brass' | 'vault' | string;
  label?: string;
  children?: React.ReactNode;
  className?: string;
  withDot?: boolean;
}

export const Badge: React.FC<BadgeProps> = ({
  status,
  variant,
  label,
  children,
  className,
  withDot = false,
}) => {
  const { language } = useLanguage();
  const normStatus = (status || '').toUpperCase();

  const getBadgeStyle = () => {
    if (variant) {
      switch (variant) {
        case 'success':
          return 'bg-status-success-bg text-status-success-text border-status-success-border';
        case 'warning':
          return 'bg-status-warning-bg text-status-warning-text border-status-warning-border';
        case 'danger':
          return 'bg-status-danger-bg text-status-danger-text border-status-danger-border';
        case 'info':
          return 'bg-status-info-bg text-status-info-text border-status-info-border';
        case 'accent':
        case 'brass':
          return 'bg-accent-subtle text-accent-txt border-accent-border';
        case 'vault':
          return 'bg-surface text-txt-secondary border-border';
        case 'neutral':
        default:
          return 'bg-surface-subtle text-txt-secondary border-border-subtle';
      }
    }

    switch (normStatus) {
      case 'DRAFT':
        return 'bg-surface-subtle text-txt-secondary border-border-subtle';
      case 'PENDING_REVIEW':
        return 'bg-status-warning-bg text-status-warning-text border-status-warning-border';
      case 'APPROVED':
        return 'bg-status-success-bg text-status-success-text border-status-success-border';
      case 'SCHEDULED':
        return 'bg-status-info-bg text-status-info-text border-status-info-border';
      case 'PUBLISHING':
        return 'bg-status-info-bg text-status-info-text border-status-info-border animate-pulse';
      case 'PUBLISHED':
        return 'bg-status-success-bg text-status-success-text border-status-success-border';
      case 'FAILED':
        return 'bg-status-danger-bg text-status-danger-text border-status-danger-border';
      case 'PUBLISH_UNKNOWN':
        return 'bg-status-warning-bg text-status-warning-text border-status-warning-border';
      case 'DEGRADED':
        return 'bg-status-warning-bg text-status-warning-text border-status-warning-border';
      default:
        return 'bg-surface-subtle text-txt-secondary border-border-subtle';
    }
  };

  const getDotColor = () => {
    if (variant === 'success' || normStatus === 'PUBLISHED' || normStatus === 'APPROVED') {
      return 'bg-status-success-text';
    }
    if (variant === 'danger' || normStatus === 'FAILED') {
      return 'bg-status-danger-text';
    }
    if (variant === 'warning' || normStatus === 'PENDING_REVIEW' || normStatus === 'DEGRADED' || normStatus === 'PUBLISH_UNKNOWN') {
      return 'bg-status-warning-text';
    }
    if (variant === 'accent' || variant === 'brass') {
      return 'bg-accent';
    }
    return 'bg-txt-muted';
  };

  const getDisplayContent = () => {
    if (children) return children;
    if (label) return label;

    const isEn = language === 'en';
    switch (normStatus) {
      case 'DRAFT':
        return isEn ? 'Draft' : 'Brouillon';
      case 'PENDING_REVIEW':
        return isEn ? 'Pending Review (HITL)' : 'À Revoir (HITL)';
      case 'APPROVED':
        return isEn ? 'Approved' : 'Approuvé';
      case 'SCHEDULED':
        return isEn ? 'Scheduled' : 'Planifié';
      case 'PUBLISHING':
        return isEn ? 'Publishing...' : 'Publication en cours';
      case 'PUBLISHED':
        return isEn ? 'Published' : 'Publié';
      case 'FAILED':
        return isEn ? 'Failed' : 'Échec';
      case 'PUBLISH_UNKNOWN':
        return isEn ? 'Unknown Status' : 'Statut Incertain';
      case 'DEGRADED':
        return isEn ? 'Degraded Mode' : 'Mode Dégradé';
      default:
        return status || '';
    }
  };

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium border select-none transition-colors',
        getBadgeStyle(),
        className
      )}
    >
      {withDot && (
        <span
          className={clsx('h-1.5 w-1.5 rounded-full shrink-0', getDotColor())}
          aria-hidden="true"
        />
      )}
      {getDisplayContent()}
    </span>
  );
};

export const StatusBadge: React.FC<BadgeProps> = Badge;
