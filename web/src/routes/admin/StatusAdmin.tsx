import { useState, useEffect, useCallback } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import { Plus, Pencil, Trash2 } from "lucide-react";
import toast from "react-hot-toast";

import Layout from "../../components/layout/Layout";
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
  Status,
  StatusCreateInput,
  StatusUpdateInput,
  fetchAllStatuses,
  createStatus,
  updateStatus,
  deleteStatus,
  fetchStatusUsage,
} from "../../lib/api";

const AUTH0_AUDIENCE = import.meta.env.VITE_AUTH0_AUDIENCE as string | undefined;
const ADMIN_SCOPE = "api:admin";
const BASE_SCOPES = "openid profile email api:write api:read-pii offline_access";
const ADMIN_AUTH_PARAMS: { scope: string; audience?: string } = AUTH0_AUDIENCE
  ? { audience: AUTH0_AUDIENCE, scope: `${BASE_SCOPES} ${ADMIN_SCOPE}` }
  : { scope: `${BASE_SCOPES} ${ADMIN_SCOPE}` };

// ============================================================================
// Status Row Component
// ============================================================================

interface StatusRowProps {
  status: Status;
  onEdit: (status: Status) => void;
  onDelete: (status: Status) => void;
}

function StatusRow({ status, onEdit, onDelete }: StatusRowProps) {
  return (
    <div className="flex items-center gap-3 py-3 px-4 bg-gray-50 dark:bg-gray-700/50 rounded-md group hover:bg-gray-100 dark:hover:bg-gray-700">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-3">
          <span className="font-mono text-sm bg-gray-200 dark:bg-gray-600 px-2 py-0.5 rounded">
            {status.id}
          </span>
          <span className="font-semibold text-gray-900 dark:text-gray-100">
            {status.name.trim()}
          </span>
        </div>
        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1 truncate">
          {status.descr}
        </p>
        {status.limit_descr && (
          <p className="text-xs text-gray-500 dark:text-gray-500 mt-0.5 truncate">
            {status.limit_descr}
          </p>
        )}
      </div>
      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onEdit(status)}
          className="p-1.5"
          aria-label={`Edit ${status.name}`}
        >
          <Pencil className="w-4 h-4" />
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onDelete(status)}
          className="p-1.5 text-red-600 hover:text-red-700 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20"
          aria-label={`Delete ${status.name}`}
        >
          <Trash2 className="w-4 h-4" />
        </Button>
      </div>
    </div>
  );
}

// ============================================================================
// Status Form Component
// ============================================================================

interface StatusFormProps {
  initialData?: Status;
  onSubmit: (data: StatusCreateInput | StatusUpdateInput) => Promise<void>;
  isSubmitting: boolean;
  mode: "create" | "edit";
}

function StatusForm({ initialData, onSubmit, isSubmitting, mode }: StatusFormProps) {
  const [id, setId] = useState(initialData?.id?.toString() ?? "");
  const [name, setName] = useState(initialData?.name?.trim() ?? "");
  const [descr, setDescr] = useState(initialData?.descr ?? "");
  const [limitDescr, setLimitDescr] = useState(initialData?.limit_descr ?? "");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (mode === "create") {
      const idNum = parseInt(id, 10);
      if (isNaN(idNum) || idNum < 0) {
        toast.error("ID must be a non-negative number");
        return;
      }
      await onSubmit({
        id: idNum,
        name: name.trim(),
        descr: descr.trim(),
        limit_descr: limitDescr.trim(),
      } as StatusCreateInput);
    } else {
      await onSubmit({
        name: name.trim() || undefined,
        descr: descr.trim() || undefined,
        limit_descr: limitDescr.trim() || undefined,
      } as StatusUpdateInput);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {mode === "create" && (
        <div className="space-y-2">
          <Label htmlFor="status-id" required>
            ID
          </Label>
          <Input
            id="status-id"
            type="number"
            min="0"
            value={id}
            onChange={(e) => setId(e.target.value)}
            placeholder="e.g. 10"
            required
          />
          <p className="text-xs text-gray-500">
            Unique numeric identifier for this status
          </p>
        </div>
      )}

      <div className="space-y-2">
        <Label htmlFor="status-name" required>
          Name
        </Label>
        <Input
          id="status-name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Good"
          maxLength={20}
          required
        />
        <p className="text-xs text-gray-500">
          Short name (max 20 characters)
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="status-descr" required>
          Description
        </Label>
        <Input
          id="status-descr"
          value={descr}
          onChange={(e) => setDescr(e.target.value)}
          placeholder="e.g. In good condition"
          maxLength={50}
          required
        />
        <p className="text-xs text-gray-500">
          Short description (max 50 characters)
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="status-limit-descr" required>
          Limit Description
        </Label>
        <Textarea
          id="status-limit-descr"
          value={limitDescr}
          onChange={(e) => setLimitDescr(e.target.value)}
          placeholder="Detailed description for filtering and display..."
          rows={3}
          maxLength={255}
          required
        />
        <p className="text-xs text-gray-500">
          Detailed description (max 255 characters)
        </p>
      </div>

      <DialogFooter>
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? (
            <>
              <Spinner size="sm" className="mr-2" />
              {mode === "create" ? "Creating..." : "Saving..."}
            </>
          ) : mode === "create" ? (
            "Create Status"
          ) : (
            "Save Changes"
          )}
        </Button>
      </DialogFooter>
    </form>
  );
}

// ============================================================================
// Main StatusAdmin Component
// ============================================================================

export default function StatusAdmin() {
  const { getAccessTokenSilently, isAuthenticated, loginWithRedirect } = useAuth0();

  const [statuses, setStatuses] = useState<Status[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Dialog states
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [editingStatus, setEditingStatus] = useState<Status | null>(null);
  const [deletingStatus, setDeletingStatus] = useState<Status | null>(null);
  const [deleteUsageCount, setDeleteUsageCount] = useState<number | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Fetch statuses
  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const token = await getAccessTokenSilently(ADMIN_AUTH_PARAMS);
      const data = await fetchAllStatuses(token);
      setStatuses(data);
    } catch (err) {
      console.error("Error fetching statuses:", err);
      setError(err instanceof Error ? err.message : "Failed to load statuses");
    } finally {
      setLoading(false);
    }
  }, [getAccessTokenSilently]);

  useEffect(() => {
    if (isAuthenticated) {
      fetchData();
    }
  }, [isAuthenticated, fetchData]);

  // Handlers
  const handleAddStatus = async (data: StatusCreateInput | StatusUpdateInput) => {
    try {
      setIsSubmitting(true);
      const token = await getAccessTokenSilently(ADMIN_AUTH_PARAMS);
      await createStatus(data as StatusCreateInput, token);
      toast.success("Status created successfully");
      setIsAddDialogOpen(false);
      await fetchData();
    } catch (err) {
      console.error("Error creating status:", err);
      toast.error(err instanceof Error ? err.message : "Failed to create status");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleEditStatus = async (data: StatusCreateInput | StatusUpdateInput) => {
    if (!editingStatus) return;
    try {
      setIsSubmitting(true);
      const token = await getAccessTokenSilently(ADMIN_AUTH_PARAMS);
      await updateStatus(editingStatus.id, data as StatusUpdateInput, token);
      toast.success("Status updated successfully");
      setEditingStatus(null);
      await fetchData();
    } catch (err) {
      console.error("Error updating status:", err);
      toast.error(err instanceof Error ? err.message : "Failed to update status");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteClick = async (status: Status) => {
    setDeletingStatus(status);
    setDeleteUsageCount(null);

    // Fetch usage count
    try {
      const token = await getAccessTokenSilently(ADMIN_AUTH_PARAMS);
      const usage = await fetchStatusUsage(status.id, token);
      setDeleteUsageCount(usage.usage_count);
    } catch (err) {
      console.error("Error fetching usage count:", err);
      setDeleteUsageCount(0);
    }
  };

  const handleConfirmDelete = async () => {
    if (!deletingStatus) return;
    try {
      setIsSubmitting(true);
      const token = await getAccessTokenSilently(ADMIN_AUTH_PARAMS);
      await deleteStatus(deletingStatus.id, token);
      toast.success("Status deleted successfully");
      setDeletingStatus(null);
      await fetchData();
    } catch (err) {
      console.error("Error deleting status:", err);
      toast.error(err instanceof Error ? err.message : "Failed to delete status");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Render
  if (!isAuthenticated) {
    return (
      <Layout>
        <div className="max-w-4xl mx-auto py-8 px-4">
          <Card className="p-8 text-center">
            <h2 className="text-xl font-semibold mb-4">Authentication Required</h2>
            <p className="text-gray-600 dark:text-gray-400 mb-4">
              You must be logged in as an administrator to access this page.
            </p>
            <Button onClick={() => loginWithRedirect()}>Log In</Button>
          </Card>
        </div>
      </Layout>
    );
  }

  if (loading) {
    return (
      <Layout>
        <div className="max-w-4xl mx-auto py-8 px-4">
          <div className="flex items-center justify-center py-12">
            <Spinner size="lg" />
            <span className="ml-3 text-gray-600 dark:text-gray-400">
              Loading statuses...
            </span>
          </div>
        </div>
      </Layout>
    );
  }

  if (error) {
    return (
      <Layout>
        <div className="max-w-4xl mx-auto py-8 px-4">
          <Card className="p-8 text-center">
            <h2 className="text-xl font-semibold text-red-600 mb-4">Error</h2>
            <p className="text-gray-600 dark:text-gray-400 mb-4">{error}</p>
            <Button onClick={fetchData}>Retry</Button>
          </Card>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="max-w-4xl mx-auto py-8 px-4">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              Status Management
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mt-1">
              Manage trigpoint condition statuses
            </p>
          </div>
          <Button onClick={() => setIsAddDialogOpen(true)}>
            <Plus className="w-4 h-4 mr-2" />
            Add Status
          </Button>
        </div>

        {/* Status List */}
        <Card className="p-4">
          {statuses.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              No statuses found. Click "Add Status" to create one.
            </div>
          ) : (
            <div className="space-y-2">
              {statuses.map((status) => (
                <StatusRow
                  key={status.id}
                  status={status}
                  onEdit={setEditingStatus}
                  onDelete={handleDeleteClick}
                />
              ))}
            </div>
          )}
        </Card>

        {/* Add Status Dialog */}
        <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add New Status</DialogTitle>
              <DialogDescription>
                Create a new trigpoint condition status.
              </DialogDescription>
            </DialogHeader>
            <StatusForm
              onSubmit={handleAddStatus}
              isSubmitting={isSubmitting}
              mode="create"
            />
          </DialogContent>
        </Dialog>

        {/* Edit Status Dialog */}
        <Dialog
          open={editingStatus !== null}
          onOpenChange={(open) => !open && setEditingStatus(null)}
        >
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Edit Status</DialogTitle>
              <DialogDescription>
                Update status details. ID cannot be changed.
              </DialogDescription>
            </DialogHeader>
            {editingStatus && (
              <StatusForm
                initialData={editingStatus}
                onSubmit={handleEditStatus}
                isSubmitting={isSubmitting}
                mode="edit"
              />
            )}
          </DialogContent>
        </Dialog>

        {/* Delete Confirmation Dialog */}
        <AlertDialog
          open={deletingStatus !== null}
          onOpenChange={(open) => !open && setDeletingStatus(null)}
          title="Delete Status"
          description={
            deleteUsageCount === null
              ? "Checking usage..."
              : deleteUsageCount > 0
                ? `This status is used by ${deleteUsageCount} trigpoint(s) and cannot be deleted.`
                : `Are you sure you want to delete "${deletingStatus?.name.trim()}"? This action cannot be undone.`
          }
          confirmLabel={deleteUsageCount === 0 ? "Delete" : "Close"}
          onConfirm={deleteUsageCount === 0 ? handleConfirmDelete : () => setDeletingStatus(null)}
          destructive={deleteUsageCount === 0}
        />
      </div>
    </Layout>
  );
}

