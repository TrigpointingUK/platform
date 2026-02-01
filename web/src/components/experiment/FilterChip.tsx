/**
 * FilterChip component for the experimental filter chips UI.
 * 
 * A small clickable chip that displays a filter summary and opens a popover
 * with detailed filter controls when clicked.
 */

import { useState, useRef, useEffect, ReactNode } from "react";
import { X, ChevronDown, Check, Minus } from "lucide-react";

export interface FilterChipProps {
  /** Label shown on the chip (e.g., "Category", "Condition") */
  label: string;
  /** Summary text showing current selection (e.g., "2 selected", "All") */
  summary: string;
  /** Whether any filter is active (affects styling) */
  isActive?: boolean;
  /** Whether the filter is in a warning state (nothing selected = empty results) */
  isWarning?: boolean;
  /** Whether the chip can be cleared */
  clearable?: boolean;
  /** Called when the clear button is clicked */
  onClear?: () => void;
  /** Content to display in the popover */
  children: ReactNode | ((actions: { close: () => void }) => ReactNode);
  /** Width of the popover (default: 'auto') */
  popoverWidth?: "sm" | "md" | "lg" | "xl" | "auto";
  /** Max height class for the popover content area */
  contentMaxHeightClass?: string;
  /** Icon to display before the label */
  icon?: ReactNode;
}

const popoverWidths = {
  sm: "w-48",
  md: "w-64",
  lg: "w-80",
  xl: "w-96",
  auto: "w-auto min-w-48",
};

export function FilterChip({
  label,
  summary,
  isActive = false,
  isWarning = false,
  clearable = true,
  onClear,
  children,
  popoverWidth = "md",
  contentMaxHeightClass = "max-h-80",
  icon,
}: FilterChipProps) {
  const [isOpen, setIsOpen] = useState(false);
  const chipRef = useRef<HTMLDivElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);

  // Close popover when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        chipRef.current &&
        !chipRef.current.contains(event.target as Node) &&
        popoverRef.current &&
        !popoverRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [isOpen]);

  // Close popover on Escape key
  useEffect(() => {
    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener("keydown", handleEscape);
      return () => document.removeEventListener("keydown", handleEscape);
    }
  }, [isOpen]);

  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation();
    onClear?.();
  };

  const closePopover = () => setIsOpen(false);

  return (
    <div className="relative" ref={chipRef}>
      {/* Chip trigger - using div with role="button" to allow nested clear button */}
      <div
        role="button"
        tabIndex={0}
        onClick={() => setIsOpen(!isOpen)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            setIsOpen(!isOpen);
          }
        }}
        className={`
          inline-flex items-center gap-1.5 px-3 py-1.5
          w-72 text-sm font-medium rounded-full cursor-pointer select-none
          border transition-all duration-150
          ${isWarning
            ? "bg-red-50 dark:bg-red-900/20 border-red-300 dark:border-red-700 text-red-700 dark:text-red-300"
            : isActive
              ? "bg-trig-green-50 dark:bg-trig-green-900/30 border-trig-green-300 dark:border-trig-green-700 text-trig-green-700 dark:text-trig-green-300"
              : "bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:border-gray-400 dark:hover:border-gray-500"
          }
          ${isOpen ? `ring-2 ${isWarning ? "ring-red-500" : "ring-trig-green-500"} ring-offset-1 dark:ring-offset-gray-900` : ""}
        `}
        aria-expanded={isOpen}
        aria-haspopup="true"
      >
        {icon && <span className="flex-shrink-0">{icon}</span>}
        <span className="font-medium flex-shrink-0">{label}:</span>
        <span className={`truncate flex-1 min-w-0 ${isActive || isWarning ? "font-semibold" : ""}`}>
          {summary}
        </span>
        {clearable && (isActive || isWarning) && onClear ? (
          <button
            type="button"
            onClick={handleClear}
            className={`ml-0.5 p-0.5 rounded-full transition-colors ${
              isWarning 
                ? "hover:bg-red-200 dark:hover:bg-red-800" 
                : "hover:bg-trig-green-200 dark:hover:bg-trig-green-800"
            }`}
            aria-label={`Clear ${label} filter`}
          >
            <X className="w-3 h-3" />
          </button>
        ) : (
          <ChevronDown className={`w-3.5 h-3.5 transition-transform ${isOpen ? "rotate-180" : ""}`} />
        )}
      </div>

      {/* Popover */}
      {isOpen && (
        <div
          ref={popoverRef}
          className={`
            absolute z-50 mt-2 left-0
            ${popoverWidths[popoverWidth]}
            bg-[color:var(--color-bg-secondary)]
            border border-[color:var(--color-border)]
            rounded-lg shadow-lg dark:shadow-gray-900/50
          `}
          role="dialog"
          aria-label={`${label} filter options`}
        >
          {/* Popover header */}
          <div className="px-3 py-2 bg-[color:var(--color-bg-tertiary)] border-b border-[color:var(--color-border)]">
            <h3 className="text-sm font-semibold text-[color:var(--color-text-primary)]">
              {label}
            </h3>
          </div>
          
          {/* Popover content */}
          <div className={`${contentMaxHeightClass} overflow-y-auto`}>
            {typeof children === "function" ? children({ close: closePopover }) : children}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Helper component for a toggleable list item within a filter popover
 */
export interface FilterListItemProps {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  icon?: ReactNode;
  count?: number;
  indented?: boolean;
}

export interface FilterCheckboxProps {
  checked: boolean;
  indeterminate?: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  ariaLabel?: string;
  className?: string;
}

export function FilterCheckbox({
  checked,
  indeterminate = false,
  onChange,
  disabled = false,
  ariaLabel,
  className,
}: FilterCheckboxProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.indeterminate = indeterminate;
    }
  }, [indeterminate]);

  // Determine visual state
  const isCheckedOrIndeterminate = checked || indeterminate;

  return (
    <span className={`relative inline-flex items-center ${className ?? ""}`}>
      <input
        ref={inputRef}
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        disabled={disabled}
        aria-label={ariaLabel}
        className="sr-only"
      />
      <span 
        className={`
          flex h-4 w-4 items-center justify-center rounded border
          ${isCheckedOrIndeterminate 
            ? "border-trig-green-600 bg-trig-green-600" 
            : "border-gray-400 bg-white"
          }
          ${disabled ? "opacity-50" : ""}
        `}
      >
        {checked && !indeterminate && (
          <Check className="h-3 w-3 text-white" strokeWidth={3} />
        )}
        {indeterminate && (
          <Minus className="h-3 w-3 text-white" strokeWidth={3} />
        )}
      </span>
    </span>
  );
}

export function FilterListItem({
  label,
  checked,
  onChange,
  icon,
  count,
  indented = false,
}: FilterListItemProps) {
  return (
    <label
      className={`
        flex items-center gap-2 px-3 py-2 cursor-pointer
        hover:bg-[color:var(--color-bg-tertiary)] transition-colors
        ${indented ? "pl-8" : ""}
      `}
    >
      <FilterCheckbox checked={checked} onChange={onChange} ariaLabel={label} />
      {icon && <span className="flex-shrink-0">{icon}</span>}
      <span className="flex-1 text-sm text-[color:var(--color-text-primary)] truncate">
        {label}
      </span>
      {count !== undefined && (
        <span className="text-xs text-[color:var(--color-text-secondary)] tabular-nums">
          ({count})
        </span>
      )}
    </label>
  );
}

/**
 * Helper component for All/None selection buttons
 */
export interface FilterSelectionButtonsProps {
  onSelectAll: () => void;
  onSelectNone: () => void;
}

export function FilterSelectionButtons({
  onSelectAll,
  onSelectNone,
}: FilterSelectionButtonsProps) {
  return (
    <div className="flex gap-2 px-3 py-2 border-b border-[color:var(--color-border)]">
      <button
        type="button"
        onClick={onSelectAll}
        className="px-2 py-1 text-xs font-medium text-trig-green-600 
                   hover:bg-trig-green-50 rounded transition-colors"
      >
        All
      </button>
      <button
        type="button"
        onClick={onSelectNone}
        className="px-2 py-1 text-xs font-medium text-[color:var(--color-text-secondary)] 
                   hover:bg-[color:var(--color-bg-tertiary)] rounded transition-colors"
      >
        None
      </button>
    </div>
  );
}

/**
 * Helper component for a section divider in filter popover
 */
export function FilterDivider() {
  return <div className="border-t border-[color:var(--color-border)] my-1" />;
}

export default FilterChip;

