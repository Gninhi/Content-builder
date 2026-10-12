import React from 'react';
import { Button } from '../common/Button';
import { Sun, Moon, Globe } from 'lucide-react';
import { Language, useLanguage } from '../../context/LanguageContext';
import { useTheme, ThemePalette, ThemeDensity, ThemeMotion } from '../../context/ThemeContext';

export const TIMEZONE_OPTIONS = [
  'UTC',
  'Europe/Paris',
  'Europe/London',
  'Europe/Berlin',
  'America/New_York',
  'America/Chicago',
  'America/Los_Angeles',
  'Asia/Tokyo',
  'Asia/Singapore',
  'Australia/Sydney',
];

interface PreferencesTabProps {
  theme?: string;
  setTheme?: (t: 'dark' | 'light') => void;
  language?: Language;
  setLanguage?: (l: Language) => void;
  timezone: string;
  setTimezone: (tz: string) => void;
  uiDensity: string;
  setUiDensity: (d: string) => void;
  defaultView: string;
  setDefaultView: (v: string) => void;
  isSaving: boolean;
  onSavePreferences: (newTheme?: 'dark' | 'light', newLang?: Language) => void;
}

export const PreferencesTab: React.FC<PreferencesTabProps> = ({
  timezone,
  setTimezone,
  setUiDensity,
  defaultView,
  setDefaultView,
  isSaving,
  onSavePreferences,
}) => {
  const { language, setLanguage } = useLanguage();
  const {
    mode,
    setMode,
    palette,
    setPalette,
    density,
    setDensity,
    motion,
    setMotion,
  } = useTheme();

  const isEn = language === 'en';

  const palettes: { id: ThemePalette; nameFr: string; nameEn: string; descFr: string; descEn: string; accentColor: string }[] = [
    {
      id: 'graphite',
      nameFr: 'Graphite & Laiton',
      nameEn: 'Graphite & Brass',
      descFr: 'Obsidienne sombre, titane et accent laiton ambré',
      descEn: 'Deep obsidian, titanium and warm amber brass',
      accentColor: '#d97706',
    },
    {
      id: 'paper',
      nameFr: 'Papier & Encre',
      nameEn: 'Paper & Ink',
      descFr: 'Édition pure, fond papier chaud et encre profonde',
      descEn: 'Editorial warmth, paper white and deep ink',
      accentColor: '#2563eb',
    },
    {
      id: 'slate',
      nameFr: 'Ardoise & Sauge',
      nameEn: 'Slate & Sage',
      descFr: 'Neutres minéraux froids et accent végétal sauge',
      descEn: 'Cool mineral slate and muted botanical sage',
      accentColor: '#059669',
    },
    {
      id: 'night',
      nameFr: 'Nuit & Corail',
      nameEn: 'Night & Coral',
      descFr: 'Noir absolu profond et accent corail terracotta',
      descEn: 'OLED black and terracotta coral accent',
      accentColor: '#e11d48',
    },
    {
      id: 'contrast',
      nameFr: 'Contraste Renforcé',
      nameEn: 'High Contrast',
      descFr: 'Bordures nettes, 7:1+ garanti pour accessibilité optimale',
      descEn: 'Sharp borders, 7:1+ guaranteed for maximum legibility',
      accentColor: '#2563eb',
    },
  ];

  return (
    <div className="rounded-xl border border-border-default bg-surface p-6 lg:p-8 space-y-8 shadow-subtle transition-colors duration-150">
      <div>
        <h2 className="text-base lg:text-lg font-semibold text-txt-primary tracking-tight">
          {isEn ? 'Appearance & Localization Preferences' : 'Préférences d’Affichage & Localisation'}
        </h2>
        <p className="text-xs text-txt-muted mt-1">
          {isEn
            ? 'Customize your theme, editorial density, language and time management.'
            : 'Personnalisez votre thème, la densité d’affichage, la langue et la gestion horaire.'}
        </p>
      </div>

      <div className="max-w-3xl space-y-8">
        {/* Theme Mode Selection */}
        <div className="space-y-3">
          <label className="block text-xs font-semibold uppercase tracking-wider text-txt-muted">
            {isEn ? 'Appearance Mode' : 'Mode d’affichage'}
          </label>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => {
                setMode('dark');
                onSavePreferences('dark');
              }}
              className={`flex items-center gap-3 p-3.5 rounded-lg border text-left transition-all ${
                mode === 'dark'
                  ? 'border-accent-border bg-accent-subtle text-accent-text shadow-xs'
                  : 'border-border-default bg-surface-subtle hover:border-border-hover text-txt-secondary'
              }`}
            >
              <div className="h-8 w-8 rounded-md bg-surface border border-border-default flex items-center justify-center shrink-0">
                <Moon className="h-4 w-4 text-accent" />
              </div>
              <div className="min-w-0">
                <span className="block text-xs font-semibold text-txt-primary">
                  {isEn ? 'Dark Mode' : 'Mode Sombre'}
                </span>
                <span className="text-[11px] text-txt-muted block truncate">
                  {isEn ? 'High contrast dark surfaces' : 'Surfaces sombres reposantes'}
                </span>
              </div>
            </button>

            <button
              type="button"
              onClick={() => {
                setMode('light');
                onSavePreferences('light');
              }}
              className={`flex items-center gap-3 p-3.5 rounded-lg border text-left transition-all ${
                mode === 'light'
                  ? 'border-accent-border bg-accent-subtle text-accent-text shadow-xs'
                  : 'border-border-default bg-surface-subtle hover:border-border-hover text-txt-secondary'
              }`}
            >
              <div className="h-8 w-8 rounded-md bg-surface border border-border-default flex items-center justify-center shrink-0">
                <Sun className="h-4 w-4 text-accent" />
              </div>
              <div className="min-w-0">
                <span className="block text-xs font-semibold text-txt-primary">
                  {isEn ? 'Light Mode' : 'Mode Clair'}
                </span>
                <span className="text-[11px] text-txt-muted block truncate">
                  {isEn ? 'Crisp daylight contrast' : 'Contraste pur pour environnements lumineux'}
                </span>
              </div>
            </button>
          </div>
        </div>

        {/* Artistic Palettes Selection */}
        <div className="space-y-3">
          <label className="block text-xs font-semibold uppercase tracking-wider text-txt-muted">
            {isEn ? 'Color Palette' : 'Palette de Couleurs'}
          </label>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {palettes.map((p) => {
              const isSelected = palette === p.id;
              return (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => setPalette(p.id)}
                  className={`flex flex-col p-3 rounded-lg border text-left transition-all ${
                    isSelected
                      ? 'border-accent-border bg-accent-subtle shadow-xs'
                      : 'border-border-default bg-surface-subtle hover:border-border-hover'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-semibold text-txt-primary">
                      {isEn ? p.nameEn : p.nameFr}
                    </span>
                    <span
                      className="h-3.5 w-3.5 rounded-full border border-border-subtle"
                      style={{ backgroundColor: p.accentColor }}
                      aria-hidden="true"
                    />
                  </div>
                  <span className="text-[11px] text-txt-muted line-clamp-2">
                    {isEn ? p.descEn : p.descFr}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Display Density & Motion */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <label htmlFor="pref-density" className="block text-xs font-semibold text-txt-secondary">
              {isEn ? 'UI Density' : 'Densité d’affichage'}
            </label>
            <select
              id="pref-density"
              value={density}
              onChange={(e) => {
                const val = e.target.value as ThemeDensity;
                setDensity(val);
                setUiDensity(val);
              }}
              className="w-full bg-surface border border-border-default rounded-md px-3 py-2 text-xs text-txt-primary focus:border-border-focus focus:outline-none"
            >
              <option value="comfortable">{isEn ? 'Comfortable (Standard)' : 'Confortable (Standard)'}</option>
              <option value="compact">{isEn ? 'Compact (High Density)' : 'Compacte (Haute Densité)'}</option>
            </select>
          </div>

          <div className="space-y-1.5">
            <label htmlFor="pref-motion" className="block text-xs font-semibold text-txt-secondary">
              {isEn ? 'Animation / Motion' : 'Animations & Transitions'}
            </label>
            <select
              id="pref-motion"
              value={motion}
              onChange={(e) => setMotion(e.target.value as ThemeMotion)}
              className="w-full bg-surface border border-border-default rounded-md px-3 py-2 text-xs text-txt-primary focus:border-border-focus focus:outline-none"
            >
              <option value="full">{isEn ? 'Smooth Transitions (Default)' : 'Transitions fluides (Par défaut)'}</option>
              <option value="reduced">{isEn ? 'Reduced Motion (Instant)' : 'Mouvements réduits (Instantané)'}</option>
            </select>
          </div>
        </div>

        {/* Language Selection */}
        <div className="space-y-3">
          <label className="block text-xs font-semibold uppercase tracking-wider text-txt-muted">
            {isEn ? 'Application Language' : 'Langue de l’application'}
          </label>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => {
                setLanguage('fr');
                onSavePreferences(undefined, 'fr');
              }}
              className={`flex items-center gap-3 p-3.5 rounded-lg border text-left transition-all ${
                language === 'fr'
                  ? 'border-accent-border bg-accent-subtle text-accent-text shadow-xs'
                  : 'border-border-default bg-surface-subtle hover:border-border-hover text-txt-secondary'
              }`}
            >
              <Globe className="h-4 w-4 text-accent shrink-0" />
              <div className="min-w-0">
                <span className="block text-xs font-semibold text-txt-primary">Français</span>
                <span className="text-[11px] text-txt-muted block truncate">
                  Interface, notifications et validation en français
                </span>
              </div>
            </button>

            <button
              type="button"
              onClick={() => {
                setLanguage('en');
                onSavePreferences(undefined, 'en');
              }}
              className={`flex items-center gap-3 p-3.5 rounded-lg border text-left transition-all ${
                language === 'en'
                  ? 'border-accent-border bg-accent-subtle text-accent-text shadow-xs'
                  : 'border-border-default bg-surface-subtle hover:border-border-hover text-txt-secondary'
              }`}
            >
              <Globe className="h-4 w-4 text-accent shrink-0" />
              <div className="min-w-0">
                <span className="block text-xs font-semibold text-txt-primary">English</span>
                <span className="text-[11px] text-txt-muted block truncate">
                  English user interface and workflows
                </span>
              </div>
            </button>
          </div>
        </div>

        {/* Timezone & Default View */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <label htmlFor="user-timezone" className="block text-xs font-semibold text-txt-secondary">
              {isEn ? 'Timezone (IANA)' : 'Fuseau horaire (IANA)'}
            </label>
            <select
              id="user-timezone"
              value={timezone}
              onChange={(e) => setTimezone(e.target.value)}
              className="w-full bg-surface border border-border-default rounded-md px-3 py-2 text-xs text-txt-primary focus:border-border-focus focus:outline-none"
            >
              {TIMEZONE_OPTIONS.map((tz) => (
                <option key={tz} value={tz}>
                  {tz}
                </option>
              ))}
            </select>
            <p className="text-[11px] text-txt-muted">
              {isEn
                ? 'Used for scheduling slots and publication times.'
                : 'Utilisé pour calculer les créneaux de programmation.'}
            </p>
          </div>

          <div className="space-y-1.5">
            <label htmlFor="default-view" className="block text-xs font-semibold text-txt-secondary">
              {isEn ? 'Default Landing Screen' : 'Écran de démarrage par défaut'}
            </label>
            <select
              id="default-view"
              value={defaultView}
              onChange={(e) => setDefaultView(e.target.value)}
              className="w-full bg-surface border border-border-default rounded-md px-3 py-2 text-xs text-txt-primary focus:border-border-focus focus:outline-none"
            >
              <option value="dashboard">{isEn ? "Overview (Dashboard)" : "Vue d'ensemble (Dashboard)"}</option>
              <option value="inbox">{isEn ? "HITL Validation (Inbox)" : "Revue HITL (Inbox)"}</option>
              <option value="calendar">{isEn ? "Editorial Calendar" : "Calendrier éditorial"}</option>
            </select>
          </div>
        </div>

        <div className="pt-2">
          <Button
            type="button"
            onClick={() => onSavePreferences()}
            isLoading={isSaving}
            variant="primary"
          >
            {isEn ? 'Save Preferences' : 'Enregistrer les préférences'}
          </Button>
        </div>
      </div>
    </div>
  );
};
