import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Input } from '../components/common/Input';
import { Select } from '../components/common/Select';
import { Textarea } from '../components/common/Textarea';

describe('Form Primitives Accessibility & useId Fallback (ANOM-09)', () => {
  it('generates an automatic stable id for Input and links label htmlFor', () => {
    render(<Input label="Nom du projet" error="Champ requis" helperText="Aide contextuelle" />);

    const input = screen.getByLabelText(/Nom du projet/i);
    expect(input).toBeDefined();
    expect(input.id).toBeTruthy();
    expect(input.getAttribute('aria-invalid')).toBe('true');
    expect(input.getAttribute('aria-describedby')).toBe(`${input.id}-error`);

    const label = screen.getByText(/Nom du projet/i);
    expect(label.getAttribute('for')).toBe(input.id);
  });

  it('generates an automatic stable id for Select and links label htmlFor', () => {
    const options = [
      { value: 'opt1', label: 'Option 1' },
      { value: 'opt2', label: 'Option 2' },
    ];
    render(<Select label="Catégorie" options={options} helperText="Sélectionnez une option" />);

    const select = screen.getByLabelText(/Catégorie/i);
    expect(select).toBeDefined();
    expect(select.id).toBeTruthy();
    expect(select.getAttribute('aria-describedby')).toBe(`${select.id}-helper`);

    const label = screen.getByText(/Catégorie/i);
    expect(label.getAttribute('for')).toBe(select.id);
  });

  it('generates an automatic stable id for Textarea and links label htmlFor', () => {
    render(<Textarea label="Description détaillée" />);

    const textarea = screen.getByLabelText(/Description détaillée/i);
    expect(textarea).toBeDefined();
    expect(textarea.id).toBeTruthy();

    const label = screen.getByText(/Description détaillée/i);
    expect(label.getAttribute('for')).toBe(textarea.id);
  });

  it('preserves explicitly supplied id prop on all primitives', () => {
    render(
      <div>
        <Input id="custom-input" label="Custom Input" />
        <Select id="custom-select" label="Custom Select" options={[{ value: '1', label: 'One' }]} />
        <Textarea id="custom-textarea" label="Custom Textarea" />
      </div>
    );

    expect(screen.getByLabelText('Custom Input').id).toBe('custom-input');
    expect(screen.getByLabelText('Custom Select').id).toBe('custom-select');
    expect(screen.getByLabelText('Custom Textarea').id).toBe('custom-textarea');
  });
});
