import React, { useState, useEffect } from 'react';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';
import { DemoBanner } from './DemoBanner';
import { CommandMenu } from '../common/CommandMenu';
import { useAuth } from '../../context/AuthContext';
import { useLanguage } from '../../context/LanguageContext';
import { apiClient } from '../../lib/api';
import { InboxVariant, Workspace } from '../../types/api';
import { ErrorBoundary } from '../common/ErrorBoundary';
import {
  LayoutDashboard,
  Inbox,
  Sparkles,
  Calendar,
  Menu,
} from 'lucide-react';

interface AppShellProps {
  currentScreen: string;
  onNavigate: (screen: string) => void;
  children: React.ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({
  currentScreen,
  onNavigate,
  children,
}) => {
  const { t, language } = useLanguage();
  const { isAuthenticated, session } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [commandMenuOpen, setCommandMenuOpen] = useState(false);
  const [pendingCount, setPendingCount] = useState<number>(0);
  const [workspace, setWorkspace] = useState<Workspace | null>(null);

  const isEn = language === 'en';

  // Global Cmd+K / Ctrl+K keyboard shortcut
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setCommandMenuOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Poll review inbox count and workspace status safely
  useEffect(() => {
    if (!isAuthenticated) return;

    let isMounted = true;
    const fetchOverviewData = async () => {
      try {
        const inbox = await apiClient<InboxVariant[]>('/v1/inbox');
        if (isMounted) {
          setPendingCount(Array.isArray(inbox) ? inbox.length : 0);
        }
      } catch (e) {
        // Silent catch for background badge updates
      }

      if (session?.workspace_id) {
        try {
          const ws = await apiClient<Workspace>(`/v1/workspaces/${session.workspace_id}`);
          if (isMounted) {
            setWorkspace(ws);
          }
        } catch (e) {
          // Fallback workspace
        }
      }
    };

    fetchOverviewData();
    const interval = setInterval(fetchOverviewData, 15000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [isAuthenticated, session?.workspace_id]);

  const getScreenTitle = (screen: string): string => {
    switch (screen) {
      case 'dashboard':
        return t.nav.dashboard;
      case 'inbox':
        return t.nav.inbox;
      case 'calendar':
        return t.nav.calendar;
      case 'veille':
        return t.nav.veille;
      case 'ideation':
        return t.nav.ideation;
      case 'insights':
        return t.nav.insights;
      case 'brand':
        return t.nav.brand;
      case 'connections':
        return t.nav.connections;
      case 'settings':
        return t.nav.settings;
      case 'agents':
        return (t.nav as any).agents || "Banc d'Essai Agents";
      case 'styleguide':
        return (t.nav as any).styleguide || 'Guide de Style';
      case 'profile':
        return t.nav.profile;
      default:
        return t.nav.dashboard;
    }
  };

  return (
    <div className="flex h-screen bg-app text-txt-primary overflow-hidden font-sans transition-colors duration-150">
      {/* WCAG Skip to Main Content Link */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-50 focus:rounded-md focus:bg-accent focus:px-4 focus:py-2 focus:text-txt-inverse focus:font-semibold focus:shadow-md focus:outline-none"
      >
        {t.common.skip_to_content || 'Aller au contenu principal'}
      </a>

      {/* Global Command Palette (Cmd+K) */}
      <CommandMenu
        isOpen={commandMenuOpen}
        onClose={() => setCommandMenuOpen(false)}
        onNavigate={onNavigate}
      />

      {/* Sidebar Navigation (Desktop & Mobile Drawer) */}
      <Sidebar
        currentScreen={currentScreen}
        onNavigate={onNavigate}
        pendingReviewCount={pendingCount}
        isOpenMobile={mobileMenuOpen}
        onCloseMobile={() => setMobileMenuOpen(false)}
        isSandboxMode={true}
      />

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col overflow-hidden min-w-0">
        {/* Sleek, Non-Disruptive Demo Banner */}
        <DemoBanner />

        {/* Topbar */}
        <Topbar
          currentScreenTitle={getScreenTitle(currentScreen)}
          onOpenMobileMenu={() => setMobileMenuOpen(true)}
          killSwitchActive={Boolean(workspace?.kill_switch_enabled)}
          onKillSwitchClick={() => onNavigate('settings')}
          timezone={workspace?.timezone || 'UTC'}
          onOpenCommandMenu={() => setCommandMenuOpen(true)}
        />

        {/* Scrollable Main Content protected by Page-level ErrorBoundary */}
        <main
          id="main-content"
          tabIndex={-1}
          className="flex-1 overflow-y-auto px-3 py-4 sm:px-6 sm:py-6 lg:px-8 pb-20 lg:pb-8 focus:outline-none"
        >
          <div className="w-full max-w-7xl 2xl:max-w-[1720px] mx-auto">
            <ErrorBoundary level="page" onNavigate={onNavigate} key={currentScreen}>
              {children}
            </ErrorBoundary>
          </div>
        </main>

        {/* Mobile-First 5-Item Bottom Navigation Bar (WCAG 2.2 touch targets >= 44px) */}
        <nav
          aria-label={isEn ? 'Mobile quick navigation' : 'Navigation rapide mobile'}
          className="lg:hidden fixed bottom-0 inset-x-0 z-30 flex items-center justify-around border-t border-border-default bg-surface/95 backdrop-blur-md px-2 py-1 select-none"
        >
          <button
            type="button"
            onClick={() => onNavigate('dashboard')}
            className={`flex flex-col items-center justify-center min-h-[48px] min-w-[48px] px-2 py-1 rounded-md text-[10px] font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-border-focus ${
              currentScreen === 'dashboard'
                ? 'text-accent font-semibold'
                : 'text-txt-muted hover:text-txt-primary'
            }`}
            aria-current={currentScreen === 'dashboard' ? 'page' : undefined}
          >
            <LayoutDashboard className="h-4 w-4 shrink-0 mb-0.5" />
            <span>{isEn ? 'Control' : 'Piloter'}</span>
          </button>

          <button
            type="button"
            onClick={() => onNavigate('inbox')}
            className={`relative flex flex-col items-center justify-center min-h-[48px] min-w-[48px] px-2 py-1 rounded-md text-[10px] font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-border-focus ${
              currentScreen === 'inbox'
                ? 'text-accent font-semibold'
                : 'text-txt-muted hover:text-txt-primary'
            }`}
            aria-current={currentScreen === 'inbox' ? 'page' : undefined}
          >
            <Inbox className="h-4 w-4 shrink-0 mb-0.5" />
            <span>{isEn ? 'Validate' : 'Valider'}</span>
            {pendingCount > 0 && (
              <span className="absolute top-1 right-2 flex h-4 min-w-[16px] px-1 items-center justify-center rounded-full bg-status-warning-bg text-status-warning-text border border-status-warning-border text-[9px] font-bold">
                {pendingCount}
              </span>
            )}
          </button>

          <button
            type="button"
            onClick={() => onNavigate('ideation')}
            className={`flex flex-col items-center justify-center min-h-[48px] min-w-[48px] px-2 py-1 rounded-md text-[10px] font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-border-focus ${
              currentScreen === 'ideation'
                ? 'text-accent font-semibold'
                : 'text-txt-muted hover:text-txt-primary'
            }`}
            aria-current={currentScreen === 'ideation' ? 'page' : undefined}
          >
            <Sparkles className="h-4 w-4 shrink-0 mb-0.5" />
            <span>{isEn ? 'Ideas' : 'Idées'}</span>
          </button>

          <button
            type="button"
            onClick={() => onNavigate('calendar')}
            className={`flex flex-col items-center justify-center min-h-[48px] min-w-[48px] px-2 py-1 rounded-md text-[10px] font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-border-focus ${
              currentScreen === 'calendar'
                ? 'text-accent font-semibold'
                : 'text-txt-muted hover:text-txt-primary'
            }`}
            aria-current={currentScreen === 'calendar' ? 'page' : undefined}
          >
            <Calendar className="h-4 w-4 shrink-0 mb-0.5" />
            <span>{isEn ? 'Calendar' : 'Planning'}</span>
          </button>

          <button
            type="button"
            onClick={() => setMobileMenuOpen(true)}
            className="flex flex-col items-center justify-center min-h-[48px] min-w-[48px] px-2 py-1 rounded-md text-[10px] font-medium text-txt-muted hover:text-txt-primary transition-colors focus:outline-none focus:ring-2 focus:ring-border-focus"
            aria-label={isEn ? 'Open full menu' : 'Ouvrir le menu complet'}
          >
            <Menu className="h-4 w-4 shrink-0 mb-0.5" />
            <span>{isEn ? 'Menu' : 'Menu'}</span>
          </button>
        </nav>
      </div>
    </div>
  );
};
