import React from 'react';
import { CheckCircle2, XCircle, RefreshCw } from 'lucide-react';
import { Button } from '../common/Button';
import { useLanguage } from '../../context/LanguageContext';

interface InboxActionBarProps {
  canApprove: boolean;
  canEdit: boolean;
  userRole?: string;
  actionLoading: boolean;
  onReject: () => void;
  onRewrite: () => void;
  onApprove: () => void;
}

export const InboxActionBar: React.FC<InboxActionBarProps> = ({
  canApprove,
  canEdit,
  userRole,
  actionLoading,
  onReject,
  onRewrite,
  onApprove,
}) => {
  const { t, language } = useLanguage();
  const isEn = language === 'en';

  return (
    <div
      role="region"
      aria-label={isEn ? 'HITL Action Bar' : 'Barre d’action de validation'}
      className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4 rounded-xl border border-border-default bg-surface-elevated/95 p-3.5 sm:p-4 sticky bottom-4 shadow-elevated backdrop-blur-md z-20"
    >
      <div className="text-xs text-txt-muted">
        {canApprove ? (
          <span className="text-status-success-text font-medium flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-status-success-text shrink-0" aria-hidden="true" />
            {isEn
              ? 'Owner Role: Authorized to validate publication and apply the SHA-256 seal.'
              : 'Rôle Owner : Vous avez autorité pour valider la publication et apposer le scellement SHA-256.'}
          </span>
        ) : (
          <span className="text-txt-muted flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-txt-muted shrink-0" aria-hidden="true" />
            {isEn
              ? `Role ${userRole || 'Viewer'}: Only an Owner can approve broadcast to production.`
              : `Rôle ${userRole || 'Viewer'} : Seul un Owner peut approuver la diffusion en production.`}
          </span>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2 sm:gap-2.5 shrink-0">
        {/* Reject Button */}
        <Button
          variant="danger"
          size="sm"
          disabled={!canApprove || actionLoading}
          onClick={onReject}
          className="flex items-center gap-1.5 min-h-[44px]"
          aria-label={`${t.inbox.action_reject} (X)`}
        >
          <XCircle className="h-4 w-4" />
          <span>{t.inbox.action_reject} <kbd className="text-[10px] opacity-75 font-mono">X</kbd></span>
        </Button>

        {/* Rewrite Button */}
        <Button
          variant="secondary"
          size="sm"
          disabled={!canEdit || actionLoading}
          onClick={onRewrite}
          className="flex items-center gap-1.5 min-h-[44px]"
          aria-label={`${t.inbox.action_rewrite} (R)`}
        >
          <RefreshCw className="h-4 w-4" />
          <span>{t.inbox.action_rewrite} <kbd className="text-[10px] opacity-75 font-mono">R</kbd></span>
        </Button>

        {/* Approve Button */}
        <Button
          variant="primary"
          size="sm"
          disabled={!canApprove || actionLoading}
          onClick={onApprove}
          className="flex items-center gap-1.5 min-h-[44px]"
          aria-label={`${t.inbox.action_approve} (A)`}
        >
          <CheckCircle2 className="h-4 w-4" />
          <span>{t.inbox.action_approve} <kbd className="text-[10px] opacity-75 font-mono">A</kbd></span>
        </Button>
      </div>
    </div>
  );
};
