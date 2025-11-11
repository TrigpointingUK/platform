/**
 * Highlights matching text within a string using mark elements
 */
export function highlightText(text: string, query: string): JSX.Element[] {
  if (!query || query.length < 2) {
    return [<span key="0">{text}</span>];
  }

  // Escape special regex characters in the query
  const escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  
  // Create regex for case-insensitive matching
  const regex = new RegExp(`(${escapedQuery})`, "gi");
  
  // Split text by matches
  const parts = text.split(regex);
  
  return parts.map((part, index) => {
    // Check if this part matches the query (case-insensitive)
    if (part.toLowerCase() === query.toLowerCase()) {
      return (
        <mark
          key={index}
          className="bg-yellow-200 px-0.5 rounded font-medium"
        >
          {part}
        </mark>
      );
    }
    return <span key={index}>{part}</span>;
  });
}

