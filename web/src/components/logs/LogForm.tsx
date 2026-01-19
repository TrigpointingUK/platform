import { useState, useCallback } from "react";
import { Log, LogCreateInput, LogUpdateInput, convertCoordinates } from "../../lib/api";
import Card from "../ui/Card";
import Button from "../ui/Button";
import Spinner from "../ui/Spinner";
import ConditionSelector from "../forms/ConditionSelector";
import ScoreSelector from "../forms/ScoreSelector";
import DateTimeEditor from "../forms/DateTimeEditor";
import LocationPicker from "../forms/LocationPicker";
import PhotoManager from "../photos/PhotoManager";
import { useLogPhotos } from "../../hooks/useLogPhotos";
import { parseLocation, type GridSystem } from "../../lib/locationParser";
import { calculateDistance } from "../../lib/coordinates";

interface LogFormProps {
  trigGridRef: string;
  trigEastings: number;
  trigNorthings: number;
  trigLatitude: number;
  trigLongitude: number;
  existingLog?: Log;
  defaultCondition?: string;
  onSubmit: (data: LogCreateInput | LogUpdateInput) => Promise<void>;
  onCancel: () => void;
  isSubmitting: boolean;
}

export default function LogForm({
  trigGridRef,
  trigEastings,
  trigNorthings,
  trigLatitude,
  trigLongitude,
  existingLog,
  defaultCondition = "G",
  onSubmit,
  onCancel,
  isSubmitting,
}: LogFormProps) {
  // Get current time in HH:MM:SS format
  const getCurrentTime = () => {
    const now = new Date();
    return now.toTimeString().split(" ")[0]; // Gets HH:MM:SS
  };

  const [formData, setFormData] = useState({
    date: existingLog?.date || new Date().toISOString().split("T")[0],
    time: existingLog?.time || getCurrentTime(), // Use current time for new logs
    condition: existingLog?.condition || defaultCondition,
    score: existingLog?.score ?? 5,
    comment: existingLog?.comment || "",
    osgb_gridref: existingLog?.osgb_gridref || trigGridRef,
    osgb_eastings: existingLog?.osgb_eastings || trigEastings,
    osgb_northings: existingLog?.osgb_northings || trigNorthings,
    fb_number: existingLog?.fb_number || "",
    source: existingLog?.source || "W",
  });

  const [useCustomTime, setUseCustomTime] = useState(
    existingLog ? existingLog.time !== "12:00:00" : true // Default to true for new logs
  );
  const [locationSet, setLocationSet] = useState(!!existingLog);
  // Initialize locationInput from existingLog if present, avoiding useEffect sync
  const [locationInput, setLocationInput] = useState(() => 
    existingLog?.osgb_gridref || ""
  );
  const [locationError, setLocationError] = useState("");
  const [distanceFromTrig, setDistanceFromTrig] = useState<number | null>(null);
  const [showDistanceWarning, setShowDistanceWarning] = useState(false);
  const [pendingSubmit, setPendingSubmit] = useState<Partial<LogCreateInput> | null>(null);

  // Fetch photos for existing logs
  const { data: photos = [] } = useLogPhotos(existingLog?.id);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const submitData: Partial<LogCreateInput> = {
      date: formData.date,
      time: useCustomTime ? formData.time : "12:00:00",
      condition: formData.condition,
      score: formData.score,
      comment: formData.comment,
      fb_number: formData.fb_number,
      source: formData.source,
    };

    // Only include location fields if user has set a custom location
    if (locationSet) {
      submitData.osgb_gridref = formData.osgb_gridref;
      submitData.osgb_eastings = formData.osgb_eastings;
      submitData.osgb_northings = formData.osgb_northings;
    }

    // Check distance if location is set
    if (locationSet && distanceFromTrig !== null && distanceFromTrig > 20) {
      // Show confirmation dialog
      setPendingSubmit(submitData);
      setShowDistanceWarning(true);
      return;
    }

    try {
      await onSubmit(submitData as LogCreateInput | LogUpdateInput);
    } catch (error) {
      console.error("Failed to submit log:", error);
    }
  };

  const handleDistanceConfirm = async () => {
    setShowDistanceWarning(false);
    if (pendingSubmit) {
      try {
        await onSubmit(pendingSubmit as LogCreateInput | LogUpdateInput);
        setPendingSubmit(null);
      } catch (error) {
        console.error("Failed to submit log:", error);
      }
    }
  };

  const handleDistanceCancel = () => {
    setShowDistanceWarning(false);
    setPendingSubmit(null);
  };

  const handleChange = (
    e: React.ChangeEvent<
      HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement
    >
  ) => {
    const { name, value, type } = e.target;

    if (type === "number") {
      setFormData((prev) => ({ ...prev, [name]: parseInt(value, 10) || 0 }));
    } else {
      setFormData((prev) => ({ ...prev, [name]: value }));
    }
  };

  // Helper to calculate distance using the API for grid conversion
  const calculateDistanceFromGrid = useCallback(async (
    eastings: number,
    northings: number,
    gridSystem: GridSystem
  ) => {
    try {
      // Use the backend API to convert grid coordinates to WGS84
      const fromCrs = gridSystem === 'ie' ? 'irish' : 'osgb';
      const result = await convertCoordinates({
        from: fromCrs,
        to: 'wgs84',
        e: eastings,
        n: northings,
      });
      
      if (result.output.lat !== undefined && result.output.lon !== undefined) {
        const distance = calculateDistance(
          result.output.lat,
          result.output.lon,
          trigLatitude,
          trigLongitude
        );
        setDistanceFromTrig(distance);
      }
    } catch (error) {
      console.error("Failed to calculate distance:", error);
      setDistanceFromTrig(null);
    }
  }, [trigLatitude, trigLongitude]);

  const handleLocationInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    // Auto-uppercase for grid references
    const uppercased = value.toUpperCase();
    setLocationInput(uppercased);

    // Parse the location
    const result = parseLocation(uppercased);
    
    if (result.success && result.data) {
      // Valid location
      setFormData((prev) => ({
        ...prev,
        osgb_gridref: result.data!.gridRef,
        osgb_eastings: result.data!.eastings,
        osgb_northings: result.data!.northings,
      }));
      setLocationSet(true);
      setLocationError("");

      // Calculate distance from trigpoint
      if (result.data.lat !== undefined && result.data.lon !== undefined) {
        // We have lat/lon directly (from lat/lon input)
        const distance = calculateDistance(
          result.data.lat,
          result.data.lon,
          trigLatitude,
          trigLongitude
        );
        setDistanceFromTrig(distance);
      } else if (result.data.eastings && result.data.northings) {
        // We have grid coordinates - use the API to convert and calculate distance
        calculateDistanceFromGrid(
          result.data.eastings,
          result.data.northings,
          result.data.gridSystem ?? 'gb'
        );
      }
    } else {
      // Invalid or empty location
      if (uppercased.trim() === "") {
        // Empty input - clear everything
        setLocationSet(false);
        setLocationError("");
        setDistanceFromTrig(null);
      } else {
        // Invalid input - show error
        setLocationSet(false);
        setLocationError(result.error || "Invalid location format");
        setDistanceFromTrig(null);
      }
    }
  };

  return (
    <Card>
      <form onSubmit={handleSubmit} className="space-y-4">
        <h2 className="text-2xl font-bold text-gray-800 dark:text-gray-100 mb-4">
          {existingLog ? "Edit Log" : "Log This Trig"}
        </h2>

        {/* Date and Time */}
        <DateTimeEditor
          date={formData.date}
          time={formData.time}
          useCustomTime={useCustomTime}
          onDateChange={(date) => setFormData((prev) => ({ ...prev, date }))}
          onTimeChange={(time) => setFormData((prev) => ({ ...prev, time }))}
          onUseCustomTimeChange={setUseCustomTime}
          required
        />

        {/* Condition and Score */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <ConditionSelector
            value={formData.condition}
            onChange={(condition) =>
              setFormData((prev) => ({ ...prev, condition }))
            }
            required
          />

          <ScoreSelector
            value={formData.score}
            onChange={(score) => setFormData((prev) => ({ ...prev, score }))}
            required
          />
        </div>

        {/* Location */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
            Location (optional)
          </label>
          
          <div className="flex flex-col gap-2">
            {/* Location Input Textbox */}
            <div className="flex flex-col sm:flex-row gap-2">
              <input
                type="text"
                value={locationInput}
                onChange={handleLocationInputChange}
                placeholder="Enter grid ref (e.g., TL 137 055) or coordinates (e.g., 53.69417, -1.78231)"
                className={`flex-1 px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-trig-green-500 text-gray-900 dark:text-gray-100 dark:placeholder-gray-400 ${
                  locationError && locationInput.trim() !== "" 
                    ? "border-red-300 bg-red-50 dark:border-red-700 dark:bg-red-900/30" 
                    : "border-gray-300 bg-white dark:border-gray-600 dark:bg-gray-700"
                }`}
              />
              
              {/* Distance Display */}
              <input
                type="text"
                value={
                  distanceFromTrig !== null 
                    ? `${distanceFromTrig.toFixed(1)}m from trig`
                    : ""
                }
                readOnly
                placeholder="Distance"
                className="w-full sm:w-40 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-gray-50 dark:bg-gray-700 text-gray-700 dark:text-gray-300 text-sm"
              />
              
              {/* Buttons - kept together on small screens */}
              <div className="flex gap-2 flex-shrink-0">
                <LocationPicker
                  onLocationSelected={(location) => {
                    setFormData((prev) => ({
                      ...prev,
                      osgb_gridref: location.gridRef,
                      osgb_eastings: location.eastings,
                      osgb_northings: location.northings,
                    }));
                    setLocationSet(true);
                    setLocationInput(location.gridRef);
                    
                    // Calculate distance using lat/lon if available, otherwise use API
                    if (location.lat !== undefined && location.lon !== undefined) {
                      const distance = calculateDistance(
                        location.lat,
                        location.lon,
                        trigLatitude,
                        trigLongitude
                      );
                      setDistanceFromTrig(distance);
                    } else {
                      // Use API to convert grid coordinates (supports both OSGB and Irish Grid)
                      calculateDistanceFromGrid(
                        location.eastings,
                        location.northings,
                        location.gridSystem ?? 'gb'
                      );
                    }
                  }}
                  maxAccuracy={10}
                  trigLatitude={trigLatitude}
                  trigLongitude={trigLongitude}
                  maxDistance={25}
                />
                
                <Button
                  type="button"
                  variant="secondary"
                  disabled={!locationSet}
                  onClick={() => {
                    setFormData((prev) => ({
                      ...prev,
                      osgb_gridref: trigGridRef,
                      osgb_eastings: trigEastings,
                      osgb_northings: trigNorthings,
                    }));
                    setLocationSet(false);
                    setLocationInput("");
                    setLocationError("");
                    setDistanceFromTrig(null);
                  }}
                  className="flex-shrink-0"
                >
                  🗑️ Clear Location
                </Button>
              </div>
            </div>
            
            {/* Validation Error */}
            {locationError && locationInput.trim() !== "" && (
              <div className="text-xs text-gray-500 dark:text-gray-400">
                {locationError}
              </div>
            )}
          </div>
        </div>

        {/* Distance Warning Modal */}
        {showDistanceWarning && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <Card className="max-w-md mx-4">
              <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">Location Distance Warning</h3>
              <p className="text-gray-700 dark:text-gray-300 mb-4">
                The location you've entered is <strong>{distanceFromTrig?.toFixed(1)}m</strong> from the 
                recorded trigpoint location. This is more than 20 meters away.
              </p>
              <p className="text-gray-600 dark:text-gray-400 mb-6 text-sm">
                Are you sure this is correct? Large distances may indicate:
              </p>
              <ul className="text-sm text-gray-600 dark:text-gray-400 mb-6 list-disc list-inside space-y-1">
                <li>The trigpoint has been moved</li>
                <li>GPS accuracy issues</li>
                <li>An incorrect location entry</li>
              </ul>
              <div className="flex gap-2 justify-end">
                <Button 
                  variant="outline" 
                  onClick={handleDistanceCancel}
                >
                  Cancel
                </Button>
                <Button 
                  onClick={handleDistanceConfirm}
                >
                  Confirm and Submit
                </Button>
              </div>
            </Card>
          </div>
        )}

        {/* Grid Reference Fields - Hidden but included for form submission */}
        <input type="hidden" name="osgb_gridref" value={formData.osgb_gridref} />
        <input type="hidden" name="osgb_eastings" value={formData.osgb_eastings} />
        <input type="hidden" name="osgb_northings" value={formData.osgb_northings} />

        {/* Flush Bracket Number */}
        <div>
          <label
            htmlFor="fb_number"
            className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1"
          >
            Flush Bracket Number
          </label>
          <input
            type="text"
            id="fb_number"
            name="fb_number"
            value={formData.fb_number}
            onChange={handleChange}
            maxLength={10}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-trig-green-500"
          />
        </div>

        {/* Comment */}
        <div>
          <label
            htmlFor="comment"
            className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1"
          >
            Comment
          </label>
          <textarea
            id="comment"
            name="comment"
            value={formData.comment}
            onChange={handleChange}
            rows={4}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-trig-green-500"
            placeholder="Describe your visit..."
          />
        </div>

        {/* Photo Management - Only show for existing logs */}
        {existingLog ? (
          <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
            <PhotoManager
              logId={existingLog.id}
              photos={photos}
              isEditing={true}
            />
          </div>
        ) : (
          <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
            <div className="bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 rounded-lg px-4 py-3">
              <p className="text-sm text-gray-700 dark:text-gray-300">
                <strong>Note:</strong> Save your log first, then you can add photos by editing it.
              </p>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-3 pt-4">
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? (
              <>
                <Spinner size="sm" />
                <span className="ml-2">Saving...</span>
              </>
            ) : existingLog ? (
              "Update Log"
            ) : (
              "Create Log"
            )}
          </Button>
          <Button type="button" onClick={onCancel} disabled={isSubmitting}>
            Cancel
          </Button>
        </div>
      </form>
    </Card>
  );
}

