import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import { UserRole } from '../types/api';
import { Button } from '../components/common/Button';
import { Input } from '../components/common/Input';
import { Shield, Sparkles, AlertCircle, Lock } from 'lucide-react';

export const AuthScreen: React.FC = () => {
  const { loginWithDevToken } = useAuth();
  const { t } = useLanguage();

  const [userId, setUserId] = useState('user_martial');
  const [role, setRole] = useState<UserRole>('Owner');
  const [workspaceId, setWorkspaceId] = useState('ws_default');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMessage(null);

    try {
      await loginWithDevToken(userId, role, workspaceId);
    } catch (err: any) {
      setErrorMessage(err.message || 'Impossible de se connecter.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 px-4 py-12 selection:bg-cyan-500/30">
      <div className="w-full max-w-md space-y-8 rounded-2xl border border-slate-800 bg-slate-900/80 p-8 shadow-2xl backdrop-blur-xl">
        {/* Header Branding */}
        <div className="text-center space-y-2">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-tr from-cyan-500 to-blue-600 text-white shadow-lg shadow-cyan-500/25">
            <Sparkles className="h-7 w-7" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white">
            ContentOps Harness
          </h1>
          <p className="text-sm text-slate-400">
            {t.auth.title}
          </p>
        </div>

        {/* Error Alert */}
        {errorMessage && (
          <div
            role="alert"
            className="flex items-center gap-3 rounded-lg border border-red-500/30 bg-red-950/40 p-4 text-sm text-red-300"
          >
            <AlertCircle className="h-5 w-5 shrink-0 text-red-400" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label
              htmlFor="user-id"
              className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5"
            >
              {t.auth.user_id}
            </label>
            <Input
              id="user-id"
              type="text"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              required
              placeholder="ex: user_owner"
              autoComplete="username"
            />
          </div>

          <div>
            <label
              htmlFor="workspace-id"
              className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5"
            >
              {t.auth.workspace_id}
            </label>
            <Input
              id="workspace-id"
              type="text"
              value={workspaceId}
              onChange={(e) => setWorkspaceId(e.target.value)}
              required
              placeholder="ex: ws_default"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              {t.auth.select_role}
            </label>
            <div className="grid grid-cols-3 gap-2" role="radiogroup" aria-label="Rôle utilisateur">
              {(['Owner', 'Editor', 'Viewer'] as UserRole[]).map((r) => (
                <button
                  key={r}
                  type="button"
                  role="radio"
                  aria-checked={role === r}
                  onClick={() => setRole(r)}
                  className={`flex flex-col items-center justify-center rounded-lg border p-2.5 text-xs font-medium transition-all ${
                    role === r
                      ? 'border-cyan-500 bg-cyan-500/10 text-cyan-300 shadow-sm shadow-cyan-500/20'
                      : 'border-slate-800 bg-slate-800/60 text-slate-400 hover:border-slate-700 hover:text-slate-200'
                  }`}
                >
                  <Shield className="h-4 w-4 mb-1" />
                  <span>{r}</span>
                </button>
              ))}
            </div>
            <p className="mt-1.5 text-[11px] text-slate-400">
              {role === 'Owner'
                ? 'Accès total : gouvernance, approbation HITL, publication & OAuth.'
                : role === 'Editor'
                ? 'Création et édition de contenu, soumission en revue.'
                : 'Consultation seule (lecture des brouillons et métriques).'}
            </p>
          </div>

          <Button
            type="submit"
            variant="primary"
            className="w-full justify-center py-2.5 text-sm font-semibold"
            isLoading={isLoading}
          >
            {t.auth.dev_login_btn}
          </Button>
        </form>

        {/* Security Notice */}
        <div className="flex items-start gap-2.5 rounded-lg border border-slate-800 bg-slate-950/60 p-3 text-[11px] text-slate-400">
          <Lock className="h-4 w-4 shrink-0 text-cyan-400 mt-0.5" />
          <span>
            {t.auth.security_notice}
          </span>
        </div>
      </div>
    </main>
  );
};
