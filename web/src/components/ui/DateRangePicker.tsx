"use client";

import * as React from "react";
import { CalendarIcon, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from "lucide-react";
import { format, addMonths, addYears } from "date-fns";
import { DayPicker, type DateRange as DayPickerDateRange } from "react-day-picker";
import { cx } from "../../lib/utils";

export interface DateRange {
  from?: Date;
  to?: Date;
}

export interface DateRangePreset {
  label: string;
  dateRange: DateRange;
}

interface DateRangePickerProps {
  value?: DateRange;
  onChange?: (range: DateRange | undefined) => void;
  placeholder?: string;
  className?: string;
  presets?: DateRangePreset[];
  disabled?: boolean;
  maxValue?: Date;
}

function DateRangePicker({
  value,
  onChange,
  placeholder = "Select date range",
  className,
  presets,
  disabled,
  maxValue,
}: DateRangePickerProps) {
  const [isOpen, setIsOpen] = React.useState(false);
  const [month, setMonth] = React.useState<Date>(value?.from || new Date());
  const popoverRef = React.useRef<HTMLDivElement>(null);
  const buttonRef = React.useRef<HTMLButtonElement>(null);

  // Sync month view when value changes or popup opens
  React.useEffect(() => {
    if (isOpen) {
      // When popup opens, show the selected date's month or current month if no selection
      setMonth(value?.from || new Date());
    }
  }, [isOpen, value]);

  // Close popover when clicking outside
  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        isOpen &&
        popoverRef.current &&
        !popoverRef.current.contains(event.target as Node) &&
        buttonRef.current &&
        !buttonRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  const handlePresetClick = (preset: DateRangePreset) => {
    onChange?.(preset.dateRange);
    if (preset.dateRange.from) {
      setMonth(preset.dateRange.from);
    }
  };

  const handleDayPickerSelect = (range: DayPickerDateRange | undefined) => {
    if (!range) {
      onChange?.(undefined);
    } else {
      onChange?.({ from: range.from, to: range.to });
    }
  };

  const handleClear = () => {
    onChange?.(undefined);
    setIsOpen(false);
  };

  const handleClose = () => {
    setIsOpen(false);
  };

  // Navigation handlers
  const handlePreviousYear = () => setMonth(addYears(month, -1));
  const handlePreviousMonth = () => setMonth(addMonths(month, -1));
  const handleNextMonth = () => setMonth(addMonths(month, 1));
  const handleNextYear = () => setMonth(addYears(month, 1));

  const displayValue = React.useMemo(() => {
    if (!value?.from) return null;
    if (value.to) {
      return `${format(value.from, "MMM d, yyyy")} – ${format(value.to, "MMM d, yyyy")}`;
    }
    return format(value.from, "MMM d, yyyy");
  }, [value]);

  const navButtonClass = cx(
    "inline-flex items-center justify-center h-8 w-8 rounded-md border border-gray-300 bg-white text-gray-700",
    "hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-trig-green-500",
    "disabled:opacity-50 disabled:cursor-not-allowed"
  );

  return (
    <div className={cx("relative", className)}>
      <button
        ref={buttonRef}
        type="button"
        disabled={disabled}
        onClick={() => setIsOpen(!isOpen)}
        className={cx(
          "flex h-10 w-full items-center justify-between rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-xs transition-colors",
          "hover:bg-gray-50",
          "focus:outline-none focus:ring-2 focus:ring-trig-green-500 focus:border-trig-green-500",
          disabled && "cursor-not-allowed opacity-50"
        )}
      >
        <div className="flex items-center gap-2">
          <CalendarIcon className="h-5 w-5 text-gray-400" />
          <span className={cx(!displayValue && "text-gray-400")}>
            {displayValue || placeholder}
          </span>
        </div>
      </button>

      {isOpen && (
        <div
          ref={popoverRef}
          className="absolute top-full right-0 z-50 mt-2 rounded-lg border border-gray-200 bg-white p-4 shadow-lg"
        >
          <div className="flex gap-4">
            {presets && presets.length > 0 && (
              <div className="flex flex-col gap-1 border-r border-gray-200 pr-4">
                {presets.map((preset, index) => (
                  <button
                    key={index}
                    type="button"
                    onClick={() => handlePresetClick(preset)}
                    className="whitespace-nowrap rounded px-3 py-2 text-left text-sm text-gray-700 transition-colors hover:bg-gray-100 hover:text-gray-900"
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
            )}
            <div className="flex flex-col gap-4">
              {/* Custom navigation with year buttons */}
              <div className="flex items-center justify-between px-1">
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={handlePreviousYear}
                    className={navButtonClass}
                    aria-label="Previous year"
                  >
                    <ChevronsLeft className="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    onClick={handlePreviousMonth}
                    className={navButtonClass}
                    aria-label="Previous month"
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </button>
                </div>
                <span className="text-sm font-semibold text-gray-900">
                  {format(month, "MMMM yyyy")}
                </span>
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={handleNextMonth}
                    className={navButtonClass}
                    aria-label="Next month"
                  >
                    <ChevronRight className="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    onClick={handleNextYear}
                    className={navButtonClass}
                    aria-label="Next year"
                  >
                    <ChevronsRight className="h-4 w-4" />
                  </button>
                </div>
              </div>

              <DayPicker
                mode="range"
                month={month}
                onMonthChange={setMonth}
                selected={value ? { from: value.from, to: value.to } : undefined}
                onSelect={handleDayPickerSelect}
                numberOfMonths={1}
                disabled={maxValue ? { after: maxValue } : undefined}
                showOutsideDays={false}
                disableNavigation
                classNames={{
                  months: "flex gap-4",
                  month: "space-y-4",
                  caption: "hidden",
                  caption_label: "hidden",
                  table: "w-full border-collapse",
                  head_row: "flex",
                  head_cell: "text-gray-500 w-10 font-medium text-xs text-center",
                  row: "flex w-full mt-1",
                  cell: cx(
                    "relative p-0 text-center text-sm",
                    "focus-within:relative focus-within:z-20"
                  ),
                  day: cx(
                    "h-10 w-10 p-0 font-normal rounded-md transition-colors",
                    "hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-trig-green-500"
                  ),
                  day_selected: "bg-trig-green-600 text-white hover:bg-trig-green-500 focus:bg-trig-green-600",
                  day_today: "bg-gray-100 font-semibold",
                  day_outside: "text-gray-300 opacity-50",
                  day_disabled: "text-gray-300 opacity-50 cursor-not-allowed hover:bg-transparent",
                  day_range_middle: "bg-trig-green-50 text-gray-900 rounded-none",
                  day_range_start: "bg-trig-green-600 text-white rounded-l-full",
                  day_range_end: "bg-trig-green-600 text-white rounded-r-full",
                  day_hidden: "invisible",
                }}
              />

              {/* Action buttons */}
              <div className="flex items-center justify-end gap-2 border-t border-gray-200 pt-4">
                <button
                  type="button"
                  onClick={handleClear}
                  className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 shadow-xs transition-colors hover:bg-gray-50"
                >
                  Clear
                </button>
                <button
                  type="button"
                  onClick={handleClose}
                  className="rounded-md bg-trig-green-600 px-3 py-1.5 text-sm font-medium text-white shadow-xs transition-colors hover:bg-trig-green-500"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export { DateRangePicker };
