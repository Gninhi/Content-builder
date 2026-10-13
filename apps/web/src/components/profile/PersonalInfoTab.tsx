import React from 'react';
import { UserProfile } from '../../types/api';
import { Input } from '../common/Input';
import { Button } from '../common/Button';
import { Lock, UserCheck } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';

interface PersonalInfoTabProps {
  profile: UserProfile | null;
  fullName: string;
  setFullName: (val: string) => void;
  displayName: string;
  setDisplayName: (val: string) => void;
  jobTitle: string;
  setJobTitle: (val: string) => void;
  isSaving: boolean;
  onSave: (e: React.FormEvent) => void;
}

export const PersonalInfoTab: React.FC<PersonalInfoTabProps> = ({
  profile,
  fullName,
  setFullName,
  displayName,
  setDisplayName,
  jobTitle,
  setJobTitle,
  isSaving,
  onSave,
}) => {
  const { language } = useLanguage();
  const isEn = language === 'en';

  return (
    <div className="rounded-xl border border-border-default bg-surface p-6 lg:p-8 space-y-6 shadow-subtle transition-colors duration-150">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-base lg:text-lg font-semibold text-txt-primary tracking-tight">
            {isEn ? 'General Identity & Information' : 'Informations Générales & Identité'}
          </h2>
          <p className="text-xs text-txt-muted mt-1 leading-relaxed">
            {isEn
              ? 'This information is used in human-in-the-loop (HITL) audit logs and editorial traceability.'
              : "Ces informations sont utilisées dans la traçabilité des validations HITL et l'audit éditorial."}
          </p>
        </div>
        <div className="hidden sm:flex h-9 w-9 rounded-lg bg-surface-subtle border border-border-default items-center justify-center text-txt-muted shrink-0">
          <UserCheck className="h-4 w-4 text-accent" />
        </div>
      </div>

      <form onSubmit={onSave} className="space-y-5 max-w-2xl">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Input
            label={isEn ? 'Full Name' : 'Nom complet'}
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            placeholder={isEn ? 'e.g. Martial Martial' : 'Ex. Martial Martial'}
            required
            className="min-h-[44px]"
          />
          <Input
            label={isEn ? 'Public Display Name' : "Nom d'affichage public"}
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder={isEn ? 'e.g. Martial (CCO)' : 'Ex. Martial (CCO)'}
            className="min-h-[44px]"
          />
        </div>

        <Input
          label={isEn ? 'Job Title / Role' : 'Fonction / Titre professionnel'}
          value={jobTitle}
          onChange={(e) => setJobTitle(e.target.value)}
          placeholder={isEn ? 'e.g. Chief Content Officer, AI Strategist' : 'Ex. Chief Content Officer, AI Strategist'}
          className="min-h-[44px]"
        />

        {/* Email Field (Strictly Read-Only) */}
        <div className="space-y-1.5">
          <label className="flex items-center justify-between text-xs font-medium text-txt-secondary">
            <span className="flex items-center gap-1.5">
              <Lock className="h-3.5 w-3.5 text-accent" />
              {isEn ? 'Account Email Address' : 'Adresse email du compte'}
            </span>
            <span className="text-[11px] text-accent font-mono font-medium">
              {isEn ? 'Server-managed (immutable)' : 'Géré par le serveur (immuable)'}
            </span>
          </label>
          <input
            type="text"
            disabled
            value={profile?.email || ''}
            className="w-full bg-surface-subtle border border-border-default rounded-lg px-3.5 py-2.5 text-sm text-txt-muted cursor-not-allowed font-mono select-none min-h-[44px]"
          />
          <p className="text-xs text-txt-muted">
            {isEn
              ? 'The email address is the cryptographic anchor of your workspace permissions and cannot be changed arbitrarily. Contact an administrator for modifications.'
              : "L'adresse email est le pivot cryptographique de vos droits d'accès et ne peut être modifiée unilatéralement. Contactez un administrateur pour tout changement."}
          </p>
        </div>

        <div className="pt-2">
          <Button type="submit" variant="primary" isLoading={isSaving} className="min-h-[44px] font-medium">
            {isEn ? 'Save Changes' : 'Enregistrer les modifications'}
          </Button>
        </div>
      </form>
    </div>
  );
};
