import { useEffect } from 'react';

/**
 * Custom hook to dynamically synchronize document.title with the active screen.
 * Formats: "${title} — ContentOps Harness"
 */
export function useDocumentTitle(title?: string) {
  useEffect(() => {
    if (title && title.trim()) {
      document.title = `${title.trim()} — ContentOps Harness`;
    } else {
      document.title = 'ContentOps Harness — Gouvernance Éditoriale & Multi-Agents';
    }
  }, [title]);
}
