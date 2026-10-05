/**
 * VariantsAdmin - manage trig variants, the values that qualify a type
 * without adding types (e.g. a Buried Block's detector material). Variants
 * are grouped; a type offers a group through its "Variant group" setting.
 */

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
  TrigVariantAdmin,
  VariantGroupAdmin,
  fetchVariantGroupsAdmin,
  createVariant,
  updateVariant,
  renameVariantGroup,
  deleteVariant,
  requireAccessToken,
} from "../../lib/api";

const AUTH0_AUDIENCE = import.meta.env.VITE_AUTH0_AUDIENCE as string | undefined;
const ADMIN_SCOPE = "api:admin";
const BASE_SCOPES = "openid profile email api:write api:read-pii offline_access";
const ADMIN_AUTH_PARAMS: { scope: string; audience?: string } = AUTH0_AUDIENCE
  ? { audience: AUTH0_AUDIENCE, scope: `${BASE_SCOPES} ${ADMIN_SCOPE}` }
  : { scope: `${BASE_SCOPES} ${ADMIN_SCOPE}` };

// Group select value for starting a new group
const NEW_GROUP = "__new__";

const SELECT_CLASSES =
  "w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-gray-800 dark:text-gray-100 bg-white dark:bg-gray-700 shadow-sm focus:border-trig-green-500 focus:ring-2 focus:ring-trig-green-400";

/** A code from a name, as the API wants them: e.g. "Copper ring" -> COPPER_RING */
function toCode(name: string): string {
  return name
    .toUpperCase()
    .replace(/[^A-Z0-9]+/g, "_")
    .replace(/^[0-9_]+|_+$/g, "")
    .slice(0, 20);
}

/** The API's explanation from a failed request, if it gave one */
function errorMessage(err: unknown, fallback: string): string {
  if (!(err instanceof Error)) return fallback;
  try {
    const detail: unknown = JSON.parse(err.message.replace(/^HTTP \d+: /, "")).detail;
    if (typeof detail === "string") return detail;
  } catch {
    // Not a JSON error body
  }
  return err.message;
}

function nextSortOrder(group: VariantGroupAdmin | undefined): number {
  return (group?.variants ?? []).reduce((max, v) => Math.max(max, v.sort_order), 0) + 10;
}

/** Why a variant can't be deleted, or null if it can */
function deleteBlocker(group: VariantGroupAdmin, variant: TrigVariantAdmin): string | null {
  if (variant.trig_count > 0) {
    return `"${variant.name}" is recorded on ${variant.trig_count.toLocaleString("en-GB")} trigpoint(s) and cannot be deleted.`;
  }
  if (group.variants.length === 1 && group.type_names.length > 0) {
    return `"${variant.name}" is the last ${group.name} value, and ${group.type_names.join(", ")} offer the group, so it cannot be deleted.`;
  }
  return null;
}

// ============================================================================
// Row Component
// ============================================================================

interface VariantRowProps {
  variant: TrigVariantAdmin;
  onEdit: (variant: TrigVariantAdmin) => void;
  onDelete: (variant: TrigVariantAdmin) => void;
}

function VariantRow({ variant, onEdit, onDelete }: VariantRowProps) {
  return (
    <div className="flex items-center gap-3 py-3 px-4 bg-gray-50 dark:bg-gray-700/50 rounded-md group hover:bg-gray-100 dark:hover:bg-gray-700">
      <div className="flex-1 min-w-0">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <span className="font-semibold text-gray-900 dark:text-gray-100">{variant.name}</span>
          <span className="font-mono text-xs text-gray-500 dark:text-gray-400">{variant.code}</span>
          <span className="text-xs text-gray-500 dark:text-gray-400">#{variant.sort_order}</span>
        </div>
        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
          {variant.trig_count.toLocaleString("en-GB")}{" "}
          {variant.trig_count === 1 ? "trigpoint" : "trigpoints"}
        </p>
      </div>
      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          type="button"
          onClick={() => onEdit(variant)}
          className="p-1.5 rounded-md text-gray-500 hover:text-trig-green-600 hover:bg-trig-green-50 dark:hover:bg-trig-green-900/30"
          title={`Edit ${variant.name}`}
        >
          <Pencil className="h-4 w-4" />
        </button>
        <button
          type="button"
          onClick={() => onDelete(variant)}
          className="p-1.5 rounded-md text-gray-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30"
          title={`Delete ${variant.name}`}
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

// ============================================================================
// Group Card
// ============================================================================

interface GroupCardProps {
  group: VariantGroupAdmin;
  onRename: (group: VariantGroupAdmin) => void;
  onAdd: (group: VariantGroupAdmin) => void;
  onEdit: (group: VariantGroupAdmin, variant: TrigVariantAdmin) => void;
  onDelete: (group: VariantGroupAdmin, variant: TrigVariantAdmin) => void;
}

function GroupCard({ group, onRename, onAdd, onEdit, onDelete }: GroupCardProps) {
  return (
    <Card className="p-4">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">{group.name}</h2>
            <span className="font-mono text-xs text-gray-500 dark:text-gray-400">{group.code}</span>
            <button
              type="button"
              onClick={() => onRename(group)}
              className="p-1 rounded-md text-gray-500 hover:text-trig-green-600 hover:bg-trig-green-50 dark:hover:bg-trig-green-900/30"
              title={`Rename ${group.name}`}
            >
              <Pencil className="h-4 w-4" />
            </button>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            {group.type_names.length > 0
              ? `Offered by ${group.type_names.join(", ")}`
              : "Not offered by any type yet - set it as a type's variant group under Types & Categories"}
          </p>
        </div>
        <Button variant="secondary" size="sm" onClick={() => onAdd(group)}>
          <Plus className="w-4 h-4 mr-1" />
          Add Variant
        </Button>
      </div>
      <div className="space-y-2">
        {group.variants.map((variant) => (
          <VariantRow
            key={variant.id}
            variant={variant}
            onEdit={(v) => onEdit(group, v)}
            onDelete={(v) => onDelete(group, v)}
          />
        ))}
      </div>
    </Card>
  );
}

// ============================================================================
// Forms
// ============================================================================

interface CreateVariantFormProps {
  groups: VariantGroupAdmin[];
  initialGroupCode: string;
  onSubmit: (data: {
    group_code: string;
    group_name?: string;
    code: string;
    name: string;
    sort_order: number;
  }) => Promise<void>;
  isSubmitting: boolean;
}

function CreateVariantForm({ groups, initialGroupCode, onSubmit, isSubmitting }: CreateVariantFormProps) {
  const [groupCode, setGroupCode] = useState(initialGroupCode);
  const [groupName, setGroupName] = useState("");
  const [newGroupCode, setNewGroupCode] = useState("");
  const [newGroupCodeEdited, setNewGroupCodeEdited] = useState(false);
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [codeEdited, setCodeEdited] = useState(false);
  const [sortOrder, setSortOrder] = useState(
    nextSortOrder(groups.find((g) => g.code === initialGroupCode)).toString()
  );
  const [sortOrderEdited, setSortOrderEdited] = useState(false);

  const isNewGroup = groupCode === NEW_GROUP;

  const handleGroupChange = (value: string) => {
    setGroupCode(value);
    // Follow the group's next free position unless one was typed in
    if (!sortOrderEdited) {
      setSortOrder(nextSortOrder(groups.find((g) => g.code === value)).toString());
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const sortOrderNum = parseInt(sortOrder, 10);
    if (isNaN(sortOrderNum) || sortOrderNum < 0) {
      toast.error("Sort order must be a non-negative number");
      return;
    }
    if (!name.trim() || !code.trim()) {
      toast.error("Name and code are required");
      return;
    }
    if (isNewGroup && (!groupName.trim() || !newGroupCode.trim())) {
      toast.error("A new group needs a name and a code");
      return;
    }

    await onSubmit({
      group_code: isNewGroup ? newGroupCode.trim() : groupCode,
      ...(isNewGroup && { group_name: groupName.trim() }),
      code: code.trim(),
      name: name.trim(),
      sort_order: sortOrderNum,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="variant-group" required>
          Group
        </Label>
        <select
          id="variant-group"
          value={groupCode}
          onChange={(e) => handleGroupChange(e.target.value)}
          className={SELECT_CLASSES}
        >
          {groups.map((g) => (
            <option key={g.code} value={g.code}>
              {g.name}
            </option>
          ))}
          <option value={NEW_GROUP}>New group…</option>
        </select>
      </div>

      {isNewGroup && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="variant-group-name" required>
              Group name
            </Label>
            <Input
              id="variant-group-name"
              value={groupName}
              onChange={(e) => {
                setGroupName(e.target.value);
                if (!newGroupCodeEdited) setNewGroupCode(toCode(e.target.value));
              }}
              placeholder="e.g. Detector material"
              maxLength={30}
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="variant-group-code" required>
              Group code
            </Label>
            <Input
              id="variant-group-code"
              value={newGroupCode}
              onChange={(e) => {
                setNewGroupCode(e.target.value.toUpperCase());
                setNewGroupCodeEdited(true);
              }}
              placeholder="e.g. DETECTOR"
              maxLength={20}
              className="font-mono"
              required
            />
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="variant-name" required>
            Name
          </Label>
          <Input
            id="variant-name"
            value={name}
            onChange={(e) => {
              setName(e.target.value);
              if (!codeEdited) setCode(toCode(e.target.value));
            }}
            placeholder="e.g. Concrete ring"
            maxLength={30}
            required
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="variant-code" required>
            Code
          </Label>
          <Input
            id="variant-code"
            value={code}
            onChange={(e) => {
              setCode(e.target.value.toUpperCase());
              setCodeEdited(true);
            }}
            placeholder="e.g. CONCRETE_RING"
            maxLength={20}
            className="font-mono"
            required
          />
        </div>
      </div>
      <p className="text-xs text-gray-500">
        Codes can&apos;t be changed later: they&apos;re used in filter links
        {isNewGroup ? ", and types refer to the group code" : ""}.
      </p>

      <div className="space-y-2">
        <Label htmlFor="variant-sort-order" required>
          Sort Order
        </Label>
        <Input
          id="variant-sort-order"
          type="number"
          min="0"
          max="32767"
          value={sortOrder}
          onChange={(e) => {
            setSortOrder(e.target.value);
            setSortOrderEdited(true);
          }}
          required
        />
        <p className="text-xs text-gray-500">Order within the group (0-32767)</p>
      </div>

      <DialogFooter>
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? (
            <>
              <span className="mr-2"><Spinner size="sm" /></span>
              Creating...
            </>
          ) : (
            "Create Variant"
          )}
        </Button>
      </DialogFooter>
    </form>
  );
}

interface EditVariantFormProps {
  variant: TrigVariantAdmin;
  onSubmit: (data: { name: string; sort_order: number }) => Promise<void>;
  isSubmitting: boolean;
}

function EditVariantForm({ variant, onSubmit, isSubmitting }: EditVariantFormProps) {
  const [name, setName] = useState(variant.name);
  const [sortOrder, setSortOrder] = useState(variant.sort_order.toString());

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
    await onSubmit({ name: name.trim(), sort_order: sortOrderNum });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="variant-name" required>
          Name
        </Label>
        <Input
          id="variant-name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          maxLength={30}
          required
        />
        <p className="text-xs text-gray-500">
          Code <span className="font-mono">{variant.code}</span> stays the same.
          {variant.trig_count > 0 &&
            ` The ${variant.trig_count.toLocaleString("en-GB")} trigpoint(s) with it will show the new name.`}
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="variant-sort-order" required>
          Sort Order
        </Label>
        <Input
          id="variant-sort-order"
          type="number"
          min="0"
          max="32767"
          value={sortOrder}
          onChange={(e) => setSortOrder(e.target.value)}
          required
        />
        <p className="text-xs text-gray-500">Order within the group (0-32767)</p>
      </div>

      <DialogFooter>
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? (
            <>
              <span className="mr-2"><Spinner size="sm" /></span>
              Saving...
            </>
          ) : (
            "Save Changes"
          )}
        </Button>
      </DialogFooter>
    </form>
  );
}

interface RenameGroupFormProps {
  group: VariantGroupAdmin;
  onSubmit: (name: string) => Promise<void>;
  isSubmitting: boolean;
}

function RenameGroupForm({ group, onSubmit, isSubmitting }: RenameGroupFormProps) {
  const [name, setName] = useState(group.name);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      toast.error("Name is required");
      return;
    }
    await onSubmit(name.trim());
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="variant-group-name" required>
          Group name
        </Label>
        <Input
          id="variant-group-name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          maxLength={30}
          required
        />
        <p className="text-xs text-gray-500">
          Code <span className="font-mono">{group.code}</span> stays the same, so
          the types offering the group are unaffected.
        </p>
      </div>

      <DialogFooter>
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? (
            <>
              <span className="mr-2"><Spinner size="sm" /></span>
              Saving...
            </>
          ) : (
            "Save Changes"
          )}
        </Button>
      </DialogFooter>
    </form>
  );
}

// ============================================================================
// Main VariantsAdmin Component
// ============================================================================

interface Selected {
  group: VariantGroupAdmin;
  variant: TrigVariantAdmin;
}

export default function VariantsAdmin() {
  const { getAccessTokenSilently, isAuthenticated, loginWithRedirect } = useAuth0();
  const queryClient = useQueryClient();

  const [groups, setGroups] = useState<VariantGroupAdmin[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Dialog states. addingTo is the group to preselect, or NEW_GROUP.
  const [addingTo, setAddingTo] = useState<string | null>(null);
  const [editing, setEditing] = useState<Selected | null>(null);
  const [renamingGroup, setRenamingGroup] = useState<VariantGroupAdmin | null>(null);
  const [deleting, setDeleting] = useState<Selected | null>(null);
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
      setGroups(await fetchVariantGroupsAdmin(await getToken()));
    } catch (err) {
      console.error("Error fetching variants:", err);
      setError(err instanceof Error ? err.message : "Failed to load variants");
    } finally {
      setLoading(false);
    }
  }, [getToken]);

  useEffect(() => {
    if (isAuthenticated) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- one-shot state sync on data load; re-render cost negligible (won't fix)
      fetchData();
    }
  }, [isAuthenticated, fetchData]);

  // Refresh the list here and the variant filters and selects elsewhere
  const afterChange = async () => {
    await queryClient.invalidateQueries({ queryKey: ["reference", "variantGroups"] });
    await fetchData();
  };

  // Runs a change, reporting how it went; true if it worked
  const submit = async (action: () => Promise<unknown>, success: string, failure: string) => {
    try {
      setIsSubmitting(true);
      await action();
      toast.success(success);
      await afterChange();
      return true;
    } catch (err) {
      console.error(`${failure}:`, err);
      toast.error(errorMessage(err, failure));
      return false;
    } finally {
      setIsSubmitting(false);
    }
  };

  const deleteBlockedBy = deleting ? deleteBlocker(deleting.group, deleting.variant) : null;

  // Render
  if (!isAuthenticated) {
    return (
      <div className="max-w-4xl mx-auto py-8 px-4">
        <Card className="p-8 text-center">
          <h2 className="text-xl font-semibold mb-4">Authentication Required</h2>
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            You must be logged in as an administrator to access this page.
          </p>
          <Button onClick={() => loginWithRedirect()}>Log In</Button>
        </Card>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto py-8 px-4">
        <div className="flex items-center justify-center py-12">
          <Spinner size="lg" />
          <span className="ml-3 text-gray-600 dark:text-gray-400">Loading variants...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto py-8 px-4">
        <Card className="p-8 text-center">
          <h2 className="text-xl font-semibold text-red-600 mb-4">Error</h2>
          <p className="text-gray-600 dark:text-gray-400 mb-4">{error}</p>
          <Button onClick={fetchData}>Retry</Button>
        </Card>
      </div>
    );
  }

  return (
    <>
      <title>Variants | Admin | TrigpointingUK</title>
      <div className="max-w-4xl mx-auto py-8 px-4">
        {/* Header */}
        <div className="flex items-center justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              Variants Management
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mt-1">
              Manage the variants that qualify a trigpoint&apos;s type, e.g. a Buried
              Block&apos;s detector material
            </p>
          </div>
          <Button onClick={() => setAddingTo(groups[0]?.code ?? NEW_GROUP)}>
            <Plus className="w-4 h-4 mr-2" />
            Add Variant
          </Button>
        </div>

        {groups.length === 0 ? (
          <Card className="p-4">
            <div className="text-center py-8 text-gray-500">
              No variants found. Click &quot;Add Variant&quot; to create one.
            </div>
          </Card>
        ) : (
          <div className="space-y-6">
            {groups.map((group) => (
              <GroupCard
                key={group.code}
                group={group}
                onRename={setRenamingGroup}
                onAdd={(g) => setAddingTo(g.code)}
                onEdit={(g, variant) => setEditing({ group: g, variant })}
                onDelete={(g, variant) => setDeleting({ group: g, variant })}
              />
            ))}
          </div>
        )}

        {/* Add Dialog */}
        <Dialog open={addingTo !== null} onOpenChange={(open) => !open && setAddingTo(null)}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add Variant</DialogTitle>
              <DialogDescription>
                Add a variant to a group, or start a new group with it.
              </DialogDescription>
            </DialogHeader>
            {addingTo !== null && (
              <CreateVariantForm
                groups={groups}
                initialGroupCode={addingTo}
                onSubmit={async (data) => {
                  const ok = await submit(
                    async () => createVariant(data, await getToken()),
                    "Variant created successfully",
                    "Failed to create variant"
                  );
                  if (ok) setAddingTo(null);
                }}
                isSubmitting={isSubmitting}
              />
            )}
          </DialogContent>
        </Dialog>

        {/* Edit Dialog */}
        <Dialog open={editing !== null} onOpenChange={(open) => !open && setEditing(null)}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Edit Variant</DialogTitle>
              <DialogDescription>
                Update this {editing?.group.name ?? ""} value.
              </DialogDescription>
            </DialogHeader>
            {editing && (
              <EditVariantForm
                variant={editing.variant}
                onSubmit={async (data) => {
                  const ok = await submit(
                    async () => updateVariant(editing.variant.id, data, await getToken()),
                    "Variant updated successfully",
                    "Failed to update variant"
                  );
                  if (ok) setEditing(null);
                }}
                isSubmitting={isSubmitting}
              />
            )}
          </DialogContent>
        </Dialog>

        {/* Rename Group Dialog */}
        <Dialog
          open={renamingGroup !== null}
          onOpenChange={(open) => !open && setRenamingGroup(null)}
        >
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Rename Group</DialogTitle>
              <DialogDescription>Rename this variant group.</DialogDescription>
            </DialogHeader>
            {renamingGroup && (
              <RenameGroupForm
                group={renamingGroup}
                onSubmit={async (name) => {
                  const ok = await submit(
                    async () => renameVariantGroup(renamingGroup.code, name, await getToken()),
                    "Group renamed successfully",
                    "Failed to rename group"
                  );
                  if (ok) setRenamingGroup(null);
                }}
                isSubmitting={isSubmitting}
              />
            )}
          </DialogContent>
        </Dialog>

        {/* Delete Confirmation Dialog */}
        <AlertDialog
          open={deleting !== null}
          onOpenChange={(open) => !open && setDeleting(null)}
          title="Delete Variant"
          description={
            deleteBlockedBy ??
            `Are you sure you want to delete "${deleting?.variant.name}"? This action cannot be undone.`
          }
          confirmText={deleteBlockedBy ? "Close" : "Delete"}
          onConfirm={async () => {
            if (!deleting || deleteBlockedBy) {
              setDeleting(null);
              return;
            }
            const ok = await submit(
              async () => deleteVariant(deleting.variant.id, await getToken()),
              "Variant deleted successfully",
              "Failed to delete variant"
            );
            if (ok) setDeleting(null);
          }}
          variant={deleteBlockedBy ? "default" : "danger"}
        />
      </div>
    </>
  );
}
