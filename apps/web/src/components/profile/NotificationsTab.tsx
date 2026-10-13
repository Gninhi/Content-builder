import React from 'react';
import { Button } from '../common/Button';
import { Bell, ShieldAlert, CheckCircle, Smartphone, Calendar } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';

interface NotificationsTabProps {
  notifCrit: boolean;
  setNotifCrit: (v: boolean) => void;
  notifApproval: boolean;
  setNotifApproval: (v: boolean) => void;
  notifPush: boolean;
  setNotifPush: (v: boolean) => void;
  notifWeekly: boolean;
  setNotifWeekly: (v: boolean) => void;
  isSaving: boolean;
  onSaveNotifications: (e: React.FormEvent) => void;
}

export const NotificationsTab: React.FC<NotificationsTabProps> = ({
  notifCrit,
  setNotifCrit,
  notifApproval,
  setNotifApproval,
  notifPush,
  setNotifPush,
  notifWeekly,
  setNotifWeekly,
  isSaving,
  onSaveNotifications,
}) => {
  const { language } = useLanguage();
  const isEn = language === 'en';

  return (
    <div className="rounded-xl border border-border-default bg-surface p-6 lg:p-8 space-y-6 shadow-subtle transition-colors duration-150">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-base lg:text-lg font-semibold text-txt-primary tracking-tight">
            {isEn ? 'Notification Channels & Frequency' : 'Canaux & Fréquence de Notification'}
          </h2>
          <p className="text-xs text-txt-muted mt-1 leading-relaxed">
            {isEn
              ? 'Configure alerts, approval requests, and analytical digests for editorial operations.'
              : 'Définissez les alertes et synthèses que vous souhaitez recevoir sur vos actions éditoriales.'}
          </p>
        </div>
        <div className="hidden sm:flex h-9 w-9 rounded-lg bg-surface-subtle border border-border-default items-center justify-center text-txt-muted shrink-0">
          <Bell className="h-4 w-4 text-accent" />
        </div>
      </div>

      <form onSubmit={onSaveNotifications} className="max-w-2xl space-y-6">
        <div className="divide-y divide-border-subtle border border-border-default rounded-lg overflow-hidden bg-surface-subtle">
          <label className="flex items-start sm:items-center justify-between p-4 cursor-pointer hover:bg-surface transition-colors gap-4">
            <div className="flex items-start gap-3">
              <ShieldAlert className="h-4 w-4 text-accent shrink-0 mt-0.5" />
              <div>
                <span className="block text-sm font-medium text-txt-primary">
                  {isEn ? 'Critical & Security Alerts' : 'Alertes critiques et de sécurité'}
                </span>
                <span className="text-xs text-txt-muted block mt-0.5">
                  {isEn
                    ? 'Immediate notifications on blocks, session revocations, or high-severity events.'
                    : 'Notifications immédiates lors de blocages, révocations de session ou événements sensibles.'}
                </span>
              </div>
            </div>
            <input
              type="checkbox"
              checked={notifCrit}
              onChange={(e) => setNotifCrit(e.target.checked)}
              className="h-5 w-5 rounded border-border-default bg-surface text-accent focus:ring-accent focus:ring-offset-surface shrink-0 mt-0.5 sm:mt-0 cursor-pointer"
            />
          </label>

          <label className="flex items-start sm:items-center justify-between p-4 cursor-pointer hover:bg-surface transition-colors gap-4">
            <div className="flex items-start gap-3">
              <CheckCircle className="h-4 w-4 text-accent shrink-0 mt-0.5" />
              <div>
                <span className="block text-sm font-medium text-txt-primary">
                  {isEn ? 'HITL Approval Requests' : "Demandes d'approbation HITL"}
                </span>
                <span className="text-xs text-txt-muted block mt-0.5">
                  {isEn
                    ? 'Be alerted whenever a generated content draft requires human validation.'
                    : "Soyez notifié dès qu'une variante de contenu nécessite votre validation humaine."}
                </span>
              </div>
            </div>
            <input
              type="checkbox"
              checked={notifApproval}
              onChange={(e) => setNotifApproval(e.target.checked)}
              className="h-5 w-5 rounded border-border-default bg-surface text-accent focus:ring-accent focus:ring-offset-surface shrink-0 mt-0.5 sm:mt-0 cursor-pointer"
            />
          </label>

          <label className="flex items-start sm:items-center justify-between p-4 cursor-pointer hover:bg-surface transition-colors gap-4">
            <div className="flex items-start gap-3">
              <Smartphone className="h-4 w-4 text-accent shrink-0 mt-0.5" />
              <div>
                <span className="block text-sm font-medium text-txt-primary">
                  {isEn ? 'Browser Push Notifications' : 'Notifications Push navigateur'}
                </span>
                <span className="text-xs text-txt-muted block mt-0.5">
                  {isEn
                    ? 'Real-time foreground notifications when you are active in the workspace.'
                    : "Alertes en temps réel lorsque vous êtes actif sur l'espace de travail."}
                </span>
              </div>
            </div>
            <input
              type="checkbox"
              checked={notifPush}
              onChange={(e) => setNotifPush(e.target.checked)}
              className="h-5 w-5 rounded border-border-default bg-surface text-accent focus:ring-accent focus:ring-offset-surface shrink-0 mt-0.5 sm:mt-0 cursor-pointer"
            />
          </label>

          <label className="flex items-start sm:items-center justify-between p-4 cursor-pointer hover:bg-surface transition-colors gap-4">
            <div className="flex items-start gap-3">
              <Calendar className="h-4 w-4 text-accent shrink-0 mt-0.5" />
              <div>
                <span className="block text-sm font-medium text-txt-primary">
                  {isEn ? 'Weekly Analytical Digest' : 'Synthèse analytique hebdomadaire'}
                </span>
                <span className="text-xs text-txt-muted block mt-0.5">
                  {isEn
                    ? 'Summary of publication performance and suggested editorial angles every Monday.'
                    : "Résumé des performances des publications et suggestions d'angles éditoriaux chaque lundi."}
                </span>
              </div>
            </div>
            <input
              type="checkbox"
              checked={notifWeekly}
              onChange={(e) => setNotifWeekly(e.target.checked)}
              className="h-5 w-5 rounded border-border-default bg-surface text-accent focus:ring-accent focus:ring-offset-surface shrink-0 mt-0.5 sm:mt-0 cursor-pointer"
            />
          </label>
        </div>

        <div className="pt-2">
          <Button type="submit" variant="primary" isLoading={isSaving} className="min-h-[44px] font-medium">
            {isEn ? 'Save Notification Settings' : 'Enregistrer les notifications'}
          </Button>
        </div>
      </form>
    </div>
  );
};
