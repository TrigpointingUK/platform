interface DateTimeEditorProps {
  date: string;
  time: string;
  useCustomTime: boolean;
  onDateChange: (date: string) => void;
  onTimeChange: (time: string) => void;
  onUseCustomTimeChange: (useCustomTime: boolean) => void;
  required?: boolean;
}

export default function DateTimeEditor({
  date,
  time,
  useCustomTime,
  onDateChange,
  onTimeChange,
  onUseCustomTimeChange,
  required = false,
}: DateTimeEditorProps) {
  // Get today's date in YYYY-MM-DD format for max attribute
  const today = new Date().toISOString().split("T")[0];
  
  // Get current time in HH:MM:SS format
  const getCurrentTime = () => {
    const now = new Date();
    return now.toTimeString().split(" ")[0]; // Gets HH:MM:SS
  };

  const handleUseCustomTimeChange = (checked: boolean) => {
    // If enabling custom time and current time is default, set to current time first
    if (checked && time === "12:00:00") {
      const currentTime = getCurrentTime();
      console.log('Setting time to current time:', currentTime);
      onTimeChange(currentTime);
    }
    // Then update the checkbox state
    onUseCustomTimeChange(checked);
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {/* Date Picker */}
      <div>
        <label
          htmlFor="log-date"
          className="block text-sm font-semibold text-gray-700 mb-1"
        >
          Date {required && <span className="text-red-500">*</span>}
        </label>
        <input
          type="date"
          id="log-date"
          value={date}
          onChange={(e) => onDateChange(e.target.value)}
          max={today}
          required={required}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-trig-green-500 focus:border-trig-green-500"
        />
        <p className="text-xs text-gray-500 mt-1">
          Date of your visit (today or earlier)
        </p>
      </div>

      {/* Time Picker */}
      <div>
        <label
          htmlFor="log-time"
          className="block text-sm font-semibold text-gray-700 mb-1"
        >
          Time
        </label>
        
        {/* Checkbox to enable custom time */}
        <div className="flex items-center gap-2 mb-2">
          <input
            type="checkbox"
            id="use-custom-time"
            checked={useCustomTime}
            onChange={(e) => handleUseCustomTimeChange(e.target.checked)}
            className="h-4 w-4 text-trig-green-600 focus:ring-trig-green-500 border-gray-300 rounded"
          />
          <label htmlFor="use-custom-time" className="text-sm text-gray-600">
            Log specific time
          </label>
        </div>

        {/* Time input (only shown when custom time is enabled) */}
        {useCustomTime ? (
          <>
            <input
              type="time"
              id="log-time"
              value={time}
              onChange={(e) => {
                console.log('Time input changed to:', e.target.value);
                onTimeChange(e.target.value);
              }}
              step="1"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-trig-green-500 focus:border-trig-green-500"
            />
            <p className="text-xs text-gray-500 mt-1">
              Exact time of your visit (current: {time})
            </p>
          </>
        ) : (
          <div className="px-3 py-2 border border-gray-200 rounded-md bg-gray-50 text-gray-500 text-sm">
            12:00:00 (default)
          </div>
        )}
      </div>
    </div>
  );
}

