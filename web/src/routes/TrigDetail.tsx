import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { useInView } from "react-intersection-observer";
import { useAuth0 } from "@auth0/auth0-react";
import Layout from "../components/layout/Layout";
import Card from "../components/ui/Card";
import Spinner from "../components/ui/Spinner";
import Button from "../components/ui/Button";
import LogList from "../components/logs/LogList";
import LogForm from "../components/logs/LogForm";
import OfficialDataSection from "../components/trig/OfficialDataSection";
import TrigInfoSection from "../components/trig/TrigInfoSection";
import TrigDetailMap from "../components/map/TrigDetailMap";
import RichTextDisplay from "../components/ui/RichTextDisplay";
import { useTrigDetail } from "../hooks/useTrigDetail";
import { useTrigLogs } from "../hooks/useTrigLogs";
import { useUserTrigLogs } from "../hooks/useUserTrigLogs";
import { useCurrentUser } from "../hooks/useCurrentUser";
import { useUserProfile } from "../hooks/useUserProfile";
import { useCreateDraftLog } from "../hooks/useCreateDraftLog";
import { usePublishLog } from "../hooks/usePublishLog";
import { useCancelDraftLog } from "../hooks/useCancelDraftLog";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { useCanonical } from "../hooks/useCanonical";
import { useNoIndex } from "../hooks/useNoIndex";
import { Log, LogCreateInput, LogUpdateInput, DuplicateLogError } from "../lib/api";

export default function TrigDetail() {
  const { trigId } = useParams<{ trigId: string }>();
  const trigIdNum = trigId ? parseInt(trigId, 10) : null;
  const navigate = useNavigate();
  const { isAuthenticated, loginWithRedirect, user } = useAuth0();
  const [showLogForm, setShowLogForm] = useState(false);
  const [duplicateLogId, setDuplicateLogId] = useState<number | null>(null);
  // Draft log state - holds the draft log while user is filling in the form
  const [draftLog, setDraftLog] = useState<Log | null>(null);
  const [isCreatingDraft, setIsCreatingDraft] = useState(false);

  // Check if user has admin role
  const userRoles = (user?.["https://trigpointing.uk/roles"] as string[]) || [];
  const hasAdminRole = userRoles.includes("api-admin");

  const {
    data: trig,
    isLoading: isTrigLoading,
    error: trigError,
  } = useTrigDetail(trigIdNum!);

  // Update document title when trig data loads
  useDocumentTitle(trig ? `${trig.waypoint} - ${trig.name}` : null);
  useCanonical(trigIdNum ? `/trigs/${trigIdNum}` : null);
  useNoIndex(!trigIdNum || !!trigError);

  const {
    data: logsData,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading: isLogsLoading,
    error: logsError,
  } = useTrigLogs(trigIdNum!);

  // Get current user for highlighting their logs
  const { data: currentUser } = useCurrentUser();
  
  // Get current user's UI preferences
  const { data: userProfile } = useUserProfile("me");
  const showTrigCondition = userProfile?.prefs?.ui_prefs?.show_trig_condition ?? false;

  // Fetch current user's logs for this trig
  const {
    data: userLogs,
    isLoading: isUserLogsLoading,
  } = useUserTrigLogs(trigIdNum!, currentUser?.id);

  // Draft log mutations
  const createDraftMutation = useCreateDraftLog(trigIdNum!);
  const publishMutation = usePublishLog(draftLog?.id ?? 0, trigIdNum!);
  const cancelDraftMutation = useCancelDraftLog(draftLog?.id, trigIdNum!);

  // Intersection observer for infinite scroll
  const { ref: loadMoreRef, inView } = useInView({
    threshold: 0,
    rootMargin: "200px",
  });

  // Auto-fetch when scrolling into view
  useEffect(() => {
    if (inView && hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  }, [inView, hasNextPage, isFetchingNextPage, fetchNextPage]);

  // Flatten all pages into a single array
  const allLogs = logsData?.pages.flatMap((page) => page.items) || [];

  const handleLogThisTrig = async () => {
    if (!isAuthenticated) {
      loginWithRedirect({
        appState: { returnTo: window.location.pathname },
      });
      return;
    }

    // Create a draft log first so photos can be uploaded
    setIsCreatingDraft(true);
    try {
      const draft = await createDraftMutation.mutateAsync();
      setDraftLog(draft);
      setShowLogForm(true);
    } catch (error) {
      console.error("Failed to create draft log:", error);
      // Show error to user
      alert("Failed to start log creation. Please try again.");
    } finally {
      setIsCreatingDraft(false);
    }
  };

  const handleLogSubmit = async (data: LogCreateInput | LogUpdateInput) => {
    if (!draftLog) {
      console.error("No draft log to publish");
      return;
    }

    try {
      // Publish the draft log with the form data
      const publishedLog = await publishMutation.mutateAsync(data as LogCreateInput);
      setShowLogForm(false);
      setDraftLog(null);
      // Navigate to the published log
      navigate(`/logs/${publishedLog.id}`);
    } catch (error) {
      if (error instanceof DuplicateLogError) {
        // Show the duplicate log modal
        setDuplicateLogId(error.existingLogId);
        return;
      }
      console.error("Failed to publish log:", error);
      throw error;
    }
  };

  const handleDuplicateLogView = () => {
    if (duplicateLogId) {
      // Cancel the draft since user is viewing existing log
      if (draftLog) {
        cancelDraftMutation.mutate();
      }
      setShowLogForm(false);
      setDuplicateLogId(null);
      setDraftLog(null);
      navigate(`/logs/${duplicateLogId}`);
    }
  };

  const handleDuplicateLogDismiss = () => {
    setDuplicateLogId(null);
  };

  const handleLogCancel = async () => {
    // Cancel the draft log if one exists
    if (draftLog) {
      try {
        await cancelDraftMutation.mutateAsync();
      } catch (error) {
        console.error("Failed to cancel draft:", error);
        // Continue anyway - the draft will be cleaned up by the scheduled job
      }
    }
    setShowLogForm(false);
    setDraftLog(null);
  };

  if (!trigIdNum) {
    return (
      <Layout>
        <div className="max-w-7xl mx-auto">
          <Card>
            <p className="text-red-600 dark:text-red-400">Invalid trigpoint ID</p>
          </Card>
        </div>
      </Layout>
    );
  }

  if (trigError) {
    return (
      <Layout>
        <div className="max-w-7xl mx-auto">
          <Card>
            <p className="text-red-600 dark:text-red-400">Failed to load trigpoint details</p>
          </Card>
        </div>
      </Layout>
    );
  }

  if (isTrigLoading) {
    return (
      <Layout>
        <div className="max-w-7xl mx-auto">
          <Card>
            <Spinner size="lg" />
            <p className="text-center text-gray-600 dark:text-gray-400 mt-4">
              Loading trigpoint details...
            </p>
          </Card>
        </div>
      </Layout>
    );
  }

  if (!trig) {
    return (
      <Layout>
        <div className="max-w-7xl mx-auto">
          <Card>
            <p className="text-red-600 dark:text-red-400">Trigpoint not found</p>
          </Card>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="max-w-7xl mx-auto">
        {/* Main Info Section */}
        <TrigInfoSection trig={trig} />

        {/* Interactive Map and Official Data */}
        <div className={`grid grid-cols-1 gap-6 mb-6 ${trig.attrs && trig.attrs.length > 0 ? 'lg:grid-cols-2' : ''}`}>
          <Card className="p-0 overflow-hidden">
            <TrigDetailMap trig={trig} />
          </Card>

          {trig.attrs && trig.attrs.length > 0 && (
            <Card>
              <h2 className="text-xl font-semibold text-trig-green-600 mb-4">
                Official Data
              </h2>
              <OfficialDataSection attrs={trig.attrs} />
            </Card>
          )}
        </div>

        {/* Stats Section */}
        {trig.stats && (
          <Card className="mb-6">
            <h2 className="text-2xl font-bold text-trig-green-600 mb-4">
              Statistics
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
                <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">Total Logs</div>
                <div className="text-2xl font-bold text-trig-green-600">
                  {trig.stats.logged_count}
                </div>
              </div>

              <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
                <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">Found Count</div>
                <div className="text-2xl font-bold text-trig-green-600">
                  {trig.stats.found_count}
                </div>
              </div>

              <Link
                to={`/trigs/${trigIdNum}/photos`}
                className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors block"
              >
                <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">Photos</div>
                <div className="text-2xl font-bold text-trig-green-600">
                  {trig.stats.photo_count}
                </div>
              </Link>

              <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
                <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">Mean Score</div>
                <div className="text-2xl font-bold text-trig-green-600">
                  {parseFloat(trig.stats.score_mean).toFixed(2)}/10
                </div>
              </div>

              <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
                <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">First Logged</div>
                <div className="text-lg font-semibold text-gray-700 dark:text-gray-300 dark:text-gray-200">
                  {trig.stats.logged_first
                    ? new Date(trig.stats.logged_first).toLocaleDateString(
                        "en-GB",
                        {
                          day: "numeric",
                          month: "short",
                          year: "numeric",
                        }
                      )
                    : "Never"}
                </div>
              </div>

              <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
                <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">Last Logged</div>
                <div className="text-lg font-semibold text-gray-700 dark:text-gray-300 dark:text-gray-200">
                  {trig.stats.logged_last
                    ? new Date(trig.stats.logged_last).toLocaleDateString(
                        "en-GB",
                        {
                          day: "numeric",
                          month: "short",
                          year: "numeric",
                        }
                      )
                    : "Never"}
                </div>
              </div>

              <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
                <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">Last Found</div>
                <div className="text-lg font-semibold text-gray-700 dark:text-gray-300 dark:text-gray-200">
                  {trig.stats.found_last
                    ? new Date(trig.stats.found_last).toLocaleDateString(
                        "en-GB",
                        {
                          day: "numeric",
                          month: "short",
                          year: "numeric",
                        }
                      )
                    : "Never"}
                </div>
              </div>

              <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
                <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                  Bayesian Score
                </div>
                <div className="text-lg font-semibold text-gray-700 dark:text-gray-300 dark:text-gray-200">
                  {parseFloat(trig.stats.score_baysian).toFixed(2)}
                </div>
              </div>
            </div>
          </Card>
        )}

        {/* Legal / Access Message */}
        {trig.details?.legal_message && (
          <div className="mb-6 bg-red-50 dark:bg-red-900/30 rounded-lg shadow-md p-4">
            <RichTextDisplay
              html={trig.details.legal_message}
            />
          </div>
        )}

        {/* Log This Trig Section */}
        {!showLogForm && (
          <div className="my-8 flex flex-wrap gap-3">
            <Button 
              onClick={handleLogThisTrig} 
              className="w-full md:w-auto"
              disabled={isCreatingDraft}
            >
              {isCreatingDraft ? (
                <span className="flex items-center gap-2">
                  <Spinner size="sm" />
                  Starting...
                </span>
              ) : (
                <>📝 {userLogs && userLogs.length > 0 ? "Log This Trig Again" : "Log This Trig"}</>
              )}
            </Button>
            {hasAdminRole && (
              <Link to={`/admin/trigs/${trigId}/edit`}>
                <Button variant="secondary" className="w-full md:w-auto">
                  ✏️ Edit This Trig
                </Button>
              </Link>
            )}
          </div>
        )}

        {showLogForm && (
          <div className="my-8 bg-trig-green-200 dark:bg-trig-green-950 border-2 border-trig-green-400 dark:border-trig-green-700 rounded-lg shadow-lg p-6">
            <h2 className="text-2xl font-bold text-trig-green-800 dark:text-gray-100 mb-4 flex items-center gap-2">
              <span>📝</span> Log Your Visit
            </h2>
            <LogForm
              trigGridRef={trig.osgb_gridref}
              trigEastings={parseInt(trig.osgb_gridref.substring(2, 7))} // Simplified - would need proper conversion
              trigNorthings={parseInt(trig.osgb_gridref.substring(7, 12))} // Simplified - would need proper conversion
              trigLatitude={trig.wgs_lat}
              trigLongitude={trig.wgs_long}
              defaultCondition={trig.condition}
              onSubmit={handleLogSubmit}
              onCancel={handleLogCancel}
              isSubmitting={publishMutation.isPending}
              draftLogId={draftLog?.id}
              hideTitle
            />
          </div>
        )}

        {/* Duplicate Log Modal */}
        {duplicateLogId && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <Card className="max-w-md mx-4">
              <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">Log Already Exists</h3>
              <p className="text-gray-700 dark:text-gray-300 mb-6">
                You already have a log for this trigpoint on the selected date.
                Would you like to view or edit your existing log instead?
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

        {/* Divider */}
        <div className="border-t-4 border-gray-200 my-8"></div>

        {/* Your Visits Section - only shown when user is logged in and has logs */}
        {isAuthenticated && userLogs && userLogs.length > 0 && (
          <Card className="mb-6">
            <h2 className="text-2xl font-bold text-trig-green-600 mb-4">
              Your Visits
            </h2>
            <LogList
              logs={userLogs}
              isLoading={isUserLogsLoading}
              emptyMessage="You haven't logged this trig yet"
              currentUserId={currentUser?.id}
              showTrigCondition={showTrigCondition}
              showTrigInfo={false}
              isAdmin={hasAdminRole}
            />
          </Card>
        )}

        {/* Logged Visits Section */}
        <Card>
          <h2 className="text-2xl font-bold text-trig-green-600 mb-4">
            Logged Visits
          </h2>

          {logsError && (
            <p className="text-red-600 dark:text-red-400">Failed to load logged visits</p>
          )}

          {!logsError && (
            <>
              <LogList
                logs={allLogs}
                isLoading={isLogsLoading}
                emptyMessage="No logged visits yet"
                currentUserId={currentUser?.id}
                showTrigCondition={showTrigCondition}
                showTrigInfo={false}
                isAdmin={hasAdminRole}
              />

              {/* Load More Trigger */}
              {allLogs.length > 0 && (
                <div ref={loadMoreRef} className="py-8 text-center">
                  {isFetchingNextPage && (
                    <>
                      <Spinner size="md" />
                      <p className="text-gray-600 mt-4">Loading more logs...</p>
                    </>
                  )}
                  {!hasNextPage && (
                    <p className="text-gray-500">
                      All {allLogs.length} logged visit
                      {allLogs.length !== 1 ? "s" : ""} loaded
                    </p>
                  )}
                </div>
              )}
            </>
          )}
        </Card>
      </div>
    </Layout>
  );
}

