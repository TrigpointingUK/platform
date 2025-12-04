import { useEffect, useState, useMemo } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { useInView } from "react-intersection-observer";
import { useAuth0 } from "@auth0/auth0-react";
import Layout from "../components/layout/Layout";
import Card from "../components/ui/Card";
import Badge from "../components/ui/Badge";
import Spinner from "../components/ui/Spinner";
import Button from "../components/ui/Button";
import LogList from "../components/logs/LogList";
import LogForm from "../components/logs/LogForm";
import OfficialDataSection from "../components/trig/OfficialDataSection";
import TrigDetailMap from "../components/map/TrigDetailMap";
import { useTrigDetail } from "../hooks/useTrigDetail";
import { useTrigLogs } from "../hooks/useTrigLogs";
import { useUserTrigLogs } from "../hooks/useUserTrigLogs";
import { useCurrentUser } from "../hooks/useCurrentUser";
import { useCreateLog } from "../hooks/useCreateLog";
import { useAreasContaining, type Area } from "../hooks/useAreasContaining";
import { LogCreateInput, LogUpdateInput, DuplicateLogError } from "../lib/api";

const conditionMap: Record<
  string,
  { label: string; icon: string; variant: "good" | "damaged" | "missing" | "unknown" }
> = {
  Z: { label: "Not Logged", icon: "c_unknown.png", variant: "unknown" },
  N: { label: "Couldn't Find", icon: "c_possiblymissing.png", variant: "missing" },
  G: { label: "Good", icon: "c_good.png", variant: "good" },
  S: { label: "Slightly Damaged", icon: "c_slightlydamaged.png", variant: "damaged" },
  C: { label: "Converted", icon: "c_slightlydamaged.png", variant: "damaged" },
  D: { label: "Damaged", icon: "c_damaged.png", variant: "damaged" },
  R: { label: "Remains", icon: "c_toppled.png", variant: "damaged" },
  T: { label: "Toppled", icon: "c_toppled.png", variant: "damaged" },
  M: { label: "Moved", icon: "c_toppled.png", variant: "missing" },
  Q: { label: "Possibly Missing", icon: "c_possiblymissing.png", variant: "damaged" },
  X: { label: "Destroyed", icon: "c_definitelymissing.png", variant: "missing" },
  V: { label: "Unreachable but Visible", icon: "c_unreachablebutvisible.png", variant: "unknown" },
  P: { label: "Inaccessible", icon: "c_unknown.png", variant: "unknown" },
  U: { label: "Unknown", icon: "c_unknown.png", variant: "unknown" },
};

export default function TrigDetail() {
  const { trigId } = useParams<{ trigId: string }>();
  const trigIdNum = trigId ? parseInt(trigId, 10) : null;
  const navigate = useNavigate();
  const { isAuthenticated, loginWithRedirect, user } = useAuth0();
  const [showLogForm, setShowLogForm] = useState(false);
  const [duplicateLogId, setDuplicateLogId] = useState<number | null>(null);

  // Check if user has admin role
  const userRoles = (user?.["https://trigpointing.uk/roles"] as string[]) || [];
  const hasAdminRole = userRoles.includes("api-admin");

  const {
    data: trig,
    isLoading: isTrigLoading,
    error: trigError,
  } = useTrigDetail(trigIdNum!);

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

  // Fetch current user's logs for this trig
  const {
    data: userLogs,
    isLoading: isUserLogsLoading,
  } = useUserTrigLogs(trigIdNum!, currentUser?.id);

  const createLogMutation = useCreateLog(trigIdNum!);

  // Fetch areas containing this trigpoint
  const { data: areasData, isLoading: isAreasLoading } = useAreasContaining(
    trig ? parseFloat(trig.wgs_lat) : undefined,
    trig ? parseFloat(trig.wgs_long) : undefined
  );

  // Flatten areas for the dropdown
  const allAreas = useMemo(() => {
    if (!areasData?.groups) return [];
    const areas: Area[] = [];
    for (const group of areasData.groups) {
      areas.push(...group.areas);
    }
    // Sort by area type name, then area name
    return areas.sort((a, b) => {
      const typeCompare = a.area_type.name.localeCompare(b.area_type.name);
      if (typeCompare !== 0) return typeCompare;
      return a.name.localeCompare(b.name);
    });
  }, [areasData]);

  // State for areas dropdown
  const [isAreasDropdownOpen, setIsAreasDropdownOpen] = useState(false);

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

  const handleLogThisTrig = () => {
    if (!isAuthenticated) {
      loginWithRedirect({
        appState: { returnTo: window.location.pathname },
      });
      return;
    }
    setShowLogForm(true);
  };

  const handleLogSubmit = async (data: LogCreateInput | LogUpdateInput) => {
    try {
      const newLog = await createLogMutation.mutateAsync(data as LogCreateInput);
      setShowLogForm(false);
      // Navigate to the new log
      navigate(`/logs/${newLog.id}`);
    } catch (error) {
      if (error instanceof DuplicateLogError) {
        // Show the duplicate log modal
        setDuplicateLogId(error.existingLogId);
        return;
      }
      console.error("Failed to create log:", error);
      throw error;
    }
  };

  const handleDuplicateLogView = () => {
    if (duplicateLogId) {
      setShowLogForm(false);
      setDuplicateLogId(null);
      navigate(`/logs/${duplicateLogId}`);
    }
  };

  const handleDuplicateLogDismiss = () => {
    setDuplicateLogId(null);
  };

  const handleLogCancel = () => {
    setShowLogForm(false);
  };

  if (!trigIdNum) {
    return (
      <Layout>
        <div className="max-w-7xl mx-auto">
          <Card>
            <p className="text-red-600">Invalid trigpoint ID</p>
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
            <p className="text-red-600">Failed to load trigpoint details</p>
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
            <p className="text-center text-gray-600 mt-4">
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
            <p className="text-red-600">Trigpoint not found</p>
          </Card>
        </div>
      </Layout>
    );
  }

  const condition = conditionMap[trig.condition] || conditionMap.U;
  const apiBase = import.meta.env.VITE_API_BASE as string;

  // Helper function to create wiki links
  const getWikiUrl = (value: string) => {
    const wikiValue = value.replace(/ /g, "_");
    return `https://wiki.trigpointing.uk/${wikiValue}`;
  };

  // Helper function to check if a value should have a wiki link
  const shouldHaveWikiLink = (value: string) => {
    return value && value.toLowerCase() !== "none" && value.trim() !== "";
  };

  return (
    <Layout>
      <div className="max-w-7xl mx-auto">
        {/* Main Info Section */}
        <Card className="mb-6">
          <div className="flex flex-col lg:flex-row gap-6">
            {/* Left: Info Grid */}
            <div className="flex-1">
              <h1 className="text-3xl font-bold text-trig-green-600 mb-4">
                {trig.waypoint} - {trig.name}
              </h1>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-3 text-sm">
                <div>
                  <span className="font-semibold text-gray-700">
                    OS Grid reference:
                  </span>{" "}
                  <a
                    href={`https://openstreetmap.org/?mlat=${trig.wgs_lat}&mlon=${trig.wgs_long}#map=16/${trig.wgs_lat}/${trig.wgs_long}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-trig-green-600 hover:underline"
                  >
                    {trig.osgb_gridref}
                  </a>
                </div>

                <div>
                  <span className="font-semibold text-gray-700">
                    WGS coordinates:
                  </span>{" "}
                  <a
                    href={`https://www.google.com/maps?q=${trig.wgs_lat},${trig.wgs_long}&t=k&z=18`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-trig-green-600 hover:underline"
                  >
                    {trig.wgs_lat}, {trig.wgs_long}
                  </a>
                </div>

                <div className="hidden">
                  <span className="font-semibold text-gray-700">
                    Height (OSGB):
                  </span>{" "}
                  {trig.details?.osgb_height}m
                </div>

                {trig.details && trig.details.postcode && (
                  <div>
                    <span className="font-semibold text-gray-700">
                      Postcode:
                    </span>{" "}
                    {trig.details.postcode}
                  </div>
                )}

                <div>
                  <span className="font-semibold text-gray-700">Type:</span>{" "}
                  {shouldHaveWikiLink(trig.physical_type) ? (
                    <a
                      href={getWikiUrl(trig.physical_type)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-trig-green-600 hover:underline"
                    >
                      {trig.physical_type}
                    </a>
                  ) : (
                    trig.physical_type
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <span className="font-semibold text-gray-700">
                    Condition:
                  </span>
                  <Badge variant={condition.variant}>
                    <img
                      src={`/icons/conditions/${condition.icon}`}
                      alt=""
                      className="w-4 h-4 inline-block mr-1.5"
                    />
                    {condition.label}
                  </Badge>
                </div>

                {trig.details && (
                  <>
                    {trig.details.fb_number && (
                      <div>
                        <span className="font-semibold text-gray-700">
                          Flush Bracket:
                        </span>{" "}
                        {trig.details.fb_number}
                      </div>
                    )}

                    {trig.details.stn_number_active && trig.details.stn_number_active.trim() !== "" && (
                      <div>
                        <span className="font-semibold text-gray-700">
                          Active Station:
                        </span>{" "}
                        {trig.details.stn_number_active}
                      </div>
                    )}

                    {trig.details.stn_number_passive && trig.details.stn_number_passive.trim() !== "" && (
                      <div>
                        <span className="font-semibold text-gray-700">
                          Passive Station:
                        </span>{" "}
                        <a
                          href={`https://www.ordnancesurvey.co.uk/geodesy-positioning/legacy-data/passive-search/passive-station/${trig.details.stn_number_passive}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-trig-green-600 hover:underline"
                        >
                          {trig.details.stn_number_passive}
                        </a>
                      </div>
                    )}

                    {trig.details.stn_number_osgb36 && trig.details.stn_number_osgb36.trim() !== "" && (
                      <div>
                        <span className="font-semibold text-gray-700">
                          OSGB36 Station:
                        </span>{" "}
                        {trig.details.stn_number_osgb36}
                      </div>
                    )}

                    <div>
                      <span className="font-semibold text-gray-700">
                        Recent use:
                      </span>{" "}
                      {shouldHaveWikiLink(trig.details.current_use) ? (
                        <a
                          href={getWikiUrl(trig.details.current_use)}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-trig-green-600 hover:underline"
                        >
                          {trig.details.current_use}
                        </a>
                      ) : (
                        trig.details.current_use
                      )}
                    </div>

                    <div>
                      <span className="font-semibold text-gray-700">
                        Historic use:
                      </span>{" "}
                      {shouldHaveWikiLink(trig.details.historic_use) ? (
                        <a
                          href={getWikiUrl(trig.details.historic_use)}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-trig-green-600 hover:underline"
                        >
                          {trig.details.historic_use}
                        </a>
                      ) : (
                        trig.details.historic_use
                      )}
                    </div>

                    <div>
                      <span className="font-semibold text-gray-700">
                        County:
                      </span>{" "}
                      {trig.details.county}
                    </div>

                    <div>
                      <span className="font-semibold text-gray-700">
                        Nearest town:
                      </span>{" "}
                      {trig.details.town}
                    </div>
                  </>
                )}
              </div>

              {/* Map Links */}
              <div className="mt-4 pt-4 border-t border-gray-200">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  <div>
                    <Link
                      to={`/map?lat=${trig.wgs_lat}&lon=${trig.wgs_long}&trig=${trigIdNum}`}
                      className="text-trig-green-600 hover:underline font-semibold"
                    >
                      🗺️ View on Interactive Map
                    </Link>
                  </div>
                  <div>
                    <Link
                      to={`/trigs/${trigIdNum}/photos`}
                      className="text-trig-green-600 hover:underline font-semibold"
                    >
                      📷 View Photo Album
                    </Link>
                  </div>
                  {/* Nearby trigpoints dropdown */}
                  <div className="relative">
                    <button
                      onClick={() => setIsAreasDropdownOpen(!isAreasDropdownOpen)}
                      className="text-trig-green-600 hover:underline font-semibold flex items-center gap-1"
                    >
                      📍 View Nearby Trigpoints
                      {isAreasLoading ? (
                        <span className="text-gray-400 text-xs">(loading...)</span>
                      ) : (
                        <svg
                          className={`w-4 h-4 transition-transform ${isAreasDropdownOpen ? 'rotate-180' : ''}`}
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                        </svg>
                      )}
                    </button>
                    
                    {isAreasDropdownOpen && (
                      <>
                        {/* Backdrop to close dropdown */}
                        <div
                          className="fixed inset-0 z-[1100]"
                          onClick={() => setIsAreasDropdownOpen(false)}
                        />
                        
                        {/* Dropdown menu */}
                        <div className="absolute left-0 mt-1 w-72 max-h-64 overflow-y-auto bg-white border border-gray-200 rounded-lg shadow-lg z-[1101]">
                          {/* All nearby option */}
                          <Link
                            to={`/trigs?lat=${trig.wgs_lat}&lon=${trig.wgs_long}&location=${encodeURIComponent(`${trig.waypoint} - ${trig.name}`)}`}
                            className="block px-3 py-2 text-sm text-gray-700 hover:bg-trig-green-50 hover:text-trig-green-700 font-medium"
                            onClick={() => setIsAreasDropdownOpen(false)}
                          >
                            All nearby trigpoints
                          </Link>
                          
                          {/* Divider and area options */}
                          {allAreas.length > 0 && (
                            <>
                              <div className="border-t border-gray-200 my-1" />
                              {allAreas.map((area) => (
                                <Link
                                  key={area.id}
                                  to={`/trigs?lat=${trig.wgs_lat}&lon=${trig.wgs_long}&location=${encodeURIComponent(`${trig.waypoint} - ${trig.name}`)}&areaId=${area.id}&areaName=${encodeURIComponent(`${area.area_type.name} : ${area.name}`)}`}
                                  className="block px-3 py-2 text-sm text-gray-700 hover:bg-trig-green-50 hover:text-trig-green-700 border-b border-gray-100 last:border-b-0"
                                  onClick={() => setIsAreasDropdownOpen(false)}
                                >
                                  <span className="font-medium">{area.area_type.name}</span>
                                  <span className="text-gray-400 mx-1">:</span>
                                  <span>{area.name}</span>
                                </Link>
                              ))}
                            </>
                          )}
                        </div>
                      </>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Right: Map Thumbnail */}
            <div className="flex-shrink-0">
              <img
                src={`${apiBase}/v1/trigs/${trigIdNum}/map`}
                alt={`Map thumbnail for ${trig.name}`}
                className="w-[110px] h-[110px] border border-gray-300 rounded"
              />
            </div>
          </div>
        </Card>

        {/* Interactive Map and Official Data */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <Card className="p-0 overflow-hidden">
            <TrigDetailMap trig={trig} />
          </Card>

          {trig.attrs && trig.attrs.length > 0 ? (
            <Card>
              <h2 className="text-xl font-semibold text-gray-800 mb-4">
                Official Data
              </h2>
              <OfficialDataSection attrs={trig.attrs} />
            </Card>
          ) : (
            <Card className="bg-gray-50 border-2 border-dashed border-gray-300">
              <div className="text-center py-12">
                <div className="text-4xl mb-3">📋</div>
                <h3 className="text-xl font-semibold text-gray-600 mb-2">
                  Official Data
                </h3>
                <p className="text-gray-500">No official data available</p>
              </div>
            </Card>
          )}
        </div>

        {/* Stats Section */}
        {trig.stats && (
          <Card className="mb-6">
            <h2 className="text-2xl font-bold text-gray-800 mb-4">
              Statistics
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-gray-50 p-4 rounded-lg">
                <div className="text-sm text-gray-600 mb-1">Total Logs</div>
                <div className="text-2xl font-bold text-trig-green-600">
                  {trig.stats.logged_count}
                </div>
              </div>

              <div className="bg-gray-50 p-4 rounded-lg">
                <div className="text-sm text-gray-600 mb-1">Found Count</div>
                <div className="text-2xl font-bold text-trig-green-600">
                  {trig.stats.found_count}
                </div>
              </div>

              <Link
                to={`/trigs/${trigIdNum}/photos`}
                className="bg-gray-50 p-4 rounded-lg hover:bg-gray-100 transition-colors block"
              >
                <div className="text-sm text-gray-600 mb-1">Photos</div>
                <div className="text-2xl font-bold text-trig-green-600">
                  {trig.stats.photo_count}
                </div>
              </Link>

              <div className="bg-gray-50 p-4 rounded-lg">
                <div className="text-sm text-gray-600 mb-1">Mean Score</div>
                <div className="text-2xl font-bold text-trig-green-600">
                  {parseFloat(trig.stats.score_mean).toFixed(2)}/10
                </div>
              </div>

              <div className="bg-gray-50 p-4 rounded-lg">
                <div className="text-sm text-gray-600 mb-1">First Logged</div>
                <div className="text-lg font-semibold text-gray-700">
                  {new Date(trig.stats.logged_first).toLocaleDateString(
                    "en-GB",
                    {
                      day: "numeric",
                      month: "short",
                      year: "numeric",
                    }
                  )}
                </div>
              </div>

              <div className="bg-gray-50 p-4 rounded-lg">
                <div className="text-sm text-gray-600 mb-1">Last Logged</div>
                <div className="text-lg font-semibold text-gray-700">
                  {new Date(trig.stats.logged_last).toLocaleDateString(
                    "en-GB",
                    {
                      day: "numeric",
                      month: "short",
                      year: "numeric",
                    }
                  )}
                </div>
              </div>

              <div className="bg-gray-50 p-4 rounded-lg">
                <div className="text-sm text-gray-600 mb-1">Last Found</div>
                <div className="text-lg font-semibold text-gray-700">
                  {new Date(trig.stats.found_last).toLocaleDateString("en-GB", {
                    day: "numeric",
                    month: "short",
                    year: "numeric",
                  })}
                </div>
              </div>

              <div className="bg-gray-50 p-4 rounded-lg">
                <div className="text-sm text-gray-600 mb-1">
                  Bayesian Score
                </div>
                <div className="text-lg font-semibold text-gray-700">
                  {parseFloat(trig.stats.score_baysian).toFixed(2)}
                </div>
              </div>
            </div>
          </Card>
        )}

        {/* Log This Trig Section */}
        {!showLogForm && (
          <div className="my-8 flex flex-wrap gap-3">
            <Button onClick={handleLogThisTrig} className="w-full md:w-auto">
              📝 {userLogs && userLogs.length > 0 ? "Log This Trig Again" : "Log This Trig"}
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
          <div className="my-8">
            <LogForm
              trigGridRef={trig.osgb_gridref}
              trigEastings={parseInt(trig.osgb_gridref.substring(2, 7))} // Simplified - would need proper conversion
              trigNorthings={parseInt(trig.osgb_gridref.substring(7, 12))} // Simplified - would need proper conversion
              trigLatitude={parseFloat(trig.wgs_lat)}
              trigLongitude={parseFloat(trig.wgs_long)}
              defaultCondition={trig.condition}
              onSubmit={handleLogSubmit}
              onCancel={handleLogCancel}
              isSubmitting={createLogMutation.isPending}
            />
          </div>
        )}

        {/* Duplicate Log Modal */}
        {duplicateLogId && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <Card className="max-w-md mx-4">
              <h3 className="text-lg font-semibold mb-4">Log Already Exists</h3>
              <p className="text-gray-700 mb-6">
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
            <h2 className="text-2xl font-bold text-gray-800 mb-4">
              Your Visits
            </h2>
            <LogList
              logs={userLogs}
              isLoading={isUserLogsLoading}
              emptyMessage="You haven't logged this trig yet"
              currentUserId={currentUser?.id}
            />
          </Card>
        )}

        {/* Logged Visits Section */}
        <Card>
          <h2 className="text-2xl font-bold text-gray-800 mb-4">
            Logged Visits
          </h2>

          {logsError && (
            <p className="text-red-600">Failed to load logged visits</p>
          )}

          {!logsError && (
            <>
              <LogList
                logs={allLogs}
                isLoading={isLogsLoading}
                emptyMessage="No logged visits yet"
                currentUserId={currentUser?.id}
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

