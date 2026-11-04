import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { InboxDraftList } from '../components/inbox/InboxDraftList';
import { LanguageProvider } from '../context/LanguageContext';

describe('InboxDraftList ARIA Compliance (ANOM-30)', () => {
  const dummyVariants = [
    {
      id: 'v1',
      platform: 'linkedin',
      hook: 'Hook test 1',
      body: 'Body test 1',
      status: 'pending_review',
    },
    {
      id: 'v2',
      platform: 'x',
      hook: 'Hook test 2',
      body: 'Body test 2',
      status: 'pending_review',
    },
  ];

  it('renders a role="group" container without invalid button role="option"', () => {
    const onSelect = vi.fn();
    render(
      <LanguageProvider>
        <InboxDraftList
          variants={dummyVariants as any}
          selectedIndex={0}
          onSelect={onSelect}
        />
      </LanguageProvider>
    );

    // Group container has accessible label
    const group = screen.getByRole('group', { name: /Liste des brouillons à réviser|Drafts queue to review/i });
    expect(group).toBeDefined();

    // No elements with invalid role="option"
    const options = screen.queryAllByRole('option');
    expect(options.length).toBe(0);

    // Buttons are native buttons with aria-current on the selected one
    const buttons = screen.getAllByRole('button');
    expect(buttons.length).toBe(2);
    expect(buttons[0].getAttribute('aria-current')).toBe('true');
    expect(buttons[1].getAttribute('aria-current')).toBeNull();
  });
});
