import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import { useTheme } from '../context/ThemeContext';
import { UserRole } from '../types/api';
import { Button } from '../components/common/Button';
import { Input } from '../components/common/Input';
import {
  Shield,
  Sparkles,
  AlertCircle,
  CheckCircle2,
  Lock,
  Eye,
  EyeOff,
  Mail,
  ArrowLeft,
  Sun,
  Moon,
  Globe,
  Zap,
} from 'lucide-react';

type ScreenView = 'login' | 'register' | 'forgot_password' | 'reset_password' | 'verify_notice' | 'dev';

export const AuthScreen: React.FC = () => {
  const {
    login,
    register,
    forgotPassword,
    resetPassword,
    resendVerification,
    startDemo,
    loginWithDevToken,
  } = useAuth();
  const { t, language, setLanguage } = useLanguage();
  const { theme, toggleTheme } = useTheme();

  const isDevEnvironment = Boolean((import.meta as any).env?.DEV);

  const [currentView, setCurrentView] = useState<ScreenView>('login');
  const [showPassword, setShowPassword] = useState(false);

  // Login form state
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [enterpriseWorkspaceId, setEnterpriseWorkspaceId] = useState('');

  // Register form state
  const [regFullName, setRegFullName] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regWorkspaceName, setRegWorkspaceName] = useState('');
  const [regInvitationCode, setRegInvitationCode] = useState('');
  const [regCguAccepted, setRegCguAccepted] = useState(false);
  const [regPrivacyAccepted, setRegPrivacyAccepted] = useState(false);

  // Forgot / Reset password state
  const [forgotEmail, setForgotEmail] = useState('');
  const [resetToken, setResetToken] = useState('');
  const [resetNewPassword, setResetNewPassword] = useState('');

  // Dev form state
  const [userId, setUserId] = useState('owner_martial');
  const [role, setRole] = useState<UserRole>('Owner');
  const [workspaceId, setWorkspaceId] = useState('ws_default');

  // UI state
  const [isLoading, setIsLoading] = useState(false);
  const [isDemoLoading, setIsDemoLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [pendingVerificationEmail, setPendingVerificationEmail] = useState<string>('');

  // Check URL parameters for reset_token or verification
  useEffect(() => {
    try {
      const params = new URLSearchParams(window.location.search);
      const tokenFromUrl = params.get('reset_token');
      if (tokenFromUrl) {
        setResetToken(tokenFromUrl);
        setCurrentView('reset_password');
      }
    } catch {
      // Ignore URL parsing errors
    }
  }, []);

  // Password strength calculation (OWASP / NIST SP 800-63B)
  const computePasswordStrength = (pwd: string) => {
    if (!pwd) return { score: 0, label: '', color: 'bg-border-subtle' };
    let score = 0;
    if (pwd.length >= 10) score += 30;
    if (pwd.length >= 14) score += 20;
    if (/[A-Z]/.test(pwd) && /[a-z]/.test(pwd)) score += 20;
    if (/[0-9]/.test(pwd)) score += 15;
    if (/[^A-Za-z0-9]/.test(pwd)) score += 15;

    if (score < 40) return { score: 25, label: 'Faible (< 10 car.)', color: 'bg-status-danger-text' };
    if (score < 70) return { score: 60, label: 'Moyen (conforme)', color: 'bg-status-warning-text' };
    return { score: 100, label: 'Robuste', color: 'bg-status-success-text' };
  };

  const regPwdStrength = computePasswordStrength(regPassword);
  const resetPwdStrength = computePasswordStrength(resetNewPassword);

  // Handlers
  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      await login(email, password, enterpriseWorkspaceId.trim() || undefined);
    } catch (err: any) {
      setErrorMessage(err.message || 'Impossible de se connecter.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!regCguAccepted || !regPrivacyAccepted) {
      setErrorMessage(t.auth.accept_cgu + ' & ' + t.auth.accept_privacy);
      return;
    }
    if (regPassword.length < 10) {
      setErrorMessage('Le mot de passe doit contenir au moins 10 caractères.');
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const result = await register({
        email: regEmail,
        password: regPassword,
        fullName: regFullName,
        workspaceName: regWorkspaceName.trim() || undefined,
        invitationCode: regInvitationCode.trim() || undefined,
        cguAccepted: regCguAccepted,
        privacyAccepted: regPrivacyAccepted,
      });

      if (result.requiresVerification) {
        setPendingVerificationEmail(regEmail);
        setCurrentView('verify_notice');
        setSuccessMessage(result.message);
      } else {
        setSuccessMessage('Compte créé avec succès ! Connexion en cours...');
        await login(regEmail, regPassword);
      }
    } catch (err: any) {
      setErrorMessage(err.message || "Échec de l'inscription.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleForgotPasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const msg = await forgotPassword(forgotEmail);
      setSuccessMessage(msg);
    } catch (err: any) {
      setErrorMessage(err.message || "Erreur lors de l'envoi.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleResetPasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (resetNewPassword.length < 10) {
      setErrorMessage('Le mot de passe doit contenir au moins 10 caractères.');
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const msg = await resetPassword(resetToken, resetNewPassword);
      setSuccessMessage(msg);
      setTimeout(() => {
        setCurrentView('login');
        setSuccessMessage('Vous pouvez maintenant vous connecter avec votre nouveau mot de passe.');
      }, 1500);
    } catch (err: any) {
      setErrorMessage(err.message || 'Échec de la réinitialisation.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleResendEmail = async () => {
    if (!pendingVerificationEmail) return;
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const msg = await resendVerification(pendingVerificationEmail);
      setSuccessMessage(msg);
    } catch (err: any) {
      setErrorMessage(err.message || "Impossible de renvoyer l'email.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleDemoClick = async () => {
    setIsDemoLoading(true);
    setErrorMessage(null);
    try {
      await startDemo();
    } catch (err: any) {
      setErrorMessage(err.message || 'Le mode démo est temporairement indisponible.');
    } finally {
      setIsDemoLoading(false);
    }
  };

  const handleDevSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMessage(null);
    try {
      await loginWithDevToken(userId, role, workspaceId);
    } catch (err: any) {
      setErrorMessage(err.message || 'Échec de la génération du jeton.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="relative flex min-h-screen items-center justify-center bg-page px-4 py-8 selection:bg-accent-subtle font-sans text-txt">
      {/* Top Bar: Language & Theme switchers */}
      <div className="absolute top-4 right-4 flex items-center gap-2">
        <button
          type="button"
          onClick={() => setLanguage(language === 'fr' ? 'en' : 'fr')}
          className="flex items-center gap-1.5 rounded-lg border border-border bg-surface px-3 py-2 text-xs font-mono text-txt-secondary hover:text-txt transition-all shadow-sm min-h-[44px]"
          title="Changer de langue (FR/EN)"
        >
          <Globe className="h-3.5 w-3.5 text-accent" />
          <span className="uppercase font-bold">{language}</span>
        </button>

        <button
          type="button"
          onClick={toggleTheme}
          className="rounded-lg border border-border bg-surface p-2.5 text-txt-secondary hover:text-txt transition-all shadow-sm min-h-[44px] min-w-[44px] flex items-center justify-center"
          title="Changer de thème"
          aria-label="Basculer le thème clair/sombre"
        >
          {theme === 'dark' ? (
            <Sun className="h-4 w-4 text-accent" />
          ) : (
            <Moon className="h-4 w-4 text-accent" />
          )}
        </button>
      </div>

      <div className="w-full max-w-md space-y-6 rounded-2xl border border-border bg-surface p-6 sm:p-8 shadow-sm">
        {/* Header Branding */}
        <div className="text-center space-y-2">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-accent text-accent-txt shadow-sm">
            <Sparkles className="h-7 w-7 text-accent-txt" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-txt">
            ContentOps Harness
          </h1>
          <p className="text-xs sm:text-sm text-txt-secondary">
            {currentView === 'register'
              ? t.auth.register_tab
              : currentView === 'forgot_password'
              ? t.auth.forgot_password_title
              : currentView === 'reset_password'
              ? t.auth.reset_password_title
              : currentView === 'verify_notice'
              ? t.auth.verify_email_title
              : t.auth.title}
          </p>
        </div>
        {/* Navigation Tabs (Login / Register / Dev) */}
        {['login', 'register', 'dev'].includes(currentView) && (
          <div className="grid grid-cols-2 gap-1 rounded-xl bg-surface-subtle p-1 border border-border-subtle text-xs font-medium" role="tablist">
            <button
              type="button"
              role="tab"
              aria-selected={currentView === 'login'}
              onClick={() => {
                setCurrentView('login');
                setErrorMessage(null);
                setSuccessMessage(null);
              }}
              className={`py-2 px-3 rounded-lg transition-all min-h-[40px] ${
                currentView === 'login'
                  ? 'bg-surface text-txt font-semibold shadow-xs border border-border-subtle'
                  : 'text-txt-secondary hover:text-txt'
              }`}
            >
              {t.auth.enterprise_tab}
            </button>

            <button
              type="button"
              role="tab"
              aria-selected={currentView === 'register'}
              onClick={() => {
                setCurrentView('register');
                setErrorMessage(null);
                setSuccessMessage(null);
              }}
              className={`py-2 px-3 rounded-lg transition-all min-h-[40px] ${
                currentView === 'register'
                  ? 'bg-surface text-txt font-semibold shadow-xs border border-border-subtle'
                  : 'text-txt-secondary hover:text-txt'
              }`}
            >
              {t.auth.register_tab}
            </button>
          </div>
        )}

        {/* Alerts */}
        {errorMessage && (
          <div
            role="alert"
            className="flex items-start gap-3 rounded-xl border border-status-danger-border bg-status-danger-bg p-3.5 text-xs text-status-danger-text animate-fade-in"
          >
            <AlertCircle className="h-4 w-4 shrink-0 text-status-danger-text mt-0.5" />
            <span className="leading-relaxed">{errorMessage}</span>
          </div>
        )}

        {successMessage && (
          <div
            role="status"
            className="flex items-start gap-3 rounded-xl border border-status-success-border bg-status-success-bg p-3.5 text-xs text-status-success-text animate-fade-in"
          >
            <CheckCircle2 className="h-4 w-4 shrink-0 text-status-success-text mt-0.5" />
            <span className="leading-relaxed">{successMessage}</span>
          </div>
        )}

        {/* ================================================================= */}
        {/* VIEW: LOGIN                                                       */}
        {/* ================================================================= */}
        {currentView === 'login' && (
          <form onSubmit={handleLoginSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="auth-email"
                className="block text-xs font-medium text-txt mb-1.5"
              >
                {t.auth.email}
              </label>
              <Input
                id="auth-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                placeholder="nom@entreprise.com"
                autoComplete="email"
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label
                  htmlFor="auth-password"
                  className="block text-xs font-medium text-txt"
                >
                  {t.auth.password}
                </label>
                <button
                  type="button"
                  onClick={() => {
                    setCurrentView('forgot_password');
                    setErrorMessage(null);
                    setSuccessMessage(null);
                  }}
                  className="text-[11px] text-accent hover:text-accent-hover transition-colors"
                >
                  {t.auth.forgot_password}
                </button>
              </div>
              <div className="relative">
                <Input
                  id="auth-password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  placeholder="••••••••••••"
                  autoComplete="current-password"
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-txt-muted hover:text-txt transition-colors"
                  title={showPassword ? t.auth.hide_password : t.auth.show_password}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <div>
              <label
                htmlFor="auth-workspace"
                className="block text-xs font-medium text-txt-secondary mb-1.5"
              >
                {t.auth.workspace_id} (Optionnel)
              </label>
              <Input
                id="auth-workspace"
                type="text"
                value={enterpriseWorkspaceId}
                onChange={(e) => setEnterpriseWorkspaceId(e.target.value)}
                placeholder="Par défaut (laisser vide)"
                className="font-mono text-xs"
              />
            </div>

            <Button
              type="submit"
              variant="primary"
              className="w-full justify-center py-2.5 text-sm font-medium mt-2 min-h-[44px]"
              isLoading={isLoading}
            >
              {t.auth.login_btn}
            </Button>

            {/* Quick Demo CTA */}
            <div className="pt-2">
              <Button
                type="button"
                variant="secondary"
                onClick={handleDemoClick}
                isLoading={isDemoLoading}
                className="w-full justify-center py-2 text-xs min-h-[44px]"
              >
                <Zap className="h-3.5 w-3.5 text-accent mr-2" />
                {t.auth.demo_btn}
              </Button>
            </div>
          </form>
        )}

        {/* ================================================================= */}
        {/* VIEW: REGISTER                                                    */}
        {/* ================================================================= */}
        {currentView === 'register' && (
          <form onSubmit={handleRegisterSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="reg-name"
                className="block text-xs font-medium text-txt mb-1"
              >
                {t.auth.full_name}
              </label>
              <Input
                id="reg-name"
                type="text"
                value={regFullName}
                onChange={(e) => setRegFullName(e.target.value)}
                required
                placeholder="Ex : Sarah Connor"
              />
            </div>

            <div>
              <label
                htmlFor="reg-email"
                className="block text-xs font-medium text-txt mb-1"
              >
                {t.auth.email}
              </label>
              <Input
                id="reg-email"
                type="email"
                value={regEmail}
                onChange={(e) => setRegEmail(e.target.value)}
                required
                placeholder="nom@entreprise.com"
              />
            </div>

            <div>
              <label
                htmlFor="reg-password"
                className="block text-xs font-medium text-txt mb-1"
              >
                {t.auth.password} (min. 10 car.)
              </label>
              <div className="relative">
                <Input
                  id="reg-password"
                  type={showPassword ? 'text' : 'password'}
                  value={regPassword}
                  onChange={(e) => setRegPassword(e.target.value)}
                  required
                  placeholder="Minimum 10 caractères"
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-txt-muted hover:text-txt"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>

              {/* Password strength meter */}
              {regPassword && (
                <div className="mt-1.5 space-y-1">
                  <div className="h-1.5 w-full bg-surface-subtle border border-border-subtle rounded-full overflow-hidden">
                    <div
                      className={`h-full ${regPwdStrength.color} transition-all duration-300`}
                      style={{ width: `${regPwdStrength.score}%` }}
                    />
                  </div>
                  <span className="text-[10px] text-txt-muted font-mono">
                    Robustesse : {regPwdStrength.label}
                  </span>
                </div>
              )}
            </div>

            <div>
              <label
                htmlFor="reg-workspace"
                className="block text-xs font-medium text-txt-secondary mb-1"
              >
                {t.auth.workspace_name}
              </label>
              <Input
                id="reg-workspace"
                type="text"
                value={regWorkspaceName}
                onChange={(e) => setRegWorkspaceName(e.target.value)}
                placeholder="Ex : Acme Content Studio"
              />
            </div>

            <div>
              <label
                htmlFor="reg-invite"
                className="block text-xs font-medium text-txt-secondary mb-1"
              >
                {t.auth.invitation_code}
              </label>
              <Input
                id="reg-invite"
                type="text"
                value={regInvitationCode}
                onChange={(e) => setRegInvitationCode(e.target.value)}
                placeholder="Code à 6 chiffres ou chaîne reçue"
                className="font-mono text-xs"
              />
            </div>

            {/* Checkboxes: CGU & Privacy */}
            <div className="space-y-2 pt-1">
              <label className="flex items-start gap-2.5 text-xs text-txt-secondary cursor-pointer">
                <input
                  type="checkbox"
                  checked={regCguAccepted}
                  onChange={(e) => setRegCguAccepted(e.target.checked)}
                  required
                  className="mt-0.5 rounded border-border text-accent focus:ring-accent"
                />
                <span className="leading-snug">{t.auth.accept_cgu}</span>
              </label>

              <label className="flex items-start gap-2.5 text-xs text-txt-secondary cursor-pointer">
                <input
                  type="checkbox"
                  checked={regPrivacyAccepted}
                  onChange={(e) => setRegPrivacyAccepted(e.target.checked)}
                  required
                  className="mt-0.5 rounded border-border text-accent focus:ring-accent"
                />
                <span className="leading-snug">{t.auth.accept_privacy}</span>
              </label>
            </div>

            <Button
              type="submit"
              variant="primary"
              className="w-full justify-center py-2.5 text-sm font-medium mt-2 min-h-[44px]"
              isLoading={isLoading}
            >
              {t.auth.create_account}
            </Button>
          </form>
        )}

        {/* ================================================================= */}
        {/* VIEW: FORGOT PASSWORD                                             */}
        {/* ================================================================= */}
        {currentView === 'forgot_password' && (
          <form onSubmit={handleForgotPasswordSubmit} className="space-y-4">
            <p className="text-xs text-txt-secondary leading-relaxed">
              {t.auth.forgot_password_desc}
            </p>

            <div>
              <label
                htmlFor="forgot-email"
                className="block text-xs font-medium text-txt mb-1.5"
              >
                {t.auth.email}
              </label>
              <Input
                id="forgot-email"
                type="email"
                value={forgotEmail}
                onChange={(e) => setForgotEmail(e.target.value)}
                required
                placeholder="nom@entreprise.com"
              />
            </div>

            <Button
              type="submit"
              variant="primary"
              className="w-full justify-center py-2.5 text-sm font-medium min-h-[44px]"
              isLoading={isLoading}
            >
              {t.auth.reset_password_btn}
            </Button>

            <button
              type="button"
              onClick={() => {
                setCurrentView('login');
                setErrorMessage(null);
                setSuccessMessage(null);
              }}
              className="flex items-center justify-center gap-2 w-full py-2 text-xs text-txt-secondary hover:text-txt transition-colors min-h-[40px]"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              <span>{t.auth.back_to_login}</span>
            </button>
          </form>
        )}

        {/* ================================================================= */}
        {/* VIEW: RESET PASSWORD                                              */}
        {/* ================================================================= */}
        {currentView === 'reset_password' && (
          <form onSubmit={handleResetPasswordSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="reset-token"
                className="block text-xs font-medium text-txt mb-1"
              >
                Jeton de réinitialisation
              </label>
              <Input
                id="reset-token"
                type="text"
                value={resetToken}
                onChange={(e) => setResetToken(e.target.value)}
                required
                placeholder="Jeton reçu par email"
                className="font-mono text-xs"
              />
            </div>

            <div>
              <label
                htmlFor="reset-new-pwd"
                className="block text-xs font-medium text-txt mb-1"
              >
                {t.auth.new_password} (min. 10 car.)
              </label>
              <div className="relative">
                <Input
                  id="reset-new-pwd"
                  type={showPassword ? 'text' : 'password'}
                  value={resetNewPassword}
                  onChange={(e) => setResetNewPassword(e.target.value)}
                  required
                  placeholder="Nouveau mot de passe"
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-txt-muted hover:text-txt"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>

              {resetNewPassword && (
                <div className="mt-1.5 space-y-1">
                  <div className="h-1.5 w-full bg-surface-subtle border border-border-subtle rounded-full overflow-hidden">
                    <div
                      className={`h-full ${resetPwdStrength.color} transition-all duration-300`}
                      style={{ width: `${resetPwdStrength.score}%` }}
                    />
                  </div>
                  <span className="text-[10px] text-txt-muted font-mono">
                    Robustesse : {resetPwdStrength.label}
                  </span>
                </div>
              )}
            </div>

            <Button
              type="submit"
              variant="primary"
              className="w-full justify-center py-2.5 text-sm font-medium min-h-[44px]"
              isLoading={isLoading}
            >
              {t.auth.save_password}
            </Button>

            <button
              type="button"
              onClick={() => {
                setCurrentView('login');
                setErrorMessage(null);
                setSuccessMessage(null);
              }}
              className="flex items-center justify-center gap-2 w-full py-2 text-xs text-txt-secondary hover:text-txt transition-colors min-h-[40px]"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              <span>{t.auth.back_to_login}</span>
            </button>
          </form>
        )}

        {/* ================================================================= */}
        {/* VIEW: VERIFICATION NOTICE                                         */}
        {/* ================================================================= */}
        {currentView === 'verify_notice' && (
          <div className="space-y-5 text-center">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-accent-subtle text-accent border border-accent-border">
              <Mail className="h-6 w-6" />
            </div>

            <div className="space-y-2">
              <h3 className="text-sm font-bold text-txt">
                {t.auth.verify_email_title}
              </h3>
              <p className="text-xs text-txt-secondary leading-relaxed">
                {t.auth.verify_email_desc}
              </p>
              {pendingVerificationEmail && (
                <p className="text-xs font-mono font-medium text-accent-txt bg-surface-subtle py-1.5 px-3 rounded-lg border border-border-subtle inline-block">
                  {pendingVerificationEmail}
                </p>
              )}
            </div>

            <div className="space-y-2 pt-2">
              <Button
                type="button"
                variant="secondary"
                onClick={handleResendEmail}
                isLoading={isLoading}
                className="w-full justify-center py-2 text-xs min-h-[40px]"
              >
                {t.auth.resend_email}
              </Button>

              <button
                type="button"
                onClick={() => {
                  setCurrentView('login');
                  setErrorMessage(null);
                  setSuccessMessage(null);
                }}
                className="flex items-center justify-center gap-2 w-full py-2 text-xs text-txt-secondary hover:text-txt transition-colors min-h-[40px]"
              >
                <ArrowLeft className="h-3.5 w-3.5" />
                <span>{t.auth.back_to_login}</span>
              </button>
            </div>
          </div>
        )}

        {/* ================================================================= */}
        {/* VIEW: DEV TOKENS (DEV ONLY)                                       */}
        {/* ================================================================= */}
        {currentView === 'dev' && isDevEnvironment && (
          <form onSubmit={handleDevSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="user-id"
                className="block text-xs font-medium text-txt mb-1"
              >
                {t.auth.user_id}
              </label>
              <Input
                id="user-id"
                type="text"
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                required
                className="font-mono text-xs"
              />
            </div>

            <div>
              <label
                htmlFor="workspace-id"
                className="block text-xs font-medium text-txt mb-1"
              >
                {t.auth.workspace_id}
              </label>
              <Input
                id="workspace-id"
                type="text"
                value={workspaceId}
                onChange={(e) => setWorkspaceId(e.target.value)}
                required
                className="font-mono text-xs"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-txt mb-1.5">
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
                    className={`flex flex-col items-center justify-center rounded-xl border p-2 text-xs font-medium transition-all min-h-[40px] ${
                      role === r
                        ? 'border-accent bg-accent-subtle text-accent-txt shadow-xs font-semibold'
                        : 'border-border bg-surface text-txt-secondary hover:border-border-focus hover:text-txt'
                    }`}
                  >
                    <Shield className="h-3.5 w-3.5 mb-0.5" />
                    <span>{r}</span>
                  </button>
                ))}
              </div>
            </div>

            <Button
              type="submit"
              variant="primary"
              className="w-full justify-center py-2.5 text-sm font-medium min-h-[44px]"
              isLoading={isLoading}
            >
              {t.auth.dev_login_btn}
            </Button>
          </form>
        )}

        {/* Security Notice */}
        <div className="flex items-start gap-2.5 rounded-xl border border-border-subtle bg-surface-subtle p-3.5 text-xs text-txt-secondary">
          <Lock className="h-4 w-4 shrink-0 text-accent mt-0.5" />
          <span className="leading-relaxed">
            {t.auth.security_notice}
          </span>
        </div>
      </div>
    </main>
  );
};
