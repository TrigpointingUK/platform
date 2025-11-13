import { useState } from "react";
import type { Map as LeafletMap } from "leaflet";
import { Locate } from "lucide-react";

interface LocationButtonProps {
  onLocationFound?: (lat: number, lon: number) => void;
  className?: string;
  map: LeafletMap; // Map instance (required when used outside MapContainer)
}

/**
 * Button to center the map on the user's current location
 * 
 * Requests geolocation permission if needed and handles errors gracefully.
 * For use outside MapContainer - requires map prop.
 * For use inside MapContainer, use LocationButtonInternal instead.
 */
export default function LocationButton({
  onLocationFound,
  className = "",
  map,
}: LocationButtonProps) {
  const [isLocating, setIsLocating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const handleLocate = () => {
    setIsLocating(true);
    setError(null);
    
    if (!navigator.geolocation) {
      setError("Geolocation not supported");
      setIsLocating(false);
      return;
    }
    
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude } = position.coords;
        
        // Center map on user's location with zoom 2 levels out from current
        const currentZoom = map.getZoom();
        const targetZoom = Math.max(currentZoom - 2, map.getMinZoom());
        map.setView([latitude, longitude], targetZoom);
        
        if (onLocationFound) {
          onLocationFound(latitude, longitude);
        }
        
        setIsLocating(false);
      },
      (error) => {
        console.error("Geolocation error:", error);
        
        let errorMessage = "Location unavailable";
        switch (error.code) {
          case error.PERMISSION_DENIED:
            errorMessage = "Location permission denied";
            break;
          case error.POSITION_UNAVAILABLE:
            errorMessage = "Location unavailable";
            break;
          case error.TIMEOUT:
            errorMessage = "Location request timed out";
            break;
        }
        
        setError(errorMessage);
        setIsLocating(false);
        
        // Clear error after 3 seconds
        setTimeout(() => setError(null), 3000);
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0,
      }
    );
  };
  
  return (
    <div className={className}>
      <button
        onClick={handleLocate}
        disabled={isLocating}
        className={`bg-white hover:bg-gray-50 p-2 rounded-lg shadow-md transition-colors ${
          isLocating ? 'opacity-50 cursor-not-allowed' : ''
        }`}
        title="Center on my location"
      >
        <Locate
          size={20}
          className={`text-trig-green-600 ${isLocating ? 'animate-pulse' : ''}`}
        />
      </button>
      
      {error && (
        <div className="absolute top-full mt-2 right-0 bg-red-100 border border-red-300 text-red-700 px-3 py-2 rounded text-xs whitespace-nowrap">
          {error}
        </div>
      )}
    </div>
  );
}

