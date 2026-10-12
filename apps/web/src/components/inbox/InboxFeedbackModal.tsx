import React from 'react';
import { Dialog } from '../common/Dialog';
import { Button } from '../common/Button';
import { Textarea } from '../common/Textarea';
import { useLanguage } from '../../context/LanguageContext';

interface InboxFeedbackModalProps {
  isOpen: boolean;
  action: 'rewrite' | 'reject' | null;
  comment: string;
  error: string | null;
  isLoading: boolean;
  onCommentChange: (value: string) => void;
  onClose: () => void;
  onSubmit: () => void;
}

export const InboxFeedbackModal: React.FC<InboxFeedbackModalProps> = ({
  isOpen,
  action,
  comment,
  error,
  isLoading,
  onCommentChange,
  onClose,
  onSubmit,
}) => {
  const { t } = useLanguage();

  if (!isOpen || !action) return null;

  return (
    <Dialog
      isOpen={isOpen}
      onClose={onClose}
      title={
        action === 'rewrite'
          ? 'Demander une réécriture par l’agent'
          : 'Rejeter le brouillon'
      }
    >
      <div className="space-y-4">
        <p className="text-xs text-slate-300">
          {t.inbox.comment_required_hint}
        </p>
        <Textarea
          rows={4}
          value={comment}
          onChange={(e) => onCommentChange(e.target.value)}
          placeholder="Ex: Le ton est trop informel sur le 2e paragraphe, corriger l'angle technique..."
          required
        />
        {error && (
          <p className="text-xs text-red-400 font-medium">{error}</p>
        )}

        <div className="flex justify-end gap-2.5 pt-2">
          <Button variant="ghost" onClick={onClose}>
            Annuler
          </Button>
          <Button
            variant={action === 'reject' ? 'danger' : 'primary'}
            isLoading={isLoading}
            onClick={onSubmit}
          >
            Confirmer l'action
          </Button>
        </div>
      </div>
    </Dialog>
  );
};
