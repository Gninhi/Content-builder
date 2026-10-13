import { useEffect, useCallback } from 'react';

export interface UseHitlShortcutsOptions {
  onNext?: () => void;
  onPrev?: () => void;
  onApprove?: () => void;
  onRewrite?: () => void;
  onReject?: () => void;
  onHelp?: () => void;
  onEscape?: () => void;
  enabled?: boolean;
}

/**
 * Custom hook to manage keyboard shortcuts for HITL editorial review.
 * Respects form inputs by suppressing shortcuts when typing.
 */
export function useHitlShortcuts({
  onNext,
  onPrev,
  onApprove,
  onRewrite,
  onReject,
  onHelp,
  onEscape,
  enabled = true,
}: UseHitlShortcutsOptions) {
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!enabled) return;

      const target = e.target as HTMLElement | null;
      if (
        target &&
        (target.tagName === 'INPUT' ||
          target.tagName === 'TEXTAREA' ||
          target.isContentEditable)
      ) {
        return;
      }

      switch (e.key.toLowerCase()) {
        case 'j':
          onNext?.();
          break;
        case 'k':
          onPrev?.();
          break;
        case 'a':
          onApprove?.();
          break;
        case 'r':
          onRewrite?.();
          break;
        case 'x':
          onReject?.();
          break;
        case '?':
          onHelp?.();
          break;
        case 'escape':
          onEscape?.();
          break;
        default:
          break;
      }
    },
    [enabled, onNext, onPrev, onApprove, onRewrite, onReject, onHelp, onEscape]
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);
}
