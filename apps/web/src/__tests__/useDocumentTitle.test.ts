import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useDocumentTitle } from '../hooks/useDocumentTitle';

describe('useDocumentTitle Hook (ANOM-33)', () => {
  const originalTitle = document.title;

  beforeEach(() => {
    document.title = 'Default Title';
  });

  afterEach(() => {
    document.title = originalTitle;
  });

  it('updates document.title with screen name and branding suffix', () => {
    renderHook(() => useDocumentTitle('Calendrier'));
    expect(document.title).toBe('Calendrier — ContentOps Harness');
  });

  it('updates document.title for other screens correctly', () => {
    const { rerender } = renderHook(({ title }) => useDocumentTitle(title), {
      initialProps: { title: 'Tableau de bord' },
    });
    expect(document.title).toBe('Tableau de bord — ContentOps Harness');

    rerender({ title: 'Revue HITL' });
    expect(document.title).toBe('Revue HITL — ContentOps Harness');
  });

  it('falls back to default title if empty or undefined', () => {
    renderHook(() => useDocumentTitle(''));
    expect(document.title).toBe('ContentOps Harness — Gouvernance Éditoriale & Multi-Agents');
  });
});
