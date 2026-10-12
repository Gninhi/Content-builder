import React, { useState, useEffect } from 'react';
import { useLanguage } from '../context/LanguageContext';
import { useAuth } from '../context/AuthContext';
import { apiClient } from '../lib/api';
import { formatDateTime } from '../lib/date';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';
import { Skeleton } from '../components/common/Skeleton';
import { ErrorState } from '../components/common/ErrorState';
import { EmptyState } from '../components/common/EmptyState';
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
  Shield,
} from 'lucide-react';
import { InboxVariant } from '../types/api';

interface DashboardScreenProps {
  onNavigate: (screen: string) => void;
}

export const DashboardScreen: React.FC<DashboardScreenProps> = ({ onNavigate }) => {
  const { t, language } = useLanguage();
  const { session, workspaces } = useAuth();
  const isEn = language === 'en';

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

  const currentWorkspaceName =
    workspaces.find((w) => w.workspace_id === session?.workspace_id)?.name ||
    session?.workspace_id ||
    (isEn ? 'Main Workspace' : 'Workspace Principal');

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
    <div className="space-y-6 sm:space-y-8 w-full">
      {/* Top Banner / Welcome & Quick action */}
      <div className="relative overflow-hidden rounded-xl border border-border-default bg-surface-elevated p-5 sm:p-6 shadow-subtle transition-colors duration-150">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-5 relative z-10">
          <div>
            <div className="flex items-center gap-2 mb-1.5 flex-wrap">
              <span className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-accent-text">
                <Shield className="h-3.5 w-3.5 text-accent" />
                {t.dashboard.title}
              </span>
              <Badge variant="warning" className="text-[10px] font-medium">
                {t.header.sandbox_mode}
              </Badge>
              <span className="text-[11px] text-txt-muted font-mono hidden sm:inline">
                • SHA-256 Cryptographic Vault
              </span>
            </div>
            <h2 className="text-xl sm:text-2xl font-bold text-txt-primary tracking-tight">
              {isEn ? 'Editorial Workspace' : 'Espace Éditorial'}{' '}
              <span className="text-accent-text font-semibold">{currentWorkspaceName}</span>
            </h2>
            <p className="text-xs sm:text-sm text-txt-secondary mt-1 max-w-2xl leading-relaxed">
              {isEn
                ? 'Deterministic governance with mandatory Human-In-The-Loop (HITL) validation prior to cryptographic sealing and broadcasting.'
                : 'Gouvernance déterministe avec validation humaine obligatoire (HITL) avant tout scellement cryptographique et diffusion.'}
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5 sm:gap-3 shrink-0">
            <Button
              variant="primary"
              onClick={() => onNavigate('inbox')}
              className="flex items-center justify-center gap-2 min-h-[44px]"
            >
              <span>{t.nav.inbox}</span>
              {inboxCount > 0 && (
                <Badge variant="warning" className="px-1.5 py-0 text-xs font-bold">
                  {inboxCount}
                </Badge>
              )}
              <ArrowRight className="h-4 w-4" />
            </Button>
            <Button
              variant="secondary"
              onClick={() => onNavigate('ideation')}
              className="flex items-center justify-center gap-2 min-h-[44px]"
            >
              <span>{t.nav.ideation}</span>
              <Zap className="h-4 w-4 text-accent" />
            </Button>
          </div>
        </div>
      </div>

      {/* KPI Cards Grid — Responsive 1 to 6 columns */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3.5 sm:gap-4">
        {/* 1. Pending HITL */}
        <div className="rounded-xl border border-border-default bg-surface p-4 sm:p-5 shadow-xs transition-colors hover:border-border-hover">
          <div className="flex items-center justify-between text-status-warning-text mb-2">
            <span className="text-xs font-medium text-txt-muted">
              {t.dashboard.kpi_pending_review}
            </span>
            <Inbox className="h-4 w-4" />
          </div>
          <div className="text-2xl sm:text-3xl font-bold text-txt-primary font-mono">
            {loading ? <Skeleton className="h-8 w-14" /> : inboxCount}
          </div>
          <p className="text-[11px] text-status-warning-text mt-1.5 font-medium">
            {isEn ? 'Human action required' : 'Action humaine requise'}
          </p>
        </div>

        {/* 2. Scheduled */}
        <div className="rounded-xl border border-border-default bg-surface p-4 sm:p-5 shadow-xs transition-colors hover:border-border-hover">
          <div className="flex items-center justify-between text-txt-secondary mb-2">
            <span className="text-xs font-medium text-txt-muted">
              {t.dashboard.kpi_scheduled}
            </span>
            <Calendar className="h-4 w-4 text-accent" />
          </div>
          <div className="text-2xl sm:text-3xl font-bold text-txt-primary font-mono">
            {loading ? <Skeleton className="h-8 w-14" /> : scheduledCount}
          </div>
          <p className="text-[11px] text-txt-muted mt-1.5">
            {isEn ? 'In editorial queue' : 'Dans la file d’attente'}
          </p>
        </div>

        {/* 3. Published (7d) */}
        <div className="rounded-xl border border-border-default bg-surface p-4 sm:p-5 shadow-xs transition-colors hover:border-border-hover">
          <div className="flex items-center justify-between text-status-success-text mb-2">
            <span className="text-xs font-medium text-txt-muted">
              {t.dashboard.kpi_published_7d}
            </span>
            <CheckCircle2 className="h-4 w-4" />
          </div>
          <div className="text-2xl sm:text-3xl font-bold text-txt-primary font-mono">
            {loading ? <Skeleton className="h-8 w-14" /> : publishedCount}
          </div>
          <p className="text-[11px] text-status-success-text mt-1.5">
            {isEn ? 'Validated & broadcasted' : 'Validés & diffusés'}
          </p>
        </div>

        {/* 4. Failed / Unknown */}
        <div className="rounded-xl border border-border-default bg-surface p-4 sm:p-5 shadow-xs transition-colors hover:border-border-hover">
          <div className="flex items-center justify-between text-status-danger-text mb-2">
            <span className="text-xs font-medium text-txt-muted">
              {t.dashboard.kpi_failed_unknown}
            </span>
            <AlertTriangle className="h-4 w-4" />
          </div>
          <div className="text-2xl sm:text-3xl font-bold text-txt-primary font-mono">
            {loading ? <Skeleton className="h-8 w-14" /> : failedCount}
          </div>
          <p className="text-[11px] text-status-danger-text mt-1.5">
            {isEn ? 'Broadcast issues' : 'Échecs de diffusion'}
          </p>
        </div>

        {/* 5. LLM Budget */}
        <div className="rounded-xl border border-border-default bg-surface p-4 sm:p-5 shadow-xs transition-colors hover:border-border-hover">
          <div className="flex items-center justify-between text-accent-text mb-2">
            <span className="text-xs font-medium text-txt-muted">
              {t.dashboard.kpi_llm_budget}
            </span>
            <Cpu className="h-4 w-4 text-accent" />
          </div>
          <div className="text-2xl font-bold text-txt-primary font-mono">
            {loading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              `$${llmBudgetSpent.toFixed(2)}`
            )}
          </div>
          <div className="w-full bg-surface-subtle rounded-full h-1.5 mt-2.5 overflow-hidden border border-border-subtle">
            <div
              className="bg-accent h-1.5 rounded-full transition-all"
              style={{ width: `${Math.min(100, (llmBudgetSpent / llmLimit) * 100)}%` }}
            />
          </div>
          <p className="text-[11px] text-txt-muted mt-1 font-mono">
            {isEn ? `Cap: $${llmLimit}` : `Plafond: $${llmLimit}`}
          </p>
        </div>

        {/* 6. Degraded */}
        <div className="rounded-xl border border-border-default bg-surface p-4 sm:p-5 shadow-xs transition-colors hover:border-border-hover">
          <div className="flex items-center justify-between text-status-warning-text mb-2">
            <span className="text-xs font-medium text-txt-muted">
              {t.dashboard.kpi_degraded}
            </span>
            <ShieldAlert className="h-4 w-4" />
          </div>
          <div className="text-2xl sm:text-3xl font-bold text-txt-primary font-mono">
            {loading ? <Skeleton className="h-8 w-14" /> : degradedCount}
          </div>
          <p className="text-[11px] text-txt-muted mt-1.5">
            {isEn ? 'Partial LLM / sources' : 'Sources ou LLM partiels'}
          </p>
        </div>
      </div>

      {/* Middle Grid: Social Connections + Upcoming Publications */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Accounts Status */}
        <div className="rounded-xl border border-border-default bg-surface p-5 sm:p-6 space-y-4 shadow-subtle">
          <div className="flex items-center justify-between">
            <h3 className="text-sm sm:text-base font-semibold text-txt-primary tracking-tight">
              {t.dashboard.social_status_title}
            </h3>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onNavigate('connections')}
              className="text-xs min-h-[36px]"
            >
              {isEn ? 'Manage' : 'Gérer'}
            </Button>
          </div>

          <div className="space-y-3">
            {/* LinkedIn */}
            <div className="flex items-center justify-between p-3.5 rounded-lg border border-border-subtle bg-surface-subtle transition-colors hover:border-border-default">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-md bg-accent-subtle text-accent-text border border-accent-border">
                  <Share2 className="h-4 w-4" />
                </div>
                <div>
                  <h4 className="text-xs sm:text-sm font-semibold text-txt-primary">LinkedIn</h4>
                  <p className="text-[11px] text-txt-muted font-mono">OAuth 2.0 PKCE</p>
                </div>
              </div>
              <Badge variant={linkedInStatus === 'connected' ? 'success' : 'neutral'} className="text-[11px]">
                {linkedInStatus === 'connected' ? (isEn ? 'Connected' : 'Connecté') : (isEn ? 'Disconnected' : 'Non connecté')}
              </Badge>
            </div>

            {/* X */}
            <div className="flex items-center justify-between p-3.5 rounded-lg border border-border-subtle bg-surface-subtle transition-colors hover:border-border-default">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-md bg-surface text-txt-primary border border-border-default">
                  <span className="font-bold text-sm">𝕏</span>
                </div>
                <div>
                  <h4 className="text-xs sm:text-sm font-semibold text-txt-primary">X (Twitter)</h4>
                  <p className="text-[11px] text-txt-muted font-mono">OAuth 2.0 PKCE</p>
                </div>
              </div>
              <Badge variant={xStatus === 'connected' ? 'success' : 'neutral'} className="text-[11px]">
                {xStatus === 'connected' ? (isEn ? 'Connected' : 'Connecté') : (isEn ? 'Disconnected' : 'Non connecté')}
              </Badge>
            </div>
          </div>
        </div>

        {/* Right: Next Scheduled Publications */}
        <div className="lg:col-span-2 rounded-xl border border-border-default bg-surface p-5 sm:p-6 space-y-4 shadow-subtle">
          <div className="flex items-center justify-between">
            <h3 className="text-sm sm:text-base font-semibold text-txt-primary tracking-tight">
              {t.dashboard.upcoming_title}
            </h3>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onNavigate('calendar')}
              className="text-xs min-h-[36px]"
            >
              {isEn ? 'View calendar' : 'Voir le calendrier'}
            </Button>
          </div>

          {loading ? (
            <div className="space-y-3">
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
            </div>
          ) : nextScheduled.length === 0 ? (
            <EmptyState
              title={isEn ? 'No scheduled publications' : 'Aucune publication planifiée'}
              description={
                isEn
                  ? 'Approve drafts in the HITL review to populate the editorial calendar.'
                  : 'Validez des brouillons dans la revue HITL pour alimenter le calendrier.'
              }
              actionLabel={t.nav.inbox}
              onAction={() => onNavigate('inbox')}
            />
          ) : (
            <div className="space-y-3">
              {nextScheduled.map((item, idx) => (
                <div
                  key={idx}
                  className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 p-3.5 sm:p-4 rounded-lg border border-border-subtle bg-surface-subtle hover:border-border-default transition-colors"
                >
                  <div className="flex items-center gap-3 overflow-hidden">
                    <Badge variant={item.platform === 'linkedin' ? 'info' : 'neutral'} className="text-[10px] uppercase font-mono">
                      {item.platform?.toUpperCase() || 'MULTI'}
                    </Badge>
                    <p className="text-xs sm:text-sm text-txt-primary truncate max-w-md font-medium">
                      {item.body_snippet || (isEn ? 'Scheduled post' : 'Publication programmée')}
                    </p>
                  </div>
                  <div className="text-left sm:text-right shrink-0">
                    <span className="text-[11px] sm:text-xs font-mono text-txt-muted">
                      {formatDateTime(item.scheduled_at, language)}
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
