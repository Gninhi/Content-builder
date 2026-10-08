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
import { InsightsScreen } from './screens/InsightsScreen';
import { BrandProfileScreen } from './screens/BrandProfileScreen';
import { ConnectionsScreen } from './screens/ConnectionsScreen';
import { SettingsScreen } from './screens/SettingsScreen';
import { AgentsScreen } from './screens/AgentsScreen';

const MainRouter: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const [currentScreen, setCurrentScreen] = useState<string>('dashboard');

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

