import React from 'react';
import { Info, ArrowRight } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import { useAuth } from '../../context/AuthContext';

export const DemoBanner: React.FC = () => {
  const { t } = useLanguage();
  const { session, logout } = useAuth();

  if (!session?.is_demo) {
    return null;
  }

  return (
    <aside
      aria-label="Bannière d'information espace démo"
      className="shrink-0 border-b border-border-subtle bg-surface-subtle/80 px-4 py-2 text-xs text-txt-secondary backdrop-blur-xs flex items-center justify-between gap-3 transition-colors duration-150"
    >
      <div className="flex items-center gap-2 min-w-0">
        <Info className="h-4 w-4 text-accent shrink-0" aria-hidden="true" />
        <span className="truncate text-txt-secondary font-medium">
          {t.auth.demo_banner}
        </span>
      </div>

      <button
        type="button"
        onClick={() => logout()}
        className="inline-flex items-center gap-1.5 shrink-0 rounded px-2.5 py-1 text-xs font-semibold text-accent-text hover:text-accent-hover hover:bg-accent-subtle transition-colors focus:outline-none focus:ring-2 focus:ring-border-focus"
      >
        <span>{t.auth.demo_cta}</span>
        <ArrowRight className="h-3 w-3" aria-hidden="true" />
      </button>
    </aside>
  );
};
