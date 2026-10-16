import React, { useState, useEffect } from 'react';
import { useLanguage } from '../context/LanguageContext';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { apiClient } from '../lib/api';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { Skeleton } from '../components/common/Skeleton';
import { ErrorState } from '../components/common/ErrorState';
import { ConfirmDialog } from '../components/common/ConfirmDialog';
import { Dialog } from '../components/common/Dialog';
import {
  Share2,
  ExternalLink,
  Unlink,
  RefreshCw,
  Lock,
  CheckCircle2,
  Zap,
  Terminal,
  ShieldAlert,
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
  const { showToast } = useToast();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [accounts, setAccounts] = useState<AccountInfo[]>([]);

  // Disconnect confirmation
  const [disconnectTarget, setDisconnectTarget] = useState<AccountInfo | null>(null);
  const [disconnecting, setDisconnecting] = useState(false);

  // Connecting state
  const [connectingProvider, setConnectingProvider] = useState<string | null>(null);
  const [sandboxConnecting, setSandboxConnecting] = useState<string | null>(null);

  // Testing connection state
  const [testingProvider, setTestingProvider] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<{
    status: string;
    provider: string;
    external_post_id: string;
    url?: string;
    verified_at: string;
    receipt?: any;
    message: string;
  } | null>(null);

  const fetchAccounts = async (silent = false) => {
    if (!silent) setLoading(true);
    setError(null);
    try {
      const res = await apiClient<{ accounts: AccountInfo[] }>('/v1/oauth/accounts');
      setAccounts(res.accounts || []);
    } catch (err: any) {
      if (!silent) {
        setError(err.message || 'Impossible de récupérer les comptes connectés.');
      }
    } finally {
      if (!silent) setLoading(false);
    }
  };

  useEffect(() => {
    fetchAccounts();
  }, [session?.workspace_id]);

  // Listen for OAuth completion message from the opened external tab
  useEffect(() => {
    const handleOAuthMessage = (event: MessageEvent) => {
      // Validate origin to prevent cross-site message injection or spoofing
      const trustedOrigins = [
        window.location.origin,
        'http://localhost:8000',
        'http://127.0.0.1:8000',
        'http://localhost:3000',
        'http://127.0.0.1:3000'
      ];
      if (!trustedOrigins.includes(event.origin)) {
        return;
      }
      if (event.data?.type === 'CONTENTOPS_OAUTH_SUCCESS') {
        const prov = String(event.data.provider || '').toUpperCase();
        showToast('success', `Compte ${prov} connecté et vérifié avec succès !`);
        fetchAccounts(true);
      } else if (event.data?.type === 'CONTENTOPS_OAUTH_ERROR') {
        showToast('error', `Échec d'autorisation OAuth : ${event.data.error || 'Erreur inconnue'}`);
      }
    };

    window.addEventListener('message', handleOAuthMessage);
    return () => window.removeEventListener('message', handleOAuthMessage);
  }, [showToast]);

  // Open OAuth authorization flow in an EXTERNAL TAB
  const handleStartOAuth = async (provider: 'linkedin' | 'x') => {
    if (!isOwner) {
      showToast('error', 'Seul le rôle Owner peut autoriser de nouveaux comptes sociaux.');
      return;
    }

    setConnectingProvider(provider);
    try {
      const res = await apiClient<{ authorization_url: string; state: string }>(
        `/v1/oauth/start/${provider}`
      );
      if (res.authorization_url) {
        // Must open in an external tab to preserve application session and JWT
        window.open(res.authorization_url, '_blank', 'noopener,noreferrer');
        showToast(
          'info',
          `Ouverture de la fenêtre d'autorisation ${provider.toUpperCase()} dans un nouvel onglet...`
        );

        // Start background polling to detect callback completion
        let pollCount = 0;
        const interval = setInterval(async () => {
          pollCount++;
          try {
            const accRes = await apiClient<{ accounts: AccountInfo[] }>('/v1/oauth/accounts');
            const found = accRes.accounts?.some(
              (a) => a.provider.toLowerCase() === provider.toLowerCase()
            );
            if (found) {
              clearInterval(interval);
              setAccounts(accRes.accounts);
              showToast('success', `Compte ${provider.toUpperCase()} synchronisé avec succès !`);
            }
          } catch (e) {
            // Ignore polling errors
          }
          if (pollCount >= 30) {
            clearInterval(interval);
          }
        }, 3000);
      }
    } catch (err: any) {
      showToast('error', `Erreur d'initialisation OAuth : ${err.message}`);
    } finally {
      setConnectingProvider(null);
    }
  };

  // Instant sandbox / test connection for local testing
  const handleSandboxConnect = async (provider: 'linkedin' | 'x') => {
    if (!isOwner) {
      showToast('error', 'Seul le rôle Owner peut connecter des comptes sociaux.');
      return;
    }
    setSandboxConnecting(provider);
    try {
      await apiClient(`/v1/oauth/sandbox-connect/${provider}`, {
        method: 'POST',
      });
      showToast('success', `Compte ${provider.toUpperCase()} connecté en coffre-fort chiffré !`);
      await fetchAccounts(true);
    } catch (err: any) {
      showToast('error', `Erreur sandbox : ${err.message}`);
    } finally {
      setSandboxConnecting(null);
    }
  };

  // Test connector execution and cryptographic receipt
  const handleTestConnection = async (provider: string) => {
    setTestingProvider(provider);
    setTestResult(null);
    try {
      const res = await apiClient<any>(`/v1/oauth/test-connection/${provider}`, {
        method: 'POST',
      });
      setTestResult(res);
      showToast('success', `Connecteur ${provider.toUpperCase()} vérifié avec succès !`);
    } catch (err: any) {
      showToast('error', `Échec du test de connexion : ${err.message}`);
    } finally {
      setTestingProvider(null);
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
      showToast('info', `Compte ${disconnectTarget.provider.toUpperCase()} déconnecté et révoqué.`);
      await fetchAccounts(true);
      setDisconnectTarget(null);
    } catch (err: any) {
      showToast('error', `Erreur de déconnexion : ${err.message}`);
    } finally {
      setDisconnecting(false);
    }
  };

  const getAccount = (prov: string) =>
    accounts.find((a) => a.provider.toLowerCase() === prov.toLowerCase());

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
    return <ErrorState message={error} onRetry={() => fetchAccounts()} />;
  }

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border-subtle pb-5">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold text-txt tracking-tight">
            {t.connections.title}
          </h2>
          <p className="text-xs sm:text-sm text-txt-secondary mt-1">
            Connecteurs officiels OAuth 2.0 PKCE. Connexions ouvertes en onglet externe pour garantir la persistance de session.
          </p>
        </div>

        <Button
          variant="secondary"
          size="sm"
          onClick={() => fetchAccounts()}
          className="text-xs min-h-[40px] sm:min-h-[36px]"
          title="Actualiser les statuts"
        >
          <RefreshCw className="h-3.5 w-3.5 mr-1.5 text-txt-muted" />
          Actualiser
        </Button>
      </div>

      {/* Security Info Banner */}
      <div className="rounded-xl border border-border-subtle bg-surface-subtle p-4 sm:p-5 text-xs text-txt-secondary flex items-start gap-3.5 shadow-sm">
        <Lock className="h-4 w-4 text-accent shrink-0 mt-0.5" />
        <div>
          <strong className="text-txt font-semibold block mb-1">Sécurité Zéro-Fuite & Coffre-Fort Chiffré</strong>
          <span className="leading-relaxed text-txt-secondary">
            Les jetons d'accès ne transitent jamais dans l'URL ni dans le navigateur. Ils sont scellés côté serveur en base de données avec AES-256-GCM et clés tournantes (AAD lié au workspace).
          </span>
        </div>
      </div>

      {!isOwner && (
        <div className="rounded-xl border border-status-warning-border bg-status-warning-bg p-4 text-xs sm:text-sm text-status-warning-text flex items-center gap-3">
          <ShieldAlert className="h-5 w-5 shrink-0 text-status-warning-text" />
          <span>
            Vous êtes connecté avec le rôle <strong>{session?.role}</strong>. Seul le rôle <strong>Owner</strong> est habilité à connecter ou révoquer les comptes tiers. Vous pouvez changer de rôle via le sélecteur supérieur pour tester.
          </span>
        </div>
      )}

      {/* Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* LinkedIn Account Card */}
        <div className="rounded-xl border border-border bg-surface p-6 flex flex-col justify-between space-y-5 shadow-sm hover:border-border-focus transition-colors">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-surface-subtle text-accent border border-border-subtle">
                  <Share2 className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="font-semibold text-txt text-base">LinkedIn</h3>
                  <span className="text-xs text-txt-muted font-mono">w_member_social</span>
                </div>
              </div>

              <Badge
                variant={linkedIn ? 'success' : 'neutral'}
                withDot
                className="text-xs"
              >
                {linkedIn ? t.connections.status_connected : t.connections.status_disconnected}
              </Badge>
            </div>

            {linkedIn ? (
              <div className="space-y-2.5 rounded-lg bg-surface-subtle p-4 border border-border-subtle text-xs">
                <div className="flex justify-between">
                  <span className="text-txt-muted">Compte membre :</span>
                  <span className="font-medium text-txt">{linkedIn.account_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-txt-muted">ID d'entité :</span>
                  <span className="font-mono text-accent-txt truncate max-w-[180px]">{linkedIn.account_id}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-txt-muted">Scopes autorisés :</span>
                  <span className="text-txt-secondary font-mono">{linkedIn.scopes?.join(', ') || 'N/A'}</span>
                </div>
              </div>
            ) : (
              <p className="text-xs text-txt-secondary leading-relaxed">
                Connectez un profil ou une page LinkedIn pour permettre la planification et la publication par les agents.
              </p>
            )}
          </div>

          <div className="pt-2 space-y-2.5">
            {linkedIn ? (
              <div className="space-y-2">
                <div className="flex gap-2">
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => handleTestConnection('linkedin')}
                    isLoading={testingProvider === 'linkedin'}
                    className="flex-1 text-xs min-h-[44px] font-medium"
                    title="Vérifier la validité du connecteur et tester la publication"
                  >
                    <Zap className="h-3.5 w-3.5 mr-1.5" />
                    Tester le connecteur
                  </Button>
                  <Button
                    variant="danger"
                    size="sm"
                    disabled={!isOwner}
                    onClick={() => setDisconnectTarget(linkedIn)}
                    className="text-xs min-h-[44px]"
                    title={!isOwner ? 'Réservé au rôle Owner' : 'Déconnecter le compte'}
                  >
                    <Unlink className="h-3.5 w-3.5 mr-1.5" />
                    Déconnecter
                  </Button>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={!isOwner}
                  onClick={() => handleStartOAuth('linkedin')}
                  className="w-full text-xs text-txt-muted hover:text-txt min-h-[40px]"
                  title="Ouvrir à nouveau la fenêtre d'autorisation dans un autre onglet"
                >
                  <ExternalLink className="h-3 w-3 mr-1.5" />
                  Renouveler l'autorisation (Nouvel onglet)
                </Button>
              </div>
            ) : (
              <div className="space-y-2.5">
                <Button
                  variant="primary"
                  disabled={!isOwner || connectingProvider === 'linkedin'}
                  isLoading={connectingProvider === 'linkedin'}
                  onClick={() => handleStartOAuth('linkedin')}
                  className="w-full justify-center text-xs min-h-[44px] font-medium"
                  title={!isOwner ? 'Réservé au rôle Owner' : "Ouvrir l'autorisation LinkedIn dans un autre onglet"}
                >
                  <span>{t.connections.action_connect} LinkedIn (Onglet externe)</span>
                  <ExternalLink className="h-3.5 w-3.5 ml-1.5" />
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={!isOwner || sandboxConnecting === 'linkedin'}
                  isLoading={sandboxConnecting === 'linkedin'}
                  onClick={() => handleSandboxConnect('linkedin')}
                  className="w-full justify-center text-xs min-h-[44px] text-txt-secondary hover:text-txt"
                  title="Connecter un compte test en local sans redirection externe"
                >
                  <Zap className="h-3.5 w-3.5 mr-1.5 text-accent" />
                  Connexion Immédiate Sandbox (Mode Test)
                </Button>
              </div>
            )}
          </div>
        </div>

        {/* X (Twitter) Account Card */}
        <div className="rounded-xl border border-border bg-surface p-6 flex flex-col justify-between space-y-5 shadow-sm hover:border-border-focus transition-colors">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-surface-subtle text-txt border border-border-subtle">
                  <span className="font-bold text-lg font-mono">𝕏</span>
                </div>
                <div>
                  <h3 className="font-semibold text-txt text-base">X (Twitter)</h3>
                  <span className="text-xs text-txt-muted font-mono">tweet.write, offline.access</span>
                </div>
              </div>

              <Badge
                variant={xAccount ? 'success' : 'neutral'}
                withDot
                className="text-xs"
              >
                {xAccount ? t.connections.status_connected : t.connections.status_disconnected}
              </Badge>
            </div>

            {xAccount ? (
              <div className="space-y-2.5 rounded-lg bg-surface-subtle p-4 border border-border-subtle text-xs">
                <div className="flex justify-between">
                  <span className="text-txt-muted">Compte membre :</span>
                  <span className="font-medium text-txt">{xAccount.account_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-txt-muted">Identifiant :</span>
                  <span className="font-mono text-accent-txt">{xAccount.account_id}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-txt-muted">Scopes autorisés :</span>
                  <span className="text-txt-secondary font-mono">{xAccount.scopes?.join(', ') || 'N/A'}</span>
                </div>
              </div>
            ) : (
              <p className="text-xs text-txt-secondary leading-relaxed">
                Connectez votre compte X pour diffuser des posts concis et des threads validés en revue humaine.
              </p>
            )}
          </div>

          <div className="pt-2 space-y-2.5">
            {xAccount ? (
              <div className="space-y-2">
                <div className="flex gap-2">
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => handleTestConnection('x')}
                    isLoading={testingProvider === 'x'}
                    className="flex-1 text-xs min-h-[44px] font-medium"
                    title="Vérifier la validité du connecteur et tester la publication"
                  >
                    <Zap className="h-3.5 w-3.5 mr-1.5" />
                    Tester le connecteur
                  </Button>
                  <Button
                    variant="danger"
                    size="sm"
                    disabled={!isOwner}
                    onClick={() => setDisconnectTarget(xAccount)}
                    className="text-xs min-h-[44px]"
                    title={!isOwner ? 'Réservé au rôle Owner' : 'Déconnecter le compte'}
                  >
                    <Unlink className="h-3.5 w-3.5 mr-1.5" />
                    Déconnecter
                  </Button>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={!isOwner}
                  onClick={() => handleStartOAuth('x')}
                  className="w-full text-xs text-txt-muted hover:text-txt min-h-[40px]"
                  title="Ouvrir à nouveau la fenêtre d'autorisation dans un autre onglet"
                >
                  <ExternalLink className="h-3 w-3 mr-1.5" />
                  Renouveler l'autorisation (Nouvel onglet)
                </Button>
              </div>
            ) : (
              <div className="space-y-2.5">
                <Button
                  variant="primary"
                  disabled={!isOwner || connectingProvider === 'x'}
                  isLoading={connectingProvider === 'x'}
                  onClick={() => handleStartOAuth('x')}
                  className="w-full justify-center text-xs min-h-[44px] font-medium"
                  title={!isOwner ? 'Réservé au rôle Owner' : "Ouvrir l'autorisation X dans un autre onglet"}
                >
                  <span>{t.connections.action_connect} X (Onglet externe)</span>
                  <ExternalLink className="h-3.5 w-3.5 ml-1.5" />
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={!isOwner || sandboxConnecting === 'x'}
                  isLoading={sandboxConnecting === 'x'}
                  onClick={() => handleSandboxConnect('x')}
                  className="w-full justify-center text-xs min-h-[44px] text-txt-secondary hover:text-txt"
                  title="Connecter un compte test en local sans redirection externe"
                >
                  <Zap className="h-3.5 w-3.5 mr-1.5 text-accent" />
                  Connexion Immédiate Sandbox (Mode Test)
                </Button>
              </div>
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

      {/* Connector Verification Dialog */}
      <Dialog
        isOpen={Boolean(testResult)}
        onClose={() => setTestResult(null)}
        title={`Vérification du Connecteur ${testResult?.provider?.toUpperCase()}`}
      >
        <div className="space-y-4 text-xs">
          <div className="flex items-center gap-3 p-3.5 bg-status-success-bg border border-status-success-border rounded-xl text-status-success-text">
            <CheckCircle2 className="h-5 w-5 shrink-0 text-status-success-text" />
            <div>
              <strong className="block text-txt font-semibold">Connecteur 100% Opérationnel</strong>
              <span className="text-status-success-text">{testResult?.message}</span>
            </div>
          </div>

          <div className="space-y-2.5 bg-surface-subtle p-4 rounded-xl border border-border-subtle">
            <div className="flex justify-between">
              <span className="text-txt-muted">Post ID Plateforme :</span>
              <span className="font-mono text-accent-txt">{testResult?.external_post_id}</span>
            </div>
            {testResult?.url && (
              <div className="flex justify-between items-center">
                <span className="text-txt-muted">Lien généré :</span>
                <a
                  href={testResult.url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-accent underline flex items-center gap-1 hover:text-accent-hover font-mono"
                >
                  Ouvrir le post <ExternalLink className="h-3 w-3" />
                </a>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-txt-muted">Horodatage vérifié :</span>
              <span className="text-txt-secondary font-mono">{testResult?.verified_at}</span>
            </div>
          </div>

          {testResult?.receipt && (
            <div>
              <span className="text-txt-secondary block mb-1.5 font-semibold flex items-center gap-1.5 font-mono">
                <Terminal className="h-3.5 w-3.5 text-accent" /> Reçu cryptographique :
              </span>
              <pre className="p-3.5 bg-surface-subtle rounded-lg text-txt font-mono text-[11px] overflow-x-auto border border-border-subtle">
                {JSON.stringify(testResult.receipt, null, 2)}
              </pre>
            </div>
          )}

          <div className="pt-2 flex justify-end">
            <Button variant="secondary" size="sm" onClick={() => setTestResult(null)} className="min-h-[40px]">
              Fermer
            </Button>
          </div>
        </div>
      </Dialog>
    </div>
  );
};
