import { useParams, Link } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { useAuth0 } from "@auth0/auth0-react";
import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import Layout from "../components/layout/Layout";
import Card from "../components/ui/Card";
import Spinner from "../components/ui/Spinner";
import EditableField from "../components/ui/EditableField";
import { useUserProfile, updateUserProfile } from "../hooks/useUserProfile";

// Helper function to decode JWT payload
interface JWTPayload {
  scope?: string;
  permissions?: string[];
  [key: string]: unknown;
}

function decodeJWT(token: string): JWTPayload | null {
  try {
    const base64Url = token.split(".")[1];
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split("")
        .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
        .join("")
    );
    return JSON.parse(jsonPayload) as JWTPayload;
  } catch (error) {
    console.error("Failed to decode JWT:", error);
    return null;
  }
}

export default function UserProfile() {
  const { userId } = useParams<{ userId: string }>();
  const queryClient = useQueryClient();
  const { getAccessTokenSilently, user: authUser } = useAuth0();
  const [tokenScopes, setTokenScopes] = useState<string[]>([]);
  
  // If no userId in URL, fetch "me", otherwise fetch the specified user
  const targetUserId = userId || "me";
  const { data: user, isLoading, error } = useUserProfile(targetUserId);

  // Own profile if: no userId param, or userId matches the logged-in user's ID
  const isOwnProfile = !userId || (authUser && userId === authUser.sub);

  // Extract scopes from JWT token
  useEffect(() => {
    const extractScopes = async () => {
      if (isOwnProfile) {
        try {
          const token = await getAccessTokenSilently({ cacheMode: "on" });
          const decoded = decodeJWT(token);

          if (decoded) {
            // Extract scopes - can be in "scope" (space-separated string) or "permissions" (array)
            let scopes: string[] = [];

            if (decoded.scope && typeof decoded.scope === "string") {
              scopes = decoded.scope.split(" ").filter((s: string) => s);
            } else if (
              decoded.permissions &&
              Array.isArray(decoded.permissions)
            ) {
              scopes = decoded.permissions;
            }

            setTokenScopes(scopes);
          }
        } catch (error) {
          console.error("Failed to extract scopes:", error);
        }
      }
    };

    extractScopes();
  }, [isOwnProfile, getAccessTokenSilently]);

  const handleFieldUpdate = async (field: string, value: string) => {
    try {
      // If updating full name, split into firstname and surname
      if (field === "fullname") {
        const nameParts = value.trim().split(/\s+/);
        const firstname = nameParts[0] || "";
        const surname = nameParts.slice(1).join(" ") || "";
        await updateUserProfile({ firstname, surname }, getAccessTokenSilently);
      } else {
        await updateUserProfile({ [field]: value }, getAccessTokenSilently);
      }
      // Invalidate to refetch
      queryClient.invalidateQueries({ queryKey: ["user", "profile"] });
    } catch (error) {
      console.error(`Failed to update ${field}:`, error);
      throw error;
    }
  };

  if (isLoading) {
    return (
      <Layout>
        <div className="max-w-6xl mx-auto">
          <div className="py-12 text-center">
            <Spinner size="lg" />
            <p className="text-gray-600 mt-4">Loading profile...</p>
          </div>
        </div>
      </Layout>
    );
  }

  if (error || !user) {
    return (
      <Layout>
        <div className="max-w-6xl mx-auto">
          <Card>
            <div className="text-center py-12">
              <p className="text-red-600 text-lg">
                {error ? "Failed to load user profile" : "User not found"}
              </p>
            </div>
          </Card>
        </div>
      </Layout>
    );
  }

  const memberSince = user.member_since
    ? new Date(user.member_since).toLocaleDateString("en-GB", {
        day: "numeric",
        month: "long",
        year: "numeric",
      })
    : "Unknown";

  const apiBase = import.meta.env.VITE_API_BASE as string;
  const displayUserId = userId || user.id;

  const handleBadgeClick = async () => {
    const badgeUrl = `${apiBase}/v1/users/${displayUserId}/badge`;
    try {
      await navigator.clipboard.writeText(badgeUrl);
      toast.success("Badge URL copied to clipboard!");
    } catch (error) {
      console.error("Failed to copy badge URL:", error);
      toast.error("Failed to copy URL. Please try again.");
    }
  };

  return (
    <Layout>
      <div className="max-w-6xl mx-auto">
        {/* Header Section */}
        <Card className="mb-6">
          {/* Main layout: Two columns on large screens */}
          <div className="flex flex-col xl:flex-row gap-6">
            {/* Left column: All user info */}
            <div className="flex-1">
              {/* Top: Username, Member Since, and Statistics */}
              <div className="flex items-start gap-6 flex-col sm:flex-row mb-6">
                <div className="flex-shrink-0">
                  <h1 className="text-3xl font-bold text-gray-800 mb-2">
                    {user.name}
                  </h1>
                  <p className="text-gray-600">
                    Member since {memberSince}
                  </p>
                </div>

                {user.stats && (
                  <div className="flex gap-8 text-center flex-1 min-w-0 justify-center">
                    <Link
                      to={`/profile/${displayUserId}/logs`}
                      className="hover:opacity-80 transition-opacity"
                    >
                      <div className="text-2xl font-bold text-trig-green-600">
                        {user.stats.total_trigs_logged.toLocaleString()}
                      </div>
                      <div className="text-sm text-gray-600">Trigs Logged</div>
                    </Link>
                    <Link
                      to={`/profile/${displayUserId}/logs`}
                      className="hover:opacity-80 transition-opacity"
                    >
                      <div className="text-2xl font-bold text-trig-green-600">
                        {user.stats.total_logs.toLocaleString()}
                      </div>
                      <div className="text-sm text-gray-600">Total Logs</div>
                    </Link>
                    <Link
                      to={`/profile/${displayUserId}/photos`}
                      className="hover:opacity-80 transition-opacity"
                    >
                      <div className="text-2xl font-bold text-trig-green-600">
                        {user.stats.total_photos.toLocaleString()}
                      </div>
                      <div className="text-sm text-gray-600">Photos</div>
                    </Link>
                  </div>
                )}
              </div>

              {/* User details fields */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                <EditableField
                  label="Username"
                  value={user.name}
                  onSave={(value) => handleFieldUpdate("name", value)}
                  editable={isOwnProfile}
                  maxLength={30}
                />
                {((user.firstname || user.surname) || isOwnProfile) && (
                  <EditableField
                    label="Full Name"
                    value={[user.firstname, user.surname].filter(Boolean).join(" ")}
                    onSave={(value) => handleFieldUpdate("fullname", value)}
                    editable={isOwnProfile}
                    placeholder="First Last"
                    maxLength={61}
                  />
                )}
                {!userId && (
                  <EditableField
                    label="Email"
                    value={user.prefs?.email || ""}
                    onSave={(value) => handleFieldUpdate("email", value)}
                    editable={isOwnProfile}
                    placeholder="your.email@example.com"
                    type="email"
                    maxLength={255}
                  />
                )}
                {(user.homepage || isOwnProfile) && (
                  <EditableField
                    label="Homepage"
                    value={user.homepage || ""}
                    onSave={(value) => handleFieldUpdate("homepage", value)}
                    editable={isOwnProfile}
                    placeholder="https://example.com"
                    maxLength={255}
                  />
                )}
              </div>

              {((user.about && user.about.trim() !== "") || isOwnProfile) && (
                <div className="mt-6">
                  <EditableField
                    label="About"
                    value={user.about}
                    onSave={(value) => handleFieldUpdate("about", value)}
                    editable={isOwnProfile}
                    multiline
                    placeholder="Tell us about yourself..."
                  />
                </div>
              )}
            </div>

            {/* Right column: Map and Badge stacked on large screens, side by side on medium */}
            <div className="flex flex-col md:flex-row xl:flex-col gap-6 xl:w-72 flex-shrink-0 md:items-start">
              <img 
                src={`${apiBase}/v1/users/${displayUserId}/map?height=500`}
                alt={`${user.name}'s trig map`}
                className="rounded-lg border border-gray-200 w-full h-auto"
                loading="lazy"
              />
              <div className="flex justify-center items-center w-full">
                <img 
                  src={`${apiBase}/v1/users/${displayUserId}/badge`}
                  alt={`${user.name}'s badge`}
                  width="200"
                  height="50"
                  className="rounded border border-gray-200 cursor-pointer hover:opacity-80 transition-opacity"
                  loading="lazy"
                  onClick={handleBadgeClick}
                  title="Click to copy URL"
                />
              </div>
            </div>
          </div>
        </Card>

        {/* Breakdown Section */}
        {user.breakdown && (
          <div className="mb-6">
            <h2 className="text-2xl font-bold text-gray-800 mb-4">
              Trig Statistics Breakdown
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* By Current Use */}
              <Card>
                <h3 className="text-lg font-semibold text-gray-800 mb-3">
                  Current Use
                </h3>
                <div className="space-y-2">
                  {Object.entries(user.breakdown.by_current_use)
                    .sort(([, a], [, b]) => b - a)
                    .map(([key, value]) => (
                      <div key={key} className="flex justify-between text-sm">
                        <span className="text-gray-700">{key}</span>
                        <span className="font-medium text-trig-green-600">
                          {value}
                        </span>
                      </div>
                    ))}
                  {Object.keys(user.breakdown.by_current_use).length === 0 && (
                    <p className="text-gray-400 text-sm italic">No data</p>
                  )}
                </div>
              </Card>

              {/* By Historic Use */}
              <Card>
                <h3 className="text-lg font-semibold text-gray-800 mb-3">
                  Historic Use
                </h3>
                <div className="space-y-2">
                  {Object.entries(user.breakdown.by_historic_use)
                    .sort(([, a], [, b]) => b - a)
                    .map(([key, value]) => (
                      <div key={key} className="flex justify-between text-sm">
                        <span className="text-gray-700">{key}</span>
                        <span className="font-medium text-trig-green-600">
                          {value}
                        </span>
                      </div>
                    ))}
                  {Object.keys(user.breakdown.by_historic_use).length === 0 && (
                    <p className="text-gray-400 text-sm italic">No data</p>
                  )}
                </div>
              </Card>

              {/* By Physical Type */}
              <Card>
                <h3 className="text-lg font-semibold text-gray-800 mb-3">
                  Physical Type
                </h3>
                <div className="space-y-2">
                  {Object.entries(user.breakdown.by_physical_type)
                    .sort(([, a], [, b]) => b - a)
                    .map(([key, value]) => (
                      <div key={key} className="flex justify-between text-sm">
                        <span className="text-gray-700">{key}</span>
                        <span className="font-medium text-trig-green-600">
                          {value}
                        </span>
                      </div>
                    ))}
                  {Object.keys(user.breakdown.by_physical_type).length === 0 && (
                    <p className="text-gray-400 text-sm italic">No data</p>
                  )}
                </div>
              </Card>

              {/* By Condition */}
              <Card>
                <h3 className="text-lg font-semibold text-gray-800 mb-3">
                  Condition
                </h3>
                <div className="space-y-2">
                  {Object.entries(user.breakdown.by_condition)
                    .sort(([, a], [, b]) => b - a)
                    .map(([key, value]) => (
                      <div key={key} className="flex justify-between text-sm">
                        <span className="text-gray-700">{key}</span>
                        <span className="font-medium text-trig-green-600">
                          {value}
                        </span>
                      </div>
                    ))}
                  {Object.keys(user.breakdown.by_condition).length === 0 && (
                    <p className="text-gray-400 text-sm italic">No data</p>
                  )}
                </div>
              </Card>
            </div>
          </div>
        )}

        {/* Debug Info Section (for own profile only) */}
        {isOwnProfile && user && (
          <Card className="mt-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-3">
              Account Information
            </h2>
            <div className="space-y-2 text-sm font-mono bg-gray-50 p-3 rounded">
              <div className="flex justify-between">
                <span className="text-gray-600">User ID:</span>
                <span className="font-semibold text-gray-800">{user.id}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Auth0 User ID:</span>
                <span className="font-semibold text-gray-800 break-all">
                  {user.auth0_user_id || "N/A"}
                </span>
              </div>
              {user.roles && user.roles.length > 0 && (
                <div className="flex justify-between">
                  <span className="text-gray-600">Roles:</span>
                  <span className="font-semibold text-gray-800">
                    {user.roles.join(", ")}
                  </span>
                </div>
              )}
              {tokenScopes.length > 0 && (
                <div className="flex justify-between">
                  <span className="text-gray-600">Scopes:</span>
                  <span className="font-semibold text-gray-800">
                    {tokenScopes.join(", ")}
                  </span>
                </div>
              )}
            </div>
          </Card>
        )}
      </div>
    </Layout>
  );
}

