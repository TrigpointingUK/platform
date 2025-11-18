import { FormEvent, useEffect, useState } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import { Link, useNavigate, useParams } from "react-router-dom";
import Layout from "../../components/layout/Layout";
import Card from "../../components/ui/Card";
import Spinner from "../../components/ui/Spinner";
import Button from "../../components/ui/Button";
import LinkedCoordinates from "../../components/admin/LinkedCoordinates";
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

const CONDITION_OPTIONS = [
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

const PHYSICAL_TYPE_OPTIONS = [
  "Pillar",
  "FBM",
  "Bolt",
  "Block",
  "Buried Block",
  "Surface Block",
  "Cannon",
  "Intersection Station",
  "Rivet",
  "Spider",
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
  const { getAccessTokenSilently, user } = useAuth0();
  const navigate = useNavigate();

  const [trig, setTrig] = useState<TrigAdminDetail | null>(null);
  const [statuses, setStatuses] = useState<StatusRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Form fields
  const [name, setName] = useState("");
  const [fbNumber, setFbNumber] = useState("");
  const [stnNumber, setStnNumber] = useState("");
  const [statusId, setStatusId] = useState(1);
  const [currentUse, setCurrentUse] = useState("none");
  const [historicUse, setHistoricUse] = useState("none");
  const [physicalType, setPhysicalType] = useState("Pillar");
  const [condition, setCondition] = useState("G");
  const [wgsLat, setWgsLat] = useState("");
  const [wgsLong, setWgsLong] = useState("");
  const [wgsHeight, setWgsHeight] = useState(0);
  const [osgbEastings, setOsgbEastings] = useState(0);
  const [osgbNorthings, setOsgbNorthings] = useState(0);
  const [osgbGridref, setOsgbGridref] = useState("");
  const [osgbHeight, setOsgbHeight] = useState(0);
  const [action, setAction] = useState<"solved" | "revisit" | "cant_fix">("revisit");
  const [adminComment, setAdminComment] = useState("");

  // Check if user has admin role
  const userRoles = (user?.["https://trigpointing.uk/roles"] as string[]) || [];
  const hasAdminRole = userRoles.includes("api-admin");

  useEffect(() => {
    if (!hasAdminRole || !trigId) {
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
          setStatusId(trigData.status_id);
          setCurrentUse(trigData.current_use);
          setHistoricUse(trigData.historic_use);
          setPhysicalType(trigData.physical_type);
          setCondition(trigData.condition);
          setWgsLat(trigData.wgs_lat);
          setWgsLong(trigData.wgs_long);
          setWgsHeight(trigData.wgs_height);
          setOsgbEastings(trigData.osgb_eastings);
          setOsgbNorthings(trigData.osgb_northings);
          setOsgbGridref(trigData.osgb_gridref);
          setOsgbHeight(trigData.osgb_height);
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
  }, [getAccessTokenSilently, hasAdminRole, trigId]);

  const handleWgsChange = (lat: string, long: string) => {
    setWgsLat(lat);
    setWgsLong(long);
  };

  const handleOsgbChange = (eastings: number, northings: number, gridref: string) => {
    setOsgbEastings(eastings);
    setOsgbNorthings(northings);
    setOsgbGridref(gridref);
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
          status_id: statusId,
          current_use: currentUse,
          historic_use: historicUse,
          physical_type: physicalType,
          condition,
          wgs_lat: wgsLat,
          wgs_long: wgsLong,
          wgs_height: wgsHeight,
          osgb_eastings: osgbEastings,
          osgb_northings: osgbNorthings,
          osgb_gridref: osgbGridref,
          osgb_height: osgbHeight,
          action,
          admin_comment: adminComment,
        },
        token
      );

      setSaveSuccess(true);
      // Redirect back to list after short delay
      setTimeout(() => {
        navigate("/admin/needs-attention");
      }, 1500);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Failed to save changes");
    } finally {
      setIsSaving(false);
    }
  };

  if (!hasAdminRole) {
    return (
      <Layout>
        <div className="max-w-6xl mx-auto">
          <Card>
            <div className="text-center py-12">
              <h1 className="text-2xl font-bold text-gray-800 mb-4">
                Access Denied
              </h1>
              <p className="text-gray-600">
                You do not have permission to access this page.
              </p>
            </div>
          </Card>
        </div>
      </Layout>
    );
  }

  if (isLoading) {
    return (
      <Layout>
        <div className="max-w-6xl mx-auto">
          <Card>
            <div className="flex items-center justify-center py-12">
              <Spinner size="lg" />
              <span className="ml-3 text-gray-600">Loading trigpoint...</span>
            </div>
          </Card>
        </div>
      </Layout>
    );
  }

  if (error || !trig) {
    return (
      <Layout>
        <div className="max-w-6xl mx-auto">
          <Card>
            <div className="text-center py-12">
              <p className="text-red-600">Error: {error || "Trigpoint not found"}</p>
              <Link
                to="/admin/needs-attention"
                className="text-[#046935] hover:text-[#035228] mt-4 inline-block"
              >
                ← Back to list
              </Link>
            </div>
          </Card>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="max-w-6xl mx-auto">
        <Card className="mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-800 mb-2">
                Edit Trigpoint: {trig.name}
              </h1>
              <p className="text-gray-600 mb-2">
                Waypoint: {trig.waypoint} | ID: {trig.id}
              </p>
              <div className="flex gap-4 text-sm">
                <Link
                  to={`/trigs/${trig.id}`}
                  className="text-[#046935] hover:text-[#035228] font-medium"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  View Trigpoint Details →
                </Link>
              </div>
            </div>
            <Link
              to="/admin/needs-attention"
              className="text-[#046935] hover:text-[#035228] font-medium"
            >
              ← Back to Admin
            </Link>
          </div>
        </Card>

        <form onSubmit={handleSubmit} className="space-y-6">
          <Card>
            <h2 className="text-xl font-semibold text-gray-800 mb-4">
              Basic Information
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Name
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-gray-800 shadow-sm focus:border-trig-green-500 focus:ring-2 focus:ring-trig-green-400"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Type
                </label>
                <select
                  value={physicalType}
                  onChange={(e) => setPhysicalType(e.target.value)}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-gray-800 shadow-sm focus:border-trig-green-500 focus:ring-2 focus:ring-trig-green-400"
                >
                  {PHYSICAL_TYPE_OPTIONS.map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Status
                </label>
                <select
                  value={statusId}
                  onChange={(e) => setStatusId(parseInt(e.target.value))}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-gray-800 shadow-sm focus:border-trig-green-500 focus:ring-2 focus:ring-trig-green-400"
                >
                  {statuses.map((status) => (
                    <option key={status.id} value={status.id}>
                      {status.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Current Use
                </label>
                <select
                  value={currentUse}
                  onChange={(e) => setCurrentUse(e.target.value)}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-gray-800 shadow-sm focus:border-trig-green-500 focus:ring-2 focus:ring-trig-green-400"
                >
                  {CURRENT_USE_OPTIONS.map((use) => (
                    <option key={use} value={use}>
                      {use}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Historic Use
                </label>
                <select
                  value={historicUse}
                  onChange={(e) => setHistoricUse(e.target.value)}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-gray-800 shadow-sm focus:border-trig-green-500 focus:ring-2 focus:ring-trig-green-400"
                >
                  {HISTORIC_USE_OPTIONS.map((use) => (
                    <option key={use} value={use}>
                      {use}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Condition
                </label>
                <select
                  value={condition}
                  onChange={(e) => setCondition(e.target.value)}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-gray-800 shadow-sm focus:border-trig-green-500 focus:ring-2 focus:ring-trig-green-400"
                >
                  {CONDITION_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  FB Number
                </label>
                <input
                  type="text"
                  value={fbNumber}
                  onChange={(e) => setFbNumber(e.target.value)}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-gray-800 shadow-sm focus:border-trig-green-500 focus:ring-2 focus:ring-trig-green-400"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Station Number
                </label>
                <input
                  type="text"
                  value={stnNumber}
                  onChange={(e) => setStnNumber(e.target.value)}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-gray-800 shadow-sm focus:border-trig-green-500 focus:ring-2 focus:ring-trig-green-400"
                />
              </div>
            </div>
          </Card>

          <Card>
            <h2 className="text-xl font-semibold text-gray-800 mb-4">
              Coordinates
            </h2>
            <LinkedCoordinates
              wgsLat={wgsLat}
              wgsLong={wgsLong}
              osgbEastings={osgbEastings}
              osgbNorthings={osgbNorthings}
              osgbGridref={osgbGridref}
              onWgsChange={handleWgsChange}
              onOsgbChange={handleOsgbChange}
            />

            <div className="grid grid-cols-2 gap-4 mt-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  WGS Height (m)
                </label>
                <input
                  type="number"
                  value={wgsHeight}
                  onChange={(e) => setWgsHeight(parseInt(e.target.value) || 0)}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-gray-800 shadow-sm focus:border-trig-green-500 focus:ring-2 focus:ring-trig-green-400"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  OSGB Height (m)
                </label>
                <input
                  type="number"
                  value={osgbHeight}
                  onChange={(e) => setOsgbHeight(parseInt(e.target.value) || 0)}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-gray-800 shadow-sm focus:border-trig-green-500 focus:ring-2 focus:ring-trig-green-400"
                />
              </div>
            </div>
          </Card>

          <Card>
            <h2 className="text-xl font-semibold text-gray-800 mb-4">
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
                  className="h-4 w-4 text-[#046935] focus:ring-[#046935]"
                />
                <span className="text-gray-800">
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
                  className="h-4 w-4 text-[#046935] focus:ring-[#046935]"
                />
                <span className="text-gray-800">
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
                  className="h-4 w-4 text-[#046935] focus:ring-[#046935]"
                />
                <span className="text-gray-800">
                  Can&apos;t fix using this tool (increments needs_attention)
                </span>
              </label>
            </div>

            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Admin Comment (required)
              </label>
              <textarea
                value={adminComment}
                onChange={(e) => setAdminComment(e.target.value)}
                required
                rows={4}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-gray-800 shadow-sm focus:border-trig-green-500 focus:ring-2 focus:ring-trig-green-400"
                placeholder="Enter your comment about this update..."
              />
            </div>

            {trig.attention_comment && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Comment History
                </label>
                <div className="bg-gray-50 p-4 rounded-md border border-gray-300 whitespace-pre-line text-sm text-gray-700 max-h-64 overflow-y-auto">
                  {trig.attention_comment}
                </div>
              </div>
            )}
          </Card>

          {saveError && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
              {saveError}
            </div>
          )}

          {saveSuccess && (
            <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-md">
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
            <Link to="/admin/needs-attention">
              <Button type="button" variant="secondary">
                Back to Admin
              </Button>
            </Link>
          </div>
        </form>
      </div>
    </Layout>
  );
}

