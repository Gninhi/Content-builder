import React, { useState, useEffect, useMemo } from 'react';
import { useLanguage } from '../context/LanguageContext';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { apiClient } from '../lib/api';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { Dialog } from '../components/common/Dialog';
import { Input } from '../components/common/Input';
import { Skeleton } from '../components/common/Skeleton';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorState } from '../components/common/ErrorState';
import { VeilleSignal, VeilleSource, VeilleAxis, TrustLevel } from '../types/api';
import {
  Radar,
  RefreshCw,
  Plus,
  ExternalLink,
  Sparkles,
  ShieldCheck,
  CheckCircle2,
  SlidersHorizontal,
  Search,
  Filter,
  Layers,
  Database,
  TrendingUp,
  X,
  Zap,
} from 'lucide-react';

interface VeilleScreenProps {
  onNavigate?: (screen: string) => void;
}

export const VeilleScreen: React.FC<VeilleScreenProps> = ({ onNavigate }) => {
  const { language } = useLanguage();
  const { session, canEdit, isOwner } = useAuth();
  const { showToast } = useToast();
  const isEn = language === 'en';

  // Data states
  const [signals, setSignals] = useState<VeilleSignal[]>([]);
  const [sources, setSources] = useState<VeilleSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [collecting, setCollecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [selectedAxis, setSelectedAxis] = useState<string>('all');
  const [selectedTrust, setSelectedTrust] = useState<string>('all');
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isDemoMode, setIsDemoMode] = useState<boolean>(true);

  // Source Modal state
  const [sourcesModalOpen, setSourcesModalOpen] = useState(false);
  const [newSourceName, setNewSourceName] = useState('');
  const [newSourceUrl, setNewSourceUrl] = useState('');
  const [newSourceAxis, setNewSourceAxis] = useState<VeilleAxis>('ia');
  const [newSourceTrust, setNewSourceTrust] = useState<TrustLevel>('A');
  const [newSourceType, setNewSourceType] = useState('web');
  const [submittingSource, setSubmittingSource] = useState(false);
  const [seedingSources, setSeedingSources] = useState(false);

  // Converting state
  const [convertingSignalId, setConvertingSignalId] = useState<string | null>(null);

  // 1. Fetch Signals & Sources
  const fetchSignals = async () => {
    try {
      setLoading(true);
      setError(null);
      const params = new URLSearchParams();
      if (selectedAxis !== 'all') params.append('axis', selectedAxis);
      if (selectedTrust !== 'all') params.append('trust_level', selectedTrust);
      if (selectedStatus !== 'all') params.append('status', selectedStatus);

      const qs = params.toString() ? `?${params.toString()}` : '';
      const data = await apiClient<VeilleSignal[]>(`/v1/signals${qs}`);
      setSignals(Array.isArray(data) ? data : []);
    } catch (err: any) {
      setError(err.message || (isEn ? 'Failed to load monitoring signals.' : 'Impossible de charger les signaux de veille.'));
    } finally {
      setLoading(false);
    }
  };

  const fetchSources = async () => {
    try {
      const data = await apiClient<VeilleSource[]>('/v1/signals/sources');
      setSources(Array.isArray(data) ? data : []);
    } catch (err) {
      // Non-blocking for general view
    }
  };

  useEffect(() => {
    fetchSignals();
    fetchSources();
  }, [selectedAxis, selectedTrust, selectedStatus, session?.workspace_id]);

  // 2. Trigger Collection Cycle
  const handleCollectSignals = async () => {
    try {
      setCollecting(true);
      const payload = {
        axis: selectedAxis === 'all' ? null : selectedAxis,
        demo: isDemoMode,
        limit_per_axis: 3,
      };

      const collected = await apiClient<VeilleSignal[]>('/v1/signals/collect', {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      showToast(
        'success',
        isEn
          ? `Collected and qualified ${collected?.length || 0} monitoring signals.`
          : `${collected?.length || 0} signaux de veille collectés et qualifiés.`
      );
      fetchSignals();
    } catch (err: any) {
      showToast('error', `Erreur de collecte : ${err.message}`);
    } finally {
      setCollecting(false);
    }
  };

  // 3. Convert Signal to Ideation
  const handleConvertToIdea = async (signal: VeilleSignal) => {
    if (convertingSignalId) return; // Prevent double trigger
    try {
      setConvertingSignalId(signal.id);

      // Call dedicated transactional conversion endpoint
      await apiClient<any>(`/v1/signals/${signal.id}/convert`, {
        method: 'POST',
      });

      // Update signal status locally to CONVERTED
      setSignals((prev) =>
        prev.map((s) => (s.id === signal.id ? { ...s, status: 'CONVERTED' } : s))
      );

      showToast(
        'success',
        isEn
          ? 'Signal converted to verified editorial idea! Navigating to Ideation...'
          : 'Signal transformé en angle éditorial ancré ! Redirection vers Idéation...'
      );

      if (onNavigate) {
        onNavigate('ideation');
      } else {
        window.location.hash = '#ideation';
      }
    } catch (err: any) {
      showToast('error', `Erreur de conversion : ${err.message}`);
    } finally {
      setConvertingSignalId(null);
    }
  };

  // 4. Update Signal Status
  const handleUpdateStatus = async (signalId: string, newStatus: string) => {
    try {
      await apiClient<any>(`/v1/signals/${signalId}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ status: newStatus }),
      });
      setSignals((prev) =>
        prev.map((s) => (s.id === signalId ? { ...s, status: newStatus } : s))
      );
      showToast('info', `Statut mis à jour : ${newStatus}`);
    } catch (err: any) {
      showToast('error', `Erreur : ${err.message}`);
    }
  };

  // 5. Source Management Actions
  const handleAddSource = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newSourceName.trim() || !newSourceUrl.trim()) return;

    try {
      setSubmittingSource(true);
      const created = await apiClient<VeilleSource>('/v1/signals/sources', {
        method: 'POST',
        body: JSON.stringify({
          name: newSourceName.trim(),
          url: newSourceUrl.trim(),
          axis: newSourceAxis,
          trust_level: newSourceTrust,
          source_type: newSourceType,
        }),
      });
      setSources((prev) => [created, ...prev]);
      setNewSourceName('');
      setNewSourceUrl('');
      showToast('success', isEn ? 'Monitoring source added.' : 'Source de veille ajoutée avec succès.');
    } catch (err: any) {
      showToast('error', `Erreur d'ajout de source : ${err.message}`);
    } finally {
      setSubmittingSource(false);
    }
  };

  const handleSeedSources = async () => {
    try {
      setSeedingSources(true);
      const seeded = await apiClient<VeilleSource[]>('/v1/signals/sources/seed', {
        method: 'POST',
      });
      setSources(Array.isArray(seeded) ? seeded : []);
      showToast('success', isEn ? 'Curated source catalogue seeded!' : 'Catalogue officiel de sources injecté avec succès !');
    } catch (err: any) {
      showToast('error', `Erreur d'injection du catalogue : ${err.message}`);
    } finally {
      setSeedingSources(false);
    }
  };

  // Filter signals locally by search query
  const filteredSignals = useMemo(() => {
    if (!searchQuery.trim()) return signals;
    const q = searchQuery.toLowerCase();
    return signals.filter(
      (s) =>
        s.title.toLowerCase().includes(q) ||
        s.summary.toLowerCase().includes(q) ||
        (s.executive_takeaway && s.executive_takeaway.toLowerCase().includes(q))
    );
  }, [signals, searchQuery]);

  const getAxisBadgeProps = (axis: string) => {
    switch (axis) {
      case 'ia':
        return { label: 'IA & Agents', variant: 'accent' as const, color: 'text-purple-400 bg-purple-500/10 border-purple-500/20' };
      case 'frameworks':
        return { label: 'Frameworks & Outils', variant: 'info' as const, color: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/20' };
      case 'metiers':
        return { label: 'Évolution des Métiers', variant: 'success' as const, color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20' };
      default:
        return { label: axis, variant: 'neutral' as const, color: 'text-txt-muted bg-surface border-border-default' };
    }
  };

  const getTrustBadge = (trust: string) => {
    switch (trust) {
      case 'A':
        return <Badge variant="success" className="text-[10px] font-mono">Niveau A (Primaire)</Badge>;
      case 'B':
        return <Badge variant="info" className="text-[10px] font-mono">Niveau B (Analyste)</Badge>;
      case 'C':
        return <Badge variant="warning" className="text-[10px] font-mono">Niveau C (Communauté)</Badge>;
      default:
        return <Badge variant="neutral" className="text-[10px] font-mono">{trust}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border-subtle pb-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-accent/10 text-accent border border-accent/20">
              <Radar className="h-5 w-5" />
            </div>
            <h1 className="text-xl sm:text-2xl font-bold text-txt-primary tracking-tight">
              {isEn ? 'Tech Monitoring & Signals' : 'Veille Technologique & Signaux'}
            </h1>
          </div>
          <p className="text-xs text-txt-muted mt-1">
            {isEn
              ? 'Multi-axis continuous radar grounded in primary sources, powering verified ideation.'
              : 'Radar continu multi-axes fondé sur des sources primaires, alimentant une idéation strictement ancrée.'}
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {/* Demo toggle */}
          <button
            onClick={() => setIsDemoMode(!isDemoMode)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-mono transition-colors ${
              isDemoMode
                ? 'bg-amber-500/10 border-amber-500/30 text-amber-300'
                : 'bg-surface border-border-default text-txt-muted hover:text-txt-primary'
            }`}
            title="Bascule entre le mode démo vérifié (rapide) et la collecte web réelle"
          >
            <Zap className="h-3.5 w-3.5" />
            <span>Mode Démo : {isDemoMode ? 'ON' : 'OFF'}</span>
          </button>

          {/* Sources manager button */}
          <Button
            variant="outline"
            size="sm"
            onClick={() => setSourcesModalOpen(true)}
            className="flex items-center gap-1.5 text-xs min-h-[38px]"
          >
            <Database className="h-3.5 w-3.5" />
            <span>{isEn ? 'Sources' : 'Sources'} ({sources.length})</span>
          </Button>

          {/* Trigger collection */}
          {canEdit && (
            <Button
              variant="primary"
              size="sm"
              disabled={collecting}
              isLoading={collecting}
              onClick={handleCollectSignals}
              className="flex items-center gap-1.5 text-xs min-h-[38px]"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${collecting ? 'animate-spin' : ''}`} />
              <span>{isEn ? 'Collect Signals' : 'Collecter les Signaux'}</span>
            </Button>
          )}
        </div>
      </div>

      {/* Axis Navigation Tabs */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 border-b border-border-default text-xs">
        {[
          { id: 'all', label: isEn ? 'All Axes' : 'Tous les axes', icon: Layers },
          { id: 'ia', label: 'IA & Agents', icon: Sparkles },
          { id: 'frameworks', label: 'Frameworks & Outils', icon: SlidersHorizontal },
          { id: 'metiers', label: 'Évolution des Métiers', icon: TrendingUp },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = selectedAxis === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setSelectedAxis(tab.id)}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-lg font-medium transition-all shrink-0 ${
                isActive
                  ? 'bg-accent text-accent-foreground shadow-subtle'
                  : 'text-txt-secondary hover:text-txt-primary hover:bg-surface'
              }`}
            >
              <Icon className="h-4 w-4" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col md:flex-row items-center justify-between gap-3 bg-surface border border-border-default rounded-xl p-3">
        <div className="relative w-full md:w-72">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-txt-muted" />
          <input
            type="text"
            placeholder={isEn ? 'Search signals, facts...' : 'Filtrer les signaux, faits...'}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs bg-app border border-border-default rounded-lg text-txt-primary placeholder:text-txt-muted focus:outline-none focus:border-accent"
          />
        </div>

        <div className="flex items-center gap-2 w-full md:w-auto overflow-x-auto">
          {/* Trust filter */}
          <div className="flex items-center gap-1.5 text-xs text-txt-muted shrink-0">
            <ShieldCheck className="h-3.5 w-3.5" />
            <span>Confiance :</span>
            <select
              value={selectedTrust}
              onChange={(e) => setSelectedTrust(e.target.value)}
              className="bg-app border border-border-default rounded-md px-2 py-1 text-xs text-txt-primary focus:outline-none"
            >
              <option value="all">Tous</option>
              <option value="A">Niveau A</option>
              <option value="B">Niveau B</option>
              <option value="C">Niveau C</option>
            </select>
          </div>

          {/* Status filter */}
          <div className="flex items-center gap-1.5 text-xs text-txt-muted shrink-0 ml-2">
            <Filter className="h-3.5 w-3.5" />
            <span>Statut :</span>
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="bg-app border border-border-default rounded-md px-2 py-1 text-xs text-txt-primary focus:outline-none"
            >
              <option value="all">Tous</option>
              <option value="NEW">Nouveau</option>
              <option value="QUALIFIED">Qualifié</option>
              <option value="CONVERTED">Converti en idée</option>
              <option value="REJECTED">Rejeté</option>
            </select>
          </div>
        </div>
      </div>

      {/* Main Content State */}
      {loading && signals.length === 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          <Skeleton className="h-72 w-full rounded-xl" />
          <Skeleton className="h-72 w-full rounded-xl" />
          <Skeleton className="h-72 w-full rounded-xl" />
        </div>
      ) : error && signals.length === 0 ? (
        <ErrorState message={error} onRetry={fetchSignals} />
      ) : filteredSignals.length === 0 ? (
        <EmptyState
          title={isEn ? 'No monitoring signals yet' : 'Aucun signal de veille pour ce filtre'}
          description={
            isEn
              ? 'Trigger an ingestion cycle to capture and qualify fresh primary signals across your target axes.'
              : 'Lancez un cycle de collecte pour capturer et qualifier des signaux récents sur vos axes stratégiques.'
          }
          actionLabel={isEn ? 'Collect Signals' : 'Collecter les Signaux'}
          onAction={handleCollectSignals}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredSignals.map((signal) => {
            const axisProps = getAxisBadgeProps(signal.axis);
            const isConverting = convertingSignalId === signal.id;
            const scoreOutOf100 = Math.round(signal.qualification_score * 20); // 0-5.0 scale to 0-100%

            return (
              <div
                key={signal.id}
                className="flex flex-col justify-between rounded-xl border border-border-default bg-surface p-5 hover:border-border-hover transition-all shadow-subtle"
              >
                <div>
                  {/* Card Header */}
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <span className={`text-[11px] font-semibold px-2 py-0.5 rounded border ${axisProps.color}`}>
                      {axisProps.label}
                    </span>
                    <div className="flex items-center gap-1.5">
                      {getTrustBadge(signal.trust_level)}
                      <span
                        className="text-[11px] font-mono font-bold text-accent px-1.5 py-0.5 bg-accent/10 rounded cursor-help"
                        title={
                          isEn
                            ? `Editorial qualification score: ${signal.qualification_score.toFixed(1)}/5.0 (Authority, Freshness, Fact Density. Editorial index, not guarantee of truth)`
                            : `Score de qualification éditoriale : ${signal.qualification_score.toFixed(1)}/5.0 (Autorité, Fraîcheur, Richesse factuelle. Indice éditorial, non garantie de vérité)`
                        }
                      >
                        {scoreOutOf100}/100
                      </span>
                    </div>
                  </div>

                  {/* Source domain & date metadata */}
                  <div className="flex items-center gap-2 text-[11px] text-txt-muted mb-2.5">
                    {signal.canonical_url && (
                      <span className="font-mono text-txt-secondary truncate max-w-[150px]">
                        {(() => {
                          try {
                            return new URL(signal.canonical_url).hostname.replace('www.', '');
                          } catch {
                            return 'source';
                          }
                        })()}
                      </span>
                    )}
                    {signal.created_at && (
                      <>
                        <span>•</span>
                        <span>
                          {new Date(signal.created_at).toLocaleDateString(isEn ? 'en-US' : 'fr-FR', {
                            day: 'numeric',
                            month: 'short',
                            year: 'numeric',
                          })}
                        </span>
                      </>
                    )}
                    {signal.is_synthetic && (
                      <span className="text-[10px] bg-status-warning-bg text-status-warning-text px-1 rounded border border-status-warning-border">
                        {isEn ? 'Demo' : 'Démo'}
                      </span>
                    )}
                  </div>

                  {/* Title */}
                  <h3 className="text-sm font-semibold text-txt-primary leading-snug mb-2 group flex items-start justify-between gap-2">
                    <span>{signal.title}</span>
                    {signal.canonical_url && (
                      <a
                        href={signal.canonical_url}
                        target="_blank"
                        rel="noreferrer noopener"
                        className="text-txt-muted hover:text-accent shrink-0 pt-0.5"
                        title="Consulter la source primaire"
                      >
                        <ExternalLink className="h-3.5 w-3.5" />
                      </a>
                    )}
                  </h3>

                  {/* Summary */}
                  <p className="text-xs text-txt-secondary mb-3 leading-relaxed line-clamp-3">
                    {signal.summary}
                  </p>

                  {/* Executive takeaway */}
                  {signal.executive_takeaway && (
                    <div className="mb-3.5 rounded-lg border border-accent/20 bg-accent/5 p-3 text-xs">
                      <div className="flex items-center gap-1.5 text-accent font-semibold text-[11px] mb-1">
                        <TrendingUp className="h-3.5 w-3.5" />
                        <span>Pourquoi ça compte pour un décideur</span>
                      </div>
                      <p className="text-txt-primary text-[11px] leading-relaxed">
                        {signal.executive_takeaway}
                      </p>
                    </div>
                  )}

                  {/* Facts list with source links */}
                  {signal.facts && signal.facts.length > 0 ? (
                    <div className="space-y-1.5 py-2.5 border-t border-border-subtle">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[10px] font-mono text-txt-muted uppercase tracking-wider">
                          Faits vérifiés ({signal.facts.length})
                        </span>
                        <span className="text-[10px] text-status-success-text font-medium">
                          {signal.facts.filter((f) => f.verified !== false).length}/{signal.facts.length} corroborés
                        </span>
                      </div>
                      {signal.facts.slice(0, 2).map((fact, i) => (
                        <div key={i} className="flex items-start gap-1.5 text-[11px] text-txt-secondary bg-app/30 p-2 rounded border border-border-subtle">
                          <CheckCircle2 className="h-3 w-3 text-status-success-text shrink-0 mt-0.5" />
                          <div className="flex-1 min-w-0">
                            <span className="line-clamp-2">{fact.claim}</span>
                            {fact.source_id && (
                              <a
                                href={fact.source_id.startsWith('http') ? fact.source_id : (signal.canonical_url || '#')}
                                target="_blank"
                                rel="noreferrer noopener"
                                className="inline-flex items-center gap-1 text-[10px] text-accent hover:underline mt-0.5 font-mono"
                              >
                                <span>Preuve source</span>
                                <ExternalLink className="h-2.5 w-2.5" />
                              </a>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="py-2 border-t border-border-subtle text-[11px] text-txt-muted italic">
                      Aucun fait primaire extrait pour ce signal
                    </div>
                  )}
                </div>

                {/* Footer Actions */}
                <div className="pt-4 border-t border-border-subtle mt-2 flex items-center justify-between gap-2">
                  <div className="flex items-center gap-1">
                    <Badge
                      variant={
                        signal.status === 'CONVERTED'
                          ? 'success'
                          : signal.status === 'QUALIFIED'
                          ? 'accent'
                          : signal.status === 'REJECTED'
                          ? 'danger'
                          : 'neutral'
                      }
                      className="text-[10px]"
                    >
                      {signal.status}
                    </Badge>
                  </div>

                  <div className="flex items-center gap-1.5">
                    {signal.status !== 'CONVERTED' && signal.status !== 'REJECTED' && canEdit && (
                      <button
                        onClick={() => handleUpdateStatus(signal.id, 'REJECTED')}
                        className="p-1.5 text-txt-muted hover:text-status-danger-text rounded hover:bg-app"
                        title="Rejeter ce signal"
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    )}

                    {canEdit && (
                      <Button
                        variant={signal.status === 'CONVERTED' ? 'outline' : 'primary'}
                        size="sm"
                        disabled={isConverting}
                        isLoading={isConverting}
                        onClick={() => handleConvertToIdea(signal)}
                        className="text-xs min-h-[36px]"
                      >
                        <Sparkles className="h-3.5 w-3.5 mr-1" />
                        <span>{signal.status === 'CONVERTED' ? 'Générer un autre angle' : 'Transformer en Idée'}</span>
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Source Management Modal */}
      <Dialog
        isOpen={sourcesModalOpen}
        onClose={() => setSourcesModalOpen(false)}
        title={isEn ? 'Monitoring Sources Governance' : 'Gouvernance des Sources de Veille'}
      >
        <div className="space-y-6">
          <p className="text-xs text-txt-muted">
            {isEn
              ? 'Manage official monitoring sources per strategic axis with trust level classifications (A = Primary, B = Analyst/Secondary, C = Community).'
              : 'Gérez les sources de veille officielles par axe stratégique avec classification de confiance (A = Primaire, B = Analyste/Secondaire, C = Communauté).'}
          </p>

          {/* Quick seed curated catalog button (Owner only) */}
          {isOwner && (
            <div className="flex items-center justify-between p-3 rounded-lg border border-accent/20 bg-accent/5">
              <div>
                <strong className="block text-xs font-semibold text-txt-primary">
                  {isEn ? 'Standard Curated Catalog' : 'Catalogue de Référence Curé'}
                </strong>
                <span className="text-[11px] text-txt-muted">
                  Injecte les flux officiels validés (Commission EU, HuggingFace, GitHub Trending, Inria...).
                </span>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={handleSeedSources}
                isLoading={seedingSources}
                className="text-xs shrink-0"
              >
                <Database className="h-3.5 w-3.5 mr-1" />
                <span>Injecter le catalogue</span>
              </Button>
            </div>
          )}

          {/* Add source form (Owner only) */}
          {isOwner && (
            <form onSubmit={handleAddSource} className="space-y-3 p-3.5 rounded-lg border border-border-default bg-surface">
              <h4 className="text-xs font-semibold text-txt-primary">Ajouter une nouvelle source</h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <Input
                  label="Nom de la source"
                  value={newSourceName}
                  onChange={(e) => setNewSourceName(e.target.value)}
                  placeholder="ex: ArXiv AI RSS"
                  required
                />
                <Input
                  label="URL du flux / site"
                  value={newSourceUrl}
                  onChange={(e) => setNewSourceUrl(e.target.value)}
                  placeholder="https://..."
                  required
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-[11px] font-medium text-txt-muted mb-1">Axe</label>
                  <select
                    value={newSourceAxis}
                    onChange={(e) => setNewSourceAxis(e.target.value as VeilleAxis)}
                    className="w-full bg-app border border-border-default rounded-md px-2.5 py-1.5 text-xs text-txt-primary"
                  >
                    <option value="ia">IA & Agents</option>
                    <option value="frameworks">Frameworks & Outils</option>
                    <option value="metiers">Évolution des Métiers</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-medium text-txt-muted mb-1">Niveau Confiance</label>
                  <select
                    value={newSourceTrust}
                    onChange={(e) => setNewSourceTrust(e.target.value as TrustLevel)}
                    className="w-full bg-app border border-border-default rounded-md px-2.5 py-1.5 text-xs text-txt-primary"
                  >
                    <option value="A">Niveau A (Primaire)</option>
                    <option value="B">Niveau B (Secondaire)</option>
                    <option value="C">Niveau C (Communauté)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-medium text-txt-muted mb-1">Type</label>
                  <select
                    value={newSourceType}
                    onChange={(e) => setNewSourceType(e.target.value)}
                    className="w-full bg-app border border-border-default rounded-md px-2.5 py-1.5 text-xs text-txt-primary"
                  >
                    <option value="web">Web</option>
                    <option value="rss">Flux RSS</option>
                    <option value="arxiv">ArXiv</option>
                    <option value="github">GitHub</option>
                    <option value="hackernews">Hacker News</option>
                  </select>
                </div>
              </div>

              <div className="flex justify-end pt-2">
                <Button variant="primary" size="sm" type="submit" isLoading={submittingSource} className="text-xs">
                  <Plus className="h-3.5 w-3.5 mr-1" />
                  <span>Enregistrer la source</span>
                </Button>
              </div>
            </form>
          )}

          {/* Sources list */}
          <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
            <h4 className="text-xs font-semibold text-txt-primary">Sources Actives ({sources.length})</h4>
            {sources.length === 0 ? (
              <p className="text-xs text-txt-muted py-4 text-center">Aucune source configurée.</p>
            ) : (
              sources.map((src) => (
                <div
                  key={src.id}
                  className="flex items-center justify-between p-2.5 rounded-lg border border-border-subtle bg-app text-xs"
                >
                  <div className="truncate pr-2">
                    <strong className="block text-txt-primary truncate">{src.name}</strong>
                    <span className="text-[10px] text-txt-muted truncate">{src.url}</span>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <Badge variant="neutral" className="text-[10px] uppercase">{src.axis}</Badge>
                    <Badge variant={src.trust_level === 'A' ? 'success' : 'info'} className="text-[10px]">
                      {src.trust_level}
                    </Badge>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </Dialog>
    </div>
  );
};
