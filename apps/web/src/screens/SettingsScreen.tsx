import React, { useState, useEffect } from 'react';
import { useLanguage } from '../context/LanguageContext';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { apiClient } from '../lib/api';
import { Workspace } from '../types/api';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { Skeleton } from '../components/common/Skeleton';
import { ErrorState } from '../components/common/ErrorState';
import { ConfirmDialog } from '../components/common/ConfirmDialog';
import {
  AlertTriangle,
  Lock,
  Cpu,
  ShieldAlert,
} from 'lucide-react';
import { LLMConfigurationSection } from '../components/settings/LLMConfigurationSection';

export const SettingsScreen: React.FC = () => {
  const { t } = useLanguage();
  const { session, isOwner } = useAuth();
  const { showToast } = useToast();

  const [activeTab, setActiveTab] = useState<'llm' | 'governance'>('llm');
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Kill switch modal state
  const [killSwitchModalOpen, setKillSwitchModalOpen] = useState(false);
  const [togglingKillSwitch, setTogglingKillSwitch] = useState(false);

  const fetchWorkspace = async () => {
    setLoading(true);
    setError(null);
    const wsId = session?.workspace_id || 'ws_default';
    try {
      const data = await apiClient<Workspace>(`/v1/workspaces/${wsId}`);
      setWorkspace(data);
    } catch (err: any) {
      setError(err.message || 'Impossible de récupérer les paramètres de gouvernance.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWorkspace();
  }, [session?.workspace_id]);

  const handleToggleKillSwitch = async () => {
    if (!workspace || !isOwner) return;
    setTogglingKillSwitch(true);
    const targetState = !workspace.kill_switch_enabled;
    try {
      await apiClient(`/v1/workspaces/${workspace.id}/kill-switch`, {
        method: 'POST',
        body: JSON.stringify({ enabled: targetState }),
      });
      await fetchWorkspace();
      setKillSwitchModalOpen(false);
      showToast(
        targetState ? 'warning' : 'success',
        targetState
          ? 'KILL SWITCH ACTIVÉ : Toutes les publications sont verrouillées en urgence.'
          : 'KILL SWITCH DÉSACTIVÉ : Système nominal rétabli.'
      );
    } catch (err: any) {
      showToast('error', `Erreur de modification du Kill Switch : ${err.message}`);
    } finally {
      setTogglingKillSwitch(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (error) {
    return <ErrorState message={error} onRetry={fetchWorkspace} />;
  }

  const isKillSwitchActive = Boolean(workspace?.kill_switch_enabled);

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border-subtle pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <h2 className="text-xl sm:text-2xl font-bold text-txt tracking-tight">
              {t.settings.title}
            </h2>
            <Badge variant="accent" className="text-xs">
              Rôle : {session?.role}
            </Badge>
          </div>
          <p className="text-xs sm:text-sm text-txt-secondary mt-1">
            Gouvernance d'urgence, plafonds de fréquence et intégrité opérationnelle.
          </p>
        </div>
      </div>

      {/* Settings Navigation Tabs */}
      <div className="flex border-b border-border-subtle gap-6" role="tablist">
        <button
          role="tab"
          aria-selected={activeTab === 'llm'}
          onClick={() => setActiveTab('llm')}
          className={`pb-3 text-sm font-medium flex items-center gap-2 border-b-2 transition-colors min-h-[44px] ${
            activeTab === 'llm'
              ? 'border-accent text-accent'
              : 'border-transparent text-txt-secondary hover:text-txt'
          }`}
        >
          <Cpu className="h-4 w-4" />
          Modèles & Providers LLM
        </button>
        <button
          role="tab"
          aria-selected={activeTab === 'governance'}
          onClick={() => setActiveTab('governance')}
          className={`pb-3 text-sm font-medium flex items-center gap-2 border-b-2 transition-colors min-h-[44px] ${
            activeTab === 'governance'
              ? 'border-accent text-accent'
              : 'border-transparent text-txt-secondary hover:text-txt'
          }`}
        >
          <ShieldAlert className="h-4 w-4" />
          Gouvernance & Kill Switch
        </button>
      </div>

      {activeTab === 'llm' ? (
        <LLMConfigurationSection />
      ) : (
        <div className="space-y-8">
          {!isOwner && (
            <div className="rounded-xl border border-status-warning-border bg-status-warning-bg p-4 text-xs sm:text-sm text-status-warning-text flex items-center gap-3">
              <Lock className="h-5 w-5 shrink-0 text-status-warning-text" />
              <span>
                Les paramètres de sécurité critique sont en lecture seule pour votre rôle ({session?.role}). Seul le rôle Owner peut commuter le Kill Switch.
              </span>
            </div>
          )}

          {/* Emergency Kill Switch Card */}
          <div className={`rounded-xl border p-6 transition-all shadow-sm ${
            isKillSwitchActive
              ? 'border-status-danger-border bg-status-danger-bg'
              : 'border-border bg-surface'
          }`}>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2.5">
                  <AlertTriangle className={`h-5 w-5 ${isKillSwitchActive ? 'text-status-danger-text' : 'text-accent'}`} />
                  <h3 className="font-semibold text-txt text-base">
                    {t.settings.kill_switch_title}
                  </h3>
                  <Badge variant={isKillSwitchActive ? 'danger' : 'success'} withDot className="text-xs">
                    {isKillSwitchActive ? 'KILL SWITCH ACTIF' : 'NOMINAL'}
                  </Badge>
                </div>
                <p className="text-xs text-txt-secondary max-w-xl leading-relaxed">
                  {t.settings.kill_switch_desc}
                </p>
              </div>

              <div>
                <Button
                  variant={isKillSwitchActive ? 'secondary' : 'danger'}
                  disabled={!isOwner}
                  onClick={() => setKillSwitchModalOpen(true)}
                  className="text-xs font-medium min-h-[44px] px-4"
                >
                  {isKillSwitchActive
                    ? t.settings.deactivate_kill_switch
                    : t.settings.activate_kill_switch}
                </Button>
              </div>
            </div>
          </div>

          {/* Rate Limits & Environment Configuration */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="rounded-xl border border-border bg-surface p-6 space-y-4 shadow-sm">
              <h3 className="text-sm font-semibold text-txt flex items-center justify-between">
                <span>Plafonds de Publication & Garde-Fous</span>
                <span className="text-[11px] text-txt-muted font-normal">Cadence nominale</span>
              </h3>
              <div className="space-y-2.5 text-xs">
                <div className="flex justify-between p-3.5 rounded-lg border border-border-subtle bg-surface-subtle">
                  <span className="text-txt-muted">Plafond horaire de diffusion :</span>
                  <span className="font-medium font-mono text-accent-txt">5 posts / heure</span>
                </div>
                <div className="flex justify-between p-3.5 rounded-lg border border-border-subtle bg-surface-subtle">
                  <span className="text-txt-muted">Intervalle anti-collision :</span>
                  <span className="font-medium font-mono text-txt">30 minutes</span>
                </div>
                <div className="flex justify-between p-3.5 rounded-lg border border-border-subtle bg-surface-subtle">
                  <span className="text-txt-muted">Règle de publication :</span>
                  <span className="font-medium text-status-success-text">Validation humaine obligatoire (HITL)</span>
                </div>
              </div>
            </div>

            <div className="rounded-xl border border-border bg-surface p-6 space-y-4 shadow-sm">
              <h3 className="text-sm font-semibold text-txt flex items-center justify-between">
                <span>Environnement & Sécurité API</span>
                <span className="text-[11px] text-status-success-text font-normal">Audit 0-fuite</span>
              </h3>
              <div className="space-y-2.5 text-xs">
                <div className="flex justify-between p-3.5 rounded-lg border border-border-subtle bg-surface-subtle">
                  <span className="text-txt-muted">Mode d'exécution :</span>
                  <Badge variant="accent" className="text-[10px]">
                    SANDBOX SÉCURISÉ
                  </Badge>
                </div>
                <div className="flex justify-between p-3.5 rounded-lg border border-border-subtle bg-surface-subtle">
                  <span className="text-txt-muted">Content Security Policy (CSP) :</span>
                  <span className="font-mono text-accent-txt">default-src 'self'</span>
                </div>
                <div className="flex justify-between p-3.5 rounded-lg border border-border-subtle bg-surface-subtle">
                  <span className="text-txt-muted">Stockage des jetons :</span>
                  <span className="font-medium text-txt">Mémoire volatile (Zero LocalStorage)</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Confirmation Modal for Kill Switch Toggle */}
      <ConfirmDialog
        isOpen={killSwitchModalOpen}
        onClose={() => setKillSwitchModalOpen(false)}
        onConfirm={handleToggleKillSwitch}
        title={
          isKillSwitchActive
            ? 'Réarmer le système de publication ?'
            : "ACTIVATION D'URGENCE DU KILL SWITCH"
        }
        message={
          isKillSwitchActive
            ? 'Cette action réautorisera le worker de publication à exécuter les tâches programmées.'
            : 'ATTENTION : L’activation du Kill Switch bloque immédiatement toutes les publications automatiques et stoppe les envois vers LinkedIn et X.'
        }
        confirmText={isKillSwitchActive ? 'Réarmer' : 'Activer le Kill Switch'}
        variant={isKillSwitchActive ? 'primary' : 'danger'}
        isLoading={togglingKillSwitch}
      />
    </div>
  );
};
