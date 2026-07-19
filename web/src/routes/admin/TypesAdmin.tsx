import { useState, useEffect, useCallback } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import { Plus, Pencil, Trash2, ChevronDown, ChevronRight, GripVertical, ExternalLink } from "lucide-react";
import toast from "react-hot-toast";

import Card from "../../components/ui/Card";
import Button from "../../components/ui/Button";
import Spinner from "../../components/ui/Spinner";
import Input from "../../components/ui/Input";
import Label from "../../components/ui/Label";
import Textarea from "../../components/ui/Textarea";
import AlertDialog from "../../components/ui/AlertDialog";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "../../components/ui/Dialog";

import {
  TrigCategory,
  TrigCategoryWithTypes,
  TrigType,
  TrigCategoryCreateInput,
  TrigCategoryUpdateInput,
  TrigTypeCreateInput,
  TrigTypeUpdateInput,
  fetchCategoriesWithTypes,
  createCategory,
  updateCategory,
  deleteCategory,
  reorderCategories,
  createType,
  updateType,
  deleteType,
  reorderTypes,
  fetchTypeUsage,
} from "../../lib/api";

// DnD Kit imports
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

const AUTH0_AUDIENCE = import.meta.env.VITE_AUTH0_AUDIENCE as string | undefined;
const ADMIN_SCOPE = "api:admin";
const BASE_SCOPES = "openid profile email api:write api:read-pii offline_access";
const ADMIN_AUTH_PARAMS: { scope: string; audience?: string } = AUTH0_AUDIENCE
  ? { audience: AUTH0_AUDIENCE, scope: `${BASE_SCOPES} ${ADMIN_SCOPE}` }
  : { scope: `${BASE_SCOPES} ${ADMIN_SCOPE}` };

// ============================================================================
// Sortable Type Row Component
// ============================================================================

interface SortableTypeRowProps {
  type: TrigType;
  onEdit: (type: TrigType) => void;
  onDelete: (type: TrigType) => void;
}

function SortableTypeRow({ type, onEdit, onDelete }: SortableTypeRowProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: type.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="flex items-center gap-3 py-2 px-3 bg-gray-50 dark:bg-gray-700/50 rounded-md group hover:bg-gray-100 dark:hover:bg-gray-700"
    >
      <button
        type="button"
        className="cursor-grab active:cursor-grabbing text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
        {...attributes}
        {...listeners}
      >
        <GripVertical className="h-4 w-4" />
      </button>
      
      <div className="flex-1 min-w-0">
        <div className="font-medium text-gray-800 dark:text-gray-200 truncate">
          {type.name}
        </div>
        <div className="text-xs text-gray-500 dark:text-gray-400">
          Code: {type.code}
          {type.description && <span className="ml-2">• {type.description}</span>}
        </div>
      </div>

      {type.wiki_url && (
        <a
          href={type.wiki_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-gray-400 hover:text-trig-green-600 dark:hover:text-trig-green-400"
          title="View wiki page"
        >
          <ExternalLink className="h-4 w-4" />
        </a>
      )}

      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          type="button"
          onClick={() => onEdit(type)}
          className="p-1.5 rounded-md text-gray-500 hover:text-trig-green-600 hover:bg-trig-green-50 dark:hover:bg-trig-green-900/30"
          title="Edit type"
        >
          <Pencil className="h-4 w-4" />
        </button>
        <button
          type="button"
          onClick={() => onDelete(type)}
          className="p-1.5 rounded-md text-gray-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30"
          title="Delete type"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

// ============================================================================
// Sortable Category Card Component
// ============================================================================

interface SortableCategoryCardProps {
  category: TrigCategoryWithTypes;
  isExpanded: boolean;
  onToggle: () => void;
  onEditCategory: (category: TrigCategory) => void;
  onDeleteCategory: (category: TrigCategory) => void;
  onAddType: (categoryId: number) => void;
  onEditType: (type: TrigType) => void;
  onDeleteType: (type: TrigType) => void;
  onReorderTypes: (categoryId: number, newOrder: number[]) => void;
}

function SortableCategoryCard({
  category,
  isExpanded,
  onToggle,
  onEditCategory,
  onDeleteCategory,
  onAddType,
  onEditType,
  onDeleteType,
  onReorderTypes,
}: SortableCategoryCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: `category-${category.id}` });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleTypesDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (over && active.id !== over.id) {
      const oldIndex = category.types.findIndex((t) => t.id === active.id);
      const newIndex = category.types.findIndex((t) => t.id === over.id);
      const newOrder = arrayMove(category.types, oldIndex, newIndex).map((t) => t.id);
      onReorderTypes(category.id, newOrder);
    }
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden"
    >
      {/* Category Header */}
      <div className="flex items-center gap-3 p-4 bg-white dark:bg-gray-800">
        <button
          type="button"
          className="cursor-grab active:cursor-grabbing text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          {...attributes}
          {...listeners}
        >
          <GripVertical className="h-5 w-5" />
        </button>

        <button
          type="button"
          onClick={onToggle}
          className="flex items-center gap-2 text-left focus:outline-none"
        >
          {isExpanded ? (
            <ChevronDown className="h-5 w-5 text-gray-500" />
          ) : (
            <ChevronRight className="h-5 w-5 text-gray-500" />
          )}
          <span className="text-lg font-semibold text-gray-800 dark:text-gray-100">
            {category.name}
          </span>
          <span className="text-sm text-gray-500 dark:text-gray-400">
            ({category.types.length} type{category.types.length !== 1 ? "s" : ""})
          </span>
        </button>

        <div className="flex-1" />

        <div className="text-sm text-gray-500 dark:text-gray-400 hidden sm:block">
          {category.code}
        </div>

        {category.wiki_url && (
          <a
            href={category.wiki_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-gray-400 hover:text-trig-green-600 dark:hover:text-trig-green-400"
            title="View wiki page"
          >
            <ExternalLink className="h-4 w-4" />
          </a>
        )}

        <button
          type="button"
          onClick={() => onEditCategory(category)}
          className="p-1.5 rounded-md text-gray-500 hover:text-trig-green-600 hover:bg-trig-green-50 dark:hover:bg-trig-green-900/30"
          title="Edit category"
        >
          <Pencil className="h-4 w-4" />
        </button>
        <button
          type="button"
          onClick={() => onDeleteCategory(category)}
          className="p-1.5 rounded-md text-gray-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30"
          title="Delete category"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>

      {/* Category Content (Types) */}
      {isExpanded && (
        <div className="p-4 pt-0 bg-white dark:bg-gray-800 border-t border-gray-100 dark:border-gray-700">
          {category.description && (
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4 mt-2">
              {category.description}
            </p>
          )}

          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={handleTypesDragEnd}
          >
            <SortableContext
              items={category.types.map((t) => t.id)}
              strategy={verticalListSortingStrategy}
            >
              <div className="space-y-2">
                {category.types.map((type) => (
                  <SortableTypeRow
                    key={type.id}
                    type={type}
                    onEdit={onEditType}
                    onDelete={onDeleteType}
                  />
                ))}
              </div>
            </SortableContext>
          </DndContext>

          {category.types.length === 0 && (
            <p className="text-sm text-gray-500 dark:text-gray-400 italic py-4">
              No types in this category
            </p>
          )}

          <div className="mt-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onAddType(category.id)}
            >
              <Plus className="h-4 w-4 mr-1" />
              Add Type
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Main TypesAdmin Component
// ============================================================================

export default function TypesAdmin() {
  const { getAccessTokenSilently } = useAuth0();

  // Data state
  const [categories, setCategories] = useState<TrigCategoryWithTypes[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // UI state
  const [expandedCategories, setExpandedCategories] = useState<Set<number>>(new Set());

  // Category dialog state
  const [categoryDialogOpen, setCategoryDialogOpen] = useState(false);
  const [editingCategory, setEditingCategory] = useState<TrigCategory | null>(null);
  const [categoryForm, setCategoryForm] = useState<TrigCategoryCreateInput>({
    code: "",
    name: "",
    description: "",
    wiki_url: "",
  });
  const [categorySubmitting, setCategorySubmitting] = useState(false);

  // Type dialog state
  const [typeDialogOpen, setTypeDialogOpen] = useState(false);
  const [editingType, setEditingType] = useState<TrigType | null>(null);
  const [typeForm, setTypeForm] = useState<TrigTypeCreateInput>({
    category_id: 0,
    code: "",
    name: "",
    description: "",
    wiki_url: "",
  });
  const [typeSubmitting, setTypeSubmitting] = useState(false);

  // Delete confirmation state
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<{
    type: "category" | "type";
    item: TrigCategory | TrigType;
    usageCount?: number;
  } | null>(null);
  const [deleteSubmitting, setDeleteSubmitting] = useState(false);

  // DnD sensors
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  // ============================================================================
  // Data Loading
  // ============================================================================

  const loadCategories = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const token = await getAccessTokenSilently({
        authorizationParams: ADMIN_AUTH_PARAMS,
      });
      const data = await fetchCategoriesWithTypes(token);
      setCategories(data);
      // Expand all categories by default
      setExpandedCategories(new Set(data.map((c) => c.id)));
    } catch (err) {
      console.error("Failed to load categories:", err);
      setError(err instanceof Error ? err.message : "Failed to load data");
    } finally {
      setIsLoading(false);
    }
  }, [getAccessTokenSilently]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one-shot state sync on data load; re-render cost negligible (won't fix)
    loadCategories();
  }, [loadCategories]);

  // ============================================================================
  // Category Handlers
  // ============================================================================

  const handleAddCategory = () => {
    setEditingCategory(null);
    setCategoryForm({
      code: "",
      name: "",
      description: "",
      wiki_url: "",
    });
    setCategoryDialogOpen(true);
  };

  const handleEditCategory = (category: TrigCategory) => {
    setEditingCategory(category);
    setCategoryForm({
      code: category.code,
      name: category.name,
      description: category.description || "",
      wiki_url: category.wiki_url || "",
    });
    setCategoryDialogOpen(true);
  };

  const handleCategorySubmit = async () => {
    try {
      setCategorySubmitting(true);
      const token = await getAccessTokenSilently({
        authorizationParams: ADMIN_AUTH_PARAMS,
      });

      if (editingCategory) {
        const updates: TrigCategoryUpdateInput = {};
        if (categoryForm.code !== editingCategory.code) updates.code = categoryForm.code;
        if (categoryForm.name !== editingCategory.name) updates.name = categoryForm.name;
        if (categoryForm.description !== (editingCategory.description || ""))
          updates.description = categoryForm.description || null;
        if (categoryForm.wiki_url !== (editingCategory.wiki_url || ""))
          updates.wiki_url = categoryForm.wiki_url || null;

        await updateCategory(editingCategory.id, updates, token);
        toast.success("Category updated");
      } else {
        await createCategory(categoryForm, token);
        toast.success("Category created");
      }

      setCategoryDialogOpen(false);
      await loadCategories();
    } catch (err) {
      console.error("Failed to save category:", err);
      toast.error(err instanceof Error ? err.message : "Failed to save category");
    } finally {
      setCategorySubmitting(false);
    }
  };

  const handleDeleteCategory = (category: TrigCategory) => {
    const cat = categories.find((c) => c.id === category.id);
    const typeCount = cat?.types.length || 0;
    setDeleteTarget({
      type: "category",
      item: category,
      usageCount: typeCount,
    });
    setDeleteConfirmOpen(true);
  };

  const handleCategoriesDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const oldIndex = categories.findIndex(
      (c) => `category-${c.id}` === active.id
    );
    const newIndex = categories.findIndex(
      (c) => `category-${c.id}` === over.id
    );

    if (oldIndex === -1 || newIndex === -1) return;

    // Optimistic update
    const newCategories = arrayMove(categories, oldIndex, newIndex);
    setCategories(newCategories);

    // Save to server
    try {
      const token = await getAccessTokenSilently({
        authorizationParams: ADMIN_AUTH_PARAMS,
      });
      await reorderCategories(
        newCategories.map((c) => c.id),
        token
      );
      toast.success("Categories reordered");
    } catch (err) {
      console.error("Failed to reorder categories:", err);
      toast.error("Failed to reorder categories");
      // Revert on error
      await loadCategories();
    }
  };

  // ============================================================================
  // Type Handlers
  // ============================================================================

  const handleAddType = (categoryId: number) => {
    setEditingType(null);
    setTypeForm({
      category_id: categoryId,
      code: "",
      name: "",
      description: "",
      wiki_url: "",
    });
    setTypeDialogOpen(true);
  };

  const handleEditType = (type: TrigType) => {
    setEditingType(type);
    setTypeForm({
      category_id: type.category_id,
      code: type.code,
      name: type.name,
      description: type.description || "",
      wiki_url: type.wiki_url || "",
    });
    setTypeDialogOpen(true);
  };

  const handleTypeSubmit = async () => {
    try {
      setTypeSubmitting(true);
      const token = await getAccessTokenSilently({
        authorizationParams: ADMIN_AUTH_PARAMS,
      });

      if (editingType) {
        const updates: TrigTypeUpdateInput = {};
        if (typeForm.category_id !== editingType.category_id)
          updates.category_id = typeForm.category_id;
        if (typeForm.code !== editingType.code) updates.code = typeForm.code;
        if (typeForm.name !== editingType.name) updates.name = typeForm.name;
        if (typeForm.description !== (editingType.description || ""))
          updates.description = typeForm.description || null;
        if (typeForm.wiki_url !== (editingType.wiki_url || ""))
          updates.wiki_url = typeForm.wiki_url || null;

        await updateType(editingType.id, updates, token);
        toast.success("Type updated");
      } else {
        await createType(typeForm, token);
        toast.success("Type created");
      }

      setTypeDialogOpen(false);
      await loadCategories();
    } catch (err) {
      console.error("Failed to save type:", err);
      toast.error(err instanceof Error ? err.message : "Failed to save type");
    } finally {
      setTypeSubmitting(false);
    }
  };

  const handleDeleteType = async (type: TrigType) => {
    try {
      const token = await getAccessTokenSilently({
        authorizationParams: ADMIN_AUTH_PARAMS,
      });
      const usage = await fetchTypeUsage(type.id, token);
      setDeleteTarget({
        type: "type",
        item: type,
        usageCount: usage.usage_count,
      });
      setDeleteConfirmOpen(true);
    } catch (err) {
      console.error("Failed to check type usage:", err);
      // Proceed with delete dialog anyway
      setDeleteTarget({
        type: "type",
        item: type,
      });
      setDeleteConfirmOpen(true);
    }
  };

  const handleReorderTypes = async (categoryId: number, newOrder: number[]) => {
    // Optimistic update
    setCategories((prev) =>
      prev.map((cat) => {
        if (cat.id !== categoryId) return cat;
        const reorderedTypes = newOrder.map(
          (id) => cat.types.find((t) => t.id === id)!
        );
        return { ...cat, types: reorderedTypes };
      })
    );

    // Save to server
    try {
      const token = await getAccessTokenSilently({
        authorizationParams: ADMIN_AUTH_PARAMS,
      });
      await reorderTypes(categoryId, newOrder, token);
      toast.success("Types reordered");
    } catch (err) {
      console.error("Failed to reorder types:", err);
      toast.error("Failed to reorder types");
      // Revert on error
      await loadCategories();
    }
  };

  // ============================================================================
  // Delete Handler
  // ============================================================================

  const handleConfirmDelete = async () => {
    if (!deleteTarget) return;

    try {
      setDeleteSubmitting(true);
      const token = await getAccessTokenSilently({
        authorizationParams: ADMIN_AUTH_PARAMS,
      });

      if (deleteTarget.type === "category") {
        await deleteCategory(deleteTarget.item.id, token);
        toast.success("Category deleted");
      } else {
        await deleteType(deleteTarget.item.id, token);
        toast.success("Type deleted");
      }

      setDeleteConfirmOpen(false);
      setDeleteTarget(null);
      await loadCategories();
    } catch (err) {
      console.error("Failed to delete:", err);
      toast.error(err instanceof Error ? err.message : "Failed to delete");
    } finally {
      setDeleteSubmitting(false);
    }
  };

  // ============================================================================
  // UI Helpers
  // ============================================================================

  const toggleCategory = (categoryId: number) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(categoryId)) {
        next.delete(categoryId);
      } else {
        next.add(categoryId);
      }
      return next;
    });
  };

  // ============================================================================
  // Render
  // ============================================================================

  if (isLoading) {
    return (
      <>
        <title>Types Admin | TrigpointingUK</title>
        <div className="max-w-4xl mx-auto">
          <Card>
            <div className="flex items-center justify-center py-12">
              <Spinner size="lg" />
              <span className="ml-3 text-gray-600 dark:text-gray-400">
                Loading types and categories...
              </span>
            </div>
          </Card>
        </div>
      </>
    );
  }

  if (error) {
    return (
      <>
        <title>Types Admin | TrigpointingUK</title>
        <div className="max-w-4xl mx-auto">
          <Card>
            <div className="text-center py-12">
              <p className="text-red-600 dark:text-red-400 mb-4">{error}</p>
              <Button onClick={loadCategories}>Retry</Button>
            </div>
          </Card>
        </div>
      </>
    );
  }

  return (
    <>
      <title>Types Admin | TrigpointingUK</title>
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <Card className="mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-800 dark:text-gray-100">
                Types &amp; Categories
              </h1>
              <p className="text-gray-600 dark:text-gray-400 mt-1">
                Manage trigpoint physical types and categories
              </p>
            </div>
            <Button onClick={handleAddCategory}>
              <Plus className="h-4 w-4 mr-2" />
              Add Category
            </Button>
          </div>
        </Card>

        {/* Categories List */}
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={handleCategoriesDragEnd}
        >
          <SortableContext
            items={categories.map((c) => `category-${c.id}`)}
            strategy={verticalListSortingStrategy}
          >
            <div className="space-y-4">
              {categories.map((category) => (
                <SortableCategoryCard
                  key={category.id}
                  category={category}
                  isExpanded={expandedCategories.has(category.id)}
                  onToggle={() => toggleCategory(category.id)}
                  onEditCategory={handleEditCategory}
                  onDeleteCategory={handleDeleteCategory}
                  onAddType={handleAddType}
                  onEditType={handleEditType}
                  onDeleteType={handleDeleteType}
                  onReorderTypes={handleReorderTypes}
                />
              ))}
            </div>
          </SortableContext>
        </DndContext>

        {categories.length === 0 && (
          <Card>
            <div className="text-center py-12">
              <p className="text-gray-500 dark:text-gray-400 mb-4">
                No categories found. Create your first category to get started.
              </p>
              <Button onClick={handleAddCategory}>
                <Plus className="h-4 w-4 mr-2" />
                Add Category
              </Button>
            </div>
          </Card>
        )}
      </div>

      {/* Category Dialog */}
      <Dialog open={categoryDialogOpen} onOpenChange={setCategoryDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editingCategory ? "Edit Category" : "Add Category"}
            </DialogTitle>
            <DialogDescription>
              {editingCategory
                ? "Update the category details below."
                : "Fill in the details to create a new category."}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="category-code" required>
                Code
              </Label>
              <Input
                id="category-code"
                value={categoryForm.code}
                onChange={(e) =>
                  setCategoryForm((f) => ({ ...f, code: e.target.value }))
                }
                placeholder="e.g., PILLAR"
                maxLength={20}
              />
              <p className="text-xs text-gray-500 dark:text-gray-400">
                API-friendly identifier (uppercase, no spaces)
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="category-name" required>
                Name
              </Label>
              <Input
                id="category-name"
                value={categoryForm.name}
                onChange={(e) =>
                  setCategoryForm((f) => ({ ...f, name: e.target.value }))
                }
                placeholder="e.g., Pillar"
                maxLength={30}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="category-description">Description</Label>
              <Textarea
                id="category-description"
                value={categoryForm.description || ""}
                onChange={(e) =>
                  setCategoryForm((f) => ({ ...f, description: e.target.value }))
                }
                placeholder="Optional description..."
                maxLength={100}
                rows={2}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="category-wiki">Wiki URL</Label>
              <Input
                id="category-wiki"
                value={categoryForm.wiki_url || ""}
                onChange={(e) =>
                  setCategoryForm((f) => ({ ...f, wiki_url: e.target.value }))
                }
                placeholder="https://wiki.trigpointing.uk/..."
                maxLength={255}
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setCategoryDialogOpen(false)}
              disabled={categorySubmitting}
            >
              Cancel
            </Button>
            <Button
              onClick={handleCategorySubmit}
              disabled={
                categorySubmitting || !categoryForm.code || !categoryForm.name
              }
            >
              {categorySubmitting ? (
                <>
                  <Spinner size="sm" />
                  <span className="ml-2">Saving...</span>
                </>
              ) : editingCategory ? (
                "Update"
              ) : (
                "Create"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Type Dialog */}
      <Dialog open={typeDialogOpen} onOpenChange={setTypeDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingType ? "Edit Type" : "Add Type"}</DialogTitle>
            <DialogDescription>
              {editingType
                ? "Update the type details below."
                : "Fill in the details to create a new type."}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="type-category" required>
                Category
              </Label>
              <select
                id="type-category"
                value={typeForm.category_id}
                onChange={(e) =>
                  setTypeForm((f) => ({
                    ...f,
                    category_id: Number(e.target.value),
                  }))
                }
                className="flex h-10 w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-trig-green-500"
              >
                {categories.map((cat) => (
                  <option key={cat.id} value={cat.id}>
                    {cat.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="type-code" required>
                Code
              </Label>
              <Input
                id="type-code"
                value={typeForm.code}
                onChange={(e) =>
                  setTypeForm((f) => ({ ...f, code: e.target.value }))
                }
                placeholder="e.g., HOTINE"
                maxLength={20}
              />
              <p className="text-xs text-gray-500 dark:text-gray-400">
                API-friendly identifier (uppercase, no spaces)
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="type-name" required>
                Name
              </Label>
              <Input
                id="type-name"
                value={typeForm.name}
                onChange={(e) =>
                  setTypeForm((f) => ({ ...f, name: e.target.value }))
                }
                placeholder="e.g., Hotine Pillar"
                maxLength={30}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="type-description">Description</Label>
              <Textarea
                id="type-description"
                value={typeForm.description || ""}
                onChange={(e) =>
                  setTypeForm((f) => ({ ...f, description: e.target.value }))
                }
                placeholder="Optional description..."
                maxLength={100}
                rows={2}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="type-wiki">Wiki URL</Label>
              <Input
                id="type-wiki"
                value={typeForm.wiki_url || ""}
                onChange={(e) =>
                  setTypeForm((f) => ({ ...f, wiki_url: e.target.value }))
                }
                placeholder="https://wiki.trigpointing.uk/..."
                maxLength={255}
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setTypeDialogOpen(false)}
              disabled={typeSubmitting}
            >
              Cancel
            </Button>
            <Button
              onClick={handleTypeSubmit}
              disabled={
                typeSubmitting ||
                !typeForm.code ||
                !typeForm.name ||
                !typeForm.category_id
              }
            >
              {typeSubmitting ? (
                <>
                  <Spinner size="sm" />
                  <span className="ml-2">Saving...</span>
                </>
              ) : editingType ? (
                "Update"
              ) : (
                "Create"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog
        open={deleteConfirmOpen}
        onOpenChange={setDeleteConfirmOpen}
        title={`Delete ${deleteTarget?.type === "category" ? "Category" : "Type"}?`}
        description={
          deleteTarget?.type === "category"
            ? deleteTarget.usageCount && deleteTarget.usageCount > 0
              ? `This category has ${deleteTarget.usageCount} type(s). You must delete or move them first.`
              : `Are you sure you want to delete the category "${(deleteTarget.item as TrigCategory).name}"? This action cannot be undone.`
            : deleteTarget?.usageCount && deleteTarget.usageCount > 0
              ? `This type is used by ${deleteTarget.usageCount} trigpoint(s). You cannot delete it while it's in use.`
              : `Are you sure you want to delete the type "${(deleteTarget?.item as TrigType)?.name}"? This action cannot be undone.`
        }
        cancelText="Cancel"
        confirmText="Delete"
        variant="danger"
        onConfirm={handleConfirmDelete}
        confirmDisabled={
          deleteSubmitting ||
          (deleteTarget?.usageCount !== undefined && deleteTarget.usageCount > 0)
        }
      />
    </>
  );
}

