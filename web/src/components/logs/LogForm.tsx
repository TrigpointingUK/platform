import { useState } from "react";
import { Log, LogCreateInput, LogUpdateInput } from "../../lib/api";
import Card from "../ui/Card";
import Button from "../ui/Button";
import Spinner from "../ui/Spinner";
import ConditionSelector from "../forms/ConditionSelector";
import ScoreSelector from "../forms/ScoreSelector";
import DateTimeEditor from "../forms/DateTimeEditor";
import LocationPicker from "../forms/LocationPicker";
import PhotoManager from "../photos/PhotoManager";
import { useLogPhotos } from "../../hooks/useLogPhotos";

interface LogFormProps {
  trigGridRef: string;
  trigEastings: number;
  trigNorthings: number;
  trigLatitude: number;
  trigLongitude: number;
  existingLog?: Log;
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
    condition: existingLog?.condition || "G",
    score: existingLog?.score || 5,
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

    try {
      await onSubmit(submitData as LogCreateInput | LogUpdateInput);
    } catch (error) {
      console.error("Failed to submit log:", error);
    }
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

  return (
    <Card>
      <form onSubmit={handleSubmit} className="space-y-4">
        <h2 className="text-2xl font-bold text-gray-800 mb-4">
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

        {/* Location - Use Current Location Button */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            Location (optional)
          </label>
          
          {!locationSet ? (
            <>
              <LocationPicker
                onLocationSelected={(location) => {
                  setFormData((prev) => ({
                    ...prev,
                    osgb_gridref: location.gridRef,
                    osgb_eastings: location.eastings,
                    osgb_northings: location.northings,
                  }));
                  setLocationSet(true);
                }}
                maxAccuracy={10}
                trigLatitude={trigLatitude}
                trigLongitude={trigLongitude}
                maxDistance={25}
              />
              <div className="mt-2 text-xs text-gray-500 bg-blue-50 border border-blue-200 rounded px-3 py-2">
                <strong>Note:</strong> Location is optional. If you don't set your location, 
                no location data will be recorded with this log.
              </div>
            </>
          ) : (
            <div className="space-y-2">
              <div className="px-4 py-3 bg-green-50 border border-green-200 rounded-lg">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1">
                    <div className="font-semibold text-green-800 mb-1">
                      Location Set
                    </div>
                    <div className="text-sm text-green-700 space-y-1">
                      <div>
                        <span className="font-medium">Grid Ref:</span>{" "}
                        {formData.osgb_gridref}
                      </div>
                      <div>
                        <span className="font-medium">Eastings:</span>{" "}
                        {formData.osgb_eastings}
                      </div>
                      <div>
                        <span className="font-medium">Northings:</span>{" "}
                        {formData.osgb_northings}
                      </div>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setLocationSet(false)}
                    className="text-sm text-green-700 hover:text-green-900 underline flex-shrink-0"
                  >
                    Change
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Grid Reference Fields - Hidden but included for form submission */}
        <input type="hidden" name="osgb_gridref" value={formData.osgb_gridref} />
        <input type="hidden" name="osgb_eastings" value={formData.osgb_eastings} />
        <input type="hidden" name="osgb_northings" value={formData.osgb_northings} />

        {/* Flush Bracket Number */}
        <div>
          <label
            htmlFor="fb_number"
            className="block text-sm font-semibold text-gray-700 mb-1"
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
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-trig-green-500"
          />
        </div>

        {/* Comment */}
        <div>
          <label
            htmlFor="comment"
            className="block text-sm font-semibold text-gray-700 mb-1"
          >
            Comment
          </label>
          <textarea
            id="comment"
            name="comment"
            value={formData.comment}
            onChange={handleChange}
            rows={4}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-trig-green-500"
            placeholder="Describe your visit..."
          />
        </div>

        {/* Photo Management - Only show for existing logs */}
        {existingLog ? (
          <div className="pt-4 border-t border-gray-200">
            <PhotoManager
              logId={existingLog.id}
              photos={photos}
              isEditing={true}
            />
          </div>
        ) : (
          <div className="pt-4 border-t border-gray-200">
            <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-3">
              <p className="text-sm text-gray-700">
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

