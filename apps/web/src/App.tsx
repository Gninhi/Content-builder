import React, { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { LanguageProvider } from './context/LanguageContext';
import { ThemeProvider } from './context/ThemeContext';
import { ToastProvider } from './context/ToastContext';
import { AppShell } from './components/layout/AppShell';

// Screens
import { AuthScreen } from './screens/AuthScreen';
import { DashboardScreen } from './screens/DashboardScreen';
import { InboxScreen } from './screens/InboxScreen';
import { CalendarScreen } from './screens/CalendarScreen';
import { IdeationScreen } from './screens/IdeationScreen';
import { VeilleScreen } from './screens/VeilleScreen';
import { InsightsScreen } from './screens/InsightsScreen';
import { BrandProfileScreen } from './screens/BrandProfileScreen';
import { ConnectionsScreen } from './screens/ConnectionsScreen';
import { SettingsScreen } from './screens/SettingsScreen';
import { AgentsScreen } from './screens/AgentsScreen';
import { UserProfileScreen } from './screens/UserProfileScreen';
import { StyleGuideScreen } from './screens/StyleGuideScreen';

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
      {renderActiveScreen()}
    </AppShell>
  );
};

export const App: React.FC = () => {
  return (
    <ThemeProvider>
      <LanguageProvider>
        <AuthProvider>
          <ToastProvider>
            <MainRouter />
          </ToastProvider>
        </AuthProvider>
      </LanguageProvider>
    </ThemeProvider>
  );
};

export default App;
