import { useState } from "react";
import { Log, LogCreateInput, LogUpdateInput } from "../../lib/api";
import Card from "../ui/Card";
import Button from "../ui/Button";
import Spinner from "../ui/Spinner";

interface LogFormProps {
  trigId: number;
  trigGridRef: string;
  trigEastings: number;
  trigNorthings: number;
  existingLog?: Log;
  onSubmit: (data: LogCreateInput) => Promise<void>;
  onCancel: () => void;
  isSubmitting: boolean;
}

export default function LogForm({
  trigId,
  trigGridRef,
  trigEastings,
  trigNorthings,
  existingLog,
  onSubmit,
  onCancel,
  isSubmitting,
}: LogFormProps) {
  const [formData, setFormData] = useState({
    date: existingLog?.date || new Date().toISOString().split("T")[0],
    time: existingLog?.time || "12:00:00",
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
    existingLog?.time !== "12:00:00"
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const submitData = {
      ...formData,
      time: useCustomTime ? formData.time : "12:00:00",
    };

    try {
      await onSubmit(submitData);
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
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label
              htmlFor="date"
              className="block text-sm font-semibold text-gray-700 mb-1"
            >
              Date *
            </label>
            <input
              type="date"
              id="date"
              name="date"
              value={formData.date}
              onChange={handleChange}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-trig-green-500"
            />
          </div>

          <div>
            <label
              htmlFor="time"
              className="block text-sm font-semibold text-gray-700 mb-1"
            >
              Time
            </label>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="useCustomTime"
                checked={useCustomTime}
                onChange={(e) => setUseCustomTime(e.target.checked)}
                className="h-4 w-4 text-trig-green-600 focus:ring-trig-green-500 border-gray-300 rounded"
              />
              <label htmlFor="useCustomTime" className="text-sm text-gray-600">
                Log specific time
              </label>
            </div>
            {useCustomTime && (
              <input
                type="time"
                id="time"
                name="time"
                value={formData.time}
                onChange={handleChange}
                step="1"
                className="w-full mt-2 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-trig-green-500"
              />
            )}
          </div>
        </div>

        {/* Condition and Score */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label
              htmlFor="condition"
              className="block text-sm font-semibold text-gray-700 mb-1"
            >
              Condition *
            </label>
            <select
              id="condition"
              name="condition"
              value={formData.condition}
              onChange={handleChange}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-trig-green-500"
            >
              <option value="G">Good</option>
              <option value="D">Damaged</option>
              <option value="M">Missing</option>
              <option value="P">Possibly Missing</option>
              <option value="U">Unknown</option>
            </select>
          </div>

          <div>
            <label
              htmlFor="score"
              className="block text-sm font-semibold text-gray-700 mb-1"
            >
              Score (0-10) *
            </label>
            <select
              id="score"
              name="score"
              value={formData.score}
              onChange={handleChange}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-trig-green-500"
            >
              <option value="0">----</option>
              {[...Array(10)].map((_, i) => (
                <option key={i + 1} value={i + 1}>
                  {i + 1}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Grid Reference Fields */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label
              htmlFor="osgb_gridref"
              className="block text-sm font-semibold text-gray-700 mb-1"
            >
              Grid Reference *
            </label>
            <input
              type="text"
              id="osgb_gridref"
              name="osgb_gridref"
              value={formData.osgb_gridref}
              onChange={handleChange}
              required
              maxLength={14}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-trig-green-500"
            />
          </div>

          <div>
            <label
              htmlFor="osgb_eastings"
              className="block text-sm font-semibold text-gray-700 mb-1"
            >
              Eastings *
            </label>
            <input
              type="number"
              id="osgb_eastings"
              name="osgb_eastings"
              value={formData.osgb_eastings}
              onChange={handleChange}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-trig-green-500"
            />
          </div>

          <div>
            <label
              htmlFor="osgb_northings"
              className="block text-sm font-semibold text-gray-700 mb-1"
            >
              Northings *
            </label>
            <input
              type="number"
              id="osgb_northings"
              name="osgb_northings"
              value={formData.osgb_northings}
              onChange={handleChange}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-trig-green-500"
            />
          </div>
        </div>

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

