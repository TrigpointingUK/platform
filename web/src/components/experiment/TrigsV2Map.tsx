/**
 * TrigsV2Map - map view of every trigpoint matching the Trigs v2 filters.
 *
 * Plots the whole filtered set (from /trigs/points), not just the pages the
 * list has loaded. Like the main map, it only renders markers inside the
 * viewport and switches to a heatmap when too many would be visible.
 */

import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState, type MutableRefObject } from "react";
import { CircleMarker, Marker, Pane, Tooltip, useMap } from "react-leaflet";
import { divIcon, latLngBounds, type LatLngBounds, type Map as LeafletMap } from "leaflet";
import AreaBoundaryLayer from "../map/AreaBoundaryLayer";
import BaseMap from "../map/BaseMap";
import TrigMarker from "../map/TrigMarker";
import ViewCycleControl, { type MapFocus } from "../map/ViewCycleControl";
import CompassWedge from "../map/CompassWedge";
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
import { useCompassHeading } from "../../hooks/useCompassHeading";
import { useDefaultListTrigIds } from "../../hooks/useTrigLists";

// Above this many markers in view, show a density heatmap instead
const MAX_VISIBLE_MARKERS = 1000;

// Pin marking the search centre: lucide's MapPin, as on the Centre on chip,
// filled yellow to stand out from the trigs. Drawn in the marker pane, so it
// sits on top of the blue current-location circle when they coincide.
const CENTRE_ICON = divIcon({
  className: "",
  html: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="28" height="28"
    fill="#facc15" stroke="#854d0e" stroke-width="1.5" stroke-linejoin="round">
    <path d="M20 10c0 4.993-5.539 10.193-7.399 11.799a1 1 0 0 1-1.202 0C9.539 20.193 4 14.993 4 10a8 8 0 0 1 16 0"/>
    <circle cx="12" cy="10" r="3" fill="#fff"/>
  </svg>`,
  iconSize: [28, 28],
  // The pin's tip, and just above its head
  iconAnchor: [14, 26],
  tooltipAnchor: [0, -22],
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

// Where every trig in FIT_REGION lies (measured Sept 2026, rounded outwards).
// The map opens fitted to this, so it's already where the unfiltered trigs
// will fit it when they load, rather than jumping.
const UK_TRIG_EXTENT = latLngBounds([49.867, -10.56], [60.856, 1.754]);

const FIT_OPTIONS = { padding: [24, 24] as [number, number], maxZoom: 13 };

// Added to a control while an open popup overlaps it
const OVERLAPPED_CLASSES = ["opacity-0", "pointer-events-none"];

/**
 * Hide map controls while an open popup overlaps them. The controls sit above
 * all of Leaflet's panes (popups can't be raised over them without lifting
 * the whole map), so they get out of the way instead.
 */
function PopupOverlapWatcher({
  getTargets,
}: {
  getTargets: (map: LeafletMap) => (HTMLElement | null | undefined)[];
}) {
  const map = useMap();

  useEffect(() => {
    let frame = 0;
    let open = false;
    const check = () => {
      cancelAnimationFrame(frame);
      // After Leaflet has positioned (and auto-panned) the popup
      frame = requestAnimationFrame(() => {
        const popup = open ? map.getContainer().querySelector(".leaflet-popup:last-of-type") : null;
        const a = popup?.getBoundingClientRect();
        for (const target of getTargets(map)) {
          if (!target) continue;
          const b = target.getBoundingClientRect();
          const overlapping =
            !!a && a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top;
          for (const cls of OVERLAPPED_CLASSES) target.classList.toggle(cls, overlapping);
        }
      });
    };
    // A closing popup lingers in the DOM while it fades out, so track
    // whether one is open rather than trusting the DOM alone
    const opened = () => {
      open = true;
      check();
    };
    const closed = () => {
      open = false;
      check();
    };
    map.on("popupopen", opened);
    map.on("popupclose", closed);
    map.on("move zoomend", check);
    return () => {
      cancelAnimationFrame(frame);
      map.off("popupopen", opened);
      map.off("popupclose", closed);
      map.off("move zoomend", check);
    };
  }, [map, getTargets]);

  return null;
}

/** Bounds of the trigs inside FIT_REGION, or null if there are none */
function trigBounds(trigs: TrigData[]): LatLngBounds | null {
  const points = trigs
    .map((t) => [Number(t.wgs_lat), Number(t.wgs_long)] as [number, number])
    .filter(
      ([lat, lon]) =>
        lat >= FIT_REGION.south &&
        lat <= FIT_REGION.north &&
        lon >= FIT_REGION.west &&
        lon <= FIT_REGION.east,
    );
  return points.length > 0 ? latLngBounds(points) : null;
}

/**
 * Zoom to fit the trigpoints when they first load, and again once the trigs
 * for the latest filters have loaded after `fitKey` changes. Other filter
 * changes leave the view alone. `fittedRef` lives outside the map, so a
 * remount (e.g. switching to a layer with a different projection) keeps the
 * user's view rather than fitting again.
 */
function FitToTrigs({
  bounds,
  isLoading,
  fitKey,
  fittedRef,
  onFit,
}: {
  bounds: LatLngBounds | null;
  isLoading: boolean;
  fitKey: string;
  fittedRef: MutableRefObject<string | null>;
  onFit: () => void;
}) {
  const map = useMap();

  useEffect(() => {
    // Not the trigs for the latest filters yet
    if (isLoading || fittedRef.current === fitKey) return;
    fittedRef.current = fitKey;
    if (!bounds) return;
    map.fitBounds(bounds, FIT_OPTIONS);
    onFit();
  }, [map, bounds, isLoading, fitKey, fittedRef, onFit]);

  return null;
}

/**
 * Pan to the search centre, keeping the zoom, when `centreRequest` changes.
 * `pannedRef` starts at the request the map opened with, so opening the map
 * (or a remount) doesn't pan.
 */
function PanToCentre({
  centre,
  centreRequest,
  pannedRef,
  onPan,
}: {
  centre?: { lat: number; lon: number };
  centreRequest: number;
  pannedRef: MutableRefObject<number>;
  onPan: () => void;
}) {
  const map = useMap();

  useEffect(() => {
    if (pannedRef.current === centreRequest) return;
    pannedRef.current = centreRequest;
    if (!centre) return;
    map.panTo([centre.lat, centre.lon]);
    onPan();
  }, [map, centre, centreRequest, pannedRef, onPan]);

  return null;
}

/**
 * Open the map fitted to the whole UK trig set. The fitted zoom depends on the
 * map's size, so it can't be a fixed starting zoom. Only on first mount - a
 * projection change remounts the map but keeps its view.
 */
function InitialFit({ doneRef }: { doneRef: MutableRefObject<boolean> }) {
  const map = useMap();

  // Before paint, so the default view never shows
  useLayoutEffect(() => {
    if (doneRef.current) return;
    doneRef.current = true;
    map.fitBounds(UK_TRIG_EXTENT, { ...FIT_OPTIONS, animate: false });
  }, [map, doneRef]);

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
  /** Change (e.g. with the area or radius filter) to zoom to fit all the trigs */
  fitKey?: string;
  /** Change to pan to the centre, keeping the zoom */
  centreRequest?: number;
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
  fitKey = "",
  centreRequest = 0,
}: TrigsV2MapProps) {
  const [tileLayerId, setTileLayerId] = useState(getPreferredTileLayer);
  const selectorRef = useRef<HTMLDivElement | null>(null);
  const [bounds, setBounds] = useState<MapBounds | null>(null);
  const fittedRef = useRef<string | null>(null);
  const pannedRef = useRef(centreRequest);
  const initialFitDoneRef = useRef(false);
  // What the map is showing, for the view button. It opens showing all the trigs.
  const [focus, setFocus] = useState<MapFocus>("all");
  const focusAll = useCallback(() => setFocus("all"), []);
  const focusCentre = useCallback(() => setFocus("centre"), []);
  const areaBoundaries = useAreaBoundaries(areaIds);
  const deviceLocation = useWatchedDeviceLocation();
  const compass = useCompassHeading();

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

  // Controls that get out of the way of popups
  const getOverlapTargets = useCallback(
    (map: LeafletMap) => [
      selectorRef.current,
      // The zoom and view buttons, together
      map.getContainer().querySelector<HTMLElement>(".leaflet-top.leaflet-left"),
    ],
    [],
  );

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

  const allBounds = useMemo(() => trigBounds(trigs), [trigs]);

  // Trigs on the user's default list get the highlighted (_h) icons. Only
  // fetched when logged in; toggling the star updates it optimistically.
  const { data: defaultList } = useDefaultListTrigIds();
  const defaultListIds = useMemo(() => new Set(defaultList?.trig_ids ?? []), [defaultList]);

  // Rebuild the markers only when the set of visible trigs changes, not on
  // every pan. Re-rendering a marker refreshes its open popup, whose auto-pan
  // moves the map, which re-rendered the markers again - an endless creep.
  const visibleIds = useMemo(() => visibleTrigs.map((t) => t.id).join(","), [visibleTrigs]);
  const markers = useMemo(() => {
    const ids = new Set(visibleIds.split(","));
    return trigs
      .filter((trig) => ids.has(String(trig.id)))
      .map((trig) => (
        <TrigMarker
          key={trig.id}
          trig={trig}
          colorMode="condition"
          highlighted={defaultListIds.has(trig.id)}
          actions={showListActions ? <AddToListButton trigId={trig.id} /> : undefined}
        />
      ));
  }, [trigs, visibleIds, showListActions, defaultListIds]);

  return (
    <div className="-mx-4 mt-2 lg:mx-4 lg:mt-4">
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
      <div className="relative z-0 lg:rounded-lg overflow-hidden shadow dark:shadow-gray-900/50">
        <BaseMap
          center={startView.center}
          zoom={startView.zoom}
          height="70vh"
          tileLayerId={tileLayerId}
        >
          <ViewportTracker onChange={setBounds} viewRef={viewRef} />
          <PopupOverlapWatcher getTargets={getOverlapTargets} />
          <ViewCycleControl
            focus={focus}
            onFocusChange={setFocus}
            centre={centre}
            location={deviceLocation}
            allBounds={allBounds}
            allFitOptions={FIT_OPTIONS}
            onLocate={compass.requestPermission}
          />
          <InitialFit doneRef={initialFitDoneRef} />
          <FitToTrigs
            bounds={allBounds}
            isLoading={isLoading}
            fitKey={fitKey}
            fittedRef={fittedRef}
            onFit={focusAll}
          />
          <PanToCentre
            centre={centre}
            centreRequest={centreRequest}
            pannedRef={pannedRef}
            onPan={focusCentre}
          />
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
            markers
          )}
          {deviceLocation && compass.heading !== null && (
            <CompassWedge lat={deviceLocation.lat} lon={deviceLocation.lon} heading={compass.heading} />
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
              {centre.name && <Tooltip direction="top">Centre: {centre.name}</Tooltip>}
            </Marker>
          )}
        </BaseMap>

        {/* Above Leaflet's controls (z-index 1000) */}
        <div
          ref={selectorRef}
          className="absolute top-2 right-2 z-[1001] transition-opacity"
        >
          <TilesetSelector value={tileLayerId} onChange={handleTilesetChange} compactOnMobile />
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
