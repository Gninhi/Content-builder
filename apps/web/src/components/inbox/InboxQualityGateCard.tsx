import React from 'react';
import { ShieldCheck, ShieldAlert } from 'lucide-react';
import { Badge } from '../common/Badge';
import { useLanguage } from '../../context/LanguageContext';
import { InboxVariant } from '../../types/api';

interface InboxQualityGateCardProps {
  variant: InboxVariant;
}

export const InboxQualityGateCard: React.FC<InboxQualityGateCardProps> = ({ variant }) => {
  const { t, language } = useLanguage();
  const isEn = language === 'en';
  const report = variant.quality_gate_report;

  const isPassed = report?.passed ?? !variant.is_degraded;
  const alignmentScore = report?.brand_alignment_score ?? 95;
  const isBannedClean = report ? report.prohibited_topics_clean : true;
  const isUnique = report ? !report.duplicate_detected : true;
  const isAiCompliant = report ? report.ai_disclosure_compliant : true;

  return (
    <div className="rounded-xl border border-border-default bg-surface-elevated p-5 space-y-4 shadow-subtle">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          {isPassed ? (
            <ShieldCheck className="h-5 w-5 text-status-success-text" />
          ) : (
            <ShieldAlert className="h-5 w-5 text-status-danger-text" />
          )}
          <div>
            <h4 className="text-sm font-semibold text-txt-primary tracking-tight">
              {t.inbox.quality_gate_title}
            </h4>
            <p className="text-xs text-txt-muted">
              {isEn ? 'Brand compliance and safety verification' : 'Contrôle de conformité de marque et sécurité'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {variant.is_degraded ? (
            <Badge variant="warning" className="px-2.5 py-1 text-xs flex items-center gap-1.5 font-medium">
              <ShieldAlert className="h-3.5 w-3.5" />
              <span>{t.inbox.degraded_badge}</span>
            </Badge>
          ) : isPassed ? (
            <Badge variant="success" className="px-2.5 py-1 text-xs font-medium">
              {isEn ? `Compliant (Gate ${alignmentScore}%)` : `Conforme (Gate ${alignmentScore}%)`}
            </Badge>
          ) : (
            <Badge variant="danger" className="px-2.5 py-1 text-xs font-medium">
              {isEn ? 'Non-compliant' : 'Non-conforme'}
            </Badge>
          )}
        </div>
      </div>

      {/* Quality Gate details grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 text-xs border-t border-border-subtle">
        <div className="rounded-lg bg-surface-subtle p-3 border border-border-subtle">
          <span className="text-xs text-txt-muted font-medium block">
            {isEn ? 'Brand alignment' : 'Alignement marque'}
          </span>
          <span className={`font-semibold text-sm ${alignmentScore >= 80 ? 'text-status-success-text' : 'text-status-warning-text'}`}>
            {alignmentScore} / 100
          </span>
        </div>
        <div className="rounded-lg bg-surface-subtle p-3 border border-border-subtle">
          <span className="text-xs text-txt-muted font-medium block">
            {isEn ? 'Banned terms' : 'Mots interdits'}
          </span>
          <span className={`font-semibold text-sm ${isBannedClean ? 'text-status-success-text' : 'text-status-danger-text'}`}>
            {isBannedClean ? (isEn ? '0 detected' : '0 détecté') : (isEn ? 'Violation' : 'Détecté')}
          </span>
        </div>
        <div className="rounded-lg bg-surface-subtle p-3 border border-border-subtle">
          <span className="text-xs text-txt-muted font-medium block">
            {isEn ? 'Deduplication' : 'Doublons'}
          </span>
          <span className={`font-semibold text-sm ${isUnique ? 'text-status-success-text' : 'text-status-warning-text'}`}>
            {isUnique ? (isEn ? 'Unique' : 'Non dupliqué') : (isEn ? 'Duplicate' : 'Doublon détecté')}
          </span>
        </div>
        <div className="rounded-lg bg-surface-subtle p-3 border border-border-subtle">
          <span className="text-xs text-txt-muted font-medium block">
            {isEn ? 'AI disclosure' : 'Mention IA'}
          </span>
          <span className={`font-semibold text-sm ${isAiCompliant ? 'text-accent-text' : 'text-status-warning-text'}`}>
            {isAiCompliant ? (isEn ? 'Compliant' : 'Conforme') : (isEn ? 'Missing' : 'Manquante')}
          </span>
        </div>
      </div>
    </div>
  );
};
