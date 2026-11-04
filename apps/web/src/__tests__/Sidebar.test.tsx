import { describe, it, expect, vi } from 'vitest';
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { Sidebar } from '../components/layout/Sidebar';
import { LanguageProvider } from '../context/LanguageContext';
import { AuthProvider } from '../context/AuthContext';

function renderSidebar(props: Partial<React.ComponentProps<typeof Sidebar>> = {}) {
  const defaultProps = {
    currentScreen: 'dashboard',
    onNavigate: vi.fn(),
    isOpenMobile: false,
    onCloseMobile: vi.fn(),
    ...props,
  };

  return render(
    <AuthProvider>
      <LanguageProvider>
        <Sidebar {...defaultProps} />
      </LanguageProvider>
    </AuthProvider>
  );
}

describe('Sidebar Mobile Drawer Accessibility & Focus Trap (ANOM-10)', () => {
  it('does not have role="dialog" or aria-modal when mobile drawer is closed', () => {
    renderSidebar({ isOpenMobile: false });
    const aside = document.getElementById('sidebar-navigation');
    expect(aside).toBeDefined();
    expect(aside?.getAttribute('role')).toBeNull();
    expect(aside?.getAttribute('aria-modal')).toBeNull();
  });

  it('sets role="dialog" and aria-modal="true" on mobile drawer when open', () => {
    renderSidebar({ isOpenMobile: true });
    const aside = document.getElementById('sidebar-navigation');
    expect(aside?.getAttribute('role')).toBe('dialog');
    expect(aside?.getAttribute('aria-modal')).toBe('true');
    expect(aside?.getAttribute('aria-label')).toBe('Navigation principale');
  });

  it('renders accessible close button and triggers onCloseMobile on click', () => {
    const onCloseMobile = vi.fn();
    renderSidebar({ isOpenMobile: true, onCloseMobile });

    const closeBtn = screen.getByLabelText('Fermer le menu');
    expect(closeBtn).toBeDefined();
    fireEvent.click(closeBtn);
    expect(onCloseMobile).toHaveBeenCalledTimes(1);
  });

  it('closes mobile drawer when pressing Escape key', () => {
    const onCloseMobile = vi.fn();
    renderSidebar({ isOpenMobile: true, onCloseMobile });

    fireEvent.keyDown(window, { key: 'Escape' });
    expect(onCloseMobile).toHaveBeenCalledTimes(1);
  });
});
