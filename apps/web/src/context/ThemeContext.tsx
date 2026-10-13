import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';

export type ThemeMode = 'dark' | 'light' | 'system';
export type ThemePalette = 'graphite' | 'paper' | 'slate' | 'night' | 'contrast';
export type ThemeDensity = 'comfortable' | 'compact';
export type ThemeContrast = 'standard' | 'high' | 'system';
export type ThemeMotion = 'full' | 'reduced' | 'system';

export interface ThemePreferences {
  v: number;
  mode: ThemeMode;
  palette: ThemePalette;
  density: ThemeDensity;
  contrast: ThemeContrast;
  motion: ThemeMotion;
  fontScale: number;
}

export const DEFAULT_THEME_PREFERENCES: ThemePreferences = {
  v: 1,
  mode: 'dark',
  palette: 'graphite',
  density: 'comfortable',
  contrast: 'standard',
  motion: 'full',
  fontScale: 1,
};

export type SaveStatus = 'idle' | 'saving' | 'saved' | 'error';

interface ThemeContextType {
  preferences: ThemePreferences;
  mode: ThemeMode;
  palette: ThemePalette;
  density: ThemeDensity;
  contrast: ThemeContrast;
  motion: ThemeMotion;
  fontScale: number;
  resolvedMode: 'dark' | 'light';
  resolvedContrast: 'standard' | 'high';
  resolvedMotion: 'full' | 'reduced';
  saveStatus: SaveStatus;
  setMode: (mode: ThemeMode) => void;
  setPalette: (palette: ThemePalette) => void;
  setDensity: (density: ThemeDensity) => void;
  setContrast: (contrast: ThemeContrast) => void;
  setMotion: (motion: ThemeMotion) => void;
  setFontScale: (scale: number) => void;
  resetToDefaults: () => void;
  toggleMode: () => void;
  // Backwards compatibility aliases
  theme: 'dark' | 'light';
  setTheme: (t: 'dark' | 'light') => void;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

const COOKIE_NAME = 'co_prefs';
const COOKIE_MAX_AGE = 365 * 24 * 60 * 60; // 1 year in seconds
const BROADCAST_CHANNEL_NAME = 'contentops_theme_sync';

// Validate and sanitize schema values safely
function sanitizePreferences(raw: any): ThemePreferences {
  if (!raw || typeof raw !== 'object') return DEFAULT_THEME_PREFERENCES;
  
  const validModes: ThemeMode[] = ['dark', 'light', 'system'];
  const validPalettes: ThemePalette[] = ['graphite', 'paper', 'slate', 'night', 'contrast'];
  const validDensities: ThemeDensity[] = ['comfortable', 'compact'];
  const validContrasts: ThemeContrast[] = ['standard', 'high', 'system'];
  const validMotions: ThemeMotion[] = ['full', 'reduced', 'system'];

  return {
    v: 1,
    mode: validModes.includes(raw.mode) ? raw.mode : DEFAULT_THEME_PREFERENCES.mode,
    palette: validPalettes.includes(raw.palette) ? raw.palette : DEFAULT_THEME_PREFERENCES.palette,
    density: validDensities.includes(raw.density) ? raw.density : DEFAULT_THEME_PREFERENCES.density,
    contrast: validContrasts.includes(raw.contrast) ? raw.contrast : DEFAULT_THEME_PREFERENCES.contrast,
    motion: validMotions.includes(raw.motion) ? raw.motion : DEFAULT_THEME_PREFERENCES.motion,
    fontScale: typeof raw.fontScale === 'number' && raw.fontScale >= 0.8 && raw.fontScale <= 1.25 ? raw.fontScale : 1,
  };
}

function readStoredPreferences(): ThemePreferences {
  try {
    // 1. Read first-party non-sensitive cookie
    if (typeof document !== 'undefined') {
      const match = document.cookie.match(new RegExp('(^| )' + COOKIE_NAME + '=([^;]+)'));
      if (match && match[2]) {
        return sanitizePreferences(JSON.parse(decodeURIComponent(match[2])));
      }
    }
  } catch {
    // Fallback on error
  }

  try {
    // 2. LocalStorage fallback
    if (typeof window !== 'undefined' && window.localStorage) {
      const local = localStorage.getItem('co_prefs');
      if (local) return sanitizePreferences(JSON.parse(local));
      
      const legacy = localStorage.getItem('contentops_theme');
      if (legacy === 'light' || legacy === 'dark') {
        return { ...DEFAULT_THEME_PREFERENCES, mode: legacy };
      }
    }
  } catch {
    // Fallback on error
  }

  return DEFAULT_THEME_PREFERENCES;
}

function persistPreferences(prefs: ThemePreferences) {
  const json = JSON.stringify(prefs);
  try {
    if (typeof document !== 'undefined') {
      document.cookie = `${COOKIE_NAME}=${encodeURIComponent(json)}; path=/; max-age=${COOKIE_MAX_AGE}; SameSite=Lax`;
    }
  } catch {
    // Ignore cookie write errors
  }

  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      localStorage.setItem('co_prefs', json);
      localStorage.setItem('contentops_theme', prefs.mode);
    }
  } catch {
    // Ignore localStorage write errors in sandbox
  }
}

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [preferences, setPreferences] = useState<ThemePreferences>(readStoredPreferences);
  const [saveStatus, setSaveStatus] = useState<SaveStatus>('idle');
  const broadcastChannelRef = useRef<BroadcastChannel | null>(null);

  // System media query state
  const [systemDark, setSystemDark] = useState<boolean>(() => {
    if (typeof window === 'undefined') return true;
    return window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)').matches : true;
  });

  const [systemContrast, setSystemContrast] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false;
    return window.matchMedia ? window.matchMedia('(prefers-contrast: more)').matches : false;
  });

  const [systemReducedMotion, setSystemReducedMotion] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false;
    return window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)').matches : false;
  });

  // Calculate resolved values
  const resolvedMode: 'dark' | 'light' =
    preferences.mode === 'system' ? (systemDark ? 'dark' : 'light') : preferences.mode;

  const resolvedContrast: 'standard' | 'high' =
    preferences.contrast === 'system' ? (systemContrast ? 'high' : 'standard') : preferences.contrast;

  const resolvedMotion: 'full' | 'reduced' =
    preferences.motion === 'system' ? (systemReducedMotion ? 'reduced' : 'full') : preferences.motion;

  // Listen to system preferences changes in real time
  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return;

    const darkQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleDarkChange = (e: MediaQueryListEvent) => setSystemDark(e.matches);
    darkQuery.addEventListener('change', handleDarkChange);

    const contrastQuery = window.matchMedia('(prefers-contrast: more)');
    const handleContrastChange = (e: MediaQueryListEvent) => setSystemContrast(e.matches);
    contrastQuery.addEventListener('change', handleContrastChange);

    const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    const handleMotionChange = (e: MediaQueryListEvent) => setSystemReducedMotion(e.matches);
    motionQuery.addEventListener('change', handleMotionChange);

    return () => {
      darkQuery.removeEventListener('change', handleDarkChange);
      contrastQuery.removeEventListener('change', handleContrastChange);
      motionQuery.removeEventListener('change', handleMotionChange);
    };
  }, []);

  // Multi-tab synchronization via BroadcastChannel
  useEffect(() => {
    if (typeof window === 'undefined' || !('BroadcastChannel' in window)) return;

    try {
      const channel = new BroadcastChannel(BROADCAST_CHANNEL_NAME);
      broadcastChannelRef.current = channel;

      channel.onmessage = (event) => {
        if (event.data && event.data.type === 'THEME_SYNC') {
          const synced = sanitizePreferences(event.data.preferences);
          setPreferences(synced);
        }
      };

      return () => {
        channel.close();
      };
    } catch {
      // BroadcastChannel not available in environment
    }
  }, []);

  // Apply attributes to DOM without flash (disables transition for 1 frame)
  const applyDomAttributes = useCallback((
    targetMode: 'dark' | 'light',
    palette: ThemePalette,
    density: ThemeDensity,
    contrast: 'standard' | 'high',
    motion: 'full' | 'reduced'
  ) => {
    const root = document.documentElement;

    // Temporarily freeze transitions to eliminate flash
    root.classList.add('theme-transitioning');

    root.setAttribute('data-mode', targetMode);
    root.setAttribute('data-palette', palette);
    root.setAttribute('data-density', density);
    root.setAttribute('data-contrast', contrast);
    root.setAttribute('data-motion', motion);

    if (targetMode === 'dark') {
      root.classList.add('dark');
      root.classList.remove('light');
      root.style.colorScheme = 'dark';
    } else {
      root.classList.add('light');
      root.classList.remove('dark');
      root.style.colorScheme = 'light';
    }

    const themeMeta = document.getElementById('theme-color-meta');
    if (themeMeta) {
      themeMeta.setAttribute('content', targetMode === 'dark' ? '#090D14' : '#F6F8FA');
    }

    // Restore transitions on the next animation frame
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        root.classList.remove('theme-transitioning');
      });
    });
  }, []);

  // Sync DOM and Storage when preferences change
  useEffect(() => {
    const executeUpdate = () => {
      applyDomAttributes(
        resolvedMode,
        preferences.palette,
        preferences.density,
        resolvedContrast,
        resolvedMotion
      );
      persistPreferences(preferences);

      if (broadcastChannelRef.current) {
        broadcastChannelRef.current.postMessage({
          type: 'THEME_SYNC',
          preferences,
        });
      }
    };

    // Use View Transitions API if supported and motion is not reduced
    if (
      typeof document !== 'undefined' &&
      'startViewTransition' in document &&
      resolvedMotion !== 'reduced'
    ) {
      try {
        const transition = (document as any).startViewTransition(executeUpdate);
        if (transition?.finished && typeof transition.finished.catch === 'function') {
          transition.finished.catch(() => {});
        }
        if (transition?.ready && typeof transition.ready.catch === 'function') {
          transition.ready.catch(() => {});
        }
      } catch {
        executeUpdate();
      }
    } else {
      executeUpdate();
    }
  }, [
    preferences,
    resolvedMode,
    resolvedContrast,
    resolvedMotion,
    applyDomAttributes,
  ]);

  // Update preference helper
  const updatePreference = useCallback((updater: (prev: ThemePreferences) => ThemePreferences) => {
    setPreferences((prev) => {
      const next = sanitizePreferences(updater(prev));
      setSaveStatus('saving');
      // Simulated debounced save indication
      setTimeout(() => setSaveStatus('saved'), 400);
      setTimeout(() => setSaveStatus('idle'), 2500);
      return next;
    });
  }, []);

  const setMode = useCallback((mode: ThemeMode) => {
    updatePreference((prev) => ({ ...prev, mode }));
  }, [updatePreference]);

  const setPalette = useCallback((palette: ThemePalette) => {
    updatePreference((prev) => ({ ...prev, palette }));
  }, [updatePreference]);

  const setDensity = useCallback((density: ThemeDensity) => {
    updatePreference((prev) => ({ ...prev, density }));
  }, [updatePreference]);

  const setContrast = useCallback((contrast: ThemeContrast) => {
    updatePreference((prev) => ({ ...prev, contrast }));
  }, [updatePreference]);

  const setMotion = useCallback((motion: ThemeMotion) => {
    updatePreference((prev) => ({ ...prev, motion }));
  }, [updatePreference]);

  const setFontScale = useCallback((fontScale: number) => {
    updatePreference((prev) => ({ ...prev, fontScale }));
  }, [updatePreference]);

  const resetToDefaults = useCallback(() => {
    updatePreference(() => DEFAULT_THEME_PREFERENCES);
  }, [updatePreference]);

  const toggleMode = useCallback(() => {
    setMode(resolvedMode === 'dark' ? 'light' : 'dark');
  }, [resolvedMode, setMode]);

  return (
    <ThemeContext.Provider
      value={{
        preferences,
        mode: preferences.mode,
        palette: preferences.palette,
        density: preferences.density,
        contrast: preferences.contrast,
        motion: preferences.motion,
        fontScale: preferences.fontScale,
        resolvedMode,
        resolvedContrast,
        resolvedMotion,
        saveStatus,
        setMode,
        setPalette,
        setDensity,
        setContrast,
        setMotion,
        setFontScale,
        resetToDefaults,
        toggleMode,
        // Backward-compatible aliases
        theme: resolvedMode,
        setTheme: (t) => setMode(t),
        toggleTheme: toggleMode,
      }}
    >
      {/* Aria-live status region for screen-reader theme change notifications */}
      <div
        role="status"
        aria-live="polite"
        className="sr-only"
        aria-atomic="true"
      >
        {saveStatus === 'saving' && 'Enregistrement des préférences...'}
        {saveStatus === 'saved' && 'Préférences d’apparence enregistrées.'}
        {saveStatus === 'error' && 'Erreur lors de l’enregistrement des préférences.'}
      </div>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used within a ThemeProvider');
  return ctx;
};
