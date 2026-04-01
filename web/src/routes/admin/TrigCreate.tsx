import { FormEvent, useEffect, useMemo, useState } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import { Link, useNavigate } from "react-router-dom";
import Card from "../../components/ui/Card";
import Spinner from "../../components/ui/Spinner";
import Button from "../../components/ui/Button";
import LinkedCoordinates from "../../components/admin/LinkedCoordinates";
import RichTextEditor from "../../components/ui/RichTextEditor";
import { useDocumentTitle } from "../../hooks/useDocumentTitle";
import { useAdminAuth } from "../../hooks/useAdminAuth";
import { useTrigCategories } from "../../hooks/useTrigTypes";
import { useConditions } from "../../hooks/useConditions";
import {
  fetchStatuses,
  createTrigAdmin,
  StatusRecord,
} from "../../lib/api";

const ADMIN_AUTH_PARAMS = {
  audience: import.meta.env.VITE_AUTH0_AUDIENCE as string | undefined,
  scope: "openid profile email api:write api:read-pii offline_access api:admin",
};

// Fallback condition options for when API data is loading
const FALLBACK_CONDITION_OPTIONS = [
  { value: "U", label: "Unknown" },
  { value: "G", label: "Good" },
  { value: "S", label: "Slightly damaged" },
  { value: "C", label: "Converted" },
  { value: "D", label: "Damaged" },
  { value: "R", label: "Remains" },
  { value: "T", label: "Toppled" },
  { value: "M", label: "Moved" },
  { value: "Q", label: "Possibly missing" },
  { value: "X", label: "Destroyed" },
  { value: "V", label: "Unreachable but visible" },
  { value: "P", label: "Inaccessible" },
  { value: "N", label: "Couldn't find it" },
  { value: "Z", label: "Not Logged" },
];

const CURRENT_USE_OPTIONS = [
  "none",
  "Passive station",
  "Active station",
];

const HISTORIC_USE_OPTIONS = [
  "none",
  "Primary",
  "Secondary",
  "3rd order",
  "4th order",
  "Fundamental",
  "Intersection",
];

export default function TrigCreate() {
  const { getAccessTokenSilently } = useAuth0();
  const navigate = useNavigate();
  const { hasAdminRole, hasAdminScope, isLoading: isAuthLoading } = useAdminAuth();

  const [statuses, setStatuses] = useState<StatusRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Fetch trig type categories for the dropdown
  const { data: typeCategories, isLoading: isLoadingTypes } = useTrigCategories();

  // Fetch condition options from API
  const { data: apiConditions } = useConditions();
  const conditionOptions = useMemo(() => {
    if (!apiConditions || apiConditions.length === 0) {
      return FALLBACK_CONDITION_OPTIONS;
    }
    return apiConditions.map((c) => ({ value: c.code, label: c.name }));
  }, [apiConditions]);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Set document title
  useDocumentTitle("Create New Trigpoint");

  // Form fields with empty defaults
  const [name, setName] = useState("");
  const [fbNumber, setFbNumber] = useState("");
  const [stnNumber, setStnNumber] = useState("");
  const [stnNumberActive, setStnNumberActive] = useState("");
  const [stnNumberPassive, setStnNumberPassive] = useState("");
  const [stnNumberOsgb36, setStnNumberOsgb36] = useState("");
  const [statusId, setStatusId] = useState(10); // Default to a common status
  const [typeId, setTypeId] = useState<number | null>(null);
  const [currentUse, setCurrentUse] = useState("none");
  const [historicUse, setHistoricUse] = useState("none");
  const [condition, setCondition] = useState("U");
  const [wgsLat, setWgsLat] = useState("");
  const [wgsLong, setWgsLong] = useState("");
  const [wgsHeight, setWgsHeight] = useState<number | null>(null);
  const [osgbEastings, setOsgbEastings] = useState(0);
  const [osgbNorthings, setOsgbNorthings] = useState(0);
  const [osgbGridref, setOsgbGridref] = useState("");
  const [osgbHeight, setOsgbHeight] = useState<number | null>(null);
  const [legalMessage, setLegalMessage] = useState<string>("");
  const [adminComment, setAdminComment] = useState("");

  useEffect(() => {
    if (!hasAdminRole || !hasAdminScope) {
      return;
    }

    let cancelled = false;

    const fetchData = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const token = await getAccessTokenSilently({
          authorizationParams: { ...ADMIN_AUTH_PARAMS },
        });

        const statusesData = await fetchStatuses(token);

        if (!cancelled) {
          setStatuses(statusesData);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load data");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    fetchData();

    return () => {
      cancelled = true;
    };
  }, [getAccessTokenSilently, hasAdminRole, hasAdminScope]);

  const handleWgsChange = (lat: string, long: string, height: number | null) => {
    setWgsLat(lat);
    setWgsLong(long);
    setWgsHeight(height);
  };

  const handleOsgbChange = (eastings: number, northings: number, gridref: string, height: number | null) => {
    setOsgbEastings(eastings);
    setOsgbNorthings(northings);
    setOsgbGridref(gridref);
    setOsgbHeight(height);
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();

    if (!adminComment.trim()) {
      setSaveError("Admin comment is required");
      return;
    }

    if (!name.trim()) {
      setSaveError("Name is required");
      return;
    }

    if (!wgsLat || !wgsLong) {
      setSaveError("Coordinates are required");
      return;
    }

    setIsSaving(true);
    setSaveError(null);
    setSaveSuccess(false);

    try {
      const token = await getAccessTokenSilently({
        authorizationParams: { ...ADMIN_AUTH_PARAMS },
      });

      const newTrig = await createTrigAdmin(
        {
          name,
          fb_number: fbNumber,
          stn_number: stnNumber,
          stn_number_active: stnNumberActive,
          stn_number_passive: stnNumberPassive,
          stn_number_osgb36: stnNumberOsgb36,
          status_id: statusId,
          type_id: typeId,
          current_use: currentUse,
          historic_use: historicUse,
          condition,
          wgs_lat: wgsLat,
          wgs_long: wgsLong,
          wgs_height: wgsHeight,
          osgb_eastings: osgbEastings,
          osgb_northings: osgbNorthings,
          osgb_gridref: osgbGridref,
          osgb_height: osgbHeight,
          legal_message: legalMessage || null,
          admin_comment: adminComment,
        },
        token
      );

      setSaveSuccess(true);
      // Redirect to the new trigpoint's detail page after short delay
      setTimeout(() => {
        navigate(`/trigs/${newTrig.id}`);
      }, 1500);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Failed to create trigpoint");
    } finally {
      setIsSaving(false);
    }
  };

  if (!hasAdminRole) {
    return (
      <>
        <div className="max-w-6xl mx-auto">
          <Card>
            <div className="text-center py-12">
              <h1 className="text-2xl font-bold text-gray-800 dark:text-gray-100 mb-4">
                Access Denied
              </h1>
              <p className="text-gray-600 dark:text-gray-400">
                You do not have permission to access this page.
              </p>
            </div>
          </Card>
        </div>
      </>
    );
  }

  // Show loading state while checking admin scope
  if (isAuthLoading || !hasAdminScope) {
    return (
      <>
        <div className="max-w-6xl mx-auto">
          <Card>
            <div className="flex flex-col items-center justify-center py-12">
              <Spinner size="lg" />
              <span className="mt-3 text-gray-600 dark:text-gray-400">
                {isAuthLoading ? "Verifying admin permissions..." : "Requesting elevated permissions..."}
              </span>
            </div>
          </Card>
        </div>
      </>
    );
  }

  if (isLoading) {
    return (
      <>
        <div className="max-w-6xl mx-auto">
          <Card>
            <div className="flex items-center justify-center py-12">
              <Spinner size="lg" />
              <span className="ml-3 text-gray-600 dark:text-gray-400">Loading...</span>
            </div>
          </Card>
        </div>
      </>
    );
  }

  if (error) {
    return (
      <>
        <div className="max-w-6xl mx-auto">
          <Card>
            <div className="text-center py-12">
              <p className="text-red-600 dark:text-red-400">Error: {error}</p>
              <Link
                to="/admin"
                className="text-trig-green-600 hover:text-trig-green-700 dark:text-trig-green-400 dark:hover:text-trig-green-300 mt-4 inline-block"
              >
                ← Back to Admin
              </Link>
            </div>
          </Card>
        </div>
      </>
    );
  }

  return (
    <>
      <div className="max-w-6xl mx-auto">
        <Card className="mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100 mb-2">
                Create New Trigpoint
              </h1>
              <p className="text-gray-600 dark:text-gray-400">
                A waypoint code will be automatically assigned when the trigpoint is created.
              </p>
            </div>
            <Link
              to="/admin"
              className="text-trig-green-600 hover:text-trig-green-700 dark:text-trig-green-400 dark:hover:text-trig-green-300 font-medium"
            >
              ← Back to Admin
            </Link>
          </div>
        </Card>

        <form onSubmit={handleSubmit} className="space-y-6">
          <Card>
            <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-100 mb-4">
              Basic Information
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  className="w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-gray-800 dark:text-gray-100 bg-white dark:bg-gray-700 shadow-sm focus:border-trig-green-500 focus:ring-2 focus:ring-trig-green-400"
                  placeholder="e.g., Ben Nevis"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Type
                </label>
                <select
                  value={typeId ?? ""}
                  onChange={(e) => setTypeId(e.target.value ? parseInt(e.target.value) : null)}
                  className="w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-gray-800 dark:text-gray-100 bg-white dark:bg-gray-700 shadow-sm focus:border-trig-green-500 focus:ring-2 focus:ring-trig-green-400"
                  disabled={isLoadingTypes}
                >
                  <option value="">Select type...</option>
                  {isLoadingTypes ? (
                    <option value="">Loading types...</option>
                  ) : (
                    typeCategories?.map((category) => (
                      <optgroup key={category.id} label={category.name}>
                        {category.types.map((type) => (
                          <option key={type.id} value={type.id}>
                            {type.name}
                          </option>
                        ))}
                      </optgroup>
                    ))
                  )}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Status
                </label>
                <select
                  value={statusId}
                  onChange={(e) => setStatusId(parseInt(e.target.value))}
                  className="w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-gray-800 dark:text-gray-100 bg-white dark:bg-gray-700 shadow-sm focus:border-trig-green-500 focus:ring-2 focus:ring-trig-green-400"
                >
                  {statuses.map((status) => (
                    <option key={status.id} value={status.id}>
                      {status.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Recent Use
                </label>
                <select
                  value={currentUse}
                  onChange={(e) => setCurrentUse(e.target.value)}
                  className="w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-gray-800 dark:text-gray-100 bg-white dark:bg-gray-700 shadow-sm focus:border-trig-green-500 focus:ring-2 focus:ring-trig-green-400"
                >
                  {CURRENT_USE_OPTIONS.map((use) => (
                    <option key={use} value={use}>
                      {use}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Historic Use
                </label>
                <select
                  value={historicUse}
                  onChange={(e) => setHistoricUse(e.target.value)}
                  className="w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-gray-800 dark:text-gray-100 bg-white dark:bg-gray-700 shadow-sm focus:border-trig-green-500 focus:ring-2 focus:ring-trig-green-400"
                >
                  {HISTORIC_USE_OPTIONS.map((use) => (
                    <option key={use} value={use}>
                      {use}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Condition
                </label>
                <select
                  value={condition}
                  onChange={(e) => setCondition(e.target.value)}
                  className="w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-gray-800 dark:text-gray-100 bg-white dark:bg-gray-700 shadow-sm focus:border-trig-green-500 focus:ring-2 focus:ring-trig-green-400"
                >
                  {conditionOptions.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  FB Number
                </label>
                <input
                  type="text"
                  value={fbNumber}
                  onChange={(e) => setFbNumber(e.target.value)}
                  className="w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-gray-800 dark:text-gray-100 bg-white dark:bg-gray-700 shadow-sm focus:border-trig-green-500 focus:ring-2 focus:ring-trig-green-400"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Station Number
                </label>
                <input
                  type="text"
                  value={stnNumber}
                  onChange={(e) => setStnNumber(e.target.value)}
                  className="w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-gray-800 dark:text-gray-100 bg-white dark:bg-gray-700 shadow-sm focus:border-trig-green-500 focus:ring-2 focus:ring-trig-green-400"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Station Number (Active)
                </label>
                <input
                  type="text"
                  value={stnNumberActive}
                  onChange={(e) => setStnNumberActive(e.target.value)}
                  className="w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-gray-800 dark:text-gray-100 bg-white dark:bg-gray-700 shadow-sm focus:border-trig-green-500 focus:ring-2 focus:ring-trig-green-400"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Station Number (Passive)
                </label>
                <input
                  type="text"
                  value={stnNumberPassive}
                  onChange={(e) => setStnNumberPassive(e.target.value)}
                  className="w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-gray-800 dark:text-gray-100 bg-white dark:bg-gray-700 shadow-sm focus:border-trig-green-500 focus:ring-2 focus:ring-trig-green-400"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Station Number (OSGB36)
                </label>
                <input
                  type="text"
                  value={stnNumberOsgb36}
                  onChange={(e) => setStnNumberOsgb36(e.target.value)}
                  className="w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-gray-800 dark:text-gray-100 bg-white dark:bg-gray-700 shadow-sm focus:border-trig-green-500 focus:ring-2 focus:ring-trig-green-400"
                />
              </div>
            </div>
          </Card>

          <Card>
            <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-100 mb-4">
              Coordinates <span className="text-red-500">*</span>
            </h2>
            <LinkedCoordinates
              wgsLat={wgsLat}
              wgsLong={wgsLong}
              wgsHeight={wgsHeight}
              osgbEastings={osgbEastings}
              osgbNorthings={osgbNorthings}
              osgbGridref={osgbGridref}
              osgbHeight={osgbHeight}
              initialGridSystem="gb"
              onWgsChange={handleWgsChange}
              onOsgbChange={handleOsgbChange}
            />
          </Card>

          <Card>
            <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-100 mb-4">
              Legal / Access Information
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
              Optional message displayed on the trigpoint detail page above the &quot;Log this trig&quot; button.
              Use this for access restrictions, landowner permissions, or safety warnings.
            </p>
            <RichTextEditor
              value={legalMessage}
              onChange={setLegalMessage}
              placeholder="Enter legal or access information (optional)..."
            />
            {legalMessage && (
              <>
                <button
                  type="button"
                  onClick={() => setLegalMessage("")}
                  className="mt-2 text-sm text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300"
                >
                  Clear message
                </button>
                <div className="mt-4">
                  <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Preview:</p>
                  <div className="bg-red-50 dark:bg-red-900/30 rounded-lg shadow-md p-4">
                    <div 
                      className="prose prose-sm max-w-none dark:prose-invert"
                      dangerouslySetInnerHTML={{ __html: legalMessage }}
                    />
                  </div>
                </div>
              </>
            )}
          </Card>

          <Card>
            <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-100 mb-4">
              Admin Comment <span className="text-red-500">*</span>
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
              Provide a reason for creating this trigpoint. This will be recorded in the audit trail.
            </p>
            <textarea
              value={adminComment}
              onChange={(e) => setAdminComment(e.target.value)}
              required
              rows={4}
              className="w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-gray-800 dark:text-gray-100 bg-white dark:bg-gray-700 shadow-sm focus:border-trig-green-500 focus:ring-2 focus:ring-trig-green-400"
              placeholder="e.g., Adding missing trigpoint discovered during survey..."
            />
          </Card>

          {saveError && (
            <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded-md">
              {saveError}
            </div>
          )}

          {saveSuccess && (
            <div className="bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 text-green-700 dark:text-green-400 px-4 py-3 rounded-md">
              Trigpoint created successfully! Redirecting...
            </div>
          )}

          <div className="flex gap-3">
            <Button type="submit" disabled={isSaving}>
              {isSaving ? (
                <span className="flex items-center gap-2">
                  <Spinner size="sm" />
                  <span>Creating...</span>
                </span>
              ) : (
                "Create Trigpoint"
              )}
            </Button>
            <Link to="/admin">
              <Button type="button" variant="secondary">
                Cancel
              </Button>
            </Link>
          </div>
        </form>
      </div>
    </>
  );
}

