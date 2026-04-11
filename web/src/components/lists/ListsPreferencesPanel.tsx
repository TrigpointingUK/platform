import { useCallback, useState } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import { Link } from "react-router-dom";
import {
  DndContext,
  DragEndEvent,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import Card from "../ui/Card";
import {
  useMyLists,
  useCreateList,
  useDeleteList,
  useUpdateList,
  useReorderLists,
  useSetDefaultList,
  type TrigListFull,
} from "../../hooks/useTrigLists";

const VISIBILITY_OPTIONS: { value: string; label: string; adminOnly?: boolean }[] = [
  { value: "private", label: "Private" },
  { value: "public", label: "Public" },
  { value: "admins", label: "Admins only", adminOnly: true },
];

const EDITABILITY_OPTIONS: { value: string; label: string; adminOnly?: boolean }[] = [
  { value: "private", label: "Owner only" },
  { value: "public", label: "Any user" },
  { value: "admins", label: "Admins only", adminOnly: true },
];

interface ListsPreferencesPanelProps {
  hasAdminRole: boolean;
}

// ---------------------------------------------------------------------------
// Sortable list tile
// ---------------------------------------------------------------------------

interface SortableListTileProps {
  list: TrigListFull;
  hasAdminRole: boolean;
  editingId: number | null;
  editName: string;
  editDescription: string;
  confirmDeleteId: number | null;
  onStartEditing: (list: TrigListFull) => void;
  onSaveEditing: () => void;
  onCancelEditing: () => void;
  onEditNameChange: (v: string) => void;
  onEditDescriptionChange: (v: string) => void;
  onVisibilityChange: (list: TrigListFull, value: string) => void;
  onEditabilityChange: (list: TrigListFull, value: string) => void;
  onConfirmDelete: (listId: number) => void;
  onCancelDelete: () => void;
  onDelete: (listId: number) => void;
  onSetDefault: (listId: number) => void;
}

function SortableListTile({
  list,
  hasAdminRole,
  editingId,
  editName,
  editDescription,
  confirmDeleteId,
  onStartEditing,
  onSaveEditing,
  onCancelEditing,
  onEditNameChange,
  onEditDescriptionChange,
  onVisibilityChange,
  onEditabilityChange,
  onConfirmDelete,
  onCancelDelete,
  onDelete,
  onSetDefault,
}: SortableListTileProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: list.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const isEditing = editingId === list.id;

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="border border-gray-200 dark:border-gray-700 rounded-lg p-3"
    >
      <div className="flex items-start justify-between gap-3">
        {/* Drag handle */}
        <button
          type="button"
          className="mt-0.5 cursor-grab touch-none text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300"
          {...attributes}
          {...listeners}
          title="Drag to reorder"
        >
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
            <circle cx="9" cy="5" r="1.5" />
            <circle cx="15" cy="5" r="1.5" />
            <circle cx="9" cy="12" r="1.5" />
            <circle cx="15" cy="12" r="1.5" />
            <circle cx="9" cy="19" r="1.5" />
            <circle cx="15" cy="19" r="1.5" />
          </svg>
        </button>

        <div className="flex-1 min-w-0">
          {isEditing ? (
            <div className="space-y-2">
              <input
                type="text"
                value={editName}
                onChange={(e) => onEditNameChange(e.target.value)}
                className="w-full px-2 py-1 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm focus:ring-trig-green-500 focus:border-trig-green-500"
                maxLength={100}
                autoFocus
              />
              <input
                type="text"
                value={editDescription}
                onChange={(e) => onEditDescriptionChange(e.target.value)}
                placeholder="Description (optional)"
                className="w-full px-2 py-1 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm focus:ring-trig-green-500 focus:border-trig-green-500"
                maxLength={200}
              />
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={onSaveEditing}
                  className="px-2 py-1 text-xs font-medium rounded-md bg-trig-green-600 text-white hover:bg-trig-green-700"
                >
                  Save
                </button>
                <button
                  type="button"
                  onClick={onCancelEditing}
                  className="px-2 py-1 text-xs font-medium rounded-md bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-300 dark:hover:bg-gray-500"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <Link to={`/lists/${list.id}`} className="block group">
              <div className="flex items-center gap-2">
                <span className="font-medium text-gray-900 dark:text-gray-100 text-sm group-hover:text-trig-green-600 dark:group-hover:text-trig-green-400 transition-colors">
                  {list.name}
                </span>
                {list.is_default && (
                  <span className="text-xs bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-400 px-1.5 py-0.5 rounded">
                    default
                  </span>
                )}
                <span className="text-xs text-gray-400 dark:text-gray-500">
                  {list.item_count} {list.item_count === 1 ? "item" : "items"}
                </span>
              </div>
              {list.description && (
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                  {list.description}
                </p>
              )}
            </Link>
          )}
        </div>

        {!isEditing && (
          <div className="flex items-center gap-1 flex-shrink-0">
            {!list.is_default && (
              <button
                type="button"
                onClick={() => onSetDefault(list.id)}
                className="px-1.5 py-0.5 text-xs font-medium rounded text-gray-500 hover:text-amber-600 hover:bg-amber-50 dark:text-gray-400 dark:hover:text-amber-400 dark:hover:bg-amber-900/30 transition-colors"
                title="Set as default list"
              >
                Make default
              </button>
            )}
            <button
              type="button"
              onClick={() => onStartEditing(list)}
              className="p-1 text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300"
              title="Edit list"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125" />
              </svg>
            </button>
            {confirmDeleteId === list.id ? (
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => onDelete(list.id)}
                  className="px-1.5 py-0.5 text-xs font-medium rounded bg-red-600 text-white hover:bg-red-700"
                >
                  Confirm
                </button>
                <button
                  type="button"
                  onClick={onCancelDelete}
                  className="px-1.5 py-0.5 text-xs font-medium rounded bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-200"
                >
                  No
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => onConfirmDelete(list.id)}
                className="p-1 text-gray-400 hover:text-red-500 dark:text-gray-500 dark:hover:text-red-400"
                title="Delete list"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
                </svg>
              </button>
            )}
          </div>
        )}
      </div>

      {/* Visibility & editability */}
      {!isEditing && (
        <div className="flex flex-wrap gap-3 mt-2 ml-7">
          <div className="flex items-center gap-1.5">
            <label className="text-xs text-gray-500 dark:text-gray-400">Visible to:</label>
            <select
              value={list.visibility}
              onChange={(e) => onVisibilityChange(list, e.target.value)}
              className="text-xs px-1.5 py-0.5 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200"
            >
              {VISIBILITY_OPTIONS.filter(
                (o) => !o.adminOnly || hasAdminRole,
              ).map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-1.5">
            <label className="text-xs text-gray-500 dark:text-gray-400">Editable by:</label>
            <select
              value={list.editability}
              onChange={(e) => onEditabilityChange(list, e.target.value)}
              className="text-xs px-1.5 py-0.5 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200"
            >
              {EDITABILITY_OPTIONS.filter(
                (o) => !o.adminOnly || hasAdminRole,
              ).map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main panel
// ---------------------------------------------------------------------------

export default function ListsPreferencesPanel({ hasAdminRole }: ListsPreferencesPanelProps) {
  const { isAuthenticated } = useAuth0();
  const { data: lists, isLoading } = useMyLists();
  const createList = useCreateList();
  const deleteList = useDeleteList();
  const updateList = useUpdateList();
  const reorderLists = useReorderLists();
  const setDefaultList = useSetDefaultList();

  const [newListName, setNewListName] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const handleCreate = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      const trimmed = newListName.trim();
      if (!trimmed) return;
      createList.mutate({ name: trimmed });
      setNewListName("");
    },
    [createList, newListName],
  );

  const startEditing = useCallback((list: TrigListFull) => {
    setEditingId(list.id);
    setEditName(list.name);
    setEditDescription(list.description ?? "");
  }, []);

  const saveEditing = useCallback(() => {
    if (editingId == null) return;
    updateList.mutate({
      listId: editingId,
      data: { name: editName.trim() || undefined, description: editDescription.trim() || undefined },
    });
    setEditingId(null);
  }, [editingId, editName, editDescription, updateList]);

  const handleVisibilityChange = useCallback(
    (list: TrigListFull, value: string) => {
      updateList.mutate({ listId: list.id, data: { visibility: value } });
    },
    [updateList],
  );

  const handleEditabilityChange = useCallback(
    (list: TrigListFull, value: string) => {
      updateList.mutate({ listId: list.id, data: { editability: value } });
    },
    [updateList],
  );

  const handleDelete = useCallback(
    (listId: number) => {
      deleteList.mutate(listId);
      setConfirmDeleteId(null);
    },
    [deleteList],
  );

  const handleSetDefault = useCallback(
    (listId: number) => {
      setDefaultList.mutate(listId);
    },
    [setDefaultList],
  );

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;
      if (!over || active.id === over.id || !lists) return;

      const oldIndex = lists.findIndex((l) => l.id === active.id);
      const newIndex = lists.findIndex((l) => l.id === over.id);
      if (oldIndex === -1 || newIndex === -1) return;

      const reordered = arrayMove(lists, oldIndex, newIndex);
      const ordering = reordered.map((l, i) => ({
        list_id: l.id,
        position: (i + 1) * 1000,
      }));
      reorderLists.mutate({ ordering });
    },
    [lists, reorderLists],
  );

  if (!isAuthenticated) return null;

  return (
    <Card className="mb-6" id="trig-lists">
      <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
        Trig Lists
      </h2>
      <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
        Manage your lists of trigpoints. Use lists to bookmark favourites, plan visits, or organise trigs however you like.
        {" "}
        <Link
          to="/lists"
          className="text-trig-green-600 dark:text-trig-green-400 hover:underline font-medium"
        >
          View your lists →
        </Link>
      </p>

      {isLoading ? (
        <div className="text-center py-4 text-gray-500 dark:text-gray-400 text-sm">
          Loading lists...
        </div>
      ) : (
        <div className="space-y-3">
          {lists && lists.length > 0 ? (
            <DndContext
              sensors={sensors}
              collisionDetection={closestCenter}
              onDragEnd={handleDragEnd}
            >
              <SortableContext
                items={lists.map((l) => l.id)}
                strategy={verticalListSortingStrategy}
              >
                <div className="space-y-3">
                  {lists.map((list) => (
                    <SortableListTile
                      key={list.id}
                      list={list}
                      hasAdminRole={hasAdminRole}
                      editingId={editingId}
                      editName={editName}
                      editDescription={editDescription}
                      confirmDeleteId={confirmDeleteId}
                      onStartEditing={startEditing}
                      onSaveEditing={saveEditing}
                      onCancelEditing={() => setEditingId(null)}
                      onEditNameChange={setEditName}
                      onEditDescriptionChange={setEditDescription}
                      onVisibilityChange={handleVisibilityChange}
                      onEditabilityChange={handleEditabilityChange}
                      onConfirmDelete={setConfirmDeleteId}
                      onCancelDelete={() => setConfirmDeleteId(null)}
                      onDelete={handleDelete}
                      onSetDefault={handleSetDefault}
                    />
                  ))}
                </div>
              </SortableContext>
            </DndContext>
          ) : (
            <p className="text-sm text-gray-500 dark:text-gray-400 py-2">
              You have no lists yet. Create one below, or use the star button on a trigpoint page to get started.
            </p>
          )}

          {/* Create new list */}
          <form onSubmit={handleCreate} className="flex gap-2 pt-2">
            <input
              type="text"
              value={newListName}
              onChange={(e) => setNewListName(e.target.value)}
              placeholder="New list name..."
              className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm placeholder-gray-400 dark:placeholder-gray-500 focus:ring-trig-green-500 focus:border-trig-green-500"
              maxLength={100}
            />
            <button
              type="submit"
              disabled={!newListName.trim() || createList.isPending}
              className="px-4 py-2 text-sm font-medium rounded-md bg-trig-green-600 text-white hover:bg-trig-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Create
            </button>
          </form>
        </div>
      )}
    </Card>
  );
}
