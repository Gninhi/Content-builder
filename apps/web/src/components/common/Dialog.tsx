import React, { useEffect, useRef } from 'react';
import { X } from 'lucide-react';
import clsx from 'clsx';

interface DialogProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children: React.ReactNode;
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl';
}

export const Dialog: React.FC<DialogProps> = ({
  isOpen,
  onClose,
  title,
  description,
  children,
  maxWidth = 'md',
}) => {
  const dialogRef = useRef<HTMLDivElement>(null);
  const previouslyFocusedElement = useRef<HTMLElement | null>(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;
  const wasOpenRef = useRef(false);

  useEffect(() => {
    if (isOpen) {
      if (!wasOpenRef.current) {
        wasOpenRef.current = true;
        previouslyFocusedElement.current = document.activeElement as HTMLElement;
        document.body.style.overflow = 'hidden';

        // Focus the first form input or autofocus element once on opening
        const timer = setTimeout(() => {
          // Do not steal focus if user has already focused an element inside the dialog
          if (dialogRef.current?.contains(document.activeElement)) {
            return;
          }

          const autoFocusEl = dialogRef.current?.querySelector<HTMLElement>(
            '[autofocus], [data-autofocus]'
          );
          if (autoFocusEl) {
            autoFocusEl.focus();
            return;
          }

          const formInput = dialogRef.current?.querySelector<HTMLElement>(
            'input:not([disabled]), textarea:not([disabled]), select:not([disabled])'
          );
          if (formInput) {
            formInput.focus();
            return;
          }

          const focusable = dialogRef.current?.querySelectorAll<HTMLElement>(
            'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
          );
          if (focusable && focusable.length > 0) {
            focusable[0].focus();
          } else {
            dialogRef.current?.focus();
          }
        }, 50);

        return () => {
          clearTimeout(timer);
        };
      }
    } else {
      if (wasOpenRef.current) {
        wasOpenRef.current = false;
        document.body.style.overflow = 'unset';
        if (previouslyFocusedElement.current) {
          previouslyFocusedElement.current.focus();
        }
      }
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onCloseRef.current();
      }

      if (e.key === 'Tab' && dialogRef.current) {
        const focusables = dialogRef.current.querySelectorAll<HTMLElement>(
          'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
        );
        if (focusables.length === 0) return;

        const first = focusables[0];
        const last = focusables[focusables.length - 1];

        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const widthClasses = {
    sm: 'max-w-sm',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-4xl',
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/60 backdrop-blur-sm transition-opacity"
      role="presentation"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="dialog-title"
        aria-describedby={description ? 'dialog-description' : undefined}
        tabIndex={-1}
        className={clsx(
          'w-full bg-surface-raised border border-border rounded-xl p-5 sm:p-6 shadow-raised relative text-txt-primary outline-none max-h-[90vh] overflow-y-auto',
          widthClasses[maxWidth]
        )}
      >
        <div className="flex items-center justify-between pb-3.5 border-b border-border">
          <div>
            <h2 id="dialog-title" className="text-base sm:text-lg font-bold text-txt-primary tracking-tight">
              {title}
            </h2>
            {description && (
              <p id="dialog-description" className="text-xs text-txt-muted mt-0.5">
                {description}
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Fermer la boîte de dialogue"
            className="p-1.5 rounded-md text-txt-muted hover:text-txt-primary hover:bg-surface-hover transition-colors min-w-[36px] min-h-[36px] flex items-center justify-center focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-border-focus"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="mt-4">{children}</div>
      </div>
    </div>
  );
};
