import React, { useState } from 'react';
import { 
  Shield, 
  CheckCircle2, 
  AlertTriangle, 
  Terminal, 
  ExternalLink,
  Layers,
  Palette,
  Type,
  Sliders,
  Check,
  Copy,
  Inbox,
  Sun,
  Moon,
  Sparkles,
  Eye
} from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import { useTheme, ThemePalette } from '../context/ThemeContext';
import { Button } from '../components/common/Button';
import { Badge, StatusBadge } from '../components/common/Badge';
import { Input } from '../components/common/Input';
import { Textarea } from '../components/common/Textarea';
import { Select } from '../components/common/Select';
import { Dialog } from '../components/common/Dialog';
import { ConfirmDialog } from '../components/common/ConfirmDialog';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorState } from '../components/common/ErrorState';
import { PlatformPreview } from '../components/common/PlatformPreview';

interface PaletteSpec {
  id: ThemePalette;
  name: string;
  tagline: string;
  desc: string;
  accentHex: string;
  swatches: {
    label: string;
    darkHex: string;
    lightHex: string;
  }[];
  previewMood: string;
}

export const StyleGuideScreen: React.FC = () => {
  const { language } = useLanguage();
  const { mode, toggleMode, palette, setPalette } = useTheme();
  const isEn = language === 'en';

  // Interactive States
  const [copiedToken, setCopiedToken] = useState<string | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState<boolean>(false);
  const [isConfirmOpen, setIsConfirmOpen] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'tokens' | 'typography' | 'buttons' | 'badges' | 'forms' | 'states' | 'previews' | 'a11y'>('tokens');
  
  // Sample Form States
  const [sampleInput, setSampleInput] = useState<string>('Diffusion trimestrielle Q4');
  const [sampleErrorInput, setSampleErrorInput] = useState<string>('Valeur non scellée');
  const [sampleTextarea, setSampleTextarea] = useState<string>(
    'Voici une annonce stratégique pour le réseau B2B. L\'intégration de notre moteur de gouvernance éditoriale garantit une publication au plus une fois avec scellement cryptographique SHA-256.'
  );
  const [sampleSelect, setSampleSelect] = useState<string>('linkedin');

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedToken(text);
    setTimeout(() => setCopiedToken(null), 2000);
  };

  const palettes: PaletteSpec[] = [
    {
      id: 'graphite',
      name: 'Graphite & Laiton',
      tagline: 'Obsidienne, Titane & Laiton Ambré',
      desc: 'Direction sobre, équilibre architectural, métal brossé et laiton chaud non strident.',
      accentHex: '#d97706',
      swatches: [
        { label: 'Fond App', darkHex: '#0d1017', lightHex: '#f2f5f8' },
        { label: 'Surface', darkHex: '#121722', lightHex: '#ffffff' },
        { label: 'Bordure', darkHex: '#252e3d', lightHex: '#c2ccd7' },
        { label: 'Accent', darkHex: '#f59e0b', lightHex: '#b45309' },
        { label: 'Texte', darkHex: '#f3f4f6', lightHex: '#0e141e' },
      ],
      previewMood: 'border-amber-500/30 bg-amber-500/10 text-amber-400',
    },
    {
      id: 'paper',
      name: 'Papier & Encre',
      tagline: 'Vélin Lin Naturel & Encre Bleue Indigo',
      desc: 'Édition littéraire haut de gamme, fond papier lin tactile et encre de calligraphie profonde.',
      accentHex: '#1e3a8a',
      swatches: [
        { label: 'Fond App', darkHex: '#181310', lightHex: '#f5efe6' },
        { label: 'Surface', darkHex: '#241d17', lightHex: '#fcfaf6' },
        { label: 'Bordure', darkHex: '#3b2f25', lightHex: '#c9bcab' },
        { label: 'Accent', darkHex: '#3b82f6', lightHex: '#1d4ed8' },
        { label: 'Texte', darkHex: '#f5f0eb', lightHex: '#201812' },
      ],
      previewMood: 'border-blue-500/30 bg-blue-500/10 text-blue-400',
    },
    {
      id: 'slate',
      name: 'Ardoise & Sauge',
      tagline: 'Fjord Minéral Nordique & Sauge Alpine',
      desc: 'Sérénité scandinave, teintes minérales d’ardoise bleue et fraîcheur végétale reposante.',
      accentHex: '#10b981',
      swatches: [
        { label: 'Fond App', darkHex: '#0d1520', lightHex: '#ebf1f6' },
        { label: 'Surface', darkHex: '#131e2d', lightHex: '#fcfeff' },
        { label: 'Bordure', darkHex: '#27384c', lightHex: '#b8cad7' },
        { label: 'Accent', darkHex: '#22c55e', lightHex: '#15803d' },
        { label: 'Texte', darkHex: '#f1f5f9', lightHex: '#0f172a' },
      ],
      previewMood: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400',
    },
    {
      id: 'night',
      name: 'Nuit & Corail',
      tagline: 'Noir Pur OLED & Corail Vermillon Radiant',
      desc: 'Technologique, tranchant et moderne. Noir absolu sans compromis et corail énergisant.',
      accentHex: '#f43f5e',
      swatches: [
        { label: 'Fond App', darkHex: '#040308', lightHex: '#f6f6fb' },
        { label: 'Surface', darkHex: '#0b0a12', lightHex: '#ffffff' },
        { label: 'Bordure', darkHex: '#242033', lightHex: '#c5c2d6' },
        { label: 'Accent', darkHex: '#f43f5e', lightHex: '#e11d48' },
        { label: 'Texte', darkHex: '#ffffff', lightHex: '#13121e' },
      ],
      previewMood: 'border-rose-500/30 bg-rose-500/10 text-rose-400',
    },
    {
      id: 'contrast',
      name: 'Contraste Renforcé',
      tagline: 'Monochrome AAA & Ambre / Saphir 7:1+',
      desc: 'Accessibilité maximale certifiée WCAG 2.2 AAA. Bordures 2px renforcées et lisibilité absolue.',
      accentHex: '#f59e0b',
      swatches: [
        { label: 'Fond App', darkHex: '#000000', lightHex: '#ffffff' },
        { label: 'Surface', darkHex: '#080808', lightHex: '#ffffff' },
        { label: 'Bordure', darkHex: '#888888', lightHex: '#222222' },
        { label: 'Accent', darkHex: '#f59e0b', lightHex: '#0f52ba' },
        { label: 'Texte', darkHex: '#ffffff', lightHex: '#000000' },
      ],
      previewMood: 'border-amber-400 bg-amber-400/20 text-amber-300 font-bold',
    },
  ];

  const semanticTokens = [
    { name: '--bg-app', type: 'bg', cssVar: 'var(--bg-app)', role: 'Fond global de l’application', contrast: 'Base' },
    { name: '--bg-surface', type: 'bg', cssVar: 'var(--bg-surface)', role: 'Fond des conteneurs et cartes', contrast: '3:1+' },
    { name: '--bg-surface-raised', type: 'bg', cssVar: 'var(--bg-surface-raised)', role: 'Surfaces surélevées / modales', contrast: '4.5:1+' },
    { name: '--bg-subtle', type: 'bg', cssVar: 'var(--bg-subtle)', role: 'Arrière-plan discret / tableau', contrast: 'Doux' },
    { name: '--border-default', type: 'border', cssVar: 'var(--border-default)', role: 'Bordure standard structurelle', contrast: '3:1+' },
    { name: '--border-subtle', type: 'border', cssVar: 'var(--border-subtle)', role: 'Bordure subtile de séparation', contrast: 'Démarcation' },
    { name: '--text-primary', type: 'text', cssVar: 'var(--text-primary)', role: 'Texte principal à fort contraste', contrast: '12:1+ (AAA)' },
    { name: '--text-secondary', type: 'text', cssVar: 'var(--text-secondary)', role: 'Texte d’accompagnement', contrast: '7:1+ (AA)' },
    { name: '--text-muted', type: 'text', cssVar: 'var(--text-muted)', role: 'Légendes, horodatages et métadonnées', contrast: '4.5:1+ (AA)' },
    { name: '--accent-solid', type: 'bg', cssVar: 'var(--accent-solid)', role: 'Couleur maîtresse d’action', contrast: 'Primaire' },
    { name: '--accent-subtle', type: 'bg', cssVar: 'var(--accent-subtle)', role: 'Fond feutré sélection active', contrast: 'Sélection' },
    { name: '--accent-text', type: 'text', cssVar: 'var(--accent-text)', role: 'Texte accentué accessible', contrast: '4.5:1+ (AA)' },
    { name: '--status-success-bg', type: 'bg', cssVar: 'var(--status-success-bg)', role: 'Fond validation / Scellement', contrast: 'Succès' },
    { name: '--status-warning-bg', type: 'bg', cssVar: 'var(--status-warning-bg)', role: 'Fond attente HITL', contrast: 'Avertissement' },
    { name: '--status-danger-bg', type: 'bg', cssVar: 'var(--status-danger-bg)', role: 'Fond échec / Coupe-circuit', contrast: 'Danger' },
    { name: '--status-info-bg', type: 'bg', cssVar: 'var(--status-info-bg)', role: 'Fond programmation', contrast: 'Info' },
  ];

  return (
    <div className="space-y-8 pb-16">
      {/* Top Banner */}
      <div className="p-6 sm:p-8 rounded-xl border border-border-default bg-surface shadow-subtle relative overflow-hidden transition-colors duration-150">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 relative z-10">
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <span className="p-2.5 rounded-xl bg-accent-subtle text-accent-text border border-accent-border shadow-xs">
                <Palette className="w-6 h-6" />
              </span>
              <div>
                <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-txt-primary flex items-center gap-2">
                  {isEn ? 'Living Style Guide' : 'Guide de Style Vivant'}
                  <Badge variant="accent" withDot className="font-mono text-xs">
                    {palette.toUpperCase()} • {mode.toUpperCase()}
                  </Badge>
                </h1>
                <p className="text-xs sm:text-sm text-txt-muted max-w-2xl">
                  {isEn
                    ? 'Explore 5 living OKLCH palettes, switch modes instantly, test tactile accessibility and verify cryptographic governance tokens.'
                    : 'Explorez nos 5 palettes OKLCH vivantes, changez de thème en direct, testez l’accessibilité tactile et validez les tokens de scellement cryptographique.'}
                </p>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <Button 
              variant="outline" 
              size="sm" 
              onClick={toggleMode}
              className="text-xs min-h-[38px] font-medium"
            >
              {mode === 'dark' ? <Sun className="w-3.5 h-3.5 mr-1.5 text-accent" /> : <Moon className="w-3.5 h-3.5 mr-1.5 text-accent" />}
              {mode === 'dark' ? 'Basculer en Mode Clair' : 'Basculer en Mode Sombre'}
            </Button>
            <Button 
              variant="secondary" 
              size="sm" 
              onClick={() => setIsDialogOpen(true)}
              className="gap-1.5 text-xs min-h-[38px]"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              Tester Modale
            </Button>
            <Button 
              variant="danger" 
              size="sm" 
              onClick={() => setIsConfirmOpen(true)}
              className="gap-1.5 text-xs min-h-[38px]"
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              Kill-Switch Test
            </Button>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex flex-wrap gap-2 mt-6 pt-5 border-t border-border-subtle">
          {[
            { id: 'tokens', label: 'Tokens OKLCH', icon: Palette },
            { id: 'typography', label: 'Typographie Geist', icon: Type },
            { id: 'buttons', label: 'Boutons & Cibles', icon: Sliders },
            { id: 'badges', label: 'Badges & Statuts', icon: Shield },
            { id: 'forms', label: 'Formulaires & Contrôles', icon: Terminal },
            { id: 'states', label: 'États & Rétroactions', icon: Inbox },
            { id: 'previews', label: 'Aperçus Réseaux', icon: Layers },
            { id: 'a11y', label: 'Accessibilité WCAG 2.2', icon: CheckCircle2 },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-colors min-h-[38px] ${
                  isActive
                    ? 'bg-accent text-txt-inverse font-semibold shadow-xs'
                    : 'text-txt-muted hover:text-txt-primary hover:bg-surface-hover'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Hero Showcase: 5 OKLCH Living Palettes Selection Cards */}
      <section className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 className="text-base sm:text-lg font-bold text-txt-primary flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-accent" />
              {isEn ? 'Choose Your Visual Theme & Palette' : 'Choisissez Votre Direction Visuelle & Palette'}
            </h2>
            <p className="text-xs text-txt-muted">
              {isEn 
                ? 'Click on any palette card below to immediately transform the whole interface in real time.'
                : 'Cliquez sur une carte ci-dessous pour transformer immédiatement l’interface de toute l’application en temps réel.'}
            </p>
          </div>
          <div className="flex items-center gap-2 self-start sm:self-auto">
            <span className="text-[11px] font-mono text-txt-muted uppercase">Palette active :</span>
            <Badge variant="accent" withDot className="font-semibold text-xs capitalize">
              {palette} ({mode})
            </Badge>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
          {palettes.map((p) => {
            const isSelected = palette === p.id;
            return (
              <div
                key={p.id}
                onClick={() => setPalette(p.id)}
                className={`group relative flex flex-col justify-between rounded-xl border p-4 transition-all cursor-pointer shadow-subtle ${
                  isSelected
                    ? 'border-accent ring-2 ring-accent/30 bg-accent-subtle/30 shadow-md scale-[1.01]'
                    : 'border-border-default bg-surface hover:border-border-hover hover:bg-surface-hover'
                }`}
              >
                <div>
                  {/* Top Bar with Accent Dot and Status */}
                  <div className="flex items-center justify-between mb-2.5">
                    <div className="flex items-center gap-2">
                      <span
                        className="h-3.5 w-3.5 rounded-full border border-border-subtle shadow-xs"
                        style={{ backgroundColor: p.accentHex }}
                        aria-hidden="true"
                      />
                      <span className="font-bold text-xs text-txt-primary truncate">
                        {p.name}
                      </span>
                    </div>
                    {isSelected ? (
                      <Badge variant="accent" className="text-[10px] px-1.5 py-0 font-semibold shrink-0">
                        <Check className="w-3 h-3 mr-0.5 inline" /> Actif
                      </Badge>
                    ) : (
                      <span className="text-[10px] text-txt-muted font-mono opacity-0 group-hover:opacity-100 transition-opacity">
                        Choisir
                      </span>
                    )}
                  </div>

                  <p className="text-[11px] font-medium text-txt-secondary line-clamp-1 mb-1">
                    {p.tagline}
                  </p>
                  <p className="text-[10px] text-txt-muted line-clamp-2 leading-relaxed mb-3">
                    {p.desc}
                  </p>

                  {/* Swatch Pill Bar */}
                  <div className="mb-3 space-y-1">
                    <span className="text-[9px] font-mono uppercase tracking-wider text-txt-muted block">
                      Échantillons ({mode}) :
                    </span>
                    <div className="grid grid-cols-5 gap-1">
                      {p.swatches.map((s) => (
                        <div key={s.label} className="text-center group/swatch">
                          <div
                            className="h-5 w-full rounded border border-border-subtle shadow-xs"
                            style={{
                              backgroundColor: mode === 'dark' ? s.darkHex : s.lightHex,
                            }}
                            title={`${s.label}: ${mode === 'dark' ? s.darkHex : s.lightHex}`}
                          />
                          <span className="text-[8px] text-txt-muted block truncate mt-0.5">
                            {s.label.split(' ')[0]}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Live Mini Preview Box */}
                  <div className="p-2.5 rounded-lg border border-border-default bg-surface-subtle space-y-2 mb-3">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-semibold text-txt-primary truncate">Aperçu direct</span>
                      <span
                        className="text-[9px] px-1.5 py-0.5 rounded font-mono font-medium border"
                        style={{
                          backgroundColor: mode === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.03)',
                          borderColor: p.accentHex,
                          color: p.accentHex,
                        }}
                      >
                        SHA-256
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <div
                        className="h-5 px-2 rounded text-[10px] font-semibold flex items-center justify-center text-white shrink-0 shadow-xs"
                        style={{ backgroundColor: p.accentHex }}
                      >
                        Action
                      </div>
                      <div className="h-2 w-full bg-border-subtle rounded-full" />
                    </div>
                  </div>
                </div>

                <Button
                  variant={isSelected ? 'primary' : 'outline'}
                  size="sm"
                  className="w-full text-xs min-h-[32px] justify-center mt-1"
                  onClick={(e) => {
                    e.stopPropagation();
                    setPalette(p.id);
                  }}
                >
                  {isSelected ? 'Palette Actuelle' : 'Appliquer ce Thème'}
                </Button>
              </div>
            );
          })}
        </div>
      </section>

      {/* Live Component Sandbox Card */}
      <section className="p-6 rounded-xl border border-border-default bg-surface shadow-subtle space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border-subtle pb-3">
          <div className="flex items-center gap-2">
            <Eye className="w-4 h-4 text-accent" />
            <h3 className="text-sm font-bold text-txt-primary">
              Aperçu en Direct des Composants avec le Thème Actif
            </h3>
          </div>
          <span className="text-xs text-txt-muted font-mono">
            Rendu instantané des styles avec tokens sémantiques réels
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Column 1: Buttons & Actions */}
          <div className="space-y-3">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-txt-muted">Boutons & Cibles</h4>
            <div className="flex flex-col gap-2">
              <Button variant="primary" size="sm" className="w-full justify-center">
                Bouton Primaire (bg-accent)
              </Button>
              <Button variant="secondary" size="sm" className="w-full justify-center">
                Bouton Secondaire (bg-surface)
              </Button>
              <Button variant="outline" size="sm" className="w-full justify-center">
                Bouton Contour (border-default)
              </Button>
            </div>
          </div>

          {/* Column 2: Badges & Identifiers */}
          <div className="space-y-3">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-txt-muted">Badges & Statuts</h4>
            <div className="flex flex-wrap gap-2">
              <Badge variant="accent" withDot>Accent Actif</Badge>
              <Badge variant="success" withDot>Scellé SHA-256</Badge>
              <Badge variant="warning" withDot>Attente HITL</Badge>
              <Badge variant="danger" withDot>Erreur Réseau</Badge>
              <Badge variant="info" withDot>Planifié Q4</Badge>
              <Badge variant="neutral">Neutre Métadonnée</Badge>
            </div>
            <div className="p-3 rounded-lg bg-accent-subtle border border-accent-border text-xs text-accent-text font-mono mt-2">
              surface: bg-accent-subtle • texte: text-accent-text
            </div>
          </div>

          {/* Column 3: Live Input & Container */}
          <div className="space-y-3">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-txt-muted">Champs de Formulaire</h4>
            <Input 
              value={sampleInput} 
              onChange={(e) => setSampleInput(e.target.value)}
              placeholder="Texte de démonstration..."
            />
            <div className="flex items-center justify-between text-xs text-txt-muted font-mono pt-1">
              <span>Focus ring :</span>
              <span className="text-accent font-semibold">ring-border-focus</span>
            </div>
          </div>
        </div>
      </section>

      {/* Tab 1: Tokens OKLCH */}
      {activeTab === 'tokens' && (
        <section className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-base sm:text-lg font-semibold text-txt-primary flex items-center gap-2">
              <Palette className="w-4 h-4 text-accent" />
              Architecture des Tokens Sémantiques (OKLCH)
            </h2>
            <span className="text-xs text-txt-muted font-mono">Cliquez sur un token pour copier</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {semanticTokens.map((token) => (
              <div 
                key={token.name}
                onClick={() => copyToClipboard(token.name)}
                className="p-4 rounded-xl border border-border-default bg-surface hover:border-border-hover transition-colors cursor-pointer group shadow-subtle flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-mono text-txt-muted">{token.role}</span>
                    <Badge variant="neutral" className="text-[10px]">{token.contrast}</Badge>
                  </div>

                  {/* Real Live Swatch Preview */}
                  <div 
                    className="h-12 rounded-lg mb-3 border border-border-default flex items-center justify-center shadow-xs transition-colors"
                    style={{
                      background: token.type === 'bg' ? token.cssVar : 'var(--bg-surface)',
                      borderColor: token.type === 'border' ? token.cssVar : 'var(--border-default)',
                      borderWidth: token.type === 'border' ? '2px' : '1px',
                    }}
                  >
                    <span 
                      className="font-mono text-xs font-bold"
                      style={{
                        color: token.type === 'text' 
                          ? token.cssVar 
                          : token.type === 'bg' && (token.name.includes('solid') || token.name.includes('danger-text'))
                            ? 'var(--text-inverse)'
                            : 'var(--text-primary)'
                      }}
                    >
                      {token.name}
                    </span>
                  </div>
                </div>

                <div className="space-y-1">
                  <div className="text-xs font-semibold text-txt-primary group-hover:text-accent-text transition-colors">
                    {token.name}
                  </div>
                  <div className="text-[11px] font-mono text-txt-muted flex items-center justify-between">
                    <span>{token.cssVar}</span>
                    {copiedToken === token.name ? (
                      <Check className="w-3.5 h-3.5 text-status-success-text" />
                    ) : (
                      <Copy className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 text-txt-muted transition-opacity" />
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Tab 2: Typography */}
      {activeTab === 'typography' && (
        <section className="space-y-6">
          <div className="p-6 rounded-xl border border-border-default bg-surface space-y-6 shadow-subtle">
            <h2 className="text-base sm:text-lg font-semibold text-txt-primary flex items-center gap-2">
              <Type className="w-4 h-4 text-accent" />
              Hiérarchie Typographique Geist Sans & Geist Mono
            </h2>

            <div className="space-y-6 divide-y divide-border-subtle">
              <div className="pt-4 first:pt-0 space-y-2">
                <div className="flex items-center justify-between text-xs text-txt-muted font-mono">
                  <span>H1 Display — text-xl sm:text-2xl font-bold</span>
                  <span>Geist Sans (clamp 20px - 28px)</span>
                </div>
                <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-txt-primary">
                  Système Éditorial B2B & Gouvernance Cryptographique
                </h1>
              </div>

              <div className="pt-4 space-y-2">
                <div className="flex items-center justify-between text-xs text-txt-muted font-mono">
                  <span>H2 Section — text-lg font-semibold</span>
                  <span>Geist Sans (18px)</span>
                </div>
                <h2 className="text-lg font-semibold tracking-tight text-txt-primary">
                  Validation Humaine Obligatoire (Human-in-the-Loop)
                </h2>
              </div>

              <div className="pt-4 space-y-2">
                <div className="flex items-center justify-between text-xs text-txt-muted font-mono">
                  <span>Corps de Texte — text-xs sm:text-sm text-txt-secondary</span>
                  <span>Geist Sans (14px / Line-height 1.6)</span>
                </div>
                <p className="text-xs sm:text-sm text-txt-secondary leading-relaxed max-w-3xl">
                  Chaque proposition de contenu générée par les agents autonomes est soumise à une revue stricte. 
                  L'approbation humaine calcule l'empreinte cryptographique SHA-256 du texte définitif avant l'ordonnancement vers le réseau de diffusion.
                </p>
              </div>

              <div className="pt-4 space-y-2">
                <div className="flex items-center justify-between text-xs text-txt-muted font-mono">
                  <span>Chiffres Tabulaires & Scellement — font-mono tabular-nums</span>
                  <span>Geist Mono (Latin 400/500/600)</span>
                </div>
                <div className="p-4 rounded-lg bg-surface-subtle border border-border-default space-y-2">
                  <div className="text-xs font-mono text-accent-text flex items-center gap-2">
                    <span className="text-txt-muted">SHA-256:</span>
                    <span>e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855</span>
                  </div>
                  <div className="flex items-center gap-6 text-xs font-mono text-txt-muted">
                    <span>HORODATAGE: 2026-10-10T14:32:00Z</span>
                    <span>CARACTÈRES: 1,420 / 3,000</span>
                    <span>JOB_ID: job_01ha829c48b29</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Tab 3: Buttons & Actions */}
      {activeTab === 'buttons' && (
        <section className="space-y-6">
          <div className="p-6 rounded-xl border border-border-default bg-surface space-y-6 shadow-subtle">
            <div className="flex items-center justify-between">
              <h2 className="text-base sm:text-lg font-semibold text-txt-primary flex items-center gap-2">
                <Sliders className="w-4 h-4 text-accent" />
                Matrice des Boutons & Cibles Tactiles (min-h-[44px])
              </h2>
              <Badge variant="success">WCAG 2.2 Target Size</Badge>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-4">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-txt-muted">Variantes Sémantiques</h3>
                <div className="flex flex-wrap gap-3">
                  <Button variant="primary">Bouton Principal</Button>
                  <Button variant="secondary">Bouton Secondaire</Button>
                  <Button variant="outline">Bouton Contour</Button>
                  <Button variant="ghost">Bouton Discret</Button>
                  <Button variant="danger">Bouton Danger</Button>
                </div>
              </div>

              <div className="space-y-4">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-txt-muted">Tailles & États</h3>
                <div className="flex flex-wrap items-center gap-3">
                  <Button size="sm">Taille SM (36px)</Button>
                  <Button size="md">Taille MD (44px)</Button>
                  <Button size="lg">Taille LG (48px)</Button>
                  <Button isLoading>Chargement...</Button>
                  <Button disabled>Désactivé</Button>
                </div>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Tab 4: Badges & Statuses */}
      {activeTab === 'badges' && (
        <section className="space-y-6">
          <div className="p-6 rounded-xl border border-border-default bg-surface space-y-6 shadow-subtle">
            <h2 className="text-base sm:text-lg font-semibold text-txt-primary flex items-center gap-2">
              <Shield className="w-4 h-4 text-accent" />
              Badges & Statuts Métier Déterministes
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-3">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-txt-muted">Statuts de Publication</h3>
                <div className="flex flex-wrap gap-2.5">
                  <StatusBadge status="DRAFT" />
                  <StatusBadge status="PENDING_REVIEW" />
                  <StatusBadge status="APPROVED" />
                  <StatusBadge status="SCHEDULED" />
                  <StatusBadge status="PUBLISHING" />
                  <StatusBadge status="PUBLISHED" />
                  <StatusBadge status="FAILED" />
                  <StatusBadge status="DEGRADED" />
                </div>
              </div>

              <div className="space-y-3">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-txt-muted">Variantes avec Micro-Puce (WithDot)</h3>
                <div className="flex flex-wrap gap-2.5">
                  <Badge variant="success" withDot>Scellé SHA-256</Badge>
                  <Badge variant="warning" withDot>Revue HITL</Badge>
                  <Badge variant="danger" withDot>Échec Réseau</Badge>
                  <Badge variant="info" withDot>Programmé</Badge>
                  <Badge variant="neutral" withDot>Neutre</Badge>
                </div>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Tab 5: Forms */}
      {activeTab === 'forms' && (
        <section className="space-y-6">
          <div className="p-6 rounded-xl border border-border-default bg-surface space-y-6 shadow-subtle">
            <h2 className="text-base sm:text-lg font-semibold text-txt-primary flex items-center gap-2">
              <Terminal className="w-4 h-4 text-accent" />
              Champs de Saisie & Contrôles Accessibles
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-txt-secondary mb-1.5">Saisie Standard</label>
                  <Input value={sampleInput} onChange={(e) => setSampleInput(e.target.value)} />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-txt-secondary mb-1.5">Saisie avec Erreur</label>
                  <Input value={sampleErrorInput} onChange={(e) => setSampleErrorInput(e.target.value)} error="Valeur non conforme aux règles de scellement" />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-txt-secondary mb-1.5">Sélection Déroulante</label>
                  <Select value={sampleSelect} onChange={(e) => setSampleSelect(e.target.value)} options={[{ value: 'linkedin', label: 'LinkedIn Post' }, { value: 'x', label: 'X / Twitter Post' }]} />
                </div>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-txt-secondary mb-1.5">Zone de Texte Long (Textarea)</label>
                  <Textarea rows={6} value={sampleTextarea} onChange={(e) => setSampleTextarea(e.target.value)} />
                </div>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Tab 6: Feedback States */}
      {activeTab === 'states' && (
        <section className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="p-6 rounded-xl border border-border-default bg-surface shadow-subtle">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-txt-muted mb-4">État Vide (Empty State)</h3>
              <EmptyState title="Aucune publication planifiée" description="Validez des brouillons dans la revue HITL pour alimenter le calendrier." actionLabel="Aller à la Revue" onAction={() => {}} />
            </div>

            <div className="p-6 rounded-xl border border-border-default bg-surface shadow-subtle">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-txt-muted mb-4">État d'Erreur (Error State)</h3>
              <ErrorState message="Échec de connexion au coffre de chiffrement des jetons OAuth." onRetry={() => {}} />
            </div>
          </div>
        </section>
      )}

      {/* Tab 7: Previews */}
      {activeTab === 'previews' && (
        <section className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <PlatformPreview
              platform="linkedin"
              hook="Pourquoi les architectures agentiques échouent en production"
              body="90% des déploiements sous-estiment la gouvernance humaine et la traçabilité des décisions."
              cta="Découvrez notre modèle de validation HITL."
              authorName="Martial / Analyticatech"
              authorHeadline="Head of AI & Engineering"
            />

            <PlatformPreview
              platform="x"
              hook="Les systèmes autonomes nécessitent un contrôle strict"
              body="Sans scellement cryptographique et revue humaine, un agent en boucle fermée dérive inévitablement."
              cta="Plus d'infos ci-dessous"
              authorName="Analyticatech"
              authorHeadline="@analyticatech"
            />
          </div>
        </section>
      )}

      {/* Tab 8: Accessibility */}
      {activeTab === 'a11y' && (
        <section className="space-y-6">
          <div className="p-6 rounded-xl border border-border-default bg-surface space-y-4 shadow-subtle">
            <h2 className="text-base sm:text-lg font-semibold text-txt-primary flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-status-success-text" />
              Garanties Accessibilité WCAG 2.2 AA
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
              <div className="p-4 rounded-lg bg-surface-subtle border border-border-subtle space-y-1.5">
                <div className="font-semibold text-txt-primary">Contraste Minimal 4.5:1 / 7:1</div>
                <p className="text-txt-muted">
                  Toutes les palettes (Graphite, Papier, Ardoise, Nuit, Contraste) sont certifiées sans texte blanc sur fond blanc ou contraste insuffisant.
                </p>
              </div>
              <div className="p-4 rounded-lg bg-surface-subtle border border-border-subtle space-y-1.5">
                <div className="font-semibold text-txt-primary">Cibles Tactiles ≥ 44px</div>
                <p className="text-txt-muted">
                  Tous les boutons principaux et contrôles mobiles respectent la norme WCAG 2.2 target size minimale de 44x44px.
                </p>
              </div>
              <div className="p-4 rounded-lg bg-surface-subtle border border-border-subtle space-y-1.5">
                <div className="font-semibold text-txt-primary">Focus Visuel & Navigation Clavier</div>
                <p className="text-txt-muted">
                  Liens d’évitement (skip-to-content), anneau de focus net (focus-visible:ring-border-focus) et raccourcis J/K, A, R, X, ?.
                </p>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Sample Modals */}
      <Dialog isOpen={isDialogOpen} onClose={() => setIsDialogOpen(false)} title="Test de Modale Accessible">
        <div className="space-y-4">
          <p className="text-xs text-txt-secondary leading-relaxed">
            Cette modale utilise les tokens sémantiques universels, piège le focus avec accessibilité complète et gère la fermeture via Escape.
          </p>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="ghost" size="sm" onClick={() => setIsDialogOpen(false)}>Fermer</Button>
            <Button variant="primary" size="sm" onClick={() => setIsDialogOpen(false)}>Confirmer</Button>
          </div>
        </div>
      </Dialog>

      <ConfirmDialog
        isOpen={isConfirmOpen}
        onClose={() => setIsConfirmOpen(false)}
        onConfirm={() => setIsConfirmOpen(false)}
        title="Arrêt d'Urgence (Kill-Switch)"
        message="Êtes-vous certain de vouloir couper immédiatement toutes les publications automatiques et révoquer les accès de diffusion ?"
        confirmText="Activer le Kill-Switch"
        variant="danger"
      />
    </div>
  );
};
