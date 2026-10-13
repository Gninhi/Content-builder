import React, { useState, useEffect } from 'react';
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
import { PlatformPreview } from '../components/common/PlatformPreview';
import { useHitlShortcuts } from '../hooks/useHitlShortcuts';
import { InboxQualityGateCard } from '../components/inbox/InboxQualityGateCard';
import { InboxDraftList } from '../components/inbox/InboxDraftList';
import { InboxEditForm } from '../components/inbox/InboxEditForm';
import { InboxActionBar } from '../components/inbox/InboxActionBar';
import { InboxFeedbackModal } from '../components/inbox/InboxFeedbackModal';
import { InboxShortcutsModal } from '../components/inbox/InboxShortcutsModal';
import { Edit3, Keyboard, Shield } from 'lucide-react';

export const InboxScreen: React.FC = () => {
  const { t, language } = useLanguage();
  const { session, canApprove, canEdit } = useAuth();
  const { showToast } = useToast();
  const isEn = language === 'en';

  const [variants, setVariants] = useState<InboxVariant[]>([]);
  const [selectedIndex, setSelectedIndex] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filter state
  const [platformFilter, setPlatformFilter] = useState<string>('all');

  // Mobile sub-tab state ('list' | 'preview' | 'quality')
  const [mobileTab, setMobileTab] = useState<'list' | 'preview' | 'quality'>('list');

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

  // Live mode approval confirmation dialog & shortcuts modal
  const [confirmApproveOpen, setConfirmApproveOpen] = useState<boolean>(false);
  const [shortcutsOpen, setShortcutsOpen] = useState<boolean>(false);

  const initEditState = (v: InboxVariant) => {
    setEditHook(v.hook || '');
    setEditBody(v.body || '');
    setEditCta(v.cta || '');
    setIsEditing(false);
  };

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
        showToast('success', res.message || (isEn ? 'Draft rewritten by agent!' : 'Brouillon réécrit avec succès par l’agent !'));
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
            ? (isEn ? 'Draft approved and cryptographically sealed (SHA-256)!' : 'Brouillon approuvé et scellé cryptographiquement !')
            : (isEn ? 'Draft rejected.' : 'Brouillon rejeté avec succès.')
        );
      }

      await fetchInbox();
    } catch (err: any) {
      showToast(
        'error',
        err.detail || err.message || (isEn ? 'Error while processing decision.' : 'Erreur lors du traitement de la décision.')
      );
    } finally {
      setActionLoading(false);
      setFeedbackAction(null);
      setFeedbackComment('');
      setConfirmApproveOpen(false);
    }
  };

  // Keyboard Shortcuts Hook
  useHitlShortcuts({
    onNext: () => {
      if (selectedIndex < filteredVariants.length - 1) {
        setSelectedIndex((prev) => prev + 1);
      }
    },
    onPrev: () => {
      if (selectedIndex > 0) {
        setSelectedIndex((prev) => prev - 1);
      }
    },
    onApprove: () => {
      if (canApprove && !actionLoading && selectedVariant) {
        setConfirmApproveOpen(true);
      }
    },
    onRewrite: () => {
      if (canEdit && !actionLoading && selectedVariant) {
        setFeedbackAction('rewrite');
      }
    },
    onReject: () => {
      if (canApprove && !actionLoading && selectedVariant) {
        setFeedbackAction('reject');
      }
    },
    onHelp: () => {
      setShortcutsOpen(true);
    },
    enabled: !feedbackAction && !confirmApproveOpen && !shortcutsOpen && !isEditing,
  });

  if (loading && variants.length === 0) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-14 w-full rounded-xl" />
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <Skeleton className="lg:col-span-3 h-96 rounded-xl" />
          <Skeleton className="lg:col-span-5 h-96 rounded-xl" />
          <Skeleton className="lg:col-span-4 h-96 rounded-xl" />
        </div>
      </div>
    );
  }

  if (error && variants.length === 0) {
    return <ErrorState message={error} onRetry={fetchInbox} />;
  }

  return (
    <div className="space-y-6 w-full pb-28">
      {/* Top Header & Filters */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border-default pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg sm:text-xl font-bold text-txt-primary tracking-tight">
              {t.inbox.title}
            </h2>
            <Badge variant="warning" className="text-xs font-semibold">
              {filteredVariants.length} {t.inbox.queue_title}
            </Badge>
          </div>
          <p className="text-xs text-txt-muted mt-0.5">
            {isEn
              ? 'Mandatory human validation prior to cryptographic sealing and scheduling (Shortcuts: J/K, A, R, X, ?)'
              : 'Validation humaine obligatoire avant tout scellement et diffusion (raccourcis: J/K, A, R, X, ?)'}
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Platform Filter */}
          <div className="flex items-center rounded-md border border-border-default bg-surface-subtle p-0.5 text-xs font-mono">
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
                    ? 'bg-accent text-txt-inverse font-bold shadow-xs'
                    : 'text-txt-muted hover:text-txt-primary'
                }`}
              >
                {p === 'all' ? (isEn ? 'All' : 'Toutes') : p.toUpperCase()}
              </button>
            ))}
          </div>

          {/* Keyboard Shortcuts Trigger */}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShortcutsOpen(true)}
            className="text-txt-muted hover:text-txt-primary flex items-center gap-1.5 min-h-[36px]"
            title={t.inbox.shortcuts_help}
          >
            <Keyboard className="h-4 w-4" />
            <span className="hidden md:inline text-xs font-mono">
              {isEn ? 'Help (?)' : 'Aide (?)'}
            </span>
          </Button>
        </div>
      </div>

      {filteredVariants.length === 0 ? (
        <EmptyState
          title={t.inbox.empty_title}
          description={t.inbox.empty_desc}
          actionLabel={isEn ? 'Generate new ideas' : 'Générer de nouvelles idées'}
          onAction={() => {
            window.location.hash = '#ideation';
          }}
        />
      ) : (
        <>
          {/* Mobile sub-tabs selector (sm/md only) */}
          <div className="flex lg:hidden rounded-lg border border-border-default bg-surface-subtle p-1 text-xs">
            <button
              type="button"
              onClick={() => setMobileTab('list')}
              className={`flex-1 py-1.5 text-center font-medium rounded transition-colors ${
                mobileTab === 'list'
                  ? 'bg-surface text-txt-primary font-semibold shadow-xs'
                  : 'text-txt-muted'
              }`}
            >
              {isEn ? `Drafts (${filteredVariants.length})` : `Brouillons (${filteredVariants.length})`}
            </button>
            <button
              type="button"
              onClick={() => setMobileTab('preview')}
              className={`flex-1 py-1.5 text-center font-medium rounded transition-colors ${
                mobileTab === 'preview'
                  ? 'bg-surface text-txt-primary font-semibold shadow-xs'
                  : 'text-txt-muted'
              }`}
            >
              {isEn ? 'Draft & Previews' : 'Révision & Aperçus'}
            </button>
            <button
              type="button"
              onClick={() => setMobileTab('quality')}
              className={`flex-1 py-1.5 text-center font-medium rounded transition-colors ${
                mobileTab === 'quality'
                  ? 'bg-surface text-txt-primary font-semibold shadow-xs'
                  : 'text-txt-muted'
              }`}
            >
              {isEn ? 'Quality Gate' : 'Quality Gate'}
            </button>
          </div>

          {/* Desktop 3-column layout */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            {/* Column 1: Drafts List Queue */}
            <div className={`lg:col-span-3 ${mobileTab === 'list' ? 'block' : 'hidden lg:block'}`}>
              <InboxDraftList
                variants={filteredVariants}
                selectedIndex={selectedIndex}
                onSelect={(idx) => {
                  setSelectedIndex(idx);
                  initEditState(filteredVariants[idx]);
                  setMobileTab('preview');
                }}
              />
            </div>

            {/* Column 2: Draft Editor & WYSIWYG Platform Previews */}
            {selectedVariant && (
              <div
                className={`lg:col-span-5 space-y-4 ${
                  mobileTab === 'preview' ? 'block' : 'hidden lg:block'
                }`}
              >
                {/* Edit Mode Toggle Header */}
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-txt-secondary">
                    {isEn ? 'Review & Previews' : 'Aperçu & Révision'}
                  </span>
                  {canEdit && (
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setIsEditing(!isEditing)}
                      className="flex items-center gap-1.5 text-xs min-h-[36px]"
                    >
                      <Edit3 className="h-3.5 w-3.5" />
                      <span>{isEditing ? (isEn ? 'Done Editing' : 'Terminer l’édition') : t.inbox.action_edit}</span>
                    </Button>
                  )}
                </div>

                {/* Editable form fields */}
                {isEditing && (
                  <InboxEditForm
                    hook={editHook}
                    body={editBody}
                    cta={editCta}
                    onHookChange={setEditHook}
                    onBodyChange={setEditBody}
                    onCtaChange={setEditCta}
                  />
                )}

                {/* Side-by-side or stacked Platform WYSIWYG Previews */}
                <div className="space-y-4">
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
              </div>
            )}

            {/* Column 3: Quality Gate, Cryptographic Seal Status & Evidence */}
            {selectedVariant && (
              <div
                className={`lg:col-span-4 space-y-4 ${
                  mobileTab === 'quality' ? 'block' : 'hidden lg:block'
                }`}
              >
                <InboxQualityGateCard variant={selectedVariant} />

                {/* Cryptographic Seal & Fact-Checking Card */}
                <div className="rounded-xl border border-border-default bg-surface p-5 space-y-3.5 shadow-subtle">
                  <div className="flex items-center gap-2">
                    <Shield className="h-4 w-4 text-accent" />
                    <h4 className="text-xs font-semibold text-txt-primary">
                      {isEn ? 'Cryptographic Proof & Audit Trail' : 'Scellement & Preuves Cryptographiques'}
                    </h4>
                  </div>

                  <p className="text-[11px] text-txt-secondary leading-relaxed">
                    {isEn
                      ? 'Upon approval, an irreversible SHA-256 seal is computed and registered in the append-only audit trail before dispatching.'
                      : 'À l’approbation, une empreinte SHA-256 immuable est scellée et enregistrée dans le registre d’audit append-only avant diffusion.'}
                  </p>

                  <div className="rounded-lg bg-surface-subtle p-3 border border-border-subtle space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-txt-muted">{isEn ? 'Status' : 'Statut'}</span>
                      <Badge variant="warning" className="text-[10px]">
                        {isEn ? 'Pending Seal' : 'En attente de scellement'}
                      </Badge>
                    </div>
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-txt-muted">{isEn ? 'Algorithm' : 'Algorithme'}</span>
                      <span className="font-mono text-[11px] text-txt-primary">SHA-256 / Ed25519</span>
                    </div>
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-txt-muted">{isEn ? 'Publication Gate' : 'Garantie diffusion'}</span>
                      <span className="font-medium text-status-success-text text-[11px]">
                        {isEn ? 'At-most-once' : 'Au plus une fois'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Sticky HITL Responsive Action Dock */}
          {selectedVariant && (
            <div className="fixed bottom-4 inset-x-4 max-w-4xl mx-auto z-30">
              <InboxActionBar
                canApprove={canApprove}
                canEdit={canEdit}
                userRole={session?.role}
                actionLoading={actionLoading}
                onReject={() => setFeedbackAction('reject')}
                onRewrite={() => setFeedbackAction('rewrite')}
                onApprove={() => setConfirmApproveOpen(true)}
              />
            </div>
          )}
        </>
      )}

      {/* Mandatory Comment Dialog for Reject / Rewrite */}
      <InboxFeedbackModal
        isOpen={Boolean(feedbackAction)}
        action={feedbackAction}
        comment={feedbackComment}
        error={feedbackError}
        isLoading={actionLoading}
        onCommentChange={(val) => {
          setFeedbackComment(val);
          setFeedbackError(null);
        }}
        onClose={() => {
          setFeedbackAction(null);
          setFeedbackComment('');
          setFeedbackError(null);
        }}
        onSubmit={() => {
          if (!feedbackComment.trim()) {
            setFeedbackError(
              isEn
                ? 'A motivated comment is strictly required to guide the agent or trace the decision.'
                : 'Un commentaire motivé est strictement obligatoire.'
            );
            return;
          }
          if (feedbackAction) {
            executeDecision(feedbackAction, feedbackComment);
          }
        }}
      />

      {/* Live mode approval confirmation dialog */}
      <ConfirmDialog
        isOpen={confirmApproveOpen}
        onClose={() => setConfirmApproveOpen(false)}
        onConfirm={() => executeDecision('approve')}
        title={isEn ? 'Confirm Content Approval' : 'Confirmer l’approbation du contenu'}
        message={t.inbox.confirm_approve_msg}
        confirmText={isEn ? 'Approve & Schedule' : 'Valider pour planification'}
        variant="primary"
      />

      {/* Shortcuts Help Modal */}
      <InboxShortcutsModal
        isOpen={shortcutsOpen}
        onClose={() => setShortcutsOpen(false)}
      />
    </div>
  );
};
