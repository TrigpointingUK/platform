import { useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { useAuth0 } from "@auth0/auth0-react";
import Layout from "../components/layout/Layout";
import Card from "../components/ui/Card";
import Spinner from "../components/ui/Spinner";
import Button from "../components/ui/Button";
import LogCard from "../components/logs/LogCard";
import LogForm from "../components/logs/LogForm";
import { useLogDetail } from "../hooks/useLogDetail";
import { useTrigDetail } from "../hooks/useTrigDetail";
import { useUpdateLog } from "../hooks/useUpdateLog";
import { useDeleteLog } from "../hooks/useDeleteLog";
import { useCurrentUser } from "../hooks/useCurrentUser";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { LogUpdateInput, DuplicateLogError } from "../lib/api";

export default function LogDetail() {
  const { logId } = useParams<{ logId: string }>();
  const logIdNum = logId ? parseInt(logId, 10) : null;
  const { user: auth0User } = useAuth0();
  const navigate = useNavigate();

  const [isEditing, setIsEditing] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [duplicateLogId, setDuplicateLogId] = useState<number | null>(null);

  const {
    data: log,
    isLoading,
    error,
  } = useLogDetail(logIdNum!);

  // Update document title when log data loads
  useDocumentTitle(log ? `Log #${log.id} - ${log.trig_name}` : null);

  // Get current user's database profile
  const { data: currentUser } = useCurrentUser();

  // Fetch trig details to get latitude/longitude for location picker
  // Only fetch if we have a log and are in editing mode
  const shouldFetchTrig = !!log && isEditing;
  const {
    data: trig,
    isLoading: isTrigLoading,
  } = useTrigDetail(shouldFetchTrig ? log.trig_id : undefined);

  const updateLogMutation = useUpdateLog(logIdNum!);
  const deleteLogMutation = useDeleteLog(logIdNum!, log?.trig_id || 0);

  // Check if the current user is the owner of this log
  const isOwner = !!currentUser && !!log && currentUser.id === log.user_id;

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
            <p className="text-red-600">Invalid log ID</p>
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
            <p className="text-red-600">Failed to load log details</p>
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
            <p className="text-center text-gray-600 mt-4">Loading log...</p>
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
            <p className="text-red-600">Log not found</p>
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

  // If we're editing but trig data isn't loaded yet, show spinner
  if (isEditing && !trig) {
    return (
      <Layout>
        <div className="max-w-7xl mx-auto">
          <Card>
            <Spinner size="lg" />
            <p className="text-center text-gray-600 mt-4">Loading trigpoint data...</p>
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

        {/* Edit/View Toggle */}
        {!isEditing ? (
          <>
            {/* Read-only view */}
            <LogCard log={log} />
            
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

            {/* Delete confirmation modal */}
            {showDeleteConfirm && (
              <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                <Card className="max-w-md mx-4">
                  <h3 className="text-lg font-semibold mb-4">Delete Log?</h3>
                  <p className="text-gray-600 mb-6">
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
          </>
        ) : (
          <>
            {/* Edit mode */}
            {trig && (
              <LogForm
                trigGridRef={log.osgb_gridref}
                trigEastings={log.osgb_eastings}
                trigNorthings={log.osgb_northings}
                trigLatitude={parseFloat(trig.wgs_lat)}
                trigLongitude={parseFloat(trig.wgs_long)}
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
              <h3 className="text-lg font-semibold mb-4">Log Already Exists</h3>
              <p className="text-gray-700 mb-6">
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

