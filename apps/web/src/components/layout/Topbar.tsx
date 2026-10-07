import React from 'react';
import { useLanguage } from '../../context/LanguageContext';
import { useTheme } from '../../context/ThemeContext';
import { useAuth } from '../../context/AuthContext';
import {
  Menu,
  Sun,
  Moon,
  AlertTriangle,
  CheckCircle2,
  Clock,
} from 'lucide-react';

interface TopbarProps {
  currentScreenTitle: string;
  onOpenMobileMenu: () => void;
  killSwitchActive: boolean;
  onKillSwitchClick?: () => void;
  timezone?: string;
}

export const Topbar: React.FC<TopbarProps> = ({
  currentScreenTitle,
  onOpenMobileMenu,
  killSwitchActive,
  onKillSwitchClick,
  timezone = 'UTC',
}) => {
  const { t, language, setLanguage } = useLanguage();
  const { theme, toggleTheme } = useTheme();
  const { isOwner } = useAuth();

  return (
    <header className="sticky top-0 z-30 flex h-16 w-full items-center justify-between border-b border-slate-800 bg-slate-900/80 px-4 md:px-8 backdrop-blur-md">
      {/* Left: Mobile Toggle & Page Title */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onOpenMobileMenu}
          className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white lg:hidden focus:outline-none focus:ring-2 focus:ring-cyan-500"
          aria-label="Ouvrir le menu"
        >
          <Menu className="h-5 w-5" />
        </button>

        <div>
          <h1 className="text-base font-semibold text-white tracking-tight md:text-lg">
            {currentScreenTitle}
          </h1>
          <div className="flex items-center gap-2 text-[11px] text-slate-400">
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3 text-slate-500" />
              <span>{timezone}</span>
            </span>
          </div>
        </div>
      </div>

      {/* Right Actions: Kill Switch Indicator, Lang, Theme */}
      <div className="flex items-center gap-2 md:gap-4">
        {/* Kill Switch Global Banner / Button */}
        {killSwitchActive ? (
          <button
            type="button"
            onClick={onKillSwitchClick}
            disabled={!isOwner}
            aria-label={isOwner ? t.settings.deactivate_kill_switch : t.header.kill_switch_active}
            className="flex items-center gap-1.5 rounded-full bg-red-950/80 border border-red-500/50 px-3 py-1 text-xs font-semibold text-red-300 shadow-sm shadow-red-900/30 animate-pulse hover:bg-red-900/90 transition-all focus:outline-none focus:ring-2 focus:ring-red-400"
            title={isOwner ? t.settings.deactivate_kill_switch : t.header.kill_switch_active}
          >
            <AlertTriangle className="h-3.5 w-3.5 text-red-400" />
            <span className="hidden sm:inline font-mono uppercase">{t.header.kill_switch_active}</span>
          </button>
        ) : (
          <div className="flex items-center gap-1.5 rounded-full bg-emerald-950/40 border border-emerald-500/30 px-2.5 py-1 text-xs font-medium text-emerald-400">
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
            <span className="hidden md:inline">{t.header.kill_switch_normal}</span>
          </div>
        )}

        {/* Language Switcher */}
        <div className="flex items-center rounded-lg border border-slate-700 bg-slate-800 p-0.5 text-xs">
          <button
            type="button"
            onClick={() => setLanguage('fr')}
            className={`rounded px-2.5 py-1 font-medium transition-colors ${
              language === 'fr'
                ? 'bg-cyan-500 text-slate-950 font-bold'
                : 'text-slate-300 hover:text-white'
            }`}
            aria-label="FR - Passer en français"
          >
            FR
          </button>
          <button
            type="button"
            onClick={() => setLanguage('en')}
            className={`rounded px-2.5 py-1 font-medium transition-colors ${
              language === 'en'
                ? 'bg-cyan-500 text-slate-950 font-bold'
                : 'text-slate-300 hover:text-white'
            }`}
            aria-label="EN - Switch to English"
          >
            EN
          </button>
        </div>

        {/* Theme Toggle */}
        <button
          type="button"
          onClick={toggleTheme}
          className="rounded-lg border border-slate-700 bg-slate-800 p-2 text-slate-300 hover:bg-slate-700 hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-cyan-500"
          aria-label={theme === 'dark' ? 'Activer le mode clair' : 'Activer le mode sombre'}
          title={theme === 'dark' ? 'Mode clair' : 'Mode sombre'}
        >
          {theme === 'dark' ? <Sun className="h-4 w-4 text-amber-400" /> : <Moon className="h-4 w-4 text-cyan-400" />}
        </button>
      </div>
    </header>
  );
};
