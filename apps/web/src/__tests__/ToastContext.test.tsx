import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ToastProvider, useToast } from '../context/ToastContext';

const TestComponent = () => {
  const { showToast } = useToast();
  return (
    <div>
      <button onClick={() => showToast('success', 'Opération réussie !')}>Trigger Success</button>
      <button onClick={() => showToast('error', 'Une erreur est survenue.')}>Trigger Error</button>
    </div>
  );
};

describe('ToastContext', () => {
  it('renders children and displays toasts when triggered', () => {
    render(
      <ToastProvider>
        <TestComponent />
      </ToastProvider>
    );

    expect(screen.queryByText('Opération réussie !')).not.toBeInTheDocument();

    const successBtn = screen.getByText('Trigger Success');
    fireEvent.click(successBtn);

    expect(screen.getByText('Opération réussie !')).toBeInTheDocument();
  });

  it('allows dismissing a toast via the close button', () => {
    render(
      <ToastProvider>
        <TestComponent />
      </ToastProvider>
    );

    fireEvent.click(screen.getByText('Trigger Error'));
    expect(screen.getByText('Une erreur est survenue.')).toBeInTheDocument();

    const closeBtn = screen.getByLabelText('Fermer la notification');
    fireEvent.click(closeBtn);

    expect(screen.queryByText('Une erreur est survenue.')).not.toBeInTheDocument();
  });

  it('throws an error if useToast is called outside of ToastProvider', () => {
    const BadComponent = () => {
      useToast();
      return null;
    };

    // Suppress console.error from React boundary
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});
    expect(() => render(<BadComponent />)).toThrow('useToast must be used within a ToastProvider');
    spy.mockRestore();
  });
});
