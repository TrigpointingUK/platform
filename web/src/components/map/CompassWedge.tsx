import { useEffect, useRef, useState } from "react";
import { useMap } from "react-leaflet";
import { divIcon, latLng, marker, type Marker } from "leaflet";

interface CompassWedgeProps {
  lat: number;
  lon: number;
  /** Degrees clockwise from true north */
  heading: number;
}

const SIZE = 120;

// A fan pointing up from the centre, fading outwards, in the location blue.
// Rotated about its centre to the heading.
const WEDGE_ICON = divIcon({
  className: "",
  html: `<svg class="compass-wedge" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${SIZE} ${SIZE}"
      width="${SIZE}" height="${SIZE}" style="display:block;transform-origin:50% 50%">
    <defs>
      <radialGradient id="compass-wedge-fade" cx="50%" cy="50%" r="50%">
        <stop offset="0.15" stop-color="#3b82f6" stop-opacity="0.7"/>
        <stop offset="0.9" stop-color="#3b82f6" stop-opacity="0.05"/>
      </radialGradient>
    </defs>
    <path d="M60 60 L33 13.23 A54 54 0 0 1 87 13.23 Z" fill="url(#compass-wedge-fade)"/>
  </svg>`,
  iconSize: [SIZE, SIZE],
  iconAnchor: [SIZE / 2, SIZE / 2],
});

/**
 * Screen angle of true north at a point, in degrees clockwise from up. Zero
 * for Web Mercator, but British National Grid layers (e.g. OS Paper) are drawn
 * grid-north-up, which is a few degrees off true north away from 2°W.
 */
function northOnScreen(map: ReturnType<typeof useMap>, lat: number, lon: number): number {
  const here = map.latLngToLayerPoint(latLng(lat, lon));
  const north = map.latLngToLayerPoint(latLng(lat + 0.01, lon));
  return (Math.atan2(north.x - here.x, here.y - north.y) * 180) / Math.PI;
}

/**
 * Blue fan from the current-location circle showing which way the device is
 * pointing. Not interactive, and beneath the trig markers.
 */
export default function CompassWedge({ lat, lon, heading }: CompassWedgeProps) {
  const map = useMap();
  const markerRef = useRef<Marker | null>(null);
  const [northAngle, setNorthAngle] = useState(0);

  useEffect(() => {
    const m = marker([lat, lon], {
      icon: WEDGE_ICON,
      interactive: false,
      keyboard: false,
      pane: "overlayPane",
    }).addTo(map);
    markerRef.current = m;
    return () => {
      m.remove();
      markerRef.current = null;
    };
    // Created once; position is kept up to date below
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map]);

  useEffect(() => {
    markerRef.current?.setLatLng([lat, lon]);
    const update = () => setNorthAngle(northOnScreen(map, lat, lon));
    update();
    map.on("zoomend", update);
    return () => {
      map.off("zoomend", update);
    };
  }, [map, lat, lon]);

  useEffect(() => {
    const svg = markerRef.current?.getElement()?.querySelector<SVGElement>(".compass-wedge");
    if (svg) svg.style.transform = `rotate(${heading + northAngle}deg)`;
  }, [heading, northAngle]);

  return null;
}
