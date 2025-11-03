import { useState } from "react";

interface GeolocationPosition {
  lat: number;
  lon: number;
}

interface UseDeviceLocationReturn {
  position: GeolocationPosition | null;
  error: string | null;
  isLoading: boolean;
  requestLocation: () => void;
}

export function useDeviceLocation(): UseDeviceLocationReturn {
  const [position, setPosition] = useState<GeolocationPosition | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const requestLocation = () => {
    if (!navigator.geolocation) {
      setError("Geolocation is not supported by your browser");
      return;
    }

    setIsLoading(true);
    setError(null);

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setPosition({
          lat: pos.coords.latitude,
          lon: pos.coords.longitude,
        });
        setIsLoading(false);
      },
      (err) => {
        setError(err.message);
        setIsLoading(false);
      },
      {
        enableHighAccuracy: false,
        timeout: 10000,
        maximumAge: 5 * 60 * 1000, // 5 minutes
      }
    );
  };

  // Optionally auto-request on mount (commented out - user should manually request)
  // useEffect(() => {
  //   requestLocation();
  // }, []);

  return { position, error, isLoading, requestLocation };
}

