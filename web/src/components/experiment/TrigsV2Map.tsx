/**
 * TrigsV2Map - map view of every trigpoint matching the Trigs v2 filters.
 *
 * Plots the whole filtered set (from /trigs/points), not just the pages the
 * list has loaded. Like the main map, it only renders markers inside the
 * viewport and switches to a heatmap when too many would be visible.
 */

import { useCallback, useEffect, useMemo, useRef, useState, type MutableRefObject } from "react";
import { CircleMarker, Marker, Pane, Tooltip, useMap } from "react-leaflet";
import { divIcon, latLngBounds } from "leaflet";
import AreaBoundaryLayer from "../map/AreaBoundaryLayer";
import BaseMap from "../map/BaseMap";
import TrigMarker from "../map/TrigMarker";
import HeatmapLayer from "../map/HeatmapLayer";
import TilesetSelector from "../map/TilesetSelector";
import AddToListButton from "../lists/AddToListButton";
import type { MapBounds, TrigData } from "../map/types";
import {
  calculateProjectionZoom,
  getPreferredTileLayer,
  getTileLayer,
  MAP_CONFIG,
} from "../../lib/mapConfig";
import { useAreaBoundaries } from "../../hooks/useAreaBoundary";
import { useWatchedDeviceLocation } from "../../hooks/useDeviceLocation";

// Above this many markers in view, show a density heatmap instead
const MAX_VISIBLE_MARKERS = 1000;

// Small yellow star marking the search centre. Drawn in the marker pane, so it
// sits on top of the blue current-location circle when they coincide.
const CENTRE_ICON = divIcon({
  className: "",
  html: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="18" height="18">
    <path d="M12 2l2.9 6.9 7.1.6-5.4 4.7 1.6 7.3L12 17.8 5.8 21.5l1.6-7.3L2 9.5l7.1-.6z"
      fill="#facc15" stroke="#854d0e" stroke-width="1.5" stroke-linejoin="round"/>
  </svg>`,
  iconSize: [18, 18],
  iconAnchor: [9, 9],
});

interface MapView {
  center: [number, number];
  zoom: number;
}

function ViewportTracker({
  onChange,
  viewRef,
}: {
  onChange: (bounds: MapBounds) => void;
  viewRef: MutableRefObject<MapView>;
}) {
  const map = useMap();

  useEffect(() => {
    const update = () => {
      const bounds = map.getBounds();
      onChange({
        north: bounds.getNorth(),
        south: bounds.getSouth(),
        east: bounds.getEast(),
        west: bounds.getWest(),
      });
      const center = map.getCenter();
      viewRef.current = { center: [center.lat, center.lng], zoom: map.getZoom() };
    };
    update();
    map.on("moveend", update);
    return () => {
      map.off("moveend", update);
    };
  }, [map, onChange, viewRef]);

  return null;
}

// Rough box around the British Isles and Channel Islands. Trigs outside it
// (e.g. with missing 0,0 coordinates) are ignored when fitting the view, so a
// few bad positions can't drag the map off the UK.
const FIT_REGION = { south: 49, north: 61.5, west: -11, east: 2.5 };

/**
 * Zoom to fit the trigpoints whenever the filtered set changes, or when
 * `fitRequest` changes. `fittedRef` lives outside the map, so a remount (e.g.
 * switching to a layer with a different projection) keeps the user's view
 * rather than fitting again.
 */
function FitToTrigs({
  trigs,
  fitRequest,
  fittedRef,
}: {
  trigs: TrigData[];
  fitRequest: number;
  fittedRef: MutableRefObject<{ trigs: TrigData[]; fitRequest: number } | null>;
}) {
  const map = useMap();

  useEffect(() => {
    if (fittedRef.current?.trigs === trigs && fittedRef.current.fitRequest === fitRequest) return;
    fittedRef.current = { trigs, fitRequest };
    const points = trigs
      .map((t) => [Number(t.wgs_lat), Number(t.wgs_long)] as [number, number])
      .filter(
        ([lat, lon]) =>
          lat >= FIT_REGION.south &&
          lat <= FIT_REGION.north &&
          lon >= FIT_REGION.west &&
          lon <= FIT_REGION.east,
      );
    if (points.length === 0) return;
    map.fitBounds(latLngBounds(points), { padding: [24, 24], maxZoom: 13 });
  }, [map, trigs, fitRequest, fittedRef]);

  return null;
}

export interface TrigsV2MapProps {
  trigs: TrigData[];
  isLoading: boolean;
  error: Error | null;
  truncated: boolean;
  showListActions: boolean;
  /** The search centre, marked with a star */
  centre?: { lat: number; lon: number; name: string };
  /** Areas the trigs are filtered to, outlined on the map */
  areaIds?: number[];
  /** Change to zoom back out to fit all the trigs */
  fitRequest?: number;
}

const NO_AREAS: number[] = [];

export function TrigsV2Map({
  trigs,
  isLoading,
  error,
  truncated,
  showListActions,
  centre,
  areaIds = NO_AREAS,
  fitRequest = 0,
}: TrigsV2MapProps) {
  const [tileLayerId, setTileLayerId] = useState(getPreferredTileLayer);
  const [bounds, setBounds] = useState<MapBounds | null>(null);
  const fittedRef = useRef<{ trigs: TrigData[]; fitRequest: number } | null>(null);
  const areaBoundaries = useAreaBoundaries(areaIds);
  const deviceLocation = useWatchedDeviceLocation();

  // The view the map starts from - only read when it mounts, i.e. first time
  // and whenever a change of projection remounts it
  const [startView, setStartView] = useState<MapView>(() => {
    const layer = getTileLayer(tileLayerId);
    return {
      center: [MAP_CONFIG.defaultCenter.lat, MAP_CONFIG.defaultCenter.lng],
      zoom: calculateProjectionZoom(
        MAP_CONFIG.defaultZoom,
        "EPSG:3857",
        layer.crs || "EPSG:3857",
        layer,
      ),
    };
  });
  const viewRef = useRef<MapView>(startView);

  // Keep the current view across a projection change (zoom levels differ
  // between projections, so convert it)
  const handleTilesetChange = useCallback(
    (newTileLayerId: string) => {
      const currentCrs = getTileLayer(tileLayerId).crs || "EPSG:3857";
      const newLayer = getTileLayer(newTileLayerId);
      const newCrs = newLayer.crs || "EPSG:3857";
      if (currentCrs !== newCrs) {
        setStartView({
          center: viewRef.current.center,
          zoom: calculateProjectionZoom(viewRef.current.zoom, currentCrs, newCrs, newLayer),
        });
      }
      setTileLayerId(newTileLayerId);
    },
    [tileLayerId],
  );

  const visibleTrigs = useMemo(() => {
    if (!bounds) return trigs;
    return trigs.filter((t) => {
      const lat = Number(t.wgs_lat);
      const lon = Number(t.wgs_long);
      return (
        lat >= bounds.south && lat <= bounds.north && lon >= bounds.west && lon <= bounds.east
      );
    });
  }, [trigs, bounds]);

  const showHeatmap = visibleTrigs.length > MAX_VISIBLE_MARKERS;

  return (
    <div className="mx-4 mt-4">
      {truncated && (
        <div className="mb-2 p-2 text-sm rounded bg-amber-50 dark:bg-amber-900/20 text-amber-800 dark:text-amber-200">
          Only the first {trigs.length.toLocaleString("en-GB")} trigpoints are shown - narrow your filters to see the rest.
        </div>
      )}

      {error && (
        <div className="mb-2 p-3 rounded-lg bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300">
          Error loading the map: {error.message}
        </div>
      )}

      {/* relative z-0 contains Leaflet's pane z-indexes so the sticky footer stays on top */}
      <div className="relative z-0 rounded-lg overflow-hidden shadow dark:shadow-gray-900/50">
        <BaseMap
          center={startView.center}
          zoom={startView.zoom}
          height="70vh"
          tileLayerId={tileLayerId}
        >
          <ViewportTracker onChange={setBounds} viewRef={viewRef} />
          <FitToTrigs trigs={trigs} fitRequest={fitRequest} fittedRef={fittedRef} />
          {/* Below the overlay pane (400), so outlines never cover the markers.
              The view fits the trigs, not the outlines. */}
          <Pane name="area-boundaries" style={{ zIndex: 350 }}>
            {areaBoundaries.map((area) => (
              <AreaBoundaryLayer
                key={area.id}
                boundary={area.boundary}
                name={area.name}
                areaTypeName={area.area_type.name}
                fitBounds={false}
                pane="area-boundaries"
              />
            ))}
          </Pane>
          {showHeatmap ? (
            <HeatmapLayer trigpoints={trigs} />
          ) : (
            visibleTrigs.map((trig) => (
              <TrigMarker
                key={trig.id}
                trig={trig}
                colorMode="condition"
                actions={showListActions ? <AddToListButton trigId={trig.id} /> : undefined}
              />
            ))
          )}
          {deviceLocation && (
            // Same blue as the location circle on the popup mini-maps
            <CircleMarker
              center={[deviceLocation.lat, deviceLocation.lon]}
              radius={10}
              pathOptions={{ color: "#2563eb", weight: 2, fillColor: "#3b82f6", fillOpacity: 0.3 }}
            >
              <Tooltip direction="top">Your location</Tooltip>
            </CircleMarker>
          )}
          {centre && (
            <Marker
              position={[centre.lat, centre.lon]}
              icon={CENTRE_ICON}
              zIndexOffset={1000}
              keyboard={false}
            >
              {centre.name && <Tooltip direction="top" offset={[0, -8]}>Centre: {centre.name}</Tooltip>}
            </Marker>
          )}
        </BaseMap>

        {/* Above Leaflet's controls (z-index 1000) */}
        <div className="absolute top-2 right-2 z-[1001]">
          <TilesetSelector value={tileLayerId} onChange={handleTilesetChange} />
        </div>
        {isLoading && (
          <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-[1001] px-3 py-1 rounded-full text-sm bg-white/90 dark:bg-gray-800/90 text-gray-700 dark:text-gray-300 shadow">
            Loading map…
          </div>
        )}
      </div>
    </div>
  );
}

export default TrigsV2Map;
