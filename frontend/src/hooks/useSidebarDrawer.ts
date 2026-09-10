import { useCallback, useEffect, useState } from 'react';

const DESKTOP_QUERY = '(min-width: 768px)';

export function useSidebarDrawer() {
  const [isDesktop, setIsDesktop] = useState(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return true;
    return window.matchMedia(DESKTOP_QUERY).matches;
  });
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return;
    const mql = window.matchMedia(DESKTOP_QUERY);
    const onChange = (event: MediaQueryListEvent) => {
      setIsDesktop(event.matches);
      if (!event.matches) {
        setMobileOpen(false);
      }
    };
    setIsDesktop(mql.matches);
    mql.addEventListener('change', onChange);
    return () => mql.removeEventListener('change', onChange);
  }, []);

  const isOpen = isDesktop || mobileOpen;

  const open = useCallback(() => {
    if (!isDesktop) setMobileOpen(true);
  }, [isDesktop]);

  const close = useCallback(() => {
    if (!isDesktop) setMobileOpen(false);
  }, [isDesktop]);

  const toggle = useCallback(() => {
    if (isDesktop) return;
    setMobileOpen((prev) => !prev);
  }, [isDesktop]);

  return { isOpen, isDesktop, open, close, toggle };
}
