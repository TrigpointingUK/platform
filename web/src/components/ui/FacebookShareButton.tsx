interface FacebookShareButtonProps {
  url: string;
  className?: string;
}

function getCanonicalOrigin(): string {
  const host = window.location.hostname;
  if (host === "trigpointing.me" || host.endsWith(".trigpointing.me")) {
    return "https://trigpointing.me";
  }
  return "https://trigpointing.uk";
}

export { getCanonicalOrigin };

export default function FacebookShareButton({
  url,
  className = "",
}: FacebookShareButtonProps) {
  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    const shareUrl = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`;
    window.open(shareUrl, "_blank", "width=600,height=400,noopener,noreferrer");
  };

  return (
    <button
      onClick={handleClick}
      title="Share on Facebook"
      className={`inline-flex items-center justify-center text-gray-400 hover:text-blue-600 dark:text-gray-500 dark:hover:text-blue-400 transition-colors ${className}`}
    >
      <svg
        viewBox="0 0 24 24"
        fill="currentColor"
        className="w-4 h-4"
        aria-hidden="true"
      >
        <path d="M22 12c0-5.523-4.477-10-10-10S2 6.477 2 12c0 4.991 3.657 9.128 8.438 9.878v-6.987h-2.54V12h2.54V9.797c0-2.506 1.492-3.89 3.777-3.89 1.094 0 2.238.195 2.238.195v2.46h-1.26c-1.243 0-1.63.771-1.63 1.562V12h2.773l-.443 2.89h-2.33v6.988C18.343 21.128 22 16.991 22 12z" />
      </svg>
    </button>
  );
}
