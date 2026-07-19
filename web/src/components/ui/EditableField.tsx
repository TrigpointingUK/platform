import { useState, useRef, useEffect } from "react";

interface EditableFieldProps {
  value: string;
  onSave: (newValue: string) => Promise<void>;
  label: string;
  type?: string;
  multiline?: boolean;
  editable?: boolean;
  placeholder?: string;
  maxLength?: number;
}

export default function EditableField({
  value,
  onSave,
  label,
  type = "text",
  multiline = false,
  editable = false,
  placeholder = "",
  maxLength,
}: EditableFieldProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(value);
  const [prevValue, setPrevValue] = useState(value);
  const [isSaving, setIsSaving] = useState(false);
  const inputRef = useRef<HTMLInputElement | HTMLTextAreaElement>(null);

  // Sync local state when the prop changes (adjust-during-render rather than an
  // effect, per https://react.dev/learn/you-might-not-need-an-effect).
  if (value !== prevValue) {
    setPrevValue(value);
    setEditValue(value);
  }

  // Focus input when entering edit mode
  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [isEditing]);

  const handleSave = async () => {
    if (editValue !== value) {
      setIsSaving(true);
      try {
        await onSave(editValue);
      } catch (error) {
        console.error('Failed to save:', error);
        // Revert on error
        setEditValue(value);
      } finally {
        setIsSaving(false);
      }
    }
    setIsEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !multiline) {
      e.preventDefault();
      handleSave();
    } else if (e.key === 'Escape') {
      setEditValue(value);
      setIsEditing(false);
    }
  };

  if (!editable) {
    return (
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          {label}
        </label>
        <p className="text-gray-900 dark:text-gray-100">
          {value || <span className="text-gray-400 dark:text-gray-500 italic">Not set</span>}
        </p>
      </div>
    );
  }

  return (
    <div className="relative">
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
        {label}
      </label>
      
      {isEditing ? (
        multiline ? (
          <textarea
            ref={inputRef as React.RefObject<HTMLTextAreaElement>}
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            onBlur={handleSave}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            maxLength={maxLength}
            disabled={isSaving}
            rows={4}
            className="w-full px-3 py-2 border border-trig-green-500 rounded-md focus:outline-none focus:ring-2 focus:ring-trig-green-400 resize-none bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500"
          />
        ) : (
          <input
            ref={inputRef as React.RefObject<HTMLInputElement>}
            type={type}
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            onBlur={handleSave}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            maxLength={maxLength}
            disabled={isSaving}
            className="w-full px-3 py-2 border border-trig-green-500 rounded-md focus:outline-none focus:ring-2 focus:ring-trig-green-400 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500"
          />
        )
      ) : (
        <div
          className="group flex items-start gap-2 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 rounded-md -mx-2 px-2 py-1 transition-colors"
          onClick={() => setIsEditing(true)}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              setIsEditing(true);
            }
          }}
        >
          <p className="flex-1 text-gray-900 dark:text-gray-100 min-h-[2.5rem] flex items-center">
            {value || <span className="text-gray-400 dark:text-gray-500 italic">Not set</span>}
          </p>
          <div
            className="opacity-0 group-hover:opacity-100 transition-opacity p-1"
            title={`Edit ${label.toLowerCase()}`}
          >
            <svg
              className="w-4 h-4 text-gray-600 dark:text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"
              />
            </svg>
          </div>
        </div>
      )}
      
      {isSaving && (
        <span className="absolute right-0 top-0 text-xs text-gray-500 dark:text-gray-400">Saving...</span>
      )}
    </div>
  );
}

