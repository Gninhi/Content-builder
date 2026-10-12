import React, { useState } from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { Dialog } from '../components/common/Dialog';
import { Input } from '../components/common/Input';

const ModalWithControlledInput: React.FC = () => {
  const [isOpen, setIsOpen] = useState(true);
  const [topic, setTopic] = useState('');
  const [targetCount, setTargetCount] = useState(3);

  return (
    <div>
      <button data-testid="open-btn" onClick={() => setIsOpen(true)}>
        Ouvrir
      </button>
      <Dialog
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        title="Recherche & Synthèse d'Idées par Agent"
      >
        <form onSubmit={(e) => e.preventDefault()}>
          <Input
            id="research-topic"
            data-testid="research-topic-input"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="Ex: Modèles de raisonnement"
            autoFocus
          />
          <Input
            id="target-count"
            data-testid="target-count-input"
            type="number"
            min={1}
            max={10}
            value={targetCount}
            onChange={(e) => {
              const val = parseInt(e.target.value, 10);
              setTargetCount(isNaN(val) ? 1 : Math.min(10, Math.max(1, val)));
            }}
          />
        </form>
      </Dialog>
    </div>
  );
};

describe('Phase 3 Regression - Ideation Modal Focus Stability', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('keeps focus continuously on the input field character by character without stealing to close button', async () => {
    render(<ModalWithControlledInput />);

    // Fast-forward initial opening timer
    act(() => {
      vi.advanceTimersByTime(100);
    });

    const input = screen.getByTestId('research-topic-input') as HTMLInputElement;
    const closeBtn = screen.getByRole('button', { name: /fermer/i });

    // Ensure input is focused
    input.focus();
    expect(document.activeElement).toBe(input);

    // Simulate typing character by character, advancing timers between each keypress
    const phrase = 'Agentic AI 2026';
    let currentVal = '';

    for (let i = 0; i < phrase.length; i++) {
      const char = phrase[i];
      currentVal += char;

      act(() => {
        fireEvent.change(input, { target: { value: currentVal } });
        // Advance timers past any potential 50ms focus stealing debounce
        vi.advanceTimersByTime(60);
      });

      // The input must RETAIN focus; it must NEVER be stolen by the close button!
      expect(document.activeElement).toBe(input);
      expect(document.activeElement).not.toBe(closeBtn);
      expect(input.value).toBe(currentVal);
    }
  });

  it('allows complete text selection, replacement, and pasting without losing focus', async () => {
    render(<ModalWithControlledInput />);

    act(() => {
      vi.advanceTimersByTime(100);
    });

    const input = screen.getByTestId('research-topic-input') as HTMLInputElement;
    input.focus();

    // Type initial text
    act(() => {
      fireEvent.change(input, { target: { value: 'Initial draft' } });
      vi.advanceTimersByTime(60);
    });
    expect(document.activeElement).toBe(input);

    // Paste / replace entire content
    act(() => {
      fireEvent.change(input, { target: { value: 'Nouveau thème collé depuis le presse-papier' } });
      vi.advanceTimersByTime(60);
    });

    expect(document.activeElement).toBe(input);
    expect(input.value).toBe('Nouveau thème collé depuis le presse-papier');
  });

  it('strictly constrains target ideas count between 1 and 10 as an integer', () => {
    render(<ModalWithControlledInput />);

    act(() => {
      vi.advanceTimersByTime(100);
    });

    const countInput = screen.getByTestId('target-count-input') as HTMLInputElement;

    // Test below minimum
    act(() => {
      fireEvent.change(countInput, { target: { value: '0' } });
      vi.advanceTimersByTime(50);
    });
    expect(countInput.value).toBe('1');

    // Test above maximum
    act(() => {
      fireEvent.change(countInput, { target: { value: '25' } });
      vi.advanceTimersByTime(50);
    });
    expect(countInput.value).toBe('10');

    // Test valid intermediate value
    act(() => {
      fireEvent.change(countInput, { target: { value: '7' } });
      vi.advanceTimersByTime(50);
    });
    expect(countInput.value).toBe('7');
  });
});
