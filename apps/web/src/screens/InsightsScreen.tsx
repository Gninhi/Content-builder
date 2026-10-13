import React, { useState, useEffect } from 'react';
import { useLanguage } from '../context/LanguageContext';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { apiClient } from '../lib/api';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { Skeleton } from '../components/common/Skeleton';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorState } from '../components/common/ErrorState';
import {
  Clock,
  Sparkles,
  BarChart3,
  Lightbulb,
} from 'lucide-react';

interface Insight {
  pillar: string;
  fact: string;
  hypothesis: string;
  confidence_level: number;
  recommended_action: string;
}

export const InsightsScreen: React.FC = () => {
  const { t, language } = useLanguage();
  const { session } = useAuth();
  const { showToast } = useToast();
  const isEn = language === 'en';

  const [period, setPeriod] = useState<'7d' | '30d' | '90d'>('7d');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [analytics, setAnalytics] = useState<any>(null);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [generatingInsights, setGeneratingInsights] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient<any>('/v1/analytics/overview');
      setAnalytics(data);
    } catch (err: any) {
      setError(err.message || (isEn ? 'Failed to fetch analytics.' : 'Impossible de récupérer les statistiques.'));
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateInsights = async () => {
    setGeneratingInsights(true);
    try {
      const res = await apiClient<{ insights: Insight[] }>('/v1/strategy/insights', {
        method: 'POST',
        body: JSON.stringify({
          workspace_id: session?.workspace_id || 'ws_default',
        }),
      });
      setInsights(res.insights || []);
      showToast('success', isEn ? 'Strategic insights updated by LangGraph agent!' : 'Recommandations stratégiques générées par l’agent LangGraph !');
    } catch (err: any) {
      showToast('error', `Erreur d'analyse stratégique : ${err.message}`);
    } finally {
      setGeneratingInsights(false);
    }
  };

  useEffect(() => {
    fetchData();
    handleGenerateInsights();
  }, [session?.workspace_id]);

  if (loading && !analytics) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Skeleton className="h-28 w-full rounded-xl" />
          <Skeleton className="h-28 w-full rounded-xl" />
          <Skeleton className="h-28 w-full rounded-xl" />
          <Skeleton className="h-28 w-full rounded-xl" />
        </div>
      </div>
    );
  }

  if (error && !analytics) {
    return <ErrorState message={error} onRetry={fetchData} />;
  }

  return (
    <div className="space-y-6 sm:space-y-8 w-full">
      {/* Top Header & Period Selector */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border-default pb-4">
        <div>
          <h2 className="text-lg sm:text-xl font-bold text-txt-primary tracking-tight">
            {t.insights.title}
          </h2>
          <p className="text-xs text-txt-muted mt-0.5">
            {isEn
              ? 'Audience analytics, engagement metrics and agentic editorial recommendations.'
              : 'Analyse des performances de contenu et recommandations tactiques de l’agent éditorial.'}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center rounded-md border border-border-default bg-surface-subtle p-0.5 text-xs font-mono">
            {(['7d', '30d', '90d'] as const).map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => setPeriod(p)}
                className={`rounded px-3 py-1 font-medium transition-colors ${
                  period === p
                    ? 'bg-accent text-txt-inverse font-bold shadow-xs'
                    : 'text-txt-muted hover:text-txt-primary'
                }`}
              >
                {p === '7d' ? (isEn ? '7 Days' : '7 Jours') : p === '30d' ? (isEn ? '30 Days' : '30 Jours') : (isEn ? '90 Days' : '90 Jours')}
              </button>
            ))}
          </div>

          <Button
            variant="secondary"
            size="sm"
            isLoading={generatingInsights}
            onClick={handleGenerateInsights}
            className="flex items-center gap-1.5 text-xs min-h-[36px]"
          >
            <Sparkles className="h-3.5 w-3.5 text-accent" />
            <span>{isEn ? 'Refresh Insights' : 'Actualiser les Insights'}</span>
          </Button>
        </div>
      </div>

      {/* Overview Analytics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5 sm:gap-4">
        <div className="rounded-xl border border-border-default bg-surface p-4 sm:p-5 shadow-xs">
          <span className="text-xs font-medium text-txt-muted block">
            {isEn ? 'Total Impressions' : 'Impressions Totales'}
          </span>
          <span className="text-2xl font-bold text-txt-primary mt-1 block font-mono">
            {analytics?.total_impressions?.toLocaleString(language === 'fr' ? 'fr-FR' : 'en-US') || '0'}
          </span>
          <span className="text-[11px] text-accent-text mt-1 block font-medium">
            {isEn ? 'Tracked over period' : 'Mesurées sur la période'}
          </span>
        </div>

        <div className="rounded-xl border border-border-default bg-surface p-4 sm:p-5 shadow-xs">
          <span className="text-xs font-medium text-txt-muted block">
            {isEn ? 'Engagement Rate' : 'Taux d’Engagement'}
          </span>
          <span className="text-2xl font-bold text-status-success-text mt-1 block font-mono">
            {analytics?.average_engagement_rate ? `${analytics.average_engagement_rate}%` : '0.0%'}
          </span>
          <span className="text-[11px] text-txt-muted mt-1 block">
            {isEn ? 'Interactions / Impressions' : 'Interactions / Impressions'}
          </span>
        </div>

        <div className="rounded-xl border border-border-default bg-surface p-4 sm:p-5 shadow-xs">
          <span className="text-xs font-medium text-txt-muted block">
            {isEn ? 'Clicks & Conversions' : 'Clics & Conversions'}
          </span>
          <span className="text-2xl font-bold text-txt-primary mt-1 block font-mono">
            {analytics?.total_clicks || 0}
          </span>
          <span className="text-[11px] text-txt-muted mt-1 block">
            {isEn ? 'On shared trackable links' : 'Sur les liens intégrés'}
          </span>
        </div>

        <div className="rounded-xl border border-border-default bg-surface p-4 sm:p-5 shadow-xs">
          <span className="text-xs font-medium text-txt-muted block">
            {isEn ? 'Published Volume' : 'Volume Publié'}
          </span>
          <span className="text-2xl font-bold text-txt-primary mt-1 block font-mono">
            {analytics?.published_posts_count || 0}
          </span>
          <span className="text-[11px] text-txt-muted mt-1 block">
            {isEn ? 'Successfully broadcasted' : 'Postés avec succès'}
          </span>
        </div>
      </div>

      {/* Best Slots & Platform Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-xl border border-border-default bg-surface p-5 sm:p-6 space-y-4 shadow-subtle">
          <div className="flex items-center gap-2 text-txt-primary font-semibold text-sm">
            <Clock className="h-4 w-4 text-accent" />
            <span>{t.insights.optimal_slots_title}</span>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between p-3.5 rounded-lg border border-border-subtle bg-surface-subtle transition-colors hover:border-border-default">
              <div>
                <span className="text-xs sm:text-sm font-semibold text-txt-primary">
                  {isEn ? 'Tuesday & Thursday — 08:30 UTC' : 'Mardi & Jeudi — 08:30 UTC'}
                </span>
                <p className="text-xs text-txt-muted">
                  {isEn ? 'B2B Tech / Decision Makers' : 'Audience B2B Tech / Dirigeants'}
                </p>
              </div>
              <Badge variant="success" className="text-xs font-medium">
                +42% Engagement
              </Badge>
            </div>

            <div className="flex items-center justify-between p-3.5 rounded-lg border border-border-subtle bg-surface-subtle transition-colors hover:border-border-default">
              <div>
                <span className="text-xs sm:text-sm font-semibold text-txt-primary">
                  {isEn ? 'Wednesday — 14:00 UTC' : 'Mercredi — 14:00 UTC'}
                </span>
                <p className="text-xs text-txt-muted">
                  {isEn ? 'In-depth case studies' : 'Retours d’expérience approfondis'}
                </p>
              </div>
              <Badge variant="info" className="text-xs font-medium">
                +28% Clics
              </Badge>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-border-default bg-surface p-5 sm:p-6 space-y-4 shadow-subtle">
          <div className="flex items-center gap-2 text-txt-primary font-semibold text-sm">
            <BarChart3 className="h-4 w-4 text-accent" />
            <span>{t.insights.platform_breakdown_title}</span>
          </div>

          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-xs text-txt-secondary mb-1.5 font-mono">
                <span className="font-semibold">LinkedIn</span>
                <span>65% {isEn ? 'traffic share' : 'du trafic'}</span>
              </div>
              <div className="w-full bg-surface-subtle rounded-full h-2 border border-border-subtle overflow-hidden">
                <div className="bg-accent h-2 rounded-full" style={{ width: '65%' }} />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs text-txt-secondary mb-1.5 font-mono">
                <span className="font-semibold">X (Twitter)</span>
                <span>35% {isEn ? 'traffic share' : 'du trafic'}</span>
              </div>
              <div className="w-full bg-surface-subtle rounded-full h-2 border border-border-subtle overflow-hidden">
                <div className="bg-accent/70 h-2 rounded-full" style={{ width: '35%' }} />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Agent Strategy Recommendations */}
      <div className="rounded-xl border border-border-default bg-surface p-5 sm:p-6 space-y-4 shadow-subtle">
        <div className="flex items-center gap-2 text-txt-primary font-semibold text-sm">
          <Lightbulb className="h-4 w-4 text-accent" />
          <span>{t.insights.recommendations_title}</span>
        </div>

        {insights.length === 0 ? (
          <EmptyState
            title={isEn ? 'No strategic recommendations yet' : 'Aucune recommandation pour l’instant'}
            description={
              isEn
                ? 'Generate posts and collect engagement metrics to enable automated strategic feedback loops.'
                : t.insights.empty_insights
            }
            actionLabel={isEn ? 'Generate Insights' : 'Générer des recommandations'}
            onAction={handleGenerateInsights}
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {insights.map((ins, idx) => (
              <div
                key={idx}
                className="rounded-lg border border-border-subtle bg-surface-subtle p-4 sm:p-5 space-y-3 hover:border-border-default transition-colors"
              >
                <div className="flex items-center justify-between">
                  <Badge variant="info" className="text-[10px]">
                    {ins.pillar}
                  </Badge>
                  <span className="text-[11px] font-mono text-status-success-text font-semibold">
                    {isEn ? 'Confidence:' : 'Confiance :'} {Math.round(ins.confidence_level * 100)}%
                  </span>
                </div>

                <div>
                  <h4 className="text-xs font-semibold text-txt-muted mb-1">
                    {isEn ? 'Observed Hypothesis' : 'Hypothèse observée'}
                  </h4>
                  <p className="text-xs text-txt-primary leading-relaxed">
                    {ins.hypothesis}
                  </p>
                </div>

                <div className="pt-2 border-t border-border-subtle">
                  <h4 className="text-xs font-semibold text-accent-text mb-1">
                    {isEn ? 'Recommended Action' : 'Action Recommandée'}
                  </h4>
                  <p className="text-xs text-txt-secondary font-medium leading-relaxed">
                    {ins.recommended_action}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
