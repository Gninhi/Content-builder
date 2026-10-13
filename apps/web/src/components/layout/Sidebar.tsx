import React from 'react';
import { useLanguage } from '../../context/LanguageContext';
import { useAuth } from '../../context/AuthContext';
import { Badge } from '../common/Badge';
import {
  LayoutDashboard,
  Inbox,
  Calendar,
  Sparkles,
  TrendingUp,
  Award,
  Share2,
  Sliders,
  LogOut,
  Activity,
  User,
  Shield,
  Palette,
  Radar,
} from 'lucide-react';

interface SidebarProps {
  currentScreen: string;
  onNavigate: (screen: string) => void;
  pendingReviewCount?: number;
  isOpenMobile?: boolean;
  onCloseMobile?: () => void;
  isSandboxMode?: boolean;
}

interface NavSection {
  title: string;
  items: {
    id: string;
    label: string;
    icon: React.FC<{ className?: string }>;
    badge?: string | number | null;
    badgeVariant?: 'success' | 'warning' | 'danger' | 'info' | 'neutral' | 'accent';
  }[];
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentScreen,
  onNavigate,
  pendingReviewCount = 0,
  isOpenMobile = false,
  onCloseMobile,
  isSandboxMode = true,
}) => {
  const { t, language } = useLanguage();
  const { session, user, workspaces, switchWorkspace, logout, isOwner, isDemo } = useAuth();
  const isEn = language === 'en';

  const sections: NavSection[] = [
    {
      title: isEn ? 'Control' : 'Piloter',
      items: [
        {
          id: 'dashboard',
          label: t.nav.dashboard,
          icon: LayoutDashboard,
          badge: null,
        },
      ],
    },
    {
      title: isEn ? 'Produce' : 'Produire',
      items: [
        {
          id: 'veille',
          label: t.nav.veille,
          icon: Radar,
          badge: null,
        },
        {
          id: 'ideation',
          label: t.nav.ideation,
          icon: Sparkles,
          badge: null,
        },
      ],
    },
    {
      title: isEn ? 'Validate' : 'Valider',
      items: [
        {
          id: 'inbox',
          label: t.nav.inbox,
          icon: Inbox,
          badge: pendingReviewCount > 0 ? pendingReviewCount : null,
          badgeVariant: 'warning',
        },
      ],
    },
    {
      title: isEn ? 'Distribute' : 'Diffuser',
      items: [
        {
          id: 'calendar',
          label: t.nav.calendar,
          icon: Calendar,
          badge: null,
        },
      ],
    },
    {
      title: isEn ? 'Learn' : 'Apprendre',
      items: [
        {
          id: 'insights',
          label: t.nav.insights,
          icon: TrendingUp,
          badge: null,
        },
      ],
    },
    {
      title: isEn ? 'Configure' : 'Configurer',
      items: [
        {
          id: 'brand',
          label: t.nav.brand,
          icon: Award,
          badge: null,
        },
        {
          id: 'connections',
          label: t.nav.connections,
          icon: Share2,
          badge: null,
        },
        {
          id: 'settings',
          label: t.nav.settings,
          icon: Sliders,
          badge: isOwner ? null : 'Owner',
          badgeVariant: 'neutral',
        },
        {
          id: 'profile',
          label: t.nav.profile,
          icon: User,
          badge: null,
        },
      ],
    },
    {
      title: isEn ? 'Studio' : 'Atelier',
      items: [
        {
          id: 'agents',
          label: (t.nav as any).agents || "Banc d'Essai",
          icon: Activity,
          badge: 'Live',
          badgeVariant: 'success',
        },
        {
          id: 'styleguide',
          label: (t.nav as any).styleguide || 'Guide de Style',
          icon: Palette,
          badge: 'Tokens',
          badgeVariant: 'accent',
        },
      ],
    },
  ];

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpenMobile && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-xs lg:hidden"
          onClick={onCloseMobile}
          aria-hidden="true"
        />
      )}

      <aside
        id="sidebar-navigation"
        aria-label="Navigation principale"
        className={`fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-border-default bg-surface transition-transform duration-200 ease-in-out lg:static lg:translate-x-0 ${
          isOpenMobile ? 'translate-x-0 shadow-elevated' : '-translate-x-full'
        }`}
      >
        {/* Brand Header */}
        <div className="flex h-16 items-center justify-between border-b border-border-subtle px-4 shrink-0">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent text-txt-inverse shadow-sm shrink-0 font-bold">
              <Shield className="h-4 w-4" />
            </div>
            <div className="min-w-0">
              <span className="font-semibold tracking-tight text-txt-primary block text-xs truncate leading-tight">
                ContentOps Harness
              </span>
              <span className="text-[10px] text-accent-text font-medium block">
                Enterprise Edition
              </span>
            </div>
          </div>

          {/* Environment Badge */}
          <div className="shrink-0">
            {isSandboxMode ? (
              <Badge variant="warning" className="px-1.5 py-0.2 text-[10px] font-medium">
                {t.header.sandbox_mode}
              </Badge>
            ) : (
              <Badge variant="success" className="px-1.5 py-0.2 text-[10px] font-medium">
                {t.header.live_mode}
              </Badge>
            )}
          </div>
        </div>

        {/* Navigation Sections */}
        <nav
          className="flex-1 overflow-y-auto px-2.5 py-3 space-y-4"
          aria-label="Menu des écrans"
        >
          {sections.map((section) => (
            <div key={section.title} className="space-y-0.5">
              <div className="px-2.5 pb-1 text-[10px] font-semibold uppercase tracking-wider text-txt-muted select-none">
                {section.title}
              </div>
              {section.items.map((item) => {
                const Icon = item.icon;
                const isActive = currentScreen === item.id;
                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => {
                      onNavigate(item.id);
                      if (onCloseMobile) onCloseMobile();
                    }}
                    className={`group flex w-full items-center justify-between rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-border-focus ${
                      isActive
                        ? 'bg-accent-subtle text-accent-text font-semibold border border-accent-border shadow-xs'
                        : 'text-txt-secondary hover:bg-surface-hover hover:text-txt-primary'
                    }`}
                    aria-current={isActive ? 'page' : undefined}
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <Icon
                        className={`h-4 w-4 shrink-0 transition-colors ${
                          isActive
                            ? 'text-accent'
                            : 'text-txt-muted group-hover:text-txt-secondary'
                        }`}
                      />
                      <span className="truncate">{item.label}</span>
                    </div>
                    {item.badge !== null && item.badge !== undefined && (
                      <Badge
                        variant={item.badgeVariant || 'neutral'}
                        className="text-[10px] px-1.5 py-0 shrink-0 font-mono"
                      >
                        {item.badge}
                      </Badge>
                    )}
                  </button>
                );
              })}
            </div>
          ))}
        </nav>

        {/* User & Workspace Profile Dock */}
        <div className="border-t border-border-subtle p-3 bg-surface-subtle shrink-0 space-y-2">
          {/* Workspace Switcher if > 1 workspace */}
          {workspaces && workspaces.length > 1 && (
            <div>
              <label htmlFor="ws-switcher" className="sr-only">
                {isEn ? 'Switch workspace' : 'Changer de workspace'}
              </label>
              <select
                id="ws-switcher"
                value={session?.workspace_id}
                onChange={(e) => switchWorkspace(e.target.value)}
                className="w-full text-xs rounded border border-border-default bg-surface py-1 px-2 text-txt-primary focus:border-border-focus focus:outline-none"
              >
                {workspaces.map((ws) => (
                  <option key={ws.workspace_id} value={ws.workspace_id}>
                    {ws.name} ({ws.role})
                  </option>
                ))}
              </select>
            </div>
          )}

          <div className="flex items-center justify-between gap-1.5">
            <button
              type="button"
              onClick={() => {
                onNavigate('profile');
                if (onCloseMobile) onCloseMobile();
              }}
              className={`flex flex-1 items-center gap-2.5 overflow-hidden rounded-md p-1.5 text-left transition-colors focus:outline-none focus:ring-2 focus:ring-border-focus ${
                currentScreen === 'profile'
                  ? 'bg-accent-subtle border border-accent-border'
                  : 'hover:bg-surface-hover'
              }`}
              title={t.nav.profile}
            >
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded bg-surface border border-border-default text-accent-text font-semibold text-xs">
                <User className="h-3.5 w-3.5" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5">
                  <span className="truncate text-xs font-semibold text-txt-primary">
                    {user?.full_name || session?.user_id || 'Invité'}
                  </span>
                  <Badge variant={isDemo ? 'warning' : isOwner ? 'success' : 'neutral'} className="text-[9px] px-1 py-0">
                    {isDemo ? 'Démo' : session?.role || 'Viewer'}
                  </Badge>
                </div>
                <p className="truncate text-[10px] text-txt-muted">
                  {workspaces.find((w) => w.workspace_id === session?.workspace_id)?.name || session?.workspace_id || 'ws_default'}
                </p>
              </div>
            </button>

            <button
              type="button"
              onClick={logout}
              className="rounded-md p-2 text-txt-muted hover:bg-surface-hover hover:text-status-danger-text transition-colors focus:outline-none focus:ring-2 focus:ring-border-focus shrink-0"
              title={t.auth.logout}
              aria-label={t.auth.logout}
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </aside>
    </>
  );
};
