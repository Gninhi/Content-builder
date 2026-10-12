import React, { useState, useEffect, useRef } from 'react';
import {
  Search,
  LayoutDashboard,
  Inbox,
  Calendar,
  Sparkles,
  TrendingUp,
  Award,
  Share2,
  Sliders,
  User,
  Activity,
  Palette,
  Sun,
  Moon,
  Globe,
  LogOut,
  X,
} from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import { useTheme } from '../../context/ThemeContext';
import { useAuth } from '../../context/AuthContext';

interface CommandItem {
  id: string;
  category: 'nav' | 'appearance' | 'action';
  label: string;
  sublabel?: string;
  icon: React.FC<{ className?: string }>;
  badge?: string;
  action: () => void;
}

interface CommandMenuProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigate: (screen: string) => void;
}

export const CommandMenu: React.FC<CommandMenuProps> = ({
  isOpen,
  onClose,
  onNavigate,
}) => {
  const { t, language, setLanguage } = useLanguage();
  const { mode, toggleMode, setPalette, density, setDensity } = useTheme();
  const { logout } = useAuth();
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const isEn = language === 'en';

  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  const items: CommandItem[] = [
    // Navigation
    {
      id: 'nav-dashboard',
      category: 'nav',
      label: t.nav.dashboard,
      sublabel: isEn ? 'Overview & key metrics' : "Vue d'ensemble et métriques clés",
      icon: LayoutDashboard,
      action: () => {
        onNavigate('dashboard');
        onClose();
      },
    },
    {
      id: 'nav-inbox',
      category: 'nav',
      label: t.nav.inbox,
      sublabel: isEn ? 'Human-in-the-loop validation queue' : 'File de validation humaine obligatoire',
      icon: Inbox,
      action: () => {
        onNavigate('inbox');
        onClose();
      },
    },
    {
      id: 'nav-ideation',
      category: 'nav',
      label: t.nav.ideation,
      sublabel: isEn ? 'Research sources & generate scored ideas' : 'Veille et génération d’idées scorées',
      icon: Sparkles,
      action: () => {
        onNavigate('ideation');
        onClose();
      },
    },
    {
      id: 'nav-calendar',
      category: 'nav',
      label: t.nav.calendar,
      sublabel: isEn ? 'Editorial schedule & publications' : 'Planning éditorial et publications programmées',
      icon: Calendar,
      action: () => {
        onNavigate('calendar');
        onClose();
      },
    },
    {
      id: 'nav-insights',
      category: 'nav',
      label: t.nav.insights,
      sublabel: isEn ? 'Performance analytics & feedback loop' : 'Analyses de performance et boucle de rétroaction',
      icon: TrendingUp,
      action: () => {
        onNavigate('insights');
        onClose();
      },
    },
    {
      id: 'nav-brand',
      category: 'nav',
      label: t.nav.brand,
      sublabel: isEn ? 'Tone, identity and guardrails' : 'Ton, identité et garde-fous',
      icon: Award,
      action: () => {
        onNavigate('brand');
        onClose();
      },
    },
    {
      id: 'nav-connections',
      category: 'nav',
      label: t.nav.connections,
      sublabel: isEn ? 'Encrypted OAuth social vault' : 'Coffre OAuth réseaux sociaux',
      icon: Share2,
      action: () => {
        onNavigate('connections');
        onClose();
      },
    },
    {
      id: 'nav-agents',
      category: 'nav',
      label: (t.nav as any).agents || "Banc d'Essai Agents",
      sublabel: isEn ? 'Multi-agent sandbox test bench' : 'Test des workflows agentiques LangGraph',
      icon: Activity,
      action: () => {
        onNavigate('agents');
        onClose();
      },
    },
    {
      id: 'nav-styleguide',
      category: 'nav',
      label: (t.nav as any).styleguide || 'Guide de Style',
      sublabel: isEn ? 'Living style guide & design tokens' : 'Guide de style vivant et tokens OKLCH',
      icon: Palette,
      action: () => {
        onNavigate('styleguide');
        onClose();
      },
    },
    {
      id: 'nav-settings',
      category: 'nav',
      label: t.nav.settings,
      sublabel: isEn ? 'Governance, LLM keys & kill-switch' : 'Gouvernance, clés LLM et interrupteur d’urgence',
      icon: Sliders,
      action: () => {
        onNavigate('settings');
        onClose();
      },
    },
    {
      id: 'nav-profile',
      category: 'nav',
      label: t.nav.profile,
      sublabel: isEn ? 'User profile & preferences' : 'Mon compte et préférences',
      icon: User,
      action: () => {
        onNavigate('profile');
        onClose();
      },
    },

    // Appearance & Themes
    {
      id: 'theme-mode',
      category: 'appearance',
      label: mode === 'dark' ? (isEn ? 'Switch to Light Mode' : 'Basculer en Mode Clair') : (isEn ? 'Switch to Dark Mode' : 'Basculer en Mode Sombre'),
      icon: mode === 'dark' ? Sun : Moon,
      badge: mode.toUpperCase(),
      action: () => {
        toggleMode();
        onClose();
      },
    },
    {
      id: 'palette-graphite',
      category: 'appearance',
      label: isEn ? 'Palette: Graphite & Brass (Obsidian)' : 'Palette : Graphite & Laiton (Obsidienne)',
      icon: Palette,
      action: () => {
        setPalette('graphite');
        onClose();
      },
    },
    {
      id: 'palette-paper',
      category: 'appearance',
      label: isEn ? 'Palette: Paper & Ink' : 'Palette : Papier & Encre',
      icon: Palette,
      action: () => {
        setPalette('paper');
        onClose();
      },
    },
    {
      id: 'palette-slate',
      category: 'appearance',
      label: isEn ? 'Palette: Slate & Sage' : 'Palette : Ardoise & Sauge',
      icon: Palette,
      action: () => {
        setPalette('slate');
        onClose();
      },
    },
    {
      id: 'palette-night',
      category: 'appearance',
      label: isEn ? 'Palette: Night & Coral' : 'Palette : Nuit & Corail',
      icon: Palette,
      action: () => {
        setPalette('night');
        onClose();
      },
    },
    {
      id: 'palette-contrast',
      category: 'appearance',
      label: isEn ? 'Palette: High Contrast' : 'Palette : Contraste Renforcé',
      icon: Palette,
      action: () => {
        setPalette('contrast');
        onClose();
      },
    },
    {
      id: 'density-toggle',
      category: 'appearance',
      label: density === 'compact' ? (isEn ? 'Density: Comfortable' : 'Densité : Confortable') : (isEn ? 'Density: Compact' : 'Densité : Compacte'),
      icon: Sliders,
      badge: density,
      action: () => {
        setDensity(density === 'compact' ? 'comfortable' : 'compact');
        onClose();
      },
    },

    // Actions & Language
    {
      id: 'lang-toggle',
      category: 'action',
      label: language === 'fr' ? 'Switch language to English' : 'Passer l’interface en Français',
      icon: Globe,
      badge: language.toUpperCase(),
      action: () => {
        setLanguage(language === 'fr' ? 'en' : 'fr');
        onClose();
      },
    },
    {
      id: 'auth-logout',
      category: 'action',
      label: t.auth.logout,
      icon: LogOut,
      action: () => {
        logout();
        onClose();
      },
    },
  ];

  const filteredItems = items.filter((item) => {
    if (!query.trim()) return true;
    const q = query.toLowerCase().trim();
    return (
      item.label.toLowerCase().includes(q) ||
      (item.sublabel && item.sublabel.toLowerCase().includes(q))
    );
  });

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % Math.max(filteredItems.length, 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + filteredItems.length) % Math.max(filteredItems.length, 1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (filteredItems[selectedIndex]) {
        filteredItems[selectedIndex].action();
      }
    } else if (e.key === 'Escape') {
      e.preventDefault();
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={isEn ? 'Command palette' : 'Palette de commandes'}
      className="fixed inset-0 z-50 flex items-start justify-center pt-16 sm:pt-24 px-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-150"
      onClick={onClose}
    >
      <div
        className="w-full max-w-xl rounded-xl border border-border-default bg-surface-elevated shadow-elevated overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={handleKeyDown}
      >
        {/* Search Input Bar */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-border-subtle bg-surface">
          <Search className="h-4 w-4 text-txt-muted shrink-0" aria-hidden="true" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            placeholder={isEn ? 'Type a command or screen name...' : 'Rechercher un écran ou une action...'}
            className="w-full bg-transparent text-sm text-txt-primary placeholder:text-txt-muted focus:outline-none"
            aria-autocomplete="list"
          />
          {query ? (
            <button
              type="button"
              onClick={() => setQuery('')}
              className="text-txt-muted hover:text-txt-primary p-1 rounded"
              aria-label="Effacer la recherche"
            >
              <X className="h-4 w-4" />
            </button>
          ) : (
            <kbd className="hidden sm:inline-block rounded px-1.5 py-0.5 text-[10px] font-mono font-medium border border-border-default text-txt-muted bg-surface-subtle">
              Esc
            </kbd>
          )}
        </div>

        {/* Results List */}
        <div
          ref={listRef}
          className="max-h-80 overflow-y-auto p-2 space-y-1"
          role="listbox"
        >
          {filteredItems.length === 0 ? (
            <div className="py-8 text-center text-xs text-txt-muted">
              {isEn ? 'No commands or screens matching your query.' : 'Aucun résultat trouvé pour votre recherche.'}
            </div>
          ) : (
            filteredItems.map((item, index) => {
              const Icon = item.icon;
              const isSelected = index === selectedIndex;
              return (
                <button
                  key={item.id}
                  type="button"
                  role="option"
                  aria-selected={isSelected}
                  onClick={() => item.action()}
                  onMouseEnter={() => setSelectedIndex(index)}
                  className={`flex w-full items-center justify-between gap-3 px-3 py-2.5 rounded-lg text-left text-xs transition-colors ${
                    isSelected
                      ? 'bg-accent text-txt-inverse font-medium'
                      : 'text-txt-secondary hover:bg-surface-hover hover:text-txt-primary'
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <Icon className={`h-4 w-4 shrink-0 ${isSelected ? 'text-txt-inverse' : 'text-txt-muted'}`} />
                    <div className="min-w-0">
                      <span className="block truncate font-medium">{item.label}</span>
                      {item.sublabel && (
                        <span className={`block truncate text-[11px] ${isSelected ? 'text-txt-inverse/80' : 'text-txt-muted'}`}>
                          {item.sublabel}
                        </span>
                      )}
                    </div>
                  </div>
                  {item.badge && (
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded font-mono shrink-0 ${
                        isSelected
                          ? 'bg-txt-inverse/20 text-txt-inverse'
                          : 'bg-surface-subtle text-txt-muted border border-border-subtle'
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })
          )}
        </div>

        {/* Footer info */}
        <div className="px-4 py-2 border-t border-border-subtle bg-surface-subtle text-[11px] text-txt-muted flex items-center justify-between">
          <span>{isEn ? 'Navigate with ↑↓, select with ↵' : 'Naviguer avec ↑↓, valider avec ↵'}</span>
          <span className="font-mono text-[10px]">ContentOps Harness</span>
        </div>
      </div>
    </div>
  );
};
