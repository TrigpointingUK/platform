import { useState, useEffect } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import { useFloating, flip, shift, offset, autoUpdate, FloatingPortal } from "@floating-ui/react";
import { authenticatedFetch } from "../../lib/api";

interface DownloadButtonProps {
  /** Status IDs to filter by */
  statusIds?: number[];
  /** Area ID to filter by */
  areaId?: number | null;
  /** Centre latitude for distance filter */
  lat?: number | null;
  /** Centre longitude for distance filter */
  lon?: number | null;
  /** Maximum distance in km */
  maxKm?: number;
  /** Include only trigpoints logged by the user */
  onlyFound?: boolean;
  /** Exclude trigpoints already logged by the user */
  excludeFound?: boolean;
  /** Additional CSS classes */
  className?: string;
}

type DownloadFormat = "csv" | "geojson" | "kml" | "kmz" | "gpx";

interface FormatOption {
  value: DownloadFormat;
  label: string;
  description: string;
}

const FORMAT_OPTIONS: FormatOption[] = [
  { value: "csv", label: "CSV", description: "Spreadsheet format" },
  { value: "geojson", label: "GeoJSON", description: "For mapping applications" },
  { value: "kml", label: "KML", description: "Google Earth format" },
  { value: "kmz", label: "KMZ", description: "Google Earth / My Maps (recommended)" },
  { value: "gpx", label: "GPX", description: "GPS device format" },
];

export function DownloadButton({
  statusIds,
  areaId,
  lat,
  lon,
  maxKm,
  onlyFound,
  excludeFound,
  className = "",
}: DownloadButtonProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [includeMyLogs, setIncludeMyLogs] = useState(false);
  const { getAccessTokenSilently } = useAuth0();

  // Floating UI for smart dropdown positioning with automatic flip
  const { refs, floatingStyles } = useFloating({
    open: isOpen,
    placement: "bottom-end",
    middleware: [offset(8), flip(), shift({ padding: 8 })],
    whileElementsMounted: autoUpdate,
  });

  // Close dropdown when clicking outside (check both reference and floating elements)
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      const target = event.target as Node;
      const referenceEl = refs.reference.current;
      const floatingEl = refs.floating.current;
      
      // Check if click is outside both the button and the dropdown
      // referenceEl could be a VirtualElement, so check it's an Element first
      const isOutsideReference = referenceEl && 
        referenceEl instanceof Element && 
        !referenceEl.contains(target);
      const isOutsideFloating = !floatingEl || !floatingEl.contains(target);
      
      if (isOutsideReference && isOutsideFloating) {
        setIsOpen(false);
        setError(null);
      }
    }

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [isOpen, refs.reference, refs.floating]);

  const buildDownloadUrl = (format: DownloadFormat): string => {
    const params = new URLSearchParams();
    params.set("format", format);

    if (statusIds && statusIds.length > 0) {
      params.set("status_ids", statusIds.join(","));
    }
    if (areaId) {
      params.set("area_id", areaId.toString());
    }
    if (lat !== null && lat !== undefined) {
      params.set("lat", lat.toString());
    }
    if (lon !== null && lon !== undefined) {
      params.set("lon", lon.toString());
    }
    if (maxKm) {
      params.set("max_km", maxKm.toString());
    }
    if (onlyFound) {
      params.set("only_found", "true");
    }
    if (excludeFound) {
      params.set("exclude_found", "true");
    }
    if (includeMyLogs) {
      params.set("include_my_logs", "true");
    }

    return `${import.meta.env.VITE_API_BASE}/v1/downloads/trigs?${params.toString()}`;
  };

  const handleDownload = async (format: DownloadFormat) => {
    setIsLoading(true);
    setError(null);

    try {
      const url = buildDownloadUrl(format);

      // Always use authenticated request (downloads require login)
      // authenticatedFetch handles 401 retry automatically
      const response = await authenticatedFetch(
        url,
        {},
        getAccessTokenSilently
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Download failed: ${response.status}`);
      }

      // Get filename from Content-Disposition header or generate one with timestamp
      const contentDisposition = response.headers.get("Content-Disposition");
      const now = new Date();
      const timestamp = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, "0")}${String(now.getDate()).padStart(2, "0")}_${String(now.getHours()).padStart(2, "0")}${String(now.getMinutes()).padStart(2, "0")}${String(now.getSeconds()).padStart(2, "0")}`;
      let filename = `trigpoints_${timestamp}.${format}`;
      if (contentDisposition) {
        const match = contentDisposition.match(/filename="(.+)"/);
        if (match) {
          filename = match[1];
        }
      }

      // Create download
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);

      setIsOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Download failed");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={className}>
      <button
        ref={refs.setReference}
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 rounded-lg shadow-sm transition-colors disabled:opacity-50"
        disabled={isLoading}
      >
        {isLoading ? (
          <>
            <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            Downloading...
          </>
        ) : (
          <>
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Download
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </>
        )}
      </button>

      {isOpen && (
        <FloatingPortal>
          <div
            // floating-ui's setFloating is a stable callback-ref setter, not a ref-value read
            // eslint-disable-next-line react-hooks/refs
            ref={refs.setFloating}
            style={floatingStyles}
            className="w-72 max-w-[calc(100vw-2rem)] bg-white dark:bg-gray-800 rounded-lg shadow-lg dark:shadow-gray-900/50 border border-gray-200 dark:border-gray-600 z-50"
          >
            <div className="p-3 border-b border-gray-100 dark:border-gray-700">
              <h3 className="font-medium text-gray-900 dark:text-gray-100 mb-1">Download Trigpoints</h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Downloads current filtered results
              </p>
            </div>

            {/* Include my logs checkbox */}
            <div className="px-3 py-2 border-b border-gray-100 dark:border-gray-700">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={includeMyLogs}
                  onChange={(e) => setIncludeMyLogs(e.target.checked)}
                  className="rounded border-gray-300 dark:border-gray-600 text-green-600 focus:ring-green-500 dark:bg-gray-700"
                />
                <span className="text-sm text-gray-700 dark:text-gray-200">Include my log data</span>
              </label>
            </div>

            {/* Format options */}
            <div className="py-1">
              {FORMAT_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  onClick={() => handleDownload(option.value)}
                  disabled={isLoading}
                  className="w-full px-3 py-2 text-left hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center justify-between group disabled:opacity-50"
                >
                  <div>
                    <div className="font-medium text-gray-900 dark:text-gray-100 group-hover:text-green-600">
                      {option.label}
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">{option.description}</div>
                  </div>
                  <svg
                    className="w-5 h-5 text-gray-400 dark:text-gray-500 group-hover:text-green-600"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                    />
                  </svg>
                </button>
              ))}
            </div>

            {error && (
              <div className="px-3 py-2 bg-red-50 dark:bg-red-900/30 border-t border-red-100 dark:border-red-800">
                <p className="text-sm text-red-600 dark:text-red-300">{error}</p>
              </div>
            )}
          </div>
        </FloatingPortal>
      )}
    </div>
  );
}

export default DownloadButton;
