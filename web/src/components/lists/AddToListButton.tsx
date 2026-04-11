import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  useMyLists,
  useToggleDefaultList,
  useToggleListItem,
  useTrigListMembership,
  useCreateList,
  type TrigListFull,
} from "../../hooks/useTrigLists";

interface AddToListButtonProps {
  trigId: number;
}

export default function AddToListButton({ trigId }: AddToListButtonProps) {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [newListName, setNewListName] = useState("");
  const dropdownRef = useRef<HTMLDivElement>(null);

  const { data: lists } = useMyLists();
  const { data: memberships } = useTrigListMembership([trigId]);
  const toggleDefault = useToggleDefaultList(trigId);
  const toggleItem = useToggleListItem(trigId);
  const createList = useCreateList();

  const trigMembership = memberships?.find((m) => m.trig_id === trigId);
  const memberListIds = useMemo(
    () => new Set(trigMembership?.list_ids ?? []),
    [trigMembership?.list_ids],
  );

  const defaultList = lists?.find((l) => l.is_default);
  const isInDefaultList = defaultList ? memberListIds.has(defaultList.id) : false;

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    }
    if (dropdownOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [dropdownOpen]);

  const handleToggleDefault = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
      toggleDefault.mutate();
    },
    [toggleDefault],
  );

  const handleToggleDropdown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDropdownOpen((prev) => !prev);
    },
    [],
  );

  const handleListClick = useCallback(
    (list: TrigListFull, e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
      toggleItem.mutate({ listId: list.id });
    },
    [toggleItem],
  );

  const handleCreateList = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      e.stopPropagation();
      const trimmed = newListName.trim();
      if (!trimmed) return;
      createList.mutate({ name: trimmed });
      setNewListName("");
    },
    [createList, newListName],
  );

  return (
    <div className="relative inline-flex" ref={dropdownRef}>
      {/* Star button -- toggle default list */}
      <button
        type="button"
        onClick={handleToggleDefault}
        disabled={toggleDefault.isPending}
        className={`
          inline-flex items-center justify-center
          rounded-l-md border border-r-0 px-2.5 py-1.5
          text-sm font-medium transition-colors
          focus:outline-none focus:ring-2 focus:ring-trig-green-500 focus:ring-offset-1
          ${
            isInDefaultList
              ? "bg-trig-green-50 border-trig-green-300 text-trig-green-600 hover:bg-trig-green-100 dark:bg-trig-green-900/40 dark:border-trig-green-700 dark:text-trig-green-400 dark:hover:bg-trig-green-900/60"
              : "bg-white border-gray-300 text-gray-400 hover:bg-gray-50 hover:text-trig-green-500 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-500 dark:hover:bg-gray-700 dark:hover:text-trig-green-400"
          }
        `}
        title={isInDefaultList ? "Remove from Marked" : "Add to Marked"}
      >
        {isInDefaultList ? (
          <svg className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
          </svg>
        ) : (
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M11.48 3.499a.562.562 0 011.04 0l2.125 5.111a.563.563 0 00.475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 00-.182.557l1.285 5.385a.562.562 0 01-.84.61l-4.725-2.885a.563.563 0 00-.586 0L6.982 20.54a.562.562 0 01-.84-.61l1.285-5.386a.562.562 0 00-.182-.557l-4.204-3.602a.563.563 0 01.321-.988l5.518-.442a.563.563 0 00.475-.345L11.48 3.5z" />
          </svg>
        )}
      </button>

      {/* Dropdown toggle */}
      <button
        type="button"
        onClick={handleToggleDropdown}
        className={`
          inline-flex items-center justify-center
          rounded-r-md border px-1.5 py-1.5
          text-sm font-medium transition-colors
          focus:outline-none focus:ring-2 focus:ring-trig-green-500 focus:ring-offset-1
          bg-white border-gray-300 text-gray-500 hover:bg-gray-50
          dark:bg-gray-800 dark:border-gray-600 dark:text-gray-400 dark:hover:bg-gray-700
        `}
        title="Add to other lists"
        aria-expanded={dropdownOpen}
      >
        <svg className="w-3 h-3" viewBox="0 0 20 20" fill="currentColor">
          <path fillRule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clipRule="evenodd" />
        </svg>
      </button>

      {/* Dropdown menu */}
      {dropdownOpen && (
        <div className="absolute right-0 top-full z-50 mt-1 w-56 rounded-md bg-white shadow-lg ring-1 ring-black/5 dark:bg-gray-800 dark:ring-gray-700">
          <div className="py-1 max-h-60 overflow-y-auto">
            {lists && lists.length > 0 ? (
              lists.map((list) => {
                const isInList = memberListIds.has(list.id);
                return (
                  <button
                    key={list.id}
                    type="button"
                    onClick={(e) => handleListClick(list, e)}
                    className="flex w-full items-center gap-2 px-3 py-2 text-sm text-left transition-colors text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700"
                  >
                    <span className={`flex-shrink-0 w-4 h-4 rounded border flex items-center justify-center
                      ${isInList ? "bg-trig-green-600 border-trig-green-600" : "border-gray-300 dark:border-gray-600"}`}
                    >
                      {isInList && (
                        <svg className="w-3 h-3 text-white" viewBox="0 0 20 20" fill="currentColor">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      )}
                    </span>
                    <span className="truncate">{list.name}</span>
                    {list.is_default && (
                      <span className="ml-auto text-xs text-gray-400 dark:text-gray-500">default</span>
                    )}
                  </button>
                );
              })
            ) : (
              <div className="px-3 py-2 text-sm text-gray-500 dark:text-gray-400">
                No lists yet
              </div>
            )}
          </div>
          <div className="border-t border-gray-200 dark:border-gray-700 p-2">
            <form onSubmit={handleCreateList} className="flex gap-1">
              <input
                type="text"
                value={newListName}
                onChange={(e) => setNewListName(e.target.value)}
                placeholder="New list name..."
                className="flex-1 rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-2 py-1 text-sm text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:ring-1 focus:ring-trig-green-500 focus:border-trig-green-500"
                maxLength={100}
                onClick={(e) => e.stopPropagation()}
              />
              <button
                type="submit"
                disabled={!newListName.trim() || createList.isPending}
                className="rounded-md bg-trig-green-600 px-2 py-1 text-xs font-medium text-white hover:bg-trig-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Add
              </button>
            </form>
          </div>
          <div className="border-t border-gray-200 dark:border-gray-700 px-3 py-1.5">
            <Link
              to="/lists"
              className="text-xs text-trig-green-600 dark:text-trig-green-400 hover:underline"
            >
              View all lists →
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
