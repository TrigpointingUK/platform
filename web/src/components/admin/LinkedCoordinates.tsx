import { useEffect, useState } from "react";
import { wgs84ToOSGB, osgbToWGS84 } from "../../lib/coordinates";

interface LinkedCoordinatesProps {
  wgsLat: string;
  wgsLong: string;
  osgbEastings: number;
  osgbNorthings: number;
  osgbGridref: string;
  onWgsChange: (lat: string, long: string) => void;
  onOsgbChange: (eastings: number, northings: number, gridref: string) => void;
}

export default function LinkedCoordinates({
  wgsLat,
  wgsLong,
  osgbEastings,
  osgbNorthings,
  osgbGridref,
  onWgsChange,
  onOsgbChange,
}: LinkedCoordinatesProps) {
  const [wgsLatInput, setWgsLatInput] = useState(wgsLat);
  const [wgsLongInput, setWgsLongInput] = useState(wgsLong);
  const [osgbEastingsInput, setOsgbEastingsInput] = useState(osgbEastings.toString());
  const [osgbNorthingsInput, setOsgbNorthingsInput] = useState(osgbNorthings.toString());
  const [osgbGridrefInput, setOsgbGridrefInput] = useState(osgbGridref);
  const [lastEditedField, setLastEditedField] = useState<"wgs" | "osgb" | null>(null);

  // Update local state when props change from parent
  useEffect(() => {
    setWgsLatInput(wgsLat);
    setWgsLongInput(wgsLong);
  }, [wgsLat, wgsLong]);

  useEffect(() => {
    setOsgbEastingsInput(osgbEastings.toString());
    setOsgbNorthingsInput(osgbNorthings.toString());
    setOsgbGridrefInput(osgbGridref);
  }, [osgbEastings, osgbNorthings, osgbGridref]);

  const handleWgsLatChange = (value: string) => {
    setWgsLatInput(value);
    setLastEditedField("wgs");
  };

  const handleWgsLongChange = (value: string) => {
    setWgsLongInput(value);
    setLastEditedField("wgs");
  };

  const handleOsgbEastingsChange = (value: string) => {
    setOsgbEastingsInput(value);
    setLastEditedField("osgb");
  };

  const handleOsgbNorthingsChange = (value: string) => {
    setOsgbNorthingsInput(value);
    setLastEditedField("osgb");
  };

  const handleOsgbGridrefChange = (value: string) => {
    setOsgbGridrefInput(value);
    setLastEditedField("osgb");
  };

  // Debounced conversion when WGS values change
  useEffect(() => {
    if (lastEditedField !== "wgs") return;

    const timer = setTimeout(() => {
      const lat = parseFloat(wgsLatInput);
      const long = parseFloat(wgsLongInput);

      if (!isNaN(lat) && !isNaN(long)) {
        try {
          const osgb = wgs84ToOSGB(lat, long);
          onWgsChange(wgsLatInput, wgsLongInput);
          onOsgbChange(osgb.eastings, osgb.northings, osgb.gridRef);
        } catch (error) {
          console.error("Error converting WGS to OSGB:", error);
        }
      }
    }, 500);

    return () => clearTimeout(timer);
  }, [wgsLatInput, wgsLongInput, lastEditedField, onWgsChange, onOsgbChange]);

  // Debounced conversion when OSGB eastings/northings change
  useEffect(() => {
    if (lastEditedField !== "osgb") return;

    const timer = setTimeout(() => {
      const eastings = parseInt(osgbEastingsInput);
      const northings = parseInt(osgbNorthingsInput);

      if (!isNaN(eastings) && !isNaN(northings)) {
        try {
          const wgs = osgbToWGS84(eastings, northings);
          const osgb = wgs84ToOSGB(wgs.lat, wgs.lon); // Get gridref too
          onOsgbChange(eastings, northings, osgb.gridRef);
          onWgsChange(wgs.lat.toFixed(5), wgs.lon.toFixed(5));
        } catch (error) {
          console.error("Error converting OSGB to WGS:", error);
        }
      }
    }, 500);

    return () => clearTimeout(timer);
  }, [osgbEastingsInput, osgbNorthingsInput, lastEditedField, onWgsChange, onOsgbChange]);

  return (
    <div className="space-y-6">
      <div className="border border-gray-300 rounded-md p-4 bg-gray-50">
        <h3 className="text-lg font-medium text-gray-800 mb-3">WGS84 Coordinates</h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Latitude
            </label>
            <input
              type="text"
              value={wgsLatInput}
              onChange={(e) => handleWgsLatChange(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-gray-800 shadow-sm focus:border-trig-green-500 focus:ring-2 focus:ring-trig-green-400"
              placeholder="e.g., 52.12345"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Longitude
            </label>
            <input
              type="text"
              value={wgsLongInput}
              onChange={(e) => handleWgsLongChange(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-gray-800 shadow-sm focus:border-trig-green-500 focus:ring-2 focus:ring-trig-green-400"
              placeholder="e.g., -2.12345"
            />
          </div>
        </div>
      </div>

      <div className="border border-gray-300 rounded-md p-4 bg-gray-50">
        <h3 className="text-lg font-medium text-gray-800 mb-3">OSGB36 Coordinates</h3>
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Eastings
            </label>
            <input
              type="text"
              value={osgbEastingsInput}
              onChange={(e) => handleOsgbEastingsChange(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-gray-800 shadow-sm focus:border-trig-green-500 focus:ring-2 focus:ring-trig-green-400"
              placeholder="e.g., 512345"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Northings
            </label>
            <input
              type="text"
              value={osgbNorthingsInput}
              onChange={(e) => handleOsgbNorthingsChange(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-gray-800 shadow-sm focus:border-trig-green-500 focus:ring-2 focus:ring-trig-green-400"
              placeholder="e.g., 212345"
            />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Grid Reference
          </label>
          <input
            type="text"
            value={osgbGridrefInput}
            onChange={(e) => handleOsgbGridrefChange(e.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-gray-800 shadow-sm focus:border-trig-green-500 focus:ring-2 focus:ring-trig-green-400"
            placeholder="e.g., SO 12345 67890"
            readOnly
          />
          <p className="text-xs text-gray-500 mt-1">
            Grid reference is auto-calculated from eastings/northings
          </p>
        </div>
      </div>
    </div>
  );
}

