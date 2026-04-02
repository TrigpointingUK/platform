/**
 * Returns the canonical origin URL based on the current hostname.
 */
export function getCanonicalOrigin(): string {
  const host = window.location.hostname;
  if (host === "trigpointing.me" || host.endsWith(".trigpointing.me")) {
    return "https://trigpointing.me";
  }
  return "https://trigpointing.uk";
}
