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
  const { t } = useLanguage();
  const { session, canEdit } = useAuth();

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
      setError(err.message || 'Impossible de récupérer le profil de marque.');
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
    if (!confirm(`Restaurer les paramètres de la version ${v.version} ?`)) return;
    setVoice(v.voice || '');
    setPillars(v.pillars || []);
    setProhibitedTopics(v.prohibited_topics || []);
    setAllowedCtas(v.cta_policy?.allowed_ctas || []);
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  if (error) {
    return <ErrorState message={error} onRetry={fetchProfileAndVersions} />;
  }

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-white tracking-tight">
              {t.brand.title}
            </h2>
            <Badge variant="info" className="text-xs">
              Version {currentVersion}
            </Badge>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Gouverne la voix, la conformité légale et les limites éditoriales de tous les agents.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setShowHistory(!showHistory)}
            className="flex items-center gap-1.5 text-xs"
          >
            <History className="h-4 w-4" />
            <span>{showHistory ? 'Masquer l’historique' : 'Historique des versions'}</span>
          </Button>

          {canEdit && (
            <Button
              variant="primary"
              size="sm"
              isLoading={saving}
              onClick={handleSave}
              className="flex items-center gap-1.5 text-xs"
            >
              <Save className="h-4 w-4" />
              <span>{t.brand.save_btn}</span>
            </Button>
          )}
        </div>
      </div>

      {saveSuccess && (
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-4 text-xs text-emerald-300 flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
          <span>Profil de marque mis à jour avec succès et nouvelle version incrémentée.</span>
        </div>
      )}

      {/* Version History Drawer / Panel */}
      {showHistory && (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-5 space-y-3">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Historique des versions enregistrées ({versions.length})
          </h3>
          <div className="space-y-2 max-h-60 overflow-y-auto">
            {versions.map((ver) => (
              <div
                key={ver.id || ver.version}
                className="flex items-center justify-between p-3 rounded-xl border border-slate-800 bg-slate-950/60 text-xs"
              >
                <div>
                  <span className="font-bold text-slate-200">Version {ver.version}</span>
                  <span className="text-slate-400 ml-3">
                    {ver.pillars?.length || 0} piliers • {ver.prohibited_topics?.length || 0} interdits
                  </span>
                </div>
                {canEdit && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleRestoreVersion(ver)}
                    className="text-cyan-400 hover:text-cyan-300 text-xs"
                  >
                    <RotateCcw className="h-3.5 w-3.5 mr-1" />
                    Restaurer
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
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 space-y-3">
          <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300">
            {t.brand.voice_label}
          </label>
          <Textarea
            rows={3}
            value={voice}
            onChange={(e) => setVoice(e.target.value)}
            disabled={!canEdit}
            placeholder="Ex: Expert, pragmatique, direct, orienté retour d'expérience et architecture sans jargon creux."
            required
          />
        </div>

        {/* Editorial Pillars */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 space-y-4">
          <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300">
            {t.brand.pillars_label}
          </label>
          <div className="flex flex-wrap gap-2">
            {pillars.map((pil, idx) => (
              <span
                key={idx}
                className="inline-flex items-center gap-1.5 rounded-lg bg-cyan-950/60 border border-cyan-500/30 px-3 py-1.5 text-xs text-cyan-300"
              >
                <span>{pil}</span>
                {canEdit && (
                  <button
                    type="button"
                    onClick={() => setPillars(pillars.filter((_, i) => i !== idx))}
                    className="hover:text-red-400 focus:outline-none focus:ring-1 focus:ring-red-400 rounded"
                    aria-label={`Supprimer le pilier ${pil}`}
                  >
                    <X className="h-3 w-3" />
                  </button>
                )}
              </span>
            ))}
          </div>

          {canEdit && (
            <div className="flex gap-2 max-w-md">
              <Input
                value={newPillar}
                onChange={(e) => setNewPillar(e.target.value)}
                placeholder="Ajouter un pilier thématique..."
                className="text-xs"
              />
              <Button
                type="button"
                variant="secondary"
                size="sm"
                aria-label="Ajouter ce pilier"
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
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 space-y-4">
          <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300">
            {t.brand.prohibited_label}
          </label>
          <div className="flex flex-wrap gap-2">
            {prohibitedTopics.map((top, idx) => (
              <span
                key={idx}
                className="inline-flex items-center gap-1.5 rounded-lg bg-red-950/40 border border-red-500/30 px-3 py-1.5 text-xs text-red-300"
              >
                <span>{top}</span>
                {canEdit && (
                  <button
                    type="button"
                    onClick={() => setProhibitedTopics(prohibitedTopics.filter((_, i) => i !== idx))}
                    className="hover:text-white focus:outline-none focus:ring-1 focus:ring-white rounded"
                    aria-label={`Supprimer le sujet interdit ${top}`}
                  >
                    <X className="h-3 w-3" />
                  </button>
                )}
              </span>
            ))}
          </div>

          {canEdit && (
            <div className="flex gap-2 max-w-md">
              <Input
                value={newProhibited}
                onChange={(e) => setNewProhibited(e.target.value)}
                placeholder="Ajouter un sujet ou mot interdit..."
                className="text-xs"
              />
              <Button
                type="button"
                variant="secondary"
                size="sm"
                aria-label="Ajouter ce sujet interdit"
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
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 space-y-4">
          <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300">
            Appels à l'action autorisés (CTA Policy)
          </label>
          <div className="flex flex-wrap gap-2">
            {allowedCtas.map((cta, idx) => (
              <span
                key={idx}
                className="inline-flex items-center gap-1.5 rounded-lg bg-slate-800 border border-slate-700 px-3 py-1.5 text-xs text-slate-200"
              >
                <span>{cta}</span>
                {canEdit && (
                  <button
                    type="button"
                    onClick={() => setAllowedCtas(allowedCtas.filter((_, i) => i !== idx))}
                    className="hover:text-red-400 focus:outline-none focus:ring-1 focus:ring-red-400 rounded"
                    aria-label={`Supprimer le CTA ${cta}`}
                  >
                    <X className="h-3 w-3" />
                  </button>
                )}
              </span>
            ))}
          </div>

          {canEdit && (
            <div className="flex gap-2 max-w-md">
              <Input
                value={newCta}
                onChange={(e) => setNewCta(e.target.value)}
                placeholder="Ajouter un CTA validé..."
                className="text-xs"
              />
              <Button
                type="button"
                variant="secondary"
                size="sm"
                aria-label="Ajouter ce CTA"
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
