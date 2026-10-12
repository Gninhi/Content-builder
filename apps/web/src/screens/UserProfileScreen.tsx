import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import { useTheme } from '../context/ThemeContext';
import { useToast } from '../context/ToastContext';
import { apiClient } from '../lib/api';
import {
  UserProfile,
  UserProfileUpdate,
  SessionInfo,
  PersonalDataExport,
} from '../types/api';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import {
  User,
  Shield,
  Key,
  Bell,
  Palette,
  Building,
  Camera,
  Download,
} from 'lucide-react';
import { PersonalInfoTab } from '../components/profile/PersonalInfoTab';
import { PreferencesTab } from '../components/profile/PreferencesTab';
import { NotificationsTab } from '../components/profile/NotificationsTab';
import { SecurityTab } from '../components/profile/SecurityTab';
import { WorkspacesTab } from '../components/profile/WorkspacesTab';
import { GdprTab } from '../components/profile/GdprTab';

interface UserProfileScreenProps {
  onNavigate?: (screen: string) => void;
}

type TabType = 'informations' | 'preferences' | 'notifications' | 'security' | 'workspaces' | 'gdpr';

export const UserProfileScreen: React.FC<UserProfileScreenProps> = () => {
  const { session, logout, isOwner } = useAuth();
  const { language, setLanguage } = useLanguage();
  const { theme, setTheme } = useTheme();
  const { showToast } = useToast();

  const isEn = language === 'en';

  const [activeTab, setActiveTab] = useState<TabType>('informations');
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [isUploadingAvatar, setIsUploadingAvatar] = useState<boolean>(false);

  // Form states
  const [fullName, setFullName] = useState<string>('');
  const [displayName, setDisplayName] = useState<string>('');
  const [jobTitle, setJobTitle] = useState<string>('');
  const [timezone, setTimezone] = useState<string>('UTC');
  const [uiDensity, setUiDensity] = useState<string>('comfortable');
  const [defaultView, setDefaultView] = useState<string>('dashboard');

  // Notifications
  const [notifCrit, setNotifCrit] = useState<boolean>(true);
  const [notifApproval, setNotifApproval] = useState<boolean>(true);
  const [notifPush, setNotifPush] = useState<boolean>(false);
  const [notifWeekly, setNotifWeekly] = useState<boolean>(true);

  // Password change
  const [currentPassword, setCurrentPassword] = useState<string>('');
  const [newPassword, setNewPassword] = useState<string>('');
  const [confirmPassword, setConfirmPassword] = useState<string>('');
  const [isChangingPassword, setIsChangingPassword] = useState<boolean>(false);

  // Account deletion modal
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState<boolean>(false);
  const [deleteConfirmationText, setDeleteConfirmationText] = useState<string>('');
  const [isDeletingAccount, setIsDeletingAccount] = useState<boolean>(false);

  // Avatar file input ref
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load Profile and Sessions
  const loadProfileData = async () => {
    setIsLoading(true);
    try {
      const data = await apiClient<UserProfile>('/v1/me');
      setProfile(data);
      setFullName(data.full_name || '');
      setDisplayName(data.display_name || '');
      setJobTitle(data.job_title || '');
      setTimezone(data.timezone || 'UTC');

      if (data.ui_preferences) {
        setUiDensity(data.ui_preferences.density || 'comfortable');
        setDefaultView(data.ui_preferences.default_view || 'dashboard');
      }

      if (data.notification_preferences) {
        setNotifCrit(data.notification_preferences.email_critical_alerts !== false);
        setNotifApproval(data.notification_preferences.notify_on_approval !== false);
        setNotifPush(Boolean(data.notification_preferences.browser_push));
        setNotifWeekly(data.notification_preferences.weekly_digest !== false);
      }

      // Sync theme & language if returned from profile
      if (data.theme === 'light' || data.theme === 'dark') {
        setTheme(data.theme);
      }
      if (data.language === 'fr' || data.language === 'en') {
        setLanguage(data.language);
      }
    } catch (err: any) {
      showToast('error', err.detail || (isEn ? 'Failed to load user profile.' : 'Impossible de charger le profil utilisateur.'));
    } finally {
      setIsLoading(false);
    }
  };

  const loadSessionsData = async () => {
    try {
      const sessList = await apiClient<SessionInfo[]>('/v1/me/sessions');
      setSessions(sessList);
    } catch {
      // Ignored background failure
    }
  };

  useEffect(() => {
    loadProfileData();
    loadSessionsData();
  }, []);

  // Save General Profile Info
  const handleSaveInfo = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    try {
      const payload: UserProfileUpdate = {
        full_name: fullName.trim(),
        display_name: displayName.trim() || undefined,
        job_title: jobTitle.trim() || undefined,
      };
      const updated = await apiClient<UserProfile>('/v1/me', {
        method: 'PATCH',
        body: JSON.stringify(payload),
      });
      setProfile(updated);
      showToast('success', isEn ? 'Personal information updated successfully.' : 'Informations personnelles mises à jour avec succès.');
    } catch (err: any) {
      showToast('error', err.detail || (isEn ? 'Error updating personal info.' : 'Erreur lors de la mise à jour des informations.'));
    } finally {
      setIsSaving(false);
    }
  };

  // Save Preferences
  const handleSavePreferences = async (newTheme?: 'dark' | 'light', newLang?: 'fr' | 'en') => {
    setIsSaving(true);
    try {
      const targetTheme = newTheme || theme;
      const targetLang = newLang || language;

      const payload: UserProfileUpdate = {
        timezone,
        theme: targetTheme,
        language: targetLang,
        ui_preferences: {
          density: uiDensity,
          default_view: defaultView,
        },
      };

      const updated = await apiClient<UserProfile>('/v1/me', {
        method: 'PATCH',
        body: JSON.stringify(payload),
      });
      setProfile(updated);
      showToast('success', isEn ? 'Display and localization preferences saved.' : "Préférences d'affichage et de langue enregistrées.");
    } catch (err: any) {
      showToast('error', err.detail || (isEn ? 'Error saving preferences.' : 'Erreur lors de la sauvegarde des préférences.'));
    } finally {
      setIsSaving(false);
    }
  };

  // Save Notification Preferences
  const handleSaveNotifications = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    try {
      const payload: UserProfileUpdate = {
        notification_preferences: {
          email_critical_alerts: notifCrit,
          notify_on_approval: notifApproval,
          browser_push: notifPush,
          weekly_digest: notifWeekly,
        },
      };
      const updated = await apiClient<UserProfile>('/v1/me', {
        method: 'PATCH',
        body: JSON.stringify(payload),
      });
      setProfile(updated);
      showToast('success', isEn ? 'Notification settings updated.' : 'Préférences de notifications mises à jour.');
    } catch (err: any) {
      showToast('error', err.detail || (isEn ? 'Error saving notification preferences.' : 'Erreur lors de la sauvegarde des notifications.'));
    } finally {
      setIsSaving(false);
    }
  };

  // Handle Avatar Upload
  const handleAvatarSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > 2 * 1024 * 1024) {
      showToast('error', isEn ? 'File size exceeds maximum 2 MB limit.' : 'Le fichier dépasse la taille maximale autorisée de 2 Mo.');
      return;
    }

    const allowedTypes = ['image/jpeg', 'image/png', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
      showToast('error', isEn ? 'Invalid format. Allowed: JPEG, PNG, WebP (SVG forbidden for security).' : 'Format non autorisé. Formats acceptés : JPEG, PNG, WebP (SVG interdit pour raisons de sécurité).');
      return;
    }

    setIsUploadingAvatar(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await apiClient<{ avatar_url: string; message: string }>('/v1/me/avatar', {
        method: 'POST',
        body: formData,
      });
      if (profile) {
        setProfile({ ...profile, avatar_url: res.avatar_url });
      }
      showToast('success', res.message || (isEn ? 'Avatar updated successfully.' : 'Avatar mis à jour avec succès.'));
    } catch (err: any) {
      showToast('error', err.detail || (isEn ? 'Failed to upload avatar.' : "Échec du téléchargement de l'avatar."));
    } finally {
      setIsUploadingAvatar(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  // Handle Password Change
  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      showToast('error', isEn ? 'Passwords do not match.' : 'Les nouveaux mots de passe ne correspondent pas.');
      return;
    }
    if (newPassword.length < 8) {
      showToast('error', isEn ? 'Password must be at least 8 characters.' : 'Le nouveau mot de passe doit comporter au moins 8 caractères.');
      return;
    }

    setIsChangingPassword(true);
    try {
      const res = await apiClient<{ message: string; revoked_sessions_count: number }>(
        '/v1/me/change-password',
        {
          method: 'POST',
          body: JSON.stringify({
            current_password: currentPassword,
            new_password: newPassword,
          }),
        }
      );
      showToast('success', res.message || (isEn ? 'Password updated successfully.' : 'Mot de passe modifié avec succès.'));
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      loadSessionsData();
    } catch (err: any) {
      showToast('error', err.detail || (isEn ? 'Error updating password.' : 'Erreur lors du changement de mot de passe.'));
    } finally {
      setIsChangingPassword(false);
    }
  };

  // Revoke Single Session
  const handleRevokeSession = async (sessionId: string) => {
    try {
      await apiClient(`/v1/me/sessions/${sessionId}`, { method: 'DELETE' });
      showToast('success', isEn ? 'Session revoked successfully.' : 'Session révoquée avec succès.');
      loadSessionsData();
    } catch (err: any) {
      showToast('error', err.detail || (isEn ? 'Unable to revoke session.' : 'Impossible de révoquer la session.'));
    }
  };

  // Revoke All Other Sessions
  const handleRevokeOtherSessions = async () => {
    try {
      const res = await apiClient<{ message: string }>('/v1/me/sessions/revoke-others', {
        method: 'POST',
      });
      showToast('success', res.message || (isEn ? 'All other sessions revoked.' : 'Autres sessions révoquées.'));
      loadSessionsData();
    } catch (err: any) {
      showToast('error', err.detail || (isEn ? 'Error revoking other sessions.' : 'Erreur lors de la révocation des sessions.'));
    }
  };

  // Export Personal Data (GDPR Art. 20)
  const handleExportData = async () => {
    try {
      showToast('info', isEn ? 'Preparing personal data archive...' : 'Génération de votre archive de données en cours...');
      const data = await apiClient<PersonalDataExport>('/v1/me/export');
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `contentops_export_${profile?.id || 'user'}_${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      showToast('success', isEn ? 'Personal data archive downloaded.' : 'Archive de données personnelles téléchargée avec succès.');
    } catch (err: any) {
      showToast('error', err.detail || (isEn ? 'Failed to export data.' : "Échec de l'export des données."));
    }
  };

  // Delete Account (GDPR Art. 17)
  const handleDeleteAccount = async () => {
    if (deleteConfirmationText.trim() !== 'SUPPRIMER') {
      showToast('error', isEn ? "Please type 'SUPPRIMER' to confirm." : "Veuillez taper le mot 'SUPPRIMER' en majuscules pour confirmer.");
      return;
    }

    setIsDeletingAccount(true);
    try {
      await apiClient('/v1/me', { method: 'DELETE' });
      showToast('success', isEn ? 'Your account has been deleted and data anonymized.' : 'Votre compte a été supprimé et vos données ont été anonymisées.');
      setIsDeleteModalOpen(false);
      setTimeout(() => {
        logout();
      }, 1500);
    } catch (err: any) {
      showToast('error', err.detail || (isEn ? 'Failed to delete account.' : 'Impossible de supprimer le compte.'));
    } finally {
      setIsDeletingAccount(false);
    }
  };

  if (isLoading && !profile) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent border-t-transparent" />
          <p className="text-xs text-txt-muted font-mono">
            {isEn ? 'Loading secure profile...' : 'Chargement du profil sécurisé...'}
          </p>
        </div>
      </div>
    );
  }

  const tabs: { id: TabType; labelFr: string; labelEn: string; icon: React.FC<{ className?: string }> }[] = [
    { id: 'informations', labelFr: 'Informations', labelEn: 'Identity & Info', icon: User },
    { id: 'preferences', labelFr: 'Affichage & Langue', labelEn: 'Display & Language', icon: Palette },
    { id: 'notifications', labelFr: 'Notifications', labelEn: 'Notifications', icon: Bell },
    { id: 'security', labelFr: 'Sécurité & Sessions', labelEn: 'Security & Sessions', icon: Key },
    { id: 'workspaces', labelFr: 'Workspaces & Rôles', labelEn: 'Workspaces & Roles', icon: Building },
    { id: 'gdpr', labelFr: 'Conformité RGPD', labelEn: 'GDPR Compliance', icon: Shield },
  ];

  return (
    <div className="mx-auto max-w-6xl space-y-8 p-4 sm:p-6 lg:p-8 animate-fade-in text-txt-primary">
      {/* Top Banner / Header Card */}
      <div className="rounded-xl border border-border-default bg-surface p-6 shadow-subtle transition-colors duration-150">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6">
          <div className="flex items-center gap-5">
            {/* Avatar container */}
            <div className="relative group shrink-0">
              <div className="h-18 w-18 sm:h-20 sm:w-20 rounded-xl bg-surface-subtle border border-border-default flex items-center justify-center overflow-hidden shadow-xs">
                {profile?.avatar_url ? (
                  <img
                    src={profile.avatar_url}
                    alt={profile.display_name || profile.full_name || 'Avatar'}
                    className="h-full w-full object-cover"
                  />
                ) : (
                  <div className="text-xl sm:text-2xl font-bold text-accent font-mono">
                    {(profile?.display_name || profile?.full_name || 'U').slice(0, 2).toUpperCase()}
                  </div>
                )}
              </div>
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploadingAvatar}
                className="absolute -bottom-1 -right-1 rounded-lg bg-accent p-2 text-accent-foreground hover:opacity-90 shadow-subtle transition-transform hover:scale-105 focus:outline-none focus:ring-2 focus:ring-accent min-h-[36px] min-w-[36px] flex items-center justify-center"
                title={isEn ? 'Update avatar (JPEG, PNG, WebP)' : "Modifier l'avatar (JPEG, PNG, WebP)"}
                aria-label={isEn ? 'Update avatar' : "Modifier l'avatar"}
              >
                <Camera className="h-3.5 w-3.5" />
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                className="hidden"
                onChange={handleAvatarSelect}
              />
            </div>

            {/* Profile identifiers */}
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2.5">
                <h1 className="text-lg sm:text-xl lg:text-2xl font-bold tracking-tight text-txt-primary truncate">
                  {profile?.display_name || profile?.full_name || session?.user_id}
                </h1>
                <Badge variant={isOwner ? 'accent' : 'neutral'} className="text-xs px-2.5 py-0.5">
                  {session?.role || 'Viewer'}
                </Badge>
              </div>
              <p className="text-xs sm:text-sm text-txt-muted font-mono mt-0.5 truncate">{profile?.email}</p>
              {profile?.job_title && (
                <p className="text-xs text-txt-secondary font-medium mt-1 truncate">{profile.job_title}</p>
              )}
            </div>
          </div>

          {/* Quick Actions */}
          <div className="flex items-center gap-3 self-start sm:self-center">
            <Button
              variant="secondary"
              size="sm"
              onClick={handleExportData}
              className="flex items-center gap-2 text-xs min-h-[38px]"
            >
              <Download className="h-3.5 w-3.5 text-accent" />
              {isEn ? 'GDPR Export (JSON)' : 'Export RGPD (JSON)'}
            </Button>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <nav
        aria-label={isEn ? 'Profile navigation' : 'Navigation du profil'}
        className="flex items-center gap-1 sm:gap-2 overflow-x-auto border-b border-border-default pb-0 scrollbar-none"
      >
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              aria-current={isActive ? 'page' : undefined}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-3.5 py-3 text-xs sm:text-sm font-medium transition-colors border-b-2 shrink-0 min-h-[44px] ${
                isActive
                  ? 'border-accent text-accent font-semibold'
                  : 'border-transparent text-txt-muted hover:text-txt-primary hover:border-border-hover'
              }`}
            >
              <Icon className={`h-4 w-4 ${isActive ? 'text-accent' : 'text-txt-muted'}`} />
              <span>{isEn ? tab.labelEn : tab.labelFr}</span>
            </button>
          );
        })}
      </nav>

      {/* Tab Panels */}
      <div role="tabpanel">
        {activeTab === 'informations' && (
          <PersonalInfoTab
            profile={profile}
            fullName={fullName}
            setFullName={setFullName}
            displayName={displayName}
            setDisplayName={setDisplayName}
            jobTitle={jobTitle}
            setJobTitle={setJobTitle}
            isSaving={isSaving}
            onSave={handleSaveInfo}
          />
        )}

        {activeTab === 'preferences' && (
          <PreferencesTab
            theme={theme}
            setTheme={setTheme}
            language={language}
            setLanguage={setLanguage}
            timezone={timezone}
            setTimezone={setTimezone}
            uiDensity={uiDensity}
            setUiDensity={setUiDensity}
            defaultView={defaultView}
            setDefaultView={setDefaultView}
            isSaving={isSaving}
            onSavePreferences={handleSavePreferences}
          />
        )}

        {activeTab === 'notifications' && (
          <NotificationsTab
            notifCrit={notifCrit}
            setNotifCrit={setNotifCrit}
            notifApproval={notifApproval}
            setNotifApproval={setNotifApproval}
            notifPush={notifPush}
            setNotifPush={setNotifPush}
            notifWeekly={notifWeekly}
            setNotifWeekly={setNotifWeekly}
            isSaving={isSaving}
            onSaveNotifications={handleSaveNotifications}
          />
        )}

        {activeTab === 'security' && (
          <SecurityTab
            currentPassword={currentPassword}
            setCurrentPassword={setCurrentPassword}
            newPassword={newPassword}
            setNewPassword={setNewPassword}
            confirmPassword={confirmPassword}
            setConfirmPassword={setConfirmPassword}
            isChangingPassword={isChangingPassword}
            onChangePassword={handleChangePassword}
            sessions={sessions}
            onRevokeSession={handleRevokeSession}
            onRevokeOtherSessions={handleRevokeOtherSessions}
          />
        )}

        {activeTab === 'workspaces' && <WorkspacesTab profile={profile} />}

        {activeTab === 'gdpr' && (
          <GdprTab
            onExportData={handleExportData}
            isDeleteModalOpen={isDeleteModalOpen}
            setIsDeleteModalOpen={setIsDeleteModalOpen}
            deleteConfirmationText={deleteConfirmationText}
            setDeleteConfirmationText={setDeleteConfirmationText}
            isDeletingAccount={isDeletingAccount}
            onDeleteAccount={handleDeleteAccount}
          />
        )}
      </div>
    </div>
  );
};
