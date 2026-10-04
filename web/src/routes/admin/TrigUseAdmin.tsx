import { useState, useEffect, useCallback } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import { useQueryClient } from "@tanstack/react-query";
import { Plus, Pencil, Trash2 } from "lucide-react";
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
  TrigUse,
  TrigUseKind,
  TrigUseCreateInput,
  TrigUseUpdateInput,
  fetchAllTrigUses,
  createTrigUse,
  updateTrigUse,
  deleteTrigUse,
  fetchTrigUseUsage,
  requireAccessToken,
} from "../../lib/api";

const AUTH0_AUDIENCE = import.meta.env.VITE_AUTH0_AUDIENCE as string | undefined;
const ADMIN_SCOPE = "api:admin";
const BASE_SCOPES = "openid profile email api:write api:read-pii offline_access";
const ADMIN_AUTH_PARAMS: { scope: string; audience?: string } = AUTH0_AUDIENCE
  ? { audience: AUTH0_AUDIENCE, scope: `${BASE_SCOPES} ${ADMIN_SCOPE}` }
  : { scope: `${BASE_SCOPES} ${ADMIN_SCOPE}` };

// Per-kind wording; name lengths match the trig columns
const KINDS: Record<
  TrigUseKind,
  {
    title: string;
    singular: string;
    blurb: string;
    maxLength: number;
    example: string;
    referenceKey: string;
  }
> = {
  historic: {
    title: "Historic Use",
    singular: "historic use",
    blurb: "Manage the historic use values offered for trigpoints",
    maxLength: 30,
    example: "e.g. Primary",
    referenceKey: "historicUse",
  },
  current: {
    title: "Recent Use",
    singular: "recent use",
    blurb: "Manage the recent use values offered for trigpoints",
    maxLength: 25,
    example: "e.g. Passive station",
    referenceKey: "currentUse",
  },
};

// ============================================================================
// Row Component
// ============================================================================

interface TrigUseRowProps {
  value: TrigUse;
  onEdit: (value: TrigUse) => void;
  onDelete: (value: TrigUse) => void;
}

function TrigUseRow({ value, onEdit, onDelete }: TrigUseRowProps) {
  return (
    <div className="flex items-center gap-3 py-3 px-4 bg-gray-50 dark:bg-gray-700/50 rounded-md group hover:bg-gray-100 dark:hover:bg-gray-700">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-3">
          <span className="font-semibold text-gray-900 dark:text-gray-100">
            {value.name}
          </span>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            #{value.sort_order}
          </span>
        </div>
        {value.description && (
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1 truncate">
            {value.description}
          </p>
        )}
      </div>
      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          type="button"
          onClick={() => onEdit(value)}
          className="p-1.5 rounded-md text-gray-500 hover:text-trig-green-600 hover:bg-trig-green-50 dark:hover:bg-trig-green-900/30"
          title={`Edit ${value.name}`}
        >
          <Pencil className="h-4 w-4" />
        </button>
        <button
          type="button"
          onClick={() => onDelete(value)}
          className="p-1.5 rounded-md text-gray-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30"
          title={`Delete ${value.name}`}
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

// ============================================================================
// Form Component
// ============================================================================

interface TrigUseFormProps {
  kind: TrigUseKind;
  initialData?: TrigUse;
  defaultSortOrder?: number;
  onSubmit: (data: TrigUseCreateInput | TrigUseUpdateInput) => Promise<void>;
  isSubmitting: boolean;
  mode: "create" | "edit";
}

function TrigUseForm({
  kind,
  initialData,
  defaultSortOrder,
  onSubmit,
  isSubmitting,
  mode,
}: TrigUseFormProps) {
  const config = KINDS[kind];
  const [name, setName] = useState(initialData?.name ?? "");
  const [description, setDescription] = useState(initialData?.description ?? "");
  const [sortOrder, setSortOrder] = useState(
    (initialData?.sort_order ?? defaultSortOrder)?.toString() ?? ""
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const sortOrderNum = parseInt(sortOrder, 10);
    if (isNaN(sortOrderNum) || sortOrderNum < 0) {
      toast.error("Sort order must be a non-negative number");
      return;
    }
    if (!name.trim()) {
      toast.error("Name is required");
      return;
    }

    // Description is always sent so it can be cleared
    await onSubmit({
      name: name.trim(),
      description: description.trim(),
      sort_order: sortOrderNum,
    });
  };

  const renaming = mode === "edit" && name.trim() !== initialData?.name;

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="trig-use-name" required>
          Name
        </Label>
        <Input
          id="trig-use-name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder={config.example}
          maxLength={config.maxLength}
          required
        />
        <p className="text-xs text-gray-500">
          As shown on trigpoints (max {config.maxLength} characters)
        </p>
        {renaming && (
          <p className="text-xs text-amber-700 dark:text-amber-400">
            Every trigpoint with &quot;{initialData?.name}&quot; will be updated to
            the new name.
          </p>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="trig-use-sort-order" required>
          Sort Order
        </Label>
        <Input
          id="trig-use-sort-order"
          type="number"
          min="0"
          max="32767"
          value={sortOrder}
          onChange={(e) => setSortOrder(e.target.value)}
          placeholder="e.g. 10"
          required
        />
        <p className="text-xs text-gray-500">
          Order in dropdowns and filters (0-32767)
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="trig-use-description">Description</Label>
        <Textarea
          id="trig-use-description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Optional notes for admins..."
          rows={2}
          maxLength={255}
        />
        <p className="text-xs text-gray-500">Optional (max 255 characters)</p>
      </div>

      <DialogFooter>
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? (
            <>
              <span className="mr-2"><Spinner size="sm" /></span>
              {mode === "create" ? "Creating..." : "Saving..."}
            </>
          ) : mode === "create" ? (
            "Create Value"
          ) : (
            "Save Changes"
          )}
        </Button>
      </DialogFooter>
    </form>
  );
}

// ============================================================================
// Main TrigUseAdmin Component
// ============================================================================

interface TrigUseAdminProps {
  kind: TrigUseKind;
}

export default function TrigUseAdmin({ kind }: TrigUseAdminProps) {
  const { getAccessTokenSilently, isAuthenticated, loginWithRedirect } = useAuth0();
  const queryClient = useQueryClient();
  const config = KINDS[kind];

  const [values, setValues] = useState<TrigUse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Dialog states
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [editingValue, setEditingValue] = useState<TrigUse | null>(null);
  const [deletingValue, setDeletingValue] = useState<TrigUse | null>(null);
  const [deleteUsageCount, setDeleteUsageCount] = useState<number | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const getToken = useCallback(
    () =>
      requireAccessToken(getAccessTokenSilently, {
        authorizationParams: ADMIN_AUTH_PARAMS,
      }),
    [getAccessTokenSilently]
  );

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      setValues(await fetchAllTrigUses(kind, await getToken()));
    } catch (err) {
      console.error(`Error fetching ${config.singular} values:`, err);
      setError(err instanceof Error ? err.message : "Failed to load values");
    } finally {
      setLoading(false);
    }
  }, [kind, config.singular, getToken]);

  useEffect(() => {
    if (isAuthenticated) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- one-shot state sync on data load; re-render cost negligible (won't fix)
      fetchData();
    }
  }, [isAuthenticated, fetchData]);

  // Refresh the list here and the dropdowns/filters elsewhere in the app
  const afterChange = async () => {
    await queryClient.invalidateQueries({
      queryKey: ["reference", config.referenceKey],
    });
    await fetchData();
  };

  // Handlers
  const handleAdd = async (data: TrigUseCreateInput | TrigUseUpdateInput) => {
    try {
      setIsSubmitting(true);
      await createTrigUse(kind, data as TrigUseCreateInput, await getToken());
      toast.success("Value created successfully");
      setIsAddDialogOpen(false);
      await afterChange();
    } catch (err) {
      console.error(`Error creating ${config.singular}:`, err);
      toast.error(err instanceof Error ? err.message : "Failed to create value");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleEdit = async (data: TrigUseCreateInput | TrigUseUpdateInput) => {
    if (!editingValue) return;
    try {
      setIsSubmitting(true);
      await updateTrigUse(kind, editingValue.id, data, await getToken());
      toast.success("Value updated successfully");
      setEditingValue(null);
      await afterChange();
    } catch (err) {
      console.error(`Error updating ${config.singular}:`, err);
      toast.error(err instanceof Error ? err.message : "Failed to update value");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteClick = async (value: TrigUse) => {
    setDeletingValue(value);
    setDeleteUsageCount(null);

    try {
      const usage = await fetchTrigUseUsage(kind, value.id, await getToken());
      setDeleteUsageCount(usage.usage_count);
    } catch (err) {
      console.error("Error fetching usage count:", err);
      setDeleteUsageCount(0);
    }
  };

  const handleConfirmDelete = async () => {
    if (!deletingValue) return;
    try {
      setIsSubmitting(true);
      await deleteTrigUse(kind, deletingValue.id, await getToken());
      toast.success("Value deleted successfully");
      setDeletingValue(null);
      await afterChange();
    } catch (err) {
      console.error(`Error deleting ${config.singular}:`, err);
      toast.error(err instanceof Error ? err.message : "Failed to delete value");
    } finally {
      setIsSubmitting(false);
    }
  };

  const nextSortOrder =
    values.reduce((max, v) => Math.max(max, v.sort_order), 0) + 10;

  // Render
  if (!isAuthenticated) {
    return (
      <>
        <div className="max-w-4xl mx-auto py-8 px-4">
          <Card className="p-8 text-center">
            <h2 className="text-xl font-semibold mb-4">Authentication Required</h2>
            <p className="text-gray-600 dark:text-gray-400 mb-4">
              You must be logged in as an administrator to access this page.
            </p>
            <Button onClick={() => loginWithRedirect()}>Log In</Button>
          </Card>
        </div>
      </>
    );
  }

  if (loading) {
    return (
      <>
        <div className="max-w-4xl mx-auto py-8 px-4">
          <div className="flex items-center justify-center py-12">
            <Spinner size="lg" />
            <span className="ml-3 text-gray-600 dark:text-gray-400">
              Loading {config.singular} values...
            </span>
          </div>
        </div>
      </>
    );
  }

  if (error) {
    return (
      <>
        <div className="max-w-4xl mx-auto py-8 px-4">
          <Card className="p-8 text-center">
            <h2 className="text-xl font-semibold text-red-600 mb-4">Error</h2>
            <p className="text-gray-600 dark:text-gray-400 mb-4">{error}</p>
            <Button onClick={fetchData}>Retry</Button>
          </Card>
        </div>
      </>
    );
  }

  return (
    <>
      <title>{`${config.title} | Admin | TrigpointingUK`}</title>
      <div className="max-w-4xl mx-auto py-8 px-4">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              {config.title} Management
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mt-1">{config.blurb}</p>
          </div>
          <Button onClick={() => setIsAddDialogOpen(true)}>
            <Plus className="w-4 h-4 mr-2" />
            Add Value
          </Button>
        </div>

        {/* Value List */}
        <Card className="p-4">
          {values.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              No values found. Click "Add Value" to create one.
            </div>
          ) : (
            <div className="space-y-2">
              {values.map((value) => (
                <TrigUseRow
                  key={value.id}
                  value={value}
                  onEdit={setEditingValue}
                  onDelete={handleDeleteClick}
                />
              ))}
            </div>
          )}
        </Card>

        {/* Add Dialog */}
        <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add {config.title} Value</DialogTitle>
              <DialogDescription>
                Create a new {config.singular} value for trigpoints.
              </DialogDescription>
            </DialogHeader>
            <TrigUseForm
              kind={kind}
              defaultSortOrder={nextSortOrder}
              onSubmit={handleAdd}
              isSubmitting={isSubmitting}
              mode="create"
            />
          </DialogContent>
        </Dialog>

        {/* Edit Dialog */}
        <Dialog
          open={editingValue !== null}
          onOpenChange={(open) => !open && setEditingValue(null)}
        >
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Edit {config.title} Value</DialogTitle>
              <DialogDescription>Update this {config.singular} value.</DialogDescription>
            </DialogHeader>
            {editingValue && (
              <TrigUseForm
                kind={kind}
                initialData={editingValue}
                onSubmit={handleEdit}
                isSubmitting={isSubmitting}
                mode="edit"
              />
            )}
          </DialogContent>
        </Dialog>

        {/* Delete Confirmation Dialog */}
        <AlertDialog
          open={deletingValue !== null}
          onOpenChange={(open) => !open && setDeletingValue(null)}
          title={`Delete ${config.title} Value`}
          description={
            deleteUsageCount === null
              ? "Checking usage..."
              : deleteUsageCount > 0
                ? `This value is used by ${deleteUsageCount} trigpoint(s) and cannot be deleted.`
                : `Are you sure you want to delete "${deletingValue?.name}"? This action cannot be undone.`
          }
          confirmText={deleteUsageCount === 0 ? "Delete" : "Close"}
          onConfirm={deleteUsageCount === 0 ? handleConfirmDelete : () => setDeletingValue(null)}
          variant={deleteUsageCount === 0 ? "danger" : "default"}
        />
      </div>
    </>
  );
}
