import React, { useState, useEffect } from 'react';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';
import { useAuth } from '../../context/AuthContext';
import { useLanguage } from '../../context/LanguageContext';
import { apiClient } from '../../lib/api';
import { InboxVariant, Workspace } from '../../types/api';

// Screen imports will be connected here
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
  const { t } = useLanguage();
  const { session, isAuthenticated } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [pendingCount, setPendingCount] = useState<number>(0);
  const [workspace, setWorkspace] = useState<Workspace | null>(null);

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
      default:
        return t.nav.dashboard;
    }
  };

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 overflow-hidden font-sans">
      {/* WCAG Skip to Main Content Link */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-50 focus:rounded-md focus:bg-cyan-500 focus:px-4 focus:py-2 focus:text-slate-950 focus:font-bold focus:shadow-lg focus:outline-none"
      >
        {t.common.skip_to_content || 'Aller au contenu principal'}
      </a>

      {/* Sidebar Navigation */}
      <Sidebar
        currentScreen={currentScreen}
        onNavigate={onNavigate}
        pendingReviewCount={pendingCount}
        isOpenMobile={mobileMenuOpen}
        onCloseMobile={() => setMobileMenuOpen(false)}
        isSandboxMode={true}
      />

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <Topbar
          currentScreenTitle={getScreenTitle(currentScreen)}
          onOpenMobileMenu={() => setMobileMenuOpen(true)}
          killSwitchActive={Boolean(workspace?.kill_switch_enabled)}
          onKillSwitchClick={() => onNavigate('settings')}
          timezone={workspace?.timezone || 'UTC'}
        />

        <main
          id="main-content"
          tabIndex={-1}
          className="flex-1 overflow-y-auto px-4 py-6 md:px-8 focus:outline-none"
        >
          {children}
        </main>
      </div>
    </div>
  );
};
