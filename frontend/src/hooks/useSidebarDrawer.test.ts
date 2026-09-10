import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, afterEach, vi } from 'vitest';
import { useSidebarDrawer } from './useSidebarDrawer';

type MediaListener = (event: MediaQueryListEvent) => void;

function mockMatchMedia(matches: boolean) {
  const listeners = new Set<MediaListener>();
  const mql = {
    matches,
    media: '(min-width: 768px)',
    onchange: null,
    addEventListener: (_: string, listener: MediaListener) => {
      listeners.add(listener);
    },
    removeEventListener: (_: string, listener: MediaListener) => {
      listeners.delete(listener);
    },
    addListener: (listener: MediaListener) => listeners.add(listener),
    removeListener: (listener: MediaListener) => listeners.delete(listener),
    dispatchEvent: () => true,
    _setMatches(next: boolean) {
      mql.matches = next;
      listeners.forEach((listener) => listener({ matches: next } as MediaQueryListEvent));
    },
  };
  vi.stubGlobal(
    'matchMedia',
    vi.fn().mockImplementation(() => mql)
  );
  return mql;
}

describe('useSidebarDrawer', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('starts closed on mobile and toggles open/close', () => {
    mockMatchMedia(false);
    const { result } = renderHook(() => useSidebarDrawer());

    expect(result.current.isDesktop).toBe(false);
    expect(result.current.isOpen).toBe(false);

    act(() => result.current.open());
    expect(result.current.isOpen).toBe(true);

    act(() => result.current.close());
    expect(result.current.isOpen).toBe(false);

    act(() => result.current.toggle());
    expect(result.current.isOpen).toBe(true);
  });

  it('starts open on desktop and close is a no-op', () => {
    mockMatchMedia(true);
    const { result } = renderHook(() => useSidebarDrawer());

    expect(result.current.isDesktop).toBe(true);
    expect(result.current.isOpen).toBe(true);

    act(() => result.current.close());
    expect(result.current.isOpen).toBe(true);
  });

  it('syncs when viewport crosses the md breakpoint', () => {
    const mql = mockMatchMedia(false);
    const { result } = renderHook(() => useSidebarDrawer());
    expect(result.current.isOpen).toBe(false);

    act(() => mql._setMatches(true));
    expect(result.current.isDesktop).toBe(true);
    expect(result.current.isOpen).toBe(true);

    act(() => mql._setMatches(false));
    expect(result.current.isDesktop).toBe(false);
    expect(result.current.isOpen).toBe(false);
  });
});
