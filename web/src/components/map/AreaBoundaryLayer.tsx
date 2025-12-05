import { useEffect } from "react";
import { useMap } from "react-leaflet";
import L from "leaflet";
import type { GeoJSONGeometry } from "../../hooks/useAreaBoundary";

interface AreaBoundaryLayerProps {
  boundary: GeoJSONGeometry;
  name: string;
  areaTypeName: string;
  fitBounds?: boolean;
}

/**
 * Renders an area boundary polygon on the map.
 * 
 * Uses Leaflet's GeoJSON layer to draw the boundary with a styled stroke.
 */
export default function AreaBoundaryLayer({
  boundary,
  name,
  areaTypeName,
  fitBounds = true,
}: AreaBoundaryLayerProps) {
  const map = useMap();

  useEffect(() => {
    if (!boundary) {
      return;
    }

    // Create a GeoJSON feature from the boundary geometry
    const feature: GeoJSON.Feature = {
      type: "Feature",
      properties: {
        name,
        areaTypeName,
      },
      geometry: boundary as GeoJSON.Geometry,
    };

    // Create GeoJSON layer with styling
    const geoJsonLayer = L.geoJSON(feature, {
      style: {
        color: "#2563eb", // Blue-600
        weight: 3,
        opacity: 0.8,
        fillColor: "#3b82f6", // Blue-500
        fillOpacity: 0.1,
        dashArray: "5, 5", // Dashed line for boundary
      },
    });

    // Add tooltip with area name
    geoJsonLayer.bindTooltip(`${areaTypeName}: ${name}`, {
      permanent: false,
      direction: "center",
      className: "area-boundary-tooltip",
    });

    // Add to map
    geoJsonLayer.addTo(map);

    // Fit map bounds to show the entire boundary
    if (fitBounds) {
      const bounds = geoJsonLayer.getBounds();
      if (bounds.isValid()) {
        map.fitBounds(bounds, {
          padding: [50, 50],
          maxZoom: 12,
        });
      }
    }

    // Cleanup
    return () => {
      map.removeLayer(geoJsonLayer);
    };
  }, [map, boundary, name, areaTypeName, fitBounds]);

  return null;
}
