import React from 'react';
import { Input } from '../common/Input';
import { Textarea } from '../common/Textarea';
import { useLanguage } from '../../context/LanguageContext';

interface InboxEditFormProps {
  hook: string;
  body: string;
  cta: string;
  onHookChange: (value: string) => void;
  onBodyChange: (value: string) => void;
  onCtaChange: (value: string) => void;
}

export const InboxEditForm: React.FC<InboxEditFormProps> = ({
  hook,
  body,
  cta,
  onHookChange,
  onBodyChange,
  onCtaChange,
}) => {
  const { language } = useLanguage();
  const isEn = language === 'en';

  return (
    <div className="space-y-4 rounded-xl border border-border-default bg-surface p-5 shadow-subtle">
      <div>
        <label className="block text-xs font-semibold text-txt-secondary mb-1.5">
          {isEn ? 'Hook' : 'Accroche (Hook)'}
        </label>
        <Input
          value={hook}
          onChange={(e) => onHookChange(e.target.value)}
          placeholder={isEn ? 'Compelling hook...' : 'Accroche percutante...'}
        />
      </div>
      <div>
        <label className="block text-xs font-semibold text-txt-secondary mb-1.5">
          {isEn ? 'Message body' : 'Corps du message'}
        </label>
        <Textarea
          rows={6}
          value={body}
          onChange={(e) => onBodyChange(e.target.value)}
          placeholder={isEn ? 'Detailed text...' : 'Texte détaillé...'}
        />
      </div>
      <div>
        <label className="block text-xs font-semibold text-txt-secondary mb-1.5">
          {isEn ? 'Call to action (CTA)' : 'Appel à l’action (CTA)'}
        </label>
        <Input
          value={cta}
          onChange={(e) => onCtaChange(e.target.value)}
          placeholder={isEn ? 'e.g., Share your thoughts in the comments!' : 'Ex: Donnez votre avis en commentaire !'}
        />
      </div>
    </div>
  );
};
