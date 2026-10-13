import React, { useState, useEffect } from 'react';
import { useLanguage } from '../context/LanguageContext';
import { useAuth } from '../context/AuthContext';
import { apiClient } from '../lib/api';
import { BrandProfile } from '../types/api';
import { Button } from '../components/common/Button';
import { Input } from '../components/common/Input';
import { Textarea } from '../components/common/Textarea';
import { Badge } from '../components/common/Badge';
import { Skeleton } from '../components/common/Skeleton';
import { ErrorState } from '../components/common/ErrorState';
import {
  Save,
  History,
  RotateCcw,
  CheckCircle2,
  Plus,
  X,
} from 'lucide-react';

export const BrandProfileScreen: React.FC = () => {
  const { t, language } = useLanguage();
  const { session, canEdit } = useAuth();
  const isEn = language === 'en';

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Brand profile fields
  const [voice, setVoice] = useState('');
  const [pillars, setPillars] = useState<string[]>([]);
  const [newPillar, setNewPillar] = useState('');
  const [prohibitedTopics, setProhibitedTopics] = useState<string[]>([]);
  const [newProhibited, setNewProhibited] = useState('');
  const [allowedCtas, setAllowedCtas] = useState<string[]>([]);
  const [newCta, setNewCta] = useState('');
  const [currentVersion, setCurrentVersion] = useState<number>(1);

  // Versions history
  const [versions, setVersions] = useState<BrandProfile[]>([]);
  const [showHistory, setShowHistory] = useState(false);

  const fetchProfileAndVersions = async () => {
    setLoading(true);
    setError(null);
    const wsId = session?.workspace_id || 'ws_default';
    try {
      const current = await apiClient<BrandProfile>(`/v1/brand-profiles/${wsId}`);
      setVoice(current.voice || '');
      setPillars(current.pillars || []);
      setProhibitedTopics(current.prohibited_topics || []);
      setAllowedCtas(current.cta_policy?.allowed_ctas || []);
      setCurrentVersion(current.version || 1);

      // Fetch version history
      const vers = await apiClient<BrandProfile[]>(`/v1/brand-profiles/${wsId}/versions`);
      setVersions(Array.isArray(vers) ? vers : []);
    } catch (err: any) {
      setError(err.message || (isEn ? 'Failed to fetch brand profile.' : 'Impossible de récupérer le profil de marque.'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProfileAndVersions();
  }, [session?.workspace_id]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canEdit) return;

    setSaving(true);
    setSaveSuccess(false);
    try {
      const res = await apiClient<BrandProfile>('/v1/brand-profiles', {
        method: 'POST',
        body: JSON.stringify({
          workspace_id: session?.workspace_id || 'ws_default',
          audience: ['Tech Leads', 'AI Engineers', 'CTOs', 'Founders'],
          voice,
          pillars,
          prohibited_topics: prohibitedTopics,
          cta_policy: {
            allowed_ctas: allowedCtas,
            max_per_post: 1,
          },
        }),
      });

      setCurrentVersion(res.version || currentVersion + 1);
      setSaveSuccess(true);
      await fetchProfileAndVersions();
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err: any) {
      alert(`Erreur de sauvegarde : ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleRestoreVersion = (v: BrandProfile) => {
    if (!confirm(isEn ? `Restore settings from version ${v.version}?` : `Restaurer les paramètres de la version ${v.version} ?`)) return;
    setVoice(v.voice || '');
    setPillars(v.pillars || []);
    setProhibitedTopics(v.prohibited_topics || []);
    setAllowedCtas(v.cta_policy?.allowed_ctas || []);
  };

  if (loading && !voice && pillars.length === 0) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64 rounded-md" />
        <Skeleton className="h-96 w-full rounded-xl" />
      </div>
    );
  }

  if (error && !voice) {
    return <ErrorState message={error} onRetry={fetchProfileAndVersions} />;
  }

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border-default pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <h2 className="text-lg sm:text-xl font-bold text-txt-primary tracking-tight">
              {t.brand.title}
            </h2>
            <Badge variant="accent" className="font-mono text-xs">
              v{currentVersion}
            </Badge>
          </div>
          <p className="text-xs text-txt-muted mt-1">
            {isEn
              ? 'Governs tone of voice, compliance boundaries, and editorial guardrails for all agents.'
              : 'Gouverne la voix, la conformité légale et les limites éditoriales de tous les agents.'}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setShowHistory(!showHistory)}
            className="flex items-center gap-1.5 text-xs min-h-[38px] sm:min-h-[36px]"
          >
            <History className="h-4 w-4 text-txt-muted" />
            <span>{showHistory ? (isEn ? 'Hide History' : 'Masquer l’historique') : (isEn ? 'Version History' : 'Historique des versions')}</span>
          </Button>

          {canEdit && (
            <Button
              variant="primary"
              size="sm"
              isLoading={saving}
              onClick={handleSave}
              className="flex items-center gap-1.5 text-xs min-h-[38px] sm:min-h-[36px]"
            >
              <Save className="h-4 w-4" />
              <span>{t.brand.save_btn}</span>
            </Button>
          )}
        </div>
      </div>

      {saveSuccess && (
        <div className="rounded-xl border border-status-success-border bg-status-success-bg p-4 text-xs sm:text-sm text-status-success-text flex items-center gap-3">
          <CheckCircle2 className="h-5 w-5 text-status-success-text shrink-0" />
          <span>
            {isEn
              ? 'Brand profile updated successfully and new sealed version incremented.'
              : 'Profil de marque mis à jour avec succès et nouvelle version incrémentée.'}
          </span>
        </div>
      )}

      {/* Version History Drawer / Panel */}
      {showHistory && (
        <div className="rounded-xl border border-border-default bg-surface p-5 sm:p-6 space-y-4 shadow-subtle">
          <div className="flex items-center justify-between border-b border-border-subtle pb-3">
            <h3 className="text-xs font-semibold text-txt-secondary">
              {isEn ? `Sealed Version History (${versions.length})` : `Historique des versions scellées (${versions.length})`}
            </h3>
            <span className="text-[11px] text-txt-muted">
              {isEn ? 'Non-destructive restore' : 'Restauration non destructive'}
            </span>
          </div>
          <div className="space-y-2.5 max-h-64 overflow-y-auto pr-1">
            {versions.map((ver) => (
              <div
                key={ver.id || ver.version}
                className="flex items-center justify-between p-3.5 rounded-lg border border-border-subtle bg-surface-subtle hover:border-border-default text-xs transition-colors"
              >
                <div>
                  <span className="font-bold font-mono text-accent-text">Version {ver.version}</span>
                  <span className="text-txt-muted ml-3">
                    {ver.pillars?.length || 0} {isEn ? 'pillars' : 'piliers'} • {ver.prohibited_topics?.length || 0} {isEn ? 'banned' : 'interdits'}
                  </span>
                </div>
                {canEdit && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleRestoreVersion(ver)}
                    className="text-xs font-medium"
                  >
                    <RotateCcw className="h-3.5 w-3.5 mr-1" />
                    {isEn ? 'Restore' : 'Restaurer'}
                  </Button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Main Form */}
      <form onSubmit={handleSave} className="space-y-6">
        {/* Voice and Tone */}
        <div className="rounded-xl border border-border-default bg-surface p-5 sm:p-6 space-y-3 shadow-subtle">
          <div className="flex items-center justify-between">
            <label className="block text-xs font-semibold text-txt-secondary">
              {t.brand.voice_label}
            </label>
            <span className="text-[11px] text-txt-muted">
              {isEn ? 'Injected into system prompts' : 'Injecté dans le prompt système'}
            </span>
          </div>
          <Textarea
            rows={3}
            value={voice}
            onChange={(e) => setVoice(e.target.value)}
            disabled={!canEdit}
            placeholder={
              isEn
                ? 'e.g., Expert, pragmatic, direct, grounded in architecture and case studies.'
                : 'Ex: Expert, pragmatique, direct, orienté retour d’expérience et architecture sans jargon creux.'
            }
            required
          />
        </div>

        {/* Editorial Pillars */}
        <div className="rounded-xl border border-border-default bg-surface p-5 sm:p-6 space-y-4 shadow-subtle">
          <div className="flex items-center justify-between">
            <label className="block text-xs font-semibold text-txt-secondary">
              {t.brand.pillars_label}
            </label>
            <span className="text-[11px] text-txt-muted font-mono">{pillars.length} {isEn ? 'active' : 'actif(s)'}</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {pillars.map((pil, idx) => (
              <span
                key={idx}
                className="inline-flex items-center gap-1.5 rounded-md bg-accent-subtle border border-accent-border px-3 py-1.5 text-xs text-accent-text font-medium"
              >
                <span>{pil}</span>
                {canEdit && (
                  <button
                    type="button"
                    onClick={() => setPillars(pillars.filter((_, i) => i !== idx))}
                    className="hover:text-status-danger-text focus:outline-none focus:ring-1 focus:ring-border-focus rounded p-0.5"
                    aria-label={`Supprimer le pilier ${pil}`}
                  >
                    <X className="h-3 w-3" />
                  </button>
                )}
              </span>
            ))}
          </div>

          {canEdit && (
            <div className="flex gap-2 max-w-md pt-1">
              <Input
                value={newPillar}
                onChange={(e) => setNewPillar(e.target.value)}
                placeholder={isEn ? 'Add a pillar topic...' : 'Ajouter un pilier thématique...'}
                className="text-xs"
              />
              <Button
                type="button"
                variant="primary"
                size="sm"
                aria-label="Ajouter ce pilier"
                className="min-h-[38px] px-3 shrink-0"
                onClick={() => {
                  if (newPillar.trim()) {
                    setPillars([...pillars, newPillar.trim()]);
                    setNewPillar('');
                  }
                }}
              >
                <Plus className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>

        {/* Prohibited Topics */}
        <div className="rounded-xl border border-border-default bg-surface p-5 sm:p-6 space-y-4 shadow-subtle">
          <div className="flex items-center justify-between">
            <label className="block text-xs font-semibold text-txt-secondary">
              {t.brand.prohibited_label}
            </label>
            <span className="text-[11px] text-status-danger-text font-mono">
              {prohibitedTopics.length} {isEn ? 'guardrail(s)' : 'garde-fou(s)'}
            </span>
          </div>
          <div className="flex flex-wrap gap-2">
            {prohibitedTopics.map((top, idx) => (
              <span
                key={idx}
                className="inline-flex items-center gap-1.5 rounded-md bg-status-danger-bg border border-status-danger-border px-3 py-1.5 text-xs text-status-danger-text font-medium"
              >
                <span>{top}</span>
                {canEdit && (
                  <button
                    type="button"
                    onClick={() => setProhibitedTopics(prohibitedTopics.filter((_, i) => i !== idx))}
                    className="hover:text-status-danger-text focus:outline-none focus:ring-1 focus:ring-border-focus rounded p-0.5"
                    aria-label={`Supprimer le sujet interdit ${top}`}
                  >
                    <X className="h-3 w-3" />
                  </button>
                )}
              </span>
            ))}
          </div>

          {canEdit && (
            <div className="flex gap-2 max-w-md pt-1">
              <Input
                value={newProhibited}
                onChange={(e) => setNewProhibited(e.target.value)}
                placeholder={isEn ? 'Add a prohibited keyword...' : 'Ajouter un sujet ou mot interdit...'}
                className="text-xs"
              />
              <Button
                type="button"
                variant="secondary"
                size="sm"
                aria-label="Ajouter ce sujet interdit"
                className="min-h-[38px] px-3 shrink-0"
                onClick={() => {
                  if (newProhibited.trim()) {
                    setProhibitedTopics([...prohibitedTopics, newProhibited.trim()]);
                    setNewProhibited('');
                  }
                }}
              >
                <Plus className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>

        {/* CTA Policy */}
        <div className="rounded-xl border border-border-default bg-surface p-5 sm:p-6 space-y-4 shadow-subtle">
          <div className="flex items-center justify-between">
            <label className="block text-xs font-semibold text-txt-secondary">
              {isEn ? 'Allowed Calls-to-Action (CTA Policy)' : 'Appels à l’action autorisés (CTA Policy)'}
            </label>
            <span className="text-[11px] text-txt-muted font-mono">{allowedCtas.length} {isEn ? 'allowed' : 'autorisés'}</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {allowedCtas.map((cta, idx) => (
              <span
                key={idx}
                className="inline-flex items-center gap-1.5 rounded-md bg-surface-subtle border border-border-subtle px-3 py-1.5 text-xs text-txt-primary font-mono"
              >
                <span>{cta}</span>
                {canEdit && (
                  <button
                    type="button"
                    onClick={() => setAllowedCtas(allowedCtas.filter((_, i) => i !== idx))}
                    className="hover:text-status-danger-text focus:outline-none focus:ring-1 focus:ring-border-focus rounded p-0.5"
                    aria-label={`Supprimer le CTA ${cta}`}
                  >
                    <X className="h-3 w-3" />
                  </button>
                )}
              </span>
            ))}
          </div>

          {canEdit && (
            <div className="flex gap-2 max-w-md pt-1">
              <Input
                value={newCta}
                onChange={(e) => setNewCta(e.target.value)}
                placeholder={isEn ? 'Add an approved CTA...' : 'Ajouter un CTA validé...'}
                className="text-xs"
              />
              <Button
                type="button"
                variant="primary"
                size="sm"
                aria-label="Ajouter ce CTA"
                className="min-h-[38px] px-3 shrink-0"
                onClick={() => {
                  if (newCta.trim()) {
                    setAllowedCtas([...allowedCtas, newCta.trim()]);
                    setNewCta('');
                  }
                }}
              >
                <Plus className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>
      </form>
    </div>
  );
};
