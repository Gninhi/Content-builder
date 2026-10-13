import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';
import { apiClient } from '../../lib/api';
import {
  LLMProviderInfo,
  LLMModelInfo,
  WorkspaceLLMConfig,
  TaskLLMOverride,
  LLMConnectionTestResult,
} from '../../types/api';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { Skeleton } from '../common/Skeleton';
import { ErrorState } from '../common/ErrorState';
import {
  Cpu,
  CheckCircle2,
  XCircle,
  Activity,
  Save,
  RotateCcw,
  Sparkles,
  Layers,
  ShieldCheck,
} from 'lucide-react';

interface TaskMeta {
  key: string;
  name: string;
  description: string;
  recommendedTemp: number;
}

const TASKS: TaskMeta[] = [
  {
    key: 'ideation',
    name: 'Recherche & Idéation',
    description: 'Recherche de sources et génération de 10+ idées percutantes.',
    recommendedTemp: 0.3,
  },
  {
    key: 'production',
    name: 'Production Éditoriale',
    description: 'Rédaction des variantes calibrées LinkedIn et X avec hook et CTA.',
    recommendedTemp: 0.4,
  },
  {
    key: 'rewrite',
    name: 'Réécriture Interactive',
    description: 'Révision rapide suite au feedback d’un relecteur humain.',
    recommendedTemp: 0.3,
  },
  {
    key: 'strategy',
    name: 'Synthèse Stratégique',
    description: 'Analyse des métriques d’engagement et formulation d’hypothèses.',
    recommendedTemp: 0.2,
  },
];

export const LLMConfigurationSection: React.FC = () => {
  const { session, isOwner } = useAuth();
  const { showToast } = useToast();
  const canModify = Boolean(isOwner);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [providers, setProviders] = useState<LLMProviderInfo[]>([]);
  const [models, setModels] = useState<LLMModelInfo[]>([]);
  const [config, setConfig] = useState<WorkspaceLLMConfig | null>(null);
  const [initialConfig, setInitialConfig] = useState<WorkspaceLLMConfig | null>(null);
  const [saving, setSaving] = useState(false);
  const [testingProvider, setTestingProvider] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, LLMConnectionTestResult>>({});
  const [modelSearch, setModelSearch] = useState('');

  const workspaceId = session?.workspace_id || 'ws_default';

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [providersData, modelsData, configData] = await Promise.all([
        apiClient<LLMProviderInfo[]>('/v1/llm/providers'),
        apiClient<LLMModelInfo[]>('/v1/llm/models'),
        apiClient<WorkspaceLLMConfig>(`/v1/llm/config/${workspaceId}`),
      ]);
      setProviders(providersData);
      setModels(modelsData);
      setConfig(configData);
      setInitialConfig(JSON.parse(JSON.stringify(configData)));
    } catch (err: any) {
      setError(err.message || 'Impossible de charger la configuration des modèles.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [workspaceId]);

  const hasUnsavedChanges =
    Boolean(config && initialConfig) &&
    JSON.stringify(config) !== JSON.stringify(initialConfig);

  const handleTestConnection = async (providerId: string, modelId?: string) => {
    if (!canModify) return;
    setTestingProvider(providerId);
    try {
      const res = await apiClient<LLMConnectionTestResult>('/v1/llm/test-connection', {
        method: 'POST',
        body: JSON.stringify({
          provider_id: providerId,
          model_id: modelId,
        }),
      });
      setTestResults((prev) => ({ ...prev, [providerId]: res }));
      if (res.success) {
        showToast('success', `Connexion à ${providerId.toUpperCase()} réussie (${Math.round(res.latency_ms)}ms).`);
      } else {
        showToast('error', `Échec test ${providerId.toUpperCase()} : ${res.message}`);
      }
    } catch (err: any) {
      showToast('error', `Erreur test de connexion : ${err.message}`);
    } finally {
      setTestingProvider(null);
    }
  };

  const handleSaveConfig = async () => {
    if (!config || !canModify) return;
    setSaving(true);
    try {
      const updated = await apiClient<WorkspaceLLMConfig>(`/v1/llm/config/${workspaceId}`, {
        method: 'PUT',
        body: JSON.stringify({
          default_provider_id: config.default_provider_id,
          default_model_id: config.default_model_id,
          default_temperature: config.default_temperature,
          task_overrides: config.task_overrides,
          provider_settings: config.provider_settings || {},
        }),
      });
      setConfig(updated);
      setInitialConfig(JSON.parse(JSON.stringify(updated)));
      showToast('success', 'Configuration des modèles LLM enregistrée avec succès.');
    } catch (err: any) {
      showToast('error', `Erreur de sauvegarde : ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleDefaultProviderChange = (providerId: string) => {
    if (!config) return;
    const providerModels = models.filter((m) => m.provider_id === providerId);
    const newModelId = providerModels[0]?.model_id || (providerId === 'nvidia' ? 'meta/llama-3.1-70b-instruct' : 'gemini-3.8-flash');
    setConfig({
      ...config,
      default_provider_id: providerId,
      default_model_id: newModelId,
    });
  };

  const handleTaskOverrideToggle = (taskKey: string, inherit: boolean) => {
    if (!config) return;
    const overrides = { ...config.task_overrides };
    if (inherit) {
      overrides[taskKey] = {
        provider_id: config.default_provider_id,
        model_id: config.default_model_id,
        inherit_default: true,
      };
    } else {
      overrides[taskKey] = {
        provider_id: config.default_provider_id,
        model_id: config.default_model_id,
        temperature: TASKS.find((t) => t.key === taskKey)?.recommendedTemp || 0.3,
        inherit_default: false,
      };
    }
    setConfig({ ...config, task_overrides: overrides });
  };

  const handleTaskOverrideChange = (
    taskKey: string,
    updates: Partial<TaskLLMOverride>
  ) => {
    if (!config) return;
    const current = config.task_overrides[taskKey] || {
      provider_id: config.default_provider_id,
      model_id: config.default_model_id,
      inherit_default: false,
    };
    const updated: TaskLLMOverride = { ...current, ...updates };

    // If provider changed, update model to first model of that provider
    if (updates.provider_id && updates.provider_id !== current.provider_id) {
      const pModels = models.filter((m) => m.provider_id === updates.provider_id);
      updated.model_id = pModels[0]?.model_id || (updates.provider_id === 'nvidia' ? 'meta/llama-3.1-70b-instruct' : 'gemini-3.8-flash');
    }

    setConfig({
      ...config,
      task_overrides: {
        ...config.task_overrides,
        [taskKey]: updated,
      },
    });
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (error) {
    return <ErrorState message={error} onRetry={fetchData} />;
  }

  if (!config) return null;

  const filteredModelsForDefault = models.filter(
    (m) =>
      m.provider_id === config.default_provider_id &&
      (modelSearch === '' ||
        m.display_name.toLowerCase().includes(modelSearch.toLowerCase()) ||
        m.model_id.toLowerCase().includes(modelSearch.toLowerCase()))
  );

  return (
    <div className="space-y-8">
      {/* Header and save status */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border-subtle pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <Cpu className="h-5 w-5 text-accent" />
            <h3 className="text-lg sm:text-xl font-bold text-txt tracking-tight">
              Architecture Multi-Provider & Modèles LLM
            </h3>
            {hasUnsavedChanges && (
              <Badge variant="warning" className="text-[10px] animate-pulse">
                Modifications non enregistrées
              </Badge>
            )}
          </div>
          <p className="text-xs sm:text-sm text-txt-secondary mt-1">
            Gérez les moteurs de génération d’IA (Google Gemini & NVIDIA), configurez les modèles par défaut et définissez les affectations spécialisées par tâche.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {hasUnsavedChanges && (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => initialConfig && setConfig(JSON.parse(JSON.stringify(initialConfig)))}
              disabled={saving}
              className="text-xs flex items-center gap-1.5 min-h-[40px] sm:min-h-[36px]"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Réinitialiser
            </Button>
          )}
          <Button
            variant="primary"
            size="sm"
            onClick={handleSaveConfig}
            isLoading={saving}
            disabled={!canModify || !hasUnsavedChanges}
            className="text-xs flex items-center gap-1.5 min-h-[40px] sm:min-h-[36px] font-medium"
          >
            <Save className="h-3.5 w-3.5" />
            Enregistrer la configuration
          </Button>
        </div>
      </div>

      {/* Secret notice banner */}
      <div className="rounded-xl border border-border-subtle bg-surface-subtle p-4 sm:p-5 text-xs text-txt-secondary flex items-start gap-3.5 shadow-sm">
        <ShieldCheck className="h-5 w-5 text-accent shrink-0 mt-0.5" />
        <div className="space-y-1">
          <p className="font-semibold text-txt">Sécurité stricte de la chaîne d'approvisionnement IA</p>
          <p className="text-txt-secondary leading-relaxed">
            Les clés secrètes d'API (<code className="text-accent-txt font-mono bg-surface px-1 py-0.5 rounded border border-border-subtle">GOOGLE_API_KEY</code> et <code className="text-accent-txt font-mono bg-surface px-1 py-0.5 rounded border border-border-subtle">NVIDIA_API_KEY</code>) sont protégées sur le serveur et ne transitent jamais vers le client. Aucun modèle n'effectue de fallback silencieux vers un autre provider sans consentement explicite.
          </p>
        </div>
      </div>

      {/* 1. Providers Status Grid */}
      <div className="space-y-3">
        <h4 className="text-sm font-semibold text-txt flex items-center gap-2">
          <Activity className="h-4 w-4 text-accent" />
          État des Fournisseurs Disponibles
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {providers.map((p) => {
            const testResult = testResults[p.provider_id];
            const isTesting = testingProvider === p.provider_id;
            return (
              <div
                key={p.provider_id}
                className={`rounded-xl border p-5 transition-all shadow-sm ${
                  config.default_provider_id === p.provider_id
                    ? 'border-accent bg-accent-subtle/30'
                    : 'border-border bg-surface hover:border-border-focus'
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-txt text-base">
                        {p.display_name}
                      </span>
                      {p.is_configured ? (
                        <Badge variant="accent" className="text-[10px]">
                          CONFIGURÉ
                        </Badge>
                      ) : (
                        <Badge variant="warning" className="text-[10px]">
                          CLÉ ABSENTE
                        </Badge>
                      )}
                      {config.default_provider_id === p.provider_id && (
                        <Badge variant="accent" className="text-[10px]">
                          PAR DÉFAUT
                        </Badge>
                      )}
                    </div>
                    <p className="text-xs text-txt-muted mt-1 font-mono">
                      ID: {p.provider_id} • Adaptateur: {p.adapter_type}
                    </p>
                  </div>

                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => handleTestConnection(p.provider_id, p.default_model)}
                    isLoading={isTesting}
                    disabled={!p.is_configured || !canModify}
                    className="text-xs shrink-0 min-h-[38px]"
                    title={!p.is_configured ? 'Configurez la clé API sur le serveur pour tester' : 'Tester la connectivité'}
                  >
                    Tester la connexion
                  </Button>
                </div>

                {/* Diagnostics result */}
                {testResult && (
                  <div className={`mt-4 p-3 rounded-lg border text-xs flex items-center justify-between gap-2 ${
                    testResult.success
                      ? 'border-status-success-border bg-status-success-bg text-status-success-text'
                      : 'border-status-danger-border bg-status-danger-bg text-status-danger-text'
                  }`}>
                    <div className="flex items-center gap-2 truncate">
                      {testResult.success ? (
                        <CheckCircle2 className="h-4 w-4 shrink-0 text-status-success-text" />
                      ) : (
                        <XCircle className="h-4 w-4 shrink-0 text-status-danger-text" />
                      )}
                      <span className="truncate">{testResult.message}</span>
                    </div>
                    <span className="font-mono text-[11px] shrink-0">
                      {Math.round(testResult.latency_ms)}ms
                    </span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* 2. Global Default Configuration */}
      <div className="rounded-xl border border-border bg-surface p-5 sm:p-6 space-y-6 shadow-sm">
        <div className="flex items-center justify-between gap-4 border-b border-border-subtle pb-3">
          <div>
            <h4 className="text-base font-semibold text-txt flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-accent" />
              Couple Provider & Modèle Global par Défaut
            </h4>
            <p className="text-xs text-txt-secondary mt-0.5">
              Utilisé automatiquement lorsqu'aucun override spécifique de tâche n'est défini.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Provider selector */}
          <div className="space-y-1.5">
            <label className="block text-xs font-medium text-txt">
              Fournisseur par Défaut
            </label>
            <select
              value={config.default_provider_id}
              onChange={(e) => handleDefaultProviderChange(e.target.value)}
              disabled={!canModify}
              className="w-full bg-surface-subtle border border-border rounded-lg px-3 py-2 text-sm text-txt focus:outline-none focus:border-border-focus min-h-[44px]"
            >
              {providers.map((p) => (
                <option key={p.provider_id} value={p.provider_id}>
                  {p.display_name} {!p.is_configured ? '(Clé absente)' : ''}
                </option>
              ))}
            </select>
          </div>

          {/* Model selector */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="block text-xs font-medium text-txt">
                Modèle par Défaut
              </label>
              <div className="relative">
                <input
                  type="text"
                  placeholder="Filtrer..."
                  value={modelSearch}
                  onChange={(e) => setModelSearch(e.target.value)}
                  className="bg-surface-subtle border border-border rounded px-2 py-0.5 text-[11px] text-txt focus:outline-none focus:border-border-focus w-28 font-mono"
                />
              </div>
            </div>
            <select
              value={config.default_model_id}
              onChange={(e) => setConfig({ ...config, default_model_id: e.target.value })}
              disabled={!canModify}
              className="w-full bg-surface-subtle border border-border rounded-lg px-3 py-2 text-sm text-txt focus:outline-none focus:border-border-focus min-h-[44px]"
            >
              {filteredModelsForDefault.map((m) => (
                <option key={m.model_id} value={m.model_id}>
                  {m.display_name} ({m.model_id})
                </option>
              ))}
            </select>
          </div>

          {/* Temperature slider */}
          <div className="space-y-1.5">
            <div className="flex justify-between items-center text-xs">
              <span className="font-medium text-txt">Température de Génération</span>
              <span className="font-mono text-accent-txt font-semibold">{config.default_temperature.toFixed(2)}</span>
            </div>
            <input
              type="range"
              min="0.0"
              max="1.5"
              step="0.05"
              value={config.default_temperature}
              onChange={(e) => setConfig({ ...config, default_temperature: parseFloat(e.target.value) })}
              disabled={!canModify}
              className="w-full accent-accent h-2 bg-surface-subtle rounded-lg cursor-pointer mt-3"
            />
            <div className="flex justify-between text-[10px] text-txt-muted font-mono">
              <span>0.0 (Déterministe)</span>
              <span>0.7 (Équilibré)</span>
              <span>1.5 (Créatif)</span>
            </div>
          </div>
        </div>

        {/* Selected model details preview */}
        {(() => {
          const selectedModel = models.find(
            (m) => m.provider_id === config.default_provider_id && m.model_id === config.default_model_id
          );
          if (!selectedModel) return null;
          return (
            <div className="rounded-lg border border-border-subtle bg-surface-subtle p-4 space-y-2 text-xs">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-mono text-accent-txt font-semibold">{selectedModel.full_id}</span>
                <Badge variant="neutral" className="text-[10px]">
                  Provenance : {selectedModel.provenance}
                </Badge>
              </div>
              <div className="flex flex-wrap items-center gap-2 pt-1">
                <span className="text-txt-muted text-[11px]">Capacités certifiées :</span>
                {selectedModel.capabilities.structured_output && (
                  <Badge variant="accent" className="text-[10px]">Sorties structurées</Badge>
                )}
                {selectedModel.capabilities.text_generation && (
                  <Badge variant="info" className="text-[10px]">Génération texte</Badge>
                )}
                {selectedModel.capabilities.streaming && (
                  <Badge variant="neutral" className="text-[10px]">Streaming</Badge>
                )}
                {selectedModel.capabilities.vision && (
                  <Badge variant="warning" className="text-[10px]">Vision</Badge>
                )}
              </div>
            </div>
          );
        })()}
      </div>

      {/* 3. Task-Specific Overrides */}
      <div className="space-y-4">
        <div>
          <h4 className="text-base font-semibold text-txt flex items-center gap-2">
            <Layers className="h-4 w-4 text-accent" />
            Affectation Spécialisée par Tâche (Overrides)
          </h4>
          <p className="text-xs text-txt-secondary mt-0.5">
            Définit quel modèle est utilisé par chaque agent du workflow. En mode "Hériter", la tâche suit automatiquement le modèle global.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-4">
          {TASKS.map((task) => {
            const override = config.task_overrides[task.key];
            const isInheriting = !override || override.inherit_default;
            const currentProvider = isInheriting ? config.default_provider_id : override.provider_id;
            const currentModel = isInheriting ? config.default_model_id : override.model_id;
            const currentTemp = isInheriting
              ? config.default_temperature
              : override.temperature ?? task.recommendedTemp;

            const taskModels = models.filter((m) => m.provider_id === currentProvider);

            return (
              <div
                key={task.key}
                className="rounded-xl border border-border bg-surface p-5 space-y-4 shadow-sm"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border-subtle pb-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-txt text-sm">{task.name}</span>
                      <code className="text-[11px] text-accent-txt font-mono">[{task.key}]</code>
                      {isInheriting ? (
                        <Badge variant="neutral" className="text-[10px]">HÉRITE DU DÉFAUT</Badge>
                      ) : (
                        <Badge variant="accent" className="text-[10px]">OVERRIDE DÉDIÉ</Badge>
                      )}
                    </div>
                    <p className="text-xs text-txt-secondary mt-0.5 leading-relaxed">{task.description}</p>
                  </div>

                  <div className="flex items-center gap-2">
                    <Button
                      variant={isInheriting ? 'primary' : 'secondary'}
                      size="sm"
                      disabled={!canModify}
                      onClick={() => handleTaskOverrideToggle(task.key, true)}
                      className="text-xs min-h-[38px]"
                    >
                      Hériter
                    </Button>
                    <Button
                      variant={!isInheriting ? 'primary' : 'secondary'}
                      size="sm"
                      disabled={!canModify}
                      onClick={() => handleTaskOverrideToggle(task.key, false)}
                      className="text-xs min-h-[38px]"
                    >
                      Personnaliser
                    </Button>
                  </div>
                </div>

                {/* Configuration controls for this task */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="space-y-1">
                    <label className="text-[11px] text-txt-muted font-medium">Fournisseur</label>
                    <select
                      value={currentProvider}
                      disabled={isInheriting || !canModify}
                      onChange={(e) => handleTaskOverrideChange(task.key, { provider_id: e.target.value })}
                      className="w-full bg-surface-subtle border border-border rounded-lg px-2.5 py-1.5 text-xs text-txt disabled:opacity-50 min-h-[40px] focus:border-border-focus"
                    >
                      {providers.map((p) => (
                        <option key={p.provider_id} value={p.provider_id}>
                          {p.display_name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="space-y-1">
                    <label className="text-[11px] text-txt-muted font-medium">Modèle Sélectionné</label>
                    <select
                      value={currentModel}
                      disabled={isInheriting || !canModify}
                      onChange={(e) => handleTaskOverrideChange(task.key, { model_id: e.target.value })}
                      className="w-full bg-surface-subtle border border-border rounded-lg px-2.5 py-1.5 text-xs text-txt disabled:opacity-50 min-h-[40px] focus:border-border-focus"
                    >
                      {taskModels.map((m) => (
                        <option key={m.model_id} value={m.model_id}>
                          {m.display_name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="space-y-1">
                    <div className="flex justify-between items-center text-[11px]">
                      <span className="text-txt-muted font-medium">Température</span>
                      <span className="font-mono text-accent-txt font-semibold">{currentTemp.toFixed(2)}</span>
                    </div>
                    <input
                      type="range"
                      min="0.0"
                      max="1.5"
                      step="0.05"
                      value={currentTemp}
                      disabled={isInheriting || !canModify}
                      onChange={(e) => handleTaskOverrideChange(task.key, { temperature: parseFloat(e.target.value) })}
                      className="w-full accent-accent h-1.5 bg-surface-subtle rounded-lg cursor-pointer mt-2 disabled:opacity-50"
                    />
                  </div>
                </div>

                {/* Effective configuration summary */}
                <div className="text-[11px] text-txt-muted flex items-center gap-2 pt-1 font-mono">
                  <span>Configuration effective :</span>
                  <span className="text-accent-txt font-medium">
                    {currentProvider}:{currentModel} (T={currentTemp.toFixed(2)})
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
