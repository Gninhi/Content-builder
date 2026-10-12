import React from 'react';
import { SessionInfo } from '../../types/api';
import { Input } from '../common/Input';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { Smartphone, Laptop, CheckCircle2, Key } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';

interface SecurityTabProps {
  currentPassword: string;
  setCurrentPassword: (v: string) => void;
  newPassword: string;
  setNewPassword: (v: string) => void;
  confirmPassword: string;
  setConfirmPassword: (v: string) => void;
  isChangingPassword: boolean;
  onChangePassword: (e: React.FormEvent) => void;
  sessions: SessionInfo[];
  onRevokeSession: (sessionId: string) => void;
  onRevokeOtherSessions: () => void;
}

export const SecurityTab: React.FC<SecurityTabProps> = ({
  currentPassword,
  setCurrentPassword,
  newPassword,
  setNewPassword,
  confirmPassword,
  setConfirmPassword,
  isChangingPassword,
  onChangePassword,
  sessions,
  onRevokeSession,
  onRevokeOtherSessions,
}) => {
  const { language } = useLanguage();
  const isEn = language === 'en';

  // Helper password strength indicators
  const hasMinLength = newPassword.length >= 8;
  const hasUpper = /[A-Z]/.test(newPassword);
  const hasLower = /[a-z]/.test(newPassword);
  const hasNumber = /[0-9]/.test(newPassword);
  const hasSpecial = /[!@#$%^&*(),.?":{}|<>_\-+=~`[\]\\/]/.test(newPassword);
  const isPasswordValid = hasMinLength && hasUpper && hasLower && hasNumber && hasSpecial;

  return (
    <div className="space-y-8">
      {/* Section: Change Password */}
      <div className="rounded-xl border border-border-default bg-surface p-6 lg:p-8 space-y-6 shadow-subtle transition-colors duration-150">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-base lg:text-lg font-semibold text-txt-primary tracking-tight">
              {isEn ? 'Password Management' : 'Changement de Mot de Passe'}
            </h2>
            <p className="text-xs text-txt-muted mt-1 leading-relaxed max-w-2xl">
              {isEn
                ? 'Protect your account with robust Argon2id hashing. Changing your password will automatically invalidate all other active sessions.'
                : 'Protégez votre compte avec un hachage robuste Argon2id. Modifier votre mot de passe révoquera automatiquement toutes vos autres sessions actives.'}
            </p>
          </div>
          <div className="hidden sm:flex h-9 w-9 rounded-lg bg-surface-subtle border border-border-default items-center justify-center text-txt-muted shrink-0">
            <Key className="h-4 w-4 text-accent" />
          </div>
        </div>

        <form onSubmit={onChangePassword} className="max-w-xl space-y-5">
          <Input
            label={isEn ? 'Current Password' : 'Mot de passe actuel'}
            type="password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            placeholder="••••••••••••"
            required
            className="min-h-[44px]"
          />

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label={isEn ? 'New Password' : 'Nouveau mot de passe'}
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="••••••••••••"
              required
              className="min-h-[44px]"
            />
            <Input
              label={isEn ? 'Confirm New Password' : 'Confirmer le nouveau mot de passe'}
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="••••••••••••"
              required
              className="min-h-[44px]"
            />
          </div>

          {/* Password complexity checklist */}
          <div className="rounded-lg border border-border-subtle bg-surface-subtle p-4 space-y-2.5">
            <span className="text-xs font-semibold text-txt-secondary block">
              {isEn ? 'Security Requirements:' : 'Exigences de sécurité :'}
            </span>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
              <div className={`flex items-center gap-2 ${hasMinLength ? 'text-emerald-500' : 'text-txt-muted'}`}>
                <CheckCircle2 className="h-3.5 w-3.5" />
                <span>{isEn ? '8 characters minimum' : '8 caractères minimum'}</span>
              </div>
              <div className={`flex items-center gap-2 ${hasUpper ? 'text-emerald-500' : 'text-txt-muted'}`}>
                <CheckCircle2 className="h-3.5 w-3.5" />
                <span>{isEn ? 'One uppercase letter' : 'Une majuscule'}</span>
              </div>
              <div className={`flex items-center gap-2 ${hasLower ? 'text-emerald-500' : 'text-txt-muted'}`}>
                <CheckCircle2 className="h-3.5 w-3.5" />
                <span>{isEn ? 'One lowercase letter' : 'Une minuscule'}</span>
              </div>
              <div className={`flex items-center gap-2 ${hasNumber ? 'text-emerald-500' : 'text-txt-muted'}`}>
                <CheckCircle2 className="h-3.5 w-3.5" />
                <span>{isEn ? 'One number' : 'Un chiffre'}</span>
              </div>
              <div className={`flex items-center gap-2 ${hasSpecial ? 'text-emerald-500' : 'text-txt-muted'}`}>
                <CheckCircle2 className="h-3.5 w-3.5" />
                <span>{isEn ? 'One special character' : 'Un caractère spécial'}</span>
              </div>
            </div>
          </div>

          <Button
            type="submit"
            variant="primary"
            isLoading={isChangingPassword}
            disabled={!isPasswordValid}
            className="min-h-[44px] font-medium"
          >
            {isEn ? 'Update Password' : 'Mettre à jour le mot de passe'}
          </Button>
        </form>
      </div>

      {/* Section: Active Sessions */}
      <div className="rounded-xl border border-border-default bg-surface p-6 lg:p-8 space-y-6 shadow-subtle transition-colors duration-150">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-base lg:text-lg font-semibold text-txt-primary tracking-tight">
              {isEn ? 'Active Sessions & Sign-ins' : 'Sessions Actives & Connexions'}
            </h2>
            <p className="text-xs text-txt-muted mt-1 leading-relaxed">
              {isEn
                ? 'Manage active tokens and connected devices. You can revoke any suspicious session at any time.'
                : 'Gérez les appareils et jetons connectés à votre compte. Vous pouvez révoquer une session suspecte à tout moment.'}
            </p>
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={onRevokeOtherSessions}
            className="min-h-[38px] text-xs font-medium self-start sm:self-auto"
          >
            {isEn ? 'Revoke All Other Sessions' : 'Révoquer toutes les autres sessions'}
          </Button>
        </div>

        <div className="space-y-3">
          {sessions.length === 0 ? (
            <div className="p-6 text-center text-xs text-txt-muted border border-dashed border-border-default rounded-lg">
              {isEn ? 'No other active sessions recorded.' : 'Aucune session active enregistrée.'}
            </div>
          ) : (
            sessions.map((s) => (
              <div
                key={s.id}
                className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-lg border border-border-subtle bg-surface-subtle hover:border-border-default transition-colors"
              >
                <div className="flex items-center gap-3.5">
                  <div className="h-10 w-10 rounded-lg bg-surface border border-border-default flex items-center justify-center shrink-0 text-accent">
                    {s.user_agent?.toLowerCase().includes('mobile') ? (
                      <Smartphone className="h-5 w-5" />
                    ) : (
                      <Laptop className="h-5 w-5" />
                    )}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-txt-primary">
                        {s.user_agent ? s.user_agent.slice(0, 48) : 'ContentOps API Client'}
                      </span>
                      {s.is_current && (
                        <Badge variant="success" className="text-[10px] px-2 py-0.5">
                          {isEn ? 'Current Session' : 'Session Actuelle'}
                        </Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-3 text-[11px] text-txt-muted font-mono mt-1">
                      <span>IP: {s.ip_address || '127.0.0.1'}</span>
                      <span>•</span>
                      <span>
                        {isEn ? 'Last active: ' : 'Dernière activité : '}
                        {new Date(s.last_active_at).toLocaleDateString(undefined, {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                    </div>
                  </div>
                </div>

                {!s.is_current && (
                  <Button
                    variant="danger"
                    size="sm"
                    onClick={() => onRevokeSession(s.id)}
                    className="min-h-[36px] text-xs px-3 py-1 self-end sm:self-center"
                  >
                    {isEn ? 'Revoke' : 'Révoquer'}
                  </Button>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
