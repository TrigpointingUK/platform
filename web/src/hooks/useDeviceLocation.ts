import { useState, useCallback, useEffect } from "react";

interface GeolocationPosition {
  lat: number;
  lon: number;
}

interface UseDeviceLocationOptions {
  onSuccess?: (position: GeolocationPosition) => void;
}

interface UseDeviceLocationReturn {
  position: GeolocationPosition | null;
  error: string | null;
  isLoading: boolean;
  requestLocation: () => void;
}

export function useDeviceLocation(options?: UseDeviceLocationOptions): UseDeviceLocationReturn {
  const [position, setPosition] = useState<GeolocationPosition | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const requestLocation = useCallback(() => {
    if (!navigator.geolocation) {
      setError("Geolocation is not supported by your browser");
      return;
    }

    setIsLoading(true);
    setError(null);

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const newPosition = {
          lat: pos.coords.latitude,
          lon: pos.coords.longitude,
        };
        setPosition(newPosition);
        setIsLoading(false);
        // Call the success callback if provided
        options?.onSuccess?.(newPosition);
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
  }, [options]);

  return { position, error, isLoading, requestLocation };
}

/**
 * Follow the device's position while mounted. Null until there's a fix, and
 * stays null if location is blocked or unavailable.
 */
export function useWatchedDeviceLocation(): GeolocationPosition | null {
  const [position, setPosition] = useState<GeolocationPosition | null>(null);

  useEffect(() => {
    if (!navigator.geolocation) return;
    const watchId = navigator.geolocation.watchPosition(
      (pos) => setPosition({ lat: pos.coords.latitude, lon: pos.coords.longitude }),
      // Blocked or no fix - just don't show it
      () => {},
      { maximumAge: 60 * 1000 },
    );
    return () => navigator.geolocation.clearWatch(watchId);
  }, []);

  return position;
}
