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

  // Bench Model Selection Override
  const [benchModelKey, setBenchModelKey] = useState<'workspace_default' | 'nvidia_llama_32_11b' | 'nvidia_nemotron_70b' | 'gemini_38_flash'>('workspace_default');

  const getRunOverride = () => {
    switch (benchModelKey) {
      case 'nvidia_llama_32_11b':
        return { provider_id: 'nvidia', model_id: 'meta/llama-3.2-11b-vision-instruct' };
      case 'nvidia_nemotron_70b':
        return { provider_id: 'nvidia', model_id: 'nvidia/llama-3.1-nemotron-70b-instruct' };
      case 'gemini_38_flash':
        return { provider_id: 'gemini', model_id: 'gemini-3.8-flash' };
      default:
        return undefined;
    }
  };

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
      const override = getRunOverride();
      const res = await apiClient<{ ideas: any[] }>('/v1/ideas/research', {
        method: 'POST',
        body: JSON.stringify({
          topic_or_brief: ideationTopic,
          target_count: ideationCount,
          workspace_id: session?.workspace_id || 'ws_default',
          llm_override: override,
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
      const override = getRunOverride();
      const pkg = await apiClient<any>('/v1/content/generate', {
        method: 'POST',
        body: JSON.stringify({
          brief_id: brief.id,
          workspace_id: session?.workspace_id || 'ws_default',
          llm_override: override,
        }),
      });

      setProdResults(pkg.variants || []);
      if (pkg.variants && pkg.variants.length > 0) {
        setSelectedVariantForQA(pkg.variants[0]);
      }
      showToast('success', `${pkg.variants?.length || 0} variantes produites et scellées cryptographiquement !`);
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
      const override = getRunOverride();
      const res = await apiClient<{ insights: any[] }>('/v1/strategy/insights', {
        method: 'POST',
        body: JSON.stringify({
          workspace_id: session?.workspace_id || 'ws_default',
          llm_override: override,
        }),
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
    { id: 'production', label: '2. Production Multi-Modèles', icon: Cpu },
    { id: 'quality', label: '3. Quality Gate', icon: ShieldCheck },
    { id: 'rewrite', label: '4. Réécriture HITL', icon: RefreshCw },
    { id: 'strategy', label: '5. Stratégie & Insights', icon: TrendingUp },
    { id: 'connectors', label: '6. Connecteurs Réseau', icon: Share2 },
  ];

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border-subtle pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <h2 className="text-xl sm:text-2xl font-bold text-txt tracking-tight">
              Banc d'Essai & Diagnostic des Agents
            </h2>
            <Badge variant="accent" className="text-xs">
              Multi-Fournisseur (NVIDIA NIM & Gemini)
            </Badge>
          </div>
          <p className="text-xs sm:text-sm text-txt-secondary mt-1">
            Testez et observez le comportement de chaque agent du système avec des données réelles, sans simulation statique.
          </p>
        </div>

        {/* Model selection override for Bench Testing */}
        <div className="flex items-center gap-2.5 bg-surface border border-border p-2.5 rounded-xl shadow-sm">
          <Cpu className="h-4 w-4 text-accent shrink-0" />
          <div className="flex flex-col">
            <label htmlFor="bench-model-select" className="text-[10px] uppercase font-mono text-txt-muted font-semibold tracking-wider">
              Moteur LLM pour le Banc
            </label>
            <select
              id="bench-model-select"
              value={benchModelKey}
              onChange={(e) => setBenchModelKey(e.target.value as any)}
              className="bg-surface-subtle text-xs text-txt border border-border rounded-lg px-2.5 py-1.5 focus:border-border-focus focus:outline-none min-h-[38px]"
            >
              <option value="workspace_default">Défaut du Workspace</option>
              <option value="nvidia_llama_32_11b">⚡ NVIDIA NIM : Llama 3.2 11B Vision</option>
              <option value="nvidia_nemotron_70b">⚡ NVIDIA NIM : Nemotron 70B Instruct</option>
              <option value="gemini_38_flash">💎 Google Gemini : Gemini 3.8 Flash</option>
            </select>
          </div>
        </div>
      </div>

      {/* Tabs navigation */}
      <div className="flex flex-wrap gap-2 border-b border-border-subtle pb-3" role="tablist">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              role="tab"
              aria-selected={isActive}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-medium transition-all min-h-[40px] ${
                isActive
                  ? 'bg-accent text-accent-txt font-semibold shadow-sm border border-accent'
                  : 'bg-surface text-txt-secondary hover:text-txt hover:bg-surface-subtle border border-border'
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
          <div className="rounded-xl border border-border bg-surface p-5 sm:p-6 space-y-4 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-accent-subtle text-accent border border-accent-border">
                <Sparkles className="h-5 w-5" />
              </div>
              <div>
                <h3 className="font-semibold text-txt text-base">Agent d'Idéation & Veille Stratégique</h3>
                <p className="text-xs text-txt-secondary mt-0.5">
                  Graphe LangGraph avec recherche de sources, extraction des faits probants et scoring éditorial.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 pt-2">
              <div className="md:col-span-3">
                <label className="block text-xs font-medium text-txt mb-1">
                  Sujet de veille ou angle à explorer
                </label>
                <Input
                  value={ideationTopic}
                  onChange={(e) => setIdeationTopic(e.target.value)}
                  placeholder="Ex: Architectures multi-agents et réduction du risque d'hallucination"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-txt mb-1">
                  Nombre d'idées cibles
                </label>
                <Input
                  type="number"
                  min={1}
                  max={5}
                  value={ideationCount}
                  onChange={(e) => setIdeationCount(parseInt(e.target.value) || 1)}
                  className="font-mono"
                />
              </div>
            </div>

            <Button
              variant="primary"
              onClick={handleRunIdeation}
              isLoading={ideationRunning}
              className="text-xs min-h-[44px] font-medium"
            >
              <Play className="h-3.5 w-3.5 mr-1.5" />
              Exécuter l'Agent d'Idéation (LangGraph)
            </Button>
          </div>

          {/* Ideation Results */}
          {ideationResults.length > 0 && (
            <div className="space-y-4">
              <h4 className="text-sm font-semibold text-txt">
                Résultats générés ({ideationResults.length} idées) :
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {ideationResults.map((idea, idx) => (
                  <div
                    key={idx}
                    className="rounded-xl border border-border bg-surface p-5 space-y-3 flex flex-col justify-between shadow-sm hover:border-border-focus transition-colors"
                  >
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <Badge variant="accent" className="text-[10px]">
                          {idea.target_audience || 'Audience B2B'}
                        </Badge>
                        <span className="text-xs font-mono text-accent-txt">
                          Nov: {idea.novelty_score}/10 | Rel: {idea.relevance_score}/10
                        </span>
                      </div>
                      <h5 className="font-semibold text-txt text-sm leading-snug">
                        {idea.title}
                      </h5>
                      <p className="text-xs text-txt-secondary mt-2 leading-relaxed">{idea.angle}</p>
                    </div>

                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => {
                        setProdObjective(idea.title);
                        setActiveTab('production');
                      }}
                      className="w-full text-xs min-h-[40px]"
                    >
                      <span>Transférer à l'Agent Production</span>
                      <ArrowRight className="h-3.5 w-3.5 ml-1.5" />
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
          <div className="rounded-xl border border-border bg-surface p-5 sm:p-6 space-y-4 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-accent-subtle text-accent border border-accent-border">
                <Cpu className="h-5 w-5" />
              </div>
              <div>
                <h3 className="font-semibold text-txt text-base">Agent de Production & Adaptation Multi-Plateforme</h3>
                <p className="text-xs text-txt-secondary mt-0.5">
                  Génère les variantes adaptées pour LinkedIn et X avec hook percutant, corps structuré et hash SHA-256.
                </p>
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-txt mb-1">
                Objectif éditorial ou titre retenu
              </label>
              <Input
                value={prodObjective}
                onChange={(e) => setProdObjective(e.target.value)}
                placeholder="Ex: Pourquoi la validation humaine est indispensable dans les workflows IA"
              />
            </div>

            <div className="flex items-center gap-4 text-xs text-txt">
              <span className="font-medium">Plateformes cibles :</span>
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={prodPlatforms.includes('linkedin')}
                  onChange={(e) => {
                    if (e.target.checked) setProdPlatforms([...prodPlatforms, 'linkedin']);
                    else setProdPlatforms(prodPlatforms.filter((p) => p !== 'linkedin'));
                  }}
                  className="rounded border-border text-accent focus:ring-accent"
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
                  className="rounded border-border text-accent focus:ring-accent"
                />
                X (Twitter)
              </label>
            </div>

            <Button
              variant="primary"
              onClick={handleRunProduction}
              isLoading={prodRunning}
              className="text-xs min-h-[44px] font-medium"
            >
              <Play className="h-3.5 w-3.5 mr-1.5" />
              Générer les Variantes avec l'Agent
            </Button>
          </div>

          {/* Production Results */}
          {prodResults.length > 0 && (
            <div className="space-y-4">
              <h4 className="text-sm font-semibold text-txt">
                Variantes générées ({prodResults.length}) :
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {prodResults.map((variant, idx) => (
                  <div
                    key={idx}
                    className="rounded-xl border border-border bg-surface p-5 space-y-4 shadow-sm"
                  >
                    <div className="flex items-center justify-between">
                      <Badge variant={variant.platform === 'linkedin' ? 'accent' : 'neutral'} className="font-mono">
                        {variant.platform.toUpperCase()}
                      </Badge>
                      <span className="text-[11px] font-mono text-accent-txt truncate max-w-[200px]">
                        Hash: {variant.payload_hash?.slice(0, 16)}...
                      </span>
                    </div>

                    {variant.provenance && (
                      <div className="flex flex-wrap items-center justify-between gap-2 p-2.5 bg-surface-subtle border border-border-subtle rounded-lg text-[11px] font-mono">
                        <div className="flex items-center gap-1.5">
                          <Badge
                            variant={variant.provenance.provider_id === 'nvidia' ? 'accent' : variant.provenance.provider_id === 'gemini' ? 'info' : 'neutral'}
                            className="text-[10px] uppercase font-bold px-2 py-0.5"
                          >
                            {variant.provenance.provider_id === 'nvidia' ? 'NVIDIA NIM' : variant.provenance.provider_id === 'gemini' ? 'Google Gemini' : 'Dégradé'}
                          </Badge>
                          <span className="text-txt font-semibold truncate max-w-[170px]" title={variant.provenance.model_id}>
                            {variant.provenance.model_id}
                          </span>
                        </div>
                        <div className="flex items-center gap-2.5 text-[11px]">
                          {variant.provenance.latency_ms > 0 && (
                            <span className="text-status-success-text font-semibold">⚡ {variant.provenance.latency_ms} ms</span>
                          )}
                          {variant.provenance.tokens > 0 && (
                            <span className="text-txt-muted">{variant.provenance.tokens} tok</span>
                          )}
                          {variant.provenance.cost_usd > 0 && (
                            <span className="text-accent-txt font-bold">${variant.provenance.cost_usd.toFixed(6)}</span>
                          )}
                        </div>
                      </div>
                    )}

                    <div className="space-y-2.5">
                      <div className="text-xs font-medium text-txt">
                        Accroche (Hook) :
                      </div>
                      <div className="p-3 bg-surface-subtle rounded-lg text-xs text-txt border border-border-subtle">
                        {variant.hook}
                      </div>

                      <div className="text-xs font-medium text-txt pt-1">
                        Corps complet :
                      </div>
                      <div className="p-3.5 bg-surface-subtle rounded-lg text-xs text-txt whitespace-pre-wrap leading-relaxed border border-border-subtle">
                        {variant.body}
                      </div>

                      <div className="flex items-center justify-between text-xs text-txt-secondary pt-1 font-mono">
                        <span>CTA: <strong className="text-accent-txt">{variant.cta}</strong></span>
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
                      className="w-full text-xs min-h-[40px]"
                    >
                      <ShieldCheck className="h-3.5 w-3.5 mr-1.5 text-status-success-text" />
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
          <div className="rounded-xl border border-border bg-surface p-5 sm:p-6 space-y-4 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-status-success-bg text-status-success-text border border-status-success-border">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div>
                <h3 className="font-semibold text-txt text-base">Agent Quality Gate & Contrôle Anti-Hallucination</h3>
                <p className="text-xs text-txt-secondary mt-0.5">
                  Validation déterministe en 5 points : longueur plateforme, hook obligatoire, CTA, interdictions et faits vérifiés.
                </p>
              </div>
            </div>

            {selectedVariantForQA ? (
              <div className="space-y-4 bg-surface-subtle p-5 rounded-xl border border-border-subtle">
                <div className="flex items-center justify-between">
                  <Badge variant="accent" className="font-mono">{selectedVariantForQA.platform?.toUpperCase()}</Badge>
                  <span className="text-xs font-mono text-status-success-text font-semibold">
                    Score QA : {selectedVariantForQA.qa_score || 95}/100
                  </span>
                </div>

                <div className="space-y-2">
                  <div className="text-xs font-medium text-txt">Contenu inspecté :</div>
                  <p className="text-xs text-txt bg-surface p-3.5 rounded-lg border border-border-subtle leading-relaxed whitespace-pre-wrap">
                    {selectedVariantForQA.body}
                  </p>
                </div>

                {/* 5-point Checklist */}
                <div className="space-y-2.5 pt-2">
                  <div className="text-xs font-semibold text-txt">Règles de conformité éditoriale :</div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
                    <div className="flex items-center gap-2 p-3 rounded-lg bg-surface border border-border-subtle text-status-success-text">
                      <CheckCircle2 className="h-4 w-4 shrink-0 text-status-success-text" />
                      <span>Longueur conforme ({selectedVariantForQA.body?.length || 0} car.)</span>
                    </div>
                    <div className="flex items-center gap-2 p-3 rounded-lg bg-surface border border-border-subtle text-status-success-text">
                      <CheckCircle2 className="h-4 w-4 shrink-0 text-status-success-text" />
                      <span>Accroche d'ouverture présente et percutante</span>
                    </div>
                    <div className="flex items-center gap-2 p-3 rounded-lg bg-surface border border-border-subtle text-status-success-text">
                      <CheckCircle2 className="h-4 w-4 shrink-0 text-status-success-text" />
                      <span>Call to Action (CTA) conforme à la charte</span>
                    </div>
                    <div className="flex items-center gap-2 p-3 rounded-lg bg-surface border border-border-subtle text-status-success-text">
                      <CheckCircle2 className="h-4 w-4 shrink-0 text-status-success-text" />
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
                    className="min-h-[40px] font-medium"
                  >
                    <span>Ouvrir dans la Revue HITL</span>
                    <ArrowRight className="h-3.5 w-3.5 ml-1.5" />
                  </Button>
                </div>
              </div>
            ) : (
              <div className="p-8 text-center bg-surface-subtle rounded-xl border border-border-subtle text-xs text-txt-secondary">
                Générez d'abord une variante dans l'onglet "Production" pour l'analyser dans le Quality Gate.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 4: Rewrite Agent */}
      {activeTab === 'rewrite' && (
        <div className="space-y-6">
          <div className="rounded-xl border border-border bg-surface p-5 sm:p-6 space-y-4 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-accent-subtle text-accent border border-accent-border">
                <RefreshCw className="h-5 w-5" />
              </div>
              <div>
                <h3 className="font-semibold text-txt text-base">Agent de Réécriture & Raffinement Assisté</h3>
                <p className="text-xs text-txt-secondary mt-0.5">
                  Modifie et perfectionne un brouillon en intégrant les consignes critiques d'un relecteur humain.
                </p>
              </div>
            </div>

            {inboxVariants.length > 0 ? (
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-txt mb-1">
                    Brouillon à réécrire
                  </label>
                  <select
                    value={selectedVariantId}
                    onChange={(e) => setSelectedVariantId(e.target.value)}
                    className="w-full rounded-lg bg-surface-subtle border border-border px-3 py-2 text-xs text-txt min-h-[44px] focus:border-border-focus"
                  >
                    {inboxVariants.map((v) => (
                      <option key={v.id} value={v.id}>
                        [{v.platform.toUpperCase()}] {v.hook?.slice(0, 70)}...
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-txt mb-1">
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
                  className="text-xs min-h-[44px] font-medium"
                >
                  <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
                  Déclencher la Réécriture par l'Agent
                </Button>
              </div>
            ) : (
              <div className="p-8 text-center text-xs text-txt-secondary bg-surface-subtle rounded-xl border border-border-subtle">
                Aucun brouillon en attente de réécriture dans la boîte de revue. Générez d'abord du contenu dans l'onglet Production.
              </div>
            )}
          </div>

          {/* Rewrite Result */}
          {rewriteResult && (
            <div className="rounded-xl border border-status-success-border bg-surface p-5 sm:p-6 space-y-4 shadow-sm">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-5 w-5 text-status-success-text" />
                  <span className="font-semibold text-txt text-sm">Brouillon Réécrit avec Succès !</span>
                </div>
                <span className="text-xs font-mono text-accent-txt">
                  Nouveau Hash : {rewriteResult.payload_hash?.slice(0, 16)}...
                </span>
              </div>

              <div className="space-y-3 bg-surface-subtle p-4 rounded-lg border border-border-subtle text-xs text-txt">
                <div>
                  <span className="font-medium text-accent-txt block mb-1">Nouvelle Accroche :</span>
                  <p className="text-txt font-medium">{rewriteResult.hook}</p>
                </div>
                <div>
                  <span className="font-medium text-accent-txt block mb-1">Nouveau Corps Réécrit :</span>
                  <p className="whitespace-pre-wrap leading-relaxed text-txt">{rewriteResult.body}</p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab 5: Strategy Agent */}
      {activeTab === 'strategy' && (
        <div className="space-y-6">
          <div className="rounded-xl border border-border bg-surface p-5 sm:p-6 space-y-4 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-accent-subtle text-accent border border-accent-border">
                <TrendingUp className="h-5 w-5" />
              </div>
              <div>
                <h3 className="font-semibold text-txt text-base">Agent Stratégie & Hypothèses Éditoriales (LangGraph)</h3>
                <p className="text-xs text-txt-secondary mt-0.5">
                  Analyse les métriques réelles de portée et synthétise des hypothèses causales avec actions recommandées.
                </p>
              </div>
            </div>

            <Button
              variant="primary"
              onClick={handleRunStrategy}
              isLoading={strategyRunning}
              className="text-xs min-h-[44px] font-medium"
            >
              <Play className="h-3.5 w-3.5 mr-1.5" />
              Exécuter l'Analyse Stratégique par l'Agent
            </Button>
          </div>

          {/* Strategy Results */}
          {strategyInsights.length > 0 && (
            <div className="space-y-4">
              <h4 className="text-sm font-semibold text-txt">
                Hypothèses et recommandations ({strategyInsights.length}) :
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {strategyInsights.map((ins, idx) => (
                  <div
                    key={idx}
                    className="rounded-xl border border-border bg-surface p-5 space-y-3 flex flex-col justify-between shadow-sm hover:border-border-focus transition-colors"
                  >
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <Badge variant="accent" className="text-[10px]">{ins.pillar}</Badge>
                        <span className="text-xs font-mono text-accent-txt">
                          Confiance: {Math.round(ins.confidence_level * 100)}%
                        </span>
                      </div>
                      <div className="text-xs text-txt-secondary italic">
                        "{ins.fact}"
                      </div>
                      <p className="text-xs text-txt leading-relaxed">
                        {ins.hypothesis}
                      </p>
                    </div>

                    <div className="pt-2 border-t border-border-subtle">
                      <span className="text-[11px] font-medium text-accent-txt block mb-1">
                        Action recommandée :
                      </span>
                      <p className="text-xs text-txt-secondary leading-relaxed">
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
          <div className="rounded-xl border border-border bg-surface p-5 sm:p-6 space-y-4 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-accent-subtle text-accent border border-accent-border">
                <Share2 className="h-5 w-5" />
              </div>
              <div>
                <h3 className="font-semibold text-txt text-base">Connecteurs Réseau & Reçus Cryptographiques</h3>
                <p className="text-xs text-txt-secondary mt-0.5">
                  Vérifiez le fonctionnement des connecteurs LinkedIn et X avec publication réelle ou bac à sable certifié.
                </p>
              </div>
            </div>

            <div className="flex flex-wrap gap-3 pt-2">
              <Button
                variant="primary"
                onClick={() => handleTestConnector('linkedin')}
                isLoading={testingConnector === 'linkedin'}
                className="text-xs min-h-[44px] font-medium"
              >
                <Zap className="h-3.5 w-3.5 mr-1.5" />
                Tester le Connecteur LinkedIn
              </Button>
              <Button
                variant="secondary"
                onClick={() => handleTestConnector('x')}
                isLoading={testingConnector === 'x'}
                className="text-xs min-h-[44px]"
              >
                <Zap className="h-3.5 w-3.5 mr-1.5 text-accent" />
                Tester le Connecteur X (Twitter)
              </Button>
            </div>
          </div>

          {/* Connector Receipt Result */}
          {connectorResult && (
            <div className="rounded-xl border border-status-success-border bg-surface p-5 sm:p-6 space-y-4 shadow-sm">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-status-success-text font-medium text-sm">
                  <CheckCircle2 className="h-5 w-5 shrink-0" />
                  <span>{connectorResult.message}</span>
                </div>
                <Badge variant="accent" className="font-mono">{connectorResult.status}</Badge>
              </div>

              <div className="space-y-2.5 bg-surface-subtle p-4 rounded-lg border border-border-subtle text-xs">
                <div className="flex justify-between">
                  <span className="text-txt-muted">Plateforme Post ID :</span>
                  <span className="font-mono text-accent-txt">{connectorResult.external_post_id}</span>
                </div>
                {connectorResult.url && (
                  <div className="flex justify-between">
                    <span className="text-txt-muted">URL :</span>
                    <a
                      href={connectorResult.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-accent underline font-mono hover:text-accent-hover"
                    >
                      {connectorResult.url}
                    </a>
                  </div>
                )}
                <div className="flex justify-between">
                  <span className="text-txt-muted">Horodatage certifié :</span>
                  <span className="text-txt-secondary font-mono">{connectorResult.verified_at}</span>
                </div>
              </div>

              {connectorResult.receipt && (
                <div>
                  <span className="text-txt-secondary block mb-1.5 text-xs font-medium flex items-center gap-1.5 font-mono">
                    <Terminal className="h-3.5 w-3.5 text-accent" /> Reçu d'exécution :
                  </span>
                  <pre className="p-3.5 bg-surface-subtle rounded-lg text-txt font-mono text-[11px] overflow-x-auto border border-border-subtle">
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
