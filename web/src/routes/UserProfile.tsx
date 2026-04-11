import { useParams, Link } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { useAuth0 } from "@auth0/auth0-react";
import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import Card from "../components/ui/Card";
import Spinner from "../components/ui/Spinner";
import EditableField from "../components/ui/EditableField";
import LogList from "../components/logs/LogList";
import AreaBreakdown from "../components/profile/AreaBreakdown";
import AnimatedUserMap from "../components/profile/AnimatedUserMap";
import AvatarUploadModal from "../components/profile/AvatarUploadModal";
import { useUserProfile, updateUserProfile } from "../hooks/useUserProfile";
import { useInfiniteLogs } from "../hooks/useInfiniteLogs";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { useCanonical } from "../hooks/useCanonical";
import { useNoIndex } from "../hooks/useNoIndex";

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
  const [uploadedAvatarUrl, setUploadedAvatarUrl] = useState<string | null>(null);
  
  // If no userId in URL, fetch "me", otherwise fetch the specified user
  const targetUserId = userId || "me";
  const { data: user, isLoading, error } = useUserProfile(targetUserId);
  
  // Get current user's UI preferences (always fetch "me" for the viewer's prefs)
  const { data: currentUserProfile } = useUserProfile("me");
  const showTrigCondition = currentUserProfile?.prefs?.ui_prefs?.show_trig_condition ?? false;

  // Update document title when user data loads
  useDocumentTitle(user ? `${user.name}'s Profile` : null);
  useCanonical(userId ? `/profile/${userId}` : null);
  useNoIndex(!!error);

  // Own profile if: no userId param, or userId matches the logged-in user's ID
  const isOwnProfile = !userId || (authUser && userId === authUser.sub);

  // Use uploaded avatar if set (for immediate feedback), otherwise fall back to Auth0 picture
  const avatarUrl = uploadedAvatarUrl ?? authUser?.picture ?? null;

  // Extract scopes from JWT token
  useEffect(() => {
    const extractScopes = async () => {
      if (isOwnProfile) {
        try {
          const token = await getAccessTokenSilently();
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

  // Fetch user logs for recent activity section (limit to 5)
  // Use userId from URL, or if viewing own profile (/profile), use the loaded user's ID
  const logsUserId = userId ? parseInt(userId, 10) : user?.id;
  const {
    data: logsData,
    isLoading: isLoadingLogs,
  } = useInfiniteLogs({ userId: logsUserId });

  // Get first 5 logs for the preview
  const recentLogs = logsData?.pages[0]?.items.slice(0, 5) || [];

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
      <div className="max-w-6xl mx-auto">
        <div className="py-12 text-center">
          <Spinner size="lg" />
          <p className="text-gray-600 dark:text-gray-400 mt-4">Loading profile...</p>
        </div>
      </div>
    );
  }

  if (error || !user) {
    return (
      <div className="max-w-6xl mx-auto">
        <Card>
          <div className="text-center py-12">
            <p className="text-red-600 dark:text-red-400 text-lg">
              {error ? "Failed to load user profile" : "User not found"}
            </p>
          </div>
        </Card>
      </div>
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
    <div className="max-w-6xl mx-auto">
      {/* Header Section */}
        <Card className="mb-6">
          {/* Main layout: Two columns on large screens */}
          <div className="flex flex-col xl:flex-row gap-6">
            {/* Left column: All user info */}
            <div className="flex-1">
              {/* Top: Avatar, Username, Member Since, and Statistics */}
              <div className="flex items-start gap-6 flex-col sm:flex-row mb-6">
                <div className="flex items-center gap-4 flex-shrink-0">
                  {isOwnProfile ? (
                    <AvatarUploadModal
                      currentPictureUrl={avatarUrl || undefined}
                      onUploaded={(newUrl) => setUploadedAvatarUrl(newUrl)}
                    />
                  ) : user.has_avatar ? (
                    <img
                      src={`https://trigpointinguk-avatars.s3.amazonaws.com/U${user.id.toString().padStart(5, "0")}.jpg`}
                      alt={user.name}
                      className="w-20 h-20 rounded-full object-cover hidden"
                      onLoad={(e) => e.currentTarget.classList.remove("hidden")}
                      onError={(e) => e.currentTarget.classList.add("hidden")}
                    />
                  ) : null}
                  <div>
                    <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100 mb-2">
                      {user.name}
                    </h1>
                    <p className="text-gray-600 dark:text-gray-400">
                      Member since {memberSince}
                    </p>
                  </div>
                </div>

                {user.stats && (
                  <div className="flex gap-8 text-center flex-1 min-w-0 justify-center">
                    <Link
                      to={`/logs?user=${displayUserId}`}
                      className="hover:opacity-80 transition-opacity"
                    >
                      <div className="text-2xl font-bold text-trig-green-600">
                        {user.stats.total_trigs_logged.toLocaleString()}
                      </div>
                      <div className="text-sm text-gray-600 dark:text-gray-400">Trigs Logged</div>
                    </Link>
                    <Link
                      to={`/logs?user=${displayUserId}`}
                      className="hover:opacity-80 transition-opacity"
                    >
                      <div className="text-2xl font-bold text-trig-green-600">
                        {user.stats.total_logs.toLocaleString()}
                      </div>
                      <div className="text-sm text-gray-600 dark:text-gray-400">Total Logs</div>
                    </Link>
                    <Link
                      to={`/profile/${displayUserId}/photos`}
                      className="hover:opacity-80 transition-opacity"
                    >
                      <div className="text-2xl font-bold text-trig-green-600">
                        {user.stats.total_photos.toLocaleString()}
                      </div>
                      <div className="text-sm text-gray-600 dark:text-gray-400">Photos</div>
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

            {/* Right column: Animated Map and Badge */}
            <div className="flex flex-col gap-6 xl:w-auto xl:flex-shrink-0 min-w-0">
              <AnimatedUserMap userId={displayUserId} height={400} autoPlay />
              <div className="flex justify-center items-center w-full">
                <img 
                  src={`${apiBase}/v1/users/${displayUserId}/badge`}
                  alt={`${user.name}'s badge`}
                  width="200"
                  height="50"
                  className="rounded border border-gray-200 dark:border-gray-600 cursor-pointer hover:opacity-80 transition-opacity"
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
            <h2 className="text-2xl font-bold text-gray-800 dark:text-gray-100 mb-4">
              Trig Statistics Breakdown
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
              {/* By Recent Use */}
              <Card>
                <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-3">
                  Recent Use
                </h3>
                <div className="space-y-2">
                  {Object.entries(user.breakdown.by_current_use)
                    .sort(([, a], [, b]) => b - a)
                    .map(([key, value]) => (
                      <div key={key} className="flex justify-between text-sm">
                        <span className="text-gray-700 dark:text-gray-300">{key}</span>
                        <span className="font-medium text-trig-green-600">
                          {value}
                        </span>
                      </div>
                    ))}
                  {Object.keys(user.breakdown.by_current_use).length === 0 && (
                    <p className="text-gray-400 dark:text-gray-500 text-sm italic">No data</p>
                  )}
                </div>
              </Card>

              {/* By Historic Use */}
              <Card>
                <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-3">
                  Historic Use
                </h3>
                <div className="space-y-2">
                  {Object.entries(user.breakdown.by_historic_use)
                    .sort(([, a], [, b]) => b - a)
                    .map(([key, value]) => (
                      <div key={key} className="flex justify-between text-sm">
                        <span className="text-gray-700 dark:text-gray-300">{key}</span>
                        <span className="font-medium text-trig-green-600">
                          {value}
                        </span>
                      </div>
                    ))}
                  {Object.keys(user.breakdown.by_historic_use).length === 0 && (
                    <p className="text-gray-400 dark:text-gray-500 text-sm italic">No data</p>
                  )}
                </div>
              </Card>

              {/* By Type (grouped by category) */}
              <Card>
                <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-3">
                  Type
                </h3>
                <div className="space-y-4">
                  {user.breakdown.by_type && user.breakdown.by_type.length > 0 ? (
                    user.breakdown.by_type.map((category) => (
                      <div key={category.category_code}>
                        <h4 className="text-sm font-semibold text-gray-600 dark:text-gray-400 mb-2">
                          {category.category_name}
                        </h4>
                        <div className="space-y-1 pl-3">
                          {category.types.map((type) => (
                            <div key={type.type_code} className="flex justify-between text-sm">
                              <span className="text-gray-700 dark:text-gray-300">
                                {type.type_code === category.category_code
                                  ? type.type_name
                                  : type.type_name}
                              </span>
                              <span className="font-medium text-trig-green-600">
                                {type.count}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))
                  ) : (
                    <p className="text-gray-400 dark:text-gray-500 text-sm italic">No data</p>
                  )}
                </div>
              </Card>

              {/* By Condition */}
              <Card>
                <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-3">
                  Condition
                </h3>
                <div className="space-y-2">
                  {Object.entries(user.breakdown.by_condition)
                    .sort(([, a], [, b]) => b - a)
                    .map(([key, value]) => (
                      <div key={key} className="flex justify-between text-sm">
                        <span className="text-gray-700 dark:text-gray-300">{key}</span>
                        <span className="font-medium text-trig-green-600">
                          {value}
                        </span>
                      </div>
                    ))}
                  {Object.keys(user.breakdown.by_condition).length === 0 && (
                    <p className="text-gray-400 dark:text-gray-500 text-sm italic">No data</p>
                  )}
                </div>
              </Card>

              {/* By Area */}
              <AreaBreakdown userId={displayUserId} />
            </div>
          </div>
        )}

        {/* Recent Logs Section */}
        <div className="mb-6">
          <Card>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-bold text-gray-800 dark:text-gray-100">Recent Logs</h2>
              <Link
                to={`/logs?user=${displayUserId}`}
                className="text-sm text-trig-green-600 hover:text-trig-green-700 hover:underline"
              >
                View all logs →
              </Link>
            </div>
            <LogList
              logs={recentLogs}
              isLoading={isLoadingLogs}
              emptyMessage="No logs found"
              showTrigCondition={showTrigCondition}
              currentUserId={currentUserProfile?.id}
            />
          </Card>
        </div>

        {/* Debug Info Section (for own profile only) */}
        {isOwnProfile && user && (
          <Card className="mt-6">
            <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-3">
              Account Information
            </h2>
            <div className="space-y-2 text-sm font-mono bg-gray-50 dark:bg-gray-700 p-3 rounded">
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">User ID:</span>
                <span className="font-semibold text-gray-800 dark:text-gray-200">{user.id}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Auth0 User ID:</span>
                <span className="font-semibold text-gray-800 dark:text-gray-200 break-all">
                  {user.auth0_user_id || "N/A"}
                </span>
              </div>
              {user.roles && user.roles.length > 0 && (
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Roles:</span>
                  <span className="font-semibold text-gray-800 dark:text-gray-200">
                    {user.roles.join(", ")}
                  </span>
                </div>
              )}
              {tokenScopes.length > 0 && (
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Scopes:</span>
                  <span className="font-semibold text-gray-800 dark:text-gray-200">
                    {tokenScopes.join(", ")}
                  </span>
                </div>
              )}
            </div>
          </Card>
        )}
    </div>
  );
}

