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
  Shield,
  Activity,
} from 'lucide-react';

interface SidebarProps {
  currentScreen: string;
  onNavigate: (screen: string) => void;
  pendingReviewCount?: number;
  isOpenMobile?: boolean;
  onCloseMobile?: () => void;
  isSandboxMode?: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentScreen,
  onNavigate,
  pendingReviewCount = 0,
  isOpenMobile = false,
  onCloseMobile,
  isSandboxMode = true,
}) => {
  const { t } = useLanguage();
  const { session, logout, isOwner } = useAuth();

  const navItems = [
    {
      id: 'dashboard',
      label: t.nav.dashboard,
      icon: LayoutDashboard,
      badge: null,
    },
    {
      id: 'inbox',
      label: t.nav.inbox,
      icon: Inbox,
      badge: pendingReviewCount > 0 ? pendingReviewCount : null,
      badgeVariant: 'warning' as const,
    },
    {
      id: 'calendar',
      label: t.nav.calendar,
      icon: Calendar,
      badge: null,
    },
    {
      id: 'ideation',
      label: t.nav.ideation,
      icon: Sparkles,
      badge: null,
    },
    {
      id: 'insights',
      label: t.nav.insights,
      icon: TrendingUp,
      badge: null,
    },
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
      badgeVariant: 'neutral' as const,
    },
  ];

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpenMobile && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={onCloseMobile}
          aria-hidden="true"
        />
      )}

      <aside
        id="sidebar-navigation"
        aria-label="Navigation principale"
        className={`fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-slate-800 bg-slate-900/95 backdrop-blur-md transition-transform duration-300 ease-in-out lg:static lg:translate-x-0 ${
          isOpenMobile ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Brand Header */}
        <div className="flex h-16 items-center justify-between border-b border-slate-800 px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 text-white shadow-lg shadow-cyan-500/20">
              <Activity className="h-5 w-5" />
            </div>
            <div>
              <span className="font-bold tracking-tight text-white block text-sm leading-tight">
                ContentOps Harness
              </span>
              <span className="text-[10px] text-cyan-400 font-mono tracking-wider uppercase font-semibold">
                LangGraph v0.2
              </span>
            </div>
          </div>

          {/* Environment Badge */}
          <div>
            {isSandboxMode ? (
              <Badge variant="warning" className="px-2 py-0.5 text-[10px] uppercase font-bold tracking-wider">
                {t.header.sandbox_mode}
              </Badge>
            ) : (
              <Badge variant="success" className="px-2 py-0.5 text-[10px] uppercase font-bold tracking-wider animate-pulse">
                {t.header.live_mode}
              </Badge>
            )}
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 space-y-1.5 overflow-y-auto px-4 py-5" aria-label="Menu des écrans">
          {navItems.map((item) => {
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
                className={`group flex w-full items-center justify-between rounded-lg px-3.5 py-2.5 text-sm font-medium transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-offset-2 focus:ring-offset-slate-900 ${
                  isActive
                    ? 'bg-cyan-500/10 text-cyan-400 shadow-sm border border-cyan-500/30'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                }`}
                aria-current={isActive ? 'page' : undefined}
              >
                <div className="flex items-center gap-3">
                  <Icon
                    className={`h-4.5 w-4.5 transition-colors ${
                      isActive ? 'text-cyan-400' : 'text-slate-400 group-hover:text-slate-200'
                    }`}
                  />
                  <span>{item.label}</span>
                </div>
                {item.badge !== null && (
                  <Badge variant={item.badgeVariant || 'neutral'} className="text-xs px-2 py-0.5">
                    {item.badge}
                  </Badge>
                )}
              </button>
            );
          })}
        </nav>

        {/* User & Workspace Profile */}
        <div className="border-t border-slate-800 p-4 bg-slate-950/40">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3 overflow-hidden">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-800 text-slate-300 font-semibold text-xs border border-slate-700">
                <Shield className="h-4 w-4 text-cyan-400" />
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="truncate text-xs font-semibold text-slate-200">
                    {session?.user_id || 'Invité'}
                  </span>
                  <Badge variant={isOwner ? 'success' : 'info'} className="text-[10px] px-1.5 py-0">
                    {session?.role || 'Viewer'}
                  </Badge>
                </div>
                <p className="truncate text-[11px] text-slate-400 font-mono">
                  {session?.workspace_id || 'ws_default'}
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={logout}
              className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-red-400 transition-colors focus:outline-none focus:ring-2 focus:ring-red-500"
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
