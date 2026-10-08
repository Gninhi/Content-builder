import React, { useState, useEffect } from 'react';
import { useLanguage } from '../context/LanguageContext';
import { useAuth } from '../context/AuthContext';
import { apiClient } from '../lib/api';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';
import { Skeleton } from '../components/common/Skeleton';
import { ErrorState } from '../components/common/ErrorState';
import {
  Inbox,
  Calendar,
  CheckCircle2,
  AlertTriangle,
  Zap,
  Share2,
  ArrowRight,
  Cpu,
  ShieldAlert,
} from 'lucide-react';
import { InboxVariant } from '../types/api';

interface DashboardScreenProps {
  onNavigate: (screen: string) => void;
}

export const DashboardScreen: React.FC<DashboardScreenProps> = ({ onNavigate }) => {
  const { t } = useLanguage();
  const { session } = useAuth();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [inboxCount, setInboxCount] = useState(0);
  const [scheduledCount, setScheduledCount] = useState(0);
  const [publishedCount, setPublishedCount] = useState(0);
  const [failedCount, setFailedCount] = useState(0);
  const [degradedCount, setDegradedCount] = useState(0);
  const [llmBudgetSpent, setLlmBudgetSpent] = useState(0.42);
  const [llmLimit] = useState(10.0);

  const [linkedInStatus, setLinkedInStatus] = useState<'connected' | 'disconnected'>('disconnected');
  const [xStatus, setXStatus] = useState<'connected' | 'disconnected'>('disconnected');
  const [nextScheduled, setNextScheduled] = useState<any[]>([]);

  const fetchDashboardData = async () => {
    setLoading(true);
    setError(null);
    try {
      // 1. Fetch inbox
      const inbox = await apiClient<InboxVariant[]>('/v1/inbox');
      setInboxCount(Array.isArray(inbox) ? inbox.length : 0);

      // Check degraded variants in inbox
      const degraded = Array.isArray(inbox)
        ? inbox.filter((item) => Boolean(item.is_degraded)).length
        : 0;
      setDegradedCount(degraded);

      // 2. Fetch calendar
      const cal = await apiClient<{ scheduled: any[]; published: any[] }>('/v1/calendar');
      const scheduled = cal.scheduled || [];
      const published = cal.published || [];
      setScheduledCount(scheduled.length);
      setNextScheduled(scheduled.slice(0, 3));

      // Calculate failed or unknown jobs
      const failed = scheduled.filter(
        (s) => s.status === 'FAILED' || s.status === 'PUBLISH_UNKNOWN'
      ).length;
      setFailedCount(failed);

      // 3. Fetch analytics overview
      const analytics = await apiClient<any>('/v1/analytics/overview');
      setPublishedCount(analytics.published_posts_count || published.length || 0);
      if (analytics.llm_budget_spent !== undefined) {
        setLlmBudgetSpent(analytics.llm_budget_spent);
      }

      // 4. Fetch social accounts
      const accountsRes = await apiClient<{ accounts: any[] }>('/v1/oauth/accounts');
      const accounts = accountsRes.accounts || [];
      const hasLinkedIn = accounts.some(
        (a) => a.provider?.toLowerCase() === 'linkedin' && (a.status === 'ACTIVE' || a.status === 'connected')
      );
      const hasX = accounts.some(
        (a) => a.provider?.toLowerCase() === 'x' && (a.status === 'ACTIVE' || a.status === 'connected')
      );
      setLinkedInStatus(hasLinkedIn ? 'connected' : 'disconnected');
      setXStatus(hasX ? 'connected' : 'disconnected');
    } catch (err: any) {
      setError(err.message || 'Erreur lors du chargement des indicateurs.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, [session?.workspace_id]);

  if (error) {
    return <ErrorState message={error} onRetry={fetchDashboardData} />;
  }

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Top Banner / Welcome & Quick action */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 via-slate-900/90 to-cyan-950/30 p-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs uppercase font-mono font-bold tracking-wider text-cyan-400">
              {t.dashboard.title}
            </span>
            <Badge variant="warning" className="text-[10px] uppercase font-bold">
              {t.header.sandbox_mode}
            </Badge>
          </div>
          <h2 className="text-xl md:text-2xl font-bold text-white tracking-tight">
            Espace Éditorial {session?.workspace_id || 'ws_default'}
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Gouvernance déterministe avec validation humaine obligatoire (HITL) avant toute publication.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <Button
            variant="primary"
            onClick={() => onNavigate('inbox')}
            className="flex items-center gap-2"
          >
            <span>{t.nav.inbox}</span>
            {inboxCount > 0 && (
              <Badge variant="warning" className="px-1.5 py-0 text-xs">
                {inboxCount}
              </Badge>
            )}
            <ArrowRight className="h-4 w-4" />
          </Button>
          <Button
            variant="secondary"
            onClick={() => onNavigate('ideation')}
            className="flex items-center gap-2"
          >
            <span>{t.nav.ideation}</span>
            <Zap className="h-4 w-4 text-cyan-400" />
          </Button>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        {/* 1. Pending HITL */}
        <div className="rounded-xl border border-amber-500/30 bg-amber-950/10 p-5 shadow-sm">
          <div className="flex items-center justify-between text-amber-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">
              {t.dashboard.kpi_pending_review}
            </span>
            <Inbox className="h-4 w-4" />
          </div>
          <div className="text-3xl font-extrabold text-white">
            {loading ? <Skeleton className="h-8 w-14" /> : inboxCount}
          </div>
          <p className="text-[11px] text-amber-400/80 mt-1">
            Action humaine requise
          </p>
        </div>

        {/* 2. Scheduled */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 shadow-sm">
          <div className="flex items-center justify-between text-cyan-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">
              {t.dashboard.kpi_scheduled}
            </span>
            <Calendar className="h-4 w-4" />
          </div>
          <div className="text-3xl font-extrabold text-white">
            {loading ? <Skeleton className="h-8 w-14" /> : scheduledCount}
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            Dans la file d'attente
          </p>
        </div>

        {/* 3. Published (7d) */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 shadow-sm">
          <div className="flex items-center justify-between text-emerald-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">
              {t.dashboard.kpi_published_7d}
            </span>
            <CheckCircle2 className="h-4 w-4" />
          </div>
          <div className="text-3xl font-extrabold text-white">
            {loading ? <Skeleton className="h-8 w-14" /> : publishedCount}
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            Validés & diffusés
          </p>
        </div>

        {/* 4. Failed / Unknown */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 shadow-sm">
          <div className="flex items-center justify-between text-red-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">
              {t.dashboard.kpi_failed_unknown}
            </span>
            <AlertTriangle className="h-4 w-4" />
          </div>
          <div className="text-3xl font-extrabold text-white">
            {loading ? <Skeleton className="h-8 w-14" /> : failedCount}
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            Échecs de diffusion
          </p>
        </div>

        {/* 5. LLM Budget */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 shadow-sm">
          <div className="flex items-center justify-between text-purple-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">
              {t.dashboard.kpi_llm_budget}
            </span>
            <Cpu className="h-4 w-4" />
          </div>
          <div className="text-2xl font-bold text-white">
            {loading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              `$${llmBudgetSpent.toFixed(2)}`
            )}
          </div>
          <div className="w-full bg-slate-800 rounded-full h-1.5 mt-2 overflow-hidden">
            <div
              className="bg-purple-500 h-1.5 rounded-full"
              style={{ width: `${Math.min(100, (llmBudgetSpent / llmLimit) * 100)}%` }}
            />
          </div>
          <p className="text-[10px] text-slate-400 mt-1">
            Plafond mensuel: ${llmLimit}
          </p>
        </div>

        {/* 6. Degraded */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 shadow-sm">
          <div className="flex items-center justify-between text-yellow-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">
              {t.dashboard.kpi_degraded}
            </span>
            <ShieldAlert className="h-4 w-4" />
          </div>
          <div className="text-3xl font-extrabold text-white">
            {loading ? <Skeleton className="h-8 w-14" /> : degradedCount}
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            Sources ou LLM partiels
          </p>
        </div>
      </div>

      {/* Middle Grid: Social Connections + Upcoming Publications */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Accounts Status */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-semibold text-white">
              {t.dashboard.social_status_title}
            </h3>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onNavigate('connections')}
              className="text-cyan-400 hover:text-cyan-300 text-xs"
            >
              Gérer
            </Button>
          </div>

          <div className="space-y-3">
            {/* LinkedIn */}
            <div className="flex items-center justify-between p-3 rounded-xl border border-slate-800 bg-slate-950/40">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#0077b5]/20 text-[#0077b5] border border-[#0077b5]/30">
                  <Share2 className="h-4 w-4" />
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-slate-200">LinkedIn</h4>
                  <p className="text-xs text-slate-400">OAuth 2.0 PKCE</p>
                </div>
              </div>
              <Badge variant={linkedInStatus === 'connected' ? 'success' : 'neutral'}>
                {linkedInStatus === 'connected' ? 'Connecté' : 'Non connecté'}
              </Badge>
            </div>

            {/* X */}
            <div className="flex items-center justify-between p-3 rounded-xl border border-slate-800 bg-slate-950/40">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-800 text-white border border-slate-700">
                  <span className="font-bold text-sm">𝕏</span>
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-slate-200">X (Twitter)</h4>
                  <p className="text-xs text-slate-400">OAuth 2.0 PKCE</p>
                </div>
              </div>
              <Badge variant={xStatus === 'connected' ? 'success' : 'neutral'}>
                {xStatus === 'connected' ? 'Connecté' : 'Non connecté'}
              </Badge>
            </div>
          </div>
        </div>

        {/* Right: Next Scheduled Publications */}
        <div className="lg:col-span-2 rounded-2xl border border-slate-800 bg-slate-900/50 p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-semibold text-white">
              {t.dashboard.upcoming_title}
            </h3>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onNavigate('calendar')}
              className="text-cyan-400 hover:text-cyan-300 text-xs"
            >
              Voir le calendrier
            </Button>
          </div>

          {loading ? (
            <div className="space-y-3">
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
            </div>
          ) : nextScheduled.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-800 p-8 text-center text-slate-400 text-sm">
              Aucune publication planifiée. Validez des brouillons dans la revue HITL pour alimenter le calendrier.
            </div>
          ) : (
            <div className="space-y-3">
              {nextScheduled.map((item, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-4 rounded-xl border border-slate-800 bg-slate-950/40 hover:border-slate-700 transition-colors"
                >
                  <div className="flex items-center gap-3 overflow-hidden">
                    <Badge variant={item.platform === 'linkedin' ? 'info' : 'neutral'}>
                      {item.platform?.toUpperCase() || 'MULTI'}
                    </Badge>
                    <p className="text-sm text-slate-300 truncate max-w-md font-medium">
                      {item.body_snippet || 'Publication programmée'}
                    </p>
                  </div>
                  <div className="text-right shrink-0">
                    <span className="text-xs font-mono text-cyan-400">
                      {new Date(item.scheduled_at).toLocaleDateString('fr-FR', {
                        day: 'numeric',
                        month: 'short',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
