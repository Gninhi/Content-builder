import React, { useState, useEffect } from 'react';
import { useLanguage } from '../context/LanguageContext';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { apiClient } from '../lib/api';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { Dialog } from '../components/common/Dialog';
import { Input } from '../components/common/Input';
import { Skeleton } from '../components/common/Skeleton';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorState } from '../components/common/ErrorState';
import {
  Sparkles,
  Plus,
  ArrowRight,
  AlertCircle,
  Loader2,
  TrendingUp,
} from 'lucide-react';

interface Idea {
  id: string;
  title: string;
  angle: string;
  pillar: string;
  audience: string[];
  evidence_refs?: any[];
  total_score?: number;
  novelty_score: number;
  relevance_score: number;
  effort_score: number;
  priority?: string;
  status: string;
}

export const IdeationScreen: React.FC = () => {
  const { t } = useLanguage();
  const { session, canEdit } = useAuth();
  const { showToast } = useToast();

  const [ideas, setIdeas] = useState<Idea[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Research modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [topic, setTopic] = useState('Agents IA autonomes et gouvernance en entreprise');
  const [targetCount, setTargetCount] = useState(3);
  const [researching, setResearching] = useState(false);
  const [researchStep, setResearchStep] = useState<string>('');
  const [degradedTavily, setDegradedTavily] = useState(false);

  // Generating draft state
  const [convertingId, setConvertingId] = useState<string | null>(null);

  const fetchIdeas = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient<Idea[]>(
        `/v1/ideas?workspace_id=${session?.workspace_id || 'ws_default'}`
      );
      setIdeas(Array.isArray(data) ? data : []);
    } catch (err: any) {
      setError(err.message || 'Impossible de charger les idées.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIdeas();
  }, [session?.workspace_id]);

  const handleLaunchResearch = async (e: React.FormEvent) => {
    e.preventDefault();
    setResearching(true);
    setResearchStep('Recherche de sources via Tavily / Base documentaire...');
    setDegradedTavily(false);

    try {
      setTimeout(() => {
        setResearchStep('Extraction des faits et scoring éditorial par LangGraph...');
      }, 1500);

      await apiClient<any>('/v1/ideas/research', {
        method: 'POST',
        body: JSON.stringify({
          topic_or_brief: topic,
          target_count: targetCount,
          workspace_id: session?.workspace_id || 'ws_default',
        }),
      });

      setModalOpen(false);
      showToast('success', 'Nouvelles idées générées par l’agent LangGraph !');
      await fetchIdeas();
    } catch (err: any) {
      if (err.message?.toLowerCase().includes('tavily') || err.status === 502) {
        setDegradedTavily(true);
      }
      showToast('error', `Erreur de recherche d'idées : ${err.message || 'Échec du workflow'}`);
    } finally {
      setResearching(false);
      setResearchStep('');
    }
  };

  const handleConvertToDraft = async (idea: Idea) => {
    setConvertingId(idea.id);
    try {
      // 1. Create Brief
      const briefRes = await apiClient<any>('/v1/briefs', {
        method: 'POST',
        body: JSON.stringify({
          workspace_id: session?.workspace_id || 'ws_default',
          objective: idea.title,
          idea_id: idea.id,
          platform_targets: ['linkedin', 'x'],
          requirements: { angle: idea.angle },
        }),
      });

      // 2. Generate Content Package and Variants
      await apiClient<any>('/v1/content/generate', {
        method: 'POST',
        body: JSON.stringify({
          brief_id: briefRes.id,
          workspace_id: session?.workspace_id || 'ws_default',
        }),
      });

      showToast('success', 'Brouillon généré par les agents ! Redirection vers la Revue HITL...');
      window.location.hash = '#inbox';
    } catch (err: any) {
      showToast('error', `Erreur de transformation en brouillon : ${err.message}`);
    } finally {
      setConvertingId(null);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-48" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <Skeleton className="h-64 w-full" />
          <Skeleton className="h-64 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      </div>
    );
  }

  if (error) {
    return <ErrorState message={error} onRetry={fetchIdeas} />;
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">
            {t.ideation.title}
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Veille continue et génération d'idées à fort engagement par agents autonomes.
          </p>
        </div>

        {canEdit && (
          <Button
            variant="primary"
            onClick={() => setModalOpen(true)}
            className="flex items-center gap-2"
          >
            <Plus className="h-4 w-4" />
            <span>{t.ideation.new_search_btn}</span>
          </Button>
        )}
      </div>

      {/* Tavily / LLM status banner if degraded */}
      {degradedTavily && (
        <div className="rounded-xl border border-amber-500/30 bg-amber-950/20 p-4 text-xs text-amber-300 flex items-center gap-3">
          <AlertCircle className="h-5 w-5 text-amber-400 shrink-0" />
          <div>
            <strong className="block font-semibold">Mode Dégradé Actif (Tavily non configuré ou indisponible)</strong>
            <span>La recherche web externe est temporairement remplacée par le cache documentaire local.</span>
          </div>
        </div>
      )}

      {/* Ideas Grid */}
      {ideas.length === 0 ? (
        <EmptyState
          title={t.ideation.empty_title}
          description={t.ideation.empty_desc}
          actionLabel={t.ideation.new_search_btn}
          onAction={() => setModalOpen(true)}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {ideas.map((idea) => {
            const isConverting = convertingId === idea.id;
            return (
              <div
                key={idea.id}
                className="flex flex-col justify-between rounded-2xl border border-slate-800 bg-slate-900/60 p-5 hover:border-slate-700 transition-all shadow-sm"
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <Badge variant="info" className="text-[10px]">
                      {idea.pillar || 'Général'}
                    </Badge>
                    <div className="flex items-center gap-1 text-[11px] font-mono text-cyan-400 font-bold">
                      <TrendingUp className="h-3 w-3" />
                      <span>{idea.relevance_score ? `${Math.round(idea.relevance_score * 100)}%` : '85%'}</span>
                    </div>
                  </div>

                  <h3 className="text-sm font-semibold text-white leading-snug mb-2 line-clamp-2">
                    {idea.title}
                  </h3>

                  <p className="text-xs text-slate-400 mb-4 line-clamp-3">
                    {idea.angle}
                  </p>

                  {/* Scores breakdown */}
                  <div className="grid grid-cols-3 gap-2 py-3 border-t border-b border-slate-800 text-[10px]">
                    <div>
                      <span className="text-slate-400 block uppercase">Nouveauté</span>
                      <span className="font-semibold text-emerald-400">
                        {Math.round((idea.novelty_score || 0.8) * 10)} / 10
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 block uppercase">Pertinence</span>
                      <span className="font-semibold text-cyan-400">
                        {Math.round((idea.relevance_score || 0.9) * 10)} / 10
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 block uppercase">Effort</span>
                      <span className="font-semibold text-yellow-400">
                        {Math.round((idea.effort_score || 0.4) * 10)} / 10
                      </span>
                    </div>
                  </div>
                </div>

                <div className="pt-4 flex items-center justify-between gap-2">
                  <Button
                    variant="primary"
                    size="sm"
                    disabled={isConverting || !canEdit}
                    isLoading={isConverting}
                    onClick={() => handleConvertToDraft(idea)}
                    className="flex-1 justify-center text-xs"
                  >
                    <span>{t.ideation.action_convert_draft}</span>
                    <ArrowRight className="h-3.5 w-3.5 ml-1" />
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Accessible Research Modal Dialog */}
      <Dialog
        isOpen={modalOpen}
        onClose={() => !researching && setModalOpen(false)}
        title={t.ideation.search_modal_title}
      >
        <form onSubmit={handleLaunchResearch} className="space-y-4">
          <div>
            <label
              htmlFor="research-topic"
              className="block text-xs font-semibold uppercase text-slate-300 mb-1"
            >
              Thématique ou Déclencheur Éditorial
            </label>
            <Input
              id="research-topic"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="Ex: Architectures de modèles de raisonnement (DeepSeek R1 vs OpenAI o3)"
              required
              disabled={researching}
            />
          </div>

          <div>
            <label
              htmlFor="target-count"
              className="block text-xs font-semibold uppercase text-slate-300 mb-1"
            >
              Nombre d'idées à synthétiser
            </label>
            <Input
              id="target-count"
              type="number"
              min={1}
              max={10}
              value={targetCount}
              onChange={(e) => setTargetCount(Number(e.target.value))}
              disabled={researching}
            />
          </div>

          {/* Long running workflow progression tracker */}
          {researching && (
            <div className="rounded-xl border border-cyan-500/30 bg-cyan-950/20 p-4 space-y-2">
              <div className="flex items-center gap-2 text-cyan-400 text-xs font-semibold">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>{researchStep || 'Orchestration en cours...'}</span>
              </div>
              <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                <div className="bg-cyan-500 h-1.5 rounded-full animate-pulse w-3/4" />
              </div>
            </div>
          )}

          <div className="flex justify-end gap-2.5 pt-3 border-t border-slate-800">
            <Button
              type="button"
              variant="ghost"
              disabled={researching}
              onClick={() => setModalOpen(false)}
            >
              Annuler
            </Button>
            <Button
              type="submit"
              variant="primary"
              isLoading={researching}
              className="flex items-center gap-1.5"
            >
              <Sparkles className="h-4 w-4" />
              <span>{t.ideation.launch_research_btn}</span>
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
};
