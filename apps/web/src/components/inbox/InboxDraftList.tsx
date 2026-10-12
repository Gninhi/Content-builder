import React from 'react';
import { Badge } from '../common/Badge';
import { useLanguage } from '../../context/LanguageContext';
import { InboxVariant } from '../../types/api';

interface InboxDraftListProps {
  variants: InboxVariant[];
  selectedIndex: number;
  onSelect: (index: number) => void;
}

export const InboxDraftList: React.FC<InboxDraftListProps> = ({
  variants,
  selectedIndex,
  onSelect,
}) => {
  const { t, language } = useLanguage();
  const isEn = language === 'en';

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between px-1">
        <h3 className="text-xs font-semibold text-txt-secondary">
          {isEn ? 'Pending Drafts' : 'Brouillons en attente'}
        </h3>
        <span className="text-[11px] font-mono text-txt-muted">
          {variants.length}
        </span>
      </div>

      <div
        className="space-y-2 max-h-[calc(100vh-260px)] overflow-y-auto pr-1"
        role="listbox"
        aria-label={isEn ? 'Drafts queue to review' : 'Liste des brouillons à réviser'}
      >
        {variants.map((item, idx) => {
          const isSelected = idx === selectedIndex;
          const charCount = (item.hook?.length || 0) + (item.body?.length || 0);
          return (
            <button
              key={item.id}
              type="button"
              role="option"
              aria-selected={isSelected}
              onClick={() => onSelect(idx)}
              className={`w-full text-left rounded-lg p-3.5 border transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-border-focus ${
                isSelected
                  ? 'border-accent-border bg-accent-subtle shadow-xs'
                  : 'border-border-default bg-surface hover:border-border-hover hover:bg-surface-hover'
              }`}
            >
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-1.5">
                  <Badge
                    variant={item.platform === 'linkedin' ? 'info' : 'neutral'}
                    className="text-[10px]"
                  >
                    {item.platform?.toUpperCase()}
                  </Badge>
                  {item.is_degraded && (
                    <Badge variant="warning" className="text-[10px]">
                      {t.inbox.degraded_badge}
                    </Badge>
                  )}
                </div>
                <span className="text-[11px] font-mono text-txt-muted">
                  {charCount} {isEn ? 'chars' : 'car.'}
                </span>
              </div>

              <p className="text-xs font-semibold text-txt-primary line-clamp-1 mb-1">
                {item.hook || (isEn ? 'Untitled Hook' : 'Sans accroche')}
              </p>
              <p className="text-[11px] text-txt-muted line-clamp-2">
                {item.body || (isEn ? 'Empty body' : 'Corps vide')}
              </p>
            </button>
          );
        })}
      </div>
    </div>
  );
};
