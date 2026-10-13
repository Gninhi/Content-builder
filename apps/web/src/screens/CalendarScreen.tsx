import React, { useState, useEffect } from 'react';
import { useLanguage } from '../context/LanguageContext';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { apiClient } from '../lib/api';
import { Button } from '../components/common/Button';
import { Skeleton } from '../components/common/Skeleton';
import { ErrorState } from '../components/common/ErrorState';
import { EmptyState } from '../components/common/EmptyState';
import { ConfirmDialog } from '../components/common/ConfirmDialog';
import { Clock, RefreshCw } from 'lucide-react';
import {
  CalendarSlotCard,
  CalendarPost,
} from '../components/calendar/CalendarSlotCard';
import { CalendarListView } from '../components/calendar/CalendarListView';
import { CalendarRescheduleModal } from '../components/calendar/CalendarRescheduleModal';

export const CalendarScreen: React.FC = () => {
  const { t, language } = useLanguage();
  const { session, canEdit, isOwner } = useAuth();
  const { showToast } = useToast();
  const isEn = language === 'en';

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [scheduledPosts, setScheduledPosts] = useState<CalendarPost[]>([]);
  const [publishedPosts, setPublishedPosts] = useState<CalendarPost[]>([]);

  const [viewMode, setViewMode] = useState<'month' | 'week' | 'list'>('month');
  const [platformFilter, setPlatformFilter] = useState<string>('all');

  // Reschedule dialog
  const [selectedPost, setSelectedPost] = useState<CalendarPost | null>(null);
  const [newDateStr, setNewDateStr] = useState<string>('');
  const [isRescheduling, setIsRescheduling] = useState<boolean>(false);
  const [isPublishingNow, setIsPublishingNow] = useState<boolean>(false);
  const [cancelTargetJobId, setCancelTargetJobId] = useState<string | null>(null);
  const [isCancelling, setIsCancelling] = useState<boolean>(false);
  const [collisionWarning, setCollisionWarning] = useState<string | null>(null);

  const fetchCalendar = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient<{ scheduled: CalendarPost[]; published: CalendarPost[] }>(
        '/v1/calendar'
      );
      setScheduledPosts(data.scheduled || []);
      setPublishedPosts(data.published || []);
    } catch (err: any) {
      setError(err.message || (isEn ? 'Failed to load calendar.' : 'Impossible de charger le calendrier.'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCalendar();
  }, [session?.workspace_id]);

  const allPosts: CalendarPost[] = [
    ...scheduledPosts.map((p) => ({ ...p, isPublished: false })),
    ...publishedPosts.map((p) => ({
      ...p,
      isPublished: true,
      scheduled_at: p.published_at || p.scheduled_at,
    })),
  ];

  const filteredPosts = allPosts.filter((p) => {
    if (platformFilter === 'all') return true;
    return p.platform.toLowerCase() === platformFilter.toLowerCase();
  });

  const checkCollision = (dateIso: string, currentJobId?: string) => {
    const targetTime = new Date(dateIso).getTime();
    const collision = scheduledPosts.find((p) => {
      if (p.job_id === currentJobId) return false;
      if (!p.scheduled_at) return false;
      const otherTime = new Date(p.scheduled_at).getTime();
      return Math.abs(targetTime - otherTime) < 30 * 60 * 1000; // < 30 minutes collision
    });

    if (collision) {
      setCollisionWarning(
        isEn
          ? `Warning: A post on ${collision.platform.toUpperCase()} is already scheduled within this 30-minute window.`
          : `Attention : Une publication sur ${collision.platform.toUpperCase()} est déjà programmée dans cet intervalle de 30 min.`
      );
    } else {
      setCollisionWarning(null);
    }
  };

  const handleOpenReschedule = (post: CalendarPost) => {
    setSelectedPost(post);
    setNewDateStr(
      post.scheduled_at
        ? new Date(post.scheduled_at).toISOString().slice(0, 16)
        : new Date().toISOString().slice(0, 16)
    );
  };

  const handleReschedule = async () => {
    if (!selectedPost || !newDateStr) return;
    setIsRescheduling(true);
    try {
      await apiClient('/v1/publications/schedule', {
        method: 'POST',
        body: JSON.stringify({
          variant_id: selectedPost.variant_id,
          scheduled_at: new Date(newDateStr).toISOString(),
        }),
      });
      showToast('success', isEn ? 'Publication rescheduled successfully!' : 'Publication reprogrammée avec succès !');
      await fetchCalendar();
      setSelectedPost(null);
    } catch (err: any) {
      showToast('error', `Erreur de programmation : ${err.message}`);
    } finally {
      setIsRescheduling(false);
    }
  };

  const handlePublishNow = async (jobId: string) => {
    if (!isOwner) {
      showToast('error', isEn ? 'Only an Owner can trigger immediate broadcast.' : 'Seul le rôle Owner peut déclencher la publication immédiate.');
      return;
    }
    setIsPublishingNow(true);
    try {
      await apiClient(`/v1/publications/${jobId}/publish-now`, { method: 'POST' });
      showToast('success', isEn ? 'Post broadcasted and sealed successfully!' : 'Publication diffusée et scellée en base avec succès !');
      await fetchCalendar();
      setSelectedPost(null);
    } catch (err: any) {
      showToast('error', `Erreur de publication immédiate : ${err.message}`);
    } finally {
      setIsPublishingNow(false);
    }
  };

  const handleConfirmCancel = async () => {
    if (!cancelTargetJobId) return;
    setIsCancelling(true);
    try {
      await apiClient(`/v1/publications/${cancelTargetJobId}/cancel`, { method: 'POST' });
      showToast('info', isEn ? 'Scheduled publication cancelled.' : 'Publication planifiée annulée.');
      await fetchCalendar();
      setCancelTargetJobId(null);
      setSelectedPost(null);
    } catch (err: any) {
      showToast('error', `Erreur d'annulation : ${err.message}`);
    } finally {
      setIsCancelling(false);
    }
  };

  if (loading && allPosts.length === 0) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64 rounded-md" />
        <Skeleton className="h-[500px] w-full rounded-xl" />
      </div>
    );
  }

  if (error && allPosts.length === 0) {
    return <ErrorState message={error} onRetry={fetchCalendar} />;
  }

  return (
    <div className="space-y-6 w-full">
      {/* Top Header & View Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border-default pb-4">
        <div>
          <h2 className="text-lg sm:text-xl font-bold text-txt-primary tracking-tight">
            {t.calendar.title}
          </h2>
          <div className="flex items-center gap-2 text-xs text-txt-muted mt-1">
            <Clock className="h-3.5 w-3.5 text-accent" />
            <span className="font-mono">
              {isEn ? 'Timezone: UTC (Local display: ' : 'Fuseau : UTC (affichage local : '}
              {Intl.DateTimeFormat().resolvedOptions().timeZone})
            </span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Platform Filters */}
          <div className="flex items-center rounded-md border border-border-default bg-surface-subtle p-0.5 text-xs font-mono">
            {['all', 'linkedin', 'x'].map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => setPlatformFilter(p)}
                className={`rounded px-2.5 py-1 font-medium transition-colors ${
                  platformFilter === p
                    ? 'bg-accent text-txt-inverse font-bold shadow-xs'
                    : 'text-txt-muted hover:text-txt-primary'
                }`}
              >
                {p === 'all' ? (isEn ? 'All' : 'Toutes') : p.toUpperCase()}
              </button>
            ))}
          </div>

          {/* Month / Week / List Switcher */}
          <div className="flex items-center rounded-md border border-border-default bg-surface-subtle p-0.5 text-xs">
            <button
              type="button"
              onClick={() => setViewMode('month')}
              className={`rounded px-2.5 py-1 font-medium transition-colors ${
                viewMode === 'month'
                  ? 'bg-surface text-txt-primary font-semibold shadow-xs'
                  : 'text-txt-muted hover:text-txt-primary'
              }`}
            >
              {t.calendar.view_month}
            </button>
            <button
              type="button"
              onClick={() => setViewMode('week')}
              className={`rounded px-2.5 py-1 font-medium transition-colors ${
                viewMode === 'week'
                  ? 'bg-surface text-txt-primary font-semibold shadow-xs'
                  : 'text-txt-muted hover:text-txt-primary'
              }`}
            >
              {t.calendar.view_week}
            </button>
            <button
              type="button"
              onClick={() => setViewMode('list')}
              className={`rounded px-2.5 py-1 font-medium transition-colors ${
                viewMode === 'list'
                  ? 'bg-surface text-txt-primary font-semibold shadow-xs'
                  : 'text-txt-muted hover:text-txt-primary'
              }`}
            >
              {isEn ? 'List' : 'Liste'}
            </button>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="rounded-xl border border-border-default bg-surface p-5 sm:p-6 space-y-6 shadow-subtle">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-semibold text-txt-secondary">
            {isEn ? `Publication Events (${filteredPosts.length})` : `Événements de publication (${filteredPosts.length})`}
          </h3>
          <Button
            variant="ghost"
            size="sm"
            onClick={fetchCalendar}
            className="text-xs min-h-[36px]"
          >
            <RefreshCw className="h-3.5 w-3.5 mr-1 text-accent" />
            {isEn ? 'Refresh' : 'Actualiser'}
          </Button>
        </div>

        {filteredPosts.length === 0 ? (
          <EmptyState
            title={isEn ? 'No publications in calendar' : 'Aucune publication dans le calendrier'}
            description={
              isEn
                ? 'Approved posts in the HITL review will automatically appear in this timeline.'
                : 'Les publications approuvées dans la revue HITL apparaîtront automatiquement ici.'
            }
          />
        ) : viewMode === 'list' ? (
          <CalendarListView
            posts={filteredPosts}
            canEdit={canEdit}
            onReschedule={handleOpenReschedule}
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredPosts.map((post, idx) => (
              <CalendarSlotCard
                key={idx}
                post={post}
                canEdit={canEdit}
                onReschedule={handleOpenReschedule}
              />
            ))}
          </div>
        )}
      </div>

      {/* Reschedule Modal */}
      <CalendarRescheduleModal
        isOpen={Boolean(selectedPost)}
        selectedPost={selectedPost}
        newDateStr={newDateStr}
        collisionWarning={collisionWarning}
        isOwner={isOwner}
        isRescheduling={isRescheduling}
        isPublishingNow={isPublishingNow}
        onDateChange={(val) => {
          setNewDateStr(val);
          if (selectedPost) {
            checkCollision(val, selectedPost.job_id);
          }
        }}
        onClose={() => setSelectedPost(null)}
        onReschedule={handleReschedule}
        onPublishNow={handlePublishNow}
        onCancelJob={(jobId) => setCancelTargetJobId(jobId)}
      />

      {/* Cancellation Confirm Dialog */}
      <ConfirmDialog
        isOpen={Boolean(cancelTargetJobId)}
        onClose={() => setCancelTargetJobId(null)}
        onConfirm={handleConfirmCancel}
        title={isEn ? 'Cancel Scheduled Publication' : 'Annuler la publication planifiée'}
        message={
          isEn
            ? 'Are you sure you want to permanently cancel this scheduled publication job?'
            : 'Êtes-vous certain de vouloir annuler définitivement ce travail de publication ?'
        }
        confirmText={isEn ? 'Confirm Cancellation' : 'Confirmer l’annulation'}
        variant="danger"
        isLoading={isCancelling}
      />
    </div>
  );
};
