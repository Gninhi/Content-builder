import React from 'react';
import { Badge } from '../common/Badge';
import { Button } from '../common/Button';
import { formatDateTime } from '../../lib/date';
import { useLanguage } from '../../context/LanguageContext';

export interface CalendarPost {
  job_id?: string;
  post_id?: string;
  variant_id: string;
  workspace_id: string;
  platform: string;
  scheduled_at?: string;
  published_at?: string;
  status: string;
  body_snippet: string;
  isPublished?: boolean;
}

interface CalendarSlotCardProps {
  post: CalendarPost;
  canEdit: boolean;
  onReschedule: (post: CalendarPost) => void;
}

export const CalendarSlotCard: React.FC<CalendarSlotCardProps> = ({
  post,
  canEdit,
  onReschedule,
}) => {
  const { language } = useLanguage();
  const isEn = language === 'en';

  return (
    <div
      className={`rounded-xl border p-4 transition-colors ${
        post.isPublished
          ? 'border-status-success-border bg-status-success-bg'
          : post.status === 'FAILED'
          ? 'border-status-danger-border bg-status-danger-bg'
          : 'border-border-default bg-surface hover:border-border-hover'
      }`}
    >
      <div className="flex items-center justify-between mb-2">
        <Badge
          variant={post.platform === 'linkedin' ? 'info' : 'neutral'}
          className="text-[10px]"
        >
          {post.platform.toUpperCase()}
        </Badge>
        <Badge
          variant={
            post.isPublished
              ? 'success'
              : post.status === 'FAILED'
              ? 'danger'
              : 'warning'
          }
          className="text-[10px]"
        >
          {post.isPublished ? (isEn ? 'Published' : 'Publié') : post.status}
        </Badge>
      </div>

      <p className="text-xs text-txt-primary line-clamp-2 font-medium mb-3 leading-relaxed">
        {post.body_snippet || (isEn ? 'Post without text' : 'Publication sans texte')}
      </p>

      <div className="flex items-center justify-between pt-2 border-t border-border-subtle text-xs text-txt-muted">
        <span className="font-mono text-[11px] text-accent-text">
          {post.scheduled_at ? formatDateTime(post.scheduled_at, language) : (isEn ? 'Not scheduled' : 'Non planifié')}
        </span>

        {canEdit && !post.isPublished && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onReschedule(post)}
            className="text-[11px] py-0.5 px-2 min-h-[36px]"
          >
            {isEn ? 'Reschedule' : 'Reprogrammer'}
          </Button>
        )}
      </div>
    </div>
  );
};
