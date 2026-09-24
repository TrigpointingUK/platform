/**
 * TrigsV2Map - map view of every trigpoint matching the Trigs v2 filters.
 *
 * Plots the whole filtered set (from /trigs/points), not just the pages the
 * list has loaded. Like the main map, it only renders markers inside the
 * viewport and switches to a heatmap when too many would be visible.
 */

import { useEffect, useMemo, useState } from "react";
import { useMap } from "react-leaflet";
import { latLngBounds } from "leaflet";
import BaseMap from "../map/BaseMap";
import TrigMarker from "../map/TrigMarker";
import HeatmapLayer from "../map/HeatmapLayer";
import AddToListButton from "../lists/AddToListButton";
import type { MapBounds, TrigData } from "../map/types";
import {
  calculateProjectionZoom,
  getPreferredTileLayer,
  getTileLayer,
  MAP_CONFIG,
} from "../../lib/mapConfig";

// Above this many markers in view, show a density heatmap instead
const MAX_VISIBLE_MARKERS = 1000;

function ViewportTracker({ onChange }: { onChange: (bounds: MapBounds) => void }) {
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
    };
    update();
    map.on("moveend", update);
    return () => {
      map.off("moveend", update);
    };
  }, [map, onChange]);

  return null;
}

// Rough box around the British Isles and Channel Islands. Trigs outside it
// (e.g. with missing 0,0 coordinates) are ignored when fitting the view, so a
// few bad positions can't drag the map off the UK.
const FIT_REGION = { south: 49, north: 61.5, west: -11, east: 2.5 };

/** Zoom to fit the trigpoints whenever the filtered set changes. */
function FitToTrigs({ trigs }: { trigs: TrigData[] }) {
  const map = useMap();

  useEffect(() => {
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
  }, [map, trigs]);

  return null;
}

export interface TrigsV2MapProps {
  trigs: TrigData[];
  isLoading: boolean;
  error: Error | null;
  truncated: boolean;
  showListActions: boolean;
}

export function TrigsV2Map({
  trigs,
  isLoading,
  error,
  truncated,
  showListActions,
}: TrigsV2MapProps) {
  const [tileLayerId] = useState(getPreferredTileLayer);
  const [bounds, setBounds] = useState<MapBounds | null>(null);

  const initialZoom = useMemo(() => {
    const layer = getTileLayer(tileLayerId);
    return calculateProjectionZoom(
      MAP_CONFIG.defaultZoom,
      "EPSG:3857",
      layer.crs || "EPSG:3857",
      layer,
    );
  }, [tileLayerId]);

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
      <div className="mb-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-gray-600 dark:text-gray-400">
        {isLoading ? (
          <span>Loading map…</span>
        ) : (
          <span>
            <strong>{trigs.length.toLocaleString("en-GB")}</strong> trigpoints on the map
          </span>
        )}
        {showHeatmap && (
          <span className="text-xs text-gray-500 dark:text-gray-400">
            Showing density - zoom in to see individual trigpoints
          </span>
        )}
      </div>

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
          center={[MAP_CONFIG.defaultCenter.lat, MAP_CONFIG.defaultCenter.lng]}
          zoom={initialZoom}
          height="70vh"
          tileLayerId={tileLayerId}
        >
          <ViewportTracker onChange={setBounds} />
          <FitToTrigs trigs={trigs} />
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
        </BaseMap>
      </div>
    </div>
  );
}

export default TrigsV2Map;
