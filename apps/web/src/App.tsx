import React, { useEffect, useMemo } from 'react';
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  useLocation,
  useNavigate,
} from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { LanguageProvider, useLanguage } from './context/LanguageContext';
import { ThemeProvider } from './context/ThemeContext';
import { ToastProvider } from './context/ToastContext';
import { AppShell } from './components/layout/AppShell';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { useDocumentTitle } from './hooks/useDocumentTitle';

// Lazy-loaded auth screen (ANOM-36)
const AuthScreen = React.lazy(() => import('./screens/AuthScreen').then(m => ({ default: m.AuthScreen })));

// Primary screens (critical path)
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

const KNOWN_SCREENS = new Set([
  'dashboard',
  'inbox',
  'calendar',
  'veille',
  'ideation',
  'insights',
  'brand',
  'connections',
  'settings',
  'agents',
  'styleguide',
  'profile',
]);

/**
 * Handles seamless legacy hash migration (e.g., /ui/#veille or /ui/#/connections?oauth=success)
 * to clean HTML5 URLs (/ui/veille, /ui/connections?oauth=success).
 */
const HashMigrationHandler: React.FC = () => {
  const navigate = useNavigate();

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const checkAndMigrateHash = () => {
      const rawHash = window.location.hash;
      if (!rawHash) return;

      // Extract route and search params from hash: #/veille?filter=ia or #veille
      const cleanHash = rawHash.replace(/^#\/?/, '').trim();
      if (!cleanHash) return;

      const [routePart, queryPart] = cleanHash.split('?');
      const targetRoute = routePart.replace(/\/$/, '');

      if (KNOWN_SCREENS.has(targetRoute)) {
        const dest = `/${targetRoute}${queryPart ? `?${queryPart}` : ''}`;
        // Clean hash from window history to avoid loops
        window.history.replaceState(null, '', window.location.pathname);
        navigate(dest, { replace: true });
      }
    };

    checkAndMigrateHash();
    window.addEventListener('hashchange', checkAndMigrateHash);
    return () => window.removeEventListener('hashchange', checkAndMigrateHash);
  }, [navigate]);

  return null;
};

/**
 * Synchronous Root Redirector that inspects window.location.hash
 * BEFORE defaulting to /dashboard. This ensures that deep links like
 * /ui/#calendar or /ui/#/connections?oauth=success cleanly navigate to /calendar
 * without being overwritten by an eager redirect to /dashboard.
 */
const RootRedirect: React.FC = () => {
  if (typeof window !== 'undefined' && window.location.hash) {
    const rawHash = window.location.hash;
    const cleanHash = rawHash.replace(/^#\/?/, '').trim();
    if (cleanHash) {
      const [routePart, queryPart] = cleanHash.split('?');
      const targetRoute = routePart.replace(/\/$/, '');
      if (KNOWN_SCREENS.has(targetRoute)) {
        return <Navigate to={`/${targetRoute}${queryPart ? `?${queryPart}` : ''}`} replace />;
      }
    }
  }
  return <Navigate to="/dashboard" replace />;
};

const SCREEN_TITLES: Record<string, { fr: string; en: string }> = {
  dashboard: { fr: 'Tableau de bord', en: 'Dashboard' },
  inbox: { fr: 'Revue HITL', en: 'HITL Review' },
  calendar: { fr: 'Calendrier', en: 'Calendar' },
  veille: { fr: 'Veille', en: 'Monitoring' },
  ideation: { fr: 'Idéation', en: 'Ideation' },
  insights: { fr: 'Insights', en: 'Insights' },
  brand: { fr: 'Profil de Marque', en: 'Brand Profile' },
  connections: { fr: 'Connexions', en: 'Connections' },
  settings: { fr: 'Paramètres', en: 'Settings' },
  agents: { fr: "Banc d'Essai", en: 'Agents' },
  styleguide: { fr: 'Guide de Style', en: 'Style Guide' },
  profile: { fr: 'Mon Profil', en: 'Profile' },
};

const AuthenticatedAppLayout: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { language } = useLanguage();

  // Extract active screen identifier from URL pathname (e.g., /ui/veille -> veille)
  const currentScreen = useMemo(() => {
    const segments = location.pathname.split('/').filter(Boolean);
    const screen = segments[0] || 'dashboard';
    return KNOWN_SCREENS.has(screen) ? screen : 'dashboard';
  }, [location.pathname]);

  const screenTitle = useMemo(() => {
    const info = SCREEN_TITLES[currentScreen] || { fr: 'Tableau de bord', en: 'Dashboard' };
    return language === 'en' ? info.en : info.fr;
  }, [currentScreen, language]);

  useDocumentTitle(screenTitle);

  const handleNavigate = (screen: string) => {
    navigate(`/${screen}`);
  };

  return (
    <AppShell currentScreen={currentScreen} onNavigate={handleNavigate}>
      <ErrorBoundary level="page" onNavigate={handleNavigate} key={currentScreen}>
        <React.Suspense
          fallback={
            <div className="flex h-64 items-center justify-center text-txt-muted text-sm font-mono animate-pulse">
              Chargement du module...
            </div>
          }
        >
          <Routes>
            <Route path="/" element={<RootRedirect />} />
            <Route path="/dashboard" element={<DashboardScreen onNavigate={handleNavigate} />} />
            <Route path="/inbox" element={<InboxScreen onNavigate={handleNavigate} />} />
            <Route path="/calendar" element={<CalendarScreen />} />
            <Route path="/veille" element={<VeilleScreen onNavigate={handleNavigate} />} />
            <Route path="/ideation" element={<IdeationScreen onNavigate={handleNavigate} />} />
            <Route path="/insights" element={<InsightsScreen />} />
            <Route path="/brand" element={<BrandProfileScreen />} />
            <Route path="/connections" element={<ConnectionsScreen />} />
            <Route path="/settings" element={<SettingsScreen />} />
            <Route path="/agents" element={<AgentsScreen onNavigate={handleNavigate} />} />
            <Route path="/styleguide" element={<StyleGuideScreen />} />
            <Route path="/profile" element={<UserProfileScreen onNavigate={handleNavigate} />} />
            <Route path="*" element={<RootRedirect />} />
          </Routes>
        </React.Suspense>
      </ErrorBoundary>
    </AppShell>
  );
};

const MainRouter: React.FC = () => {
  const { isAuthenticated, isInitializing } = useAuth();
  const { language } = useLanguage();

  useDocumentTitle(!isAuthenticated ? (language === 'en' ? 'Sign In' : 'Connexion') : undefined);

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
    return (
      <React.Suspense
        fallback={
          <div className="flex min-h-screen items-center justify-center bg-app text-txt-primary">
            <div className="flex flex-col items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-accent text-accent-foreground shadow-subtle animate-pulse">
                <span className="font-bold text-lg font-mono">CO</span>
              </div>
              <span className="text-xs font-mono text-txt-muted">Chargement...</span>
            </div>
          </div>
        }
      >
        <AuthScreen />
      </React.Suspense>
    );
  }

  return (
    <>
      <HashMigrationHandler />
      <AuthenticatedAppLayout />
    </>
  );
};

export const App: React.FC = () => {
  return (
    <ErrorBoundary level="root">
      <ThemeProvider>
        <LanguageProvider>
          <AuthProvider>
            <ToastProvider>
              <BrowserRouter basename="/ui">
                <MainRouter />
              </BrowserRouter>
            </ToastProvider>
          </AuthProvider>
        </LanguageProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
};

export default App;
