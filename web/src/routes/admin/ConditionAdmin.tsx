import { useState, useEffect, useCallback } from "react";
import { useAuth0 } from "@auth0/auth0-react";
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
  Condition,
  ConditionCreateInput,
  ConditionUpdateInput,
  fetchAllConditions,
  createCondition,
  updateCondition,
  deleteCondition,
  fetchConditionUsage,
} from "../../lib/api";

const AUTH0_AUDIENCE = import.meta.env.VITE_AUTH0_AUDIENCE as string | undefined;
const ADMIN_SCOPE = "api:admin";
const BASE_SCOPES = "openid profile email api:write api:read-pii offline_access";
const ADMIN_AUTH_PARAMS: { scope: string; audience?: string } = AUTH0_AUDIENCE
  ? { audience: AUTH0_AUDIENCE, scope: `${BASE_SCOPES} ${ADMIN_SCOPE}` }
  : { scope: `${BASE_SCOPES} ${ADMIN_SCOPE}` };

// ============================================================================
// Condition Row Component
// ============================================================================

interface ConditionRowProps {
  condition: Condition;
  onEdit: (condition: Condition) => void;
  onDelete: (condition: Condition) => void;
}

function ConditionRow({ condition, onEdit, onDelete }: ConditionRowProps) {
  return (
    <div className="flex items-center gap-3 py-3 px-4 bg-gray-50 dark:bg-gray-700/50 rounded-md group hover:bg-gray-100 dark:hover:bg-gray-700">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-3 flex-wrap">
          <span className="font-mono text-sm bg-gray-200 dark:bg-gray-600 px-2 py-0.5 rounded font-bold">
            {condition.code}
          </span>
          {condition.icon_file && (
            <img
              src={`/icons/conditions/${condition.icon_file}`}
              alt={condition.name}
              className="w-5 h-5"
            />
          )}
          {condition.trig_colour && (
            <span
              className="px-2 py-0.5 text-xs rounded"
              style={{
                backgroundColor: condition.trig_colour,
                color: ["white", "yellow", "lime", "cyan", "aqua"].includes(
                  condition.trig_colour.toLowerCase()
                )
                  ? "black"
                  : "white",
              }}
            >
              trig
            </span>
          )}
          {condition.log_colour && (
            <span
              className="px-2 py-0.5 text-xs rounded"
              style={{
                backgroundColor: condition.log_colour,
                color: ["white", "yellow", "lime", "cyan", "aqua"].includes(
                  condition.log_colour.toLowerCase()
                )
                  ? "black"
                  : "white",
              }}
            >
              log
            </span>
          )}
          <span className="font-semibold text-gray-900 dark:text-gray-100">
            {condition.name}
          </span>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            #{condition.sort_order}
          </span>
        </div>
        {condition.description && (
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            {condition.description}
          </p>
        )}
        <div className="flex items-center gap-4 mt-1 text-xs text-gray-500 dark:text-gray-500">
          <span>Similar: {condition.similar_codes}</span>
          {condition.wiki_url && (
            <a
              href={condition.wiki_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 dark:text-blue-400 hover:underline"
            >
              Wiki
            </a>
          )}
        </div>
      </div>
      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onEdit(condition)}
          className="p-1.5"
          aria-label={`Edit ${condition.name}`}
        >
          <Pencil className="w-4 h-4" />
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onDelete(condition)}
          className="p-1.5 text-red-600 hover:text-red-700 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20"
          aria-label={`Delete ${condition.name}`}
        >
          <Trash2 className="w-4 h-4" />
        </Button>
      </div>
    </div>
  );
}

// ============================================================================
// Condition Form Component
// ============================================================================

interface ConditionFormProps {
  initialData?: Condition;
  onSubmit: (data: ConditionCreateInput | ConditionUpdateInput) => Promise<void>;
  isSubmitting: boolean;
  mode: "create" | "edit";
}

function ConditionForm({
  initialData,
  onSubmit,
  isSubmitting,
  mode,
}: ConditionFormProps) {
  const [code, setCode] = useState(initialData?.code ?? "");
  const [name, setName] = useState(initialData?.name ?? "");
  const [description, setDescription] = useState(initialData?.description ?? "");
  const [iconFile, setIconFile] = useState(initialData?.icon_file ?? "");
  const [trigColour, setTrigColour] = useState(initialData?.trig_colour ?? "");
  const [logColour, setLogColour] = useState(initialData?.log_colour ?? "");
  const [similarCodes, setSimilarCodes] = useState(
    initialData?.similar_codes ?? ""
  );
  const [wikiUrl, setWikiUrl] = useState(initialData?.wiki_url ?? "");
  const [sortOrder, setSortOrder] = useState(
    initialData?.sort_order?.toString() ?? ""
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const sortOrderNum = parseInt(sortOrder, 10);
    if (isNaN(sortOrderNum) || sortOrderNum < 0) {
      toast.error("Sort order must be a non-negative number");
      return;
    }

    if (mode === "create") {
      if (!code || code.length !== 1 || !/^[A-Z]$/.test(code)) {
        toast.error("Code must be a single uppercase letter (A-Z)");
        return;
      }
      await onSubmit({
        code: code.toUpperCase(),
        name: name.trim(),
        sort_order: sortOrderNum,
        description: description.trim() || undefined,
        icon_file: iconFile.trim() || undefined,
        trig_colour: trigColour.trim() || undefined,
        log_colour: logColour.trim() || undefined,
        similar_codes: similarCodes.trim().toUpperCase() || undefined,
        wiki_url: wikiUrl.trim() || undefined,
      } as ConditionCreateInput);
    } else {
      await onSubmit({
        name: name.trim() || undefined,
        description: description.trim() || undefined,
        icon_file: iconFile.trim() || undefined,
        trig_colour: trigColour.trim() || undefined,
        log_colour: logColour.trim() || undefined,
        similar_codes: similarCodes.trim().toUpperCase() || undefined,
        wiki_url: wikiUrl.trim() || undefined,
        sort_order: sortOrderNum,
      } as ConditionUpdateInput);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {mode === "create" && (
        <div className="space-y-2">
          <Label htmlFor="condition-code" required>
            Code
          </Label>
          <Input
            id="condition-code"
            value={code}
            onChange={(e) => {
              // Only allow letters A-Z, automatically uppercase
              const filtered = e.target.value.replace(/[^A-Za-z]/g, "").toUpperCase();
              setCode(filtered);
            }}
            placeholder="e.g. G"
            maxLength={1}
            className="font-mono uppercase"
            required
          />
          <p className="text-xs text-gray-500">
            Single letter code (A-Z), used as primary key
          </p>
        </div>
      )}

      <div className="space-y-2">
        <Label htmlFor="condition-name" required>
          Name
        </Label>
        <Input
          id="condition-name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Good"
          maxLength={50}
          required
        />
        <p className="text-xs text-gray-500">
          Human-readable name (max 50 characters)
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="condition-sort-order" required>
          Sort Order
        </Label>
        <Input
          id="condition-sort-order"
          type="number"
          min="0"
          max="32767"
          value={sortOrder}
          onChange={(e) => setSortOrder(e.target.value)}
          placeholder="e.g. 10"
          required
        />
        <p className="text-xs text-gray-500">Display order (0-32767)</p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="condition-description">Description</Label>
        <Textarea
          id="condition-description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Detailed description of this condition..."
          rows={2}
          maxLength={255}
        />
        <p className="text-xs text-gray-500">
          Optional description (max 255 characters)
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="condition-icon-file">Icon File</Label>
          <Input
            id="condition-icon-file"
            value={iconFile}
            onChange={(e) => setIconFile(e.target.value)}
            placeholder="e.g. c_good.png"
            maxLength={100}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="condition-similar-codes">Similar Codes</Label>
          <Input
            id="condition-similar-codes"
            value={similarCodes}
            onChange={(e) => setSimilarCodes(e.target.value.toUpperCase())}
            placeholder="e.g. GS"
            maxLength={10}
            className="font-mono uppercase"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="condition-trig-colour">Trig Colour</Label>
          <Input
            id="condition-trig-colour"
            value={trigColour}
            onChange={(e) => setTrigColour(e.target.value)}
            placeholder="e.g. green"
            maxLength={20}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="condition-log-colour">Log Colour</Label>
          <Input
            id="condition-log-colour"
            value={logColour}
            onChange={(e) => setLogColour(e.target.value)}
            placeholder="e.g. red"
            maxLength={20}
          />
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="condition-wiki-url">Wiki URL</Label>
        <Input
          id="condition-wiki-url"
          type="url"
          value={wikiUrl}
          onChange={(e) => setWikiUrl(e.target.value)}
          placeholder="https://wiki.example.com/condition"
          maxLength={255}
        />
      </div>

      <DialogFooter>
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? (
            <>
              <span className="mr-2">
                <Spinner size="sm" />
              </span>
              {mode === "create" ? "Creating..." : "Saving..."}
            </>
          ) : mode === "create" ? (
            "Create Condition"
          ) : (
            "Save Changes"
          )}
        </Button>
      </DialogFooter>
    </form>
  );
}

// ============================================================================
// Main ConditionAdmin Component
// ============================================================================

export default function ConditionAdmin() {
  const { getAccessTokenSilently, isAuthenticated, loginWithRedirect } =
    useAuth0();

  const [conditions, setConditions] = useState<Condition[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Dialog states
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [editingCondition, setEditingCondition] = useState<Condition | null>(
    null
  );
  const [deletingCondition, setDeletingCondition] = useState<Condition | null>(
    null
  );
  const [deleteUsageCount, setDeleteUsageCount] = useState<number | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Fetch conditions
  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const token = await getAccessTokenSilently({
        authorizationParams: ADMIN_AUTH_PARAMS,
      });
      const data = await fetchAllConditions(token);
      setConditions(data);
    } catch (err) {
      console.error("Error fetching conditions:", err);
      setError(err instanceof Error ? err.message : "Failed to load conditions");
    } finally {
      setLoading(false);
    }
  }, [getAccessTokenSilently]);

  useEffect(() => {
    if (isAuthenticated) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- one-shot state sync on data load; re-render cost negligible (won't fix)
      fetchData();
    }
  }, [isAuthenticated, fetchData]);

  // Handlers
  const handleAddCondition = async (
    data: ConditionCreateInput | ConditionUpdateInput
  ) => {
    try {
      setIsSubmitting(true);
      const token = await getAccessTokenSilently({
        authorizationParams: ADMIN_AUTH_PARAMS,
      });
      await createCondition(data as ConditionCreateInput, token);
      toast.success("Condition created successfully");
      setIsAddDialogOpen(false);
      await fetchData();
    } catch (err) {
      console.error("Error creating condition:", err);
      toast.error(
        err instanceof Error ? err.message : "Failed to create condition"
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleEditCondition = async (
    data: ConditionCreateInput | ConditionUpdateInput
  ) => {
    if (!editingCondition) return;
    try {
      setIsSubmitting(true);
      const token = await getAccessTokenSilently({
        authorizationParams: ADMIN_AUTH_PARAMS,
      });
      await updateCondition(
        editingCondition.code,
        data as ConditionUpdateInput,
        token
      );
      toast.success("Condition updated successfully");
      setEditingCondition(null);
      await fetchData();
    } catch (err) {
      console.error("Error updating condition:", err);
      toast.error(
        err instanceof Error ? err.message : "Failed to update condition"
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteClick = async (condition: Condition) => {
    setDeletingCondition(condition);
    setDeleteUsageCount(null);

    // Fetch usage count
    try {
      const token = await getAccessTokenSilently({
        authorizationParams: ADMIN_AUTH_PARAMS,
      });
      const usage = await fetchConditionUsage(condition.code, token);
      setDeleteUsageCount(usage.usage_count);
    } catch (err) {
      console.error("Error fetching usage count:", err);
      setDeleteUsageCount(0);
    }
  };

  const handleConfirmDelete = async () => {
    if (!deletingCondition) return;
    try {
      setIsSubmitting(true);
      const token = await getAccessTokenSilently({
        authorizationParams: ADMIN_AUTH_PARAMS,
      });
      await deleteCondition(deletingCondition.code, token);
      toast.success("Condition deleted successfully");
      setDeletingCondition(null);
      await fetchData();
    } catch (err) {
      console.error("Error deleting condition:", err);
      toast.error(
        err instanceof Error ? err.message : "Failed to delete condition"
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  // Render
  if (!isAuthenticated) {
    return (
      <>
        <div className="max-w-4xl mx-auto py-8 px-4">
          <Card className="p-8 text-center">
            <h2 className="text-xl font-semibold mb-4">
              Authentication Required
            </h2>
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
              Loading conditions...
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
      <div className="max-w-4xl mx-auto py-8 px-4">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              Condition Management
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mt-1">
              Manage trigpoint condition codes
            </p>
          </div>
          <Button onClick={() => setIsAddDialogOpen(true)}>
            <Plus className="w-4 h-4 mr-2" />
            Add Condition
          </Button>
        </div>

        {/* Condition List */}
        <Card className="p-4">
          {conditions.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              No conditions found. Click "Add Condition" to create one.
            </div>
          ) : (
            <div className="space-y-2">
              {conditions.map((condition) => (
                <ConditionRow
                  key={condition.code}
                  condition={condition}
                  onEdit={setEditingCondition}
                  onDelete={handleDeleteClick}
                />
              ))}
            </div>
          )}
        </Card>

        {/* Add Condition Dialog */}
        <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>Add New Condition</DialogTitle>
              <DialogDescription>
                Create a new trigpoint condition code.
              </DialogDescription>
            </DialogHeader>
            <ConditionForm
              onSubmit={handleAddCondition}
              isSubmitting={isSubmitting}
              mode="create"
            />
          </DialogContent>
        </Dialog>

        {/* Edit Condition Dialog */}
        <Dialog
          open={editingCondition !== null}
          onOpenChange={(open) => !open && setEditingCondition(null)}
        >
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>Edit Condition</DialogTitle>
              <DialogDescription>
                Update condition details. Code cannot be changed.
              </DialogDescription>
            </DialogHeader>
            {editingCondition && (
              <ConditionForm
                initialData={editingCondition}
                onSubmit={handleEditCondition}
                isSubmitting={isSubmitting}
                mode="edit"
              />
            )}
          </DialogContent>
        </Dialog>

        {/* Delete Confirmation Dialog */}
        <AlertDialog
          open={deletingCondition !== null}
          onOpenChange={(open) => !open && setDeletingCondition(null)}
          title="Delete Condition"
          description={
            deleteUsageCount === null
              ? "Checking usage..."
              : deleteUsageCount > 0
                ? `This condition is used by ${deleteUsageCount} log(s) and cannot be deleted.`
                : `Are you sure you want to delete "${deletingCondition?.name}"? This action cannot be undone.`
          }
          confirmText={deleteUsageCount === 0 ? "Delete" : "Close"}
          onConfirm={
            deleteUsageCount === 0
              ? handleConfirmDelete
              : () => setDeletingCondition(null)
          }
          variant={deleteUsageCount === 0 ? "danger" : "default"}
        />
      </div>
    </>
  );
}

