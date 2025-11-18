import { useEffect, useState } from "react";
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
import { useCreateLog } from "../hooks/useCreateLog";
import { LogCreateInput, LogUpdateInput } from "../lib/api";

const conditionMap: Record<
  string,
  { label: string; variant: "good" | "damaged" | "missing" | "unknown" }
> = {
  G: { label: "Good", variant: "good" },
  D: { label: "Damaged", variant: "damaged" },
  M: { label: "Missing", variant: "missing" },
  P: { label: "Possibly Missing", variant: "damaged" },
  U: { label: "Unknown", variant: "unknown" },
};

export default function TrigDetail() {
  const { trigId } = useParams<{ trigId: string }>();
  const trigIdNum = trigId ? parseInt(trigId, 10) : null;
  const navigate = useNavigate();
  const { isAuthenticated, loginWithRedirect, user } = useAuth0();
  const [showLogForm, setShowLogForm] = useState(false);

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

  const createLogMutation = useCreateLog(trigIdNum!);

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
      console.error("Failed to create log:", error);
      throw error;
    }
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

                {trig.details && trig.details.osgb_height && (
                  <div>
                    <span className="font-semibold text-gray-700">
                      Height (OSGB):
                    </span>{" "}
                    {trig.details.osgb_height}m
                  </div>
                )}

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
                  <Badge variant={condition.variant}>{condition.label}</Badge>
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

                    {trig.details.stn_number_osgb36 && (
                      <div>
                        <span className="font-semibold text-gray-700">
                          OSGB36 Station:
                        </span>{" "}
                        {trig.details.stn_number_osgb36}
                      </div>
                    )}

                    {trig.details.stn_number && trig.details.stn_number.trim() !== "" && (
                      <div>
                        <span className="font-semibold text-gray-700">
                          Passive Station:
                        </span>{" "}
                        <a
                          href={`https://www.ordnancesurvey.co.uk/geodesy-positioning/legacy-data/passive-search/passive-station/${trig.details.stn_number}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-trig-green-600 hover:underline"
                        >
                          {trig.details.stn_number}
                        </a>
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
                  <div>
                    <Link
                      to={`/trigs?lat=${trig.wgs_lat}&lon=${trig.wgs_long}&location=${encodeURIComponent(`${trig.waypoint} - ${trig.name}`)}`}
                      className="text-trig-green-600 hover:underline font-semibold"
                    >
                      📍 View Nearby Trigpoints
                    </Link>
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
              📝 Log This Trig
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
              onSubmit={handleLogSubmit}
              onCancel={handleLogCancel}
              isSubmitting={createLogMutation.isPending}
            />
          </div>
        )}

        {/* Divider */}
        <div className="border-t-4 border-gray-200 my-8"></div>

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

