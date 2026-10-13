/**
 * Unified date formatting library with FR / EN locale support.
 * Zero external date library dependency (uses native Intl.DateTimeFormat).
 */

export type SupportedLocale = 'fr' | 'en';

export function formatDate(
  dateInput: string | number | Date,
  locale: SupportedLocale = 'fr',
  options?: Intl.DateTimeFormatOptions
): string {
  if (!dateInput) return '';
  const date = typeof dateInput === 'string' || typeof dateInput === 'number' ? new Date(dateInput) : dateInput;
  if (isNaN(date.getTime())) return '';

  const defaultOptions: Intl.DateTimeFormatOptions = {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    ...options,
  };

  const localeTag = locale === 'fr' ? 'fr-FR' : 'en-US';
  return new Intl.DateTimeFormat(localeTag, defaultOptions).format(date);
}

export function formatDateTime(
  dateInput: string | number | Date,
  locale: SupportedLocale = 'fr'
): string {
  return formatDate(dateInput, locale, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function formatTime(
  dateInput: string | number | Date,
  locale: SupportedLocale = 'fr'
): string {
  return formatDate(dateInput, locale, {
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function formatRelativeTime(
  dateInput: string | number | Date,
  locale: SupportedLocale = 'fr'
): string {
  if (!dateInput) return '';
  const date = typeof dateInput === 'string' || typeof dateInput === 'number' ? new Date(dateInput) : dateInput;
  if (isNaN(date.getTime())) return '';

  const now = new Date();
  const diffSec = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (diffSec < 60) {
    return locale === 'fr' ? "À l'instant" : 'Just now';
  }

  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) {
    return locale === 'fr' ? `Il y a ${diffMin} min` : `${diffMin}m ago`;
  }

  const diffHours = Math.floor(diffMin / 60);
  if (diffHours < 24) {
    return locale === 'fr' ? `Il y a ${diffHours} h` : `${diffHours}h ago`;
  }

  const diffDays = Math.floor(diffHours / 24);
  if (diffDays === 1) {
    return locale === 'fr' ? 'Hier' : 'Yesterday';
  }
  if (diffDays < 7) {
    return locale === 'fr' ? `Il y a ${diffDays} j` : `${diffDays}d ago`;
  }

  return formatDate(date, locale, { day: 'numeric', month: 'short' });
}
