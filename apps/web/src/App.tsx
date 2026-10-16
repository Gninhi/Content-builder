import React, { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { LanguageProvider } from './context/LanguageContext';
import { ThemeProvider } from './context/ThemeContext';
import { ToastProvider } from './context/ToastContext';
import { AppShell } from './components/layout/AppShell';
import { ErrorBoundary } from './components/common/ErrorBoundary';

// Primary screens (critical path)
import { AuthScreen } from './screens/AuthScreen';
import { DashboardScreen } from './screens/DashboardScreen';
import { InboxScreen } from './screens/InboxScreen';

// Secondary screens (code-split via dynamic import)
const CalendarScreen = React.lazy(() => import('./screens/CalendarScreen').then(m => ({ default: m.CalendarScreen })));
const VeilleScreen = React.lazy(() => import('./screens/VeilleScreen').then(m => ({ default: m.VeilleScreen })));
const IdeationScreen = React.lazy(() => import('./screens/IdeationScreen').then(m => ({ default: m.IdeationScreen })));
const InsightsScreen = React.lazy(() => import('./screens/InsightsScreen').then(m => ({ default: m.InsightsScreen })));
const BrandProfileScreen = React.lazy(() => import('./screens/BrandProfileScreen').then(m => ({ default: m.BrandProfileScreen })));
const ConnectionsScreen = React.lazy(() => import('./screens/ConnectionsScreen').then(m => ({ default: m.ConnectionsScreen })));
const SettingsScreen = React.lazy(() => import('./screens/SettingsScreen').then(m => ({ default: m.SettingsScreen })));
const AgentsScreen = React.lazy(() => import('./screens/AgentsScreen').then(m => ({ default: m.AgentsScreen })));
const UserProfileScreen = React.lazy(() => import('./screens/UserProfileScreen').then(m => ({ default: m.UserProfileScreen })));
const StyleGuideScreen = React.lazy(() => import('./screens/StyleGuideScreen').then(m => ({ default: m.StyleGuideScreen })));

const MainRouter: React.FC = () => {
  const { isAuthenticated, isInitializing } = useAuth();
  const [currentScreen, setCurrentScreen] = useState<string>(() => {
    if (typeof window !== 'undefined' && window.location.hash) {
      const hash = window.location.hash.replace('#', '').trim();
      if (hash) return hash;
    }
    return 'dashboard';
  });

  // Sync with URL hash for deep linking
  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.replace('#', '').trim();
      if (hash) {
        setCurrentScreen(hash);
      }
    };

    handleHashChange();
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const navigateTo = (screen: string) => {
    setCurrentScreen(screen);
    window.location.hash = screen;
  };

  if (isInitializing) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-app text-txt-primary">
        <div className="flex flex-col items-center gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-accent text-accent-foreground shadow-subtle animate-pulse">
            <span className="font-bold text-lg font-mono">CO</span>
          </div>
          <span className="text-xs font-mono text-txt-muted">Initialisation de la session sécurisée...</span>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <AuthScreen />;
  }

  const renderActiveScreen = () => {
    switch (currentScreen) {
      case 'dashboard':
        return <DashboardScreen onNavigate={navigateTo} />;
      case 'inbox':
        return <InboxScreen />;
      case 'calendar':
        return <CalendarScreen />;
      case 'veille':
        return <VeilleScreen onNavigate={navigateTo} />;
      case 'ideation':
        return <IdeationScreen />;
      case 'insights':
        return <InsightsScreen />;
      case 'brand':
        return <BrandProfileScreen />;
      case 'connections':
        return <ConnectionsScreen />;
      case 'settings':
        return <SettingsScreen />;
      case 'agents':
        return <AgentsScreen />;
      case 'styleguide':
        return <StyleGuideScreen />;
      case 'profile':
        return <UserProfileScreen onNavigate={navigateTo} />;
      default:
        return <DashboardScreen onNavigate={navigateTo} />;
    }
  };

  return (
    <AppShell currentScreen={currentScreen} onNavigate={navigateTo}>
      <React.Suspense
        fallback={
          <div className="flex h-64 items-center justify-center text-txt-muted text-sm font-mono animate-pulse">
            Chargement du module...
          </div>
        }
      >
        {renderActiveScreen()}
      </React.Suspense>
    </AppShell>
  );
};

export const App: React.FC = () => {
  return (
    <ErrorBoundary level="root">
      <ThemeProvider>
        <LanguageProvider>
          <AuthProvider>
            <ToastProvider>
              <MainRouter />
            </ToastProvider>
          </AuthProvider>
        </LanguageProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
};

export default App;
