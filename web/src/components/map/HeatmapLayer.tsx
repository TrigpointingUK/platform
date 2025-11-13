import { useEffect } from "react";
import { useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet.heat";

interface TrigPoint {
  wgs_lat: string | number;
  wgs_long: string | number;
}

interface HeatmapLayerProps {
  trigpoints: TrigPoint[];
}

/**
 * Heatmap layer for displaying trigpoint density
 * 
 * Used when there are too many trigpoints to render as individual markers.
 */
export default function HeatmapLayer({
  trigpoints,
}: HeatmapLayerProps) {
  const map = useMap();
  
  useEffect(() => {
    if (!trigpoints || trigpoints.length === 0) {
      console.log('HeatmapLayer: No trigpoints to display');
      return;
    }
    
    console.log(`HeatmapLayer: Rendering ${trigpoints.length} trigpoints`);
    
    // Convert trigpoints to heatmap points [lat, lng, intensity]
    // Use logarithmic scaling for better representation of sparse and dense areas
    const heatmapPoints: [number, number, number][] = trigpoints.map((trig) => {
      const lat = typeof trig.wgs_lat === 'string' ? parseFloat(trig.wgs_lat) : trig.wgs_lat;
      const lng = typeof trig.wgs_long === 'string' ? parseFloat(trig.wgs_long) : trig.wgs_long;
      // Use constant intensity - logarithmic scaling happens via max parameter
      return [lat, lng, 1.0];
    });
    
    console.log(`HeatmapLayer: Created ${heatmapPoints.length} heatmap points`);
    
    // Verify leaflet.heat is available
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    if (!(L as any).heatLayer) {
      console.error('HeatmapLayer: leaflet.heat plugin not loaded!');
      return;
    }
    
    // Create heatmap layer with tuned parameters
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const heatLayer = (L as any).heatLayer(heatmapPoints, {
      // Smaller radius for better definition of coastlines and boundaries
      radius: 15,
      // Less blur for more granular detail
      blur: 10,
      maxZoom: 17,
      // Higher max value creates logarithmic-like effect - dense areas don't dominate
      max: 3.0,
      // Lower minimum opacity so sparse areas still show
      minOpacity: 0.2,
      // More subtle, cooler gradient - less jarring transition
      gradient: {
        0.0: 'rgba(0, 0, 180, 0)',      // Transparent blue
        0.2: 'rgba(0, 100, 255, 0.3)',  // Light blue
        0.4: 'rgba(0, 180, 180, 0.5)',  // Cyan
        0.6: 'rgba(100, 200, 100, 0.6)', // Light green
        0.8: 'rgba(255, 200, 0, 0.7)',  // Amber
        1.0: 'rgba(255, 100, 0, 0.8)',  // Orange (not aggressive red)
      },
    });
    
    console.log('HeatmapLayer: Adding layer to map');
    
    // Add to map
    heatLayer.addTo(map);
    
    // Cleanup
    return () => {
      console.log('HeatmapLayer: Removing layer from map');
      map.removeLayer(heatLayer);
    };
  }, [map, trigpoints]);
  
  return null;
}

