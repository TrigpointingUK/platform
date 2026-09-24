/**
 * LogsChip - Filter chip for filtering by a user's logged status
 *
 * Whose logs: "me" (the signed-in user) by default, or any user picked by
 * name - e.g. to check someone's extant pillar total.
 *
 * Two-tier structure:
 * - "Logged by <user>" expands to show individual conditions
 * - "Not logged by <user>" is a simple toggle
 */

import { useState } from "react";
import { CheckCircle, ChevronRight, ChevronDown, Search, X } from "lucide-react";
import { FilterChip, FilterListItem, FilterCheckbox } from "../FilterChip";
import { useUserSearch } from "../../../hooks/useUserSearch";
import { useConditions } from "../../../hooks/useReferenceData";

export interface LogUser {
  id: number;
  name: string;
}

export interface LogsChipProps {
  selectedLoggedConditions: string[];
  showNotLogged: boolean;
  onToggleLoggedCondition: (code: string) => void;
  onToggleNotLogged: () => void;
  onSelectAllLogged: () => void;
  onSelectNoneLogged: () => void;
  isAuthenticated: boolean;
  /** Another user whose logs to filter on; null means the signed-in user */
  logUser: LogUser | null;
  onLogUserChange: (user: LogUser | null) => void;
}

function LogUserPicker({
  logUser,
  onLogUserChange,
  isAuthenticated,
}: Pick<LogsChipProps, "logUser" | "onLogUserChange" | "isAuthenticated">) {
  const [query, setQuery] = useState("");
  const { data: results, isLoading } = useUserSearch(query);

  const choose = (user: LogUser | null) => {
    onLogUserChange(user);
    setQuery("");
  };

  return (
    <div className="px-3 py-2 border-b border-gray-200 dark:border-gray-700">
      <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1.5">
        Whose logs
      </div>
      <div className="flex items-center gap-2 mb-2">
        {isAuthenticated && (
          <button
            type="button"
            onClick={() => choose(null)}
            className={`px-2 py-1 text-xs font-medium rounded border transition-colors ${
              logUser === null
                ? "bg-trig-green-50 dark:bg-trig-green-900/30 border-trig-green-300 dark:border-trig-green-700 text-trig-green-700 dark:text-trig-green-300"
                : "border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
            }`}
          >
            Me
          </button>
        )}
        {logUser && (
          <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded border bg-trig-green-50 dark:bg-trig-green-900/30 border-trig-green-300 dark:border-trig-green-700 text-trig-green-700 dark:text-trig-green-300">
            {logUser.name}
            <button
              type="button"
              onClick={() => choose(null)}
              aria-label={`Stop filtering on ${logUser.name}'s logs`}
              className="hover:text-trig-green-900 dark:hover:text-trig-green-100"
            >
              <X className="w-3 h-3" />
            </button>
          </span>
        )}
      </div>
      <div className="relative">
        <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Find a user…"
          aria-label="Find a user"
          className="w-full pl-7 pr-2 py-1 text-sm border border-gray-300 dark:border-gray-600
                     rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100
                     focus:ring-1 focus:ring-trig-green-500 focus:border-trig-green-500"
        />
      </div>
      {query.length >= 2 && (
        <ul className="mt-1 max-h-48 overflow-y-auto">
          {isLoading && (
            <li className="px-2 py-1 text-xs text-gray-500 dark:text-gray-400">Searching…</li>
          )}
          {!isLoading && results?.length === 0 && (
            <li className="px-2 py-1 text-xs text-gray-500 dark:text-gray-400">No users found</li>
          )}
          {results?.map((user) => (
            <li key={user.id}>
              <button
                type="button"
                onClick={() => choose({ id: user.id, name: user.name })}
                className="w-full flex items-center justify-between px-2 py-1 text-left text-sm rounded
                           text-gray-800 dark:text-gray-200 hover:bg-trig-green-50 dark:hover:bg-gray-700"
              >
                <span className="truncate">{user.name}</span>
                <span className="text-xs text-gray-500 dark:text-gray-400 flex-shrink-0 ml-2">
                  {user.stats.total_trigs_logged.toLocaleString("en-GB")} trigs
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function LogsChip({
  selectedLoggedConditions,
  showNotLogged,
  onToggleLoggedCondition,
  onToggleNotLogged,
  onSelectAllLogged,
  onSelectNoneLogged,
  isAuthenticated,
  logUser,
  onLogUserChange,
}: LogsChipProps) {
  const [isLoggedExpanded, setIsLoggedExpanded] = useState(false);

  // Signed out and nobody picked: there are no logs to filter on yet
  const hasLogUser = logUser !== null || isAuthenticated;
  const who = logUser ? logUser.name : "me";

  // Log conditions come from the conditions API, so every code in use is listed
  const { data: conditions } = useConditions();
  const conditionCount = conditions?.length ?? 0;
  const allLoggedSelected = selectedLoggedConditions.length >= conditionCount;
  const someLoggedSelected = selectedLoggedConditions.length > 0;
  const isPartialLogged = someLoggedSelected && !allLoggedSelected;

  // Generate summary
  let summary: string;
  if (!hasLogUser) {
    summary = "Pick a user";
  } else if (allLoggedSelected && showNotLogged) {
    summary = logUser ? logUser.name : "All";
  } else if (!someLoggedSelected && !showNotLogged) {
    summary = "None";
  } else if (!someLoggedSelected && showNotLogged) {
    summary = `Not logged by ${who}`;
  } else if (allLoggedSelected && !showNotLogged) {
    summary = `Logged by ${who}`;
  } else if (someLoggedSelected && !showNotLogged) {
    summary = `${selectedLoggedConditions.length} logged conditions`;
  } else {
    // Some logged conditions + not logged
    summary = `${selectedLoggedConditions.length} logged conditions +`;
  }

  // Active when filtered (not showing everything) or looking at someone else
  const isFiltered = !(allLoggedSelected && showNotLogged);
  const isActive = hasLogUser && (isFiltered || logUser !== null);
  // Warning when nothing is selected
  const isWarning = hasLogUser && !someLoggedSelected && !showNotLogged;

  const handleClear = () => {
    // Reset to showing all, for the signed-in user
    onSelectAllLogged();
    if (!showNotLogged) onToggleNotLogged();
    onLogUserChange(null);
  };

  const handleShowAll = () => {
    onSelectAllLogged();
    if (!showNotLogged) onToggleNotLogged();
  };

  const handleToggleAllLogged = () => {
    if (allLoggedSelected) {
      onSelectNoneLogged();
    } else {
      onSelectAllLogged();
    }
  };

  return (
    <FilterChip
      label="Logs"
      summary={summary}
      isActive={isActive}
      isWarning={isWarning}
      clearable={isActive || isWarning}
      onClear={handleClear}
      popoverWidth="lg"
      icon={<CheckCircle className="w-3.5 h-3.5" />}
    >
      <LogUserPicker
        logUser={logUser}
        onLogUserChange={onLogUserChange}
        isAuthenticated={isAuthenticated}
      />

      {!hasLogUser ? (
        <p className="px-3 py-2 text-xs text-gray-500 dark:text-gray-400">
          Pick a user to filter by their logs.
        </p>
      ) : (
        <>
          {/* Quick selection shortcuts */}
          <div className="px-3 py-2 border-b border-gray-200 dark:border-gray-700 flex gap-2">
            <button
              type="button"
              onClick={handleShowAll}
              className="px-2 py-1 text-xs font-medium text-gray-600 dark:text-gray-400
                         hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
            >
              All
            </button>
            <button
              type="button"
              onClick={() => {
                onSelectAllLogged();
                if (showNotLogged) onToggleNotLogged();
              }}
              className="px-2 py-1 text-xs font-medium text-trig-green-600 dark:text-trig-green-400
                         hover:bg-trig-green-50 dark:hover:bg-trig-green-900/30 rounded transition-colors"
            >
              Logged only
            </button>
            <button
              type="button"
              onClick={() => {
                onSelectNoneLogged();
                if (!showNotLogged) onToggleNotLogged();
              }}
              className="px-2 py-1 text-xs font-medium text-gray-600 dark:text-gray-400
                         hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
            >
              Not logged only
            </button>
          </div>
          <div className="py-1">
            {/* Not logged - simple toggle (at top) */}
            <div className="flex items-center px-3 py-2 hover:bg-trig-green-50 dark:hover:bg-gray-800 transition-colors">
              {/* Spacer to align with expand button below */}
              <div className="w-4 h-4 p-0.5 mr-1" />
              <label className="flex items-center gap-2 cursor-pointer flex-1">
                <FilterCheckbox
                  checked={showNotLogged}
                  onChange={onToggleNotLogged}
                  ariaLabel={`Not logged by ${who}`}
                />
                <img src="/icons/mapicon_pillar_grey.png" alt="" className="w-5 h-5" />
                <span className="text-sm text-gray-800 dark:text-gray-200">
                  Not logged by {who}
                </span>
              </label>
            </div>

            {/* Logged - expandable */}
            <div>
              <div className="flex items-center px-3 py-2 hover:bg-trig-green-50 dark:hover:bg-gray-800">
                {/* Expand/collapse button */}
                <button
                  type="button"
                  onClick={() => setIsLoggedExpanded(!isLoggedExpanded)}
                  aria-label={isLoggedExpanded ? "Hide logged conditions" : "Show logged conditions"}
                  className="p-0.5 mr-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                >
                  {isLoggedExpanded ? (
                    <ChevronDown className="w-4 h-4" />
                  ) : (
                    <ChevronRight className="w-4 h-4" />
                  )}
                </button>

                {/* Logged checkbox */}
                <label className="flex items-center gap-2 cursor-pointer flex-1">
                  <FilterCheckbox
                    checked={allLoggedSelected}
                    indeterminate={isPartialLogged}
                    onChange={handleToggleAllLogged}
                    ariaLabel={`Logged by ${who}`}
                  />
                  <div className="flex -space-x-1">
                    <img src="/icons/mapicon_pillar_green.png" alt="" className="w-5 h-5" />
                    <img src="/icons/mapicon_pillar_yellow.png" alt="" className="w-5 h-5" />
                    <img src="/icons/mapicon_pillar_red.png" alt="" className="w-5 h-5" />
                  </div>
                  <span className="text-sm font-medium text-gray-800 dark:text-gray-200">
                    Logged by {who}
                  </span>
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    ({selectedLoggedConditions.length}/{conditionCount})
                  </span>
                </label>
              </div>

              {/* Expanded conditions */}
              {isLoggedExpanded && (
                <div className="pl-4">
                  {conditions?.map((condition) => (
                    <FilterListItem
                      key={condition.code}
                      label={condition.name}
                      checked={selectedLoggedConditions.includes(condition.code)}
                      onChange={() => onToggleLoggedCondition(condition.code)}
                      icon={
                        <img
                          src={`/icons/conditions/${condition.icon_file || "c_unknown.png"}`}
                          alt=""
                          className="w-5 h-5 object-contain"
                        />
                      }
                      indented
                    />
                  ))}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </FilterChip>
  );
}

export default LogsChip;
