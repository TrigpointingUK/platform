import { useEffect, useState, useCallback, useRef } from "react";
import { convertCoordinates } from "../../lib/api";
import Spinner from "../ui/Spinner";

interface LinkedCoordinatesProps {
  wgsLat: string;
  wgsLong: string;
  wgsHeight: number;
  osgbEastings: number;
  osgbNorthings: number;
  osgbGridref: string;
  osgbHeight: number;
  onWgsChange: (lat: string, long: string, height: number) => void;
  onOsgbChange: (eastings: number, northings: number, gridref: string, height: number) => void;
}

/**
 * LinkedCoordinates component for editing coordinates in both WGS84 and OSGB36 systems.
 *
 * Edits in one coordinate system are automatically converted to the other using the
 * backend OSTN15/OSGM15 transformation API for sub-centimetre accuracy.
 *
 * Height conversion uses OSGM15:
 * - WGS84 height = ellipsoidal height (above WGS84 ellipsoid)
 * - OSGB height = orthometric height (above ODN/sea level)
 *
 * Focus management:
 * - The field being edited never loses focus during conversion
 * - Only the "other side" of the conversion is updated
 * - Conversions are debounced at 500ms
 */
export default function LinkedCoordinates({
  wgsLat,
  wgsLong,
  wgsHeight,
  osgbEastings,
  osgbNorthings,
  osgbGridref,
  osgbHeight,
  onWgsChange,
  onOsgbChange,
}: LinkedCoordinatesProps) {
  // Local input state (strings for text inputs)
  const [wgsLatInput, setWgsLatInput] = useState(wgsLat);
  const [wgsLongInput, setWgsLongInput] = useState(wgsLong);
  const [wgsHeightInput, setWgsHeightInput] = useState(wgsHeight.toString());
  const [osgbEastingsInput, setOsgbEastingsInput] = useState(osgbEastings.toString());
  const [osgbNorthingsInput, setOsgbNorthingsInput] = useState(osgbNorthings.toString());
  const [osgbGridrefInput, setOsgbGridrefInput] = useState(osgbGridref);
  const [osgbHeightInput, setOsgbHeightInput] = useState(osgbHeight.toString());

  // Track which side is being edited to determine conversion direction
  const [editingSide, setEditingSide] = useState<"wgs" | "osgb" | null>(null);

  // Track the currently focused field to avoid updating it during conversion
  const focusedFieldRef = useRef<string | null>(null);

  // Loading and error states
  const [isConverting, setIsConverting] = useState(false);
  const [conversionError, setConversionError] = useState<string | null>(null);

  // Convert WGS84 to OSGB - only updates OSGB fields
  const convertWgsToOsgb = useCallback(async () => {
    const lat = parseFloat(wgsLatInput);
    const lon = parseFloat(wgsLongInput);
    const height = parseFloat(wgsHeightInput);

    if (isNaN(lat) || isNaN(lon)) return;

    setIsConverting(true);
    setConversionError(null);

    try {
      const result = await convertCoordinates({
        from: "wgs84",
        to: "osgb",
        lat,
        lon,
        height: isNaN(height) ? undefined : height,
      });

      // Update parent WGS values (local inputs are already correct)
      onWgsChange(wgsLatInput, wgsLongInput, isNaN(height) ? 0 : height);

      // Update OSGB fields from conversion result
      const newEastings = result.output.e ?? 0;
      const newNorthings = result.output.n ?? 0;
      const newGridref = result.output.gridref ?? "";
      const newOsgbHeight = result.output.height ?? 0;

      // Only update fields that aren't currently focused
      if (focusedFieldRef.current !== "osgbEastings") {
        setOsgbEastingsInput(newEastings.toString());
      }
      if (focusedFieldRef.current !== "osgbNorthings") {
        setOsgbNorthingsInput(newNorthings.toString());
      }
      setOsgbGridrefInput(newGridref);
      if (focusedFieldRef.current !== "osgbHeight") {
        setOsgbHeightInput(Math.round(newOsgbHeight).toString());
      }

      onOsgbChange(newEastings, newNorthings, newGridref, Math.round(newOsgbHeight));
    } catch (error) {
      console.error("Error converting WGS84 to OSGB:", error);
      setConversionError(error instanceof Error ? error.message : "Conversion failed");
    } finally {
      setIsConverting(false);
    }
  }, [wgsLatInput, wgsLongInput, wgsHeightInput, onWgsChange, onOsgbChange]);

  // Convert OSGB to WGS84 - only updates WGS fields
  const convertOsgbToWgs = useCallback(async () => {
    const eastings = parseInt(osgbEastingsInput);
    const northings = parseInt(osgbNorthingsInput);
    const height = parseFloat(osgbHeightInput);

    if (isNaN(eastings) || isNaN(northings)) return;

    setIsConverting(true);
    setConversionError(null);

    try {
      const result = await convertCoordinates({
        from: "osgb",
        to: "wgs84",
        e: eastings,
        n: northings,
        height: isNaN(height) ? undefined : height,
      });

      // Update gridref from API response
      const gridref = result.input.gridref ?? osgbGridrefInput;
      setOsgbGridrefInput(gridref);

      // Update parent OSGB values
      onOsgbChange(eastings, northings, gridref, isNaN(height) ? 0 : height);

      // Update WGS fields from conversion result
      const newLat = result.output.lat?.toFixed(5) ?? "0";
      const newLon = result.output.lon?.toFixed(5) ?? "0";
      const newWgsHeight = result.output.height ?? 0;

      // Only update fields that aren't currently focused
      if (focusedFieldRef.current !== "wgsLat") {
        setWgsLatInput(newLat);
      }
      if (focusedFieldRef.current !== "wgsLong") {
        setWgsLongInput(newLon);
      }
      if (focusedFieldRef.current !== "wgsHeight") {
        setWgsHeightInput(Math.round(newWgsHeight).toString());
      }

      onWgsChange(newLat, newLon, Math.round(newWgsHeight));
    } catch (error) {
      console.error("Error converting OSGB to WGS84:", error);
      setConversionError(error instanceof Error ? error.message : "Conversion failed");
    } finally {
      setIsConverting(false);
    }
  }, [osgbEastingsInput, osgbNorthingsInput, osgbHeightInput, osgbGridrefInput, onWgsChange, onOsgbChange]);

  // Debounced conversion when WGS values change
  useEffect(() => {
    if (editingSide !== "wgs") return;

    const timer = setTimeout(() => {
      convertWgsToOsgb();
    }, 500);

    return () => clearTimeout(timer);
  }, [wgsLatInput, wgsLongInput, wgsHeightInput, editingSide, convertWgsToOsgb]);

  // Debounced conversion when OSGB values change
  useEffect(() => {
    if (editingSide !== "osgb") return;

    const timer = setTimeout(() => {
      convertOsgbToWgs();
    }, 500);

    return () => clearTimeout(timer);
  }, [osgbEastingsInput, osgbNorthingsInput, osgbHeightInput, editingSide, convertOsgbToWgs]);

  // Track focus for each field
  const handleFocus = (fieldName: string, side: "wgs" | "osgb") => {
    focusedFieldRef.current = fieldName;
    setEditingSide(side);
  };

  const handleBlur = () => {
    focusedFieldRef.current = null;
    // Don't clear editingSide on blur - let the debounce complete
  };

  const inputClassName = "w-full rounded-md border border-gray-300 px-3 py-2 text-gray-800 shadow-sm focus:border-trig-green-500 focus:ring-2 focus:ring-trig-green-400";

  return (
    <div className="space-y-6">
      {/* Conversion error */}
      {conversionError && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded-md text-sm">
          {conversionError}
        </div>
      )}

      {/* WGS84 Section */}
      <div className="border border-gray-300 rounded-md p-4 bg-gray-50 relative">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-medium text-gray-800">
            WGS84 Coordinates
            <span className="text-sm font-normal text-gray-500 ml-2">(GPS)</span>
          </h3>
          {isConverting && editingSide === "osgb" && (
            <div className="flex items-center gap-1 text-xs text-gray-500">
              <Spinner size="sm" />
              <span>updating...</span>
            </div>
          )}
        </div>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Latitude</label>
            <input
              type="text"
              value={wgsLatInput}
              onChange={(e) => setWgsLatInput(e.target.value)}
              onFocus={() => handleFocus("wgsLat", "wgs")}
              onBlur={handleBlur}
              className={inputClassName}
              placeholder="e.g., 52.12345"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Longitude</label>
            <input
              type="text"
              value={wgsLongInput}
              onChange={(e) => setWgsLongInput(e.target.value)}
              onFocus={() => handleFocus("wgsLong", "wgs")}
              onBlur={handleBlur}
              className={inputClassName}
              placeholder="e.g., -2.12345"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Height (m)
              <span className="text-xs text-gray-500 ml-1" title="Height above WGS84 ellipsoid">
                ellipsoidal
              </span>
            </label>
            <input
              type="number"
              value={wgsHeightInput}
              onChange={(e) => setWgsHeightInput(e.target.value)}
              onFocus={() => handleFocus("wgsHeight", "wgs")}
              onBlur={handleBlur}
              className={inputClassName}
              placeholder="e.g., 100"
            />
          </div>
        </div>
      </div>

      {/* OSGB36 Section */}
      <div className="border border-gray-300 rounded-md p-4 bg-gray-50 relative">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-medium text-gray-800">
            OSGB36 Coordinates
            <span className="text-sm font-normal text-gray-500 ml-2">(British National Grid)</span>
          </h3>
          {isConverting && editingSide === "wgs" && (
            <div className="flex items-center gap-1 text-xs text-gray-500">
              <Spinner size="sm" />
              <span>updating...</span>
            </div>
          )}
        </div>
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Eastings</label>
            <input
              type="text"
              value={osgbEastingsInput}
              onChange={(e) => setOsgbEastingsInput(e.target.value)}
              onFocus={() => handleFocus("osgbEastings", "osgb")}
              onBlur={handleBlur}
              className={inputClassName}
              placeholder="e.g., 512345"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Northings</label>
            <input
              type="text"
              value={osgbNorthingsInput}
              onChange={(e) => setOsgbNorthingsInput(e.target.value)}
              onFocus={() => handleFocus("osgbNorthings", "osgb")}
              onBlur={handleBlur}
              className={inputClassName}
              placeholder="e.g., 212345"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Height (m)
              <span className="text-xs text-gray-500 ml-1" title="Height above Ordnance Datum Newlyn (sea level)">
                ODN
              </span>
            </label>
            <input
              type="number"
              value={osgbHeightInput}
              onChange={(e) => setOsgbHeightInput(e.target.value)}
              onFocus={() => handleFocus("osgbHeight", "osgb")}
              onBlur={handleBlur}
              className={inputClassName}
              placeholder="e.g., 55"
            />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Grid Reference</label>
          <input
            type="text"
            value={osgbGridrefInput}
            className={`${inputClassName} bg-gray-100`}
            placeholder="e.g., SO 12345 67890"
            readOnly
          />
          <p className="text-xs text-gray-500 mt-1">
            Grid reference is auto-calculated from eastings/northings using OSTN15
          </p>
        </div>
      </div>
    </div>
  );
}
