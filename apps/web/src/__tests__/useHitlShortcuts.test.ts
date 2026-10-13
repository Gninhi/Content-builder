import { describe, it, expect, vi } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useHitlShortcuts } from '../hooks/useHitlShortcuts';

describe('useHitlShortcuts Hook', () => {
  it('triggers onNext when pressing "j"', () => {
    const onNext = vi.fn();
    renderHook(() => useHitlShortcuts({ onNext }));

    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'j' }));
    expect(onNext).toHaveBeenCalledTimes(1);
  });

  it('triggers onPrev when pressing "k"', () => {
    const onPrev = vi.fn();
    renderHook(() => useHitlShortcuts({ onPrev }));

    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k' }));
    expect(onPrev).toHaveBeenCalledTimes(1);
  });

  it('triggers onApprove when pressing "a"', () => {
    const onApprove = vi.fn();
    renderHook(() => useHitlShortcuts({ onApprove }));

    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'a' }));
    expect(onApprove).toHaveBeenCalledTimes(1);
  });

  it('triggers onRewrite when pressing "r"', () => {
    const onRewrite = vi.fn();
    renderHook(() => useHitlShortcuts({ onRewrite }));

    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'r' }));
    expect(onRewrite).toHaveBeenCalledTimes(1);
  });

  it('triggers onReject when pressing "x"', () => {
    const onReject = vi.fn();
    renderHook(() => useHitlShortcuts({ onReject }));

    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'x' }));
    expect(onReject).toHaveBeenCalledTimes(1);
  });

  it('suppresses shortcuts when typing inside an input element', () => {
    const onNext = vi.fn();
    renderHook(() => useHitlShortcuts({ onNext }));

    const input = document.createElement('input');
    document.body.appendChild(input);

    const event = new KeyboardEvent('keydown', { key: 'j', bubbles: true });
    Object.defineProperty(event, 'target', { value: input, enumerable: true });

    window.dispatchEvent(event);
    expect(onNext).not.toHaveBeenCalled();

    document.body.removeChild(input);
  });
});
