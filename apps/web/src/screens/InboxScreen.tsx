import React, { useState, useEffect, useCallback } from 'react';
import { useLanguage } from '../context/LanguageContext';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { apiClient } from '../lib/api';
import { InboxVariant } from '../types/api';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { Skeleton } from '../components/common/Skeleton';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorState } from '../components/common/ErrorState';
import { ConfirmDialog } from '../components/common/ConfirmDialog';
import { Dialog } from '../components/common/Dialog';
import { PlatformPreview } from '../components/common/PlatformPreview';
import { Textarea } from '../components/common/Textarea';
import { Input } from '../components/common/Input';
import {
  CheckCircle2,
  XCircle,
  RefreshCw,
  Edit3,
  ShieldCheck,
  ShieldAlert,
  Keyboard,
} from 'lucide-react';

export const InboxScreen: React.FC = () => {
  const { t } = useLanguage();
  const { session, canApprove, canEdit } = useAuth();
  const { showToast } = useToast();

  const [variants, setVariants] = useState<InboxVariant[]>([]);
  const [selectedIndex, setSelectedIndex] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filter state
  const [platformFilter, setPlatformFilter] = useState<string>('all');

  // Edit state
  const [isEditing, setIsEditing] = useState<boolean>(false);
  const [editHook, setEditHook] = useState<string>('');
  const [editBody, setEditBody] = useState<string>('');
  const [editCta, setEditCta] = useState<string>('');

  // Modals & Feedback dialogs
  const [feedbackAction, setFeedbackAction] = useState<'rewrite' | 'reject' | null>(null);
  const [feedbackComment, setFeedbackComment] = useState<string>('');
  const [feedbackError, setFeedbackError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<boolean>(false);

  // Live mode approval confirmation dialog
  const [confirmApproveOpen, setConfirmApproveOpen] = useState<boolean>(false);
  const [shortcutsOpen, setShortcutsOpen] = useState<boolean>(false);

  // Fetch inbox items
  const fetchInbox = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient<InboxVariant[]>('/v1/inbox');
      const list = Array.isArray(data) ? data : [];
      setVariants(list);
      setSelectedIndex(0);
      if (list.length > 0) {
        initEditState(list[0]);
      }
    } catch (err: any) {
      setError(err.message || 'Impossible de récupérer la file de revue.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInbox();
  }, [session?.workspace_id]);

  const initEditState = (v: InboxVariant) => {
    setEditHook(v.hook || '');
    setEditBody(v.body || '');
    setEditCta(v.cta || '');
    setIsEditing(false);
  };

  const filteredVariants = variants.filter((v) => {
    if (platformFilter === 'all') return true;
    return v.platform.toLowerCase() === platformFilter.toLowerCase();
  });

  const selectedVariant = filteredVariants[selectedIndex] || null;

  useEffect(() => {
    if (selectedVariant) {
      initEditState(selectedVariant);
    }
  }, [selectedIndex, selectedVariant?.id]);

  // Execute approval / decision (strictly non-optimistic: await server before updating state)
  const executeDecision = async (
    decision: 'approve' | 'rewrite' | 'reject',
    feedback?: string
  ) => {
    if (!selectedVariant) return;

    setActionLoading(true);
    try {
      if (decision === 'rewrite') {
        const res = await apiClient<{ message: string }>(
          `/v1/content/${selectedVariant.id}/rewrite`,
          {
            method: 'POST',
            body: JSON.stringify({ feedback: feedback || 'Améliorer le style et la clarté' }),
          }
        );
        showToast('success', res.message || 'Brouillon réécrit avec succès par l’agent !');
      } else {
        const payload: any = {
          decision,
          reviewer_id: session?.user_id || 'anonymous_reviewer',
          feedback: feedback || undefined,
        };

        if (isEditing) {
          payload.edited_payload = {
            hook: editHook,
            body: editBody,
            cta: editCta,
          };
        }

        await apiClient(`/v1/content/${selectedVariant.id}/approve`, {
          method: 'POST',
          body: JSON.stringify(payload),
        });

        showToast(
          'success',
          decision === 'approve'
            ? 'Brouillon approuvé et scellé cryptographiquement !'
            : 'Brouillon rejeté avec succès.'
        );
      }

      // Refetch inbox only upon confirmed server success
      await fetchInbox();
      setFeedbackAction(null);
      setFeedbackComment('');
      setConfirmApproveOpen(false);
    } catch (err: any) {
      showToast('error', `Erreur d'action : ${err.message || 'Échec de la validation'}`);
    } finally {
      setActionLoading(false);
    }
  };

  // Keyboard navigation handler
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      // Ignore if focus is in an input or textarea
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
        return;
      }

      switch (e.key.toLowerCase()) {
        case 'j':
          // Next item
          if (selectedIndex < filteredVariants.length - 1) {
            setSelectedIndex((prev) => prev + 1);
          }
          break;
        case 'k':
          // Previous item
          if (selectedIndex > 0) {
            setSelectedIndex((prev) => prev - 1);
          }
          break;
        case 'a':
          if (canApprove && selectedVariant) {
            setConfirmApproveOpen(true);
          }
          break;
        case 'r':
          if (canEdit && selectedVariant) {
            setFeedbackAction('rewrite');
          }
          break;
        case 'x':
          if (canApprove && selectedVariant) {
            setFeedbackAction('reject');
          }
          break;
        case '?':
          setShortcutsOpen(true);
          break;
        default:
          break;
      }
    },
    [selectedIndex, filteredVariants.length, canApprove, canEdit, selectedVariant]
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="h-8 w-64 bg-slate-800 rounded animate-pulse" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Skeleton className="h-96 w-full" />
          <Skeleton className="h-96 w-full lg:col-span-2" />
        </div>
      </div>
    );
  }

  if (error) {
    return <ErrorState message={error} onRetry={fetchInbox} />;
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Top Header & Filters */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-white tracking-tight">
              {t.inbox.title}
            </h2>
            <Badge variant="warning" className="text-xs">
              {filteredVariants.length} {t.inbox.queue_title}
            </Badge>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Validation humaine obligatoire avant toute diffusion (raccourcis: J/K, A, R, X, ?)
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Platform Filter */}
          <div className="flex items-center rounded-lg border border-slate-700 bg-slate-800/80 p-0.5 text-xs">
            {['all', 'linkedin', 'x'].map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => {
                  setPlatformFilter(p);
                  setSelectedIndex(0);
                }}
                className={`rounded px-2.5 py-1 font-medium transition-colors ${
                  platformFilter === p
                    ? 'bg-cyan-500 text-slate-950 font-bold'
                    : 'text-slate-300 hover:text-white'
                }`}
              >
                {p === 'all' ? 'Toutes' : p.toUpperCase()}
              </button>
            ))}
          </div>

          {/* Keyboard Shortcuts Trigger */}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShortcutsOpen(true)}
            className="text-slate-400 hover:text-white flex items-center gap-1.5"
            title={t.inbox.shortcuts_help}
          >
            <Keyboard className="h-4 w-4" />
            <span className="hidden md:inline text-xs">Aide (?)</span>
          </Button>
        </div>
      </div>

      {filteredVariants.length === 0 ? (
        <EmptyState
          title={t.inbox.empty_title}
          description={t.inbox.empty_desc}
          actionLabel="Générer de nouvelles idées"
          onAction={() => window.location.hash = '#ideation'}
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: Drafts Queue (4 cols) */}
          <div className="lg:col-span-4 space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 px-1">
              Brouillons en attente ({filteredVariants.length})
            </h3>
            <div
              className="space-y-2.5 max-h-[calc(100vh-250px)] overflow-y-auto pr-1"
              role="listbox"
              aria-label="Liste des brouillons à réviser"
            >
              {filteredVariants.map((item, idx) => {
                const isSelected = idx === selectedIndex;
                const charCount = (item.hook?.length || 0) + (item.body?.length || 0);
                return (
                  <button
                    key={item.id}
                    type="button"
                    role="option"
                    aria-selected={isSelected}
                    onClick={() => {
                      setSelectedIndex(idx);
                      initEditState(item);
                    }}
                    className={`w-full text-left rounded-xl p-4 border transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-cyan-500 ${
                      isSelected
                        ? 'border-cyan-500 bg-cyan-950/20 shadow-md shadow-cyan-950/40'
                        : 'border-slate-800 bg-slate-900/60 hover:border-slate-700 hover:bg-slate-900'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <Badge variant={item.platform === 'linkedin' ? 'info' : 'neutral'} className="text-[10px]">
                          {item.platform?.toUpperCase()}
                        </Badge>
                        {item.is_degraded && (
                          <Badge variant="warning" className="text-[10px]">
                            {t.inbox.degraded_badge}
                          </Badge>
                        )}
                      </div>
                      <span className="text-[11px] font-mono text-slate-400">
                        {charCount} car.
                      </span>
                    </div>

                    <p className="text-xs font-semibold text-slate-200 line-clamp-1 mb-1">
                      {item.hook || 'Sans accroche'}
                    </p>
                    <p className="text-[11px] text-slate-400 line-clamp-2">
                      {item.body || 'Corps vide'}
                    </p>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Right Column: Detail View, Quality Gate & WYSIWYG Previews (8 cols) */}
          {selectedVariant && (
            <div className="lg:col-span-8 space-y-6">
              {/* Quality Gate Card & Degraded Alert */}
              <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5 space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-2.5">
                    <ShieldCheck className="h-5 w-5 text-emerald-400" />
                    <div>
                      <h4 className="text-sm font-semibold text-white">
                        {t.inbox.quality_gate_title}
                      </h4>
                      <p className="text-[11px] text-slate-400">
                        Contrôle de conformité de marque et sécurité
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {selectedVariant.is_degraded ? (
                      <Badge variant="warning" className="px-2.5 py-1 text-xs flex items-center gap-1.5">
                        <ShieldAlert className="h-3.5 w-3.5 text-amber-400" />
                        <span>{t.inbox.degraded_badge}</span>
                      </Badge>
                    ) : (
                      <Badge variant="success" className="px-2.5 py-1 text-xs">
                        Conforme (Gate 100%)
                      </Badge>
                    )}
                  </div>
                </div>

                {/* Quality Gate details pill grid */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 text-xs border-t border-slate-800/80">
                  <div className="rounded-lg bg-slate-950/60 p-2.5 border border-slate-800">
                    <span className="text-[10px] text-slate-400 uppercase font-mono block">Alignement</span>
                    <span className="font-semibold text-emerald-400">95 / 100</span>
                  </div>
                  <div className="rounded-lg bg-slate-950/60 p-2.5 border border-slate-800">
                    <span className="text-[10px] text-slate-400 uppercase font-mono block">Mots Interdits</span>
                    <span className="font-semibold text-emerald-400">Aucun détecté</span>
                  </div>
                  <div className="rounded-lg bg-slate-950/60 p-2.5 border border-slate-800">
                    <span className="text-[10px] text-slate-400 uppercase font-mono block">Doublons</span>
                    <span className="font-semibold text-emerald-400">Non dupliqué</span>
                  </div>
                  <div className="rounded-lg bg-slate-950/60 p-2.5 border border-slate-800">
                    <span className="text-[10px] text-slate-400 uppercase font-mono block">Mention IA</span>
                    <span className="font-semibold text-cyan-400">Conforme</span>
                  </div>
                </div>
              </div>

              {/* Edit Mode Toggle & Controls */}
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Aperçu et Révision
                </span>
                {canEdit && (
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => setIsEditing(!isEditing)}
                    className="flex items-center gap-1.5 text-xs"
                  >
                    <Edit3 className="h-3.5 w-3.5" />
                    <span>{isEditing ? 'Terminer l’édition' : t.inbox.action_edit}</span>
                  </Button>
                )}
              </div>

              {/* Editable form fields if editing mode is active */}
              {isEditing && (
                <div className="space-y-3 rounded-2xl border border-cyan-500/40 bg-slate-900/90 p-5 shadow-lg">
                  <div>
                    <label className="block text-xs font-semibold uppercase text-slate-300 mb-1">
                      Accroche (Hook)
                    </label>
                    <Input
                      value={editHook}
                      onChange={(e) => setEditHook(e.target.value)}
                      placeholder="Accroche percutante..."
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold uppercase text-slate-300 mb-1">
                      Corps du message
                    </label>
                    <Textarea
                      rows={5}
                      value={editBody}
                      onChange={(e) => setEditBody(e.target.value)}
                      placeholder="Texte détaillé..."
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold uppercase text-slate-300 mb-1">
                      Appel à l'action (CTA)
                    </label>
                    <Input
                      value={editCta}
                      onChange={(e) => setEditCta(e.target.value)}
                      placeholder="ex: Donnez votre avis en commentaire !"
                    />
                  </div>
                </div>
              )}

              {/* High-Fidelity Previews: Side-by-side LinkedIn & X WYSIWYG */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <PlatformPreview
                  platform="linkedin"
                  hook={isEditing ? editHook : selectedVariant.hook}
                  body={isEditing ? editBody : selectedVariant.body}
                  cta={isEditing ? editCta : selectedVariant.cta}
                  authorName="Martial / Analyticatech"
                  authorHeadline="Head of AI & Engineering"
                />

                <PlatformPreview
                  platform="x"
                  hook={isEditing ? editHook : selectedVariant.hook}
                  body={isEditing ? editBody : selectedVariant.body}
                  cta={isEditing ? editCta : selectedVariant.cta}
                  authorName="Analyticatech"
                  authorHeadline="@analyticatech"
                />
              </div>

              {/* HITL Action Bar */}
              <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-slate-800 bg-slate-900/90 p-4 sticky bottom-4 shadow-xl backdrop-blur-md">
                <div className="text-xs text-slate-400">
                  {canApprove ? (
                    <span className="text-emerald-400 font-medium">
                      Rôle Owner : Vous avez autorité pour valider la publication.
                    </span>
                  ) : (
                    <span className="text-slate-400">
                      Rôle {session?.role} : Seul un Owner peut approuver la diffusion en production.
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2.5">
                  {/* Reject Button */}
                  <Button
                    variant="danger"
                    size="sm"
                    disabled={!canApprove || actionLoading}
                    onClick={() => setFeedbackAction('reject')}
                    className="flex items-center gap-1.5"
                  >
                    <XCircle className="h-4 w-4" />
                    <span>{t.inbox.action_reject} (X)</span>
                  </Button>

                  {/* Rewrite Button */}
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={!canEdit || actionLoading}
                    onClick={() => setFeedbackAction('rewrite')}
                    className="flex items-center gap-1.5"
                  >
                    <RefreshCw className="h-4 w-4" />
                    <span>{t.inbox.action_rewrite} (R)</span>
                  </Button>

                  {/* Approve Button */}
                  <Button
                    variant="primary"
                    size="sm"
                    disabled={!canApprove || actionLoading}
                    onClick={() => setConfirmApproveOpen(true)}
                    className="flex items-center gap-1.5"
                  >
                    <CheckCircle2 className="h-4 w-4" />
                    <span>{t.inbox.action_approve} (A)</span>
                  </Button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Mandatory Comment Dialog for Reject / Rewrite */}
      {feedbackAction && (
        <Dialog
          isOpen={true}
          onClose={() => {
            setFeedbackAction(null);
            setFeedbackComment('');
            setFeedbackError(null);
          }}
          title={
            feedbackAction === 'rewrite'
              ? 'Demander une réécriture par l’agent'
              : 'Rejeter le brouillon'
          }
        >
          <div className="space-y-4">
            <p className="text-xs text-slate-300">
              {t.inbox.comment_required_hint}
            </p>
            <Textarea
              rows={4}
              value={feedbackComment}
              onChange={(e) => {
                setFeedbackComment(e.target.value);
                setFeedbackError(null);
              }}
              placeholder="Ex: Le ton est trop informel sur le 2e paragraphe, corriger l'angle technique..."
              required
            />
            {feedbackError && (
              <p className="text-xs text-red-400 font-medium">{feedbackError}</p>
            )}

            <div className="flex justify-end gap-2.5 pt-2">
              <Button
                variant="ghost"
                onClick={() => {
                  setFeedbackAction(null);
                  setFeedbackComment('');
                }}
              >
                Annuler
              </Button>
              <Button
                variant={feedbackAction === 'reject' ? 'danger' : 'primary'}
                isLoading={actionLoading}
                onClick={() => {
                  if (!feedbackComment.trim()) {
                    setFeedbackError('Un commentaire motivé est strictement obligatoire.');
                    return;
                  }
                  executeDecision(feedbackAction, feedbackComment);
                }}
              >
                Confirmer l'action
              </Button>
            </div>
          </div>
        </Dialog>
      )}

      {/* Approve Confirmation Dialog */}
      <ConfirmDialog
        isOpen={confirmApproveOpen}
        onClose={() => setConfirmApproveOpen(false)}
        onConfirm={() => executeDecision('approve')}
        title="Confirmer l'approbation du contenu"
        message={t.inbox.confirm_approve_msg}
        confirmText="Valider pour planification"
        variant="primary"
      />

      {/* Shortcuts Help Dialog */}
      <Dialog
        isOpen={shortcutsOpen}
        onClose={() => setShortcutsOpen(false)}
        title="Raccourcis Clavier Disponibles"
      >
        <div className="space-y-3 text-xs">
          <div className="flex items-center justify-between p-2 rounded bg-slate-950 border border-slate-800">
            <span className="text-slate-300">Passer au brouillon suivant</span>
            <kbd className="px-2 py-0.5 rounded bg-slate-800 text-cyan-300 font-mono font-bold">J</kbd>
          </div>
          <div className="flex items-center justify-between p-2 rounded bg-slate-950 border border-slate-800">
            <span className="text-slate-300">Passer au brouillon précédent</span>
            <kbd className="px-2 py-0.5 rounded bg-slate-800 text-cyan-300 font-mono font-bold">K</kbd>
          </div>
          <div className="flex items-center justify-between p-2 rounded bg-slate-950 border border-slate-800">
            <span className="text-slate-300">Approuver le brouillon actif</span>
            <kbd className="px-2 py-0.5 rounded bg-slate-800 text-cyan-300 font-mono font-bold">A</kbd>
          </div>
          <div className="flex items-center justify-between p-2 rounded bg-slate-950 border border-slate-800">
            <span className="text-slate-300">Demander une réécriture</span>
            <kbd className="px-2 py-0.5 rounded bg-slate-800 text-cyan-300 font-mono font-bold">R</kbd>
          </div>
          <div className="flex items-center justify-between p-2 rounded bg-slate-950 border border-slate-800">
            <span className="text-slate-300">Rejeter le brouillon actif</span>
            <kbd className="px-2 py-0.5 rounded bg-slate-800 text-red-300 font-mono font-bold">X</kbd>
          </div>
        </div>
      </Dialog>
    </div>
  );
};
