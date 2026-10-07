import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Badge, StatusBadge } from '../components/common/Badge';

describe('Badge & StatusBadge Components', () => {
  it('renders general Badge with variant styling', () => {
    render(<Badge variant="success">Succès</Badge>);
    const badge = screen.getByText('Succès');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveClass('text-emerald-300');
  });

  it('renders DEGRADED status badge accurately with warning styles', () => {
    render(<StatusBadge status="DEGRADED" />);
    const badge = screen.getByText('Mode Dégradé');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveClass('text-orange-300');
  });

  it('renders PENDING_REVIEW badge', () => {
    render(<StatusBadge status="PENDING_REVIEW" />);
    expect(screen.getByText('À Revoir (HITL)')).toBeInTheDocument();
    expect(screen.getByText('À Revoir (HITL)')).toHaveClass('text-amber-300');
  });

  it('renders PUBLISHED badge with emerald success style', () => {
    render(<StatusBadge status="PUBLISHED" />);
    const badge = screen.getByText('Publié');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveClass('text-emerald-400');
  });

  it('renders FAILED badge with rose danger style', () => {
    render(<StatusBadge status="FAILED" />);
    const badge = screen.getByText('Échec');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveClass('text-rose-300');
  });
});
