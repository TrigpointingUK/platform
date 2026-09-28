/**
 * ListsChip - Filter chip for filtering by membership of the user's trig lists
 *
 * "In" keeps trigs on any of the ticked lists, "Not in" keeps trigs on none
 * of them. The default list ("Marked" - the star) comes first and is ticked
 * automatically, so one click on "In" or "Not in" filters marked trigs.
 */

import { Bookmark, Star } from "lucide-react";
import { FilterChip, FilterListItem } from "../FilterChip";
import type { TrigListFull } from "../../../hooks/useTrigLists";
import { NO_LIST_FILTER, type ListFilter, type ListFilterMode } from "./listFilter";

export interface ListsChipProps {
  /** The signed-in user's lists (undefined while loading) */
  lists: TrigListFull[] | undefined;
  value: ListFilter;
  onChange: (value: ListFilter) => void;
}

const MODES: { mode: ListFilterMode; label: string }[] = [
  { mode: "all", label: "All" },
  { mode: "in", label: "In" },
  { mode: "not_in", label: "Not in" },
];

function describe(value: ListFilter, lists: TrigListFull[] | undefined): string {
  if (value.mode === "all") return "All";
  if (value.listIds.length === 0) return "Pick a list";
  const not = value.mode === "not_in";
  if (value.listIds.length === 1) {
    const list = lists?.find((l) => l.id === value.listIds[0]);
    if (list?.is_default) return not ? "Not marked" : "Marked";
    if (list) return `${not ? "Not in" : "In"} ${list.name}`;
  }
  return `${not ? "Not in" : "In"} ${value.listIds.length} lists`;
}

export function ListsChip({ lists, value, onChange }: ListsChipProps) {
  // Default list first, then the user's own order
  const ordered = [...(lists ?? [])].sort(
    (a, b) => Number(b.is_default) - Number(a.is_default) || a.position - b.position
  );
  const defaultListId = ordered.find((l) => l.is_default)?.id;

  const isActive = value.mode !== "all" && value.listIds.length > 0;
  const isWarning = value.mode !== "all" && value.listIds.length === 0;

  const setMode = (mode: ListFilterMode) => {
    if (mode === "all") {
      onChange({ mode, listIds: value.listIds });
      return;
    }
    // Nothing ticked yet: start from the Marked list
    const listIds =
      value.listIds.length === 0 && defaultListId !== undefined ? [defaultListId] : value.listIds;
    onChange({ mode, listIds });
  };

  const toggleList = (id: number) => {
    const listIds = value.listIds.includes(id)
      ? value.listIds.filter((l) => l !== id)
      : [...value.listIds, id];
    // Ticking a list while showing everything means "in this list"
    onChange({ mode: value.mode === "all" ? "in" : value.mode, listIds });
  };

  return (
    <FilterChip
      label="Lists"
      summary={describe(value, lists)}
      isActive={isActive}
      isWarning={isWarning}
      clearable={isActive || isWarning}
      onClear={() => onChange(NO_LIST_FILTER)}
      icon={<Bookmark className="w-3.5 h-3.5" />}
    >
      <div
        className="flex gap-1 px-3 py-2 border-b border-gray-200 dark:border-gray-700"
        role="radiogroup"
        aria-label="List filter"
      >
        {MODES.map(({ mode, label }) => (
          <button
            key={mode}
            type="button"
            role="radio"
            aria-checked={value.mode === mode}
            onClick={() => setMode(mode)}
            className={`px-2 py-1 text-xs font-medium rounded border transition-colors ${
              value.mode === mode
                ? "bg-trig-green-50 dark:bg-trig-green-900/30 border-trig-green-300 dark:border-trig-green-700 text-trig-green-700 dark:text-trig-green-300"
                : "border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {lists === undefined ? (
        <p className="px-3 py-2 text-xs text-gray-500 dark:text-gray-400">Loading lists…</p>
      ) : ordered.length === 0 ? (
        <p className="px-3 py-2 text-xs text-gray-500 dark:text-gray-400">
          You have no lists yet. Star a trigpoint to start your Marked list.
        </p>
      ) : (
        <div className={`py-1 ${value.mode === "all" ? "opacity-60" : ""}`}>
          {ordered.map((list) => (
            <FilterListItem
              key={list.id}
              label={list.name}
              checked={value.listIds.includes(list.id)}
              onChange={() => toggleList(list.id)}
              count={list.item_count}
              icon={
                list.is_default ? (
                  <Star className="w-4 h-4 text-trig-green-500 fill-trig-green-500 dark:text-trig-green-400 dark:fill-trig-green-400" />
                ) : (
                  <Bookmark className="w-4 h-4 text-gray-400" />
                )
              }
            />
          ))}
        </div>
      )}
    </FilterChip>
  );
}

export default ListsChip;
