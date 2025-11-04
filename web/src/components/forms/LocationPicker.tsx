import { useState } from "react";
import { wgs84ToOSGB, calculateDistance } from "../../lib/coordinates";
import Button from "../ui/Button";
import Spinner from "../ui/Spinner";

interface LocationData {
  eastings: number;
  northings: number;
  gridRef: string;
  accuracy: number;
  latitude: number;
  longitude: number;
}

interface LocationPickerProps {
  onLocationSelected: (data: LocationData) => void;
  maxAccuracy?: number; // Maximum acceptable accuracy in meters
  trigLatitude?: number; // Expected trigpoint latitude for distance checking
  trigLongitude?: number; // Expected trigpoint longitude for distance checking
  maxDistance?: number; // Maximum acceptable distance from trigpoint in meters
}

export default function LocationPicker({
  onLocationSelected,
  maxAccuracy = 10,
  trigLatitude,
  trigLongitude,
  maxDistance = 25,
}: LocationPickerProps) {
  const [isGettingLocation, setIsGettingLocation] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastAttempt, setLastAttempt] = useState<{
    accuracy: number;
    timestamp: number;
  } | null>(null);
  const [pendingLocation, setPendingLocation] = useState<LocationData | null>(null);
  const [distanceFromTrig, setDistanceFromTrig] = useState<number | null>(null);

  const handleGetLocation = () => {
    if (!navigator.geolocation) {
      setError("Geolocation is not supported by your browser");
      return;
    }

    setIsGettingLocation(true);
    setError(null);
    
    const startTime = Date.now();

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude, accuracy } = position.coords;
        const responseTime = Date.now() - startTime;

        console.log('GPS Location acquired:', {
          latitude,
          longitude,
          accuracy: `${accuracy}m`,
          responseTime: `${responseTime}ms`,
          timestamp: new Date(position.timestamp).toISOString(),
        });

        setLastAttempt({
          accuracy,
          timestamp: position.timestamp,
        });

        // Detect IP/WiFi-based location (heuristics)
        const isSuspiciouslyFast = responseTime < 1000; // Less than 1 second
        const isSuspiciouslyAccurate = accuracy < 5 && Math.floor(accuracy) === accuracy; // Whole numbers < 5m
        const isProbablyNotGPS = isSuspiciouslyFast && (accuracy < 10 || isSuspiciouslyAccurate);

        if (isProbablyNotGPS) {
          setError(
            `⚠️ Location source appears to be IP/WiFi-based (not GPS). ` +
            `Response time: ${responseTime}ms, Accuracy: ${accuracy}m. ` +
            `This location may be very inaccurate (could be kilometers off). ` +
            `Please use a device with GPS (smartphone/tablet) or enable location services on this device.`
          );
          setIsGettingLocation(false);
          return;
        }

        // Check if accuracy is acceptable
        if (accuracy > maxAccuracy) {
          setError(
            `Location accuracy is ${Math.round(accuracy)}m, but we need ≤${maxAccuracy}m for precise logging. ` +
            `Please ensure you have a clear view of the sky and try again, or wait for better GPS signal. ` +
            `Note: The accuracy value is the uncertainty radius, not the actual position error.`
          );
          setIsGettingLocation(false);
          return;
        }

        try {
          // Convert WGS84 to OSGB
          const { eastings, northings, gridRef } = wgs84ToOSGB(
            latitude,
            longitude
          );

          console.log('Converted to OSGB:', {
            gridRef,
            eastings,
            northings,
          });

          const locationData = {
            eastings,
            northings,
            gridRef,
            accuracy,
            latitude,
            longitude,
          };

          // Check distance from trigpoint if coordinates provided
          if (trigLatitude !== undefined && trigLongitude !== undefined) {
            const distance = calculateDistance(
              latitude,
              longitude,
              trigLatitude,
              trigLongitude
            );

            console.log('Distance from trigpoint:', {
              distance: `${Math.round(distance)}m`,
              trigLatitude,
              trigLongitude,
              userLatitude: latitude,
              userLongitude: longitude,
            });

            setDistanceFromTrig(distance);

            // If distance is greater than threshold, require confirmation
            if (distance > maxDistance) {
              setPendingLocation(locationData);
              setError(null);
              setIsGettingLocation(false);
              return; // Don't auto-accept, wait for user confirmation
            }
          }

          // Distance is acceptable or no trigpoint coords provided - accept immediately
          onLocationSelected(locationData);
          setError(null);
        } catch (err) {
          console.error('Coordinate conversion failed:', err);
          setError(
            `Failed to convert coordinates: ${err instanceof Error ? err.message : "Unknown error"}`
          );
        } finally {
          setIsGettingLocation(false);
        }
      },
      (error) => {
        setIsGettingLocation(false);
        
        switch (error.code) {
          case error.PERMISSION_DENIED:
            setError(
              "Location permission denied. Please enable location access in your browser settings."
            );
            break;
          case error.POSITION_UNAVAILABLE:
            setError(
              "Location information unavailable. Please check your device settings."
            );
            break;
          case error.TIMEOUT:
            setError(
              "Location request timed out. Please try again."
            );
            break;
          default:
            setError(`Failed to get location: ${error.message}`);
        }
      },
      {
        enableHighAccuracy: true, // Request high accuracy GPS
        timeout: 10000, // 10 second timeout
        maximumAge: 0, // Don't use cached position
      }
    );
  };

  const handleConfirmLocation = () => {
    if (pendingLocation) {
      onLocationSelected(pendingLocation);
      setPendingLocation(null);
      setDistanceFromTrig(null);
      setError(null);
    }
  };

  const handleRejectLocation = () => {
    setPendingLocation(null);
    setDistanceFromTrig(null);
    setError("Location rejected. Please move closer to the trigpoint and try again.");
  };

  return (
    <div className="space-y-3">
      <div className="flex items-start gap-3">
        <Button
          type="button"
          onClick={handleGetLocation}
          disabled={isGettingLocation}
          className="flex-shrink-0"
        >
          {isGettingLocation ? (
            <>
              <Spinner size="sm" />
              <span className="ml-2">Getting Location...</span>
            </>
          ) : (
            <>
              <span className="mr-2">📍</span>
              Use Current Location
            </>
          )}
        </Button>

        {lastAttempt && !error && (
          <div className="flex-1 text-xs text-gray-600 bg-green-50 border border-green-200 rounded px-3 py-2">
            <div className="flex items-center gap-1">
              <svg className="w-4 h-4 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                  clipRule="evenodd"
                />
              </svg>
              <span className="font-semibold">Location acquired</span>
            </div>
            <div className="mt-1 space-y-0.5">
              <div>Accuracy: {Math.round(lastAttempt.accuracy)}m
                {lastAttempt.accuracy <= 5 && " (Excellent)"}
                {lastAttempt.accuracy > 5 && lastAttempt.accuracy <= maxAccuracy && " (Good)"}
              </div>
              <div className="text-gray-500 text-[10px] font-mono">
                Check browser console for full details
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Distance confirmation dialog */}
      {pendingLocation && distanceFromTrig !== null && (
        <div className="text-sm bg-amber-50 border-2 border-amber-400 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <svg 
              className="w-6 h-6 text-amber-600 flex-shrink-0 mt-0.5" 
              fill="currentColor" 
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                clipRule="evenodd"
              />
            </svg>
            <div className="flex-1">
              <div className="font-semibold text-amber-900 mb-2">
                Location is {Math.round(distanceFromTrig)}m from trigpoint
              </div>
              <div className="text-amber-800 mb-3 space-y-1">
                <div>
                  Your GPS position is <strong>{Math.round(distanceFromTrig)} meters</strong> away from 
                  the recorded trigpoint coordinates.
                </div>
                <div className="mt-2">
                  <strong>Please confirm:</strong>
                </div>
                <div>
                  • Are you currently standing at the trigpoint?
                </div>
                <div>
                  • Do you have a good GPS signal (clear sky view)?
                </div>
                <div>
                  • Has the trigpoint been moved from its recorded position?
                </div>
              </div>
              <div className="flex gap-2 mt-3">
                <Button
                  type="button"
                  onClick={handleConfirmLocation}
                  className="bg-amber-600 hover:bg-amber-700"
                >
                  ✓ Confirm Location
                </Button>
                <Button
                  type="button"
                  onClick={handleRejectLocation}
                  className="bg-gray-500 hover:bg-gray-600"
                >
                  ✗ Try Again
                </Button>
              </div>
              <div className="text-xs text-amber-700 mt-3 border-t border-amber-200 pt-2">
                <strong>Note:</strong> Large discrepancies may indicate the trigpoint has been 
                relocated. If you're certain you're at the correct trigpoint with good GPS accuracy, 
                confirm to proceed.
              </div>
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="text-sm bg-amber-50 border border-amber-200 rounded-lg p-3">
          <div className="flex items-start gap-2">
            <svg 
              className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" 
              fill="currentColor" 
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                clipRule="evenodd"
              />
            </svg>
            <div>
              <div className="font-semibold text-amber-800">Location Issue</div>
              <div className="text-amber-700 mt-1">{error}</div>
              {lastAttempt && (
                <div className="text-amber-600 mt-2 text-xs">
                  Last attempt: {Math.round(lastAttempt.accuracy)}m accuracy
                  (need ≤{maxAccuracy}m)
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="text-xs text-gray-500 space-y-1">
        <div className="font-semibold text-gray-700">
          ⚠️ Requires actual GPS device
        </div>
        <div>
          • Desktop/laptop computers typically don't have GPS
        </div>
        <div>
          • Use a smartphone or tablet for accurate location
        </div>
        <div>
          • IP/WiFi-based location can be kilometers off target
        </div>
        <div>
          • GPS accuracy should be {maxAccuracy}m or better
        </div>
      </div>
    </div>
  );
}

