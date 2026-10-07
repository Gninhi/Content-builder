import React, { useState, useEffect } from 'react';
import { useLanguage } from '../context/LanguageContext';
import { useAuth } from '../context/AuthContext';
import { apiClient } from '../lib/api';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { Skeleton } from '../components/common/Skeleton';
import { ErrorState } from '../components/common/ErrorState';
import { ConfirmDialog } from '../components/common/ConfirmDialog';
import {
  Share2,
  ExternalLink,
  Unlink,
  RefreshCw,
  Lock,
} from 'lucide-react';

interface AccountInfo {
  id: string;
  provider: string;
  account_id: string;
  account_name: string;
  status: string;
  scopes: string[];
  expires_at?: string;
}

export const ConnectionsScreen: React.FC = () => {
  const { t } = useLanguage();
  const { session, isOwner } = useAuth();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [accounts, setAccounts] = useState<AccountInfo[]>([]);

  // Disconnect confirmation
  const [disconnectTarget, setDisconnectTarget] = useState<AccountInfo | null>(null);
  const [disconnecting, setDisconnecting] = useState(false);

  // Connecting state
  const [connectingProvider, setConnectingProvider] = useState<string | null>(null);

  const fetchAccounts = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient<{ accounts: AccountInfo[] }>('/v1/oauth/accounts');
      setAccounts(res.accounts || []);
    } catch (err: any) {
      setError(err.message || 'Impossible de récupérer les comptes connectés.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAccounts();
  }, [session?.workspace_id]);

  const handleStartOAuth = async (provider: 'linkedin' | 'x') => {
    if (!isOwner) {
      alert('Seul le rôle Owner peut autoriser de nouveaux comptes sociaux.');
      return;
    }

    setConnectingProvider(provider);
    try {
      const res = await apiClient<{ authorization_url: string; state: string }>(
        `/v1/oauth/start/${provider}`
      );
      if (res.authorization_url) {
        window.location.href = res.authorization_url;
      }
    } catch (err: any) {
      alert(`Erreur d'initialisation OAuth : ${err.message}`);
    } finally {
      setConnectingProvider(null);
    }
  };

  const handleDisconnect = async () => {
    if (!disconnectTarget) return;
    setDisconnecting(true);
    try {
      await apiClient(`/v1/oauth/disconnect/${disconnectTarget.provider}`, {
        method: 'POST',
        body: JSON.stringify({ account_id: disconnectTarget.account_id }),
      });
      await fetchAccounts();
      setDisconnectTarget(null);
    } catch (err: any) {
      alert(`Erreur de déconnexion : ${err.message}`);
    } finally {
      setDisconnecting(false);
    }
  };

  const getAccount = (prov: string) => accounts.find((a) => a.provider.toLowerCase() === prov.toLowerCase());

  const linkedIn = getAccount('linkedin');
  const xAccount = getAccount('x');

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Skeleton className="h-64 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      </div>
    );
  }

  if (error) {
    return <ErrorState message={error} onRetry={fetchAccounts} />;
  }

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">
            {t.connections.title}
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Comptes sociaux officiels connectés via OAuth 2.0 PKCE avec stockage chiffré AES-GCM.
          </p>
        </div>

        <Button variant="ghost" size="sm" onClick={fetchAccounts} className="text-xs text-slate-400">
          <RefreshCw className="h-3.5 w-3.5 mr-1" />
          Actualiser
        </Button>
      </div>

      {/* Security Info Banner */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 text-xs text-slate-400 flex items-start gap-3">
        <Lock className="h-4 w-4 text-cyan-400 shrink-0 mt-0.5" />
        <div>
          <strong className="text-slate-200 block mb-0.5">Coffre-fort à jetons isolé</strong>
          <span>
            Les tokens OAuth ne transitent jamais en clair côté client et sont chiffrés au repos en base de données avec rotation des clés AES-256.
          </span>
        </div>
      </div>

      {/* Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* LinkedIn Account Card */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 flex flex-col justify-between space-y-5">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#0077b5]/20 text-[#0077b5] border border-[#0077b5]/30">
                  <Share2 className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="font-bold text-white text-base">LinkedIn</h3>
                  <span className="text-xs text-slate-400 font-mono">w_member_social</span>
                </div>
              </div>

              <Badge variant={linkedIn ? 'success' : 'neutral'} className="text-xs">
                {linkedIn ? t.connections.status_connected : t.connections.status_disconnected}
              </Badge>
            </div>

            {linkedIn ? (
              <div className="space-y-3 rounded-xl bg-slate-950/60 p-4 border border-slate-800 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-400">Compte membre :</span>
                  <span className="font-semibold text-slate-200">{linkedIn.account_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">ID d'entité :</span>
                  <span className="font-mono text-slate-400 truncate max-w-[180px]">{linkedIn.account_id}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Scopes autorisés :</span>
                  <span className="text-cyan-400">{linkedIn.scopes?.join(', ') || 'N/A'}</span>
                </div>
              </div>
            ) : (
              <p className="text-xs text-slate-400">
                Connectez un profil ou une page LinkedIn pour permettre la planification et la publication par les agents.
              </p>
            )}
          </div>

          <div className="pt-2">
            {linkedIn ? (
              <div className="flex gap-2">
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={!isOwner}
                  onClick={() => handleStartOAuth('linkedin')}
                  className="flex-1 text-xs"
                >
                  Reconnecter
                </Button>
                <Button
                  variant="danger"
                  size="sm"
                  disabled={!isOwner}
                  onClick={() => setDisconnectTarget(linkedIn)}
                  className="text-xs"
                >
                  <Unlink className="h-3.5 w-3.5 mr-1" />
                  Déconnecter
                </Button>
              </div>
            ) : (
              <Button
                variant="primary"
                disabled={!isOwner || connectingProvider === 'linkedin'}
                isLoading={connectingProvider === 'linkedin'}
                onClick={() => handleStartOAuth('linkedin')}
                className="w-full justify-center text-xs"
              >
                <span>{t.connections.action_connect} LinkedIn</span>
                <ExternalLink className="h-3.5 w-3.5 ml-1" />
              </Button>
            )}
          </div>
        </div>

        {/* X (Twitter) Account Card */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 flex flex-col justify-between space-y-5">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-800 text-white border border-slate-700">
                  <span className="font-bold text-lg">𝕏</span>
                </div>
                <div>
                  <h3 className="font-bold text-white text-base">X (Twitter)</h3>
                  <span className="text-xs text-slate-400 font-mono">tweet.write, offline.access</span>
                </div>
              </div>

              <Badge variant={xAccount ? 'success' : 'neutral'} className="text-xs">
                {xAccount ? t.connections.status_connected : t.connections.status_disconnected}
              </Badge>
            </div>

            {xAccount ? (
              <div className="space-y-3 rounded-xl bg-slate-950/60 p-4 border border-slate-800 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-400">Compte membre :</span>
                  <span className="font-semibold text-slate-200">{xAccount.account_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Identifiant :</span>
                  <span className="font-mono text-cyan-400">{xAccount.account_id}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Scopes autorisés :</span>
                  <span className="text-cyan-400">{xAccount.scopes?.join(', ') || 'N/A'}</span>
                </div>
              </div>
            ) : (
              <p className="text-xs text-slate-400">
                Connectez votre compte X pour diffuser des posts concis et des threads validés en revue humaine.
              </p>
            )}
          </div>

          <div className="pt-2">
            {xAccount ? (
              <div className="flex gap-2">
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={!isOwner}
                  onClick={() => handleStartOAuth('x')}
                  className="flex-1 text-xs"
                >
                  Reconnecter
                </Button>
                <Button
                  variant="danger"
                  size="sm"
                  disabled={!isOwner}
                  onClick={() => setDisconnectTarget(xAccount)}
                  className="text-xs"
                >
                  <Unlink className="h-3.5 w-3.5 mr-1" />
                  Déconnecter
                </Button>
              </div>
            ) : (
              <Button
                variant="primary"
                disabled={!isOwner || connectingProvider === 'x'}
                isLoading={connectingProvider === 'x'}
                onClick={() => handleStartOAuth('x')}
                className="w-full justify-center text-xs"
              >
                <span>{t.connections.action_connect} X</span>
                <ExternalLink className="h-3.5 w-3.5 ml-1" />
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Disconnect Confirmation Modal */}
      <ConfirmDialog
        isOpen={Boolean(disconnectTarget)}
        onClose={() => setDisconnectTarget(null)}
        onConfirm={handleDisconnect}
        title="Confirmer la révocation du compte"
        message={t.connections.confirm_disconnect_msg}
        confirmText="Déconnecter et révoquer les clés"
        variant="danger"
        isLoading={disconnecting}
      />
    </div>
  );
};
