import React, { useState, useEffect } from 'react';
import { useLanguage } from '../context/LanguageContext';
import { useAuth } from '../context/AuthContext';
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
} from 'lucide-react';

export const SettingsScreen: React.FC = () => {
  const { t } = useLanguage();
  const { session, isOwner } = useAuth();

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
    } catch (err: any) {
      alert(`Erreur de modification du Kill Switch : ${err.message}`);
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
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-white tracking-tight">
              {t.settings.title}
            </h2>
            <Badge variant="success" className="text-xs">
              Rôle Actuel : {session?.role}
            </Badge>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Gouvernance d'urgence, plafonds de fréquence et intégrité opérationnelle.
          </p>
        </div>
      </div>

      {!isOwner && (
        <div className="rounded-xl border border-amber-500/30 bg-amber-950/20 p-4 text-xs text-amber-300 flex items-center gap-3">
          <Lock className="h-4 w-4 text-amber-400 shrink-0" />
          <span>
            Les paramètres de sécurité critique sont en lecture seule pour votre rôle ({session?.role}). Seul le rôle Owner peut commuter le Kill Switch.
          </span>
        </div>
      )}

      {/* Emergency Kill Switch Card */}
      <div className={`rounded-2xl border p-6 transition-all ${
        isKillSwitchActive
          ? 'border-red-500/60 bg-red-950/20 shadow-lg shadow-red-950/30'
          : 'border-slate-800 bg-slate-900/60'
      }`}>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <AlertTriangle className={`h-5 w-5 ${isKillSwitchActive ? 'text-red-400' : 'text-amber-400'}`} />
              <h3 className="font-bold text-white text-base">
                {t.settings.kill_switch_title}
              </h3>
              <Badge variant={isKillSwitchActive ? 'danger' : 'success'} className="text-xs font-mono">
                {isKillSwitchActive ? 'KILL SWITCH ACTIF' : 'NORMAL'}
              </Badge>
            </div>
            <p className="text-xs text-slate-400 max-w-xl">
              {t.settings.kill_switch_desc}
            </p>
          </div>

          <div>
            <Button
              variant={isKillSwitchActive ? 'secondary' : 'danger'}
              disabled={!isOwner}
              onClick={() => setKillSwitchModalOpen(true)}
              className="text-xs font-semibold uppercase tracking-wider"
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
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 space-y-4">
          <h3 className="text-sm font-semibold text-white">
            Plafonds de Publication & Garde-Fous
          </h3>
          <div className="space-y-3 text-xs">
            <div className="flex justify-between p-3 rounded-xl border border-slate-800 bg-slate-950/60">
              <span className="text-slate-400">Plafond horaire de diffusion :</span>
              <span className="font-semibold text-slate-200">5 posts / heure</span>
            </div>
            <div className="flex justify-between p-3 rounded-xl border border-slate-800 bg-slate-950/60">
              <span className="text-slate-400">Intervalle anti-collision :</span>
              <span className="font-semibold text-slate-200">30 minutes</span>
            </div>
            <div className="flex justify-between p-3 rounded-xl border border-slate-800 bg-slate-950/60">
              <span className="text-slate-400">Règle de publication :</span>
              <span className="font-semibold text-emerald-400">Validation humaine obligatoire (HITL)</span>
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 space-y-4">
          <h3 className="text-sm font-semibold text-white">
            Environnement & Sécurité API
          </h3>
          <div className="space-y-3 text-xs">
            <div className="flex justify-between p-3 rounded-xl border border-slate-800 bg-slate-950/60">
              <span className="text-slate-400">Mode d'exécution :</span>
              <Badge variant="warning" className="text-[10px] uppercase font-bold">
                SANDBOX SÉCURISÉ
              </Badge>
            </div>
            <div className="flex justify-between p-3 rounded-xl border border-slate-800 bg-slate-950/60">
              <span className="text-slate-400">Content Security Policy (CSP) :</span>
              <span className="font-mono text-cyan-400">default-src 'self'</span>
            </div>
            <div className="flex justify-between p-3 rounded-xl border border-slate-800 bg-slate-950/60">
              <span className="text-slate-400">Stockage des jetons :</span>
              <span className="font-semibold text-slate-200">Mémoire volatile (Zero LocalStorage)</span>
            </div>
          </div>
        </div>
      </div>

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
