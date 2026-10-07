import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { Button } from '../components/common/Button';

describe('Button Component', () => {
  it('renders children correctly', () => {
    render(<Button>Cliquez ici</Button>);
    expect(screen.getByRole('button', { name: /Cliquez ici/i })).toBeInTheDocument();
  });

  it('handles click events', () => {
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>Action</Button>);
    fireEvent.click(screen.getByRole('button', { name: /Action/i }));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('renders loading state and disables button', () => {
    const handleClick = vi.fn();
    render(<Button isLoading onClick={handleClick}>Action</Button>);
    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
    expect(screen.getByText('Chargement...')).toBeInTheDocument();
    fireEvent.click(button);
    expect(handleClick).not.toHaveBeenCalled();
  });

  it('applies accessible high-contrast primary variant', () => {
    render(<Button variant="primary">Approuver</Button>);
    const button = screen.getByRole('button', { name: /Approuver/i });
    expect(button).toHaveClass('bg-sky-700');
  });

  it('applies accessible high-contrast danger variant', () => {
    render(<Button variant="danger">Supprimer</Button>);
    const button = screen.getByRole('button', { name: /Supprimer/i });
    expect(button).toHaveClass('bg-rose-700');
  });

  it('meets minimum touch target size (>= 44px)', () => {
    render(<Button size="md">Test</Button>);
    const button = screen.getByRole('button');
    expect(button).toHaveClass('min-h-[44px]');
    expect(button).toHaveClass('min-w-[44px]');
  });
});
