import React from 'react';
import { UserProfile } from '../../types/api';
import { Badge } from '../common/Badge';
import { Shield, Clock, Building2 } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';

interface WorkspacesTabProps {
  profile: UserProfile | null;
}

export const WorkspacesTab: React.FC<WorkspacesTabProps> = ({ profile }) => {
  const { language } = useLanguage();
  const isEn = language === 'en';

  return (
    <div className="rounded-xl border border-border-default bg-surface p-6 lg:p-8 space-y-6 shadow-subtle transition-colors duration-150">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-base lg:text-lg font-semibold text-txt-primary tracking-tight">
            {isEn ? 'Workspaces & RBAC Assignments' : 'Espaces de Travail & Affectations RBAC'}
          </h2>
          <p className="text-xs text-txt-muted mt-1 leading-relaxed">
            {isEn
              ? 'List of tenants and organizations where you hold an active role (Owner, Editor, or Viewer).'
              : "Liste des tenants et organisations pour lesquels vous disposez d'un rôle (Owner, Editor ou Viewer)."}
          </p>
        </div>
        <div className="hidden sm:flex h-9 w-9 rounded-lg bg-surface-subtle border border-border-default items-center justify-center text-txt-muted shrink-0">
          <Building2 className="h-4 w-4 text-accent" />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {profile?.workspaces.map((ws) => (
          <div
            key={ws.workspace_id}
            className="p-5 rounded-lg border border-border-subtle bg-surface-subtle hover:border-border-default transition-all space-y-3"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-lg bg-surface border border-border-default flex items-center justify-center text-accent font-bold font-mono text-sm shrink-0">
                  {ws.name.slice(0, 2).toUpperCase()}
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-txt-primary">{ws.name}</h3>
                  <p className="text-xs text-txt-muted font-mono">{ws.workspace_id}</p>
                </div>
              </div>
              <Badge
                variant={ws.is_owner ? 'accent' : ws.role.toLowerCase() === 'editor' ? 'neutral' : 'neutral'}
                className="text-xs px-2.5 py-0.5"
              >
                {ws.role}
              </Badge>
            </div>

            <div className="pt-2 border-t border-border-subtle flex items-center justify-between text-xs text-txt-muted">
              <span className="flex items-center gap-1.5 font-mono">
                <Clock className="h-3.5 w-3.5 text-txt-muted" />
                {ws.timezone}
              </span>
              {ws.is_owner && (
                <span className="text-emerald-500 font-medium text-[11px] flex items-center gap-1">
                  <Shield className="h-3 w-3" />
                  {isEn ? 'Primary Owner' : 'Propriétaire Principal'}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="p-4 rounded-lg border border-border-subtle bg-surface-subtle text-xs text-txt-muted leading-relaxed">
        <strong className="text-txt-primary">
          {isEn ? 'Multi-tenant isolation guarantee: ' : "Principe d'isolation multi-tenant : "}
        </strong>
        {isEn
          ? 'Each workspace benefits from strict isolation at the database level (PostgreSQL RLS) and AES-256-GCM OAuth key sealing (with workspace-bound AAD). Your actions are strictly scoped to the designated role in each tenant.'
          : "Chaque workspace bénéficie d'un cloisonnement étanche au niveau de la base de données (RLS) et des clés de chiffrement de coffre OAuth (AAD = workspace_id). Vos actions sont strictement cantonnées au rôle conféré dans chaque tenant."}
      </div>
    </div>
  );
};
