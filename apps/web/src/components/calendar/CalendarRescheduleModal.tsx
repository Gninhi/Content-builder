import React from 'react';
import { Dialog } from '../common/Dialog';
import { Button } from '../common/Button';
import { Input } from '../common/Input';
import { AlertTriangle, Zap } from 'lucide-react';
import { CalendarPost } from './CalendarSlotCard';
import { useLanguage } from '../../context/LanguageContext';

interface CalendarRescheduleModalProps {
  isOpen: boolean;
  selectedPost: CalendarPost | null;
  newDateStr: string;
  collisionWarning: string | null;
  isOwner: boolean;
  isRescheduling: boolean;
  isPublishingNow: boolean;
  onDateChange: (val: string) => void;
  onClose: () => void;
  onReschedule: () => void;
  onPublishNow: (jobId: string) => void;
  onCancelJob: (jobId: string) => void;
}

export const CalendarRescheduleModal: React.FC<CalendarRescheduleModalProps> = ({
  isOpen,
  selectedPost,
  newDateStr,
  collisionWarning,
  isOwner,
  isRescheduling,
  isPublishingNow,
  onDateChange,
  onClose,
  onReschedule,
  onPublishNow,
  onCancelJob,
}) => {
  const { language } = useLanguage();
  const isEn = language === 'en';

  if (!isOpen || !selectedPost) return null;

  return (
    <Dialog
      isOpen={isOpen}
      onClose={onClose}
      title={isEn ? 'Reschedule Publication' : 'Reprogrammer la publication'}
    >
      <div className="space-y-4">
        <p className="text-xs text-txt-secondary leading-relaxed">
          {isEn
            ? 'Select a new broadcast time slot. Temporal collisions (<30m) are automatically verified.'
            : 'Choisissez le nouvel horaire de diffusion. Le système analyse les conflits temporels.'}
        </p>

        <div>
          <label className="block text-xs font-semibold text-txt-secondary mb-1.5">
            {isEn ? 'Date and Time (Local)' : 'Date et Heure (Local)'}
          </label>
          <Input
            type="datetime-local"
            value={newDateStr}
            onChange={(e) => onDateChange(e.target.value)}
          />
        </div>

        {collisionWarning && (
          <div className="flex items-center gap-2 rounded-lg border border-status-warning-border bg-status-warning-bg p-3 text-xs text-status-warning-text">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <span>{collisionWarning}</span>
          </div>
        )}

        <div className="flex flex-wrap items-center justify-between gap-2 pt-4 border-t border-border-subtle">
          <div className="flex items-center gap-2">
            {selectedPost.job_id && (
              <>
                <Button
                  variant="primary"
                  size="sm"
                  disabled={!isOwner}
                  isLoading={isPublishingNow}
                  onClick={() => onPublishNow(selectedPost.job_id!)}
                  title={!isOwner ? (isEn ? 'Reserved for Owner' : 'Réservé au rôle Owner') : (isEn ? 'Publish now without waiting' : 'Publier immédiatement sans attendre')}
                >
                  <Zap className="h-3.5 w-3.5 mr-1" />
                  {isEn ? 'Publish Now' : 'Diffuser maintenant'}
                </Button>
                <Button
                  variant="danger"
                  size="sm"
                  disabled={!isOwner}
                  onClick={() => onCancelJob(selectedPost.job_id!)}
                  title={!isOwner ? (isEn ? 'Reserved for Owner' : 'Réservé au rôle Owner') : (isEn ? 'Cancel scheduling' : 'Annuler la planification')}
                >
                  {isEn ? 'Cancel Job' : 'Annuler le job'}
                </Button>
              </>
            )}
          </div>
          <div className="flex gap-2 ml-auto">
            <Button variant="ghost" size="sm" onClick={onClose}>
              {isEn ? 'Close' : 'Fermer'}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              isLoading={isRescheduling}
              onClick={onReschedule}
            >
              {isEn ? 'Reschedule' : 'Reprogrammer'}
            </Button>
          </div>
        </div>
      </div>
    </Dialog>
  );
};
