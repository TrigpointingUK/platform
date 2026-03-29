import { useEffect } from "react";

/**
 * Hook to set a <link rel="canonical"> tag for the current page.
 * Helps search engines identify the preferred URL when multiple
 * paths serve equivalent content (e.g. /trig/1727 vs /trigs/1727).
 *
 * @param path - The canonical path (e.g. "/trigs/1727"). Pass null/undefined to skip.
 */
export function useCanonical(path: string | null | undefined) {
  useEffect(() => {
    if (!path) return;

    const href = `${window.location.origin}${path}`;
    let link = document.querySelector<HTMLLinkElement>('link[rel="canonical"]');
    if (!link) {
      link = document.createElement("link");
      link.setAttribute("rel", "canonical");
      document.head.appendChild(link);
    }
    link.setAttribute("href", href);

    return () => {
      link?.remove();
    };
  }, [path]);
}
