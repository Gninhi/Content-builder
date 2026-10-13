import React from 'react';
import { Button } from '../common/Button';
import { Dialog } from '../common/Dialog';
import { Download, Trash2, AlertTriangle } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';

interface GdprTabProps {
  onExportData: () => void;
  isDeleteModalOpen: boolean;
  setIsDeleteModalOpen: (open: boolean) => void;
  deleteConfirmationText: string;
  setDeleteConfirmationText: (text: string) => void;
  isDeletingAccount: boolean;
  onDeleteAccount: () => void;
}

export const GdprTab: React.FC<GdprTabProps> = ({
  onExportData,
  isDeleteModalOpen,
  setIsDeleteModalOpen,
  deleteConfirmationText,
  setDeleteConfirmationText,
  isDeletingAccount,
  onDeleteAccount,
}) => {
  const { language } = useLanguage();
  const isEn = language === 'en';

  return (
    <div className="space-y-8">
      {/* Section: Data Portability */}
      <div className="rounded-xl border border-border-default bg-surface p-6 lg:p-8 space-y-4 shadow-subtle transition-colors duration-150">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
          <div>
            <h2 className="text-base lg:text-lg font-semibold text-txt-primary flex items-center gap-2">
              <Download className="h-5 w-5 text-accent" />
              {isEn ? 'Data Portability (GDPR Article 20)' : 'Portabilité des Données (Article 20 RGPD)'}
            </h2>
            <p className="text-xs text-txt-muted mt-1 leading-relaxed max-w-2xl">
              {isEn
                ? 'You have the right to receive all personal data relating to you in a structured, open, and machine-readable format. The exported JSON archive includes your profile, workspace bindings, sessions, and security audit log.'
                : "Vous avez le droit de recevoir l'ensemble de vos données à caractère personnel dans un format ouvert, structuré et lisible par machine. L'archive JSON générée contient votre profil, vos assignations de workspace, vos sessions et votre journal d'audit de sécurité."}
            </p>
          </div>
          <Button
            variant="primary"
            size="sm"
            onClick={onExportData}
            className="shrink-0 text-xs min-h-[40px] font-medium self-start sm:self-auto"
          >
            {isEn ? 'Download JSON Archive' : "Télécharger l'archive JSON"}
          </Button>
        </div>
      </div>

      {/* Section: Right to Erasure */}
      <div className="rounded-xl border border-red-500/30 bg-red-500/5 p-6 lg:p-8 space-y-4 shadow-subtle transition-colors duration-150">
        <div className="flex items-start gap-4">
          <div className="h-10 w-10 rounded-lg bg-red-500/10 border border-red-500/20 flex items-center justify-center text-red-500 shrink-0">
            <Trash2 className="h-5 w-5" />
          </div>
          <div className="space-y-2 flex-1">
            <h2 className="text-base lg:text-lg font-semibold text-red-500">
              {isEn
                ? 'Right to Erasure & Account Deletion (GDPR Article 17)'
                : "Droit à l'Effacement & Suppression de Compte (Article 17 RGPD)"}
            </h2>
            <p className="text-xs text-txt-secondary leading-relaxed max-w-2xl">
              {isEn
                ? 'Account deletion is irreversible. All your personal identifiers will be permanently anonymized, active sessions destroyed, and access revoked.'
                : 'La suppression de compte est irréversible. Toutes vos informations personnelles seront définitivement anonymisées, vos sessions seront détruites et vous ne pourrez plus accéder au système.'}
            </p>
            <div className="text-xs text-amber-500 bg-amber-500/10 border border-amber-500/20 p-3 rounded-lg max-w-2xl leading-relaxed">
              <strong>{isEn ? 'Governance constraint: ' : 'Contrainte de gouvernance : '}</strong>
              {isEn
                ? 'If you are the sole Owner of one or more active workspaces, deletion will be rejected to prevent orphaned resources. You must first transfer ownership or assign a co-owner.'
                : "Si vous êtes l'unique Propriétaire (Owner) d'un ou plusieurs workspaces actifs, la suppression sera bloquée pour prévenir l'abandon de ressources. Vous devrez d'abord transférer la propriété ou inviter un co-propriétaire."}
            </div>
            <div className="pt-2">
              <Button
                variant="danger"
                size="sm"
                onClick={() => {
                  setDeleteConfirmationText('');
                  setIsDeleteModalOpen(true);
                }}
                className="text-xs min-h-[40px] font-medium"
              >
                {isEn ? 'Delete Account' : 'Supprimer mon compte'}
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Account Deletion Confirmation Dialog */}
      <Dialog
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        title={isEn ? 'Account Deletion Confirmation' : 'Confirmation de suppression de compte'}
        maxWidth="md"
      >
        <div className="space-y-4">
          <div className="flex items-start gap-3 p-3.5 bg-red-500/10 border border-red-500/20 rounded-lg text-red-500 text-xs leading-relaxed">
            <AlertTriangle className="h-5 w-5 shrink-0 mt-0.5" />
            <div>
              <strong>{isEn ? 'Irreversible action: ' : 'Action irréversible : '}</strong>
              {isEn
                ? 'This action will immediately anonymize your personal data pursuant to GDPR Article 17 and terminate all active sessions.'
                : 'Cette opération anonymisera immédiatement vos données conformément au RGPD et révoquera toutes vos sessions actives.'}
            </div>
          </div>

          <div className="space-y-2">
            <label className="block text-xs font-medium text-txt-secondary">
              {isEn ? (
                <>
                  To confirm account deletion, please type <strong className="text-red-500">SUPPRIMER</strong> below:
                </>
              ) : (
                <>
                  Pour confirmer la suppression, veuillez saisir le mot <strong className="text-red-500">SUPPRIMER</strong> ci-dessous :
                </>
              )}
            </label>
            <input
              type="text"
              value={deleteConfirmationText}
              onChange={(e) => setDeleteConfirmationText(e.target.value)}
              placeholder="SUPPRIMER"
              className="w-full bg-surface-subtle border border-border-default rounded-lg px-3.5 py-2.5 text-sm text-txt-primary focus:outline-none focus:ring-2 focus:ring-red-500 font-mono min-h-[44px]"
            />
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-border-subtle">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setIsDeleteModalOpen(false)}
              disabled={isDeletingAccount}
              className="min-h-[40px] text-xs"
            >
              {isEn ? 'Cancel' : 'Annuler'}
            </Button>
            <Button
              variant="danger"
              size="sm"
              onClick={onDeleteAccount}
              isLoading={isDeletingAccount}
              disabled={deleteConfirmationText.trim() !== 'SUPPRIMER'}
              className="min-h-[40px] text-xs font-medium"
            >
              {isEn ? 'Confirm Permanent Deletion' : 'Confirmer la suppression définitive'}
            </Button>
          </div>
        </div>
      </Dialog>
    </div>
  );
};
