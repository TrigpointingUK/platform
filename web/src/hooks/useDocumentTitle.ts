import { useEffect } from "react";

/**
 * Hook to update the document title.
 * Uses useEffect to ensure the title updates when data loads.
 * 
 * @param title - The title to set (without suffix). Pass null/undefined to skip.
 * @param suffix - The suffix to append (default: "TrigpointingUK")
 */
export function useDocumentTitle(title: string | null | undefined, suffix = "TrigpointingUK") {
  useEffect(() => {
    if (title) {
      document.title = `${title} | ${suffix}`;
    }
  }, [title, suffix]);
}

