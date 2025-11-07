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
  intensity?: number;
}

/**
 * Heatmap layer for displaying trigpoint density
 * 
 * Used when there are too many trigpoints to render as individual markers.
 */
export default function HeatmapLayer({
  trigpoints,
  intensity = 0.5,
}: HeatmapLayerProps) {
  const map = useMap();
  
  useEffect(() => {
    if (!trigpoints || trigpoints.length === 0) {
      return;
    }
    
    // Convert trigpoints to heatmap points [lat, lng, intensity]
    const heatmapPoints: [number, number, number][] = trigpoints.map((trig) => {
      const lat = typeof trig.wgs_lat === 'string' ? parseFloat(trig.wgs_lat) : trig.wgs_lat;
      const lng = typeof trig.wgs_long === 'string' ? parseFloat(trig.wgs_long) : trig.wgs_long;
      return [lat, lng, intensity];
    });
    
    // Create heatmap layer
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const heatLayer = (L as any).heatLayer(heatmapPoints, {
      radius: 25,
      blur: 15,
      maxZoom: 17,
      max: 1.0,
      minOpacity: 0.5,
      gradient: {
        0.0: '#0000ff',
        0.3: '#00ffff', 
        0.5: '#00ff00',
        0.7: '#ffff00',
        1.0: '#ff0000',
      },
    });
    
    // Add to map
    heatLayer.addTo(map);
    
    // Cleanup
    return () => {
      map.removeLayer(heatLayer);
    };
  }, [map, trigpoints, intensity]);
  
  return null;
}

