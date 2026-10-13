/**
 * Central constants registry for ContentOps Harness frontend.
 * Enforces DRY principles across screens and components.
 */

export interface PlatformConfig {
  id: 'linkedin' | 'x';
  name: string;
  charLimit: number;
  warnThreshold: number;
  domain: string;
  badgeClass: string;
}

export const PLATFORMS: Record<'linkedin' | 'x', PlatformConfig> = {
  linkedin: {
    id: 'linkedin',
    name: 'LinkedIn',
    charLimit: 3000,
    warnThreshold: 2800,
    domain: 'linkedin.com',
    badgeClass: 'bg-blue-900/40 text-blue-300 border-blue-800/50',
  },
  x: {
    id: 'x',
    name: 'X (Twitter)',
    charLimit: 280,
    warnThreshold: 260,
    domain: 'x.com',
    badgeClass: 'bg-slate-900 text-slate-300 border-slate-800',
  },
};

export const CONTENT_STATUSES = {
  DRAFT: 'DRAFT',
  IN_REVIEW: 'IN_REVIEW',
  APPROVED: 'APPROVED',
  REJECTED: 'REJECTED',
  SCHEDULED: 'SCHEDULED',
  PUBLISHING: 'PUBLISHING',
  PUBLISHED: 'PUBLISHED',
  PUBLISH_FAILED: 'PUBLISH_FAILED',
  PUBLISH_UNKNOWN: 'PUBLISH_UNKNOWN',
} as const;

export type ContentStatusType = typeof CONTENT_STATUSES[keyof typeof CONTENT_STATUSES];

export const USER_ROLES = {
  OWNER: 'Owner',
  EDITOR: 'Editor',
  VIEWER: 'Viewer',
} as const;

export type UserRoleType = typeof USER_ROLES[keyof typeof USER_ROLES];

export const HITL_KEYBOARD_SHORTCUTS = {
  NEXT_VARIANT: 'j',
  PREV_VARIANT: 'k',
  APPROVE: 'a',
  REJECT: 'r',
  EDIT: 'e',
  SWITCH_WORKSPACE: 'w',
  QUICK_DISMISS: 'x',
} as const;

export interface ShortcutItem {
  key: string;
  action: string;
  description: string;
}

export const HITL_SHORTCUT_ITEMS: readonly ShortcutItem[] = [
  { key: 'J', action: 'next', description: 'Passer au brouillon suivant' },
  { key: 'K', action: 'prev', description: 'Passer au brouillon précédent' },
  { key: 'A', action: 'approve', description: 'Approuver le brouillon actif (Owner)' },
  { key: 'R', action: 'rewrite', description: 'Demander une réécriture par l’agent' },
  { key: 'X', action: 'reject', description: 'Rejeter le brouillon actif (Owner)' },
  { key: '?', action: 'help', description: 'Afficher les raccourcis' },
];

