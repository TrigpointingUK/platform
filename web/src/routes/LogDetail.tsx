import { useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { useAuth0 } from "@auth0/auth0-react";
import { useQueryClient } from "@tanstack/react-query";
import Layout from "../components/layout/Layout";
import Card from "../components/ui/Card";
import Spinner from "../components/ui/Spinner";
import Button from "../components/ui/Button";
import LogCard from "../components/logs/LogCard";
import LogForm from "../components/logs/LogForm";
import TrigInfoSection from "../components/trig/TrigInfoSection";
import { useLogDetail } from "../hooks/useLogDetail";
import { useTrigDetail } from "../hooks/useTrigDetail";
import { useUpdateLog } from "../hooks/useUpdateLog";
import { useDeleteLog } from "../hooks/useDeleteLog";
import { useCurrentUser } from "../hooks/useCurrentUser";
import { useUserProfile } from "../hooks/useUserProfile";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { useCanonical } from "../hooks/useCanonical";
import { useAdminAuth } from "../hooks/useAdminAuth";
import {
  LogUpdateInput,
  DuplicateLogError,
  moveTrigToLogLocation,
  setTrigConditionFromLog,
} from "../lib/api";

export default function LogDetail() {
  const { logId } = useParams<{ logId: string }>();
  const logIdNum = logId ? parseInt(logId, 10) : null;
  const { user: auth0User, getAccessTokenSilently } = useAuth0();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [isEditing, setIsEditing] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [duplicateLogId, setDuplicateLogId] = useState<number | null>(null);

  // Admin action states
  const [showMoveConfirm, setShowMoveConfirm] = useState(false);
  const [showSetConditionConfirm, setShowSetConditionConfirm] = useState(false);
  const [adminActionPending, setAdminActionPending] = useState(false);
  const [adminActionError, setAdminActionError] = useState<string | null>(null);

  const {
    data: log,
    isLoading,
    error,
  } = useLogDetail(logIdNum!);

  // Update document title when log data loads
  useDocumentTitle(log ? `Log #${log.id} - ${log.trig_name}` : null);
  useCanonical(logIdNum ? `/logs/${logIdNum}` : null);

  // Get current user's database profile
  const { data: currentUser } = useCurrentUser();
  
  // Get current user's UI preferences
  const { data: userProfile } = useUserProfile("me");
  const showTrigCondition = userProfile?.prefs?.ui_prefs?.show_trig_condition ?? false;

  // Fetch trig details to display trig info section and for location picker when editing
  const {
    data: trig,
    isLoading: isTrigLoading,
  } = useTrigDetail(log?.trig_id);

  const updateLogMutation = useUpdateLog(logIdNum!);
  const deleteLogMutation = useDeleteLog(logIdNum!, log?.trig_id || 0);

  // Check admin role for admin buttons
  const { hasAdminRole } = useAdminAuth();

  // Check if the current user is the owner of this log
  const isOwner = !!currentUser && !!log && currentUser.id === log.user_id;

  // Admin action handlers
  const handleMoveTrigToLocation = async () => {
    if (!log || !log.trig_id) return;
    setAdminActionPending(true);
    setAdminActionError(null);
    try {
      const token = await getAccessTokenSilently({
        authorizationParams: {
          audience: import.meta.env.VITE_AUTH0_AUDIENCE,
          scope: "openid profile email api:write api:read-pii api:admin",
        },
      });
      await moveTrigToLogLocation(log.trig_id, log.id, token);
      // Invalidate caches to refresh data
      queryClient.invalidateQueries({ queryKey: ["trig", log.trig_id] });
      queryClient.invalidateQueries({ queryKey: ["log", log.id] });
      setShowMoveConfirm(false);
    } catch (err) {
      console.error("Failed to move trig:", err);
      setAdminActionError(
        err instanceof Error ? err.message : "Failed to move trig to log location"
      );
    } finally {
      setAdminActionPending(false);
    }
  };

  const handleSetTrigCondition = async () => {
    if (!log || !log.trig_id) return;
    setAdminActionPending(true);
    setAdminActionError(null);
    try {
      const token = await getAccessTokenSilently({
        authorizationParams: {
          audience: import.meta.env.VITE_AUTH0_AUDIENCE,
          scope: "openid profile email api:write api:read-pii api:admin",
        },
      });
      await setTrigConditionFromLog(log.trig_id, log.id, token);
      // Invalidate caches to refresh data
      queryClient.invalidateQueries({ queryKey: ["trig", log.trig_id] });
      queryClient.invalidateQueries({ queryKey: ["log", log.id] });
      setShowSetConditionConfirm(false);
    } catch (err) {
      console.error("Failed to set condition:", err);
      setAdminActionError(
        err instanceof Error ? err.message : "Failed to set trig condition from log"
      );
    } finally {
      setAdminActionPending(false);
    }
  };

  const handleEdit = () => {
    if (!auth0User) {
      // Could redirect to login or show message
      console.warn("User must be logged in to edit");
      return;
    }
    setIsEditing(true);
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
  };

  const handleUpdateSubmit = async (data: LogUpdateInput) => {
    try {
      await updateLogMutation.mutateAsync(data);
      setIsEditing(false);
      // Optionally show success message
    } catch (error) {
      if (error instanceof DuplicateLogError) {
        // Show the duplicate log modal
        setDuplicateLogId(error.existingLogId);
        return;
      }
      console.error("Failed to update log:", error);
      // Error handling - could show toast notification
      throw error;
    }
  };

  const handleDuplicateLogView = () => {
    if (duplicateLogId) {
      setIsEditing(false);
      setDuplicateLogId(null);
      navigate(`/logs/${duplicateLogId}`);
    }
  };

  const handleDuplicateLogDismiss = () => {
    setDuplicateLogId(null);
  };

  const handleDeleteClick = () => {
    setShowDeleteConfirm(true);
  };

  const handleDeleteConfirm = async () => {
    try {
      await deleteLogMutation.mutateAsync();
      // Navigate back to the trig page after successful deletion
      if (log) {
        navigate(`/trigs/${log.trig_id}`);
      } else {
        navigate(-1);
      }
    } catch (error) {
      console.error("Failed to delete log:", error);
      // Error handling - could show toast notification
      setShowDeleteConfirm(false);
    }
  };

  const handleDeleteCancel = () => {
    setShowDeleteConfirm(false);
  };

  if (!logIdNum) {
    return (
      <Layout>
        <div className="max-w-7xl mx-auto">
          <Card>
            <p className="text-red-600 dark:text-red-400">Invalid log ID</p>
          </Card>
        </div>
      </Layout>
    );
  }

  if (error) {
    return (
      <Layout>
        <div className="max-w-7xl mx-auto">
          <Card>
            <p className="text-red-600 dark:text-red-400">Failed to load log details</p>
            <Link
              to="/"
              className="text-trig-green-600 hover:underline mt-4 inline-block"
            >
              ← Back to Home
            </Link>
          </Card>
        </div>
      </Layout>
    );
  }

  if (isLoading || isTrigLoading) {
    return (
      <Layout>
        <div className="max-w-7xl mx-auto">
          <Card>
            <Spinner size="lg" />
            <p className="text-center text-gray-600 dark:text-gray-400 mt-4">Loading log...</p>
          </Card>
        </div>
      </Layout>
    );
  }

  if (!log) {
    return (
      <Layout>
        <div className="max-w-7xl mx-auto">
          <Card>
            <p className="text-red-600 dark:text-red-400">Log not found</p>
            <Link
              to="/"
              className="text-trig-green-600 hover:underline mt-4 inline-block"
            >
              ← Back to Home
            </Link>
          </Card>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="max-w-7xl mx-auto">
        {/* Breadcrumb */}
        <div className="mb-4">
          <button 
            onClick={() => navigate(-1)} 
            className="text-trig-green-600 hover:underline"
          >
            ← Back
          </button>
        </div>

        {/* Trig Info Section - show if trig data is loaded */}
        {trig && <TrigInfoSection trig={trig} />}

        {/* Edit/View Toggle */}
        {!isEditing ? (
          <>
            {/* Read-only view */}
            <LogCard log={log} showTrigCondition={showTrigCondition} showTrigInfo={false} />
            
            {/* Edit and Delete buttons - only show if user owns this log */}
            {isOwner && (
              <div className="mt-4 flex gap-2">
                <Button onClick={handleEdit}>
                  ✏️ Edit Log
                </Button>
                <Button 
                  onClick={handleDeleteClick}
                  variant="danger"
                >
                  🧹 Delete Log
                </Button>
              </div>
            )}

            {/* Admin buttons - only show if user has admin role */}
            {hasAdminRole && log && (
              <Card className="mt-4">
                <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
                  Admin Actions
                </h3>
                <div className="flex flex-wrap gap-2">
                  <Link to={`/admin/trigs/${log.trig_id}/edit`}>
                    <Button variant="secondary" size="sm">
                      ✏️ Edit Trig
                    </Button>
                  </Link>
                  <span
                    title={
                      !log.osgb_eastings || !log.osgb_northings
                        ? "Log has no location data"
                        : undefined
                    }
                  >
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setShowMoveConfirm(true)}
                      disabled={!log.osgb_eastings || !log.osgb_northings}
                    >
                      📍 Move Trig to This Location
                    </Button>
                  </span>
                  <span title={!log.condition ? "Log has no condition" : undefined}>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setShowSetConditionConfirm(true)}
                      disabled={!log.condition}
                    >
                      🔄 Set Trig to This Condition
                    </Button>
                  </span>
                </div>
                {adminActionError && (
                  <p className="mt-2 text-sm text-red-600 dark:text-red-400">
                    {adminActionError}
                  </p>
                )}
              </Card>
            )}

            {/* Delete confirmation modal */}
            {showDeleteConfirm && (
              <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                <Card className="max-w-md mx-4">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Delete Log?</h3>
                  <p className="text-gray-600 dark:text-gray-400 mb-6">
                    Are you sure you want to delete this log? This action cannot be undone.
                    All photos associated with this log will also be removed.
                  </p>
                  <div className="flex gap-2 justify-end">
                    <Button 
                      variant="outline" 
                      onClick={handleDeleteCancel}
                      disabled={deleteLogMutation.isPending}
                    >
                      Cancel
                    </Button>
                    <Button 
                      onClick={handleDeleteConfirm}
                      disabled={deleteLogMutation.isPending}
                      variant="danger"
                    >
                      {deleteLogMutation.isPending ? "Deleting..." : "Delete"}
                    </Button>
                  </div>
                </Card>
              </div>
            )}

            {/* Move trig confirmation modal */}
            {showMoveConfirm && log && (
              <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                <Card className="max-w-md mx-4">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                    Move Trig to This Location?
                  </h3>
                  <p className="text-gray-600 dark:text-gray-400 mb-4">
                    This will update the trigpoint&apos;s location to match this log&apos;s coordinates:
                  </p>
                  <p className="text-gray-800 dark:text-gray-200 font-mono text-sm mb-4">
                    {log.osgb_gridref}
                  </p>
                  <p className="text-gray-600 dark:text-gray-400 mb-6">
                    The trig&apos;s condition will be set to &apos;Moved&apos; (M).
                  </p>
                  {adminActionError && (
                    <p className="text-red-600 dark:text-red-400 mb-4 text-sm">
                      {adminActionError}
                    </p>
                  )}
                  <div className="flex gap-2 justify-end">
                    <Button
                      variant="outline"
                      onClick={() => {
                        setShowMoveConfirm(false);
                        setAdminActionError(null);
                      }}
                      disabled={adminActionPending}
                    >
                      Cancel
                    </Button>
                    <Button
                      onClick={handleMoveTrigToLocation}
                      disabled={adminActionPending}
                    >
                      {adminActionPending ? "Moving..." : "Move Trig"}
                    </Button>
                  </div>
                </Card>
              </div>
            )}

            {/* Set condition confirmation modal */}
            {showSetConditionConfirm && log && trig && (
              <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                <Card className="max-w-md mx-4">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                    Set Trig Condition?
                  </h3>
                  <p className="text-gray-600 dark:text-gray-400 mb-4">
                    This will update the trigpoint&apos;s condition from &apos;{trig.condition}&apos; to &apos;{log.condition}&apos;.
                  </p>
                  {adminActionError && (
                    <p className="text-red-600 dark:text-red-400 mb-4 text-sm">
                      {adminActionError}
                    </p>
                  )}
                  <div className="flex gap-2 justify-end">
                    <Button
                      variant="outline"
                      onClick={() => {
                        setShowSetConditionConfirm(false);
                        setAdminActionError(null);
                      }}
                      disabled={adminActionPending}
                    >
                      Cancel
                    </Button>
                    <Button
                      onClick={handleSetTrigCondition}
                      disabled={adminActionPending}
                    >
                      {adminActionPending ? "Updating..." : "Set Condition"}
                    </Button>
                  </div>
                </Card>
              </div>
            )}
          </>
        ) : (
          <>
            {/* Edit mode */}
            {trig && (
              <LogForm
                trigGridRef={log.osgb_gridref}
                trigEastings={log.osgb_eastings}
                trigNorthings={log.osgb_northings}
                trigLatitude={trig.wgs_lat}
                trigLongitude={trig.wgs_long}
                existingLog={log}
                onSubmit={handleUpdateSubmit}
                onCancel={handleCancelEdit}
                isSubmitting={updateLogMutation.isPending}
              />
            )}
          </>
        )}

        {/* Duplicate Log Modal */}
        {duplicateLogId && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <Card className="max-w-md mx-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Log Already Exists</h3>
              <p className="text-gray-700 dark:text-gray-300 mb-6">
                You already have a log for this trigpoint on the selected date.
                Would you like to view your existing log instead?
              </p>
              <div className="flex gap-2 justify-end">
                <Button 
                  variant="outline" 
                  onClick={handleDuplicateLogDismiss}
                >
                  Cancel
                </Button>
                <Button 
                  onClick={handleDuplicateLogView}
                >
                  View Existing Log
                </Button>
              </div>
            </Card>
          </div>
        )}
      </div>
    </Layout>
  );
}

