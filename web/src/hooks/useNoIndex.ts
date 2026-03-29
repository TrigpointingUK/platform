import { useEffect } from "react";

/**
 * Hook to add a <meta name="robots" content="noindex"> tag when active.
 * Prevents search engines from indexing error pages (404s, invalid IDs, etc.)
 * that return HTTP 200 due to SPA architecture.
 *
 * @param active - Whether to apply the noindex directive. The tag is added
 *                 when true and removed when false or on unmount.
 */
export function useNoIndex(active: boolean) {
  useEffect(() => {
    if (!active) return;

    const meta = document.createElement("meta");
    meta.setAttribute("name", "robots");
    meta.setAttribute("content", "noindex");
    document.head.appendChild(meta);

    return () => {
      meta.remove();
    };
  }, [active]);
}
