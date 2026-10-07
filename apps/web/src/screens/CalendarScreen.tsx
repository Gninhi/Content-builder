import React, { useState, useEffect } from 'react';
import { useLanguage } from '../context/LanguageContext';
import { useAuth } from '../context/AuthContext';
import { apiClient } from '../lib/api';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';
import { Skeleton } from '../components/common/Skeleton';
import { ErrorState } from '../components/common/ErrorState';
import { EmptyState } from '../components/common/EmptyState';
import { Dialog } from '../components/common/Dialog';
import { Input } from '../components/common/Input';
import {
  Clock,
  AlertTriangle,
  RefreshCw,
} from 'lucide-react';

interface CalendarPost {
  job_id?: string;
  post_id?: string;
  variant_id: string;
  workspace_id: string;
  platform: string;
  scheduled_at?: string;
  published_at?: string;
  status: string;
  body_snippet: string;
}

export const CalendarScreen: React.FC = () => {
  const { t } = useLanguage();
  const { session, canEdit } = useAuth();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [scheduledPosts, setScheduledPosts] = useState<CalendarPost[]>([]);
  const [publishedPosts, setPublishedPosts] = useState<CalendarPost[]>([]);

  const [viewMode, setViewMode] = useState<'month' | 'week'>('month');
  const [platformFilter, setPlatformFilter] = useState<string>('all');

  // Reschedule dialog
  const [selectedPost, setSelectedPost] = useState<CalendarPost | null>(null);
  const [newDateStr, setNewDateStr] = useState<string>('');
  const [isRescheduling, setIsRescheduling] = useState<boolean>(false);
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
      setError(err.message || 'Impossible de charger le calendrier.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCalendar();
  }, [session?.workspace_id]);

  const allPosts = [
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
        `Attention : Une publication sur ${collision.platform.toUpperCase()} est déjà programmée dans cet intervalle de 30 min.`
      );
    } else {
      setCollisionWarning(null);
    }
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
      await fetchCalendar();
      setSelectedPost(null);
    } catch (err: any) {
      alert(`Erreur de programmation : ${err.message}`);
    } finally {
      setIsRescheduling(false);
    }
  };

  const handleCancelJob = async (jobId: string) => {
    if (!confirm('Confirmer l’annulation de cette publication planifiée ?')) return;
    try {
      await apiClient(`/v1/publications/${jobId}/cancel`, { method: 'POST' });
      await fetchCalendar();
      setSelectedPost(null);
    } catch (err: any) {
      alert(`Erreur d'annulation : ${err.message}`);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="h-8 w-64 bg-slate-800 rounded animate-pulse" />
        <Skeleton className="h-[500px] w-full" />
      </div>
    );
  }

  if (error) {
    return <ErrorState message={error} onRetry={fetchCalendar} />;
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Top Header & View Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">
            {t.calendar.title}
          </h2>
          <div className="flex items-center gap-2 text-xs text-slate-400 mt-1">
            <Clock className="h-3.5 w-3.5 text-cyan-400" />
            <span>Fuseau : UTC (affichage local : {Intl.DateTimeFormat().resolvedOptions().timeZone})</span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Platform Filters */}
          <div className="flex items-center rounded-lg border border-slate-700 bg-slate-800 p-0.5 text-xs">
            {['all', 'linkedin', 'x'].map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => setPlatformFilter(p)}
                className={`rounded px-2.5 py-1 font-medium transition-colors ${
                  platformFilter === p
                    ? 'bg-cyan-500 text-slate-950 font-bold'
                    : 'text-slate-300 hover:text-white'
                }`}
              >
                {p === 'all' ? 'Toutes' : p.toUpperCase()}
              </button>
            ))}
          </div>

          {/* Month / Week Switcher */}
          <div className="flex items-center rounded-lg border border-slate-700 bg-slate-800 p-0.5 text-xs">
            <button
              type="button"
              onClick={() => setViewMode('month')}
              className={`rounded px-2.5 py-1 font-medium transition-colors ${
                viewMode === 'month'
                  ? 'bg-slate-700 text-white font-bold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {t.calendar.view_month}
            </button>
            <button
              type="button"
              onClick={() => setViewMode('week')}
              className={`rounded px-2.5 py-1 font-medium transition-colors ${
                viewMode === 'week'
                  ? 'bg-slate-700 text-white font-bold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {t.calendar.view_week}
            </button>
          </div>
        </div>
      </div>

      {/* Calendar List View with Status & Collision Prevention */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 space-y-6">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300">
            Événements de publication ({filteredPosts.length})
          </h3>
          <Button variant="ghost" size="sm" onClick={fetchCalendar} className="text-xs text-slate-400">
            <RefreshCw className="h-3.5 w-3.5 mr-1" />
            Actualiser
          </Button>
        </div>

        {filteredPosts.length === 0 ? (
          <EmptyState
            title="Aucune publication dans le calendrier"
            description="Les publications approuvées dans la revue HITL apparaîtront automatiquement ici."
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredPosts.map((post, idx) => {
              const date = post.scheduled_at ? new Date(post.scheduled_at) : new Date();
              return (
                <div
                  key={idx}
                  className={`rounded-xl border p-4 transition-all ${
                    post.isPublished
                      ? 'border-emerald-500/30 bg-emerald-950/10'
                      : post.status === 'FAILED'
                      ? 'border-red-500/40 bg-red-950/10'
                      : 'border-slate-800 bg-slate-950/60 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <Badge variant={post.platform === 'linkedin' ? 'info' : 'neutral'} className="text-[10px]">
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
                      {post.isPublished ? 'PUBLIÉ' : post.status}
                    </Badge>
                  </div>

                  <p className="text-xs text-slate-200 line-clamp-2 font-medium mb-3">
                    {post.body_snippet || 'Publication sans texte'}
                  </p>

                  <div className="flex items-center justify-between pt-2 border-t border-slate-800/80 text-xs text-slate-400">
                    <span className="font-mono text-[11px] text-cyan-400">
                      {date.toLocaleString('fr-FR', {
                        day: 'numeric',
                        month: 'short',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>

                    {canEdit && !post.isPublished && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setSelectedPost(post);
                          setNewDateStr(
                            post.scheduled_at
                              ? new Date(post.scheduled_at).toISOString().slice(0, 16)
                              : new Date().toISOString().slice(0, 16)
                          );
                        }}
                        className="text-[11px] text-cyan-400 hover:text-cyan-300 py-0.5 px-2"
                      >
                        Reprogrammer
                      </Button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Reschedule Modal */}
      {selectedPost && (
        <Dialog
          isOpen={true}
          onClose={() => setSelectedPost(null)}
          title="Reprogrammer la publication"
        >
          <div className="space-y-4">
            <p className="text-xs text-slate-300">
              Choisissez le nouvel horaire de diffusion. Le système analyse les conflits temporels.
            </p>

            <div>
              <label className="block text-xs font-semibold uppercase text-slate-400 mb-1">
                Date et Heure (Local)
              </label>
              <Input
                type="datetime-local"
                value={newDateStr}
                onChange={(e) => {
                  setNewDateStr(e.target.value);
                  checkCollision(e.target.value, selectedPost.job_id);
                }}
              />
            </div>

            {collisionWarning && (
              <div className="flex items-center gap-2 rounded-lg border border-amber-500/30 bg-amber-950/30 p-3 text-xs text-amber-300">
                <AlertTriangle className="h-4 w-4 shrink-0 text-amber-400" />
                <span>{collisionWarning}</span>
              </div>
            )}

            <div className="flex items-center justify-between pt-4 border-t border-slate-800">
              {selectedPost.job_id && (
                <Button
                  variant="danger"
                  size="sm"
                  onClick={() => handleCancelJob(selectedPost.job_id!)}
                >
                  Annuler le job
                </Button>
              )}
              <div className="flex gap-2 ml-auto">
                <Button variant="ghost" onClick={() => setSelectedPost(null)}>
                  Fermer
                </Button>
                <Button
                  variant="primary"
                  isLoading={isRescheduling}
                  onClick={handleReschedule}
                >
                  Confirmer
                </Button>
              </div>
            </div>
          </div>
        </Dialog>
      )}
    </div>
  );
};
