import React from 'react';
import { Badge } from '../common/Badge';
import { Button } from '../common/Button';
import { CalendarPost } from './CalendarSlotCard';
import { formatDateTime } from '../../lib/date';
import { useLanguage } from '../../context/LanguageContext';

interface CalendarListViewProps {
  posts: CalendarPost[];
  canEdit: boolean;
  onReschedule: (post: CalendarPost) => void;
}

export const CalendarListView: React.FC<CalendarListViewProps> = ({
  posts,
  canEdit,
  onReschedule,
}) => {
  const { language } = useLanguage();
  const isEn = language === 'en';

  return (
    <div className="overflow-x-auto rounded-xl border border-border-default bg-surface shadow-subtle">
      <table className="w-full text-left text-xs">
        <thead className="bg-surface-subtle text-[11px] font-semibold text-txt-muted border-b border-border-default">
          <tr>
            <th className="px-4 py-3">{isEn ? 'Platform' : 'Plateforme'}</th>
            <th className="px-4 py-3">{isEn ? 'Status' : 'Statut'}</th>
            <th className="px-4 py-3">{isEn ? 'Snippet' : 'Extrait'}</th>
            <th className="px-4 py-3">{isEn ? 'Scheduled Date' : 'Date programmée'}</th>
            <th className="px-4 py-3 text-right">{isEn ? 'Action' : 'Action'}</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border-subtle">
          {posts.map((post, idx) => (
            <tr key={idx} className="hover:bg-surface-hover transition-colors">
              <td className="px-4 py-3 whitespace-nowrap">
                <Badge
                  variant={post.platform === 'linkedin' ? 'info' : 'neutral'}
                  className="text-[10px]"
                >
                  {post.platform.toUpperCase()}
                </Badge>
              </td>
              <td className="px-4 py-3 whitespace-nowrap">
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
              </td>
              <td className="px-4 py-3 max-w-xs truncate text-txt-primary">
                {post.body_snippet || (isEn ? 'No text' : 'Sans texte')}
              </td>
              <td className="px-4 py-3 whitespace-nowrap font-mono text-[11px] text-accent-text">
                {post.scheduled_at ? formatDateTime(post.scheduled_at, language) : '—'}
              </td>
              <td className="px-4 py-3 whitespace-nowrap text-right">
                {canEdit && !post.isPublished ? (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onReschedule(post)}
                    className="text-[11px] py-0.5 px-2 min-h-[36px]"
                  >
                    {isEn ? 'Reschedule' : 'Reprogrammer'}
                  </Button>
                ) : (
                  <span className="text-[11px] text-txt-muted">—</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
