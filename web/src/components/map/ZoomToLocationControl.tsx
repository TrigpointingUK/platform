import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { useMap } from "react-leaflet";
import { Control, DomEvent, latLng, point, type Map as LeafletMap } from "leaflet";
import { Crosshair } from "lucide-react";

interface ZoomToLocationControlProps {
  /** Known device position, used straight away instead of asking again */
  location?: { lat: number; lon: number } | null;
  /** Roughly how wide the map should be once zoomed in, in metres */
  widthMetres?: number;
  /** Called first thing on a tap, e.g. to ask for compass permission, which
   *  browsers only allow directly from a user gesture */
  onActivate?: () => void;
}

/**
 * The integer zoom (Leaflet snaps to whole levels) at which the map is
 * closest to `widthMetres` across. Measured through the map's own CRS, so it
 * works for the OS layers' projection as well as Web Mercator.
 */
function zoomForWidth(map: LeafletMap, lat: number, lon: number, widthMetres: number): number {
  const centre = latLng(lat, lon);
  const halfWidth = map.getSize().x / 2;
  let best = map.getZoom();
  let bestError = Infinity;
  for (let zoom = map.getMinZoom(); zoom <= map.getMaxZoom(); zoom++) {
    const p = map.project(centre, zoom);
    const west = map.unproject(p.subtract(point(halfWidth, 0)), zoom);
    const east = map.unproject(p.add(point(halfWidth, 0)), zoom);
    const error = Math.abs(Math.log(map.distance(west, east) / widthMetres));
    if (error < bestError) {
      best = zoom;
      bestError = error;
    }
  }
  return best;
}

/**
 * Crosshair button under the zoom buttons that zooms right in on the user's
 * current location.
 */
export default function ZoomToLocationControl({
  location,
  widthMetres = 2000,
  onActivate,
}: ZoomToLocationControlProps) {
  const map = useMap();
  const [container, setContainer] = useState<HTMLElement | null>(null);
  const [isLocating, setIsLocating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // A Leaflet control in the top-left corner, so it stacks under the zoom
  // buttons; React renders into it through a portal
  useEffect(() => {
    const control = new Control({ position: "topleft" });
    control.onAdd = () => {
      const div = document.createElement("div");
      div.className = "leaflet-bar leaflet-control";
      DomEvent.disableClickPropagation(div);
      return div;
    };
    control.addTo(map);
    // eslint-disable-next-line react-hooks/set-state-in-effect -- Portal target only exists once Leaflet has added the control
    setContainer(control.getContainer() ?? null);
    return () => {
      control.remove();
    };
  }, [map]);

  useEffect(() => {
    if (!error) return;
    const timer = setTimeout(() => setError(null), 3000);
    return () => clearTimeout(timer);
  }, [error]);

  const zoomTo = (lat: number, lon: number) => {
    map.setView([lat, lon], zoomForWidth(map, lat, lon, widthMetres));
  };

  const handleClick = (e: React.MouseEvent) => {
    e.preventDefault();
    onActivate?.();
    if (isLocating) return;
    if (location) {
      zoomTo(location.lat, location.lon);
      return;
    }
    if (!navigator.geolocation) {
      setError("Location not supported");
      return;
    }
    setIsLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setIsLocating(false);
        zoomTo(pos.coords.latitude, pos.coords.longitude);
      },
      (err) => {
        setIsLocating(false);
        setError(err.code === err.PERMISSION_DENIED ? "Location permission denied" : "Location unavailable");
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 60 * 1000 },
    );
  };

  if (!container) return null;

  return createPortal(
    <>
      {/* An <a>, like Leaflet's own zoom buttons, so it picks up their styling */}
      <a
        href="#"
        role="button"
        title="Zoom to my location"
        aria-label="Zoom to my location"
        aria-disabled={isLocating}
        onClick={handleClick}
        className="flex! items-center justify-center"
      >
        <Crosshair className={`w-4 h-4 ${isLocating ? "animate-pulse" : ""}`} />
      </a>
      {error && (
        <div className="absolute left-full top-0 ml-2 px-2 py-1 rounded text-xs whitespace-nowrap bg-red-100 dark:bg-red-900/60 border border-red-300 dark:border-red-700 text-red-700 dark:text-red-300">
          {error}
        </div>
      )}
    </>,
    container,
  );
}
