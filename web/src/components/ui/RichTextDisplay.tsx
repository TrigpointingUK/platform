import { useMemo } from "react";

interface RichTextDisplayProps {
  html: string;
  className?: string;
}

/**
 * Sanitise HTML by removing potentially dangerous elements and attributes.
 * Allows: p, strong, em, a (with href), span (with style for colour)
 */
function sanitiseHtml(html: string): string {
  // Create a temporary DOM element to parse the HTML
  const doc = new DOMParser().parseFromString(html, "text/html");

  // Allowed tags
  const allowedTags = new Set([
    "p",
    "strong",
    "em",
    "b",
    "i",
    "a",
    "span",
    "br",
  ]);

  // Allowed attributes per tag
  const allowedAttrs: Record<string, Set<string>> = {
    a: new Set(["href", "target", "rel", "class"]),
    span: new Set(["style", "class"]),
    p: new Set(["class"]),
    strong: new Set(["class"]),
    em: new Set(["class"]),
    b: new Set(["class"]),
    i: new Set(["class"]),
    br: new Set([]),
  };

  // Recursively sanitise nodes
  function sanitiseNode(node: Node): Node | null {
    if (node.nodeType === Node.TEXT_NODE) {
      return node.cloneNode(true);
    }

    if (node.nodeType !== Node.ELEMENT_NODE) {
      return null;
    }

    const element = node as Element;
    const tagName = element.tagName.toLowerCase();

    // Remove disallowed tags but keep their content
    if (!allowedTags.has(tagName)) {
      const fragment = document.createDocumentFragment();
      for (const child of Array.from(element.childNodes)) {
        const sanitisedChild = sanitiseNode(child);
        if (sanitisedChild) {
          fragment.appendChild(sanitisedChild);
        }
      }
      return fragment;
    }

    // Create clean element
    const cleanElement = document.createElement(tagName);

    // Copy allowed attributes
    const allowedForTag = allowedAttrs[tagName] || new Set();
    for (const attr of Array.from(element.attributes)) {
      if (allowedForTag.has(attr.name)) {
        // Special handling for style attribute - only allow color and font-size
        if (attr.name === "style") {
          const styles: string[] = [];
          const colorMatch = attr.value.match(/color:\s*([^;]+)/i);
          if (colorMatch) {
            styles.push(`color: ${colorMatch[1]}`);
          }
          const fontSizeMatch = attr.value.match(/font-size:\s*([^;]+)/i);
          if (fontSizeMatch) {
            styles.push(`font-size: ${fontSizeMatch[1]}`);
          }
          if (styles.length > 0) {
            cleanElement.setAttribute("style", styles.join("; "));
          }
        }
        // Special handling for href - ensure it's a safe URL
        else if (attr.name === "href") {
          const href = attr.value.trim();
          // Only allow http, https, and mailto URLs
          if (
            href.startsWith("http://") ||
            href.startsWith("https://") ||
            href.startsWith("mailto:")
          ) {
            cleanElement.setAttribute("href", href);
            // Ensure external links open safely
            cleanElement.setAttribute("target", "_blank");
            cleanElement.setAttribute("rel", "noopener noreferrer");
          }
        } else {
          cleanElement.setAttribute(attr.name, attr.value);
        }
      }
    }

    // Recursively sanitise children
    for (const child of Array.from(element.childNodes)) {
      const sanitisedChild = sanitiseNode(child);
      if (sanitisedChild) {
        cleanElement.appendChild(sanitisedChild);
      }
    }

    return cleanElement;
  }

  // Sanitise the body content
  const fragment = document.createDocumentFragment();
  for (const child of Array.from(doc.body.childNodes)) {
    const sanitisedChild = sanitiseNode(child);
    if (sanitisedChild) {
      fragment.appendChild(sanitisedChild);
    }
  }

  // Convert back to HTML string
  const tempDiv = document.createElement("div");
  tempDiv.appendChild(fragment);
  return tempDiv.innerHTML;
}

/**
 * Display sanitised HTML content from the rich text editor.
 * Safely renders user-provided HTML with only allowed tags and attributes.
 */
export default function RichTextDisplay({
  html,
  className = "",
}: RichTextDisplayProps) {
  const sanitisedHtml = useMemo(() => sanitiseHtml(html), [html]);

  if (!html || html.trim() === "" || html === "<p></p>") {
    return null;
  }

  return (
    <div
      className={`prose prose-sm max-w-none ${className}`}
      dangerouslySetInnerHTML={{ __html: sanitisedHtml }}
    />
  );
}


