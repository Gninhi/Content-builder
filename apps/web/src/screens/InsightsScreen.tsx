import React, { useState, useEffect } from 'react';
import { useLanguage } from '../context/LanguageContext';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { apiClient } from '../lib/api';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { Skeleton } from '../components/common/Skeleton';
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
  const { t } = useLanguage();
  const { session } = useAuth();
  const { showToast } = useToast();

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
      setError(err.message || 'Impossible de récupérer les statistiques.');
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
      showToast('success', 'Recommandations stratégiques générées par l’agent LangGraph !');
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

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
        </div>
      </div>
    );
  }

  if (error) {
    return <ErrorState message={error} onRetry={fetchData} />;
  }

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Top Header & Period Selector */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">
            {t.insights.title}
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Analyse des performances de contenu et recommandations tactiques de l'agent éditorial.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center rounded-lg border border-slate-700 bg-slate-800 p-0.5 text-xs">
            {(['7d', '30d', '90d'] as const).map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => setPeriod(p)}
                className={`rounded px-3 py-1 font-medium transition-colors ${
                  period === p
                    ? 'bg-cyan-500 text-slate-950 font-bold'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {p === '7d' ? '7 Jours' : p === '30d' ? '30 Jours' : '90 Jours'}
              </button>
            ))}
          </div>

          <Button
            variant="secondary"
            size="sm"
            isLoading={generatingInsights}
            onClick={handleGenerateInsights}
            className="flex items-center gap-1.5 text-xs"
          >
            <Sparkles className="h-3.5 w-3.5 text-cyan-400" />
            <span>Actualiser les Insights</span>
          </Button>
        </div>
      </div>

      {/* Overview Analytics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
          <span className="text-xs text-slate-400 uppercase font-mono block">Impressions Totales</span>
          <span className="text-2xl font-bold text-white mt-1 block">
            {analytics?.total_impressions?.toLocaleString('fr-FR') || '0'}
          </span>
          <span className="text-[11px] text-cyan-400 mt-1 block">Mesurées sur la période</span>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
          <span className="text-xs text-slate-400 uppercase font-mono block">Taux d'Engagement</span>
          <span className="text-2xl font-bold text-emerald-400 mt-1 block">
            {analytics?.average_engagement_rate ? `${analytics.average_engagement_rate}%` : '0.0%'}
          </span>
          <span className="text-[11px] text-slate-400 mt-1 block">Interactions / Impressions</span>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
          <span className="text-xs text-slate-400 uppercase font-mono block">Clics & Conversions</span>
          <span className="text-2xl font-bold text-cyan-400 mt-1 block">
            {analytics?.total_clicks || 0}
          </span>
          <span className="text-[11px] text-slate-400 mt-1 block">Sur les liens intégrés</span>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
          <span className="text-xs text-slate-400 uppercase font-mono block">Volume Publié</span>
          <span className="text-2xl font-bold text-white mt-1 block">
            {analytics?.published_posts_count || 0}
          </span>
          <span className="text-[11px] text-slate-400 mt-1 block">Postés avec succès</span>
        </div>
      </div>

      {/* Best Slots & Platform Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 space-y-4">
          <div className="flex items-center gap-2 text-white font-semibold text-sm">
            <Clock className="h-4 w-4 text-cyan-400" />
            <span>{t.insights.optimal_slots_title}</span>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between p-3.5 rounded-xl border border-slate-800 bg-slate-950/60">
              <div>
                <span className="text-sm font-semibold text-slate-200">Mardi & Jeudi — 08:30 UTC</span>
                <p className="text-xs text-slate-400">Audience B2B Tech / Dirigeants</p>
              </div>
              <Badge variant="success" className="text-xs">
                +42% Engagement
              </Badge>
            </div>

            <div className="flex items-center justify-between p-3.5 rounded-xl border border-slate-800 bg-slate-950/60">
              <div>
                <span className="text-sm font-semibold text-slate-200">Mercredi — 14:00 UTC</span>
                <p className="text-xs text-slate-400">Retours d'expérience approfondis</p>
              </div>
              <Badge variant="info" className="text-xs">
                +28% Clics
              </Badge>
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 space-y-4">
          <div className="flex items-center gap-2 text-white font-semibold text-sm">
            <BarChart3 className="h-4 w-4 text-cyan-400" />
            <span>{t.insights.platform_breakdown_title}</span>
          </div>

          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-xs text-slate-300 mb-1">
                <span className="font-semibold">LinkedIn</span>
                <span>65% du trafic</span>
              </div>
              <div className="w-full bg-slate-800 rounded-full h-2">
                <div className="bg-[#0077b5] h-2 rounded-full" style={{ width: '65%' }} />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs text-slate-300 mb-1">
                <span className="font-semibold">X (Twitter)</span>
                <span>35% du trafic</span>
              </div>
              <div className="w-full bg-slate-800 rounded-full h-2">
                <div className="bg-slate-400 h-2 rounded-full" style={{ width: '35%' }} />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Agent Strategy Recommendations */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 space-y-4">
        <div className="flex items-center gap-2 text-white font-semibold text-sm">
          <Lightbulb className="h-4 w-4 text-amber-400" />
          <span>{t.insights.recommendations_title}</span>
        </div>

        {insights.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-800 p-8 text-center text-slate-400 text-xs">
            {t.insights.empty_insights}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {insights.map((ins, idx) => (
              <div
                key={idx}
                className="rounded-xl border border-slate-800 bg-slate-950/60 p-5 space-y-3"
              >
                <div className="flex items-center justify-between">
                  <Badge variant="info" className="text-[10px]">
                    {ins.pillar}
                  </Badge>
                  <span className="text-[11px] font-mono text-emerald-400">
                    Confiance : {Math.round(ins.confidence_level * 100)}%
                  </span>
                </div>

                <div>
                  <h4 className="text-xs font-semibold uppercase text-slate-400 mb-1">
                    Hypothèse observée
                  </h4>
                  <p className="text-xs text-slate-200">
                    {ins.hypothesis}
                  </p>
                </div>

                <div className="pt-2 border-t border-slate-800/80">
                  <h4 className="text-xs font-semibold uppercase text-cyan-400 mb-1">
                    Action Recommandée
                  </h4>
                  <p className="text-xs text-slate-300 font-medium">
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
