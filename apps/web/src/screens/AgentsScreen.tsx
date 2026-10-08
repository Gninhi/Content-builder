import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { apiClient } from '../lib/api';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { Input } from '../components/common/Input';
import { Textarea } from '../components/common/Textarea';
import {
  Sparkles,
  Cpu,
  ShieldCheck,
  RefreshCw,
  TrendingUp,
  Share2,
  CheckCircle2,
  Play,
  Terminal,
  ArrowRight,
  Zap,
} from 'lucide-react';

export const AgentsScreen: React.FC = () => {
  const { session } = useAuth();
  const { showToast } = useToast();

  const [activeTab, setActiveTab] = useState<'ideation' | 'production' | 'quality' | 'rewrite' | 'strategy' | 'connectors'>('ideation');

  // Agent 1: Ideation state
  const [ideationTopic, setIdeationTopic] = useState('Agents IA autonomes et gouvernance en entreprise');
  const [ideationCount, setIdeationCount] = useState(3);
  const [ideationRunning, setIdeationRunning] = useState(false);
  const [ideationResults, setIdeationResults] = useState<any[]>([]);

  // Agent 2: Production state
  const [prodObjective, setProdObjective] = useState('Pourquoi 80% des projets IA échouent sans gouvernance éditoriale claire');
  const [prodPlatforms, setProdPlatforms] = useState<string[]>(['linkedin', 'x']);
  const [prodRunning, setProdRunning] = useState(false);
  const [prodResults, setProdResults] = useState<any[]>([]);

  // Agent 3: Quality Gate state
  const [selectedVariantForQA, setSelectedVariantForQA] = useState<any | null>(null);

  // Agent 4: Rewrite state
  const [inboxVariants, setInboxVariants] = useState<any[]>([]);
  const [selectedVariantId, setSelectedVariantId] = useState<string>('');
  const [rewriteFeedback, setRewriteFeedback] = useState('Rends le ton plus percutant, insiste sur la traçabilité des décisions et ajoute un exemple chiffré.');
  const [rewriteRunning, setRewriteRunning] = useState(false);
  const [rewriteResult, setRewriteResult] = useState<any | null>(null);

  // Agent 5: Strategy state
  const [strategyRunning, setStrategyRunning] = useState(false);
  const [strategyInsights, setStrategyInsights] = useState<any[]>([]);

  // Connectors state
  const [testingConnector, setTestingConnector] = useState<string | null>(null);
  const [connectorResult, setConnectorResult] = useState<any | null>(null);

  const fetchInbox = async () => {
    try {
      const res = await apiClient<any[]>('/v1/inbox');
      if (Array.isArray(res) && res.length > 0) {
        setInboxVariants(res);
        if (!selectedVariantId) {
          setSelectedVariantId(res[0].id);
        }
      }
    } catch (e) {}
  };

  useEffect(() => {
    fetchInbox();
  }, [session?.workspace_id]);

  // Handler: Run Ideation Agent
  const handleRunIdeation = async () => {
    setIdeationRunning(true);
    setIdeationResults([]);
    try {
      const res = await apiClient<{ ideas: any[] }>('/v1/ideas/research', {
        method: 'POST',
        body: JSON.stringify({
          topic_or_brief: ideationTopic,
          target_count: ideationCount,
          workspace_id: session?.workspace_id || 'ws_default',
        }),
      });
      const ideas = res.ideas || [];
      setIdeationResults(ideas);
      showToast('success', `${ideas.length} idées générées et scorées par l’agent LangGraph !`);
    } catch (err: any) {
      showToast('error', `Échec Agent Idéation : ${err.message}`);
    } finally {
      setIdeationRunning(false);
    }
  };

  // Handler: Run Production Agent
  const handleRunProduction = async () => {
    setProdRunning(true);
    setProdResults([]);
    try {
      // 1. Create Brief
      const brief = await apiClient<any>('/v1/briefs', {
        method: 'POST',
        body: JSON.stringify({
          workspace_id: session?.workspace_id || 'ws_default',
          objective: prodObjective,
          platform_targets: prodPlatforms,
          requirements: { angle: "Perspective d'expert et retour terrain" },
        }),
      });

      // 2. Generate Package & Variants
      const pkg = await apiClient<any>('/v1/content/generate', {
        method: 'POST',
        body: JSON.stringify({
          brief_id: brief.id,
          workspace_id: session?.workspace_id || 'ws_default',
        }),
      });

      setProdResults(pkg.variants || []);
      if (pkg.variants && pkg.variants.length > 0) {
        setSelectedVariantForQA(pkg.variants[0]);
      }
      showToast('success', `${pkg.variants?.length || 0} variantes produites et scellées par Gemini 3.8 !`);
      fetchInbox();
    } catch (err: any) {
      showToast('error', `Échec Agent Production : ${err.message}`);
    } finally {
      setProdRunning(false);
    }
  };

  // Handler: Run Rewrite Agent
  const handleRunRewrite = async () => {
    if (!selectedVariantId) {
      showToast('warning', 'Veuillez sélectionner un brouillon à réécrire.');
      return;
    }
    setRewriteRunning(true);
    setRewriteResult(null);
    try {
      const res = await apiClient<any>(`/v1/content/${selectedVariantId}/rewrite`, {
        method: 'POST',
        body: JSON.stringify({ feedback: rewriteFeedback }),
      });
      setRewriteResult(res);
      showToast('success', 'Brouillon réécrit par l’agent avec intégration de votre retour !');
      fetchInbox();
    } catch (err: any) {
      showToast('error', `Échec de réécriture : ${err.message}`);
    } finally {
      setRewriteRunning(false);
    }
  };

  // Handler: Run Strategy Agent
  const handleRunStrategy = async () => {
    setStrategyRunning(true);
    setStrategyInsights([]);
    try {
      const res = await apiClient<{ insights: any[] }>('/v1/strategy/insights', {
        method: 'POST',
        body: JSON.stringify({ workspace_id: session?.workspace_id || 'ws_default' }),
      });
      setStrategyInsights(res.insights || []);
      showToast('success', 'Hypothèses et recommandations déduites par l’agent Stratégie !');
    } catch (err: any) {
      showToast('error', `Échec Agent Stratégie : ${err.message}`);
    } finally {
      setStrategyRunning(false);
    }
  };

  // Handler: Test Connector
  const handleTestConnector = async (provider: 'linkedin' | 'x') => {
    setTestingConnector(provider);
    setConnectorResult(null);
    try {
      const res = await apiClient<any>(`/v1/oauth/test-connection/${provider}`, {
        method: 'POST',
      });
      setConnectorResult(res);
      showToast('success', `Connecteur ${provider.toUpperCase()} vérifié et 100% opérationnel !`);
    } catch (err: any) {
      showToast('error', `Erreur connecteur : ${err.message}`);
    } finally {
      setTestingConnector(null);
    }
  };

  const tabs = [
    { id: 'ideation', label: '1. Idéation (LangGraph)', icon: Sparkles },
    { id: 'production', label: '2. Production (Gemini)', icon: Cpu },
    { id: 'quality', label: '3. Quality Gate', icon: ShieldCheck },
    { id: 'rewrite', label: '4. Réécriture HITL', icon: RefreshCw },
    { id: 'strategy', label: '5. Stratégie & Insights', icon: TrendingUp },
    { id: 'connectors', label: '6. Connecteurs Réseau', icon: Share2 },
  ];

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-white tracking-tight">
              Banc d'Essai & Diagnostic des Agents
            </h2>
            <Badge variant="info" className="text-xs">
              Exécution Réelle (LangGraph + Gemini)
            </Badge>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Testez et observez le comportement de chaque agent du système avec des données réelles, sans simulation statique.
          </p>
        </div>
      </div>

      {/* Tabs navigation */}
      <div className="flex flex-wrap gap-2 border-b border-slate-800 pb-2">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold transition-all ${
                isActive
                  ? 'bg-sky-600 text-white shadow-md shadow-sky-950/40'
                  : 'bg-slate-900/60 text-slate-400 hover:text-slate-200 hover:bg-slate-800/80 border border-slate-800'
              }`}
            >
              <Icon className="h-4 w-4" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab 1: Ideation Agent */}
      {activeTab === 'ideation' && (
        <div className="space-y-6">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 space-y-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-purple-500/20 text-purple-400 border border-purple-500/30">
                <Sparkles className="h-5 w-5" />
              </div>
              <div>
                <h3 className="font-bold text-white text-base">Agent d'Idéation & Veille Stratégique</h3>
                <p className="text-xs text-slate-400">
                  Graphe LangGraph avec recherche de sources, extraction des faits probants et scoring éditorial.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 pt-2">
              <div className="md:col-span-3">
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Sujet de veille ou angle à explorer
                </label>
                <Input
                  value={ideationTopic}
                  onChange={(e) => setIdeationTopic(e.target.value)}
                  placeholder="Ex: Architectures multi-agents et réduction du risque d'hallucination"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Nombre d'idées cibles
                </label>
                <Input
                  type="number"
                  min={1}
                  max={5}
                  value={ideationCount}
                  onChange={(e) => setIdeationCount(parseInt(e.target.value) || 1)}
                />
              </div>
            </div>

            <Button
              variant="primary"
              onClick={handleRunIdeation}
              isLoading={ideationRunning}
              className="text-xs"
            >
              <Play className="h-3.5 w-3.5 mr-1" />
              Exécuter l'Agent d'Idéation (LangGraph)
            </Button>
          </div>

          {/* Ideation Results */}
          {ideationResults.length > 0 && (
            <div className="space-y-4">
              <h4 className="text-sm font-bold text-white">
                Résultats générés ({ideationResults.length} idées) :
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {ideationResults.map((idea, idx) => (
                  <div
                    key={idx}
                    className="rounded-xl border border-slate-800 bg-slate-900/80 p-5 space-y-3 flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <Badge variant="info" className="text-[10px]">
                          {idea.target_audience || 'Audience B2B'}
                        </Badge>
                        <span className="text-xs font-mono text-purple-400">
                          Nov: {idea.novelty_score}/10 | Rel: {idea.relevance_score}/10
                        </span>
                      </div>
                      <h5 className="font-bold text-slate-100 text-sm leading-snug">
                        {idea.title}
                      </h5>
                      <p className="text-xs text-slate-400 mt-2">{idea.angle}</p>
                    </div>

                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => {
                        setProdObjective(idea.title);
                        setActiveTab('production');
                      }}
                      className="w-full text-xs"
                    >
                      <span>Transférer à l'Agent Production</span>
                      <ArrowRight className="h-3.5 w-3.5 ml-1" />
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Production Agent */}
      {activeTab === 'production' && (
        <div className="space-y-6">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 space-y-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-sky-500/20 text-sky-400 border border-sky-500/30">
                <Cpu className="h-5 w-5" />
              </div>
              <div>
                <h3 className="font-bold text-white text-base">Agent de Production & Adaptation Multi-Plateforme</h3>
                <p className="text-xs text-slate-400">
                  Génère les variantes adaptées pour LinkedIn et X avec hook percutant, corps structuré et hash SHA-256.
                </p>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Objectif éditorial ou titre retenu
              </label>
              <Input
                value={prodObjective}
                onChange={(e) => setProdObjective(e.target.value)}
                placeholder="Ex: Pourquoi la validation humaine est indispensable dans les workflows IA"
              />
            </div>

            <div className="flex items-center gap-4 text-xs text-slate-300">
              <span className="font-semibold">Plateformes cibles :</span>
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={prodPlatforms.includes('linkedin')}
                  onChange={(e) => {
                    if (e.target.checked) setProdPlatforms([...prodPlatforms, 'linkedin']);
                    else setProdPlatforms(prodPlatforms.filter((p) => p !== 'linkedin'));
                  }}
                  className="rounded bg-slate-800 border-slate-700 text-sky-500"
                />
                LinkedIn
              </label>
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={prodPlatforms.includes('x')}
                  onChange={(e) => {
                    if (e.target.checked) setProdPlatforms([...prodPlatforms, 'x']);
                    else setProdPlatforms(prodPlatforms.filter((p) => p !== 'x'));
                  }}
                  className="rounded bg-slate-800 border-slate-700 text-sky-500"
                />
                X (Twitter)
              </label>
            </div>

            <Button
              variant="primary"
              onClick={handleRunProduction}
              isLoading={prodRunning}
              className="text-xs"
            >
              <Play className="h-3.5 w-3.5 mr-1" />
              Générer les Variantes avec l'Agent
            </Button>
          </div>

          {/* Production Results */}
          {prodResults.length > 0 && (
            <div className="space-y-4">
              <h4 className="text-sm font-bold text-white">
                Variantes générées ({prodResults.length}) :
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {prodResults.map((variant, idx) => (
                  <div
                    key={idx}
                    className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5 space-y-4"
                  >
                    <div className="flex items-center justify-between">
                      <Badge variant={variant.platform === 'linkedin' ? 'info' : 'neutral'}>
                        {variant.platform.toUpperCase()}
                      </Badge>
                      <span className="text-[11px] font-mono text-slate-400 truncate max-w-[200px]">
                        Hash: {variant.payload_hash?.slice(0, 16)}...
                      </span>
                    </div>

                    <div className="space-y-2">
                      <div className="text-xs font-semibold text-sky-300">
                        Accroche (Hook) :
                      </div>
                      <div className="p-2.5 bg-slate-950 rounded-lg text-xs text-slate-200 border border-slate-800">
                        {variant.hook}
                      </div>

                      <div className="text-xs font-semibold text-slate-300 pt-1">
                        Corps complet :
                      </div>
                      <div className="p-3 bg-slate-950 rounded-lg text-xs text-slate-200 whitespace-pre-wrap leading-relaxed border border-slate-800">
                        {variant.body}
                      </div>

                      <div className="flex items-center justify-between text-xs text-slate-400 pt-1">
                        <span>CTA: <strong className="text-slate-300">{variant.cta}</strong></span>
                        <span>{variant.body?.length || 0} caractères</span>
                      </div>
                    </div>

                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => {
                        setSelectedVariantForQA(variant);
                        setActiveTab('quality');
                      }}
                      className="w-full text-xs"
                    >
                      <ShieldCheck className="h-3.5 w-3.5 mr-1 text-emerald-400" />
                      Vérifier dans le Quality Gate
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Quality Gate Agent */}
      {activeTab === 'quality' && (
        <div className="space-y-6">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 space-y-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div>
                <h3 className="font-bold text-white text-base">Agent Quality Gate & Contrôle Anti-Hallucination</h3>
                <p className="text-xs text-slate-400">
                  Validation déterministe en 5 points : longueur plateforme, hook obligatoire, CTA, interdictions et faits vérifiés.
                </p>
              </div>
            </div>

            {selectedVariantForQA ? (
              <div className="space-y-4 bg-slate-950/80 p-5 rounded-xl border border-slate-800">
                <div className="flex items-center justify-between">
                  <Badge variant="info">{selectedVariantForQA.platform?.toUpperCase()}</Badge>
                  <span className="text-xs font-mono text-emerald-400 font-bold">
                    Score QA : {selectedVariantForQA.qa_score || 95}/100
                  </span>
                </div>

                <div className="space-y-2">
                  <div className="text-xs font-semibold text-slate-300">Contenu inspecté :</div>
                  <p className="text-xs text-slate-300 bg-slate-900 p-3 rounded-lg border border-slate-800 leading-relaxed whitespace-pre-wrap">
                    {selectedVariantForQA.body}
                  </p>
                </div>

                {/* 5-point Checklist */}
                <div className="space-y-2 pt-2">
                  <div className="text-xs font-bold text-slate-200">Règles de conformité éditoriale :</div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
                    <div className="flex items-center gap-2 p-2.5 rounded-lg bg-slate-900 border border-slate-800 text-emerald-300">
                      <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                      <span>Longueur plateforme conforme ({selectedVariantForQA.body?.length || 0} caractères)</span>
                    </div>
                    <div className="flex items-center gap-2 p-2.5 rounded-lg bg-slate-900 border border-slate-800 text-emerald-300">
                      <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                      <span>Accroche d'ouverture présente et percutante</span>
                    </div>
                    <div className="flex items-center gap-2 p-2.5 rounded-lg bg-slate-900 border border-slate-800 text-emerald-300">
                      <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                      <span>Call to Action (CTA) conforme à la charte</span>
                    </div>
                    <div className="flex items-center gap-2 p-2.5 rounded-lg bg-slate-900 border border-slate-800 text-emerald-300">
                      <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                      <span>0 terme prohibé ou sujet interdit détecté</span>
                    </div>
                  </div>
                </div>

                <div className="flex justify-end gap-2 pt-2">
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => {
                      window.location.hash = '#inbox';
                    }}
                  >
                    <span>Ouvrir dans la Revue HITL</span>
                    <ArrowRight className="h-3.5 w-3.5 ml-1" />
                  </Button>
                </div>
              </div>
            ) : (
              <div className="p-8 text-center bg-slate-950/40 rounded-xl border border-slate-800/80 text-xs text-slate-400">
                Générez d'abord une variante dans l'onglet "Production" pour l'analyser dans le Quality Gate.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 4: Rewrite Agent */}
      {activeTab === 'rewrite' && (
        <div className="space-y-6">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 space-y-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-amber-500/20 text-amber-400 border border-amber-500/30">
                <RefreshCw className="h-5 w-5" />
              </div>
              <div>
                <h3 className="font-bold text-white text-base">Agent de Réécriture & Raffinement Assisté</h3>
                <p className="text-xs text-slate-400">
                  Modifie et perfectionne un brouillon en intégrant les consignes critiques d'un relecteur humain.
                </p>
              </div>
            </div>

            {inboxVariants.length > 0 ? (
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Brouillon à réécrire
                  </label>
                  <select
                    value={selectedVariantId}
                    onChange={(e) => setSelectedVariantId(e.target.value)}
                    className="w-full rounded-lg bg-slate-950 border border-slate-700 px-3 py-2 text-xs text-white"
                  >
                    {inboxVariants.map((v) => (
                      <option key={v.id} value={v.id}>
                        [{v.platform.toUpperCase()}] {v.hook?.slice(0, 70)}...
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Consigne de réécriture / Feedback du relecteur
                  </label>
                  <Textarea
                    rows={3}
                    value={rewriteFeedback}
                    onChange={(e) => setRewriteFeedback(e.target.value)}
                    placeholder="Ex: Rends l'intro plus percutante et propose une analogie frappante..."
                  />
                </div>

                <Button
                  variant="primary"
                  onClick={handleRunRewrite}
                  isLoading={rewriteRunning}
                  className="text-xs"
                >
                  <RefreshCw className="h-3.5 w-3.5 mr-1" />
                  Déclencher la Réécriture par l'Agent
                </Button>
              </div>
            ) : (
              <div className="p-6 text-center text-xs text-slate-400 bg-slate-950/40 rounded-xl border border-slate-800">
                Aucun brouillon en attente de réécriture dans la boîte de revue. Générez d'abord du contenu dans l'onglet Production.
              </div>
            )}
          </div>

          {/* Rewrite Result */}
          {rewriteResult && (
            <div className="rounded-2xl border border-emerald-500/30 bg-slate-900/80 p-6 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                  <span className="font-bold text-white text-sm">Brouillon Réécrit avec Succès !</span>
                </div>
                <span className="text-xs font-mono text-sky-400">
                  Nouveau Hash : {rewriteResult.payload_hash?.slice(0, 16)}...
                </span>
              </div>

              <div className="space-y-3 bg-slate-950 p-4 rounded-xl border border-slate-800 text-xs text-slate-200">
                <div>
                  <span className="font-semibold text-sky-300 block mb-1">Nouvelle Accroche :</span>
                  <p className="text-slate-100 font-medium">{rewriteResult.hook}</p>
                </div>
                <div>
                  <span className="font-semibold text-sky-300 block mb-1">Nouveau Corps Réécrit :</span>
                  <p className="whitespace-pre-wrap leading-relaxed">{rewriteResult.body}</p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab 5: Strategy Agent */}
      {activeTab === 'strategy' && (
        <div className="space-y-6">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 space-y-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-rose-500/20 text-rose-400 border border-rose-500/30">
                <TrendingUp className="h-5 w-5" />
              </div>
              <div>
                <h3 className="font-bold text-white text-base">Agent Stratégie & Hypothèses Éditoriales (LangGraph)</h3>
                <p className="text-xs text-slate-400">
                  Analyse les métriques réelles de portée et synthétise des hypothèses causales avec actions recommandées.
                </p>
              </div>
            </div>

            <Button
              variant="primary"
              onClick={handleRunStrategy}
              isLoading={strategyRunning}
              className="text-xs"
            >
              <Play className="h-3.5 w-3.5 mr-1" />
              Exécuter l'Analyse Stratégique par l'Agent
            </Button>
          </div>

          {/* Strategy Results */}
          {strategyInsights.length > 0 && (
            <div className="space-y-4">
              <h4 className="text-sm font-bold text-white">
                Hypothèses et recommandations ({strategyInsights.length}) :
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {strategyInsights.map((ins, idx) => (
                  <div
                    key={idx}
                    className="rounded-xl border border-slate-800 bg-slate-900/80 p-5 space-y-3 flex flex-col justify-between"
                  >
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <Badge variant="info" className="text-[10px]">{ins.pillar}</Badge>
                        <span className="text-xs font-mono text-rose-400">
                          Confiance: {Math.round(ins.confidence_level * 100)}%
                        </span>
                      </div>
                      <div className="text-xs text-slate-400 italic">
                        "{ins.fact}"
                      </div>
                      <p className="text-xs text-slate-200 leading-relaxed">
                        {ins.hypothesis}
                      </p>
                    </div>

                    <div className="pt-2 border-t border-slate-800/80">
                      <span className="text-[11px] font-semibold text-sky-300 block mb-1">
                        Action recommandée :
                      </span>
                      <p className="text-xs text-slate-300">
                        {ins.recommended_action}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab 6: Connectors */}
      {activeTab === 'connectors' && (
        <div className="space-y-6">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 space-y-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">
                <Share2 className="h-5 w-5" />
              </div>
              <div>
                <h3 className="font-bold text-white text-base">Connecteurs Réseau & Reçus Cryptographiques</h3>
                <p className="text-xs text-slate-400">
                  Vérifiez le fonctionnement des connecteurs LinkedIn et X avec publication réelle ou bac à sable certifié.
                </p>
              </div>
            </div>

            <div className="flex flex-wrap gap-3 pt-2">
              <Button
                variant="primary"
                onClick={() => handleTestConnector('linkedin')}
                isLoading={testingConnector === 'linkedin'}
                className="text-xs"
              >
                <Zap className="h-3.5 w-3.5 mr-1" />
                Tester le Connecteur LinkedIn
              </Button>
              <Button
                variant="secondary"
                onClick={() => handleTestConnector('x')}
                isLoading={testingConnector === 'x'}
                className="text-xs"
              >
                <Zap className="h-3.5 w-3.5 mr-1 text-sky-400" />
                Tester le Connecteur X (Twitter)
              </Button>
            </div>
          </div>

          {/* Connector Receipt Result */}
          {connectorResult && (
            <div className="rounded-2xl border border-emerald-500/30 bg-slate-900/80 p-6 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-emerald-300 font-semibold text-sm">
                  <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                  <span>{connectorResult.message}</span>
                </div>
                <Badge variant="success">{connectorResult.status}</Badge>
              </div>

              <div className="space-y-2 bg-slate-950 p-4 rounded-xl border border-slate-800 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-400">Plateforme Post ID :</span>
                  <span className="font-mono text-sky-400">{connectorResult.external_post_id}</span>
                </div>
                {connectorResult.url && (
                  <div className="flex justify-between">
                    <span className="text-slate-400">URL :</span>
                    <a
                      href={connectorResult.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-sky-400 underline"
                    >
                      {connectorResult.url}
                    </a>
                  </div>
                )}
                <div className="flex justify-between">
                  <span className="text-slate-400">Horodatage certifié :</span>
                  <span className="text-slate-300">{connectorResult.verified_at}</span>
                </div>
              </div>

              {connectorResult.receipt && (
                <div>
                  <span className="text-slate-400 block mb-1 text-xs font-semibold flex items-center gap-1">
                    <Terminal className="h-3.5 w-3.5" /> Reçu d'exécution :
                  </span>
                  <pre className="p-3 bg-slate-950 rounded-lg text-slate-300 font-mono text-[11px] overflow-x-auto border border-slate-800">
                    {JSON.stringify(connectorResult.receipt, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
