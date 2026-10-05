import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { useMap } from "react-leaflet";
import {
  Control,
  DomEvent,
  latLng,
  point,
  type FitBoundsOptions,
  type LatLngBounds,
  type Map as LeafletMap,
} from "leaflet";
import { Crosshair, MapPin } from "lucide-react";

/** What the map is showing */
export type MapFocus = "centre" | "location" | "all";

const NEXT_FOCUS: Record<MapFocus, MapFocus> = {
  centre: "location",
  location: "all",
  all: "centre",
};

const ZOOM_LABELS: Record<MapFocus, string> = {
  centre: "Zoom to the search centre",
  location: "Zoom to my location",
  all: "Zoom out to all the trigpoints",
};

// Great Britain and Northern Ireland, from the country boundaries in Web
// Mercator, merged, with small islands dropped and simplified for 24x24
const UK_OUTLINE_PATH =
  "M7.8 6.6L8.5 5.4L8.3 3.7L8.9 3.4L9.5 1.6L12.3 1.6L12.1 2.3L11.1 3.3L11.1 4.1L13.7 4.1L14.0 4.6L12.6 8.2" +
  "L14.0 9.2L14.7 11.5L16.4 13.0L17.0 15.6L18.3 15.8L18.9 16.4L18.7 17.8L17.8 19.1L18.5 19.3L18.4 19.8" +
  "L17.9 20.4L16.8 20.8L14.7 20.7L13.0 21.3L12.4 20.8L11.7 21.1L11.3 22.0L10.4 21.6L9.2 22.5L8.5 22.3" +
  "L10.6 19.8L12.1 19.6L10.2 18.6L9.4 18.8L9.0 18.3L10.7 17.2L10.6 16.0L9.8 16.1L10.8 15.0L11.9 14.8" +
  "L12.2 13.6L11.4 12.1L11.5 11.3L9.5 11.7L9.2 11.0L10.0 9.7L9.6 8.8L8.9 9.1L8.4 10.2L8.8 7.4Z" +
  "M5.0 12.2L6.2 10.8L7.4 10.3L8.0 10.4L8.9 12.1L8.0 13.3L7.2 13.2L6.7 12.6L5.9 13.0Z";

function ViewIcon({ view, pulse }: { view: MapFocus; pulse: boolean }) {
  if (view === "centre") {
    // As on the Centre on chip
    return <MapPin className="w-4 h-4" />;
  }
  if (view === "all") {
    return (
      // A size up, as the tall, narrow outline looks small next to the others
      <svg viewBox="0 0 24 24" className="w-5 h-5" fill="currentColor" aria-hidden="true">
        <path d={UK_OUTLINE_PATH} />
      </svg>
    );
  }
  return <Crosshair className={`w-4 h-4 ${pulse ? "animate-pulse" : ""}`} />;
}

interface ViewCycleControlProps {
  /** What the map is showing, which decides where the next click goes */
  focus: MapFocus;
  /** Called once the button has moved the map to its next view */
  onFocusChange: (focus: MapFocus) => void;
  /** The search centre */
  centre?: { lat: number; lon: number };
  /** Known device position, used straight away instead of asking again */
  location?: { lat: number; lon: number } | null;
  /** Everything to show when zooming out */
  allBounds: LatLngBounds | null;
  allFitOptions?: FitBoundsOptions;
  /** Roughly how wide the map should be around the centre, in metres */
  centreWidthMetres?: number;
  /** Roughly how wide the map should be around the device, in metres */
  locationWidthMetres?: number;
  /** Called when zooming to the device, e.g. to ask for compass permission,
   *  which browsers only allow directly from a user gesture */
  onLocate?: () => void;
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
 * Button under the zoom buttons that steps through three views: a medium
 * zoom on the search centre, a close zoom on the device's location, and out
 * to every trigpoint. Its icon shows where the next click goes.
 */
export default function ViewCycleControl({
  focus,
  onFocusChange,
  centre,
  location,
  allBounds,
  allFitOptions,
  centreWidthMetres = 40000,
  locationWidthMetres = 2000,
  onLocate,
}: ViewCycleControlProps) {
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

  const zoomTo = (lat: number, lon: number, widthMetres: number) => {
    map.setView([lat, lon], zoomForWidth(map, lat, lon, widthMetres));
  };

  const zoomToLocation = () => {
    onLocate?.();
    if (location) {
      zoomTo(location.lat, location.lon, locationWidthMetres);
      onFocusChange("location");
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
        zoomTo(pos.coords.latitude, pos.coords.longitude, locationWidthMetres);
        onFocusChange("location");
      },
      (err) => {
        setIsLocating(false);
        setError(err.code === err.PERMISSION_DENIED ? "Location permission denied" : "Location unavailable");
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 60 * 1000 },
    );
  };

  // Skip a view there's nothing to show for (the location is always tried)
  let next = NEXT_FOCUS[focus];
  while ((next === "centre" && !centre) || (next === "all" && !allBounds)) {
    next = NEXT_FOCUS[next];
  }

  const handleClick = (e: React.MouseEvent) => {
    e.preventDefault();
    if (isLocating) return;
    if (next === "centre" && centre) {
      zoomTo(centre.lat, centre.lon, centreWidthMetres);
      onFocusChange("centre");
    } else if (next === "all" && allBounds) {
      map.fitBounds(allBounds, allFitOptions);
      onFocusChange("all");
    } else {
      zoomToLocation();
    }
  };

  if (!container) return null;

  // A pulsing crosshair while waiting for a fix; it moves on once the map is there
  const shown = isLocating ? "location" : next;
  const label = isLocating ? "Finding your location" : ZOOM_LABELS[next];

  return createPortal(
    <>
      {/* An <a>, like Leaflet's own zoom buttons, so it picks up their styling */}
      <a
        href="#"
        role="button"
        title={label}
        aria-label={label}
        aria-disabled={isLocating}
        onClick={handleClick}
        className="flex! items-center justify-center"
      >
        <ViewIcon view={shown} pulse={isLocating} />
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
