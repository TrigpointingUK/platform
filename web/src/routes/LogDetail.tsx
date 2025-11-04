import { useState } from "react";
import { useParams, Link } from "react-router-dom";
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
import { useCurrentUser } from "../hooks/useCurrentUser";
import { LogUpdateInput } from "../lib/api";

export default function LogDetail() {
  const { logId } = useParams<{ logId: string }>();
  const logIdNum = logId ? parseInt(logId, 10) : null;
  const { user: auth0User } = useAuth0();

  const [isEditing, setIsEditing] = useState(false);

  const {
    data: log,
    isLoading,
    error,
  } = useLogDetail(logIdNum!);

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
      console.error("Failed to update log:", error);
      // Error handling - could show toast notification
      throw error;
    }
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
          <Link 
            to={`/trig/${log.trig_id}`} 
            className="text-trig-green-600 hover:underline"
          >
            ← Back to {log.trig_name || `Trigpoint TP${log.trig_id.toString().padStart(4, '0')}`}
          </Link>
        </div>

        {/* Edit/View Toggle */}
        {!isEditing ? (
          <>
            {/* Read-only view */}
            <LogCard log={log} />
            
            {/* Edit button - only show if user owns this log */}
            {isOwner && (
              <div className="mt-4">
                <Button onClick={handleEdit}>
                  ✏️ Edit Log
                </Button>
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
      </div>
    </Layout>
  );
}

