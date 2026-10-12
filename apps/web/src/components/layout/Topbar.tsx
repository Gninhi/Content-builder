import React, { useState } from 'react';
import { useLanguage } from '../../context/LanguageContext';
import { useTheme } from '../../context/ThemeContext';
import { useAuth } from '../../context/AuthContext';
import {
  Menu,
  Sun,
  Moon,
  Palette,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Search,
} from 'lucide-react';

interface TopbarProps {
  currentScreenTitle: string;
  onOpenMobileMenu: () => void;
  killSwitchActive: boolean;
  onKillSwitchClick?: () => void;
  timezone?: string;
  onOpenCommandMenu?: () => void;
}

export const Topbar: React.FC<TopbarProps> = ({
  currentScreenTitle,
  onOpenMobileMenu,
  killSwitchActive,
  onKillSwitchClick,
  timezone = 'UTC',
  onOpenCommandMenu,
}) => {
  const { t, language, setLanguage } = useLanguage();
  const { mode, toggleMode, palette, setPalette } = useTheme();
  const [isPaletteOpen, setIsPaletteOpen] = useState(false);
  const { isOwner } = useAuth();
  const isEn = language === 'en';

  return (
    <header className="sticky top-0 z-30 flex h-16 w-full items-center justify-between border-b border-border-default bg-surface/90 px-4 md:px-8 backdrop-blur-xs shrink-0 transition-colors duration-150">
      {/* Left: Mobile Toggle & Page Title */}
      <div className="flex items-center gap-3 min-w-0">
        <button
          type="button"
          onClick={onOpenMobileMenu}
          className="rounded-md p-2 text-txt-muted hover:bg-surface-hover hover:text-txt-primary lg:hidden focus:outline-none focus:ring-2 focus:ring-border-focus"
          aria-label={isEn ? 'Open menu' : 'Ouvrir le menu'}
        >
          <Menu className="h-5 w-5" />
        </button>

        <div className="min-w-0">
          <h1 className="text-sm md:text-base font-semibold text-txt-primary tracking-tight truncate">
            {currentScreenTitle}
          </h1>
          <div className="flex items-center gap-2 text-xs text-txt-muted">
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3 text-accent" />
              <span className="font-mono text-[11px]">{timezone}</span>
            </span>
          </div>
        </div>
      </div>

      {/* Center: Command Palette Trigger (Desktop) */}
      <div className="hidden md:flex items-center flex-1 max-w-sm mx-4">
        {onOpenCommandMenu && (
          <button
            type="button"
            onClick={onOpenCommandMenu}
            className="w-full flex items-center justify-between gap-2 px-3 py-1.5 rounded-md border border-border-default bg-surface-subtle text-xs text-txt-muted hover:border-border-hover hover:text-txt-secondary transition-colors focus:outline-none focus:ring-2 focus:ring-border-focus"
            aria-label={isEn ? 'Open command palette (Cmd+K)' : 'Ouvrir la palette de commandes (Cmd+K)'}
          >
            <span className="flex items-center gap-2">
              <Search className="h-3.5 w-3.5 text-txt-muted" />
              <span>{isEn ? 'Search commands...' : 'Rechercher (commandes, vues)...'}</span>
            </span>
            <kbd className="rounded px-1.5 py-0.5 text-[10px] font-mono border border-border-subtle bg-surface text-txt-muted">
              ⌘K
            </kbd>
          </button>
        )}
      </div>

      {/* Right Actions: Command Trigger (Mobile), Kill Switch Indicator, Lang, Theme */}
      <div className="flex items-center gap-2 md:gap-2.5 shrink-0">
        {/* Mobile Search Icon */}
        {onOpenCommandMenu && (
          <button
            type="button"
            onClick={onOpenCommandMenu}
            className="md:hidden rounded-md p-2 text-txt-muted hover:bg-surface-hover hover:text-txt-primary focus:outline-none focus:ring-2 focus:ring-border-focus"
            aria-label={isEn ? 'Search' : 'Rechercher'}
          >
            <Search className="h-4 w-4" />
          </button>
        )}

        {/* Kill Switch Global Indicator / Action */}
        {killSwitchActive ? (
          <button
            type="button"
            onClick={onKillSwitchClick}
            disabled={!isOwner}
            aria-label={isOwner ? t.settings.deactivate_kill_switch : t.header.kill_switch_active}
            className="flex items-center gap-1.5 rounded-md bg-status-danger-bg border border-status-danger-border px-2.5 py-1 text-xs font-semibold text-status-danger-text animate-pulse hover:opacity-90 transition-all focus:outline-none focus:ring-2 focus:ring-status-danger-border"
            title={isOwner ? t.settings.deactivate_kill_switch : t.header.kill_switch_active}
          >
            <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
            <span className="hidden sm:inline font-mono uppercase text-[11px]">{t.header.kill_switch_active}</span>
          </button>
        ) : (
          <div className="flex items-center gap-1.5 rounded-md bg-status-success-bg border border-status-success-border px-2.5 py-1 text-xs font-medium text-status-success-text">
            <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
            <span className="hidden lg:inline text-[11px]">{t.header.kill_switch_normal}</span>
          </div>
        )}

        {/* Language Switcher */}
        <div className="flex items-center rounded-md border border-border-default bg-surface-subtle p-0.5 text-xs font-mono">
          <button
            type="button"
            onClick={() => setLanguage('fr')}
            className={`rounded px-2 py-0.5 font-medium transition-colors ${
              language === 'fr'
                ? 'bg-accent text-txt-inverse font-bold shadow-xs'
                : 'text-txt-muted hover:text-txt-primary'
            }`}
            aria-label="Passer en français"
          >
            FR
          </button>
          <button
            type="button"
            onClick={() => setLanguage('en')}
            className={`rounded px-2 py-0.5 font-medium transition-colors ${
              language === 'en'
                ? 'bg-accent text-txt-inverse font-bold shadow-xs'
                : 'text-txt-muted hover:text-txt-primary'
            }`}
            aria-label="Switch to English"
          >
            EN
          </button>
        </div>

        {/* Palette Quick Switcher Dropdown */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setIsPaletteOpen((prev) => !prev)}
            className={`flex items-center gap-1.5 rounded-md border border-border-default bg-surface-subtle px-2.5 py-1.5 text-xs font-medium transition-colors hover:border-border-hover focus:outline-none focus:ring-2 focus:ring-border-focus ${
              isPaletteOpen ? 'border-accent-border bg-accent-subtle text-accent-text' : 'text-txt-secondary hover:text-txt-primary'
            }`}
            title={isEn ? 'Change Color Palette' : 'Changer la palette de couleurs'}
            aria-label={isEn ? 'Change Color Palette' : 'Changer la palette de couleurs'}
            aria-expanded={isPaletteOpen}
          >
            <Palette className="h-3.5 w-3.5 text-accent" />
            <span className="hidden sm:inline text-[11px] font-medium capitalize">
              {palette}
            </span>
          </button>

          {isPaletteOpen && (
            <>
              <div
                className="fixed inset-0 z-40"
                onClick={() => setIsPaletteOpen(false)}
                aria-hidden="true"
              />
              <div
                className="absolute right-0 mt-2 z-50 w-56 rounded-xl border border-border-default p-2 shadow-2xl animate-in fade-in zoom-in-95 duration-100"
                style={{ backgroundColor: 'var(--bg-surface-raised)', borderColor: 'var(--border-default)' }}
              >
                <div className="px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-txt-muted border-b border-border-subtle mb-1.5">
                  {isEn ? 'Color Palettes' : 'Palettes de Couleurs'}
                </div>
                {[
                  { id: 'graphite', name: 'Graphite & Laiton', desc: 'Obsidienne & Laiton', color: '#d97706' },
                  { id: 'paper', name: 'Papier & Encre', desc: 'Vélin chaud & Encre', color: '#1e3a8a' },
                  { id: 'slate', name: 'Ardoise & Sauge', desc: 'Minéral & Sauge nordique', color: '#10b981' },
                  { id: 'night', name: 'Nuit & Corail', desc: 'Noir OLED & Corail vermillon', color: '#f43f5e' },
                  { id: 'contrast', name: 'Contraste Renforcé', desc: 'Haute lisibilité AAA', color: '#f59e0b' },
                ].map((p) => {
                  const isSelected = palette === p.id;
                  return (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => {
                        setPalette(p.id as any);
                        setIsPaletteOpen(false);
                      }}
                      className={`flex w-full items-center justify-between rounded-lg px-2.5 py-2 text-xs text-left transition-colors ${
                        isSelected
                          ? 'bg-accent-subtle text-accent-text font-semibold border border-accent-border'
                          : 'text-txt-primary hover:bg-surface-hover'
                      }`}
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <span
                          className="h-3 w-3 rounded-full shrink-0 border border-border-subtle"
                          style={{ backgroundColor: p.color }}
                          aria-hidden="true"
                        />
                        <div className="min-w-0 truncate">
                          <span className="block truncate leading-tight">{p.name}</span>
                          <span className="text-[10px] text-txt-muted block truncate">{p.desc}</span>
                        </div>
                      </div>
                      {isSelected && (
                        <CheckCircle2 className="h-3.5 w-3.5 text-accent shrink-0 ml-1.5" />
                      )}
                    </button>
                  );
                })}
              </div>
            </>
          )}
        </div>

        {/* Theme Toggle (Dark / Light) */}
        <button
          type="button"
          onClick={toggleMode}
          className="rounded-md border border-border-default bg-surface-subtle p-2 text-txt-muted hover:text-txt-primary hover:border-border-hover transition-colors focus:outline-none focus:ring-2 focus:ring-border-focus"
          title={mode === 'dark' ? (isEn ? 'Switch to Light Mode' : 'Activer le mode clair') : (isEn ? 'Switch to Dark Mode' : 'Activer le mode sombre')}
          aria-label={mode === 'dark' ? (isEn ? 'Switch to Light Mode' : 'Activer le mode clair') : (isEn ? 'Switch to Dark Mode' : 'Activer le mode sombre')}
        >
          {mode === 'dark' ? (
            <Sun className="h-4 w-4 text-accent" />
          ) : (
            <Moon className="h-4 w-4 text-txt-secondary" />
          )}
        </button>
      </div>
    </header>
  );
};
