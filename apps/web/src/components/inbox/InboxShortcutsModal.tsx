import React from 'react';
import { Dialog } from '../common/Dialog';
import { HITL_SHORTCUT_ITEMS } from '../../constants';
import { useLanguage } from '../../context/LanguageContext';

interface InboxShortcutsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const InboxShortcutsModal: React.FC<InboxShortcutsModalProps> = ({
  isOpen,
  onClose,
}) => {
  const { language } = useLanguage();
  const isEn = language === 'en';

  return (
    <Dialog
      isOpen={isOpen}
      onClose={onClose}
      title={isEn ? 'Keyboard Shortcuts' : 'Raccourcis Clavier Disponibles'}
    >
      <div className="space-y-2 text-xs">
        {HITL_SHORTCUT_ITEMS.map((sc) => (
          <div
            key={sc.key}
            className="flex items-center justify-between p-2.5 rounded-lg bg-surface-subtle border border-border-default"
          >
            <span className="text-txt-secondary">{sc.description}</span>
            <kbd className="px-2.5 py-1 rounded bg-surface border border-border-default text-accent font-mono font-bold text-xs shadow-xs">
              {sc.key}
            </kbd>
          </div>
        ))}
      </div>
    </Dialog>
  );
};
