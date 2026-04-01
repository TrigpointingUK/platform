import { FormEvent, useEffect, useMemo, useState } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import { Link, useNavigate, useParams } from "react-router-dom";
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
  fetchTrigForEdit,
  fetchStatuses,
  updateTrigAdmin,
  TrigAdminDetail,
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

export default function TrigEdit() {
  const { trigId } = useParams<{ trigId: string }>();
  const { getAccessTokenSilently } = useAuth0();
  const navigate = useNavigate();
  const { hasAdminRole, hasAdminScope, isLoading: isAuthLoading } = useAdminAuth();

  const [trig, setTrig] = useState<TrigAdminDetail | null>(null);
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

  // Update document title when trig data loads
  useDocumentTitle(trig ? `Edit: ${trig.name}` : null);

  // Form fields
  const [name, setName] = useState("");
  const [fbNumber, setFbNumber] = useState("");
  const [stnNumber, setStnNumber] = useState("");
  const [stnNumberActive, setStnNumberActive] = useState("");
  const [stnNumberPassive, setStnNumberPassive] = useState("");
  const [stnNumberOsgb36, setStnNumberOsgb36] = useState("");
  const [statusId, setStatusId] = useState(1);
  const [typeId, setTypeId] = useState<number | null>(null);
  const [currentUse, setCurrentUse] = useState("none");
  const [historicUse, setHistoricUse] = useState("none");
  const [condition, setCondition] = useState("G");
  const [wgsLat, setWgsLat] = useState("");
  const [wgsLong, setWgsLong] = useState("");
  const [wgsHeight, setWgsHeight] = useState<number | null>(0);
  const [osgbEastings, setOsgbEastings] = useState(0);
  const [osgbNorthings, setOsgbNorthings] = useState(0);
  const [osgbGridref, setOsgbGridref] = useState("");
  const [osgbHeight, setOsgbHeight] = useState<number | null>(0);
  const [legalMessage, setLegalMessage] = useState<string>("");
  const [action, setAction] = useState<"solved" | "revisit" | "cant_fix">("revisit");
  const [adminComment, setAdminComment] = useState("");

  // Original location fields
  const [originalWgsLat, setOriginalWgsLat] = useState<string>("");
  const [originalWgsLong, setOriginalWgsLong] = useState<string>("");
  const [originalOsgbEastings, setOriginalOsgbEastings] = useState<string>("");
  const [originalOsgbNorthings, setOriginalOsgbNorthings] = useState<string>("");
  const [originalOsgbGridref, setOriginalOsgbGridref] = useState<string>("");
  const [originalGridSystem, setOriginalGridSystem] = useState<string>("");
  const [originalProvenance, setOriginalProvenance] = useState<string>("");
  const [originalWgsHeight, setOriginalWgsHeight] = useState<string>("");
  const [originalOsgbHeight, setOriginalOsgbHeight] = useState<string>("");

  // Key to force LinkedCoordinates re-mount when restoring from original
  const [coordinatesKey, setCoordinatesKey] = useState(0);

  useEffect(() => {
    if (!hasAdminRole || !hasAdminScope || !trigId) {
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

        const [trigData, statusesData] = await Promise.all([
          fetchTrigForEdit(parseInt(trigId), token),
          fetchStatuses(token),
        ]);

        if (!cancelled) {
          setTrig(trigData);
          setStatuses(statusesData);

          // Populate form fields
          setName(trigData.name);
          setFbNumber(trigData.fb_number);
          setStnNumber(trigData.stn_number);
          setStnNumberActive(trigData.stn_number_active);
          setStnNumberPassive(trigData.stn_number_passive);
          setStnNumberOsgb36(trigData.stn_number_osgb36);
          setStatusId(trigData.status_id);
          setTypeId(trigData.type_id);
          setCurrentUse(trigData.current_use);
          setHistoricUse(trigData.historic_use);
          setCondition(trigData.condition);
          // Format coordinates with appropriate decimal places
          setWgsLat(Number(trigData.wgs_lat).toFixed(8));
          setWgsLong(Number(trigData.wgs_long).toFixed(8));
          setWgsHeight(trigData.wgs_height);
          setOsgbEastings(trigData.osgb_eastings);
          setOsgbNorthings(trigData.osgb_northings);
          setOsgbGridref(trigData.osgb_gridref);
          setOsgbHeight(trigData.osgb_height);
          setLegalMessage(trigData.legal_message || "");
          // Original location fields
          setOriginalWgsLat(trigData.original_wgs_lat !== null ? Number(trigData.original_wgs_lat).toFixed(8) : "");
          setOriginalWgsLong(trigData.original_wgs_long !== null ? Number(trigData.original_wgs_long).toFixed(8) : "");
          setOriginalOsgbEastings(trigData.original_osgb_eastings !== null ? String(trigData.original_osgb_eastings) : "");
          setOriginalOsgbNorthings(trigData.original_osgb_northings !== null ? String(trigData.original_osgb_northings) : "");
          setOriginalOsgbGridref(trigData.original_osgb_gridref || "");
          setOriginalGridSystem(trigData.original_grid_system || "");
          setOriginalProvenance(trigData.original_provenance || "");
          setOriginalWgsHeight(trigData.original_wgs_height !== null ? String(trigData.original_wgs_height) : "");
          setOriginalOsgbHeight(trigData.original_osgb_height !== null ? String(trigData.original_osgb_height) : "");
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load trigpoint");
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
  }, [getAccessTokenSilently, hasAdminRole, hasAdminScope, trigId]);

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

    setIsSaving(true);
    setSaveError(null);
    setSaveSuccess(false);

    try {
      const token = await getAccessTokenSilently({
        authorizationParams: { ...ADMIN_AUTH_PARAMS },
      });

      await updateTrigAdmin(
        parseInt(trigId!),
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
          action,
          admin_comment: adminComment,
        },
        token
      );

      setSaveSuccess(true);
      // Redirect to trigpoint detail page after short delay
      setTimeout(() => {
        navigate(`/trigs/${trigId}`);
      }, 1500);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Failed to save changes");
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
              <span className="ml-3 text-gray-600 dark:text-gray-400">Loading trigpoint...</span>
            </div>
          </Card>
        </div>
      </>
    );
  }

  if (error || !trig) {
    return (
      <>
        <div className="max-w-6xl mx-auto">
          <Card>
            <div className="text-center py-12">
              <p className="text-red-600 dark:text-red-400">Error: {error || "Trigpoint not found"}</p>
              <Link
                to="/admin/needs-attention"
                className="text-trig-green-600 hover:text-trig-green-700 dark:text-trig-green-400 dark:hover:text-trig-green-300 mt-4 inline-block"
              >
                ← Back to list
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
                Edit Trigpoint: {trig.name}
              </h1>
              <p className="text-gray-600 dark:text-gray-400 mb-2">
                Waypoint: {trig.waypoint} | ID: {trig.id}
              </p>
              <div className="flex gap-4 text-sm">
                <Link
                  to={`/trigs/${trig.id}`}
                  className="text-trig-green-600 hover:text-trig-green-700 dark:text-trig-green-400 dark:hover:text-trig-green-300 font-medium"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  View Trigpoint Details →
                </Link>
              </div>
            </div>
            <Link
              to="/admin/needs-attention"
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
                  Name
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  className="w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-gray-800 dark:text-gray-100 bg-white dark:bg-gray-700 shadow-sm focus:border-trig-green-500 focus:ring-2 focus:ring-trig-green-400"
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
              Coordinates
            </h2>
            <LinkedCoordinates
              key={coordinatesKey}
              wgsLat={wgsLat}
              wgsLong={wgsLong}
              wgsHeight={wgsHeight}
              osgbEastings={osgbEastings}
              osgbNorthings={osgbNorthings}
              osgbGridref={osgbGridref}
              osgbHeight={osgbHeight}
              initialGridSystem={trig?.grid_system as 'gb' | 'ie' | null}
              onWgsChange={handleWgsChange}
              onOsgbChange={handleOsgbChange}
            />
          </Card>

          <Card>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-100">
                Original OS Location
              </h2>
              <Button
                type="button"
                variant="secondary"
                onClick={() => {
                  // Copy original coordinates to current
                  if (originalWgsLat) setWgsLat(originalWgsLat);
                  if (originalWgsLong) setWgsLong(originalWgsLong);
                  if (originalOsgbEastings) setOsgbEastings(parseFloat(originalOsgbEastings));
                  if (originalOsgbNorthings) setOsgbNorthings(parseFloat(originalOsgbNorthings));
                  if (originalOsgbGridref) setOsgbGridref(originalOsgbGridref);
                  if (originalWgsHeight) setWgsHeight(parseFloat(originalWgsHeight));
                  if (originalOsgbHeight) setOsgbHeight(parseFloat(originalOsgbHeight));
                  // Force LinkedCoordinates to re-mount with new values
                  setCoordinatesKey(k => k + 1);
                }}
                disabled={!originalWgsLat || !originalWgsLong}
              >
                Restore from Original
              </Button>
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              The official OS-published location. Use &quot;Restore from Original&quot; to copy these values to the current coordinates above.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 text-sm">
              <div>
                <span className="font-medium text-gray-700 dark:text-gray-300">Grid Reference:</span>{" "}
                <span className="text-gray-600 dark:text-gray-400 font-mono">
                  {originalOsgbGridref || "—"}
                </span>
              </div>
              <div>
                <span className="font-medium text-gray-700 dark:text-gray-300">Grid System:</span>{" "}
                <span className="text-gray-600 dark:text-gray-400">
                  {originalGridSystem === "gb" ? "British National Grid" : originalGridSystem === "ie" ? "Irish Grid" : "—"}
                </span>
              </div>
              <div>
                <span className="font-medium text-gray-700 dark:text-gray-300">WGS84:</span>{" "}
                <span className="text-gray-600 dark:text-gray-400 font-mono">
                  {originalWgsLat && originalWgsLong ? `${originalWgsLat}, ${originalWgsLong}` : "—"}
                </span>
              </div>
              <div>
                <span className="font-medium text-gray-700 dark:text-gray-300">Eastings:</span>{" "}
                <span className="text-gray-600 dark:text-gray-400 font-mono">
                  {originalOsgbEastings || "—"}
                </span>
              </div>
              <div>
                <span className="font-medium text-gray-700 dark:text-gray-300">Northings:</span>{" "}
                <span className="text-gray-600 dark:text-gray-400 font-mono">
                  {originalOsgbNorthings || "—"}
                </span>
              </div>
              <div>
                <span className="font-medium text-gray-700 dark:text-gray-300">WGS84 Height:</span>{" "}
                <span className="text-gray-600 dark:text-gray-400 font-mono">
                  {originalWgsHeight ? `${originalWgsHeight}m` : "—"}
                </span>
              </div>
              <div>
                <span className="font-medium text-gray-700 dark:text-gray-300">OSGB Height:</span>{" "}
                <span className="text-gray-600 dark:text-gray-400 font-mono">
                  {originalOsgbHeight ? `${originalOsgbHeight}m` : "—"}
                </span>
              </div>
              <div className="md:col-span-2 lg:col-span-3">
                <span className="font-medium text-gray-700 dark:text-gray-300">Provenance:</span>{" "}
                <span className="text-gray-600 dark:text-gray-400">
                  {originalProvenance || "—"}
                </span>
              </div>
            </div>
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
              Admin Action
            </h2>

            <div className="space-y-3 mb-6">
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="radio"
                  name="action"
                  value="solved"
                  checked={action === "solved"}
                  onChange={(e) => setAction(e.target.value as typeof action)}
                  className="h-4 w-4 text-trig-green-600 focus:ring-trig-green-500"
                />
                <span className="text-gray-800 dark:text-gray-200">
                  Problem solved! Close log (sets needs_attention to 0)
                </span>
              </label>

              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="radio"
                  name="action"
                  value="revisit"
                  checked={action === "revisit"}
                  onChange={(e) => setAction(e.target.value as typeof action)}
                  className="h-4 w-4 text-trig-green-600 focus:ring-trig-green-500"
                />
                <span className="text-gray-800 dark:text-gray-200">
                  Leave in &quot;Needs attention&quot; status, to be revisited later
                </span>
              </label>

              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="radio"
                  name="action"
                  value="cant_fix"
                  checked={action === "cant_fix"}
                  onChange={(e) => setAction(e.target.value as typeof action)}
                  className="h-4 w-4 text-trig-green-600 focus:ring-trig-green-500"
                />
                <span className="text-gray-800 dark:text-gray-200">
                  Can&apos;t fix using this tool (increments needs_attention)
                </span>
              </label>
            </div>

            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Admin Comment (required)
              </label>
              <textarea
                value={adminComment}
                onChange={(e) => setAdminComment(e.target.value)}
                required
                rows={4}
                className="w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-gray-800 dark:text-gray-100 bg-white dark:bg-gray-700 shadow-sm focus:border-trig-green-500 focus:ring-2 focus:ring-trig-green-400"
                placeholder="Enter your comment about this update..."
              />
            </div>

            {trig.attention_comment && (
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Comment History
                </label>
                <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-md border border-gray-300 dark:border-gray-600 whitespace-pre-line text-sm text-gray-700 dark:text-gray-300 max-h-64 overflow-y-auto">
                  {trig.attention_comment}
                </div>
              </div>
            )}
          </Card>

          {saveError && (
            <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded-md">
              {saveError}
            </div>
          )}

          {saveSuccess && (
            <div className="bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 text-green-700 dark:text-green-400 px-4 py-3 rounded-md">
              Changes saved successfully! Redirecting...
            </div>
          )}

          <div className="flex gap-3">
            <Button type="submit" disabled={isSaving}>
              {isSaving ? (
                <span className="flex items-center gap-2">
                  <Spinner size="sm" />
                  <span>Saving...</span>
                </span>
              ) : (
                "Update"
              )}
            </Button>
            <Button type="button" variant="secondary" onClick={() => navigate(-1)}>
              Cancel
            </Button>
          </div>
        </form>
      </div>
    </>
  );
}

